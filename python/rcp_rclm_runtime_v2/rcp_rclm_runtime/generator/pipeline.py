from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import RuntimeValidationError
from rcp_rclm_runtime.lean_bridge.packet import LeanReferencePacket
from rcp_rclm_runtime.lean_bridge.verifier import LeanBridgeVerificationReport
from rcp_rclm_runtime.mathematics.classical import apply_binary_update
from rcp_rclm_runtime.refinement.mapping import RclmCandidateRecord
from rcp_rclm_runtime.schema.certificate import RclmCertificatePacketRecord
from rcp_rclm_runtime.schema.state import ClassicalBinaryStateRecord
from rcp_rclm_runtime.schema.update import (
    ClassicalBinaryUpdateRecord,
    RclmUpdateRecord,
)
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.checker.hardened import (
    Phase4HardenedReport,
    Phase4HardenedRequest,
    check_hardened_transition,
)
from rcp_rclm_runtime.checker.integrity import build_reference_package_integrity
from rcp_rclm_runtime.checker.records import Phase3CheckerRequest
from rcp_rclm_runtime.checker.reference import (
    build_lean_reference_packet,
    canonical_rclm_certificate,
    canonical_rclm_state,
    canonical_rclm_update,
    reference_evaluation_evidence,
    reference_protected_distinctions,
)
from rcp_rclm_runtime.generator.grammar import (
    certificate_name_for_word,
    update_name_for_proposal,
    validate_untrusted_proposal,
)
from rcp_rclm_runtime.generator.process import (
    GeneratorProcessEvidence,
    run_reference_generator_process,
)
from rcp_rclm_runtime.generator.protocol import (
    GeneratorReasonCode,
    GeneratorStageResult,
    ReferenceGeneratorInputRecord,
    ReferenceProposalRecord,
)
from rcp_rclm_runtime.generator.records import Phase5AReferenceLoopReport
from rcp_rclm_runtime.generator.reference import (
    reference_controller_resource_record,
    reference_controller_trust_anchor,
)

LeanVerifierCallable = Callable[[LeanReferencePacket], LeanBridgeVerificationReport]


@dataclass(frozen=True, slots=True)
class Phase5AReferenceLoopEvidence:
    generator_input: ReferenceGeneratorInputRecord
    first_process: GeneratorProcessEvidence
    second_process: GeneratorProcessEvidence
    report: Phase5AReferenceLoopReport


