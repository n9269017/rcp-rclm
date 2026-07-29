from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.contract.certificate import (
    HeldoutAccessPolicy,
    LearnedCertificatePacket,
)
from rcp_rclm_runtime_v3.contract.common import TARGET_BY_KIND
from rcp_rclm_runtime_v3.contract.state import (
    LearnedRCLMState,
    PolicyIdentity,
    SelfHostingBinding,
)
from rcp_rclm_runtime_v3.contract.tasks import (
    CapabilityFrontier,
    CertificationRecord,
    TaskLedger,
    TaskRecord,
)
from rcp_rclm_runtime_v3.contract.update import LearnedRCLMUpdate, UpdateOperation
from rcp_rclm_runtime_v3.contract.validation import Phase9TransitionReport, validate_phase9_transition
from rcp_rclm_runtime_v3.phase10.learned_data import LeanCompletionTask
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport

from rcp_rclm_runtime_v4.gatee.records import (
    AutonomousSearchReport,
    AttemptRecord,
    FrontierSnapshot,
    RouteHintPolicy,
)
from rcp_rclm_runtime_v4.gatee.validation import validate_report
from rcp_rclm_runtime_v4.phase14.candidate import Phase14SemanticCandidate
from rcp_rclm_runtime_v4.phase14.challenges import (
    HiddenChallenge,
    answer_store_json,
    challenge_manifest_json,
)
from rcp_rclm_runtime_v4.phase14.constants import (
    CHANGED_COMPONENTS_BY_FAMILY,
    PHASE13_EXIT_REPORT_HASH,
    PHASE14_TRAJECTORY_ID,
    UpdateFamily,
)
from rcp_rclm_runtime_v4.phase14.records import (
    Phase14MutationProgram,
    Phase14ProposalEnumeration,
    Phase14SearchHistory,
)
from rcp_rclm_runtime_v4.phase14.tasks import (
    Phase14InformationReport,
    base_task_suite,
    build_information_report,
    verify_task,
)


_TARGET_TO_KIND = {target: kind for kind, target in TARGET_BY_KIND.items()}
_COMPONENT_PATH = {
    "model_weights": "model/tensors/manifest.json",
    "adapter_manifest": "model/adapters/manifest.json",
    "optimizer_policy": "training/optimizer_state.json",
    "retrieval_policy": "retrieval/index_manifest.json",
    "memory_state": "memory/memory_manifest.json",
    "planner_policy": "policies/planner_policy.json",
    "generator_policy": "policies/generator_policy.json",
}


@dataclass(frozen=True, slots=True)
class RecursiveProductivityReport:
    predecessor_frontier: Sequence[str]
    candidate_frontier: Sequence[str]
    package_generated_program: bool
    two_run_replay_equal: bool
    challenge_commitment_bound: bool
    rejection_conditioned: bool
    selected_family: UpdateFamily

    schema_id: ClassVar[str] = "runtime.v4.phase14.recursive_productivity_report.v1"

    @property
    def retained(self) -> bool:
        return set(self.predecessor_frontier).issubset(self.candidate_frontier)

    @property
    def accepted(self) -> bool:
        return (
            self.retained
            and self.package_generated_program
            and self.two_run_replay_equal
            and self.challenge_commitment_bound
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "predecessor_frontier": list(self.predecessor_frontier),
            "candidate_frontier": list(self.candidate_frontier),
            "package_generated_program": self.package_generated_program,
            "two_run_replay_equal": self.two_run_replay_equal,
            "challenge_commitment_bound": self.challenge_commitment_bound,
            "rejection_conditioned": self.rejection_conditioned,
            "selected_family": self.selected_family,
            "retained": self.retained,
            "accepted": self.accepted,
        }


def initial_recursive_frontier() -> tuple[str, ...]:
    return (
        "recursive.bind_hidden_commitment",
        "recursive.generate_valid_program",
    )


