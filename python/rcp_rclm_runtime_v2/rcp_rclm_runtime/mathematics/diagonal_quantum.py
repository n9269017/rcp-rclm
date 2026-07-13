from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Final, Mapping, Sequence, TypeAlias

from rcp_rclm_runtime.errors import NumericValidationError, SchemaValidationError, UnsupportedScopeError
from rcp_rclm_runtime.mathematics.classical import (
    BIASED_BINARY,
    SOURCE_BINARY,
    UNIFORM_BINARY,
    DistributionRecord,
    kl_divergence_interval,
    shannon_entropy_interval,
)
from rcp_rclm_runtime.mathematics.intervals import DEFAULT_PRECISION_BITS, IntervalEvidence
from rcp_rclm_runtime.mathematics.rational import Rational, rational_sum

DIAGONAL_DENSITY_SCHEMA_ID: Final[str] = "gate_c.diagonal_density.v2"
SELECTED_CHANNEL_SCHEMA_ID: Final[str] = "gate_c.selected_channel.v2"
SELECTED_DIMENSION: Final[int] = 2


@dataclass(frozen=True, slots=True)
class ComplexRational:
    real: Rational
    imaginary: Rational = Rational(0)

    def conjugate(self) -> ComplexRational:
        return ComplexRational(self.real, -self.imaginary)

    def is_real(self) -> bool:
        return self.imaginary.is_zero()

    def to_json(self) -> dict[str, object]:
        return {
            "real": self.real.to_json(),
            "imaginary": self.imaginary.to_json(),
        }


DenseComplexMatrix: TypeAlias = Sequence[Sequence[ComplexRational]]


@dataclass(frozen=True, slots=True)
class DensityMatrixEvidence:
    dimension: int
    hermitian: bool
    positive_semidefinite: bool
    trace: Rational
    trace_one: bool
    diagonal: bool

    def to_json(self) -> dict[str, object]:
        return {
            "dimension": self.dimension,
            "hermitian": self.hermitian,
            "positive_semidefinite": self.positive_semidefinite,
            "trace": self.trace.to_json(),
            "trace_one": self.trace_one,
            "diagonal": self.diagonal,
        }


@dataclass(frozen=True, slots=True)
class DiagonalDensityRecord:
    spectrum: DistributionRecord
    dimension: int = SELECTED_DIMENSION

    schema_id: ClassVar[str] = DIAGONAL_DENSITY_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.dimension != SELECTED_DIMENSION:
            raise UnsupportedScopeError(
                "diagonal_density.dimension",
                f"selected Gate C runtime supports dimension {SELECTED_DIMENSION} only",
            )
        if self.spectrum.dimension != self.dimension:
            raise NumericValidationError(
                "diagonal_density.spectrum.dimension",
                "spectrum dimension must match density dimension",
            )

    @classmethod
    def from_json(cls, value: object, path: str = "diagonal_density") -> DiagonalDensityRecord:
        if not isinstance(value, Mapping):
            raise SchemaValidationError(path, "expected an object")
        expected = {"schema_id", "dimension", "spectrum"}
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
        spectrum = DistributionRecord.from_json(value["spectrum"], f"{path}.spectrum")
        return cls(spectrum=spectrum, dimension=dimension)

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "dimension": self.dimension,
            "spectrum": self.spectrum.to_json(),
        }

    def dense_matrix(self) -> DenseComplexMatrix:
        zero = ComplexRational(Rational.zero())
        rows: list[Sequence[ComplexRational]] = []
        for row_index in range(self.dimension):
            row: list[ComplexRational] = []
            for column_index in range(self.dimension):
                if row_index == column_index:
                    row.append(ComplexRational(self.spectrum.masses[row_index]))
                else:
                    row.append(zero)
            rows.append(tuple(row))
        return tuple(rows)

    def evidence(self) -> DensityMatrixEvidence:
        trace = rational_sum(self.spectrum.masses)
        positive = all(mass.is_nonnegative() for mass in self.spectrum.masses)
        return DensityMatrixEvidence(
            dimension=self.dimension,
            hermitian=True,
            positive_semidefinite=positive,
            trace=trace,
            trace_one=trace == Rational.one(),
            diagonal=True,
        )


