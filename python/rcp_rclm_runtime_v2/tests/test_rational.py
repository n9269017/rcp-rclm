from __future__ import annotations

import unittest

from rcp_rclm_runtime.errors import NumericValidationError
from rcp_rclm_runtime.mathematics.rational import (
    Rational,
    parse_canonical_integer,
    parse_canonical_nonnegative_integer,
    power_of_two,
    rational_sum,
)


class RationalTests(unittest.TestCase):
    def test_reduction_and_sign_normalization(self) -> None:
        self.assertEqual(Rational(6, -8), Rational(-3, 4))
        self.assertEqual(Rational(-6, -8), Rational(3, 4))

    def test_zero_has_unique_representation(self) -> None:
        value = Rational(0, 99)
        self.assertEqual(value.to_json(), {"numerator": "0", "denominator": "1"})

    def test_json_round_trip(self) -> None:
        value = Rational.from_json({"numerator": "-7", "denominator": "9"})
        self.assertEqual(value, Rational(-7, 9))
        self.assertEqual(Rational.from_json(value.to_json()), value)

    def test_noncanonical_rational_json_is_rejected(self) -> None:
        with self.assertRaises(NumericValidationError):
            Rational.from_json({"numerator": "2", "denominator": "4"})
        with self.assertRaises(NumericValidationError):
            Rational.from_json({"numerator": "0", "denominator": "2"})
        with self.assertRaises(NumericValidationError):
            Rational.from_json({"numerator": "01", "denominator": "2"})

    def test_arithmetic_is_exact(self) -> None:
        left = Rational(2, 3)
        right = Rational(5, 7)
        self.assertEqual(left + right, Rational(29, 21))
        self.assertEqual(left - right, Rational(-1, 21))
        self.assertEqual(left * right, Rational(10, 21))
        self.assertEqual(left / right, Rational(14, 15))

    def test_integer_coercion_and_ordering(self) -> None:
        self.assertEqual(Rational(3, 2) + 2, Rational(7, 2))
        self.assertEqual(2 - Rational(3, 2), Rational(1, 2))
        self.assertTrue(Rational(3, 2) > 1)
        self.assertTrue(Rational(-1, 3) < 0)

    def test_power_reciprocal_and_sum(self) -> None:
        self.assertEqual(Rational(2, 3) ** -2, Rational(9, 4))
        self.assertEqual(power_of_two(-3), Rational(1, 8))
        self.assertEqual(rational_sum((Rational(1, 6), Rational(1, 3), Rational(1, 2))), 1)

    def test_zero_reciprocal_and_float_conversion_are_rejected(self) -> None:
        with self.assertRaises(NumericValidationError):
            Rational.zero().reciprocal()
        with self.assertRaises(TypeError):
            float(Rational(1, 3))

    def test_canonical_integer_parsing(self) -> None:
        self.assertEqual(parse_canonical_integer("-17", "value"), -17)
        self.assertEqual(parse_canonical_nonnegative_integer("17", "value"), 17)
        with self.assertRaises(NumericValidationError):
            parse_canonical_integer("+1", "value")
        with self.assertRaises(NumericValidationError):
            parse_canonical_integer("-0", "value")
        with self.assertRaises(NumericValidationError):
            parse_canonical_nonnegative_integer("-1", "value")


if __name__ == "__main__":
    unittest.main()
