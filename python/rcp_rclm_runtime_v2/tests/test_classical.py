from __future__ import annotations

import unittest

from rcp_rclm_runtime.errors import NumericValidationError
from rcp_rclm_runtime.mathematics.classical import (
    BIASED_BINARY,
    UNIFORM_BINARY,
    DistributionRecord,
    apply_binary_update,
    extend_by_zero,
    kl_divergence_interval,
    recover_zero_extension,
    shannon_entropy_interval,
    supported_by,
)
from rcp_rclm_runtime.mathematics.intervals import IntervalEvidence, log_rational_interval
from rcp_rclm_runtime.mathematics.rational import Rational


class ClassicalMathematicsTests(unittest.TestCase):
    def test_distribution_requires_exact_normalization(self) -> None:
        valid = DistributionRecord((Rational(1, 3), Rational(2, 3)), 2)
        self.assertEqual(valid.dimension, 2)
        with self.assertRaises(NumericValidationError):
            DistributionRecord((Rational(1, 3), Rational(1, 3)), 2)

    def test_distribution_rejects_negative_mass_and_dimension_mismatch(self) -> None:
        with self.assertRaises(NumericValidationError):
            DistributionRecord((Rational(-1, 2), Rational(3, 2)), 2)
        with self.assertRaises(NumericValidationError):
            DistributionRecord((Rational.one(),), 2)

    def test_distribution_json_is_strict_and_round_trips(self) -> None:
        encoded = UNIFORM_BINARY.to_json()
        self.assertEqual(DistributionRecord.from_json(encoded), UNIFORM_BINARY)
        malformed = dict(encoded)
        malformed["unknown"] = True
        with self.assertRaises(Exception):
            DistributionRecord.from_json(malformed)

    def test_support_is_exact_not_tolerance_based(self) -> None:
        source = DistributionRecord((Rational.one(), Rational.zero()), 2)
        supported_target = DistributionRecord((Rational(1, 2), Rational(1, 2)), 2)
        unsupported_target = DistributionRecord((Rational.zero(), Rational.one()), 2)
        self.assertTrue(supported_by(source, supported_target))
        self.assertFalse(supported_by(source, unsupported_target))

    def test_uniform_entropy_equals_log_two_interval(self) -> None:
        self.assertEqual(
            shannon_entropy_interval(UNIFORM_BINARY, 256),
            log_rational_interval(Rational(2), 256),
        )

    def test_self_kl_is_exact_zero(self) -> None:
        interval = kl_divergence_interval(BIASED_BINARY, BIASED_BINARY, 256)
        self.assertEqual(interval, IntervalEvidence.exact(Rational.zero(), 256))

    def test_uniform_to_biased_kl_is_strictly_positive(self) -> None:
        interval = kl_divergence_interval(UNIFORM_BINARY, BIASED_BINARY, 256)
        self.assertTrue(interval.strictly_positive())

    def test_kl_rejects_support_violation(self) -> None:
        source = DistributionRecord((Rational.one(), Rational.zero()), 2)
        target = DistributionRecord((Rational.zero(), Rational.one()), 2)
        with self.assertRaises(NumericValidationError):
            kl_divergence_interval(source, target, 256)

    def test_zero_extension_has_exact_recovery(self) -> None:
        extension = extend_by_zero(BIASED_BINARY)
        self.assertEqual(extension.distribution.masses[0], Rational.zero())
        self.assertEqual(recover_zero_extension(extension), BIASED_BINARY)

    def test_selected_binary_update_semantics(self) -> None:
        self.assertEqual(apply_binary_update("initial", "improve"), "target")
        self.assertEqual(apply_binary_update("target", "stay"), "target")
        self.assertEqual(apply_binary_update("outside", "improve"), "outside")
        with self.assertRaises(NumericValidationError):
            apply_binary_update("initial", "unknown")


if __name__ == "__main__":
    unittest.main()
