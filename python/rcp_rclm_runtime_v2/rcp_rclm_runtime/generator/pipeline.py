from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.lean_bridge.packet import LeanReferencePacket
from rcp_rclm_runtime.lean_bridge.verifier import (
    LeanBridgeVerificationEvidence,
    LeanBridgeVerificationReport,
    LeanReferenceVerifier,
)
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
    reference_resource_record,
    reference_trust_anchor,
)
from rcp_rclm_runtime.generator.process import run_reference_generator_replay
from rcp_rclm_runtime.generator.records import (
    REFERENCE_GENERATOR_WORKER_VERSION,
    GeneratorReasonCode,
    GeneratorReplayReport,
    ReferenceGeneratorInputRecord,
    UntrustedProposalRecord,
)
from rcp_rclm_runtime.generator.reference import reference_transition_id

CERTIFICATE_CONSTRUCTION_SCHEMA_ID = "runtime.phase5_certificate_construction.v2"
SELECTION_SCHEMA_ID = "runtime.phase5_reference_selection.v2"
REALIZATION_SCHEMA_ID = "runtime.phase5_reference_realization.v2"
PIPELINE_REPORT_SCHEMA_ID = "runtime.phase5_reference_pipeline_report.v2"


@dataclass(frozen=True, slots=True)
class CertificateConstructionRecord:
    proposal_hash: str
    certificate: RclmCertificatePacketRecord
    certificate_hash: str

    schema_id: ClassVar[str] = CERTIFICATE_CONSTRUCTION_SCHEMA_ID

    def __post_init__(self) -> None:
        validate_hash256(self.proposal_hash, "certificate_construction.proposal_hash")
        validate_hash256(self.certificate_hash, "certificate_construction.certificate_hash")
        actual = canonical_json_hash(self.certificate.to_json())
        if actual != self.certificate_hash:
            raise SchemaValidationError(
                "certificate_construction.certificate_hash",
                "certificate hash does not match the constructed packet",
            )

    @property
    def record_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "proposal_hash": self.proposal_hash,
            "certificate": self.certificate.to_json(),
            "certificate_hash": self.certificate_hash,
        }


@dataclass(frozen=True, slots=True)
class SelectionRecord:
    proposal_hash: str
    update: RclmUpdateRecord
    update_hash: str

    schema_id: ClassVar[str] = SELECTION_SCHEMA_ID

    def __post_init__(self) -> None:
        validate_hash256(self.proposal_hash, "selection.proposal_hash")
        validate_hash256(self.update_hash, "selection.update_hash")
        actual = canonical_json_hash(self.update.to_json())
        if actual != self.update_hash:
            raise SchemaValidationError(
                "selection.update_hash",
                "update hash does not match the selected update",
            )

    @property
    def record_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "proposal_hash": self.proposal_hash,
            "update": self.update.to_json(),
            "update_hash": self.update_hash,
        }


@dataclass(frozen=True, slots=True)
class RealizationRecord:
    predecessor_state_hash: str
    selection_hash: str
    candidate: RclmCandidateRecord
    candidate_hash: str
    successor_state_hash: str

    schema_id: ClassVar[str] = REALIZATION_SCHEMA_ID

    def __post_init__(self) -> None:
        for field_name in (
            "predecessor_state_hash",
            "selection_hash",
            "candidate_hash",
            "successor_state_hash",
        ):
            validate_hash256(getattr(self, field_name), f"realization.{field_name}")
        actual_candidate = canonical_json_hash(self.candidate.to_json())
        if actual_candidate != self.candidate_hash:
            raise SchemaValidationError(
                "realization.candidate_hash",
                "candidate hash does not match the realized candidate",
            )
        actual_successor = canonical_json_hash(self.candidate.next.to_json())
        if actual_successor != self.successor_state_hash:
            raise SchemaValidationError(
                "realization.successor_state_hash",
                "successor hash does not match the computed successor",
            )

    @property
    def record_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "predecessor_state_hash": self.predecessor_state_hash,
            "selection_hash": self.selection_hash,
            "candidate": self.candidate.to_json(),
            "candidate_hash": self.candidate_hash,
            "successor_state_hash": self.successor_state_hash,
        }