@dataclass(frozen=True, slots=True)
class SelectedChannelRecord:
    kind: str
    permutation: Sequence[int]
    dimension: int = SELECTED_DIMENSION

    schema_id: ClassVar[str] = SELECTED_CHANNEL_SCHEMA_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "permutation", tuple(self.permutation))
        if self.dimension != SELECTED_DIMENSION:
            raise UnsupportedScopeError(
                "selected_channel.dimension",
                f"selected Gate C runtime supports dimension {SELECTED_DIMENSION} only",
            )
        if self.kind not in {"identity", "basis_swap"}:
            raise UnsupportedScopeError(
                "selected_channel.kind", f"unsupported selected channel kind: {self.kind}"
            )
        if len(self.permutation) != self.dimension:
            raise NumericValidationError(
                "selected_channel.permutation", "permutation length must match dimension"
            )
        if any(isinstance(index, bool) or not isinstance(index, int) for index in self.permutation):
            raise NumericValidationError(
                "selected_channel.permutation", "permutation indices must be integers"
            )
        if set(self.permutation) != set(range(self.dimension)):
            raise NumericValidationError(
                "selected_channel.permutation", "permutation must be a bijection"
            )
        expected = (0, 1) if self.kind == "identity" else (1, 0)
        if self.permutation != expected:
            raise NumericValidationError(
                "selected_channel.permutation",
                f"{self.kind} requires permutation {expected}",
            )

    @classmethod
    def identity(cls) -> SelectedChannelRecord:
        return cls(kind="identity", permutation=(0, 1))

    @classmethod
    def basis_swap(cls) -> SelectedChannelRecord:
        return cls(kind="basis_swap", permutation=(1, 0))

    @classmethod
    def from_json(cls, value: object, path: str = "selected_channel") -> SelectedChannelRecord:
        if not isinstance(value, Mapping):
            raise SchemaValidationError(path, "expected an object")
        expected = {"schema_id", "dimension", "kind", "permutation"}
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
        kind = value["kind"]
        if not isinstance(kind, str):
            raise SchemaValidationError(f"{path}.kind", "expected a string")
        permutation_raw = value["permutation"]
        if not isinstance(permutation_raw, list):
            raise SchemaValidationError(f"{path}.permutation", "expected an array")
        permutation: list[int] = []
        for index, item in enumerate(permutation_raw):
            if isinstance(item, bool) or not isinstance(item, int):
                raise SchemaValidationError(
                    f"{path}.permutation[{index}]", "expected an integer"
                )
            permutation.append(item)
        return cls(kind=kind, permutation=tuple(permutation), dimension=dimension)

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "dimension": self.dimension,
            "kind": self.kind,
            "permutation": list(self.permutation),
        }

    def inverse(self) -> SelectedChannelRecord:
        inverse_values = [0] * self.dimension
        for target_index, source_index in enumerate(self.permutation):
            inverse_values[source_index] = target_index
        return SelectedChannelRecord(
            kind=self.kind,
            permutation=tuple(inverse_values),
            dimension=self.dimension,
        )


DiagonalChannelRecord = SelectedChannelRecord


def validate_dense_export(
    density: DiagonalDensityRecord,
    matrix: Sequence[Sequence[ComplexRational]],
) -> DensityMatrixEvidence:
    if len(matrix) != density.dimension:
        raise NumericValidationError("dense_matrix", "row count does not match density dimension")
    normalized_rows: list[Sequence[ComplexRational]] = []
    for row_index, row in enumerate(matrix):
        if len(row) != density.dimension:
            raise NumericValidationError(
                f"dense_matrix[{row_index}]", "column count does not match density dimension"
            )
        normalized_row: list[ComplexRational] = []
        for column_index, entry in enumerate(row):
            if not isinstance(entry, ComplexRational):
                raise NumericValidationError(
                    f"dense_matrix[{row_index}][{column_index}]",
                    "entry must use exact ComplexRational representation",
                )
            normalized_row.append(entry)
        normalized_rows.append(tuple(normalized_row))
    normalized = tuple(normalized_rows)
    expected = density.dense_matrix()
    if normalized != expected:
        raise NumericValidationError(
            "dense_matrix",
            "candidate dense matrix differs from the spectrum-derived diagonal matrix",
        )
    return density.evidence()


def apply_selected_channel(
    channel: SelectedChannelRecord,
    density: DiagonalDensityRecord,
) -> DiagonalDensityRecord:
    if channel.dimension != density.dimension:
        raise NumericValidationError(
            "selected_channel.dimension", "channel and density dimensions differ"
        )
    masses = tuple(density.spectrum.masses[source_index] for source_index in channel.permutation)
    return DiagonalDensityRecord(DistributionRecord(masses, density.dimension), density.dimension)


def recover_selected_channel(
    channel: SelectedChannelRecord,
    density_after_channel: DiagonalDensityRecord,
) -> DiagonalDensityRecord:
    return apply_selected_channel(channel.inverse(), density_after_channel)


def von_neumann_entropy_interval(
    density: DiagonalDensityRecord,
    precision_bits: int = DEFAULT_PRECISION_BITS,
) -> IntervalEvidence:
    return shannon_entropy_interval(density.spectrum, precision_bits)


def quantum_relative_entropy_interval(
    source: DiagonalDensityRecord,
    target: DiagonalDensityRecord,
    precision_bits: int = DEFAULT_PRECISION_BITS,
) -> IntervalEvidence:
    return kl_divergence_interval(source.spectrum, target.spectrum, precision_bits)


UNIFORM_DENSITY: Final[DiagonalDensityRecord] = DiagonalDensityRecord(UNIFORM_BINARY)
SOURCE_DENSITY: Final[DiagonalDensityRecord] = DiagonalDensityRecord(SOURCE_BINARY)
TARGET_DENSITY: Final[DiagonalDensityRecord] = DiagonalDensityRecord(BIASED_BINARY)


def quantum_state_density(state: str) -> DiagonalDensityRecord:
    if state == "outside":
        return UNIFORM_DENSITY
    if state == "source":
        return SOURCE_DENSITY
    if state == "target":
        return TARGET_DENSITY
    raise NumericValidationError("quantum_state", f"unknown selected quantum state: {state}")


def apply_quantum_update(state: str, update: str) -> str:
    if state not in {"outside", "source", "target"}:
        raise NumericValidationError("quantum_state", f"unknown selected quantum state: {state}")
    if update not in {"stay", "swap"}:
        raise NumericValidationError("quantum_update", f"unknown selected quantum update: {update}")
    if state == "outside":
        return "outside"
    if update == "stay":
        return state
    if state == "source":
        return "target"
    return "source"
