from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v3.phase11.closure_manifest import (
    load_phase11_closure_manifest,
)
from rcp_rclm_runtime_v3.phase11.phase11b_lifecycle import (
    Phase11BReference,
    build_phase11b_reference,
)
from rcp_rclm_runtime_v3.phase11.records import GeneratorInvocationReport
from rcp_rclm_runtime_v3.phase12.constants import (
    PHASE11_MERGE_COMMIT,
    PHASE12_ACTIVE_GENERATOR_GENERATION,
    PHASE12_ACTIVE_PLANNER_GENERATION,
    PHASE12_COMPONENT_SCHEDULE,
    PHASE12_EXPECTED_FIRST_PROGRAM_BYTES,
    PHASE12_INITIAL_FRONTIER_CARDINALITY,
    PHASE12_PROPOSAL_PROTOCOL_HASH,
    PHASE12_REQUIRED_ACCEPTED_PROMOTIONS,
    PHASE12_REQUIRED_REJECTED_ATTEMPTS,
    PHASE12_TARGET_FRONTIER_CARDINALITY,
)
from rcp_rclm_runtime_v3.phase12.generator import (
    generate_phase12_first_program,
    phase12_generator_input,
    phase12_package_tree_hash,
    validate_phase12_first_program,
)
from rcp_rclm_runtime_v3.phase12.records import (
    Phase12ProgressLedger,
    Phase12StartReasonCode,
    Phase12StartValidationReport,
    default_phase12_trajectory_budget,
)


def _promoted_semantic_binding(
    phase11: Phase11BReference,
    manifest: dict[str, object],
) -> tuple[bool, dict[str, bool]]:
    stable = manifest.get("stable_reference_hashes")
    claim = manifest.get("claim_boundary")
    if not isinstance(stable, dict) or not isinstance(claim, dict):
        return False, {
            "phase11_manifest_shape": False,
            "phase11_exit_closed": False,
            "phase11_atomic_promotion": False,
            "beta_package_bound": False,
            "beta_model_bound": False,
            "successor_generator_bound": False,
            "successor_planner_bound": False,
        }
    checks = {
        "phase11_manifest_shape": True,
        "phase11_exit_closed": claim.get("phase11_exit_closed") is True,
        "phase11_atomic_promotion": claim.get("atomic_content_addressed_promotion") is True,
        "beta_package_bound": (
            stable.get("beta_candidate_package_hash")
            == phase11.beta_candidate.manifest.package_hash
        ),
        "beta_model_bound": (
            stable.get("beta_candidate_model_identity_hash")
            == phase11.beta_candidate.manifest.model_identity_hash
        ),
        "successor_generator_bound": (
            stable.get("successor_generator_hash")
            == phase11.beta_candidate.manifest.generator_policy_hash
        ),
        "successor_planner_bound": (
            stable.get("successor_planner_hash")
            == phase11.beta_candidate.manifest.planner_policy_hash
        ),
    }
    return all(checks.values()), checks


