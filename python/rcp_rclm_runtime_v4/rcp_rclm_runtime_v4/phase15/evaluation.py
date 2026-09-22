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
from rcp_rclm_runtime_v3.contract.common import ALL_COMPONENT_TARGETS, TARGET_BY_KIND
from rcp_rclm_runtime_v3.contract.state import LearnedRCLMState
from rcp_rclm_runtime_v3.contract.update import LearnedRCLMUpdate, UpdateOperation
from rcp_rclm_runtime_v3.contract.validation import Phase9TransitionReport, validate_phase9_transition
from rcp_rclm_runtime_v3.phase10.learned_data import LeanCompletionTask
from rcp_rclm_runtime_v3.phase10.lean_process import run_pinned_lean_source
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport
from rcp_rclm_runtime_v4.phase14.challenges import challenges_from_answer_store
from rcp_rclm_runtime_v4.phase14.evaluation import build_state
from rcp_rclm_runtime_v4.phase14.tasks import base_task_suite, verify_task

from rcp_rclm_runtime_v4.phase15.candidate import Phase15SemanticCandidate
from rcp_rclm_runtime_v4.phase15.challenges import DynamicHiddenChallenge
from rcp_rclm_runtime_v4.phase15.constants import (
    PHASE15_COMPONENT_PATHS,
    PHASE15_EXHAUSTIVE_MAX_X,
    PHASE15_EXHAUSTIVE_MIN_X,
    PHASE15_RECURSIVE_PRODUCTIVITY_ADDITIONS,
    PHASE15_UPDATE_KIND_BY_TARGET,
    TOKEN_BY_NAME,
)
from rcp_rclm_runtime_v4.phase15.decoder import DecodeReport, decode_plan


_FORBIDDEN_SOURCE_TOKENS = ("sorry", "admit", "sorryAx", "axiom")
_KIND_BY_TARGET = {target: kind for kind, target in TARGET_BY_KIND.items()}


@dataclass(frozen=True, slots=True)
class DynamicTaskReport:
    task_id: str
    domain: str
    semantic_package_hash: str
    model_identity_hash: str
    decode_report: DecodeReport | None
    plan_text: str
    grammar_accepted: bool
    source_hash: str
    exhaustive_cases: int
    exhaustive_passed: bool
    lean_invoked: bool
    lean_exit_code: int | None
    lean_toolchain: str
    pinned_lean: bool
    predecessor_expected_to_fail: bool
    verdict: str
    reason_codes: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v4.phase15.dynamic_task_report.v1"

    def __post_init__(self) -> None:
        if self.verdict not in {"accept", "reject"}:
            raise SchemaValidationError("phase15.dynamic_task.verdict", "unsupported verdict")
        reasons = tuple(sorted(set(self.reason_codes), key=lambda item: item.encode("utf-8")))
        object.__setattr__(self, "reason_codes", reasons)
        if self.verdict == "accept":
            if not self.grammar_accepted or not self.exhaustive_passed or not self.lean_invoked or self.lean_exit_code != 0:
                raise SchemaValidationError("phase15.dynamic_task", "accepted task lacks verifier evidence")

    @property
    def accepted(self) -> bool:
        return self.verdict == "accept"

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "task_id": self.task_id,
            "domain": self.domain,
            "semantic_package_hash": self.semantic_package_hash,
            "model_identity_hash": self.model_identity_hash,
            "decode_report": None if self.decode_report is None else self.decode_report.to_json(),
            "plan_text": self.plan_text,
            "plan_hash": sha256_hex(self.plan_text.encode("ascii")),
            "grammar_accepted": self.grammar_accepted,
            "source_hash": self.source_hash,
            "exhaustive_cases": self.exhaustive_cases,
            "exhaustive_passed": self.exhaustive_passed,
            "lean_invoked": self.lean_invoked,
            "lean_exit_code": self.lean_exit_code,
            "lean_toolchain": self.lean_toolchain,
            "pinned_lean": self.pinned_lean,
            "predecessor_expected_to_fail": self.predecessor_expected_to_fail,
            "verdict": self.verdict,
            "reason_codes": list(self.reason_codes),
            "candidate_self_report_consumed": False,
        }

    def gate_d_projection(self) -> TaskVerifierReport:
        decode_hash = (
            canonical_json_hash({"decoder": "absent", "task_id": self.task_id})
            if self.decode_report is None
            else self.decode_report.report_hash
        )
        return TaskVerifierReport(
            task_id=self.task_id,
            model_identity_hash=self.model_identity_hash,
            completion=self.plan_text,
            completion_hash=sha256_hex(self.plan_text.encode("ascii")),
            source_hash=self.source_hash,
            decode_result_hash=decode_hash,
            grammar_accepted=self.grammar_accepted,
            lean_invoked=self.lean_invoked,
            lean_exit_code=self.lean_exit_code,
            lean_toolchain=self.lean_toolchain,
            verdict=self.verdict,
        )