@dataclass(frozen=True, slots=True)
class PreparedReferenceTransition:
    generator_input: ReferenceGeneratorInputRecord
    generator_replay: GeneratorReplayReport
    transition_id: str
    proposal: UntrustedProposalRecord
    certificate_construction: CertificateConstructionRecord
    selection: SelectionRecord
    realization: RealizationRecord
    lean_packet: LeanReferencePacket


@dataclass(frozen=True, slots=True)
class Phase5ReferencePipelineReport:
    transition_id: str
    verdict: Literal["accept", "reject", "indeterminate"]
    reason_codes: Sequence[str]
    generator_replay: GeneratorReplayReport
    certificate_construction: CertificateConstructionRecord | None
    selection: SelectionRecord | None
    realization: RealizationRecord | None
    lean_bridge_report: LeanBridgeVerificationReport | None
    hardened_checker_report: Phase4HardenedReport | None
    artifact_hashes: FrozenHashMap
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = PIPELINE_REPORT_SCHEMA_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        if self.verdict not in {"accept", "reject", "indeterminate"}:
            raise SchemaValidationError("pipeline_report.verdict", "unsupported verdict")
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "pipeline_report.contract_version",
                f"expected {CONTRACT_VERSION}",
            )
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise SchemaValidationError(
                "pipeline_report.reason_codes",
                "reason codes must be unique",
            )
        if self.verdict == "accept" and self.reason_codes:
            raise SchemaValidationError(
                "pipeline_report.reason_codes",
                "accepting pipeline report cannot contain failure reasons",
            )
        if self.verdict != "accept" and not self.reason_codes:
            raise SchemaValidationError(
                "pipeline_report.reason_codes",
                "nonaccepting pipeline report requires a reason code",
            )

    @property
    def accepted(self) -> bool:
        return self.verdict == "accept"

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "transition_id": self.transition_id,
            "verdict": self.verdict,
            "accepted": self.accepted,
            "reason_codes": list(self.reason_codes),
            "generator_replay": self.generator_replay.to_json(),
            "certificate_construction": (
                None
                if self.certificate_construction is None
                else self.certificate_construction.to_json()
            ),
            "selection": None if self.selection is None else self.selection.to_json(),
            "realization": (
                None if self.realization is None else self.realization.to_json()
            ),
            "lean_bridge_report": (
                None
                if self.lean_bridge_report is None
                else self.lean_bridge_report.to_json()
            ),
            "hardened_checker_report": (
                None
                if self.hardened_checker_report is None
                else self.hardened_checker_report.to_json()
            ),
            "artifact_hashes": self.artifact_hashes.to_json(),
        }


@dataclass(frozen=True, slots=True)
class Phase5PipelineExecution:
    report: Phase5ReferencePipelineReport
    lean_evidence: LeanBridgeVerificationEvidence | None


def construct_reference_certificate(
    proposal: UntrustedProposalRecord,
) -> CertificateConstructionRecord:
    certificate_name = "improvement" if proposal.word == "improve" else "stability"
    certificate = canonical_rclm_certificate(
        "gate_b_classical",
        certificate_name,
    )
    return CertificateConstructionRecord(
        proposal_hash=proposal.proposal_hash,
        certificate=certificate,
        certificate_hash=canonical_json_hash(certificate.to_json()),
    )


def select_reference_update(
    proposal: UntrustedProposalRecord,
) -> SelectionRecord:
    update_name = "improve" if proposal.word == "improve" else "stay"
    update = canonical_rclm_update(ClassicalBinaryUpdateRecord(update_name))
    return SelectionRecord(
        proposal_hash=proposal.proposal_hash,
        update=update,
        update_hash=canonical_json_hash(update.to_json()),
    )