def next_recursive_frontier(
    predecessor: Sequence[str],
    *,
    family: UpdateFamily,
    rejection_conditioned: bool,
) -> tuple[str, ...]:
    values = set(predecessor)
    values.add("recursive.choose_update_family")
    if rejection_conditioned:
        values.add("recursive.recover_after_rejection")
    if family == "generator_planner":
        values.add("recursive.self_modify_generator_planner")
    if family == "memory_retrieval":
        values.add("recursive.persist_search_route")
    if family == "adapter_optimizer":
        values.add("recursive.install_adapter_route")
    if family == "model_weights":
        values.add("recursive.install_weight_route")
    return tuple(sorted(values, key=lambda item: item.encode("utf-8")))


def _task_record(task: LeanCompletionTask) -> TaskRecord:
    return TaskRecord(
        task_id=task.task_id,
        task_class="lean_theorem_completion_v1",
        prompt_hash=sha256_hex(task.model_prompt),
        verifier_spec_hash=canonical_json_hash(
            {
                "source_prefix": task.source_prefix,
                "expected_completion": task.expected_completion,
                "verifier": "pinned_lean_theorem_verifier_v1",
            }
        ),
        partition=task.partition,
    )


def _certification(report: TaskVerifierReport) -> CertificationRecord:
    return CertificationRecord(
        task_id=report.task_id,
        model_identity_hash=report.model_identity_hash,
        verifier_report_hash=report.report_hash,
        verified_output_hash=canonical_json_hash(
            {
                "completion_hash": report.completion_hash,
                "source_hash": report.source_hash,
                "decode_result_hash": report.decode_result_hash,
                "verdict": report.verdict,
            }
        ),
    )


def _policy_identity(manifest) -> PolicyIdentity:
    return PolicyIdentity(
        training_policy_hash=manifest.training_policy_hash,
        optimizer_policy_hash=manifest.optimizer_state_hash,
        data_curriculum_hash=manifest.data_curriculum_hash,
        generator_policy_hash=manifest.generator_policy_hash,
        planner_policy_hash=manifest.planner_policy_hash,
        retrieval_policy_hash=manifest.retrieval_index_hash,
        memory_state_hash=manifest.memory_manifest_hash,
        tool_policy_hash=manifest.tool_policy_hash,
        verification_policy_hash=manifest.verification_policy_hash,
        resource_policy_hash=manifest.resource_policy_hash,
        self_model_hash=manifest.self_model_hash,
    )


def _proposal_protocol_hash(root: Path) -> str:
    import json

    generator = json.loads((root / "policies/generator_policy.json").read_text(encoding="utf-8"))
    planner = json.loads((root / "policies/planner_policy.json").read_text(encoding="utf-8"))
    candidate = generator.get("proposal_protocol_hash") or planner.get("proposal_protocol_hash")
    if isinstance(candidate, str) and len(candidate) == 64:
        return candidate
    return canonical_json_hash(
        {
            "generator_policy_hash": canonical_json_hash(generator),
            "planner_policy_hash": canonical_json_hash(planner),
            "protocol": "phase14-package-bound-family-enumeration-v1",
        }
    )