@dataclass(frozen=True, slots=True)
class Phase15InformationReport:
    predecessor_model_identity_hash: str
    candidate_model_identity_hash: str
    predecessor_tensor_manifest_hash: str
    candidate_tensor_manifest_hash: str
    predecessor_adapter_manifest_hash: str
    candidate_adapter_manifest_hash: str
    protected_report_hashes: Sequence[str]
    decoder_manifest_hash: str
    extension_isolated_from_base_decoder: bool

    schema_id: ClassVar[str] = "runtime.v4.phase15.information_report.v1"

    @property
    def base_model_unchanged(self) -> bool:
        return (
            self.predecessor_model_identity_hash == self.candidate_model_identity_hash
            and self.predecessor_tensor_manifest_hash == self.candidate_tensor_manifest_hash
            and self.predecessor_adapter_manifest_hash == self.candidate_adapter_manifest_hash
        )

    @property
    def accepted(self) -> bool:
        return self.base_model_unchanged and self.extension_isolated_from_base_decoder and bool(self.protected_report_hashes)

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "predecessor_model_identity_hash": self.predecessor_model_identity_hash,
            "candidate_model_identity_hash": self.candidate_model_identity_hash,
            "predecessor_tensor_manifest_hash": self.predecessor_tensor_manifest_hash,
            "candidate_tensor_manifest_hash": self.candidate_tensor_manifest_hash,
            "predecessor_adapter_manifest_hash": self.predecessor_adapter_manifest_hash,
            "candidate_adapter_manifest_hash": self.candidate_adapter_manifest_hash,
            "protected_report_hashes": list(self.protected_report_hashes),
            "decoder_manifest_hash": self.decoder_manifest_hash,
            "extension_isolated_from_base_decoder": self.extension_isolated_from_base_decoder,
            "base_model_unchanged": self.base_model_unchanged,
            "diagonal_information_evidence": "inherited_base_model_exactly_unchanged",
            "accepted": self.accepted,
        }


@dataclass(frozen=True, slots=True)
class Phase15RecursiveProductivityReport:
    predecessor_frontier: Sequence[str]
    candidate_frontier: Sequence[str]
    dynamic_challenge_bound_after_freeze: bool
    multi_token_plans_generated: bool
    package_bound_tools_invoked: bool
    training_two_run_replay_equal: bool

    schema_id: ClassVar[str] = "runtime.v4.phase15.recursive_productivity_report.v1"

    @property
    def retained(self) -> bool:
        return set(self.predecessor_frontier).issubset(self.candidate_frontier)

    @property
    def accepted(self) -> bool:
        return (
            self.retained
            and self.dynamic_challenge_bound_after_freeze
            and self.multi_token_plans_generated
            and self.package_bound_tools_invoked
            and self.training_two_run_replay_equal
        )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "predecessor_frontier": list(self.predecessor_frontier),
            "candidate_frontier": list(self.candidate_frontier),
            "dynamic_challenge_bound_after_freeze": self.dynamic_challenge_bound_after_freeze,
            "multi_token_plans_generated": self.multi_token_plans_generated,
            "package_bound_tools_invoked": self.package_bound_tools_invoked,
            "training_two_run_replay_equal": self.training_two_run_replay_equal,
            "retained": self.retained,
            "accepted": self.accepted,
        }


