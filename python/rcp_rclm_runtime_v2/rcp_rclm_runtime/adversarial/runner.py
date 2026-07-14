from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from dataclasses import replace

from rcp_rclm_runtime.canonical.hashing import SemanticFileRecord, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.errors import RuntimeValidationError
from rcp_rclm_runtime.lean_bridge.source_guard import scan_source_bytes
from rcp_rclm_runtime.mathematics.classical import DistributionRecord
from rcp_rclm_runtime.mathematics.diagonal_quantum import (
    ComplexRational,
    DiagonalDensityRecord,
    SelectedChannelRecord,
    quantum_relative_entropy_interval,
    validate_dense_export,
)
from rcp_rclm_runtime.mathematics.intervals import IntervalEvidence
from rcp_rclm_runtime.mathematics.rational import Rational
from rcp_rclm_runtime.schema._common import TypedArtifactRecord
from rcp_rclm_runtime.schema.state import (
    ClassicalBinaryStateRecord,
    QuantumStateRecord,
)
from rcp_rclm_runtime.schema.verdict import ReasonCode
from rcp_rclm_runtime.checker.hardened import (
    Phase4HardenedReport,
    Phase4HardenedRequest,
    check_hardened_transition,
    check_hardened_transition_bytes,
)
from rcp_rclm_runtime.checker.integrity import PackageIntegrityRecord
from rcp_rclm_runtime.checker.reference import canonical_rclm_state
from rcp_rclm_runtime.adversarial.records import (
    AdversarialCaseResult,
    AdversarialSuiteReport,
)
from rcp_rclm_runtime.adversarial.reference import reference_hardened_request


def run_phase4_adversarial_suite() -> AdversarialSuiteReport:
    cases = (
        _malformed_schema_case(),
        _unknown_schema_version_case(),
        _missing_evidence_case(),
        _parent_hash_substitution_case(),
        _certificate_replay_case(),
        _tampered_candidate_file_case(),
        _tampered_checker_manifest_case(),
        _nan_case(),
        _infinity_case(),
        _negative_probability_case(),
        _non_normalized_probability_case(),
        _unsupported_qre_support_case(),
        _wrong_matrix_dimension_case(),
        _non_diagonal_matrix_case(),
        _unsupported_channel_case(),
        _forged_recovery_witness_case(),
        _forged_strict_progress_witness_case(),
        _insufficient_numerical_margin_case(),
        _resource_budget_overflow_case(),
        _trust_anchor_replacement_case(),
        _manual_repair_marker_case(),
        _hidden_oracle_marker_case(),
        _source_guard_case(
            case_id="phase4.lean_source.admit",
            token="admit",
            source=b"theorem bad : True := by\n  admit\n",
            expected_reason="LEAN_SOURCE_FORBIDDEN_TOKEN",
        ),
        _source_guard_case(
            case_id="phase4.lean_source.sorry",
            token="sorry",
            source=b"theorem bad : True := by\n  sorry\n",
            expected_reason="LEAN_SOURCE_FORBIDDEN_TOKEN",
        ),
        _source_guard_case(
            case_id="phase4.lean_source.sorry_ax",
            token="sorryAx",
            source=b"theorem bad : True := by\n  exact sorryAx True true\n",
            expected_reason="LEAN_SOURCE_FORBIDDEN_TOKEN",
        ),
        _source_guard_case(
            case_id="phase4.lean_source.local_axiom",
            token="axiom",
            source=b"axiom unsafePremise : Prop\n",
            expected_reason="LEAN_SOURCE_LOCAL_AXIOM",
        ),
        _source_guard_case(
            case_id="phase4.lean_source.invalid_utf8",
            token="invalid_utf8",
            source=b"\xff\xfe",
            expected_reason="LEAN_SOURCE_INVALID_UTF8",
        ),
    )
    return AdversarialSuiteReport(tuple(sorted(cases, key=lambda item: item.case_id)))