def run_phase5a_reference_loop(
    generator_input: ReferenceGeneratorInputRecord,
    verify_lean: LeanVerifierCallable,
) -> Phase5AReferenceLoopEvidence:
    first = run_reference_generator_process(generator_input)
    second = run_reference_generator_process(generator_input)
    worker_source_result = _worker_source_result(first, second)
    replay_result = _replay_result(first, second)

    proposal = first.proposal if replay_result.status == "pass" else None
    if proposal is None:
        proposal_validation_result = _not_evaluated()
        certificate_result = _not_evaluated()
        selection_result = _not_evaluated()
        realization_result = _not_evaluated()
        report = _early_report(
            generator_input,
            first,
            second,
            worker_source_result,
            replay_result,
            proposal_validation_result,
            certificate_result,
            selection_result,
            realization_result,
        )
        return Phase5AReferenceLoopEvidence(generator_input, first, second, report)

    proposal_validation_result = validate_untrusted_proposal(generator_input, proposal)
    if proposal_validation_result.status != "pass":
        report = _early_report(
            generator_input,
            first,
            second,
            worker_source_result,
            replay_result,
            proposal_validation_result,
            _not_evaluated(),
            _not_evaluated(),
            _not_evaluated(),
            proposal=proposal,
        )
        return Phase5AReferenceLoopEvidence(generator_input, first, second, report)

    certificate, certificate_result = _construct_certificate(generator_input, proposal)
    selected_update, selection_result = _select_update(generator_input, proposal)
    candidate, realization_result = _realize_candidate(
        generator_input,
        proposal,
        selected_update,
    )
    if (
        certificate is None
        or selected_update is None
        or candidate is None
        or certificate_result.status != "pass"
        or selection_result.status != "pass"
        or realization_result.status != "pass"
    ):
        report = _early_report(
            generator_input,
            first,
            second,
            worker_source_result,
            replay_result,
            proposal_validation_result,
            certificate_result,
            selection_result,
            realization_result,
            proposal=proposal,
        )
        return Phase5AReferenceLoopEvidence(generator_input, first, second, report)

    trust_anchor = reference_controller_trust_anchor()
    resource_record = reference_controller_resource_record()
    packet = build_lean_reference_packet(
        generator_input.predecessor.state,
        candidate,
        certificate,
    )
    try:
        lean_report = verify_lean(packet)
    except Exception as exc:
        report = _lean_error_report(
            generator_input,
            first,
            second,
            worker_source_result,
            replay_result,
            proposal,
            proposal_validation_result,
            certificate_result,
            selection_result,
            realization_result,
            exc,
        )
        return Phase5AReferenceLoopEvidence(generator_input, first, second, report)

    checker_request = Phase3CheckerRequest(
        transition_id=generator_input.transition_id,
        predecessor=generator_input.predecessor.state,
        candidate=candidate,
        certificate=certificate,
        trust_anchor=trust_anchor,
        resource_record=resource_record,
        protected_distinctions=reference_protected_distinctions(
            "gate_b_classical"
        ),
        evaluation_evidence=reference_evaluation_evidence(
            generator_input.predecessor.state,
            candidate,
        ),
        lean_bridge_report=lean_report,
    )
    package_integrity = build_reference_package_integrity(checker_request)
    predecessor_manifest_matches = (
        package_integrity.predecessor_manifest.content_hash()
        == generator_input.predecessor.manifest_hash
    )
    if not predecessor_manifest_matches:
        failed_realization = GeneratorStageResult.from_evidence(
            "fail",
            (GeneratorReasonCode.REALIZATION_FAILED,),
            {
                "predecessor_manifest_matches_generator_input": False,
                "generator_manifest_hash": generator_input.predecessor.manifest_hash,
                "checker_manifest_hash": package_integrity.predecessor_manifest.content_hash(),
            },
        )
        report = _early_report(
            generator_input,
            first,
            second,
            worker_source_result,
            replay_result,
            proposal_validation_result,
            certificate_result,
            selection_result,
            failed_realization,
            proposal=proposal,
            lean_report=lean_report,
        )
        return Phase5AReferenceLoopEvidence(generator_input, first, second, report)

    hardened_request = Phase4HardenedRequest(
        checker_request=checker_request,
        package_integrity=package_integrity,
    )
    hardened_report = check_hardened_transition(hardened_request)
    reasons: list[GeneratorReasonCode] = []
    if lean_report.bridge_verdict != "accept":
        reasons.append(GeneratorReasonCode.LEAN_VERIFICATION_FAILED)
    if not hardened_report.accepted:
        reasons.append(GeneratorReasonCode.CHECKER_REJECTED)
    unique_reasons = tuple(dict.fromkeys(reasons))
    if hardened_report.verdict == "indeterminate" or lean_report.bridge_verdict == "indeterminate":
        verdict = "indeterminate"
    elif unique_reasons:
        verdict = "reject"
    else:
        verdict = "accept"
    report = Phase5AReferenceLoopReport(
        transition_id=generator_input.transition_id,
        verdict=verdict,
        reason_codes=unique_reasons,
        worker_source_result=worker_source_result,
        first_process=first.report,
        second_process=second.report,
        replay_result=replay_result,
        proposal=proposal,
        proposal_validation_result=proposal_validation_result,
        certificate_construction_result=certificate_result,
        selection_result=selection_result,
        realization_result=realization_result,
        lean_bridge_report=lean_report,
        hardened_checker_report=hardened_report,
        artifact_hashes=_artifact_hashes(
            generator_input,
            first,
            second,
            proposal,
            certificate,
            candidate,
            lean_report,
            hardened_report,
            package_integrity.to_json(),
        ),
    )
    return Phase5AReferenceLoopEvidence(generator_input, first, second, report)


