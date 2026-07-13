from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal, TypeAlias

from rcp_rclm_runtime._version import CONTRACT_VERSION, LEAN_TOOLCHAIN, MATHLIB_COMMIT
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex, validate_hash256
from rcp_rclm_runtime.errors import RuntimeValidationError, SchemaValidationError
from rcp_rclm_runtime.lean_bridge.compiler import LeanCompilationResult, LeanCompiler
from rcp_rclm_runtime.lean_bridge.packet import LeanReferencePacket
from rcp_rclm_runtime.lean_bridge.source_generator import GeneratedLeanSource, generate_reference_source
from rcp_rclm_runtime.lean_bridge.source_guard import SourceGuardReport, scan_source_bytes
from rcp_rclm_runtime.lean_bridge.verdict_parser import (
    LeanReferenceVerdict,
    LeanVerdictParseError,
    parse_lean_reference_verdict,
)
from rcp_rclm_runtime.schema.verdict import LeanVerifierReportRecord

BridgeVerdictName: TypeAlias = Literal["accept", "reject", "indeterminate"]


@dataclass(frozen=True, slots=True)
class LeanBridgeVerificationReport:
    bridge_verdict: BridgeVerdictName
    reason_codes: Sequence[str]
    case_id: str
    scope: str
    packet_hash: str
    expected_acceptance: bool
    lean_rcp_acceptance: bool | None
    lean_rclm_acceptance: bool | None
    differential_match: bool
    generated_source_path: str
    generated_source_hash: str
    theorem_surface_hash: str
    project_pin_hash: str
    toolchain_runtime_hash: str
    source_guard_hash: str
    error_detail_hash: str
    compiler_report: LeanVerifierReportRecord
    compiler_duration_ms: int
    timed_out: bool
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = "runtime.lean_bridge_verification_report.v2"

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        if self.bridge_verdict not in {"accept", "reject", "indeterminate"}:
            raise SchemaValidationError(
                "lean_bridge_report.bridge_verdict",
                f"unsupported verdict: {self.bridge_verdict}",
            )
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "lean_bridge_report.contract_version",
                f"expected {CONTRACT_VERSION}",
            )
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise SchemaValidationError(
                "lean_bridge_report.reason_codes",
                "reason codes must be unique",
            )
        if self.bridge_verdict == "accept" and self.reason_codes:
            raise SchemaValidationError(
                "lean_bridge_report.reason_codes",
                "accept verdict cannot contain failure reasons",
            )
        if self.bridge_verdict != "accept" and not self.reason_codes:
            raise SchemaValidationError(
                "lean_bridge_report.reason_codes",
                "nonaccepting verdict requires a reason code",
            )
        if self.bridge_verdict == "accept":
            if not self.differential_match:
                raise SchemaValidationError(
                    "lean_bridge_report.differential_match",
                    "accept requires a differential match",
                )
            if self.lean_rcp_acceptance != self.expected_acceptance:
                raise SchemaValidationError(
                    "lean_bridge_report.lean_rcp_acceptance",
                    "accept requires Lean RCP agreement",
                )
            if self.lean_rclm_acceptance != self.expected_acceptance:
                raise SchemaValidationError(
                    "lean_bridge_report.lean_rclm_acceptance",
                    "accept requires Lean RCLM agreement",
                )
        if isinstance(self.compiler_duration_ms, bool) or not isinstance(
            self.compiler_duration_ms, int
        ):
            raise SchemaValidationError(
                "lean_bridge_report.compiler_duration_ms",
                "expected a nonnegative integer",
            )
        if self.compiler_duration_ms < 0:
            raise SchemaValidationError(
                "lean_bridge_report.compiler_duration_ms",
                "expected a nonnegative integer",
            )
        if not isinstance(self.timed_out, bool):
            raise SchemaValidationError(
                "lean_bridge_report.timed_out",
                "expected a Boolean",
            )
        for field_name in (
            "packet_hash",
            "generated_source_hash",
            "theorem_surface_hash",
            "project_pin_hash",
            "toolchain_runtime_hash",
            "source_guard_hash",
            "error_detail_hash",
        ):
            validate_hash256(getattr(self, field_name), f"lean_bridge_report.{field_name}")

    @property
    def accepted(self) -> bool:
        return self.bridge_verdict == "accept"

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "bridge_verdict": self.bridge_verdict,
            "reason_codes": list(self.reason_codes),
            "case_id": self.case_id,
            "scope": self.scope,
            "packet_hash": self.packet_hash,
            "expected_acceptance": self.expected_acceptance,
            "lean_rcp_acceptance": self.lean_rcp_acceptance,
            "lean_rclm_acceptance": self.lean_rclm_acceptance,
            "differential_match": self.differential_match,
            "generated_source_path": self.generated_source_path,
            "generated_source_hash": self.generated_source_hash,
            "theorem_surface_hash": self.theorem_surface_hash,
            "project_pin_hash": self.project_pin_hash,
            "toolchain_runtime_hash": self.toolchain_runtime_hash,
            "source_guard_hash": self.source_guard_hash,
            "error_detail_hash": self.error_detail_hash,
            "compiler_report": self.compiler_report.to_json(),
            "compiler_duration_ms": self.compiler_duration_ms,
            "timed_out": self.timed_out,
        }