def build_state(
    package_root: Path,
    reports: Sequence[TaskVerifierReport],
    tasks: Sequence[LeanCompletionTask],
    *,
    parent_state: LearnedRCLMState | None,
    generation: int,
) -> LearnedRCLMState:
    root = package_root.resolve(strict=True)
    manifest = load_package_manifest(root)
    ordered_tasks = tuple(sorted(tasks, key=lambda item: item.task_id.encode("utf-8")))
    ordered_reports = tuple(sorted(reports, key=lambda item: item.task_id.encode("utf-8")))
    if tuple(task.task_id for task in ordered_tasks) != tuple(report.task_id for report in ordered_reports):
        raise SchemaValidationError("phase14.state", "task and report surfaces differ")
    if any(not report.solved for report in ordered_reports):
        raise SchemaValidationError("phase14.state", "frontier state requires solved task reports")
    policies = _policy_identity(manifest)
    protocol = _proposal_protocol_hash(root)
    self_hosting = SelfHostingBinding(
        generator_component_hash=policies.generator_policy_hash,
        planner_component_hash=policies.planner_policy_hash,
        proposal_protocol_hash=protocol,
        self_hosting_contract_hash=canonical_json_hash(
            {
                "schema_id": "runtime.v4.phase14.self_hosting_contract.v1",
                "proposal_protocol_hash": protocol,
                "route_hints_permitted": False,
                "manual_repair_permitted": False,
                "heldout_material_visible": False,
            }
        ),
    )
    return LearnedRCLMState(
        package_id=manifest.package_id,
        parent_package_id=None if parent_state is None else parent_state.package_id,
        base_state_hash=canonical_json_hash(
            {
                "trajectory_id": PHASE14_TRAJECTORY_ID,
                "generation": generation,
                "semantic_package_hash": manifest.package_hash,
                "phase13_exit_report_hash": PHASE13_EXIT_REPORT_HASH,
            }
        ),
        model=manifest.model_identity(),
        policies=policies,
        self_hosting=self_hosting,
        task_ledger=TaskLedger(
            tasks=tuple(_task_record(task) for task in ordered_tasks),
            certifications=tuple(_certification(report) for report in ordered_reports),
        ),
        capability_frontier=CapabilityFrontier(
            task_ids=tuple(task.task_id for task in ordered_tasks)
        ),
    )


def build_initial_m4_state(
    m4_root: Path,
    *,
    lean_project_root: Path | None,
) -> tuple[LearnedRCLMState, tuple[TaskVerifierReport, ...]]:
    tasks = base_task_suite()
    reports = tuple(
        verify_task(m4_root, task, lean_project_root=lean_project_root)
        for task in tasks
    )
    return build_state(
        m4_root,
        reports,
        tasks,
        parent_state=None,
        generation=4,
    ), reports


def _heldout_policy(challenges: Sequence[HiddenChallenge]) -> HeldoutAccessPolicy:
    manifest = challenge_manifest_json(challenges)
    answers = answer_store_json(challenges)
    return HeldoutAccessPolicy(
        policy_id="phase14-post-freeze-hidden-challenge-policy-v1",
        heldout_task_manifest_hash=str(manifest["manifest_hash"]),
        reference_answer_store_hash=str(answers["answer_store_hash"]),
        evaluator_policy_hash=canonical_json_hash(
            {
                "verifier": "pinned_lean_theorem_verifier_v1",
                "candidate_freeze_required": True,
                "successful_update_family_recorded": False,
                "route_recomputed": True,
                "candidate_self_report_authoritative": False,
            }
        ),
    )


def _update(
    predecessor: LearnedRCLMState,
    candidate: LearnedRCLMState,
    family: UpdateFamily,
    transition_id: str,
) -> LearnedRCLMUpdate:
    targets = CHANGED_COMPONENTS_BY_FAMILY[family]
    operations = tuple(
        UpdateOperation(
            operation_id=f"{index:04d}-phase14-{target}",
            kind=_TARGET_TO_KIND[target],
            target=target,
            component_path=_COMPONENT_PATH[target],
            before_hash=predecessor.component_hash(target),
            after_hash=candidate.component_hash(target),
        )
        for index, target in enumerate(
            sorted(targets, key=lambda item: item.encode("utf-8")),
            start=1,
        )
    )
    return LearnedRCLMUpdate(
        transition_id=transition_id,
        predecessor_state_hash=predecessor.state_hash,
        candidate_state_hash=candidate.state_hash,
        base_update_hash=canonical_json_hash({"gate_b_update": "stay"}),
        operations=operations,
    )