def _worker_source_result(
    first: GeneratorProcessEvidence,
    second: GeneratorProcessEvidence,
) -> GeneratorStageResult:
    clean = first.source_guard.clean and second.source_guard.clean
    same = first.source_guard.to_json() == second.source_guard.to_json()
    ok = clean and same
    return GeneratorStageResult.from_evidence(
        "pass" if ok else "fail",
        () if ok else (GeneratorReasonCode.WORKER_SOURCE_REJECTED,),
        {
            "first_guard": first.source_guard.to_json(),
            "second_guard": second.source_guard.to_json(),
            "clean": clean,
            "deterministic": same,
            "file_arguments_granted": [],
            "network_endpoints_granted": [],
            "write_handles_granted": [],
        },
    )


def _replay_result(
    first: GeneratorProcessEvidence,
    second: GeneratorProcessEvidence,
) -> GeneratorStageResult:
    process_success = (
        first.report.verdict == "success" and second.report.verdict == "success"
    )
    same_stdout = first.stdout == second.stdout
    same_stderr = first.stderr == second.stderr
    same_proposal = first.proposal == second.proposal
    same_report = first.report.to_json() == second.report.to_json()
    deterministic = same_stdout and same_stderr and same_proposal and same_report
    if process_success and deterministic:
        return GeneratorStageResult.from_evidence(
            "pass",
            (),
            {
                "process_success": True,
                "stdout_equal": True,
                "stderr_equal": True,
                "proposal_equal": True,
                "process_report_equal": True,
            },
        )
    reasons: list[GeneratorReasonCode] = []
    status = "fail"
    if first.report.timed_out or second.report.timed_out:
        status = "indeterminate"
        reasons.append(GeneratorReasonCode.PROCESS_TIMEOUT)
    elif not process_success:
        reasons.append(GeneratorReasonCode.PROCESS_FAILED)
    if not deterministic:
        reasons.append(GeneratorReasonCode.REPLAY_MISMATCH)
    return GeneratorStageResult.from_evidence(
        status,
        tuple(dict.fromkeys(reasons)),
        {
            "process_success": process_success,
            "stdout_equal": same_stdout,
            "stderr_equal": same_stderr,
            "proposal_equal": same_proposal,
            "process_report_equal": same_report,
        },
    )


def _construct_certificate(
    generator_input: ReferenceGeneratorInputRecord,
    proposal: ReferenceProposalRecord,
) -> tuple[RclmCertificatePacketRecord | None, GeneratorStageResult]:
    try:
        certificate_name = certificate_name_for_word(proposal.word)
        certificate = canonical_rclm_certificate(
            "gate_b_classical",
            certificate_name,
        )
    except (RuntimeValidationError, TypeError, ValueError) as exc:
        return None, GeneratorStageResult.from_evidence(
            "fail",
            (GeneratorReasonCode.CERTIFICATE_CONSTRUCTION_FAILED,),
            {"error_type": type(exc).__name__, "error": str(exc)},
        )
    return certificate, GeneratorStageResult.from_evidence(
        "pass",
        (),
        {
            "proposal_hash": proposal.proposal_hash,
            "certificate_name": certificate_name,
            "certificate": certificate.to_json(),
            "certificate_hash": canonical_json_hash(certificate.to_json()),
            "generator_certificate_field_consumed": False,
            "transition_id": generator_input.transition_id,
        },
    )