def realize_reference_candidate(
    generator_input: ReferenceGeneratorInputRecord,
    selection: SelectionRecord,
) -> RealizationRecord:
    predecessor = generator_input.predecessor_package.state
    if not isinstance(predecessor.core, ClassicalBinaryStateRecord):
        raise SchemaValidationError(
            "generator_input.predecessor_package.state.core",
            "Phase 5A requires a classical predecessor",
        )
    if not isinstance(selection.update.core, ClassicalBinaryUpdateRecord):
        raise SchemaValidationError(
            "selection.update.core",
            "Phase 5A requires a classical update",
        )
    successor_name = apply_binary_update(
        predecessor.core.state,
        selection.update.core.update,
    )
    successor = canonical_rclm_state(ClassicalBinaryStateRecord(successor_name))
    candidate = RclmCandidateRecord(
        update=selection.update,
        next=successor,
    )
    return RealizationRecord(
        predecessor_state_hash=canonical_json_hash(predecessor.to_json()),
        selection_hash=selection.record_hash,
        candidate=candidate,
        candidate_hash=canonical_json_hash(candidate.to_json()),
        successor_state_hash=canonical_json_hash(successor.to_json()),
    )


def prepare_reference_transition(
    generator_input: ReferenceGeneratorInputRecord,
    *,
    python_executable: str | None = None,
) -> PreparedReferenceTransition:
    replay = run_reference_generator_replay(
        generator_input,
        python_executable=python_executable,
    )
    if replay.status != "generated" or replay.proposal is None:
        raise ReferencePreparationError(replay.reason_codes, replay)
    proposal = replay.proposal
    _require_proposal_bindings(generator_input, proposal)
    core = generator_input.predecessor_package.state.core
    if not isinstance(core, ClassicalBinaryStateRecord):
        raise ReferencePreparationError(
            (GeneratorReasonCode.UNSUPPORTED_SCOPE,),
            replay,
        )
    transition_id = reference_transition_id(
        core,
        generator_input.policy,
        generator_input.objective,
        generator_input.resource_budget,
    )
    certificate_construction = construct_reference_certificate(proposal)
    selection = select_reference_update(proposal)
    realization = realize_reference_candidate(generator_input, selection)
    lean_packet = build_lean_reference_packet(
        generator_input.predecessor_package.state,
        realization.candidate,
        certificate_construction.certificate,
    )
    return PreparedReferenceTransition(
        generator_input=generator_input,
        generator_replay=replay,
        transition_id=transition_id,
        proposal=proposal,
        certificate_construction=certificate_construction,
        selection=selection,
        realization=realization,
        lean_packet=lean_packet,
    )


def finalize_reference_transition(
    prepared: PreparedReferenceTransition,
    lean_report: LeanBridgeVerificationReport,
) -> Phase5ReferencePipelineReport:
    generator_input = prepared.generator_input
    resource_record = _checker_resource_record(generator_input, prepared.transition_id)
    checker_request = Phase3CheckerRequest(
        transition_id=prepared.transition_id,
        predecessor=generator_input.predecessor_package.state,
        candidate=prepared.realization.candidate,
        certificate=prepared.certificate_construction.certificate,
        trust_anchor=reference_trust_anchor(),
        resource_record=resource_record,
        protected_distinctions=reference_protected_distinctions(
            "gate_b_classical"
        ),
        evaluation_evidence=reference_evaluation_evidence(
            generator_input.predecessor_package.state,
            prepared.realization.candidate,
        ),
        lean_bridge_report=lean_report,
    )
    package_integrity = build_reference_package_integrity(checker_request)
    if (
        package_integrity.predecessor_manifest
        != generator_input.predecessor_package.manifest
    ):
        return _binding_failure_report(prepared, lean_report, package_integrity)
    hardened_request = Phase4HardenedRequest(
        checker_request=checker_request,
        package_integrity=package_integrity,
    )
    hardened_report = check_hardened_transition(hardened_request)
    reasons: list[str] = [reason.value for reason in hardened_report.reason_codes]
    if not lean_report.accepted:
        reasons.append(GeneratorReasonCode.LEAN_VERIFIER_FAILED.value)
    if not hardened_report.accepted:
        reasons.append(GeneratorReasonCode.CHECKER_REJECTED.value)
    ordered_reasons = tuple(dict.fromkeys(reasons))
    if hardened_report.verdict == "reject":
        verdict: Literal["accept", "reject", "indeterminate"] = "reject"
    elif hardened_report.verdict == "indeterminate":
        verdict = "indeterminate"
    else:
        verdict = "accept"
    artifact_hashes = _complete_artifact_hashes(
        prepared,
        lean_report,
        hardened_report,
        package_integrity.candidate_manifest.content_hash(),
    )
    return Phase5ReferencePipelineReport(
        transition_id=prepared.transition_id,
        verdict=verdict,
        reason_codes=() if verdict == "accept" else ordered_reasons,
        generator_replay=prepared.generator_replay,
        certificate_construction=prepared.certificate_construction,
        selection=prepared.selection,
        realization=prepared.realization,
        lean_bridge_report=lean_report,
        hardened_checker_report=hardened_report,
        artifact_hashes=artifact_hashes,
    )


