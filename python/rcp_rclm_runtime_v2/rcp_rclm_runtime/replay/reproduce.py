from __future__ import annotations

import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
    sha256_hex,
    validate_hash256,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.checker.hardened import (
    Phase4HardenedRequest,
    check_hardened_transition,
)
from rcp_rclm_runtime.checker.integrity import (
    PackageIntegrityRecord,
    build_reference_package_integrity,
)
from rcp_rclm_runtime.checker.records import Phase3CheckerRequest
from rcp_rclm_runtime.checker.reference import (
    build_lean_reference_packet,
    reference_protected_distinctions,
    reference_resource_record,
    reference_trust_anchor,
)
from rcp_rclm_runtime.errors import CanonicalizationError, SchemaValidationError
from rcp_rclm_runtime.generator.grammar import validate_untrusted_proposal
from rcp_rclm_runtime.generator.protocol import (
    GeneratorPredecessorViewRecord,
    GeneratorReasonCode,
    ProcessVerdict,
    ReferenceGeneratorInputRecord,
    ReferenceProposalRecord,
)
from rcp_rclm_runtime.generator.records import GeneratorProcessReport
from rcp_rclm_runtime.generator.reference import reference_generator_input
from rcp_rclm_runtime.lean_bridge.packet import LeanReferencePacket
from rcp_rclm_runtime.lean_bridge.source_generator import generate_reference_source
from rcp_rclm_runtime.lean_bridge.source_guard import scan_source_bytes
from rcp_rclm_runtime.lean_bridge.verifier import (
    LeanBridgeVerificationEvidence,
    LeanBridgeVerificationReport,
)
from rcp_rclm_runtime.promotion.certificate import construct_reference_certificate
from rcp_rclm_runtime.promotion.evaluator import evaluate_realized_candidate
from rcp_rclm_runtime.promotion.policy import (
    PHASE7_CONTROLLER_ENVIRONMENT_HASH,
    reference_phase7_policy,
)
from rcp_rclm_runtime.promotion.records import (
    Phase7AttemptReport,
    Phase7ControllerPolicyRecord,
    Phase7ControllerReport,
    Phase7ImmutablePackageManifestRecord,
    Phase7ReasonCode,
)
from rcp_rclm_runtime.promotion.store import verify_immutable_phase7_package
from rcp_rclm_runtime.schema._common import (
    require_schema_id,
    require_string,
    require_structural_integer,
    strict_object,
)
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.successor.package_builder import (
    build_candidate_package,
    verify_candidate_package,
)
from rcp_rclm_runtime.successor.records import (
    Phase6PackageReport,
    Phase6SelectionRecord,
)
from rcp_rclm_runtime.successor.rollback_io import verify_rollback_snapshot_archive
from rcp_rclm_runtime.successor.selector import (
    Phase6SelectionError,
    select_reference_successor,
)
from rcp_rclm_runtime.successor.workspace import load_predecessor_package, write_canonical_json
from rcp_rclm_runtime.replay.bundle import (
    PHASE8_STORE_DIRECTORY_NAME,
    Phase8BundleError,
    verify_phase8_replay_bundle,
)
from rcp_rclm_runtime.replay.guard import guard_independent_replay_source
from rcp_rclm_runtime.replay.records import (
    Phase8AttemptIndexRecord,
    Phase8AttemptReplayReport,
    Phase8ReasonCode,
    Phase8ReplayReport,
    Phase8StageResult,
    ReplayVerdict,
)

LeanVerifierCallable = Callable[[LeanReferencePacket], LeanBridgeVerificationEvidence]

_STAGE_ORDER: Final[Sequence[str]] = (
    "source_binding",
    "generator_evidence",
    "proposal_validation",
    "selection_outcome",
    "realization_outcome",
    "evaluation_outcome",
    "certificate_outcome",
    "lean_outcome",
    "checker_outcome",
    "resource_outcome",
    "rollback_outcome",
    "parent_link",
)


@dataclass(frozen=True, slots=True)
class Phase8ReplayEvidence:
    report: Phase8ReplayReport
    output_root: Path | None


class _ReplayAttemptError(ValueError):
    __slots__ = ("stage", "reason", "detail", "indeterminate")

    def __init__(
        self,
        stage: str,
        reason: Phase8ReasonCode,
        detail: str,
        *,
        indeterminate: bool = False,
    ) -> None:
        super().__init__(stage, reason.value, detail)
        self.stage = stage
        self.reason = reason
        self.detail = detail
        self.indeterminate = indeterminate


@dataclass(frozen=True, slots=True)
class _AttemptSource:
    index: Phase8AttemptIndexRecord
    package_root: Path
    predecessor_root: Path
    attempt_root: Path
    evidence_root: Path
    controller: Phase7ControllerReport
    attempt: Phase7AttemptReport


