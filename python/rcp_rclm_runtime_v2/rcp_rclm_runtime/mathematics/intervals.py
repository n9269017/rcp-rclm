from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from typing import Final, Iterable, Mapping

from rcp_rclm_runtime._version import NUMERIC_BACKEND_ID
from rcp_rclm_runtime.errors import NumericValidationError, SchemaValidationError
from rcp_rclm_runtime.mathematics.rational import Rational, power_of_two

MIN_PRECISION_BITS: Final[int] = 128
MAX_PRECISION_BITS: Final[int] = 4096
DEFAULT_PRECISION_BITS: Final[int] = 256
PRECISION_SCHEDULE: Final[Sequence[int]] = (256, 512, 1024, 2048, 4096)


@dataclass(frozen=True, slots=True)
class IntervalEvidence:
    lower: Rational
    upper: Rational
    precision_bits: int = DEFAULT_PRECISION_BITS

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise NumericValidationError("interval", "lower endpoint exceeds upper endpoint")
        if isinstance(self.precision_bits, bool) or not isinstance(self.precision_bits, int):
            raise NumericValidationError("interval.precision_bits", "expected an integer")
        if not MIN_PRECISION_BITS <= self.precision_bits <= MAX_PRECISION_BITS:
            raise NumericValidationError(
                "interval.precision_bits",
                f"expected {MIN_PRECISION_BITS} through {MAX_PRECISION_BITS}",
            )

    @classmethod
    def exact(
        cls,
        value: Rational | int,
        precision_bits: int = DEFAULT_PRECISION_BITS,
    ) -> IntervalEvidence:
        rational = value if isinstance(value, Rational) else Rational(value)
        return cls(rational, rational, precision_bits)

    @classmethod
    def from_json(cls, value: object, path: str = "interval") -> IntervalEvidence:
        if not isinstance(value, Mapping):
            raise SchemaValidationError(path, "expected an object")
        expected = {"lower", "upper", "precision_bits"}
        keys = set(value.keys())
        if keys != expected:
            missing = sorted(expected - keys)
            unknown = sorted(keys - expected)
            detail: list[str] = []
            if missing:
                detail.append(f"missing fields: {', '.join(missing)}")
            if unknown:
                detail.append(f"unknown fields: {', '.join(str(item) for item in unknown)}")
            raise SchemaValidationError(path, "; ".join(detail))
        precision_bits = value["precision_bits"]
        if isinstance(precision_bits, bool) or not isinstance(precision_bits, int):
            raise SchemaValidationError(f"{path}.precision_bits", "expected an integer")
        return cls(
            Rational.from_json(value["lower"], f"{path}.lower"),
            Rational.from_json(value["upper"], f"{path}.upper"),
            precision_bits,
        )

    @property
    def backend_id(self) -> str:
        return NUMERIC_BACKEND_ID

    @property
    def width(self) -> Rational:
        return self.upper - self.lower

    def to_json(self) -> dict[str, object]:
        return {
            "lower": self.lower.to_json(),
            "upper": self.upper.to_json(),
            "precision_bits": self.precision_bits,
        }

    def contains(self, value: Rational | int) -> bool:
        rational = value if isinstance(value, Rational) else Rational(value)
        return self.lower <= rational <= self.upper

    def contains_zero(self) -> bool:
        return self.contains(Rational.zero())

    def strictly_positive(self) -> bool:
        return self.lower > Rational.zero()

    def nonnegative(self) -> bool:
        return self.lower >= Rational.zero()

    def upper_nonpositive(self) -> bool:
        return self.upper <= Rational.zero()

    def __neg__(self) -> IntervalEvidence:
        return IntervalEvidence(-self.upper, -self.lower, self.precision_bits)

    def __add__(self, other: IntervalEvidence | Rational | int) -> IntervalEvidence:
        rhs = _coerce_interval(other, self.precision_bits)
        return IntervalEvidence(
            self.lower + rhs.lower,
            self.upper + rhs.upper,
            min(self.precision_bits, rhs.precision_bits),
        )

    def __radd__(self, other: IntervalEvidence | Rational | int) -> IntervalEvidence:
        return self.__add__(other)

    def __sub__(self, other: IntervalEvidence | Rational | int) -> IntervalEvidence:
        rhs = _coerce_interval(other, self.precision_bits)
        return self + (-rhs)

    def __rsub__(self, other: IntervalEvidence | Rational | int) -> IntervalEvidence:
        lhs = _coerce_interval(other, self.precision_bits)
        return lhs - self

    def __mul__(self, other: IntervalEvidence | Rational | int) -> IntervalEvidence:
        rhs = _coerce_interval(other, self.precision_bits)
        products = (
            self.lower * rhs.lower,
            self.lower * rhs.upper,
            self.upper * rhs.lower,
            self.upper * rhs.upper,
        )
        return IntervalEvidence(
            min(products),
            max(products),
            min(self.precision_bits, rhs.precision_bits),
        )

    def __rmul__(self, other: IntervalEvidence | Rational | int) -> IntervalEvidence:
        return self.__mul__(other)