def execute_reference_pipeline(
    generator_input: ReferenceGeneratorInputRecord,
    verifier: LeanReferenceVerifier,
    *,
    python_executable: str | None = None,
) -> Phase5PipelineExecution:
    try:
        prepared = prepare_reference_transition(
            generator_input,
            python_executable=python_executable,
        )
    except ReferencePreparationError as exc:
        return Phase5PipelineExecution(
            report=_preparation_failure_report(generator_input, exc),
            lean_evidence=None,
        )
    evidence = verifier.verify_with_evidence(prepared.lean_packet)
    report = finalize_reference_transition(prepared, evidence.report)
    return Phase5PipelineExecution(report=report, lean_evidence=evidence)


class ReferencePreparationError(Exception):
    def __init__(
        self,
        reason_codes: Sequence[GeneratorReasonCode],
        replay: GeneratorReplayReport,
    ) -> None:
        self.reason_codes = tuple(reason_codes)
        self.replay = replay
        super().__init__(",".join(reason.value for reason in self.reason_codes))


def _require_proposal_bindings(
    generator_input: ReferenceGeneratorInputRecord,
    proposal: UntrustedProposalRecord,
) -> None:
    expected = {
        "predecessor_package_id": (
            generator_input.predecessor_package.manifest.package_id
        ),
        "predecessor_manifest_hash": (
            generator_input.predecessor_package.manifest_hash
        ),
        "policy_hash": generator_input.policy.policy_hash,
        "objective_hash": generator_input.objective.objective_hash,
        "budget_hash": generator_input.resource_budget.budget_hash,
        "generator_input_hash": generator_input.input_hash,
    }
    observed = {
        "predecessor_package_id": proposal.predecessor_package_id,
        "predecessor_manifest_hash": proposal.predecessor_manifest_hash,
        "policy_hash": proposal.policy_hash,
        "objective_hash": proposal.objective_hash,
        "budget_hash": proposal.budget_hash,
        "generator_input_hash": proposal.generator_input_hash,
    }
    if observed != expected:
        raise ReferencePreparationError(
            (GeneratorReasonCode.PIPELINE_BINDING_MISMATCH,),
            GeneratorReplayReport(
                status="reject",
                reason_codes=(GeneratorReasonCode.PIPELINE_BINDING_MISMATCH,),
                first=_unreachable_observation(generator_input),
                second=_unreachable_observation(generator_input),
                proposal=None,
            ),
        )


def _checker_resource_record(
    generator_input: ReferenceGeneratorInputRecord,
    transition_id: str,
):
    environment_hash = canonical_json_hash(
        {
            "schema_id": "runtime.phase5_reference_environment.v2",
            "transition_id": transition_id,
            "worker_version": REFERENCE_GENERATOR_WORKER_VERSION,
            "network": "denied",
            "model": "absent",
            "filesystem_writes": "denied",
        }
    )
    return reference_resource_record(
        precision_bits=256,
        budget_units=generator_input.resource_budget.resource_units,
        consumed_units=generator_input.resource_budget.resource_units,
        environment_hash=environment_hash,
    )


