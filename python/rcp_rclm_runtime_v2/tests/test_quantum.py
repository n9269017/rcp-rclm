from __future__ import annotations

import unittest

from rcp_rclm_runtime.errors import NumericValidationError
from rcp_rclm_runtime.mathematics.classical import kl_divergence_interval
from rcp_rclm_runtime.mathematics.diagonal_quantum import (
    SOURCE_DENSITY,
    TARGET_DENSITY,
    UNIFORM_DENSITY,
    ComplexRational,
    DiagonalDensityRecord,
    SelectedChannelRecord,
    apply_quantum_update,
    apply_selected_channel,
    quantum_relative_entropy_interval,
    recover_selected_channel,
    validate_dense_export,
    von_neumann_entropy_interval,
)
from rcp_rclm_runtime.mathematics.rational import Rational


class QuantumMathematicsTests(unittest.TestCase):
    def test_density_evidence_is_exact(self) -> None:
        evidence = SOURCE_DENSITY.evidence()
        self.assertEqual(evidence.dimension, 2)
        self.assertTrue(evidence.hermitian)
        self.assertTrue(evidence.positive_semidefinite)
        self.assertTrue(evidence.trace_one)
        self.assertTrue(evidence.diagonal)
        self.assertEqual(evidence.trace, Rational.one())

    def test_dense_matrix_is_derived_from_spectrum(self) -> None:
        matrix = SOURCE_DENSITY.dense_matrix()
        self.assertEqual(matrix[0][0], ComplexRational(Rational(1, 4)))
        self.assertEqual(matrix[1][1], ComplexRational(Rational(3, 4)))
        self.assertEqual(matrix[0][1], ComplexRational(Rational.zero()))
        self.assertTrue(validate_dense_export(SOURCE_DENSITY, matrix).trace_one)

    def test_dense_matrix_mismatch_is_rejected(self) -> None:
        bad = (
            (ComplexRational(Rational(1, 4)), ComplexRational(Rational(1, 100))),
            (ComplexRational(Rational.zero()), ComplexRational(Rational(3, 4))),
        )
        with self.assertRaises(NumericValidationError):
            validate_dense_export(SOURCE_DENSITY, bad)

    def test_identity_channel_is_exact(self) -> None:
        identity = SelectedChannelRecord.identity()
        self.assertEqual(apply_selected_channel(identity, SOURCE_DENSITY), SOURCE_DENSITY)
        self.assertEqual(identity.inverse(), identity)

    def test_basis_swap_and_recovery_are_exact(self) -> None:
        swap = SelectedChannelRecord.basis_swap()
        after = apply_selected_channel(swap, SOURCE_DENSITY)
        self.assertEqual(after, TARGET_DENSITY)
        self.assertEqual(recover_selected_channel(swap, after), SOURCE_DENSITY)
        self.assertEqual(swap.inverse(), swap)

    def test_selected_channel_rejects_wrong_permutation(self) -> None:
        with self.assertRaises(NumericValidationError):
            SelectedChannelRecord(kind="identity", permutation=(1, 0))
        with self.assertRaises(NumericValidationError):
            SelectedChannelRecord(kind="basis_swap", permutation=(0, 0))

    def test_spectral_entropy_and_qre_share_classical_backend(self) -> None:
        self.assertEqual(
            von_neumann_entropy_interval(UNIFORM_DENSITY, 256),
            von_neumann_entropy_interval(UNIFORM_DENSITY, 256),
        )
        self.assertEqual(
            quantum_relative_entropy_interval(SOURCE_DENSITY, TARGET_DENSITY, 256),
            kl_divergence_interval(SOURCE_DENSITY.spectrum, TARGET_DENSITY.spectrum, 256),
        )

    def test_selected_quantum_state_transition(self) -> None:
        self.assertEqual(apply_quantum_update("source", "swap"), "target")
        self.assertEqual(apply_quantum_update("target", "swap"), "source")
        self.assertEqual(apply_quantum_update("target", "stay"), "target")
        self.assertEqual(apply_quantum_update("outside", "swap"), "outside")

    def test_density_json_round_trip(self) -> None:
        self.assertEqual(
            DiagonalDensityRecord.from_json(SOURCE_DENSITY.to_json()),
            SOURCE_DENSITY,
        )


if __name__ == "__main__":
    unittest.main()
