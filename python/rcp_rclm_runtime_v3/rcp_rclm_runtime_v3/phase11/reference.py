from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v3.phase11.bootstrap import (
    Phase11BootstrapFixture,
    build_phase11_bootstrap,
)
from rcp_rclm_runtime_v3.phase11.constants import (
    ACCEPTED_PROGRAM_TEXT,
    PHASE11_OBJECTIVE,
    PROPOSAL_PROTOCOL_HASH,
    REJECTED_PROGRAM_TEXT,
)
from rcp_rclm_runtime_v3.phase11.generator import (
    generate_typed_mutation_program,
    phase11_objective_hash,
    validate_generated_program,
)
from rcp_rclm_runtime_v3.phase11.records import (
    BudgetLedger,
    GeneratorInvocationReport,
    ModelGeneratorInput,
    Phase11ReasonCode,
    ProgramValidationReport,
)


def _observation_hash(
    bootstrap: Phase11BootstrapFixture,
    prior_validation: ProgramValidationReport | None,
) -> str:
    return canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase11.generator_observation.v1",
            "active_state_hash": bootstrap.active_state.state_hash,
            "capability_frontier_hash": (
                bootstrap.active_state.capability_frontier.frontier_hash
            ),
            "prior_validation_report_hash": (
                None if prior_validation is None else prior_validation.report_hash
            ),
            "prior_accepted": (
                None if prior_validation is None else prior_validation.accepted
            ),
            "heldout_answer_material_present": False,
        }
    )


def _input(
    bootstrap: Phase11BootstrapFixture,
    *,
    invocation_index: int,
    prior_validation: ProgramValidationReport | None,
) -> ModelGeneratorInput:
    return ModelGeneratorInput(
        transition_id="phase11-autonomous-proposal-sequence",
        invocation_id=f"phase11-generator-invocation-{invocation_index}",
        invocation_index=invocation_index,
        active_package_hash=bootstrap.active_manifest.package_hash,
        active_state_hash=bootstrap.active_state.state_hash,
        model_identity_hash=bootstrap.active_manifest.model_identity_hash,
        active_generator_hash=bootstrap.active_manifest.generator_policy_hash,
        active_planner_hash=bootstrap.active_manifest.planner_policy_hash,
        proposal_protocol_hash=PROPOSAL_PROTOCOL_HASH,
        objective_hash=phase11_objective_hash(),
        observation_hash=_observation_hash(bootstrap, prior_validation),
        budget=bootstrap.budget,
        manual_repair_count=0,
    )