def reproduce_phase8_bundle(
    bundle_root: Path,
    output_root: Path,
    verify_lean: LeanVerifierCallable,
    *,
    policy: Phase7ControllerPolicyRecord | None = None,
) -> Phase8ReplayEvidence:
    resolved_policy = policy or reference_phase7_policy()
    resolved_output = output_root.resolve(strict=False)
    if resolved_output.exists():
        raise FileExistsError(f"replay output already exists: {resolved_output}")
    source_guard = guard_independent_replay_source()
    if not source_guard.clean:
        report = _source_guard_failure_report(source_guard.report_hash)
        return Phase8ReplayEvidence(report=report, output_root=None)
    try:
        manifest = verify_phase8_replay_bundle(bundle_root, policy=resolved_policy)
    except Phase8BundleError as exc:
        report = _bundle_failure_report(exc)
        return Phase8ReplayEvidence(report=report, output_root=None)
    bundle = bundle_root.resolve(strict=True)
    store_root = bundle / PHASE8_STORE_DIRECTORY_NAME
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix="rcp-rclm-phase8-replay-",
            dir=resolved_output.parent,
        ) as temporary_directory:
            staging = Path(temporary_directory) / "replay"
            staging.mkdir(parents=True, exist_ok=False)
            attempt_reports: list[Phase8AttemptReplayReport] = []
            for index in manifest.attempts:
                attempt_output = staging / "attempts" / f"{index.ledger_sequence_number:04d}"
                attempt_output.mkdir(parents=True, exist_ok=False)
                attempt_reports.append(
                    _replay_attempt(
                        store_root,
                        index,
                        attempt_output,
                        verify_lean,
                        resolved_policy,
                    )
                )
            reasons = tuple(
                dict.fromkeys(
                    reason
                    for attempt in attempt_reports
                    for reason in attempt.reason_codes
                )
            )
            if any(attempt.verdict == "reject" for attempt in attempt_reports):
                verdict = "reject"
            elif any(attempt.verdict == "indeterminate" for attempt in attempt_reports):
                verdict = "indeterminate"
            else:
                verdict = "accept"
            if verdict != "accept" and not reasons:
                reasons = (Phase8ReasonCode.INTERNAL_ERROR,)
            write_canonical_json(staging / "replay_source_guard.json", source_guard.to_json())
            artifact_hashes = {
                "bundle_manifest": manifest.manifest_hash,
                "replay_source_guard": source_guard.report_hash,
                "source_store_tree": manifest.source_store_tree_hash,
            }
            for attempt in attempt_reports:
                artifact_hashes[
                    f"attempt_{attempt.ledger_sequence_number:04d}"
                ] = attempt.report_hash
            report = Phase8ReplayReport(
                replay_id=manifest.replay_id,
                bundle_manifest_hash=manifest.manifest_hash,
                verdict=cast(ReplayVerdict, verdict),
                reason_codes=reasons,
                package_chain=manifest.package_chain,
                attempts=tuple(attempt_reports),
                generator_invocations=0,
                artifact_hashes=FrozenHashMap.from_mapping(
                    artifact_hashes,
                    "phase8_replay_report.artifact_hashes",
                ),
            )
            write_canonical_json(staging / "replay_report.json", report.to_json())
            os.replace(staging, resolved_output)
            return Phase8ReplayEvidence(report=report, output_root=resolved_output)
    except (
        CanonicalizationError,
        SchemaValidationError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        report = _internal_failure_report(manifest.replay_id, manifest.manifest_hash, exc)
        return Phase8ReplayEvidence(report=report, output_root=None)


def _replay_attempt(
    store_root: Path,
    index: Phase8AttemptIndexRecord,
    output_root: Path,
    verify_lean: LeanVerifierCallable,
    policy: Phase7ControllerPolicyRecord,
) -> Phase8AttemptReplayReport:
    stages: list[Phase8StageResult] = []
    recomputed: dict[str, str] = {}
    try:
        source = _load_attempt_source(store_root, index, policy)
        _verify_index_artifacts(source)
        _append_pass(
            stages,
            "source_binding",
            {
                "ledger_entry_hash": index.ledger_entry_hash,
                "attempt_report_hash": index.attempt_report_hash,
                "controller_report_hash": index.controller_report_hash,
                "predecessor_package_hash": index.predecessor_package_hash,
                "successor_package_hash": index.successor_package_hash,
            },
        )
        generator_input, proposal = _replay_generator_evidence(source)
        recomputed["generator_input"] = generator_input.input_hash
        recomputed["proposal"] = proposal.proposal_hash
        _append_pass(
            stages,
            "generator_evidence",
            {
                "generator_invocations": 0,
                "generator_input_hash": generator_input.input_hash,
                "proposal_hash": proposal.proposal_hash,
                "raw_outputs_equal": True,
                "raw_inputs_equal": True,
                "source_guards_clean": True,
            },
        )
        proposal_result = validate_untrusted_proposal(generator_input, proposal)
        if proposal_result.status != "pass":
            raise _ReplayAttemptError(
                "proposal_validation",
                Phase8ReasonCode.PROPOSAL_VALIDATION_FAILED,
                "stored proposal does not validate against the reconstructed public input",
            )
        _append_pass(
            stages,
            "proposal_validation",
            {
                "proposal_hash": proposal.proposal_hash,
                "candidate_successor_field_consumed": False,
                "certificate_field_consumed": False,
                "acceptance_field_consumed": False,
            },
        )
        predecessor = load_predecessor_package(source.predecessor_root)
        try:
            selection = select_reference_successor(generator_input, proposal, predecessor)
        except Phase6SelectionError as exc:
            if index.selection_hash is not None or index.ledger_event == "promotion":
                raise _ReplayAttemptError(
                    "selection_outcome",
                    Phase8ReasonCode.SELECTION_REPLAY_MISMATCH,
                    f"fresh selection failed but the source attempt selected a candidate: {exc}",
                ) from exc
            if Phase7ReasonCode.SELECTION_FAILED not in source.attempt.reason_codes:
                raise _ReplayAttemptError(
                    "selection_outcome",
                    Phase8ReasonCode.REJECTION_REPLAY_MISMATCH,
                    "fresh selection failure does not match the source reason code",
                ) from exc
            _append_pass(
                stages,
                "selection_outcome",
                {
                    "source_outcome": "reject",
                    "recomputed_outcome": "reject",
                    "selection_error_code": exc.reason_code.value,
                    "detail_hash": sha256_hex(exc.detail.encode("utf-8")),
                },
            )
            for stage in (
                "realization_outcome",
                "evaluation_outcome",
                "certificate_outcome",
                "lean_outcome",
                "checker_outcome",
                "resource_outcome",
                "rollback_outcome",
            ):
                _append_pass(
                    stages,
                    stage,
                    {
                        "source_not_evaluated": True,
                        "replay_not_evaluated": True,
                    },
                )
            _verify_parent_link(source, policy)
            _append_pass(
                stages,
                "parent_link",
                {
                    "promotion": False,
                    "active_package_preserved": True,
                },
            )
            return _accepted_attempt_report(source, stages, recomputed)
        if index.selection_hash is None:
            raise _ReplayAttemptError(
                "selection_outcome",
                Phase8ReasonCode.SELECTION_REPLAY_MISMATCH,
                "fresh selection succeeded but the source attempt recorded a selection failure",
            )
        stored_selection = Phase6SelectionRecord.from_json(
            _read_json(source.evidence_root / "selection.json")
        )
        if selection != stored_selection or selection.selection_hash != index.selection_hash:
            raise _ReplayAttemptError(
                "selection_outcome",
                Phase8ReasonCode.SELECTION_REPLAY_MISMATCH,
                "recomputed selection differs from the captured selection",
            )
        recomputed["selection"] = selection.selection_hash
        _append_pass(
            stages,
            "selection_outcome",
            {
                "selection_hash": selection.selection_hash,
                "operation_count": len(selection.operations),
                "substantive_component_kinds": list(selection.substantive_component_kinds),
            },
        )
        replay_candidate = output_root / "candidate"
        phase6 = build_candidate_package(
            source.predecessor_root,
            selection,
            source.controller.budget.phase6_budget,
            replay_candidate,
        )
        if not phase6.report.built or phase6.output_root is None:
            raise _ReplayAttemptError(
                "realization_outcome",
                Phase8ReasonCode.REALIZATION_REPLAY_MISMATCH,
                "fresh Phase 6 realization did not build a candidate",
            )
        replay_manifest = verify_candidate_package(replay_candidate)
        replay_tree_hash = _tree_hash(replay_candidate)
        source_candidate = source.attempt_root / "candidate"
        source_manifest = verify_candidate_package(source_candidate)
        source_tree_hash = _tree_hash(source_candidate)
        stored_phase6 = Phase6PackageReport.from_json(
            _read_json(source.evidence_root / "phase6_report.json")
        )
        if (
            phase6.report != stored_phase6
            or phase6.report.report_hash != index.phase6_report_hash
            or replay_manifest != source_manifest
            or replay_tree_hash != source_tree_hash
            or replay_tree_hash != index.candidate_package_tree_hash
        ):
            raise _ReplayAttemptError(
                "realization_outcome",
                Phase8ReasonCode.REALIZATION_REPLAY_MISMATCH,
                "fresh candidate package differs from the captured candidate package",
            )
        recomputed["phase6_report"] = phase6.report.report_hash
        recomputed["candidate_package_tree"] = replay_tree_hash
        _append_pass(
            stages,
            "realization_outcome",
            {
                "phase6_report_hash": phase6.report.report_hash,
                "candidate_manifest_hash": replay_manifest.manifest_hash,
                "candidate_payload_tree_hash": replay_manifest.payload_tree_hash,
                "candidate_package_tree_hash": replay_tree_hash,
            },
        )
        evaluation = evaluate_realized_candidate(
            source.predecessor_root,
            replay_candidate,
            selection,
        )
        stored_evaluation = _read_json(source.evidence_root / "evaluation.json")
        if evaluation.to_json() != stored_evaluation or evaluation.evaluation_hash != index.evaluation_hash:
            raise _ReplayAttemptError(
                "evaluation_outcome",
                Phase8ReasonCode.EVALUATION_REPLAY_MISMATCH,
                "recomputed objective evidence differs from the captured evaluation",
            )
        recomputed["evaluation"] = evaluation.evaluation_hash
        _append_pass(
            stages,
            "evaluation_outcome",
            {
                "evaluation_hash": evaluation.evaluation_hash,
                "candidate_assertions_authoritative": False,
                "controller_mathematical_acceptance_calculated": False,
            },
        )
        certificate = construct_reference_certificate(proposal)
        stored_certificate = _read_json(source.evidence_root / "certificate.json")
        if certificate.to_json() != stored_certificate or certificate.certificate_hash != index.certificate_hash:
            raise _ReplayAttemptError(
                "certificate_outcome",
                Phase8ReasonCode.CERTIFICATE_REPLAY_MISMATCH,
                "reconstructed certificate differs from the captured certificate",
            )
        recomputed["certificate"] = certificate.certificate_hash
        _append_pass(
            stages,
            "certificate_outcome",
            {
                "certificate_hash": certificate.certificate_hash,
                "certificate_name": certificate.certificate_name,
                "generator_certificate_field_consumed": False,
            },
        )
        packet = build_lean_reference_packet(
            evaluation.predecessor.state,
            evaluation.candidate,
            certificate.certificate,
        )
        expected_generated = generate_reference_source(packet)
        captured_source = source.evidence_root / "generated_certificate.lean"
        captured_source_bytes = captured_source.read_bytes()
        captured_generated_record = _read_json(
            source.evidence_root / "generated_source.json"
        )
        captured_guard_record = _read_json(
            source.evidence_root / "lean_source_guard.json"
        )
        recomputed_guard = scan_source_bytes(captured_source_bytes)
        if (
            captured_source_bytes != expected_generated.source_bytes
            or captured_generated_record != expected_generated.to_json()
            or captured_guard_record != recomputed_guard.to_json()
            or not recomputed_guard.clean
        ):
            raise _ReplayAttemptError(
                "lean_outcome",
                Phase8ReasonCode.LEAN_REPLAY_FAILED,
                "captured generated Lean source or source-guard evidence does not recompute",
            )
        replay_lean = _invoke_lean(verify_lean, packet)
        _write_lean_evidence(output_root / "lean", replay_lean)
        source_request = Phase3CheckerRequest.from_json(
            _read_json(source.evidence_root / "checker_request.json")
        )
        source_lean = source_request.lean_bridge_report
        if (
            source_lean.generated_source_hash != expected_generated.source_hash
            or source_lean.source_guard_hash != canonical_json_hash(recomputed_guard.to_json())
        ):
            raise _ReplayAttemptError(
                "lean_outcome",
                Phase8ReasonCode.LEAN_REPLAY_FAILED,
                "captured Lean report is not bound to the recomputed source and source guard",
            )
        if replay_lean.report.bridge_verdict == "indeterminate" or replay_lean.report.timed_out:
            raise _ReplayAttemptError(
                "lean_outcome",
                Phase8ReasonCode.LEAN_REPLAY_FAILED,
                "independent Lean replay was indeterminate",
                indeterminate=True,
            )
        if replay_lean.report.bridge_verdict != "accept":
            raise _ReplayAttemptError(
                "lean_outcome",
                Phase8ReasonCode.LEAN_REPLAY_FAILED,
                "independent Lean replay rejected the packet",
            )
        if _lean_semantic_fingerprint(replay_lean.report) != _lean_semantic_fingerprint(source_lean):
            raise _ReplayAttemptError(
                "lean_outcome",
                Phase8ReasonCode.LEAN_REPLAY_FAILED,
                "independent Lean replay differs from the captured semantic verdict",
            )
        recomputed["lean_report"] = replay_lean.report.report_hash
        recomputed["lean_semantic_fingerprint"] = _lean_semantic_fingerprint(replay_lean.report)
        _append_pass(
            stages,
            "lean_outcome",
            {
                "source_lean_report_hash": source_lean.report_hash,
                "replay_lean_report_hash": replay_lean.report.report_hash,
                "semantic_fingerprint": _lean_semantic_fingerprint(replay_lean.report),
                "captured_generated_source_hash": expected_generated.source_hash,
                "replay_generated_source_hash": replay_lean.report.generated_source_hash,
                "captured_source_guard_hash": canonical_json_hash(recomputed_guard.to_json()),
                "source_guard_clean": replay_lean.source_guard.clean and recomputed_guard.clean,
            },
        )
        units_consumed = sum(
            attempt.controller_units_consumed
            for attempt in source.controller.attempts
            if attempt.attempt_index <= source.attempt.attempt_index
        )
        resource_record = reference_resource_record(
            budget_units=source.controller.budget.max_attempt_units,
            consumed_units=units_consumed,
            environment_hash=PHASE7_CONTROLLER_ENVIRONMENT_HASH,
        )
        expected_request_without_lean = {
            "transition_id": generator_input.transition_id,
            "predecessor": evaluation.predecessor.state.to_json(),
            "candidate": evaluation.candidate.to_json(),
            "certificate": certificate.certificate.to_json(),
            "trust_anchor": reference_trust_anchor().to_json(),
            "resource_record": resource_record.to_json(),
            "protected_distinctions": [
                item.to_json()
                for item in reference_protected_distinctions("gate_b_classical")
            ],
            "evaluation_evidence": evaluation.evaluation.to_json(),
        }
        source_request_json = source_request.to_json()
        for key, expected in expected_request_without_lean.items():
            if source_request_json[key] != expected:
                raise _ReplayAttemptError(
                    "checker_outcome",
                    Phase8ReasonCode.CHECKER_REPLAY_MISMATCH,
                    f"captured checker request differs at {key}",
                )
        source_integrity = PackageIntegrityRecord.from_json(
            _read_json(source.evidence_root / "package_integrity.json")
        )
        rebuilt_source_integrity = build_reference_package_integrity(source_request)
        if source_integrity != rebuilt_source_integrity:
            raise _ReplayAttemptError(
                "checker_outcome",
                Phase8ReasonCode.CHECKER_REPLAY_MISMATCH,
                "captured package-integrity evidence does not recompute",
            )
        source_hardened = check_hardened_transition(
            Phase4HardenedRequest(source_request, source_integrity)
        )
        stored_hardened = _read_json(source.evidence_root / "hardened_checker_report.json")
        if source_hardened.to_json() != stored_hardened or source_hardened.report_hash != index.checker_report_hash:
            raise _ReplayAttemptError(
                "checker_outcome",
                Phase8ReasonCode.CHECKER_REPLAY_MISMATCH,
                "captured hardened-checker result does not recompute from captured inputs",
            )
        replay_request = Phase3CheckerRequest(
            transition_id=generator_input.transition_id,
            predecessor=evaluation.predecessor.state,
            candidate=evaluation.candidate,
            certificate=certificate.certificate,
            trust_anchor=reference_trust_anchor(),
            resource_record=resource_record,
            protected_distinctions=reference_protected_distinctions("gate_b_classical"),
            evaluation_evidence=evaluation.evaluation,
            lean_bridge_report=replay_lean.report,
        )
        replay_integrity = build_reference_package_integrity(replay_request)
        replay_hardened = check_hardened_transition(
            Phase4HardenedRequest(replay_request, replay_integrity)
        )
        if not source_hardened.accepted or not replay_hardened.accepted:
            raise _ReplayAttemptError(
                "checker_outcome",
                Phase8ReasonCode.CHECKER_REPLAY_MISMATCH,
                "source or independent hardened checker did not accept",
            )
        if _checker_semantic_fingerprint(source_hardened) != _checker_semantic_fingerprint(replay_hardened):
            raise _ReplayAttemptError(
                "checker_outcome",
                Phase8ReasonCode.CHECKER_REPLAY_MISMATCH,
                "independent checker result differs from the captured mathematical result",
            )
        recomputed["source_hardened_checker"] = source_hardened.report_hash
        recomputed["replay_hardened_checker"] = replay_hardened.report_hash
        recomputed["checker_semantic_fingerprint"] = _checker_semantic_fingerprint(replay_hardened)
        _append_pass(
            stages,
            "checker_outcome",
            {
                "source_checker_report_hash": source_hardened.report_hash,
                "replay_checker_report_hash": replay_hardened.report_hash,
                "semantic_fingerprint": _checker_semantic_fingerprint(replay_hardened),
                "checker_accepted": True,
                "controller_authoritative_math_calculated": False,
            },
        )
        source_resources = (source.attempt_root / "candidate" / "evidence" / "resources.json")
        replay_resources = replay_candidate / "evidence" / "resources.json"
        if source_resources.read_bytes() != replay_resources.read_bytes():
            raise _ReplayAttemptError(
                "resource_outcome",
                Phase8ReasonCode.RESOURCE_REPLAY_MISMATCH,
                "independently realized resource evidence differs from the source",
            )
        recomputed["resource_usage"] = sha256_hex(replay_resources.read_bytes())
        _append_pass(
            stages,
            "resource_outcome",
            {
                "resource_usage_hash": recomputed["resource_usage"],
                "budget_hash": source.controller.budget.budget_hash,
                "generator_invocations": 0,
            },
        )
        replay_rollback_record = _read_json(replay_candidate / "evidence" / "rollback.json")
        source_rollback_record = _read_json(
            source.attempt_root / "candidate" / "evidence" / "rollback.json"
        )
        if replay_rollback_record != source_rollback_record:
            raise _ReplayAttemptError(
                "rollback_outcome",
                Phase8ReasonCode.ROLLBACK_REPLAY_MISMATCH,
                "independently realized rollback record differs from the source",
            )
        archive = replay_candidate / "rollback" / "predecessor.tar"
        expected_tree = require_string(
            replay_rollback_record["predecessor_tree_hash"],
            "phase8.rollback.predecessor_tree_hash",
        )
        validate_hash256(expected_tree, "phase8.rollback.predecessor_tree_hash")
        restored_tree = verify_rollback_snapshot_archive(archive, expected_tree)
        if restored_tree != expected_tree:
            raise _ReplayAttemptError(
                "rollback_outcome",
                Phase8ReasonCode.ROLLBACK_REPLAY_MISMATCH,
                "rollback archive did not restore the predecessor tree",
            )
        recomputed["rollback_record"] = sha256_hex(
            canonical_json_bytes(replay_rollback_record)
        )
        recomputed["rollback_archive"] = sha256_hex(archive.read_bytes())
        _append_pass(
            stages,
            "rollback_outcome",
            {
                "rollback_record_hash": recomputed["rollback_record"],
                "rollback_archive_hash": recomputed["rollback_archive"],
                "restored_tree_hash": restored_tree,
                "verified": True,
            },
        )
        _verify_parent_link(source, policy)
        _append_pass(
            stages,
            "parent_link",
            {
                "promotion": True,
                "parent_package_hash": index.predecessor_package_hash,
                "successor_package_hash": index.successor_package_hash,
            },
        )
        return _accepted_attempt_report(source, stages, recomputed)
    except _ReplayAttemptError as exc:
        if not stages or stages[-1].stage != exc.stage:
            stages.append(
                Phase8StageResult.build(
                    exc.stage,
                    "indeterminate" if exc.indeterminate else "fail",
                    (exc.reason,),
                    {
                        "detail_hash": sha256_hex(exc.detail.encode("utf-8")),
                        "error_type": type(exc).__name__,
                    },
                )
            )
        while len(stages) < len(_STAGE_ORDER):
            stage = _STAGE_ORDER[len(stages)]
            stages.append(Phase8StageResult.build(stage, "not_evaluated", (), {}))
        verdict = "indeterminate" if exc.indeterminate else "reject"
        return Phase8AttemptReplayReport(
            ledger_sequence_number=index.ledger_sequence_number,
            run_id=index.run_id,
            attempt_index=index.attempt_index,
            source_attempt_report_hash=index.attempt_report_hash,
            source_ledger_entry_hash=index.ledger_entry_hash,
            verdict=cast(ReplayVerdict, verdict),
            reason_codes=(exc.reason,),
            generator_invocations=0,
            stages=tuple(stages),
            recomputed_hashes=FrozenHashMap.from_mapping(
                recomputed,
                "phase8_attempt_report.recomputed_hashes",
            ),
        )
    except Exception as exc:
        stage = _STAGE_ORDER[min(len(stages), len(_STAGE_ORDER) - 1)]
        stages.append(
            Phase8StageResult.build(
                stage,
                "fail",
                (Phase8ReasonCode.INTERNAL_ERROR,),
                {
                    "error_type": type(exc).__name__,
                    "detail_hash": sha256_hex(str(exc).encode("utf-8")),
                },
            )
        )
        while len(stages) < len(_STAGE_ORDER):
            stage = _STAGE_ORDER[len(stages)]
            stages.append(Phase8StageResult.build(stage, "not_evaluated", (), {}))
        return Phase8AttemptReplayReport(
            ledger_sequence_number=index.ledger_sequence_number,
            run_id=index.run_id,
            attempt_index=index.attempt_index,
            source_attempt_report_hash=index.attempt_report_hash,
            source_ledger_entry_hash=index.ledger_entry_hash,
            verdict="reject",
            reason_codes=(Phase8ReasonCode.INTERNAL_ERROR,),
            generator_invocations=0,
            stages=tuple(stages),
            recomputed_hashes=FrozenHashMap.from_mapping(
                recomputed,
                "phase8_attempt_report.recomputed_hashes",
            ),
        )


def _load_attempt_source(
    store_root: Path,
    index: Phase8AttemptIndexRecord,
    policy: Phase7ControllerPolicyRecord,
) -> _AttemptSource:
    package_root = store_root / "packages" / index.predecessor_package_hash
    package_manifest = verify_immutable_phase7_package(package_root, policy)
    if package_manifest.package_hash != index.predecessor_package_hash:
        raise _ReplayAttemptError(
            "source_binding",
            Phase8ReasonCode.PACKAGE_CHAIN_MISMATCH,
            "predecessor package directory does not verify to its indexed hash",
        )
    predecessor_root = package_root / "predecessor"
    run_root = store_root / "runs" / index.run_id
    controller_path = run_root / "controller_report.json"
    controller = Phase7ControllerReport.from_json(_read_json(controller_path))
    matches = [
        attempt
        for attempt in controller.attempts
        if attempt.report_hash == index.attempt_report_hash
    ]
    if len(matches) != 1:
        raise _ReplayAttemptError(
            "source_binding",
            Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
            "indexed attempt hash does not identify exactly one controller attempt",
        )
    attempt = matches[0]
    if attempt.attempt_index != index.attempt_index or attempt.verdict != index.attempt_verdict:
        raise _ReplayAttemptError(
            "source_binding",
            Phase8ReasonCode.LEDGER_CHAIN_MISMATCH,
            "indexed attempt metadata differs from the source controller report",
        )
    attempt_root = run_root / f"attempt-{attempt.attempt_index:04d}"
    evidence_root = attempt_root / "evidence"
    observed_attempt = Phase7AttemptReport.from_json(
        _read_json(evidence_root / "attempt_report.json")
    )
    if observed_attempt != attempt or controller.report_hash != index.controller_report_hash:
        raise _ReplayAttemptError(
            "source_binding",
            Phase8ReasonCode.BUNDLE_HASH_MISMATCH,
            "captured controller or attempt report differs from its index",
        )
    return _AttemptSource(
        index=index,
        package_root=package_root,
        predecessor_root=predecessor_root,
        attempt_root=attempt_root,
        evidence_root=evidence_root,
        controller=controller,
        attempt=attempt,
    )


def _verify_index_artifacts(source: _AttemptSource) -> None:
    expected = source.index.artifact_hashes.to_json()
    observed: dict[str, str] = {}
    path_map = {
        "attempt_report": source.evidence_root / "attempt_report.json",
        "controller_report": source.attempt_root.parent / "controller_report.json",
        "first_generator_input": source.evidence_root / "first_generator_input.json",
        "first_generator_stderr": source.evidence_root / "first_generator_stderr.bin",
        "first_generator_stdout": source.evidence_root / "first_generator_stdout.bin",
        "first_process_report": source.evidence_root / "first_process_report.json",
        "first_source_guard": source.evidence_root / "first_source_guard.json",
        "generator_input": source.evidence_root / "generator_input.json",
        "proposal": source.evidence_root / "proposal.json",
        "second_generator_input": source.evidence_root / "second_generator_input.json",
        "second_generator_stderr": source.evidence_root / "second_generator_stderr.bin",
        "second_generator_stdout": source.evidence_root / "second_generator_stdout.bin",
        "second_process_report": source.evidence_root / "second_process_report.json",
        "second_source_guard": source.evidence_root / "second_source_guard.json",
        "selection": source.evidence_root / "selection.json",
        "phase6_report": source.evidence_root / "phase6_report.json",
        "evaluation": source.evidence_root / "evaluation.json",
        "certificate": source.evidence_root / "certificate.json",
        "generated_lean_source": source.evidence_root / "generated_certificate.lean",
        "generated_source_record": source.evidence_root / "generated_source.json",
        "lean_source_guard": source.evidence_root / "lean_source_guard.json",
        "lean_report": source.evidence_root / "lean_report.json",
        "lean_compilation": source.evidence_root / "lean_compilation.json",
        "lean_stdout": source.evidence_root / "lean_stdout.bin",
        "lean_stderr": source.evidence_root / "lean_stderr.bin",
        "parsed_lean_verdict": source.evidence_root / "parsed_lean_verdict.json",
        "checker_request": source.evidence_root / "checker_request.json",
        "package_integrity": source.evidence_root / "package_integrity.json",
        "hardened_checker_report": source.evidence_root / "hardened_checker_report.json",
        "resource_usage": source.attempt_root / "candidate" / "evidence" / "resources.json",
        "rollback_record": source.attempt_root / "candidate" / "evidence" / "rollback.json",
        "rollback_archive": source.attempt_root / "candidate" / "rollback" / "predecessor.tar",
    }
    for key in expected:
        if key == "candidate_package_tree":
            candidate = source.attempt_root / "candidate"
            if not candidate.is_dir():
                raise _ReplayAttemptError(
                    "source_binding",
                    Phase8ReasonCode.BUNDLE_LAYOUT_INVALID,
                    "indexed candidate tree is absent",
                )
            observed[key] = _tree_hash(candidate)
            continue
        path = path_map.get(key)
        if path is None or path.is_symlink() or not path.is_file():
            raise _ReplayAttemptError(
                "source_binding",
                Phase8ReasonCode.BUNDLE_LAYOUT_INVALID,
                f"indexed artifact is absent or unsupported: {key}",
            )
        observed[key] = sha256_hex(path.read_bytes())
    if observed != expected:
        raise _ReplayAttemptError(
            "source_binding",
            Phase8ReasonCode.BUNDLE_HASH_MISMATCH,
            "captured artifact bytes differ from the replay manifest",
        )


def _replay_generator_evidence(
    source: _AttemptSource,
) -> tuple[ReferenceGeneratorInputRecord, ReferenceProposalRecord]:
    canonical_input = source.evidence_root / "generator_input.json"
    first_input = source.evidence_root / "first_generator_input.json"
    second_input = source.evidence_root / "second_generator_input.json"
    input_bytes = canonical_input.read_bytes()
    if first_input.read_bytes() != input_bytes or second_input.read_bytes() != input_bytes:
        raise _ReplayAttemptError(
            "generator_evidence",
            Phase8ReasonCode.GENERATOR_REPLAY_MISMATCH,
            "captured generator inputs are not byte-identical",
        )
    generator_input = ReferenceGeneratorInputRecord.from_json(
        load_json_strict(input_bytes, require_canonical=True)
    )
    expected_input = _generator_input_from_predecessor(source.predecessor_root)
    if generator_input != expected_input or generator_input.input_hash != source.index.generator_input_hash:
        raise _ReplayAttemptError(
            "generator_evidence",
            Phase8ReasonCode.GENERATOR_INPUT_MISMATCH,
            "captured generator input differs from the independently reconstructed input",
        )
    first_stdout = (source.evidence_root / "first_generator_stdout.bin").read_bytes()
    second_stdout = (source.evidence_root / "second_generator_stdout.bin").read_bytes()
    first_stderr = (source.evidence_root / "first_generator_stderr.bin").read_bytes()
    second_stderr = (source.evidence_root / "second_generator_stderr.bin").read_bytes()
    if first_stdout != second_stdout or first_stderr != second_stderr:
        raise _ReplayAttemptError(
            "generator_evidence",
            Phase8ReasonCode.GENERATOR_REPLAY_MISMATCH,
            "captured generator process outputs are not deterministic",
        )
    if first_stderr:
        raise _ReplayAttemptError(
            "generator_evidence",
            Phase8ReasonCode.GENERATOR_OUTPUT_MALFORMED,
            "captured successful generator emitted stderr",
        )
    try:
        proposal = ReferenceProposalRecord.from_json(
            load_json_strict(first_stdout, require_canonical=True)
        )
    except (CanonicalizationError, SchemaValidationError, TypeError, ValueError) as exc:
        raise _ReplayAttemptError(
            "generator_evidence",
            Phase8ReasonCode.GENERATOR_OUTPUT_MALFORMED,
            f"captured generator stdout is not a canonical proposal: {exc}",
        ) from exc
    stored_proposal = ReferenceProposalRecord.from_json(
        _read_json(source.evidence_root / "proposal.json")
    )
    if proposal != stored_proposal or proposal.proposal_hash != source.index.proposal_hash:
        raise _ReplayAttemptError(
            "generator_evidence",
            Phase8ReasonCode.GENERATOR_REPLAY_MISMATCH,
            "captured raw proposal differs from the indexed proposal",
        )
    first_guard = _read_json(source.evidence_root / "first_source_guard.json")
    second_guard = _read_json(source.evidence_root / "second_source_guard.json")
    if first_guard != second_guard or not _source_guard_clean(first_guard):
        raise _ReplayAttemptError(
            "generator_evidence",
            Phase8ReasonCode.GENERATOR_REPLAY_MISMATCH,
            "captured generator source guards are not equal and clean",
        )
    first_report = _parse_process_report(
        _read_json(source.evidence_root / "first_process_report.json")
    )
    second_report = _parse_process_report(
        _read_json(source.evidence_root / "second_process_report.json")
    )
    if first_report != second_report:
        raise _ReplayAttemptError(
            "generator_evidence",
            Phase8ReasonCode.GENERATOR_REPLAY_MISMATCH,
            "captured generator process reports differ",
        )
    guard_hash = canonical_json_hash(first_guard)
    checks = {
        "verdict": first_report.verdict == "success",
        "input_hash": first_report.input_hash == generator_input.input_hash,
        "stdout_hash": first_report.stdout_hash == sha256_hex(first_stdout),
        "stderr_hash": first_report.stderr_hash == sha256_hex(first_stderr),
        "worker_guard_hash": first_report.worker_guard_hash == guard_hash,
        "exit_code": first_report.exit_code == 0,
        "timed_out": not first_report.timed_out,
        "proposal_hash": first_report.proposal_hash == proposal.proposal_hash,
    }
    if not all(checks.values()):
        raise _ReplayAttemptError(
            "generator_evidence",
            Phase8ReasonCode.GENERATOR_REPLAY_MISMATCH,
            "captured process report does not recompute from raw generator evidence",
        )
    return generator_input, proposal


def _generator_input_from_predecessor(
    predecessor_root: Path,
) -> ReferenceGeneratorInputRecord:
    predecessor = load_predecessor_package(predecessor_root)
    core = predecessor.state.core
    if not hasattr(core, "state") or core.state not in {"initial", "target"}:
        raise _ReplayAttemptError(
            "generator_evidence",
            Phase8ReasonCode.GENERATOR_INPUT_MISMATCH,
            "captured predecessor is outside the finite Gate B replay scope",
        )
    template = reference_generator_input(core.state)
    view = GeneratorPredecessorViewRecord(
        package_id=predecessor.manifest.package_id,
        manifest_hash=predecessor.manifest.phase5_manifest_hash,
        semantic_tree_hash=predecessor.manifest.payload_tree_hash,
        state_hash=predecessor.manifest.state_hash,
        state=predecessor.state,
    )
    if view.package_id != template.predecessor.package_id:
        raise _ReplayAttemptError(
            "generator_evidence",
            Phase8ReasonCode.GENERATOR_INPUT_MISMATCH,
            "predecessor package ID is not bound to the finite reference transition",
        )
    if view.manifest_hash != template.predecessor.manifest_hash:
        raise _ReplayAttemptError(
            "generator_evidence",
            Phase8ReasonCode.GENERATOR_INPUT_MISMATCH,
            "predecessor logical manifest differs from the frozen reference grammar",
        )
    return ReferenceGeneratorInputRecord(
        transition_id=template.transition_id,
        predecessor=view,
        policy=template.policy,
        objective=template.objective,
        budget=template.budget,
    )


def _parse_process_report(value: object) -> GeneratorProcessReport:
    path = "phase8.generator_process_report"
    fields = {
        "schema_id",
        "verdict",
        "reason_codes",
        "input_hash",
        "stdout_hash",
        "stderr_hash",
        "worker_guard_hash",
        "exit_code",
        "timed_out",
        "proposal_hash",
    }
    obj = strict_object(value, path, fields)
    require_schema_id(obj["schema_id"], f"{path}.schema_id", GeneratorProcessReport.schema_id)
    verdict = require_string(obj["verdict"], f"{path}.verdict")
    if verdict not in {"success", "failure", "indeterminate"}:
        raise SchemaValidationError(f"{path}.verdict", "unsupported process verdict")
    reasons_raw = obj["reason_codes"]
    if not isinstance(reasons_raw, list):
        raise SchemaValidationError(f"{path}.reason_codes", "expected an array")
    reasons: list[GeneratorReasonCode] = []
    for index, item in enumerate(reasons_raw):
        text = require_string(item, f"{path}.reason_codes[{index}]")
        try:
            reasons.append(GeneratorReasonCode(text))
        except ValueError as exc:
            raise SchemaValidationError(
                f"{path}.reason_codes[{index}]",
                f"unknown generator reason code: {text}",
            ) from exc
    exit_code = obj["exit_code"]
    if exit_code is not None and (isinstance(exit_code, bool) or not isinstance(exit_code, int)):
        raise SchemaValidationError(f"{path}.exit_code", "expected integer or null")
    timed_out = obj["timed_out"]
    if not isinstance(timed_out, bool):
        raise SchemaValidationError(f"{path}.timed_out", "expected a Boolean")
    proposal_hash = obj["proposal_hash"]
    if proposal_hash is not None:
        proposal_hash = require_string(proposal_hash, f"{path}.proposal_hash")
        validate_hash256(proposal_hash, f"{path}.proposal_hash")
    return GeneratorProcessReport(
        verdict=cast(ProcessVerdict, verdict),
        reason_codes=tuple(reasons),
        input_hash=_hash_field(obj["input_hash"], f"{path}.input_hash"),
        stdout_hash=_hash_field(obj["stdout_hash"], f"{path}.stdout_hash"),
        stderr_hash=_hash_field(obj["stderr_hash"], f"{path}.stderr_hash"),
        worker_guard_hash=_hash_field(
            obj["worker_guard_hash"],
            f"{path}.worker_guard_hash",
        ),
        exit_code=exit_code,
        timed_out=timed_out,
        proposal_hash=proposal_hash,
    )


def _source_guard_clean(value: object) -> bool:
    path = "phase8.source_guard"
    obj = strict_object(
        value,
        path,
        {"schema_id", "guard_version", "file_hashes", "findings", "clean"},
    )
    require_schema_id(obj["schema_id"], f"{path}.schema_id")
    require_string(obj["guard_version"], f"{path}.guard_version")
    file_hashes = obj["file_hashes"]
    if not isinstance(file_hashes, Mapping):
        raise SchemaValidationError(f"{path}.file_hashes", "expected an object")
    for key, item in file_hashes.items():
        require_string(key, f"{path}.file_hashes.key")
        _hash_field(item, f"{path}.file_hashes.{key}")
    findings = obj["findings"]
    if not isinstance(findings, list):
        raise SchemaValidationError(f"{path}.findings", "expected an array")
    clean = obj["clean"]
    if not isinstance(clean, bool):
        raise SchemaValidationError(f"{path}.clean", "expected a Boolean")
    return clean and not findings


def _invoke_lean(
    verify_lean: LeanVerifierCallable,
    packet: LeanReferencePacket,
) -> LeanBridgeVerificationEvidence:
    if not callable(verify_lean):
        raise _ReplayAttemptError(
            "lean_outcome",
            Phase8ReasonCode.LEAN_REPLAY_FAILED,
            "Lean verifier is not callable",
            indeterminate=True,
        )
    try:
        result = verify_lean(packet)
    except Exception as exc:
        raise _ReplayAttemptError(
            "lean_outcome",
            Phase8ReasonCode.LEAN_REPLAY_FAILED,
            f"Lean verifier invocation failed: {type(exc).__name__}: {exc}",
            indeterminate=True,
        ) from exc
    if not isinstance(result, LeanBridgeVerificationEvidence):
        raise _ReplayAttemptError(
            "lean_outcome",
            Phase8ReasonCode.LEAN_REPLAY_FAILED,
            "Lean verifier returned an unsupported evidence type",
        )
    return result


def _write_lean_evidence(root: Path, evidence: LeanBridgeVerificationEvidence) -> None:
    root.mkdir(parents=True, exist_ok=False)
    (root / "generated_certificate.lean").write_bytes(evidence.generated.source_bytes)
    write_canonical_json(root / "generated_source.json", evidence.generated.to_json())
    write_canonical_json(root / "source_guard.json", evidence.source_guard.to_json())
    write_canonical_json(root / "lean_report.json", evidence.report.to_json())
    if evidence.compilation is not None:
        write_canonical_json(root / "compilation.json", evidence.compilation.to_json())
        (root / "stdout.bin").write_bytes(evidence.compilation.stdout)
        (root / "stderr.bin").write_bytes(evidence.compilation.stderr)
    if evidence.parsed_verdict is not None:
        write_canonical_json(root / "parsed_verdict.json", evidence.parsed_verdict.to_json())


def _lean_semantic_fingerprint(report: LeanBridgeVerificationReport) -> str:
    value = report.to_json()
    value.pop("compiler_duration_ms", None)
    return canonical_json_hash(value)


def _checker_semantic_fingerprint(report: object) -> str:
    if not hasattr(report, "checker_report") or report.checker_report is None:
        return canonical_json_hash({"checker_report": None})
    value = report.checker_report.to_json()
    value.pop("artifact_hashes", None)
    lean = value.get("lean_bridge_result")
    if isinstance(lean, dict):
        evidence = lean.get("evidence")
        if isinstance(evidence, dict):
            evidence.pop("report_hash", None)
    return canonical_json_hash(value)


def _verify_parent_link(source: _AttemptSource, policy: Phase7ControllerPolicyRecord) -> None:
    if source.index.ledger_event == "promotion":
        successor_root = source.attempt_root.parents[2] / "packages" / source.index.successor_package_hash
        successor = verify_immutable_phase7_package(successor_root, policy)
        if successor.parent_package_hash != source.index.predecessor_package_hash:
            raise _ReplayAttemptError(
                "parent_link",
                Phase8ReasonCode.PARENT_LINK_MISMATCH,
                "promoted package parent hash differs from the indexed predecessor",
            )
        if successor.source_candidate_package_tree_hash != source.index.candidate_package_tree_hash:
            raise _ReplayAttemptError(
                "parent_link",
                Phase8ReasonCode.PARENT_LINK_MISMATCH,
                "promoted package does not bind the independently realized candidate tree",
            )
    elif source.index.predecessor_package_hash != source.index.successor_package_hash:
        raise _ReplayAttemptError(
            "parent_link",
            Phase8ReasonCode.PARENT_LINK_MISMATCH,
            "nonpromotion changed the active package hash",
        )


def _accepted_attempt_report(
    source: _AttemptSource,
    stages: Sequence[Phase8StageResult],
    recomputed: Mapping[str, str],
) -> Phase8AttemptReplayReport:
    if tuple(stage.stage for stage in stages) != tuple(_STAGE_ORDER):
        raise _ReplayAttemptError(
            "parent_link",
            Phase8ReasonCode.INTERNAL_ERROR,
            "successful replay stage order differs from the frozen order",
        )
    return Phase8AttemptReplayReport(
        ledger_sequence_number=source.index.ledger_sequence_number,
        run_id=source.index.run_id,
        attempt_index=source.index.attempt_index,
        source_attempt_report_hash=source.index.attempt_report_hash,
        source_ledger_entry_hash=source.index.ledger_entry_hash,
        verdict="accept",
        reason_codes=(),
        generator_invocations=0,
        stages=tuple(stages),
        recomputed_hashes=FrozenHashMap.from_mapping(
            dict(recomputed),
            "phase8_attempt_report.recomputed_hashes",
        ),
    )


def _append_pass(stages: list[Phase8StageResult], stage: str, evidence: object) -> None:
    expected = _STAGE_ORDER[len(stages)]
    if stage != expected:
        raise _ReplayAttemptError(
            expected,
            Phase8ReasonCode.INTERNAL_ERROR,
            f"replay stage order mismatch: expected {expected}, observed {stage}",
        )
    stages.append(Phase8StageResult.build(stage, "pass", (), evidence))


def _read_json(path: Path) -> object:
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(f"replay evidence is not a regular file: {path}")
    return load_json_strict(path.read_bytes(), require_canonical=True)


def _tree_hash(path: Path) -> str:
    return semantic_tree_hash(build_tree_records(path))


def _hash_field(value: object, path: str) -> str:
    text = require_string(value, path)
    validate_hash256(text, path)
    return text



def _source_guard_failure_report(source_guard_hash: str) -> Phase8ReplayReport:
    validate_hash256(source_guard_hash, "phase8.source_guard_hash")
    zero = "0" * 64
    return Phase8ReplayReport(
        replay_id="phase8.replay.source_guard_rejected",
        bundle_manifest_hash=zero,
        verdict="reject",
        reason_codes=(Phase8ReasonCode.GENERATOR_INVOCATION_DETECTED,),
        package_chain=(zero, "1" * 64),
        attempts=(),
        generator_invocations=0,
        artifact_hashes=FrozenHashMap.from_mapping(
            {"replay_source_guard": source_guard_hash},
            "phase8_replay_report.artifact_hashes",
        ),
    )

def _bundle_failure_report(error: Exception) -> Phase8ReplayReport:
    detail_hash = sha256_hex(str(error).encode("utf-8"))
    reason = (
        error.reason
        if isinstance(error, Phase8BundleError)
        else Phase8ReasonCode.BUNDLE_SCHEMA_INVALID
    )
    zero = "0" * 64
    return Phase8ReplayReport(
        replay_id="phase8.unparsed.bundle",
        bundle_manifest_hash=zero,
        verdict="reject",
        reason_codes=(reason,),
        package_chain=(zero, "1" * 64),
        attempts=(),
        generator_invocations=0,
        artifact_hashes=FrozenHashMap.from_mapping(
            {"error_detail": detail_hash},
            "phase8_replay_report.artifact_hashes",
        ),
    )


def _internal_failure_report(
    replay_id: str,
    manifest_hash: str,
    error: Exception,
) -> Phase8ReplayReport:
    detail_hash = sha256_hex(str(error).encode("utf-8"))
    return Phase8ReplayReport(
        replay_id=replay_id,
        bundle_manifest_hash=manifest_hash,
        verdict="reject",
        reason_codes=(Phase8ReasonCode.INTERNAL_ERROR,),
        package_chain=("0" * 64, "1" * 64),
        attempts=(),
        generator_invocations=0,
        artifact_hashes=FrozenHashMap.from_mapping(
            {"error_detail": detail_hash},
            "phase8_replay_report.artifact_hashes",
        ),
    )


__all__ = [
    "Phase8ReplayEvidence",
    "reproduce_phase8_bundle",
]