@dataclass(frozen=True, slots=True)
class LeanBridgeVerificationEvidence:
    generated: GeneratedLeanSource
    source_guard: SourceGuardReport
    compilation: LeanCompilationResult | None
    parsed_verdict: LeanReferenceVerdict | None
    report: LeanBridgeVerificationReport


class LeanReferenceVerifier:
    def __init__(self, compiler: LeanCompiler) -> None:
        self._compiler = compiler

    def verify(self, packet: LeanReferencePacket) -> LeanBridgeVerificationReport:
        return self.verify_with_evidence(packet).report

    def verify_with_evidence(
        self,
        packet: LeanReferencePacket,
    ) -> LeanBridgeVerificationEvidence:
        generated = generate_reference_source(packet)
        guard_report = scan_source_bytes(generated.source_bytes)
        if not guard_report.clean:
            report = _rejected_before_compile(generated, guard_report)
            return LeanBridgeVerificationEvidence(
                generated=generated,
                source_guard=guard_report,
                compilation=None,
                parsed_verdict=None,
                report=report,
            )
        try:
            compilation = self._compiler.compile_source(
                generated.source_bytes,
                source_name=generated.virtual_path,
            )
        except RuntimeValidationError as exc:
            report = _indeterminate_compiler_error(
                generated,
                guard_report,
                self._compiler.project.pin_hash,
                exc,
            )
            return LeanBridgeVerificationEvidence(
                generated=generated,
                source_guard=guard_report,
                compilation=None,
                parsed_verdict=None,
                report=report,
            )
        compiler_record = LeanVerifierReportRecord(
            verdict="accept" if compilation.succeeded else "reject",
            source_hash=compilation.source_hash,
            exit_code=compilation.exit_code,
            stdout_hash=compilation.stdout_hash,
            stderr_hash=compilation.stderr_hash,
            forbidden_tokens=(),
            toolchain=LEAN_TOOLCHAIN,
            mathlib_commit=MATHLIB_COMMIT,
        )
        reasons: list[str] = []
        verdict: LeanReferenceVerdict | None = None
        error_detail = ""
        if not compilation.succeeded:
            reasons.append("LEAN_COMPILATION_FAILED")
            error_detail = compilation.stderr.decode("utf-8", errors="replace")
            if compilation.timed_out:
                reasons.append("LEAN_COMPILATION_TIMEOUT")
        else:
            try:
                verdict = parse_lean_reference_verdict(compilation.stdout)
            except LeanVerdictParseError as exc:
                reasons.append("LEAN_VERDICT_PARSE_FAILED")
                error_detail = str(exc)
        if verdict is not None:
            reasons.extend(_verdict_mismatches(generated, verdict))
        lean_rcp_acceptance = None if verdict is None else verdict.rcp_accepted
        lean_rclm_acceptance = None if verdict is None else verdict.rclm_accepted
        differential_match = verdict is not None and not reasons
        if differential_match:
            bridge_verdict: BridgeVerdictName = "accept"
        elif compilation.timed_out:
            bridge_verdict = "indeterminate"
        else:
            bridge_verdict = "reject"
        report = LeanBridgeVerificationReport(
            bridge_verdict=bridge_verdict,
            reason_codes=tuple(reasons),
            case_id=packet.case_id,
            scope=packet.scope,
            packet_hash=packet.packet_hash,
            expected_acceptance=generated.expected_acceptance,
            lean_rcp_acceptance=lean_rcp_acceptance,
            lean_rclm_acceptance=lean_rclm_acceptance,
            differential_match=differential_match,
            generated_source_path=generated.virtual_path,
            generated_source_hash=generated.source_hash,
            theorem_surface_hash=generated.theorem_surface_hash,
            project_pin_hash=compilation.project_pin_hash,
            toolchain_runtime_hash=compilation.toolchain_identity.runtime_hash,
            source_guard_hash=canonical_json_hash(guard_report.to_json()),
            error_detail_hash=sha256_hex(error_detail.encode("utf-8")),
            compiler_report=compiler_record,
            compiler_duration_ms=compilation.duration_ms,
            timed_out=compilation.timed_out,
        )
        return LeanBridgeVerificationEvidence(
            generated=generated,
            source_guard=guard_report,
            compilation=compilation,
            parsed_verdict=verdict,
            report=report,
        )