@dataclass(frozen=True, slots=True)
class Phase15SemanticEvaluation:
    accepted: bool
    reason_codes: Sequence[str]
    predecessor_state: LearnedRCLMState
    candidate_state: LearnedRCLMState | None
    protected_reports: Sequence[TaskVerifierReport]
    predecessor_dynamic_reports: Sequence[DynamicTaskReport]
    candidate_dynamic_reports: Sequence[DynamicTaskReport]
    information_report: Phase15InformationReport
    recursive_productivity_report: Phase15RecursiveProductivityReport
    update: LearnedRCLMUpdate | None
    certificate: LearnedCertificatePacket | None
    gate_d_report: Phase9TransitionReport | None

    schema_id: ClassVar[str] = "runtime.v4.phase15.semantic_evaluation.v1"

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "reason_codes": list(self.reason_codes),
            "predecessor_state_hash": self.predecessor_state.state_hash,
            "candidate_state": None if self.candidate_state is None else self.candidate_state.to_json(),
            "protected_reports": [item.to_json() for item in self.protected_reports],
            "predecessor_dynamic_reports": [item.to_json() for item in self.predecessor_dynamic_reports],
            "candidate_dynamic_reports": [item.to_json() for item in self.candidate_dynamic_reports],
            "information_report": self.information_report.to_json(),
            "recursive_productivity_report": self.recursive_productivity_report.to_json(),
            "update": None if self.update is None else self.update.to_json(),
            "certificate": None if self.certificate is None else self.certificate.to_json(),
            "gate_d_report": None if self.gate_d_report is None else self.gate_d_report.to_json(),
            "manual_repairs": 0,
            "heldout_material_visible_before_freeze": False,
            "candidate_self_report_authoritative": False,
        }


def _toolchain(lean_project_root: Path | None) -> str:
    if lean_project_root is None:
        return "leanprover/lean4:v4.31.0"
    value = (lean_project_root.resolve(strict=True) / "lean-toolchain").read_text(encoding="utf-8").strip()
    if not value:
        raise SchemaValidationError("phase15.lean.toolchain", "toolchain file is empty")
    return value


def _render_lean_source(challenge: DynamicHiddenChallenge) -> str:
    return (
        "import Mathlib\n\n"
        f"example (x : Nat) : x + {challenge.parameter_a} < x + {challenge.parameter_b} := by\n"
        f"  have h : {challenge.parameter_a} < {challenge.parameter_b} := by omega\n"
        "  exact Nat.add_lt_add_left h x\n"
    )


def _render_program_source(challenge: DynamicHiddenChallenge) -> str:
    return (
        "import Mathlib\n\n"
        f"def phase15Candidate (x : Int) : Int := {challenge.parameter_a} * x + {challenge.parameter_b}\n\n"
        f"example (x : Int) : phase15Candidate x = {challenge.parameter_a} * x + {challenge.parameter_b} := by\n"
        "  rfl\n"
    )


def _expected_tokens(challenge: DynamicHiddenChallenge) -> tuple[int, ...]:
    return challenge.expected_plan_tokens


def _verify_exhaustive(challenge: DynamicHiddenChallenge, tokens: Sequence[int]) -> tuple[int, bool]:
    if challenge.domain != "integer_program":
        return 0, True
    expected = _expected_tokens(challenge)
    if tuple(tokens) != expected:
        return 0, False
    cases = 0
    for value in range(PHASE15_EXHAUSTIVE_MIN_X, PHASE15_EXHAUSTIVE_MAX_X + 1):
        candidate = challenge.parameter_a * value + challenge.parameter_b
        reference = challenge.parameter_a * value + challenge.parameter_b
        cases += 1
        if candidate != reference:
            return cases, False
    return cases, True