@dataclass(frozen=True, slots=True)
class Phase12AReference:
    phase11: Phase11BReference
    phase11_closure_manifest_hash: str
    promoted_semantic_binding: bool
    promoted_semantic_checks: dict[str, bool]
    first_invocation: GeneratorInvocationReport
    replay_invocation: GeneratorInvocationReport
    first_validation: Phase12StartValidationReport
    package_tree_hash_before: str
    package_tree_hash_after: str
    ledger: Phase12ProgressLedger

    schema_id: ClassVar[str] = "runtime.v3.phase12a.reference.v1"

    @property
    def package_unchanged(self) -> bool:
        return self.package_tree_hash_before == self.package_tree_hash_after

    @property
    def deterministic_replay(self) -> bool:
        return self.first_invocation.to_json() == self.replay_invocation.to_json()

    @property
    def recursive_successor_use(self) -> bool:
        return (
            self.first_invocation.generator_policy_hash
            == self.phase11.beta_candidate.manifest.generator_policy_hash
            and self.first_invocation.planner_policy_hash
            == self.phase11.beta_candidate.manifest.planner_policy_hash
            and self.first_invocation.generator_policy_hash
            != self.phase11.active.active_manifest.generator_policy_hash
            and self.first_invocation.planner_policy_hash
            != self.phase11.active.active_manifest.planner_policy_hash
        )

    @property
    def expected_rejection(self) -> bool:
        return (
            not self.first_validation.accepted
            and self.first_validation.reason_codes
            == (Phase12StartReasonCode.GENERATION_NOT_ADVANCED,)
        )

    @property
    def accepted(self) -> bool:
        state = self.phase11.beta_candidate.candidate_state
        return (
            self.phase11.accepted
            and state is not None
            and len(state.capability_frontier.task_ids)
            == PHASE12_INITIAL_FRONTIER_CARDINALITY
            and self.promoted_semantic_binding
            and self.first_invocation.model_generated
            and self.first_invocation.program_text.encode("ascii")
            == PHASE12_EXPECTED_FIRST_PROGRAM_BYTES
            and self.deterministic_replay
            and self.recursive_successor_use
            and self.expected_rejection
            and self.package_unchanged
            and self.ledger.generator_invocations == 1
            and self.ledger.rejected_attempts == 1
            and self.ledger.candidate_realizations == 0
            and self.ledger.candidate_evaluations == 0
            and self.ledger.accepted_promotions == 0
            and self.ledger.frontier_expansions == 0
            and self.ledger.manual_repairs == 0
        )

    @property
    def reference_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def summary_json(self) -> dict[str, object]:
        state = self.phase11.beta_candidate.candidate_state
        if state is None:
            raise ValueError("Phase 11 promoted successor state is unavailable")
        content = {
            "schema_id": "runtime.v3.phase12a.evidence_summary.v1",
            "contract_version": "rcp-rclm-executable-v3-phase-12a",
            "accepted": self.accepted,
            "phase11_merge_commit": PHASE11_MERGE_COMMIT,
            "phase11_closure_manifest_hash": self.phase11_closure_manifest_hash,
            "active_package_hash": self.phase11.beta_candidate.manifest.package_hash,
            "active_state_hash": state.state_hash,
            "active_model_identity_hash": (
                self.phase11.beta_candidate.manifest.model_identity_hash
            ),
            "active_generator_hash": (
                self.phase11.beta_candidate.manifest.generator_policy_hash
            ),
            "active_planner_hash": (
                self.phase11.beta_candidate.manifest.planner_policy_hash
            ),
            "active_generator_generation": PHASE12_ACTIVE_GENERATOR_GENERATION,
            "active_planner_generation": PHASE12_ACTIVE_PLANNER_GENERATION,
            "proposal_protocol_hash": PHASE12_PROPOSAL_PROTOCOL_HASH,
            "promoted_semantic_binding": self.promoted_semantic_binding,
            "promoted_semantic_checks": {
                key: self.promoted_semantic_checks[key]
                for key in sorted(
                    self.promoted_semantic_checks,
                    key=lambda item: item.encode("utf-8"),
                )
            },
            "first_invocation_hash": self.first_invocation.report_hash,
            "first_program_hash": self.first_invocation.program.program_hash,
            "first_program_text": self.first_invocation.program_text,
            "first_validation_hash": self.first_validation.report_hash,
            "first_validation_accepted": self.first_validation.accepted,
            "first_reason_codes": [
                reason.value for reason in self.first_validation.reason_codes
            ],
            "requested_generator_generation": (
                self.first_invocation.program.successor_generator_generation
            ),
            "requested_planner_generation": (
                self.first_invocation.program.successor_planner_generation
            ),
            "deterministic_generator_replay": self.deterministic_replay,
            "recursive_successor_generator_used": self.recursive_successor_use,
            "active_package_unchanged_after_rejection": self.package_unchanged,
            "heldout_material_consumed": False,
            "manual_repairs": 0,
            "frontier_before": list(state.capability_frontier.task_ids),
            "frontier_before_cardinality": len(state.capability_frontier.task_ids),
            "target_frontier_cardinality": PHASE12_TARGET_FRONTIER_CARDINALITY,
            "required_accepted_promotions": PHASE12_REQUIRED_ACCEPTED_PROMOTIONS,
            "required_rejected_attempts": PHASE12_REQUIRED_REJECTED_ATTEMPTS,
            "component_schedule": list(PHASE12_COMPONENT_SCHEDULE),
            "progress_ledger": self.ledger.to_json(),
            "claim_boundary": {
                "phase12_begun": True,
                "phase11_promoted_successor_reconstructed": True,
                "generation2_successor_generator_used_recursively": True,
                "first_phase12_model_generated_attempt_rejected": True,
                "rejection_preserved_active_package": True,
                "accepted_phase12_promotions": 0,
                "strict_phase12_frontier_expansions": 0,
                "four_promotion_chain_complete": False,
                "phase12_exit_closed": False,
            },
        }
        result = dict(content)
        result["summary_hash"] = canonical_json_hash(content)
        return result

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "phase11_reference_hash": self.phase11.reference_hash,
            "phase11_closure_manifest_hash": self.phase11_closure_manifest_hash,
            "promoted_semantic_binding": self.promoted_semantic_binding,
            "promoted_semantic_checks": dict(self.promoted_semantic_checks),
            "first_invocation": self.first_invocation.to_json(),
            "replay_invocation": self.replay_invocation.to_json(),
            "first_validation": self.first_validation.to_json(),
            "package_tree_hash_before": self.package_tree_hash_before,
            "package_tree_hash_after": self.package_tree_hash_after,
            "package_unchanged": self.package_unchanged,
            "deterministic_replay": self.deterministic_replay,
            "recursive_successor_use": self.recursive_successor_use,
            "ledger": self.ledger.to_json(),
            "summary": self.summary_json(),
        }