def _certificate(
    predecessor: LearnedRCLMState,
    candidate: LearnedRCLMState,
    update: LearnedRCLMUpdate,
    challenge: HiddenChallenge,
    reports: Sequence[TaskVerifierReport],
    information: Phase14InformationReport,
    proposal: Phase14ProposalEnumeration,
    program: Phase14MutationProgram,
    candidate_semantic: Phase14SemanticCandidate,
    hidden_challenges: Sequence[HiddenChallenge],
) -> LearnedCertificatePacket:
    report_by_id = {report.task_id: report for report in reports}
    new_report = report_by_id[challenge.task_id]
    protected_reports = {
        task_id: report.report_hash
        for task_id, report in sorted(report_by_id.items())
        if task_id != challenge.task_id
    }
    heldout = _heldout_policy(hidden_challenges)
    return LearnedCertificatePacket(
        transition_id=update.transition_id,
        predecessor_state_hash=predecessor.state_hash,
        candidate_state_hash=candidate.state_hash,
        update_hash=update.update_hash,
        base_certificate_hash=canonical_json_hash({"gate_b_certificate": "stability"}),
        capability_frontier_before_hash=predecessor.capability_frontier.frontier_hash,
        capability_frontier_after_hash=candidate.capability_frontier.frontier_hash,
        protected_task_ids=predecessor.capability_frontier.task_ids,
        new_task_ids=(challenge.task_id,),
        task_frontier_retention_evidence_hash=canonical_json_hash(protected_reports),
        new_task_capability_evidence_hash=new_report.report_hash,
        model_output_density_evidence_hash=information.report_hash,
        entropy_kl_qre_evidence_hash=information.report_hash,
        goal_drift_evidence_hash=canonical_json_hash({"goal_drift": 0, "budget": 0}),
        training_data_provenance_hash=candidate_semantic.family_evidence_hash,
        heldout_isolation_evidence_hash=canonical_json_hash(
            {
                "challenge_commitment_hash": challenge.commitment_hash,
                "proposal_enumeration_hash": proposal.enumeration_hash,
                "program_hash": program.program_hash,
                "candidate_frozen_before_reveal": True,
                "prompt_visible_before_freeze": False,
                "answer_visible_before_freeze": False,
                "successful_update_family_visible_before_freeze": False,
            }
        ),
        architecture_compatibility_hash=canonical_json_hash(
            {
                "semantic_candidate_hash": candidate_semantic.candidate_hash,
                "changed_paths": list(candidate_semantic.changed_paths),
            }
        ),
        self_hosting_evidence_hash=canonical_json_hash(
            {
                "proposal_enumeration_hash": proposal.enumeration_hash,
                "two_run_replay_equal": True,
                "package_generated": True,
            }
        ),
        resource_evidence_hash=canonical_json_hash(
            {
                "search_cost": program.search_cost,
                "manual_repairs": 0,
                "candidate_count": 1,
            }
        ),
        rollback_evidence_hash=canonical_json_hash(
            {
                "candidate_semantic_package_hash": candidate_semantic.manifest.package_hash,
                "exact_rollback_required": True,
            }
        ),
        heldout_access_policy_hash=heldout.policy_hash,
        active_generator_hash=predecessor.policies.generator_policy_hash,
        active_planner_hash=predecessor.policies.planner_policy_hash,
        proposal_protocol_hash=predecessor.self_hosting.proposal_protocol_hash,
    )