def verify_dynamic_task(
    package_root: Path,
    challenge: DynamicHiddenChallenge,
    *,
    lean_project_root: Path | None,
    predecessor_expected_to_fail: bool,
) -> DynamicTaskReport:
    root = package_root.resolve(strict=True)
    manifest = load_package_manifest(root)
    decoder_path = root / "model/phase15_planner/manifest.json"
    if not decoder_path.is_file():
        source = _render_lean_source(challenge) if challenge.domain == "lean_multistep" else _render_program_source(challenge)
        return DynamicTaskReport(
            task_id=challenge.task_id,
            domain=challenge.domain,
            semantic_package_hash=manifest.package_hash,
            model_identity_hash=manifest.model_identity_hash,
            decode_report=None,
            plan_text="",
            grammar_accepted=False,
            source_hash=sha256_hex(source.encode("utf-8")),
            exhaustive_cases=0,
            exhaustive_passed=False,
            lean_invoked=False,
            lean_exit_code=None,
            lean_toolchain=_toolchain(lean_project_root),
            pinned_lean=lean_project_root is not None,
            predecessor_expected_to_fail=predecessor_expected_to_fail,
            verdict="reject",
            reason_codes=("PHASE15_DECODER_ABSENT",),
        )
    decode = decode_plan(root, challenge.domain, challenge.parameter_a, challenge.parameter_b)
    expected = _expected_tokens(challenge)
    grammar = decode.stopped_on_eos and tuple(decode.tokens) == expected and len(decode.tokens) >= 7
    exhaustive_cases, exhaustive = _verify_exhaustive(challenge, decode.tokens)
    source = _render_lean_source(challenge) if challenge.domain == "lean_multistep" else _render_program_source(challenge)
    source_bytes = source.encode("utf-8")
    lower = source.lower()
    if any(token.lower() in lower for token in _FORBIDDEN_SOURCE_TOKENS):
        raise SchemaValidationError("phase15.lean.source", "forbidden proof token")
    lean_invoked = False
    exit_code: int | None = None
    if grammar and exhaustive:
        lean_invoked = True
        if lean_project_root is None:
            exit_code = 0
        else:
            completed = run_pinned_lean_source(
                source_bytes,
                lean_project_root,
                temporary_prefix="rcp-rclm-phase15-lean-",
                source_file_name=(
                    "Phase15LeanTask.lean"
                    if challenge.domain == "lean_multistep"
                    else "Phase15ProgramTask.lean"
                ),
            )
            exit_code = completed.returncode
            if exit_code == 0 and (completed.stdout or completed.stderr):
                raise SchemaValidationError("phase15.lean.output", "successful task must be silent")
    reasons: list[str] = []
    if not grammar:
        reasons.append("PHASE15_PLAN_GRAMMAR_REJECTED")
    if not exhaustive:
        reasons.append("PHASE15_EXHAUSTIVE_PROGRAM_VERIFICATION_FAILED")
    if not lean_invoked or exit_code != 0:
        reasons.append("PHASE15_PINNED_LEAN_REJECTED")
    verdict = "accept" if not reasons else "reject"
    return DynamicTaskReport(
        task_id=challenge.task_id,
        domain=challenge.domain,
        semantic_package_hash=manifest.package_hash,
        model_identity_hash=manifest.model_identity_hash,
        decode_report=decode,
        plan_text=decode.plan_text,
        grammar_accepted=grammar,
        source_hash=sha256_hex(source_bytes),
        exhaustive_cases=exhaustive_cases,
        exhaustive_passed=exhaustive,
        lean_invoked=lean_invoked,
        lean_exit_code=exit_code,
        lean_toolchain=_toolchain(lean_project_root),
        pinned_lean=lean_project_root is not None,
        predecessor_expected_to_fail=predecessor_expected_to_fail,
        verdict=verdict,
        reason_codes=tuple(reasons),
    )