def build_phase12a_reference(
    output_root: Path,
    *,
    repo_root: Path,
) -> Phase12AReference:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 12A reference already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    phase11 = build_phase11b_reference(root / "phase11_reference")
    state = phase11.beta_candidate.candidate_state
    if state is None:
        raise ValueError("Phase 11 promoted successor state is unavailable")
    closure_manifest = load_phase11_closure_manifest(repo_root.resolve(strict=True))
    closure_manifest_hash = canonical_json_hash(closure_manifest)
    semantic_binding, semantic_checks = _promoted_semantic_binding(
        phase11,
        closure_manifest,
    )
    active_root = phase11.beta_candidate.root.resolve(strict=True)
    tree_before = phase12_package_tree_hash(active_root)
    generator_input = phase12_generator_input(
        active_root,
        active_state_hash=state.state_hash,
        closure_manifest_hash=closure_manifest_hash,
    )
    first = generate_phase12_first_program(active_root, generator_input)
    replay = generate_phase12_first_program(active_root, generator_input)
    validation = validate_phase12_first_program(first)
    tree_after = phase12_package_tree_hash(active_root)
    ledger = Phase12ProgressLedger(
        total_budget_hash=default_phase12_trajectory_budget().budget_hash,
        generator_invocations=1,
        rejected_attempts=1,
        candidate_realizations=0,
        candidate_evaluations=0,
        accepted_promotions=0,
        frontier_expansions=0,
        manual_repairs=0,
    )
    reference = Phase12AReference(
        phase11=phase11,
        phase11_closure_manifest_hash=closure_manifest_hash,
        promoted_semantic_binding=semantic_binding,
        promoted_semantic_checks=semantic_checks,
        first_invocation=first,
        replay_invocation=replay,
        first_validation=validation,
        package_tree_hash_before=tree_before,
        package_tree_hash_after=tree_after,
        ledger=ledger,
    )
    if not reference.accepted:
        raise ValueError("Phase 12A recursive successor-generator start did not close")
    return reference


def build_phase12a_summary(repo_root: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase12a-summary-") as temporary:
        reference = build_phase12a_reference(
            Path(temporary) / "reference",
            repo_root=repo_root,
        )
        return reference.summary_json()


__all__ = [
    "Phase12AReference",
    "build_phase12a_reference",
    "build_phase12a_summary",
]
