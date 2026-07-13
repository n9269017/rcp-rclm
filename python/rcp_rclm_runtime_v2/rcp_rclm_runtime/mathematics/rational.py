from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import total_ordering
from fractions import Fraction
from collections.abc import Sequence
from typing import Final, Mapping, TypeAlias

from rcp_rclm_runtime.errors import NumericValidationError, SchemaValidationError

_CANONICAL_INTEGER: Final[re.Pattern[str]] = re.compile(r"^(0|-?[1-9][0-9]*)$")
_POSITIVE_INTEGER: Final[re.Pattern[str]] = re.compile(r"^[1-9][0-9]*$")

RationalJson: TypeAlias = dict[str, str]


def parse_canonical_integer(text: object, path: str) -> int:
    if not isinstance(text, str):
        raise SchemaValidationError(path, "expected a canonical decimal string")
    if _CANONICAL_INTEGER.fullmatch(text) is None:
        raise NumericValidationError(path, "integer is not in canonical decimal form")
    return int(text, 10)


def parse_canonical_nonnegative_integer(text: object, path: str) -> int:
    value = parse_canonical_integer(text, path)
    if value < 0:
        raise NumericValidationError(path, "expected a nonnegative integer")
    return value


@total_ordering
@dataclass(frozen=True, slots=True)
class Rational:
    numerator: int
    denominator: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.numerator, bool) or not isinstance(self.numerator, int):
            raise NumericValidationError("numerator", "expected an integer")
        if isinstance(self.denominator, bool) or not isinstance(self.denominator, int):
            raise NumericValidationError("denominator", "expected an integer")
        if self.denominator == 0:
            raise NumericValidationError("denominator", "zero denominator is forbidden")

        numerator = self.numerator
        denominator = self.denominator
        if denominator < 0:
            numerator = -numerator
            denominator = -denominator
        divisor = math.gcd(abs(numerator), denominator)
        numerator //= divisor
        denominator //= divisor
        if numerator == 0:
            denominator = 1

        object.__setattr__(self, "numerator", numerator)
        object.__setattr__(self, "denominator", denominator)

    @classmethod
    def zero(cls) -> Rational:
        return cls(0, 1)

    @classmethod
    def one(cls) -> Rational:
        return cls(1, 1)

    @classmethod
    def from_fraction(cls, value: Fraction) -> Rational:
        return cls(value.numerator, value.denominator)

    @classmethod
    def from_json(cls, value: object, path: str = "rational") -> Rational:
        if not isinstance(value, Mapping):
            raise SchemaValidationError(path, "expected an object")
        keys = set(value.keys())
        if keys != {"numerator", "denominator"}:
            missing = sorted({"numerator", "denominator"} - keys)
            unknown = sorted(keys - {"numerator", "denominator"})
            detail_parts: list[str] = []
            if missing:
                detail_parts.append(f"missing fields: {', '.join(missing)}")
            if unknown:
                detail_parts.append(f"unknown fields: {', '.join(str(item) for item in unknown)}")
            raise SchemaValidationError(path, "; ".join(detail_parts))

        numerator_raw = value["numerator"]
        denominator_raw = value["denominator"]
        numerator = parse_canonical_integer(numerator_raw, f"{path}.numerator")
        if not isinstance(denominator_raw, str) or _POSITIVE_INTEGER.fullmatch(denominator_raw) is None:
            raise NumericValidationError(
                f"{path}.denominator", "denominator must be a canonical positive decimal string"
            )
        denominator = int(denominator_raw, 10)
        if math.gcd(abs(numerator), denominator) != 1:
            raise NumericValidationError(path, "rational must be reduced")
        if numerator == 0 and denominator != 1:
            raise NumericValidationError(path, "zero must be encoded as 0/1")
        return cls(numerator, denominator)

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    def to_json(self) -> RationalJson:
        return {
            "numerator": str(self.numerator),
            "denominator": str(self.denominator),
        }

    def is_zero(self) -> bool:
        return self.numerator == 0

    def is_positive(self) -> bool:
        return self.numerator > 0

    def is_nonnegative(self) -> bool:
        return self.numerator >= 0

    def reciprocal(self) -> Rational:
        if self.numerator == 0:
            raise NumericValidationError("rational", "zero has no reciprocal")
        return Rational(self.denominator, self.numerator)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Rational):
            return (self.numerator, self.denominator) == (other.numerator, other.denominator)
        if isinstance(other, bool):
            return False
        if isinstance(other, int):
            return self.denominator == 1 and self.numerator == other
        return False

    def __lt__(self, other: object) -> bool:
        rhs = _coerce_rational(other)
        return self.numerator * rhs.denominator < rhs.numerator * self.denominator

    def __hash__(self) -> int:
        return hash((self.numerator, self.denominator))

    def __neg__(self) -> Rational:
        return Rational(-self.numerator, self.denominator)

    def __abs__(self) -> Rational:
        return Rational(abs(self.numerator), self.denominator)

    def __add__(self, other: object) -> Rational:
        rhs = _coerce_rational(other)
        return Rational(
            self.numerator * rhs.denominator + rhs.numerator * self.denominator,
            self.denominator * rhs.denominator,
        )

    def __radd__(self, other: object) -> Rational:
        return self.__add__(other)

    def __sub__(self, other: object) -> Rational:
        rhs = _coerce_rational(other)
        return Rational(
            self.numerator * rhs.denominator - rhs.numerator * self.denominator,
            self.denominator * rhs.denominator,
        )

    def __rsub__(self, other: object) -> Rational:
        lhs = _coerce_rational(other)
        return lhs.__sub__(self)

    def __mul__(self, other: object) -> Rational:
        rhs = _coerce_rational(other)
        return Rational(self.numerator * rhs.numerator, self.denominator * rhs.denominator)

    def __rmul__(self, other: object) -> Rational:
        return self.__mul__(other)

    def __truediv__(self, other: object) -> Rational:
        rhs = _coerce_rational(other)
        if rhs.numerator == 0:
            raise NumericValidationError("rational", "division by zero")
        return Rational(self.numerator * rhs.denominator, self.denominator * rhs.numerator)

    def __rtruediv__(self, other: object) -> Rational:
        lhs = _coerce_rational(other)
        return lhs.__truediv__(self)

    def __pow__(self, exponent: int) -> Rational:
        if isinstance(exponent, bool) or not isinstance(exponent, int):
            raise TypeError("rational exponent must be an integer")
        if exponent == 0:
            return Rational.one()
        if exponent < 0:
            return self.reciprocal().__pow__(-exponent)
        return Rational(self.numerator**exponent, self.denominator**exponent)

    def __float__(self) -> float:
        raise TypeError("native float conversion is forbidden for authoritative runtime values")

    def __str__(self) -> str:
        if self.denominator == 1:
            return str(self.numerator)
        return f"{self.numerator}/{self.denominator}"


def _coerce_rational(value: object) -> Rational:
    if isinstance(value, Rational):
        return value
    if isinstance(value, bool):
        raise TypeError("boolean is not a rational operand")
    if isinstance(value, int):
        return Rational(value, 1)
    raise TypeError(f"unsupported rational operand: {type(value).__name__}")


def rational_sum(values: Sequence[Rational]) -> Rational:
    total = Rational.zero()
    for value in values:
        total = total + value
    return total


def power_of_two(exponent: int) -> Rational:
    if exponent >= 0:
        return Rational(1 << exponent, 1)
    return Rational(1, 1 << (-exponent))