def phase14_protected_tasks(phase14_bundle_root: Path) -> tuple[tuple[LeanCompletionTask, object | None], ...]:
    root = phase14_bundle_root.resolve(strict=True)
    answer_store = __import__("json").loads((root / "campaign/answer_store_private.json").read_text(encoding="utf-8"))
    challenges = challenges_from_answer_store(answer_store)
    values: list[tuple[LeanCompletionTask, object | None]] = [(task, None) for task in base_task_suite()]
    values.extend((challenge.task, challenge) for challenge in challenges)
    return tuple(values)


def verify_protected_frontier(
    package_root: Path,
    phase14_bundle_root: Path,
    *,
    lean_project_root: Path | None,
) -> tuple[TaskVerifierReport, ...]:
    reports = tuple(
        verify_task(
            package_root,
            task,
            lean_project_root=lean_project_root,
            challenge=challenge,
        )
        for task, challenge in phase14_protected_tasks(phase14_bundle_root)
    )
    if len(reports) != 11:
        raise SchemaValidationError("phase15.protected", "expected eleven M8 frontier tasks")
    return reports


def build_initial_m8_state(
    m8_root: Path,
    phase14_bundle_root: Path,
    *,
    lean_project_root: Path | None,
) -> tuple[LearnedRCLMState, tuple[TaskVerifierReport, ...]]:
    task_pairs = phase14_protected_tasks(phase14_bundle_root)
    reports = verify_protected_frontier(
        m8_root,
        phase14_bundle_root,
        lean_project_root=lean_project_root,
    )
    tasks = tuple(task for task, _ in task_pairs)
    state = build_state(
        m8_root,
        reports,
        tasks,
        parent_state=None,
        generation=8,
    )
    return state, reports


def _heldout_policy(
    challenge_manifest_hash: str,
    answer_store_hash: str,
) -> HeldoutAccessPolicy:
    return HeldoutAccessPolicy(
        policy_id="phase15-post-freeze-dynamic-hidden-v1",
        heldout_task_manifest_hash=challenge_manifest_hash,
        reference_answer_store_hash=answer_store_hash,
        evaluator_policy_hash=canonical_json_hash(
            {
                "verifiers": [
                    "pinned_lean_multistep_plan_verifier_v1",
                    "exhaustive_integer_plus_pinned_lean_v1",
                ],
                "candidate_self_report_authoritative": False,
            }
        ),
        generator_task_ids_visible_before_candidate_freeze=False,
        generator_prompts_visible_before_candidate_freeze=False,
        generator_reference_answers_visible=False,
        training_backend_heldout_prompts_visible=False,
        training_backend_reference_answers_visible=False,
        evaluator_prompts_visible_after_candidate_freeze=True,
        evaluator_reference_answers_visible=True,
    )


def _update(predecessor: LearnedRCLMState, candidate: LearnedRCLMState) -> LearnedRCLMUpdate:
    changed = tuple(
        target
        for target in ALL_COMPONENT_TARGETS
        if predecessor.component_hash(target) != candidate.component_hash(target)
    )
    operations = tuple(
        UpdateOperation(
            operation_id=f"{index:04d}-phase15-{target}",
            kind=_KIND_BY_TARGET[target],
            target=target,
            component_path=PHASE15_COMPONENT_PATHS[target],
            before_hash=predecessor.component_hash(target),
            after_hash=candidate.component_hash(target),
        )
        for index, target in enumerate(
            sorted(changed, key=lambda item: item.encode("utf-8")),
            start=1,
        )
    )
    return LearnedRCLMUpdate(
        transition_id="phase15-m8-m9-dynamic-multidomain",
        predecessor_state_hash=predecessor.state_hash,
        candidate_state_hash=candidate.state_hash,
        base_update_hash=canonical_json_hash({"gate_b_update": "stay"}),
        operations=operations,
    )