@dataclass(frozen=True, slots=True)
class Phase11AReference:
    bootstrap: Phase11BootstrapFixture
    first_invocation: GeneratorInvocationReport
    first_validation: ProgramValidationReport
    second_invocation: GeneratorInvocationReport
    second_validation: ProgramValidationReport
    ledger: BudgetLedger

    schema_id: ClassVar[str] = "runtime.v3.phase11a.reference.v1"

    @property
    def accepted(self) -> bool:
        first_reasons = set(self.first_validation.reason_codes)
        return (
            self.bootstrap.accepted
            and self.first_invocation.model_generated
            and not self.first_validation.accepted
            and Phase11ReasonCode.FORBIDDEN_UPDATE_CLASS in first_reasons
            and Phase11ReasonCode.BUDGET_EXCEEDED in first_reasons
            and self.second_invocation.model_generated
            and self.second_validation.accepted
            and self.first_invocation.generator_input.input_hash
            != self.second_invocation.generator_input.input_hash
            and self.first_invocation.program.program_hash
            != self.second_invocation.program.program_hash
            and self.first_invocation.program_text == REJECTED_PROGRAM_TEXT
            and self.second_invocation.program_text == ACCEPTED_PROGRAM_TEXT
            and not self.first_invocation.program.data_selection.heldout_material_visible
            and not self.second_invocation.program.data_selection.heldout_material_visible
            and self.ledger.generator_invocations == 2
            and self.ledger.candidate_count_consumed == 2
            and self.ledger.evaluation_calls_consumed == 2
            and self.ledger.manual_repair_count == 0
        )

    @property
    def reference_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def summary_json(self) -> dict[str, object]:
        content = {
            "schema_id": "runtime.v3.phase11a.evidence_summary.v1",
            "accepted": self.accepted,
            "phase10_merge_commit": "52acaa820d75380b8766a2d7f4f78226645acc1f",
            "active_package_hash": self.bootstrap.active_manifest.package_hash,
            "active_state_hash": self.bootstrap.active_state.state_hash,
            "active_model_identity_hash": self.bootstrap.active_manifest.model_identity_hash,
            "active_generator_hash": self.bootstrap.active_manifest.generator_policy_hash,
            "active_planner_hash": self.bootstrap.active_manifest.planner_policy_hash,
            "proposal_protocol_hash": PROPOSAL_PROTOCOL_HASH,
            "objective": PHASE11_OBJECTIVE,
            "objective_hash": phase11_objective_hash(),
            "bootstrap_report_hash": self.bootstrap.validation_report["report_hash"],
            "first_invocation_hash": self.first_invocation.report_hash,
            "first_program_hash": self.first_invocation.program.program_hash,
            "first_validation_hash": self.first_validation.report_hash,
            "first_validation_accepted": self.first_validation.accepted,
            "first_reason_codes": [
                reason.value for reason in self.first_validation.reason_codes
            ],
            "second_invocation_hash": self.second_invocation.report_hash,
            "second_program_hash": self.second_invocation.program.program_hash,
            "second_validation_hash": self.second_validation.report_hash,
            "second_validation_accepted": self.second_validation.accepted,
            "budget_hash": self.bootstrap.budget.budget_hash,
            "budget_ledger": self.ledger.to_json(),
            "manual_repair_count": self.ledger.manual_repair_count,
            "heldout_material_consumed": False,
            "claim_boundary": {
                "host_installed_active_generator_bootstrap": True,
                "bootstrap_counted_as_autonomous_improvement": False,
                "active_predecessor_model_generated_proposal": True,
                "model_generated_proposal_rejected": True,
                "fresh_model_generated_typed_program_validated": True,
                "model_generated_candidate_realized": False,
                "model_generated_candidate_rejected": False,
                "model_generated_candidate_promoted": False,
                "successor_generator_planner_installed": False,
                "modified_successor_generator_used_recursively": False,
                "phase11_exit_closed": False,
            },
        }
        result = dict(content)
        result["summary_hash"] = canonical_json_hash(content)
        return result

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "bootstrap": self.bootstrap.to_json(),
            "first_invocation": self.first_invocation.to_json(),
            "first_validation": self.first_validation.to_json(),
            "second_invocation": self.second_invocation.to_json(),
            "second_validation": self.second_validation.to_json(),
            "ledger": self.ledger.to_json(),
            "summary": self.summary_json(),
        }


def build_phase11a_reference(output_root: Path) -> Phase11AReference:
    bootstrap = build_phase11_bootstrap(output_root)
    first_input = _input(
        bootstrap,
        invocation_index=0,
        prior_validation=None,
    )
    first_invocation = generate_typed_mutation_program(
        bootstrap.active_package_root,
        first_input,
    )
    first_validation = validate_generated_program(first_invocation)
    second_input = _input(
        bootstrap,
        invocation_index=1,
        prior_validation=first_validation,
    )
    second_invocation = generate_typed_mutation_program(
        bootstrap.active_package_root,
        second_input,
    )
    second_validation = validate_generated_program(second_invocation)
    ledger = BudgetLedger(
        budget_hash=bootstrap.budget.budget_hash,
        generator_invocations=2,
        candidate_count_consumed=2,
        evaluation_calls_consumed=2,
        manual_repair_count=0,
    )
    reference = Phase11AReference(
        bootstrap=bootstrap,
        first_invocation=first_invocation,
        first_validation=first_validation,
        second_invocation=second_invocation,
        second_validation=second_validation,
        ledger=ledger,
    )
    if not reference.accepted:
        raise ValueError("Phase 11A autonomous proposal reference did not close")
    return reference


__all__ = ["Phase11AReference", "build_phase11a_reference"]