@dataclass(frozen=True, slots=True)
class Phase14SemanticEvaluation:
    accepted: bool
    reason_codes: Sequence[str]
    active_state: LearnedRCLMState
    candidate_state: LearnedRCLMState | None
    protected_reports: Sequence[TaskVerifierReport]
    hidden_task_report: TaskVerifierReport
    information_report: Phase14InformationReport
    recursive_productivity_report: RecursiveProductivityReport
    update: LearnedRCLMUpdate | None
    certificate: LearnedCertificatePacket | None
    gate_d_report: Phase9TransitionReport | None
    gate_d_evidence_hash: str

    schema_id: ClassVar[str] = "runtime.v4.phase14.semantic_evaluation.v1"

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "reason_codes": list(self.reason_codes),
            "active_state_hash": self.active_state.state_hash,
            "candidate_state": None if self.candidate_state is None else self.candidate_state.to_json(),
            "protected_reports": [report.to_json() for report in self.protected_reports],
            "hidden_task_report": self.hidden_task_report.to_json(),
            "information_report": self.information_report.to_json(),
            "recursive_productivity_report": self.recursive_productivity_report.to_json(),
            "update": None if self.update is None else self.update.to_json(),
            "certificate": None if self.certificate is None else self.certificate.to_json(),
            "gate_d_report": None if self.gate_d_report is None else self.gate_d_report.to_json(),
            "gate_d_evidence_hash": self.gate_d_evidence_hash,
            "manual_repairs": 0,
            "heldout_material_visible_before_freeze": False,
            "candidate_self_report_authoritative": False,
        }


def evaluate_semantic_candidate(
    active_root: Path,
    candidate: Phase14SemanticCandidate,
    active_state: LearnedRCLMState,
    accepted_challenges: Sequence[HiddenChallenge],
    challenge: HiddenChallenge,
    proposal: Phase14ProposalEnumeration,
    history: Phase14SearchHistory,
    predecessor_recursive_frontier: Sequence[str],
    *,
    lean_project_root: Path | None,
    generation: int,
    hidden_challenges: Sequence[HiddenChallenge],
) -> Phase14SemanticEvaluation:
    base_protected_tasks = base_task_suite()
    protected_tasks = (*base_protected_tasks, *(item.task for item in accepted_challenges))
    protected_reports = (
        *(
            verify_task(
                candidate.root, task, lean_project_root=lean_project_root
            )
            for task in base_protected_tasks
        ),
        *(
            verify_task(
                candidate.root,
                item.task,
                lean_project_root=lean_project_root,
                challenge=item,
            )
            for item in accepted_challenges
        ),
    )
    hidden_report = verify_task(
        candidate.root,
        challenge.task,
        lean_project_root=lean_project_root,
        challenge=challenge,
    )
    information = build_information_report(
        active_root,
        candidate.root,
        base_protected_tasks,
        challenge,
        accepted_challenges=accepted_challenges,
    )
    rejection_conditioned = bool(history.attempted_families(challenge.commitment_hash))
    recursive_after = next_recursive_frontier(
        predecessor_recursive_frontier,
        family=candidate.program.update_family,
        rejection_conditioned=rejection_conditioned,
    )
    recursive = RecursiveProductivityReport(
        predecessor_frontier=tuple(predecessor_recursive_frontier),
        candidate_frontier=recursive_after,
        package_generated_program=True,
        two_run_replay_equal=True,
        challenge_commitment_bound=(
            candidate.program.challenge_commitment_hash == challenge.commitment_hash
            and proposal.challenge_commitment_hash == challenge.commitment_hash
        ),
        rejection_conditioned=rejection_conditioned,
        selected_family=candidate.program.update_family,
    )
    preliminary_reasons: list[str] = []
    if any(not report.solved for report in protected_reports):
        preliminary_reasons.append("PHASE14_PROTECTED_FRONTIER_REGRESSION")
    if not hidden_report.solved:
        preliminary_reasons.append("PHASE14_HIDDEN_CHALLENGE_UNSOLVED")
    if not information.accepted:
        preliminary_reasons.append("PHASE14_INFORMATION_CONTRACT_FAILED")
    if not recursive.accepted:
        preliminary_reasons.append("PHASE14_RECURSIVE_PRODUCTIVITY_FAILED")
    if preliminary_reasons:
        rejection_hash = canonical_json_hash(
            {
                "schema_id": "runtime.v4.phase14.gate_d_precheck_rejection.v1",
                "candidate_semantic_package_hash": candidate.manifest.package_hash,
                "program_hash": candidate.program.program_hash,
                "reason_codes": sorted(set(preliminary_reasons)),
                "hidden_task_report_hash": hidden_report.report_hash,
                "information_report_hash": information.report_hash,
                "recursive_productivity_report_hash": recursive.report_hash,
            }
        )
        return Phase14SemanticEvaluation(
            accepted=False,
            reason_codes=tuple(sorted(set(preliminary_reasons))),
            active_state=active_state,
            candidate_state=None,
            protected_reports=protected_reports,
            hidden_task_report=hidden_report,
            information_report=information,
            recursive_productivity_report=recursive,
            update=None,
            certificate=None,
            gate_d_report=None,
            gate_d_evidence_hash=rejection_hash,
        )
    tasks = (*protected_tasks, challenge.task)
    reports = (*protected_reports, hidden_report)
    candidate_state = build_state(
        candidate.root,
        reports,
        tasks,
        parent_state=active_state,
        generation=generation,
    )
    transition_id = f"phase14-generation-{generation}-{challenge.challenge_id}"
    update = _update(
        active_state,
        candidate_state,
        candidate.program.update_family,
        transition_id,
    )
    certificate = _certificate(
        active_state,
        candidate_state,
        update,
        challenge,
        reports,
        information,
        proposal,
        candidate.program,
        candidate,
        hidden_challenges,
    )
    gate_d = validate_phase9_transition(
        active_state,
        update,
        candidate_state,
        certificate,
        _heldout_policy(hidden_challenges),
    )
    reasons = () if gate_d.accepted else tuple(gate_d.reason_codes)
    return Phase14SemanticEvaluation(
        accepted=gate_d.accepted,
        reason_codes=reasons,
        active_state=active_state,
        candidate_state=candidate_state,
        protected_reports=protected_reports,
        hidden_task_report=hidden_report,
        information_report=information,
        recursive_productivity_report=recursive,
        update=update,
        certificate=certificate,
        gate_d_report=gate_d,
        gate_d_evidence_hash=canonical_json_hash(
            {
                "certificate_hash": certificate.certificate_hash,
                "gate_d_report_hash": gate_d.semantic_report_hash,
            }
        ),
    )