def _coerce_interval(
    value: IntervalEvidence | Rational | int,
    precision_bits: int,
) -> IntervalEvidence:
    if isinstance(value, IntervalEvidence):
        return value
    if isinstance(value, Rational):
        return IntervalEvidence.exact(value, precision_bits)
    if isinstance(value, bool):
        raise TypeError("boolean is not an interval operand")
    if isinstance(value, int):
        return IntervalEvidence.exact(Rational(value), precision_bits)
    raise TypeError(f"unsupported interval operand: {type(value).__name__}")


def sum_intervals(
    values: Iterable[IntervalEvidence],
    precision_bits: int = DEFAULT_PRECISION_BITS,
) -> IntervalEvidence:
    total = IntervalEvidence.exact(Rational.zero(), precision_bits)
    for value in values:
        total = total + value
    return total


def _floor_log2(value: Rational) -> int:
    if not value.is_positive():
        raise NumericValidationError("log.input", "logarithm input must be positive")
    numerator = value.numerator
    denominator = value.denominator
    estimate = numerator.bit_length() - denominator.bit_length()
    while value < power_of_two(estimate):
        estimate -= 1
    while value >= power_of_two(estimate + 1):
        estimate += 1
    return estimate


def _log_unit_interval(
    value: Rational,
    precision_bits: int,
    width_budget: Rational,
) -> IntervalEvidence:
    if value < Rational.one() or value > Rational(2):
        raise NumericValidationError("log.range", "series input must satisfy 1 <= x <= 2")
    if value == Rational.one():
        return IntervalEvidence.exact(Rational.zero(), precision_bits)

    z = (value - Rational.one()) / (value + Rational.one())
    z_squared = z * z
    one_minus_z_squared = Rational.one() - z_squared
    partial = Rational.zero()
    power = z
    index = 0

    while True:
        denominator = 2 * index + 1
        partial = partial + power / Rational(denominator)
        next_index = index + 1
        next_power = power * z_squared
        next_denominator = 2 * next_index + 1
        remainder = next_power / (Rational(next_denominator) * one_minus_z_squared)
        width = Rational(2) * remainder
        if width <= width_budget:
            lower = Rational(2) * partial
            upper = Rational(2) * (partial + remainder)
            return IntervalEvidence(lower, upper, precision_bits)
        power = next_power
        index = next_index


def log_rational_interval(
    value: Rational,
    precision_bits: int = DEFAULT_PRECISION_BITS,
) -> IntervalEvidence:
    if not MIN_PRECISION_BITS <= precision_bits <= MAX_PRECISION_BITS:
        raise NumericValidationError(
            "log.precision_bits",
            f"expected {MIN_PRECISION_BITS} through {MAX_PRECISION_BITS}",
        )
    if not value.is_positive():
        raise NumericValidationError("log.input", "logarithm input must be positive")
    if value == Rational.one():
        return IntervalEvidence.exact(Rational.zero(), precision_bits)

    exponent = _floor_log2(value)
    reduced = value / power_of_two(exponent)
    components = abs(exponent) + 1
    target_width = Rational(1, 1 << (precision_bits + 8))
    component_budget = target_width / Rational(components)

    reduced_log = _log_unit_interval(reduced, precision_bits, component_budget)
    log_two = _log_unit_interval(Rational(2), precision_bits, component_budget)
    scaled_log_two = log_two * Rational(exponent)
    result = reduced_log + scaled_log_two

    if result.width > target_width:
        raise NumericValidationError(
            "log.interval",
            "internal enclosure width exceeded the certified target",
        )
    return result