def _malformed_schema_case() -> AdversarialCaseResult:
    value = reference_hardened_request().to_json()
    value["checker_request"] = []
    return _bytes_case(
        case_id="phase4.schema.malformed",
        attack_class="malformed_schema",
        data=canonical_json_bytes(value),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.SCHEMA_MALFORMED.value,),
    )


def _unknown_schema_version_case() -> AdversarialCaseResult:
    value = reference_hardened_request().to_json()
    value["schema_id"] = "runtime.phase4_hardened_checker_request.v999"
    return _bytes_case(
        case_id="phase4.schema.unknown_version",
        attack_class="unknown_schema_version",
        data=canonical_json_bytes(value),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.SCHEMA_MALFORMED.value,),
    )


def _missing_evidence_case() -> AdversarialCaseResult:
    value = reference_hardened_request().to_json()
    checker_request = _mapping(value["checker_request"])
    del checker_request["evaluation_evidence"]
    return _bytes_case(
        case_id="phase4.schema.missing_evidence",
        attack_class="missing_evidence",
        data=canonical_json_bytes(value),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.SCHEMA_MALFORMED.value,),
    )


def _parent_hash_substitution_case() -> AdversarialCaseResult:
    request = reference_hardened_request()
    candidate_manifest = replace(
        request.package_integrity.candidate_manifest,
        parent_manifest_hash="0" * 64,
    )
    integrity = replace(
        request.package_integrity,
        candidate_manifest=candidate_manifest,
    )
    return _request_case(
        case_id="phase4.package.parent_hash_substitution",
        attack_class="parent_hash_substitution",
        request=replace(request, package_integrity=integrity),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.PARENT_LINK_MISMATCH.value,),
    )


def _certificate_replay_case() -> AdversarialCaseResult:
    request = reference_hardened_request()
    replayed = replace(
        request.checker_request,
        predecessor=canonical_rclm_state(ClassicalBinaryStateRecord("target")),
    )
    return _request_case(
        case_id="phase4.certificate.replay_other_predecessor",
        attack_class="certificate_replay",
        request=replace(request, checker_request=replayed),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.PROVENANCE_FAILED.value,),
    )


def _tampered_candidate_file_case() -> AdversarialCaseResult:
    request = reference_hardened_request()
    original = request.package_integrity.candidate_files[0]
    tampered = SemanticFileRecord(
        path=original.path,
        mode=original.mode,
        size=original.size,
        sha256="0" * 64,
    )
    candidate_files = (tampered,) + tuple(
        request.package_integrity.candidate_files[1:]
    )
    integrity = replace(
        request.package_integrity,
        candidate_files=candidate_files,
    )
    return _request_case(
        case_id="phase4.package.tampered_candidate_file",
        attack_class="tampered_candidate_files",
        request=replace(request, package_integrity=integrity),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.HASH_MISMATCH.value,),
    )


def _tampered_checker_manifest_case() -> AdversarialCaseResult:
    request = reference_hardened_request()
    integrity = replace(
        request.package_integrity,
        checker_manifest_hash="0" * 64,
    )
    return _request_case(
        case_id="phase4.package.tampered_checker_manifest",
        attack_class="tampered_checker_manifest",
        request=replace(request, package_integrity=integrity),
        expected_verdict="reject",
        expected_reasons=(
            ReasonCode.HASH_MISMATCH.value,
            ReasonCode.PROVENANCE_FAILED.value,
        ),
    )


def _nan_case() -> AdversarialCaseResult:
    return _bytes_case(
        case_id="phase4.numeric.nan",
        attack_class="nan",
        data=b'{"budget":NaN}',
        expected_verdict="reject",
        expected_reasons=(ReasonCode.CANONICALIZATION_FAILED.value,),
    )


def _infinity_case() -> AdversarialCaseResult:
    return _bytes_case(
        case_id="phase4.numeric.infinity",
        attack_class="infinity",
        data=b'{"budget":Infinity}',
        expected_verdict="reject",
        expected_reasons=(ReasonCode.CANONICALIZATION_FAILED.value,),
    )