def _select_update(
    generator_input: ReferenceGeneratorInputRecord,
    proposal: ReferenceProposalRecord,
) -> tuple[RclmUpdateRecord | None, GeneratorStageResult]:
    try:
        update_name = update_name_for_proposal(proposal.proposal)
        core_update = ClassicalBinaryUpdateRecord(update_name)
        update = canonical_rclm_update(core_update)
    except (RuntimeValidationError, TypeError, ValueError) as exc:
        return None, GeneratorStageResult.from_evidence(
            "fail",
            (GeneratorReasonCode.SELECTION_FAILED,),
            {"error_type": type(exc).__name__, "error": str(exc)},
        )
    return update, GeneratorStageResult.from_evidence(
        "pass",
        (),
        {
            "selection_rule": "single_bounded_grammar_proposal",
            "proposal_hash": proposal.proposal_hash,
            "selected_update": update.to_json(),
            "selected_update_hash": canonical_json_hash(update.to_json()),
            "model_score_consumed": False,
            "reference_answer_consumed": False,
            "transition_id": generator_input.transition_id,
        },
    )


def _realize_candidate(
    generator_input: ReferenceGeneratorInputRecord,
    proposal: ReferenceProposalRecord,
    selected_update: RclmUpdateRecord | None,
) -> tuple[RclmCandidateRecord | None, GeneratorStageResult]:
    if selected_update is None:
        return None, GeneratorStageResult.from_evidence(
            "fail",
            (GeneratorReasonCode.REALIZATION_FAILED,),
            {"selected_update_present": False},
        )
    predecessor_core = generator_input.predecessor.state.core
    if not isinstance(predecessor_core, ClassicalBinaryStateRecord):
        return None, GeneratorStageResult.from_evidence(
            "fail",
            (GeneratorReasonCode.REALIZATION_FAILED,),
            {"predecessor_scope": type(predecessor_core).__name__},
        )
    core_update = selected_update.core
    if not isinstance(core_update, ClassicalBinaryUpdateRecord):
        return None, GeneratorStageResult.from_evidence(
            "fail",
            (GeneratorReasonCode.REALIZATION_FAILED,),
            {"update_scope": type(core_update).__name__},
        )
    successor_name = apply_binary_update(predecessor_core.state, core_update.update)
    successor = canonical_rclm_state(ClassicalBinaryStateRecord(successor_name))
    candidate = RclmCandidateRecord(update=selected_update, next=successor)
    return candidate, GeneratorStageResult.from_evidence(
        "pass",
        (),
        {
            "predecessor_state_hash": generator_input.predecessor.state_hash,
            "proposal_hash": proposal.proposal_hash,
            "applied_update": selected_update.to_json(),
            "derived_successor": successor.to_json(),
            "candidate": candidate.to_json(),
            "candidate_hash": canonical_json_hash(candidate.to_json()),
            "generator_successor_field_consumed": False,
            "manual_successor_output_consumed": False,
        },
    )


def _early_report(
    generator_input: ReferenceGeneratorInputRecord,
    first: GeneratorProcessEvidence,
    second: GeneratorProcessEvidence,
    worker_source_result: GeneratorStageResult,
    replay_result: GeneratorStageResult,
    proposal_validation_result: GeneratorStageResult,
    certificate_result: GeneratorStageResult,
    selection_result: GeneratorStageResult,
    realization_result: GeneratorStageResult,
    *,
    proposal: ReferenceProposalRecord | None = None,
    lean_report: LeanBridgeVerificationReport | None = None,
) -> Phase5AReferenceLoopReport:
    stages = (
        worker_source_result,
        replay_result,
        proposal_validation_result,
        certificate_result,
        selection_result,
        realization_result,
    )
    reasons = _stage_reasons(stages)
    if not reasons:
        reasons = (GeneratorReasonCode.INTERNAL_ERROR,)
    verdict = "indeterminate" if any(stage.status == "indeterminate" for stage in stages) else "reject"
    return Phase5AReferenceLoopReport(
        transition_id=generator_input.transition_id,
        verdict=verdict,
        reason_codes=reasons,
        worker_source_result=worker_source_result,
        first_process=first.report,
        second_process=second.report,
        replay_result=replay_result,
        proposal=proposal,
        proposal_validation_result=proposal_validation_result,
        certificate_construction_result=certificate_result,
        selection_result=selection_result,
        realization_result=realization_result,
        lean_bridge_report=lean_report,
        hardened_checker_report=None,
        artifact_hashes=_artifact_hashes(
            generator_input,
            first,
            second,
            proposal,
            None,
            None,
            lean_report,
            None,
            None,
        ),
    )