def _verdict_mismatches(
    generated: GeneratedLeanSource,
    verdict: LeanReferenceVerdict,
) -> list[str]:
    reasons: list[str] = []
    if verdict.case_id != generated.packet.case_id:
        reasons.append("LEAN_VERDICT_CASE_MISMATCH")
    if verdict.scope != generated.packet.scope:
        reasons.append("LEAN_VERDICT_SCOPE_MISMATCH")
    if verdict.packet_hash != generated.packet.packet_hash:
        reasons.append("LEAN_VERDICT_PACKET_HASH_MISMATCH")
    if verdict.theorem_surface_hash != generated.theorem_surface_hash:
        reasons.append("LEAN_VERDICT_THEOREM_SURFACE_MISMATCH")
    if not verdict.layers_agree:
        reasons.append("LEAN_RCP_RCLM_LAYER_MISMATCH")
    if verdict.rcp_accepted != generated.expected_acceptance:
        reasons.append("PYTHON_LEAN_RCP_DIFFERENTIAL_MISMATCH")
    if verdict.rclm_accepted != generated.expected_acceptance:
        reasons.append("PYTHON_LEAN_RCLM_DIFFERENTIAL_MISMATCH")
    return reasons


def _rejected_before_compile(
    generated: GeneratedLeanSource,
    guard_report: SourceGuardReport,
) -> LeanBridgeVerificationReport:
    compiler_record = LeanVerifierReportRecord(
        verdict="reject",
        source_hash=generated.source_hash,
        exit_code=126,
        stdout_hash=sha256_hex(b""),
        stderr_hash=sha256_hex(b"source_guard_rejected"),
        forbidden_tokens=(),
        toolchain=LEAN_TOOLCHAIN,
        mathlib_commit=MATHLIB_COMMIT,
    )
    finding_text = canonical_json_hash(guard_report.to_json())
    return LeanBridgeVerificationReport(
        bridge_verdict="reject",
        reason_codes=("LEAN_SOURCE_GUARD_REJECTED",),
        case_id=generated.packet.case_id,
        scope=generated.packet.scope,
        packet_hash=generated.packet.packet_hash,
        expected_acceptance=generated.expected_acceptance,
        lean_rcp_acceptance=None,
        lean_rclm_acceptance=None,
        differential_match=False,
        generated_source_path=generated.virtual_path,
        generated_source_hash=generated.source_hash,
        theorem_surface_hash=generated.theorem_surface_hash,
        project_pin_hash=canonical_json_hash({"project": "not_invoked"}),
        toolchain_runtime_hash=canonical_json_hash({"toolchain": "not_invoked"}),
        source_guard_hash=canonical_json_hash(guard_report.to_json()),
        error_detail_hash=sha256_hex(finding_text.encode("utf-8")),
        compiler_report=compiler_record,
        compiler_duration_ms=0,
        timed_out=False,
    )


def _indeterminate_compiler_error(
    generated: GeneratedLeanSource,
    guard_report: SourceGuardReport,
    project_pin_hash: str,
    error: RuntimeValidationError,
) -> LeanBridgeVerificationReport:
    detail = str(error)
    compiler_record = LeanVerifierReportRecord(
        verdict="reject",
        source_hash=generated.source_hash,
        exit_code=125,
        stdout_hash=sha256_hex(b""),
        stderr_hash=sha256_hex(detail.encode("utf-8")),
        forbidden_tokens=(),
        toolchain=LEAN_TOOLCHAIN,
        mathlib_commit=MATHLIB_COMMIT,
    )
    return LeanBridgeVerificationReport(
        bridge_verdict="indeterminate",
        reason_codes=(error.code,),
        case_id=generated.packet.case_id,
        scope=generated.packet.scope,
        packet_hash=generated.packet.packet_hash,
        expected_acceptance=generated.expected_acceptance,
        lean_rcp_acceptance=None,
        lean_rclm_acceptance=None,
        differential_match=False,
        generated_source_path=generated.virtual_path,
        generated_source_hash=generated.source_hash,
        theorem_surface_hash=generated.theorem_surface_hash,
        project_pin_hash=project_pin_hash,
        toolchain_runtime_hash=canonical_json_hash({"toolchain": "unavailable"}),
        source_guard_hash=canonical_json_hash(guard_report.to_json()),
        error_detail_hash=sha256_hex(detail.encode("utf-8")),
        compiler_report=compiler_record,
        compiler_duration_ms=0,
        timed_out=False,
    )