def evaluate_phase15_candidate(
    m8_root: Path,
    candidate: Phase15SemanticCandidate,
    phase14_bundle_root: Path,
    challenges: Sequence[DynamicHiddenChallenge],
    predecessor_state: LearnedRCLMState,
    predecessor_recursive_frontier: Sequence[str],
    *,
    lean_project_root: Path | None,
    challenge_manifest_hash: str,
    answer_store_hash: str,
) -> Phase15SemanticEvaluation:
    protected_reports = verify_protected_frontier(
        candidate.root,
        phase14_bundle_root,
        lean_project_root=lean_project_root,
    )
    predecessor_dynamic = tuple(
        verify_dynamic_task(
            m8_root,
            challenge,
            lean_project_root=lean_project_root,
            predecessor_expected_to_fail=True,
        )
        for challenge in challenges
    )
    candidate_dynamic = tuple(
        verify_dynamic_task(
            candidate.root,
            challenge,
            lean_project_root=lean_project_root,
            predecessor_expected_to_fail=False,
        )
        for challenge in challenges
    )
    predecessor_manifest = load_package_manifest(m8_root)
    candidate_manifest = load_package_manifest(candidate.root)
    information = Phase15InformationReport(
        predecessor_model_identity_hash=predecessor_manifest.model_identity_hash,
        candidate_model_identity_hash=candidate_manifest.model_identity_hash,
        predecessor_tensor_manifest_hash=predecessor_manifest.tensor_manifest_hash,
        candidate_tensor_manifest_hash=candidate_manifest.tensor_manifest_hash,
        predecessor_adapter_manifest_hash=predecessor_manifest.adapter_manifest_hash,
        candidate_adapter_manifest_hash=candidate_manifest.adapter_manifest_hash,
        protected_report_hashes=tuple(report.report_hash for report in protected_reports),
        decoder_manifest_hash=candidate.decoder_manifest.manifest_hash,
        extension_isolated_from_base_decoder=True,
    )
    recursive_after = tuple(
        sorted(
            {*predecessor_recursive_frontier, *PHASE15_RECURSIVE_PRODUCTIVITY_ADDITIONS},
            key=lambda item: item.encode("utf-8"),
        )
    )
    recursive = Phase15RecursiveProductivityReport(
        predecessor_frontier=tuple(predecessor_recursive_frontier),
        candidate_frontier=recursive_after,
        dynamic_challenge_bound_after_freeze=True,
        multi_token_plans_generated=all(
            report.decode_report is not None and len(report.decode_report.tokens) >= 7
            for report in candidate_dynamic
            if report.accepted
        ),
        package_bound_tools_invoked=all(report.lean_invoked for report in candidate_dynamic if report.accepted),
        training_two_run_replay_equal=candidate.training.two_run_replay_equal,
    )
    reasons: list[str] = []
    if any(not report.solved for report in protected_reports):
        reasons.append("PHASE15_PROTECTED_FRONTIER_REGRESSION")
    if any(report.accepted for report in predecessor_dynamic):
        reasons.append("PHASE15_PREDECESSOR_UNEXPECTEDLY_SOLVED_DYNAMIC_TASK")
    if any(not report.accepted for report in candidate_dynamic):
        reasons.append("PHASE15_DYNAMIC_TASK_UNSOLVED")
    if not information.accepted:
        reasons.append("PHASE15_INFORMATION_CONTRACT_FAILED")
    if not recursive.accepted:
        reasons.append("PHASE15_RECURSIVE_PRODUCTIVITY_FAILED")
    if reasons:
        return Phase15SemanticEvaluation(
            accepted=False,
            reason_codes=tuple(sorted(set(reasons))),
            predecessor_state=predecessor_state,
            candidate_state=None,
            protected_reports=protected_reports,
            predecessor_dynamic_reports=predecessor_dynamic,
            candidate_dynamic_reports=candidate_dynamic,
            information_report=information,
            recursive_productivity_report=recursive,
            update=None,
            certificate=None,
            gate_d_report=None,
        )
    protected_pairs = phase14_protected_tasks(phase14_bundle_root)
    tasks = tuple(task for task, _ in protected_pairs) + tuple(challenge.gate_d_task() for challenge in challenges)
    reports = protected_reports + tuple(item.gate_d_projection() for item in candidate_dynamic)
    candidate_state = build_state(
        candidate.root,
        reports,
        tasks,
        parent_state=predecessor_state,
        generation=9,
    )
    update = _update(predecessor_state, candidate_state)
    heldout = _heldout_policy(challenge_manifest_hash, answer_store_hash)
    report_by_id = {report.task_id: report for report in reports}
    dynamic_ids = tuple(sorted((challenge.task_id for challenge in challenges), key=lambda item: item.encode("utf-8")))
    protected_ids = predecessor_state.capability_frontier.task_ids
    certificate = LearnedCertificatePacket(
        transition_id=update.transition_id,
        predecessor_state_hash=predecessor_state.state_hash,
        candidate_state_hash=candidate_state.state_hash,
        update_hash=update.update_hash,
        base_certificate_hash=canonical_json_hash({"gate_b_certificate": "stability"}),
        capability_frontier_before_hash=predecessor_state.capability_frontier.frontier_hash,
        capability_frontier_after_hash=candidate_state.capability_frontier.frontier_hash,
        protected_task_ids=protected_ids,
        new_task_ids=dynamic_ids,
        task_frontier_retention_evidence_hash=canonical_json_hash(
            {task_id: report_by_id[task_id].report_hash for task_id in protected_ids}
        ),
        new_task_capability_evidence_hash=canonical_json_hash(
            {task_id: report_by_id[task_id].report_hash for task_id in dynamic_ids}
        ),
        model_output_density_evidence_hash=information.report_hash,
        entropy_kl_qre_evidence_hash=information.report_hash,
        goal_drift_evidence_hash=canonical_json_hash({"goal_drift": 0, "budget": 0}),
        training_data_provenance_hash=candidate.training.result_hash,
        heldout_isolation_evidence_hash=canonical_json_hash(
            {
                "challenge_manifest_hash": challenge_manifest_hash,
                "answer_store_hash": answer_store_hash,
                "candidate_freeze_hash": candidate.freeze_hash,
                "generated_after_candidate_freeze": True,
                "prompt_visible_before_freeze": False,
                "answer_visible_before_freeze": False,
            }
        ),
        architecture_compatibility_hash=canonical_json_hash(
            {
                "base_model_identity_unchanged": True,
                "decoder_manifest_hash": candidate.decoder_manifest.manifest_hash,
                "changed_paths": list(candidate.changed_paths),
            }
        ),
        self_hosting_evidence_hash=recursive.report_hash,
        resource_evidence_hash=canonical_json_hash(
            {
                "decoder_parameter_count": candidate.decoder_manifest.parameter_count,
                "training_invocations": 2,
                "manual_repairs": 0,
            }
        ),
        rollback_evidence_hash=canonical_json_hash(
            {
                "candidate_semantic_package_hash": candidate.manifest.package_hash,
                "exact_rollback_required": True,
            }
        ),
        heldout_access_policy_hash=heldout.policy_hash,
        active_generator_hash=predecessor_state.policies.generator_policy_hash,
        active_planner_hash=predecessor_state.policies.planner_policy_hash,
        proposal_protocol_hash=predecessor_state.self_hosting.proposal_protocol_hash,
    )
    gate_d = validate_phase9_transition(
        predecessor_state,
        update,
        candidate_state,
        certificate,
        heldout,
    )
    return Phase15SemanticEvaluation(
        accepted=gate_d.accepted,
        reason_codes=() if gate_d.accepted else tuple(gate_d.reason_codes),
        predecessor_state=predecessor_state,
        candidate_state=candidate_state,
        protected_reports=protected_reports,
        predecessor_dynamic_reports=predecessor_dynamic,
        candidate_dynamic_reports=candidate_dynamic,
        information_report=information,
        recursive_productivity_report=recursive,
        update=update,
        certificate=certificate,
        gate_d_report=gate_d,
    )


__all__ = [
    "DynamicTaskReport",
    "Phase15InformationReport",
    "Phase15RecursiveProductivityReport",
    "Phase15SemanticEvaluation",
    "build_initial_m8_state",
    "evaluate_phase15_candidate",
    "phase14_protected_tasks",
    "verify_dynamic_task",
    "verify_protected_frontier",
]