def _preparation_failure_report(
    generator_input: ReferenceGeneratorInputRecord,
    error: ReferencePreparationError,
) -> Phase5ReferencePipelineReport:
    transition_id = generator_input.predecessor_package.manifest.package_id.removesuffix(
        ".predecessor"
    )
    return Phase5ReferencePipelineReport(
        transition_id=transition_id,
        verdict=(
            "indeterminate"
            if error.replay.status == "indeterminate"
            else "reject"
        ),
        reason_codes=tuple(reason.value for reason in error.reason_codes),
        generator_replay=error.replay,
        certificate_construction=None,
        selection=None,
        realization=None,
        lean_bridge_report=None,
        hardened_checker_report=None,
        artifact_hashes=FrozenHashMap.from_mapping(
            {
                "generator_input": generator_input.input_hash,
                "generator_replay": error.replay.report_hash,
                "predecessor_manifest": (
                    generator_input.predecessor_package.manifest_hash
                ),
            },
            "pipeline_report.artifact_hashes",
        ),
    )


def _binding_failure_report(
    prepared: PreparedReferenceTransition,
    lean_report: LeanBridgeVerificationReport,
    package_integrity,
) -> Phase5ReferencePipelineReport:
    return Phase5ReferencePipelineReport(
        transition_id=prepared.transition_id,
        verdict="reject",
        reason_codes=(GeneratorReasonCode.PIPELINE_BINDING_MISMATCH.value,),
        generator_replay=prepared.generator_replay,
        certificate_construction=prepared.certificate_construction,
        selection=prepared.selection,
        realization=prepared.realization,
        lean_bridge_report=lean_report,
        hardened_checker_report=None,
        artifact_hashes=FrozenHashMap.from_mapping(
            {
                "candidate_manifest": (
                    package_integrity.candidate_manifest.content_hash()
                ),
                "generator_input": prepared.generator_input.input_hash,
                "generator_replay": prepared.generator_replay.report_hash,
                "lean_bridge_report": lean_report.report_hash,
                "observed_predecessor_manifest": (
                    package_integrity.predecessor_manifest.content_hash()
                ),
                "required_predecessor_manifest": (
                    prepared.generator_input.predecessor_package.manifest_hash
                ),
            },
            "pipeline_report.artifact_hashes",
        ),
    )


def _complete_artifact_hashes(
    prepared: PreparedReferenceTransition,
    lean_report: LeanBridgeVerificationReport,
    hardened_report: Phase4HardenedReport,
    candidate_manifest_hash: str,
) -> FrozenHashMap:
    return FrozenHashMap.from_mapping(
        {
            "candidate_manifest": candidate_manifest_hash,
            "certificate_construction": (
                prepared.certificate_construction.record_hash
            ),
            "generator_input": prepared.generator_input.input_hash,
            "generator_replay": prepared.generator_replay.report_hash,
            "hardened_checker_report": hardened_report.report_hash,
            "lean_bridge_report": lean_report.report_hash,
            "predecessor_manifest": (
                prepared.generator_input.predecessor_package.manifest_hash
            ),
            "realization": prepared.realization.record_hash,
            "selection": prepared.selection.record_hash,
            "untrusted_proposal": prepared.proposal.proposal_hash,
        },
        "pipeline_report.artifact_hashes",
    )


def _unreachable_observation(generator_input: ReferenceGeneratorInputRecord):
    from rcp_rclm_runtime.generator.records import GeneratorProcessObservation

    zero_hash = canonical_json_hash(
        {
            "schema_id": "runtime.phase5_unreachable_observation.v2",
            "generator_input_hash": generator_input.input_hash,
        }
    )
    return GeneratorProcessObservation(
        status="reject",
        reason_codes=(GeneratorReasonCode.PIPELINE_BINDING_MISMATCH,),
        exit_code=0,
        timed_out=False,
        input_hash=generator_input.input_hash,
        stdout_hash=zero_hash,
        stderr_hash=zero_hash,
        command_hash=zero_hash,
        environment_key_hash=zero_hash,
        response=None,
    )