def _negative_probability_case() -> AdversarialCaseResult:
    value = copy.deepcopy(reference_hardened_request().to_json())
    observation = _classical_predecessor_observation(value)
    observation["masses"] = [
        {"numerator": "-1", "denominator": "2"},
        {"numerator": "3", "denominator": "2"},
    ]
    return _bytes_case(
        case_id="phase4.probability.negative_mass",
        attack_class="negative_probability",
        data=canonical_json_bytes(value),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.SCHEMA_MALFORMED.value,),
    )


def _non_normalized_probability_case() -> AdversarialCaseResult:
    value = copy.deepcopy(reference_hardened_request().to_json())
    observation = _classical_predecessor_observation(value)
    observation["masses"] = [
        {"numerator": "1", "denominator": "3"},
        {"numerator": "1", "denominator": "3"},
    ]
    return _bytes_case(
        case_id="phase4.probability.non_normalized",
        attack_class="non_normalized_probability",
        data=canonical_json_bytes(value),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.SCHEMA_MALFORMED.value,),
    )


def _unsupported_qre_support_case() -> AdversarialCaseResult:
    source = DiagonalDensityRecord(
        DistributionRecord.from_masses((Rational(1, 2), Rational(1, 2)))
    )
    target = DiagonalDensityRecord(
        DistributionRecord.from_masses((Rational.one(), Rational.zero()))
    )
    return _exception_case(
        case_id="phase4.quantum.unsupported_qre_support",
        attack_class="unsupported_qre_support",
        expected_reason="QRE_SUPPORT_UNSUPPORTED",
        operation=lambda: quantum_relative_entropy_interval(source, target),
    )


def _wrong_matrix_dimension_case() -> AdversarialCaseResult:
    return _exception_case(
        case_id="phase4.quantum.wrong_matrix_dimension",
        attack_class="wrong_matrix_dimension",
        expected_reason="MATRIX_DIMENSION_UNSUPPORTED",
        operation=lambda: DiagonalDensityRecord(
            DistributionRecord.from_masses(
                (Rational(1, 3), Rational(1, 3), Rational(1, 3))
            ),
            dimension=3,
        ),
    )


def _non_diagonal_matrix_case() -> AdversarialCaseResult:
    density = QuantumStateRecord.canonical("source").density
    matrix = (
        (
            ComplexRational(Rational(1, 4)),
            ComplexRational(Rational(1, 10)),
        ),
        (
            ComplexRational(Rational(1, 10)),
            ComplexRational(Rational(3, 4)),
        ),
    )
    return _exception_case(
        case_id="phase4.quantum.non_diagonal_matrix",
        attack_class="non_diagonal_matrix",
        expected_reason="NON_DIAGONAL_MATRIX_REJECTED",
        operation=lambda: validate_dense_export(density, matrix),
    )


def _unsupported_channel_case() -> AdversarialCaseResult:
    return _exception_case(
        case_id="phase4.quantum.unsupported_channel",
        attack_class="unsupported_channel",
        expected_reason="CHANNEL_UNSUPPORTED",
        operation=lambda: SelectedChannelRecord(
            kind="depolarizing",
            permutation=(0, 1),
        ),
    )


def _forged_recovery_witness_case() -> AdversarialCaseResult:
    request = reference_hardened_request("gate_c_diagonal_quantum")
    candidate = replace(
        request.checker_request.candidate,
        next=canonical_rclm_state(QuantumStateRecord.canonical("source")),
    )
    checker_request = replace(request.checker_request, candidate=candidate)
    return _request_case(
        case_id="phase4.witness.forged_recovery",
        attack_class="forged_recovery_witness",
        request=replace(request, checker_request=checker_request),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.RECOVERY_FAILED.value,),
    )


def _forged_strict_progress_witness_case() -> AdversarialCaseResult:
    request = reference_hardened_request(stability=True)
    forged_progress = TypedArtifactRecord.from_value(
        request.checker_request.certificate.progress.schema_id,
        {"evidence": "strict"},
    )
    certificate = replace(
        request.checker_request.certificate,
        progress=forged_progress,
    )
    checker_request = replace(request.checker_request, certificate=certificate)
    return _request_case(
        case_id="phase4.witness.forged_strict_progress",
        attack_class="forged_strict_progress_witness",
        request=replace(request, checker_request=checker_request),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.REFINEMENT_MISMATCH.value,),
    )


