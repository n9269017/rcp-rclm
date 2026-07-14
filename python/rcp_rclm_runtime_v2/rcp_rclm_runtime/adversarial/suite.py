from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace

from rcp_rclm_runtime.canonical.hashing import (
    SemanticFileRecord,
    semantic_tree_hash,
    sha256_hex,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.errors import RuntimeValidationError
from rcp_rclm_runtime.mathematics.classical import DistributionRecord
from rcp_rclm_runtime.mathematics.diagonal_quantum import (
    ComplexRational,
    DiagonalDensityRecord,
    SelectedChannelRecord,
    quantum_relative_entropy_interval,
    validate_dense_export,
)
from rcp_rclm_runtime.mathematics.rational import Rational
from rcp_rclm_runtime.schema.state import QuantumStateRecord
from rcp_rclm_runtime.schema.verdict import ReasonCode
from rcp_rclm_runtime.checker.hardened import check_hardened_transition
from rcp_rclm_runtime.adversarial.records import (
    AdversarialCaseResult,
    AdversarialSuiteReport,
)
from rcp_rclm_runtime.adversarial.reference import reference_hardened_request
from rcp_rclm_runtime.adversarial.runner import (
    run_phase4_adversarial_suite as _run_base_suite,
)

_REPLACED_CASE_IDS = frozenset(
    {
        "phase4.package.tampered_candidate_file",
        "phase4.quantum.non_diagonal_matrix",
        "phase4.quantum.unsupported_channel",
        "phase4.quantum.unsupported_qre_support",
        "phase4.quantum.wrong_matrix_dimension",
    }
)


def run_phase4_adversarial_suite() -> AdversarialSuiteReport:
    base = _run_base_suite()
    retained = [item for item in base.results if item.case_id not in _REPLACED_CASE_IDS]
    replacements = [
        _coherent_candidate_file_substitution_case(),
        _unsupported_qre_support_case(),
        _wrong_matrix_dimension_case(),
        _non_diagonal_matrix_case(),
        _unsupported_channel_case(),
    ]
    results = tuple(sorted((*retained, *replacements), key=lambda item: item.case_id))
    return AdversarialSuiteReport(results)


def _coherent_candidate_file_substitution_case() -> AdversarialCaseResult:
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
    candidate_manifest = replace(
        request.package_integrity.candidate_manifest,
        semantic_tree_hash=semantic_tree_hash(candidate_files),
    )
    integrity = replace(
        request.package_integrity,
        candidate_manifest=candidate_manifest,
        candidate_files=candidate_files,
    )
    attacked = replace(request, package_integrity=integrity)
    first_report = check_hardened_transition(attacked)
    second_report = check_hardened_transition(attacked)
    first = first_report.to_json()
    second = second_report.to_json()
    return AdversarialCaseResult.from_evidence(
        case_id="phase4.package.tampered_candidate_file",
        attack_class="tampered_candidate_files",
        expected_verdict="reject",
        expected_reason_codes=(ReasonCode.HASH_MISMATCH.value,),
        observed_verdict=first_report.verdict,
        observed_reason_codes=tuple(
            reason.value for reason in first_report.reason_codes
        ),
        first_observation=first,
        second_observation=second,
        evidence={
            "attack": "coherent file-record and semantic-tree substitution",
            "input_sha256": sha256_hex(canonical_json_bytes(attacked.to_json())),
            "first_report_hash": first_report.report_hash,
            "second_report_hash": second_report.report_hash,
        },
    )


def _unsupported_qre_support_case() -> AdversarialCaseResult:
    source = DiagonalDensityRecord(
        DistributionRecord.from_masses((Rational(1, 2), Rational(1, 2)))
    )
    target = DiagonalDensityRecord(
        DistributionRecord.from_masses((Rational.one(), Rational.zero()))
    )
    return _runtime_exception_case(
        case_id="phase4.quantum.unsupported_qre_support",
        attack_class="unsupported_qre_support",
        expected_reason="NUMERIC_INVALID",
        operation=lambda: quantum_relative_entropy_interval(source, target),
    )


def _wrong_matrix_dimension_case() -> AdversarialCaseResult:
    return _runtime_exception_case(
        case_id="phase4.quantum.wrong_matrix_dimension",
        attack_class="wrong_matrix_dimension",
        expected_reason="UNSUPPORTED_SCOPE",
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
    return _runtime_exception_case(
        case_id="phase4.quantum.non_diagonal_matrix",
        attack_class="non_diagonal_matrix",
        expected_reason="NUMERIC_INVALID",
        operation=lambda: validate_dense_export(density, matrix),
    )


def _unsupported_channel_case() -> AdversarialCaseResult:
    return _runtime_exception_case(
        case_id="phase4.quantum.unsupported_channel",
        attack_class="unsupported_channel",
        expected_reason="UNSUPPORTED_SCOPE",
        operation=lambda: SelectedChannelRecord(
            kind="depolarizing",
            permutation=(0, 1),
        ),
    )


def _runtime_exception_case(
    *,
    case_id: str,
    attack_class: str,
    expected_reason: str,
    operation: Callable[[], object],
) -> AdversarialCaseResult:
    first = _runtime_exception_observation(operation)
    second = _runtime_exception_observation(operation)
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


def _runtime_exception_observation(
    operation: Callable[[], object],
) -> dict[str, object]:
    try:
        value = operation()
    except RuntimeValidationError as exc:
        return {
            "verdict": "reject",
            "reason_codes": [exc.code],
            "error_type": type(exc).__name__,
            "error_path": exc.path,
            "error_detail_hash": sha256_hex(str(exc).encode("utf-8")),
        }
    except (TypeError, ValueError) as exc:
        return {
            "verdict": "reject",
            "reason_codes": [type(exc).__name__.upper()],
            "error_type": type(exc).__name__,
            "error_detail_hash": sha256_hex(str(exc).encode("utf-8")),
        }
    return {
        "verdict": "accept",
        "reason_codes": [],
        "unexpected_value_type": type(value).__name__,
    }