def _lean_error_report(
    generator_input: ReferenceGeneratorInputRecord,
    first: GeneratorProcessEvidence,
    second: GeneratorProcessEvidence,
    worker_source_result: GeneratorStageResult,
    replay_result: GeneratorStageResult,
    proposal: ReferenceProposalRecord,
    proposal_validation_result: GeneratorStageResult,
    certificate_result: GeneratorStageResult,
    selection_result: GeneratorStageResult,
    realization_result: GeneratorStageResult,
    error: Exception,
) -> Phase5AReferenceLoopReport:
    return Phase5AReferenceLoopReport(
        transition_id=generator_input.transition_id,
        verdict="reject",
        reason_codes=(GeneratorReasonCode.LEAN_VERIFICATION_FAILED,),
        worker_source_result=worker_source_result,
        first_process=first.report,
        second_process=second.report,
        replay_result=replay_result,
        proposal=proposal,
        proposal_validation_result=proposal_validation_result,
        certificate_construction_result=certificate_result,
        selection_result=selection_result,
        realization_result=realization_result,
        lean_bridge_report=None,
        hardened_checker_report=None,
        artifact_hashes=FrozenHashMap.from_mapping(
            {
                "generator_input": generator_input.input_hash,
                "first_stdout": first.report.stdout_hash,
                "second_stdout": second.report.stdout_hash,
                "lean_error": sha256_hex(str(error).encode("utf-8")),
            },
            "phase5a_reference_loop_report.artifact_hashes",
        ),
    )


def _artifact_hashes(
    generator_input: ReferenceGeneratorInputRecord,
    first: GeneratorProcessEvidence,
    second: GeneratorProcessEvidence,
    proposal: ReferenceProposalRecord | None,
    certificate: RclmCertificatePacketRecord | None,
    candidate: RclmCandidateRecord | None,
    lean_report: LeanBridgeVerificationReport | None,
    hardened_report: Phase4HardenedReport | None,
    package_integrity_json: object | None,
) -> FrozenHashMap:
    values: dict[str, str] = {
        "generator_input": generator_input.input_hash,
        "worker_source_guard": first.source_guard.report_hash,
        "first_process_report": canonical_json_hash(first.report.to_json()),
        "second_process_report": canonical_json_hash(second.report.to_json()),
        "first_stdout": first.report.stdout_hash,
        "second_stdout": second.report.stdout_hash,
    }
    if proposal is not None:
        values["proposal"] = proposal.proposal_hash
    if certificate is not None:
        values["certificate"] = canonical_json_hash(certificate.to_json())
    if candidate is not None:
        values["candidate"] = canonical_json_hash(candidate.to_json())
    if lean_report is not None:
        values["lean_bridge_report"] = lean_report.report_hash
    if hardened_report is not None:
        values["hardened_checker_report"] = hardened_report.report_hash
    if package_integrity_json is not None:
        values["package_integrity"] = canonical_json_hash(package_integrity_json)
    return FrozenHashMap.from_mapping(
        values,
        "phase5a_reference_loop_report.artifact_hashes",
    )


def _stage_reasons(
    stages: Sequence[GeneratorStageResult],
) -> Sequence[GeneratorReasonCode]:
    return tuple(
        dict.fromkeys(
            reason
            for stage in stages
            for reason in stage.reason_codes
        )
    )


def _not_evaluated() -> GeneratorStageResult:
    return GeneratorStageResult.from_evidence("not_evaluated", (), {})