def _insufficient_numerical_margin_case() -> AdversarialCaseResult:
    interval = IntervalEvidence(
        Rational(-1, 1 << 260),
        Rational(1, 1 << 260),
        256,
    )
    first = _strict_margin_observation(interval)
    second = _strict_margin_observation(interval)
    return AdversarialCaseResult.from_evidence(
        case_id="phase4.numeric.insufficient_margin",
        attack_class="insufficient_numerical_margin",
        expected_verdict="indeterminate",
        expected_reason_codes=(ReasonCode.NUMERIC_INDETERMINATE.value,),
        observed_verdict=first["verdict"],
        observed_reason_codes=first["reason_codes"],
        first_observation=first,
        second_observation=second,
        evidence={"interval": interval.to_json()},
    )


def _resource_budget_overflow_case() -> AdversarialCaseResult:
    request = reference_hardened_request()
    resource = replace(
        request.checker_request.resource_record,
        consumed_units=request.checker_request.resource_record.budget_units + 1,
    )
    checker_request = replace(request.checker_request, resource_record=resource)
    return _request_case(
        case_id="phase4.resource.budget_overflow",
        attack_class="resource_budget_overflow",
        request=replace(request, checker_request=checker_request),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.RESOURCE_INVALID.value,),
    )


def _trust_anchor_replacement_case() -> AdversarialCaseResult:
    request = reference_hardened_request()
    anchor = replace(
        request.checker_request.trust_anchor,
        gate_c_audit_sha256="0" * 64,
    )
    checker_request = replace(request.checker_request, trust_anchor=anchor)
    return _request_case(
        case_id="phase4.trust.anchor_replacement",
        attack_class="trust_anchor_replacement",
        request=replace(request, checker_request=checker_request),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.TRUST_ANCHOR_CHANGED.value,),
    )


def _manual_repair_marker_case() -> AdversarialCaseResult:
    request = reference_hardened_request()
    resource = replace(
        request.checker_request.resource_record,
        manual_repair_count=1,
    )
    checker_request = replace(request.checker_request, resource_record=resource)
    return _request_case(
        case_id="phase4.provenance.manual_repair_marker",
        attack_class="manual_repair_marker",
        request=replace(request, checker_request=checker_request),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.MANUAL_REPAIR_DETECTED.value,),
    )


def _hidden_oracle_marker_case() -> AdversarialCaseResult:
    request = reference_hardened_request()
    resource = replace(
        request.checker_request.resource_record,
        hidden_oracle_reads=1,
    )
    checker_request = replace(request.checker_request, resource_record=resource)
    return _request_case(
        case_id="phase4.provenance.hidden_oracle_marker",
        attack_class="hidden_oracle_marker",
        request=replace(request, checker_request=checker_request),
        expected_verdict="reject",
        expected_reasons=(ReasonCode.PROVENANCE_FAILED.value,),
    )


def _source_guard_case(
    *,
    case_id: str,
    token: str,
    source: bytes,
    expected_reason: str,
) -> AdversarialCaseResult:
    first_report = scan_source_bytes(source, source_path=f"generated/{case_id}.lean")
    second_report = scan_source_bytes(source, source_path=f"generated/{case_id}.lean")
    first = first_report.to_json()
    second = second_report.to_json()
    reasons = tuple(finding.code for finding in first_report.findings)
    return AdversarialCaseResult.from_evidence(
        case_id=case_id,
        attack_class="generated_lean_forbidden_source",
        expected_verdict="reject",
        expected_reason_codes=(expected_reason,),
        observed_verdict="reject" if not first_report.clean else "accept",
        observed_reason_codes=reasons,
        first_observation=first,
        second_observation=second,
        evidence={
            "token": token,
            "source_hash": first_report.source_hash,
            "source_path": first_report.source_path,
        },
    )


