from __future__ import annotations

import unittest

from rcp_rclm_runtime.canonical.hashing import sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_text
from rcp_rclm_runtime.lean_bridge.compiler import (
    LeanCompilationResult,
    LeanToolchainRuntimeIdentity,
)
from rcp_rclm_runtime.lean_bridge.packet import reference_packets
from rcp_rclm_runtime.lean_bridge.source_generator import (
    LEAN_VERDICT_MARKER_PREFIX,
    LEAN_VERDICT_SCHEMA_ID,
    SOURCE_GENERATOR_VERSION,
    generate_reference_source,
)
from rcp_rclm_runtime.lean_bridge.verifier import LeanReferenceVerifier


class _FakeProject:
    pin_hash = "c" * 64


class _FakeCompiler:
    project = _FakeProject()

    def __init__(
        self,
        *,
        force_rcp_acceptance: bool | None = None,
        force_rclm_acceptance: bool | None = None,
    ) -> None:
        self.force_rcp_acceptance = force_rcp_acceptance
        self.force_rclm_acceptance = force_rclm_acceptance

    def compile_source(
        self,
        source: bytes,
        *,
        source_name: str = "generated/reference.lean",
    ) -> LeanCompilationResult:
        packet = reference_packets()[0]
        generated = generate_reference_source(packet)
        rcp_accepted = (
            generated.expected_acceptance
            if self.force_rcp_acceptance is None
            else self.force_rcp_acceptance
        )
        rclm_accepted = (
            generated.expected_acceptance
            if self.force_rclm_acceptance is None
            else self.force_rclm_acceptance
        )
        payload = canonical_json_text(
            {
                "schema_id": LEAN_VERDICT_SCHEMA_ID,
                "case_id": packet.case_id,
                "scope": packet.scope,
                "rcp_accepted": rcp_accepted,
                "rclm_accepted": rclm_accepted,
                "packet_hash": packet.packet_hash,
                "theorem_surface_hash": generated.theorem_surface_hash,
                "source_generator_version": SOURCE_GENERATOR_VERSION,
            }
        )
        stdout = (LEAN_VERDICT_MARKER_PREFIX + payload + "\n").encode("utf-8")
        identity = LeanToolchainRuntimeIdentity(
            lake_command="lake",
            lean_version="Lean (version 4.31.0, test)",
            lake_version="Lake version 5.0.0 (Lean version 4.31.0)",
            lean_prefix="/lean/prefix",
            platform="posix",
            environment_path_hash="a" * 64,
            runtime_hash="b" * 64,
        )
        return LeanCompilationResult(
            command=("lake", "env", "lean", "generated.lean"),
            source_name=source_name,
            exit_code=0,
            stdout=stdout,
            stderr=b"",
            duration_ms=1,
            timed_out=False,
            source_hash=sha256_hex(source),
            toolchain_identity=identity,
            project_pin_hash="c" * 64,
        )


class LeanReferenceVerifierTests(unittest.TestCase):
    def test_matching_python_and_lean_verdict_is_accepted(self) -> None:
        packet = reference_packets()[0]
        report = LeanReferenceVerifier(_FakeCompiler()).verify(packet)
        self.assertTrue(report.accepted)
        self.assertTrue(report.differential_match)
        self.assertEqual(report.reason_codes, ())
        self.assertTrue(report.lean_rcp_acceptance)
        self.assertTrue(report.lean_rclm_acceptance)

    def test_rcp_differential_mismatch_is_rejected(self) -> None:
        packet = reference_packets()[0]
        report = LeanReferenceVerifier(
            _FakeCompiler(force_rcp_acceptance=False)
        ).verify(packet)
        self.assertFalse(report.accepted)
        self.assertIn("PYTHON_LEAN_RCP_DIFFERENTIAL_MISMATCH", report.reason_codes)

    def test_rclm_layer_mismatch_is_rejected(self) -> None:
        packet = reference_packets()[0]
        report = LeanReferenceVerifier(
            _FakeCompiler(force_rclm_acceptance=False)
        ).verify(packet)
        self.assertFalse(report.accepted)
        self.assertIn("LEAN_RCP_RCLM_LAYER_MISMATCH", report.reason_codes)
        self.assertIn("PYTHON_LEAN_RCLM_DIFFERENTIAL_MISMATCH", report.reason_codes)


if __name__ == "__main__":
    unittest.main()
