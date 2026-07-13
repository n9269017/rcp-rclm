from __future__ import annotations

import unittest
from decimal import Decimal, localcontext

from rcp_rclm_runtime.errors import NumericValidationError
from rcp_rclm_runtime.mathematics.intervals import (
    MAX_PRECISION_BITS,
    MIN_PRECISION_BITS,
    IntervalEvidence,
    log_rational_interval,
)
from rcp_rclm_runtime.mathematics.rational import Rational


def decimal_value(value: Rational) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


class IntervalTests(unittest.TestCase):
    def test_exact_interval_and_predicates(self) -> None:
        interval = IntervalEvidence.exact(Rational(3, 5), 256)
        self.assertEqual(interval.lower, Rational(3, 5))
        self.assertEqual(interval.upper, Rational(3, 5))
        self.assertEqual(interval.width, Rational.zero())
        self.assertTrue(interval.strictly_positive())
        self.assertFalse(interval.contains_zero())

    def test_invalid_interval_bounds_and_precision_are_rejected(self) -> None:
        with self.assertRaises(NumericValidationError):
            IntervalEvidence(Rational(2), Rational(1), 256)
        with self.assertRaises(NumericValidationError):
            IntervalEvidence(Rational.zero(), Rational.one(), MIN_PRECISION_BITS - 1)
        with self.assertRaises(NumericValidationError):
            IntervalEvidence(Rational.zero(), Rational.one(), MAX_PRECISION_BITS + 1)

    def test_interval_arithmetic_is_outward_safe(self) -> None:
        left = IntervalEvidence(Rational(1), Rational(2), 256)
        right = IntervalEvidence(Rational(-3), Rational(4), 512)
        self.assertEqual((left + right).lower, Rational(-2))
        self.assertEqual((left + right).upper, Rational(6))
        product = left * right
        self.assertEqual(product.lower, Rational(-6))
        self.assertEqual(product.upper, Rational(8))
        self.assertEqual(product.precision_bits, 256)

    def test_log_one_is_exact_zero(self) -> None:
        interval = log_rational_interval(Rational.one(), 256)
        self.assertEqual(interval, IntervalEvidence.exact(Rational.zero(), 256))

    def test_log_two_contains_high_precision_decimal_reference(self) -> None:
        interval = log_rational_interval(Rational(2), 256)
        with localcontext() as context:
            context.prec = 100
            reference = Decimal(2).ln()
            self.assertLessEqual(decimal_value(interval.lower), reference)
            self.assertGreaterEqual(decimal_value(interval.upper), reference)

    def test_log_interval_meets_frozen_width_budget(self) -> None:
        interval = log_rational_interval(Rational(7, 5), 256)
        self.assertLessEqual(interval.width, Rational(1, 1 << 264))

    def test_log_rejects_nonpositive_inputs_and_bad_precision(self) -> None:
        with self.assertRaises(NumericValidationError):
            log_rational_interval(Rational.zero(), 256)
        with self.assertRaises(NumericValidationError):
            log_rational_interval(Rational(-1), 256)
        with self.assertRaises(NumericValidationError):
            log_rational_interval(Rational(2), 64)


if __name__ == "__main__":
    unittest.main()