def _request_case(
    *,
    case_id: str,
    attack_class: str,
    request: Phase4HardenedRequest,
    expected_verdict: str,
    expected_reasons: Sequence[str],
) -> AdversarialCaseResult:
    first_report = check_hardened_transition(request)
    second_report = check_hardened_transition(request)
    return _report_case(
        case_id=case_id,
        attack_class=attack_class,
        expected_verdict=expected_verdict,
        expected_reasons=expected_reasons,
        first_report=first_report,
        second_report=second_report,
        input_hash=sha256_hex(canonical_json_bytes(request.to_json())),
    )


def _bytes_case(
    *,
    case_id: str,
    attack_class: str,
    data: bytes,
    expected_verdict: str,
    expected_reasons: Sequence[str],
) -> AdversarialCaseResult:
    first_report = check_hardened_transition_bytes(data)
    second_report = check_hardened_transition_bytes(data)
    return _report_case(
        case_id=case_id,
        attack_class=attack_class,
        expected_verdict=expected_verdict,
        expected_reasons=expected_reasons,
        first_report=first_report,
        second_report=second_report,
        input_hash=sha256_hex(data),
    )


def _report_case(
    *,
    case_id: str,
    attack_class: str,
    expected_verdict: str,
    expected_reasons: Sequence[str],
    first_report: Phase4HardenedReport,
    second_report: Phase4HardenedReport,
    input_hash: str,
) -> AdversarialCaseResult:
    first = first_report.to_json()
    second = second_report.to_json()
    return AdversarialCaseResult.from_evidence(
        case_id=case_id,
        attack_class=attack_class,
        expected_verdict=expected_verdict,
        expected_reason_codes=expected_reasons,
        observed_verdict=first_report.verdict,
        observed_reason_codes=tuple(
            reason.value for reason in first_report.reason_codes
        ),
        first_observation=first,
        second_observation=second,
        evidence={
            "input_sha256": input_hash,
            "first_report_hash": first_report.report_hash,
            "second_report_hash": second_report.report_hash,
        },
    )


def _exception_case(
    *,
    case_id: str,
    attack_class: str,
    expected_reason: str,
    operation: Callable[[], object],
) -> AdversarialCaseResult:
    first = _exception_observation(operation, expected_reason)
    second = _exception_observation(operation, expected_reason)
    return AdversarialCaseResult.from_evidence(
        case_id=case_id,
        attack_class=attack_class,
        expected_verdict="reject",
        expected_reason_codes=(expected_reason,),
        observed_verdict=first["verdict"],
        observed_reason_codes=first["reason_codes"],
        first_observation=first,
        second_observation=second,
        evidence={"operation": attack_class},
    )


def _exception_observation(
    operation: Callable[[], object],
    expected_reason: str,
) -> dict[str, object]:
    try:
        value = operation()
    except (RuntimeValidationError, TypeError, ValueError) as exc:
        return {
            "verdict": "reject",
            "reason_codes": [expected_reason],
            "error_type": type(exc).__name__,
            "error_detail_hash": sha256_hex(str(exc).encode("utf-8")),
        }
    return {
        "verdict": "accept",
        "reason_codes": [],
        "unexpected_value_type": type(value).__name__,
    }


def _strict_margin_observation(interval: IntervalEvidence) -> dict[str, object]:
    if interval.lower > Rational.zero():
        return {"verdict": "accept", "reason_codes": []}
    if interval.upper <= Rational.zero():
        return {
            "verdict": "reject",
            "reason_codes": [ReasonCode.STRICT_WITNESS_FAILED.value],
        }
    return {
        "verdict": "indeterminate",
        "reason_codes": [ReasonCode.NUMERIC_INDETERMINATE.value],
    }


def _classical_predecessor_observation(value: dict[str, object]) -> dict[str, object]:
    checker_request = _mapping(value["checker_request"])
    evaluation = _mapping(checker_request["evaluation_evidence"])
    return _mapping(evaluation["predecessor_observation"])


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("expected a mutable object")
    return value
