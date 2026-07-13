from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Final, Mapping, Sequence

from rcp_rclm_runtime.errors import NumericValidationError, SchemaValidationError
from rcp_rclm_runtime.mathematics.intervals import (
    DEFAULT_PRECISION_BITS,
    IntervalEvidence,
    log_rational_interval,
    sum_intervals,
)
from rcp_rclm_runtime.mathematics.rational import Rational, rational_sum

DISTRIBUTION_SCHEMA_ID: Final[str] = "gate_b.distribution.v2"
ZERO_EXTENSION_SCHEMA_ID: Final[str] = "gate_b.zero_extension.v2"


@dataclass(frozen=True, slots=True)
class DistributionRecord:
    masses: Sequence[Rational]
    dimension: int

    schema_id: ClassVar[str] = DISTRIBUTION_SCHEMA_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "masses", tuple(self.masses))
        if isinstance(self.dimension, bool) or not isinstance(self.dimension, int):
            raise NumericValidationError("distribution.dimension", "expected an integer")
        if self.dimension < 1:
            raise NumericValidationError("distribution.dimension", "dimension must be at least one")
        if len(self.masses) != self.dimension:
            raise NumericValidationError(
                "distribution.masses",
                f"expected {self.dimension} masses, found {len(self.masses)}",
            )
        for index, mass in enumerate(self.masses):
            if not isinstance(mass, Rational):
                raise NumericValidationError(
                    f"distribution.masses[{index}]", "expected an exact Rational"
                )
            if not mass.is_nonnegative():
                raise NumericValidationError(
                    f"distribution.masses[{index}]", "probability mass must be nonnegative"
                )
        total = rational_sum(self.masses)
        if total != Rational.one():
            raise NumericValidationError(
                "distribution.masses", f"exact mass sum must be 1, found {total}"
            )

    @classmethod
    def from_masses(cls, masses: Sequence[Rational]) -> DistributionRecord:
        mass_tuple = tuple(masses)
        return cls(mass_tuple, len(mass_tuple))

    @classmethod
    def from_json(cls, value: object, path: str = "distribution") -> DistributionRecord:
        if not isinstance(value, Mapping):
            raise SchemaValidationError(path, "expected an object")
        expected = {"schema_id", "dimension", "masses"}
        keys = set(value.keys())
        if keys != expected:
            missing = sorted(expected - keys)
            unknown = sorted(keys - expected)
            parts: list[str] = []
            if missing:
                parts.append(f"missing fields: {', '.join(missing)}")
            if unknown:
                parts.append(f"unknown fields: {', '.join(str(item) for item in unknown)}")
            raise SchemaValidationError(path, "; ".join(parts))
        if value["schema_id"] != cls.schema_id:
            raise SchemaValidationError(f"{path}.schema_id", "unexpected schema identifier")
        dimension = value["dimension"]
        if isinstance(dimension, bool) or not isinstance(dimension, int):
            raise SchemaValidationError(f"{path}.dimension", "expected an integer")
        masses_raw = value["masses"]
        if not isinstance(masses_raw, list):
            raise SchemaValidationError(f"{path}.masses", "expected an array")
        masses = tuple(
            Rational.from_json(item, f"{path}.masses[{index}]")
            for index, item in enumerate(masses_raw)
        )
        return cls(masses, dimension)

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "dimension": self.dimension,
            "masses": [mass.to_json() for mass in self.masses],
        }


@dataclass(frozen=True, slots=True)
class ZeroExtensionRecord:
    distribution: DistributionRecord

    schema_id: ClassVar[str] = ZERO_EXTENSION_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.distribution.masses[0] != Rational.zero():
            raise NumericValidationError(
                "zero_extension.distribution.masses[0]",
                "conservative extension head coordinate must be exactly zero",
            )

    @property
    def original_dimension(self) -> int:
        return self.distribution.dimension - 1

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "distribution": self.distribution.to_json(),
        }


def supported_by(source: DistributionRecord, target: DistributionRecord) -> bool:
    _require_same_dimension(source, target)
    for source_mass, target_mass in zip(source.masses, target.masses, strict=True):
        if source_mass.is_positive() and not target_mass.is_positive():
            return False
    return True


def require_supported_by(
    source: DistributionRecord,
    target: DistributionRecord,
    path: str = "distribution_support",
) -> None:
    if not supported_by(source, target):
        raise NumericValidationError(
            path,
            "positive source mass requires positive target mass at every coordinate",
        )


def extend_by_zero(distribution: DistributionRecord) -> ZeroExtensionRecord:
    extended = DistributionRecord(
        (Rational.zero(),) + distribution.masses,
        distribution.dimension + 1,
    )
    return ZeroExtensionRecord(extended)


def recover_zero_extension(extension: ZeroExtensionRecord) -> DistributionRecord:
    if extension.distribution.dimension < 2:
        raise NumericValidationError(
            "zero_extension.dimension", "recovery requires an extended distribution"
        )
    return DistributionRecord(
        extension.distribution.masses[1:],
        extension.distribution.dimension - 1,
    )


def shannon_entropy_interval(
    distribution: DistributionRecord,
    precision_bits: int = DEFAULT_PRECISION_BITS,
) -> IntervalEvidence:
    terms: list[IntervalEvidence] = []
    for mass in distribution.masses:
        if mass.is_zero():
            terms.append(IntervalEvidence.exact(Rational.zero(), precision_bits))
        else:
            log_mass = log_rational_interval(mass, precision_bits)
            terms.append(-(log_mass * mass))
    return sum_intervals(terms, precision_bits)


def kl_divergence_interval(
    source: DistributionRecord,
    target: DistributionRecord,
    precision_bits: int = DEFAULT_PRECISION_BITS,
) -> IntervalEvidence:
    _require_same_dimension(source, target)
    require_supported_by(source, target)
    terms: list[IntervalEvidence] = []
    for source_mass, target_mass in zip(source.masses, target.masses, strict=True):
        if source_mass.is_zero():
            terms.append(IntervalEvidence.exact(Rational.zero(), precision_bits))
        else:
            ratio = source_mass / target_mass
            terms.append(log_rational_interval(ratio, precision_bits) * source_mass)
    return sum_intervals(terms, precision_bits)


def _require_same_dimension(
    first: DistributionRecord,
    second: DistributionRecord,
) -> None:
    if first.dimension != second.dimension:
        raise NumericValidationError(
            "distribution.dimension",
            f"dimension mismatch: {first.dimension} versus {second.dimension}",
        )


UNIFORM_BINARY: Final[DistributionRecord] = DistributionRecord(
    (Rational(1, 2), Rational(1, 2)),
    2,
)
BIASED_BINARY: Final[DistributionRecord] = DistributionRecord(
    (Rational(3, 4), Rational(1, 4)),
    2,
)
SOURCE_BINARY: Final[DistributionRecord] = DistributionRecord(
    (Rational(1, 4), Rational(3, 4)),
    2,
)


def binary_state_distribution(state: str) -> DistributionRecord:
    if state == "outside":
        return UNIFORM_BINARY
    if state == "initial":
        return UNIFORM_BINARY
    if state == "target":
        return BIASED_BINARY
    raise NumericValidationError("binary_state", f"unknown binary state: {state}")


def apply_binary_update(state: str, update: str) -> str:
    if state not in {"outside", "initial", "target"}:
        raise NumericValidationError("binary_state", f"unknown binary state: {state}")
    if update not in {"stay", "improve"}:
        raise NumericValidationError("binary_update", f"unknown binary update: {update}")
    if state == "outside":
        return "outside"
    if state == "initial" and update == "improve":
        return "target"
    return state