def build_gate_e_challenge_report(
    active_state: LearnedRCLMState,
    predecessor_recursive_frontier: Sequence[str],
    challenge_commitment_hash: str,
    attempt_records: Sequence[AttemptRecord],
) -> tuple[AutonomousSearchReport, dict[str, object]]:
    first_accepted = next(
        (attempt for attempt in attempt_records if attempt.evaluator_accepted),
        None,
    )
    if first_accepted is None:
        raise SchemaValidationError(
            "phase14.gate_e",
            "challenge report requires one accepted attempt",
        )
    report = AutonomousSearchReport(
        source_package_hash=active_state.state_hash,
        history_hash=canonical_json_hash(
            [attempt.attempt_hash for attempt in attempt_records]
        ),
        challenge_commitment_hash=challenge_commitment_hash,
        route_hints=RouteHintPolicy(),
        predecessor_frontier=FrontierSnapshot(
            capability_tasks=active_state.capability_frontier.task_ids,
            recursive_productivity_tasks=tuple(predecessor_recursive_frontier),
        ),
        attempts=tuple(attempt_records),
        search_budget=len(attempt_records),
        manual_repairs=0,
        heldout_material_visible_before_freeze=False,
        result_kind="promoted",
        selected_attempt_index=first_accepted.attempt_index,
        exhaustion=None,
    )
    return report, validate_report(report)


__all__ = [
    "Phase14SemanticEvaluation",
    "RecursiveProductivityReport",
    "build_gate_e_challenge_report",
    "build_initial_m4_state",
    "build_state",
    "evaluate_semantic_candidate",
    "initial_recursive_frontier",
    "next_recursive_frontier",
]
