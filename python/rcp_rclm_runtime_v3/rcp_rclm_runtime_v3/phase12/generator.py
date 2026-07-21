from __future__ import annotations

from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
    sha256_hex,
)
from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase10.constants import EOS_TOKEN_ID, VOCAB_SIZE
from rcp_rclm_runtime_v3.phase10.package import ModelPackageManifest, load_package_manifest
from rcp_rclm_runtime_v3.phase10.sparse_profile import exact_dyadic_distribution
from rcp_rclm_runtime_v3.phase11.phase11b_program import parse_phase11b_program
from rcp_rclm_runtime_v3.phase11.records import (
    GeneratorDecodeStep,
    GeneratorInvocationReport,
    InvocationBudget,
    ModelGeneratorInput,
)
from rcp_rclm_runtime_v3.phase12.constants import (
    PHASE12_ACTIVE_GENERATOR_GENERATION,
    PHASE12_ACTIVE_PLANNER_GENERATION,
    PHASE12_ACTIVE_PROPOSAL_PROTOCOL_HASH,
    PHASE12_EXPECTED_FIRST_PROGRAM_BYTES,
    PHASE12_PROPOSAL_PROTOCOL_HASH,
    PHASE12_RECURSIVE_BANK_CAPACITY,
    PHASE12_RECURSIVE_BANK_START,
    PHASE12_TRAJECTORY_ID,
)
from rcp_rclm_runtime_v3.phase12.records import (
    Phase12StartReasonCode,
    Phase12StartValidationReport,
)


def phase12_objective_hash() -> str:
    return canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase12.objective.v1",
            "trajectory_id": PHASE12_TRAJECTORY_ID,
            "objective": "four_strict_self_hosted_frontier_expansions",
            "protected_capability_retention_required": True,
            "selected_information_nonregression_required": True,
            "candidate_self_report_authoritative": False,
            "trajectory_protocol_hash": PHASE12_PROPOSAL_PROTOCOL_HASH,
        }
    )


def phase12_first_invocation_budget() -> InvocationBudget:
    return InvocationBudget(
        max_wall_clock_seconds=1,
        max_accelerator_count=0,
        max_training_steps=1,
        max_output_bytes=96,
        max_candidate_count=1,
        max_evaluation_calls=1,
    )


def phase12_package_tree_hash(package_root: Path) -> str:
    return semantic_tree_hash(build_tree_records(package_root.resolve(strict=True)))


def _policy_object(package_root: Path, relative_path: str) -> dict[str, object]:
    value = load_json_strict(
        (package_root.resolve(strict=True) / relative_path).read_bytes(),
        require_canonical=True,
    )
    if not isinstance(value, dict):
        raise SchemaValidationError("phase12.policy", f"expected object at {relative_path}")
    return value


def _validate_successor_policy(
    package_root: Path,
    manifest: ModelPackageManifest,
) -> tuple[dict[str, object], dict[str, object]]:
    generator = _policy_object(package_root, "policies/generator_policy.json")
    planner = _policy_object(package_root, "policies/planner_policy.json")
    if generator.get("policy") != "installed_self_hosted_typed_mutation_generator":
        raise SchemaValidationError("phase12.generator.policy", "unexpected generator policy")
    if generator.get("generation") != PHASE12_ACTIVE_GENERATOR_GENERATION:
        raise SchemaValidationError("phase12.generator.policy", "generation mismatch")
    if generator.get("proposal_protocol_hash") != PHASE12_ACTIVE_PROPOSAL_PROTOCOL_HASH:
        raise SchemaValidationError("phase12.generator.policy", "proposal protocol mismatch")
    if generator.get("next_proposal_authority") is not True:
        raise SchemaValidationError("phase12.generator.policy", "proposal authority is disabled")
    if generator.get("direct_candidate_write") is not False:
        raise SchemaValidationError("phase12.generator.policy", "direct candidate write is forbidden")
    if generator.get("heldout_material_visible") is not False:
        raise SchemaValidationError("phase12.generator.policy", "held-out material must remain hidden")
    if planner.get("policy") != "installed_self_hosted_bounded_experiment_planner":
        raise SchemaValidationError("phase12.planner.policy", "unexpected planner policy")
    if planner.get("generation") != PHASE12_ACTIVE_PLANNER_GENERATION:
        raise SchemaValidationError("phase12.planner.policy", "generation mismatch")
    if planner.get("bounded_within_run") is not True:
        raise SchemaValidationError("phase12.planner.policy", "planner is not bounded")
    if manifest.generator_policy_hash != canonical_json_hash(generator):
        raise SchemaValidationError("phase12.generator.policy", "manifest binding mismatch")
    if manifest.planner_policy_hash != canonical_json_hash(planner):
        raise SchemaValidationError("phase12.planner.policy", "manifest binding mismatch")
    return generator, planner


def phase12_generator_input(
    package_root: Path,
    *,
    active_state_hash: str,
    closure_manifest_hash: str,
) -> ModelGeneratorInput:
    root = package_root.resolve(strict=True)
    manifest = load_package_manifest(root)
    _validate_successor_policy(root, manifest)
    observation_hash = canonical_json_hash(
        {
            "schema_id": "runtime.v3.phase12.start_observation.v1",
            "active_state_hash": active_state_hash,
            "phase11_closure_manifest_hash": closure_manifest_hash,
            "active_generator_generation": PHASE12_ACTIVE_GENERATOR_GENERATION,
            "active_planner_generation": PHASE12_ACTIVE_PLANNER_GENERATION,
            "accepted_phase12_promotions": 0,
            "prior_phase12_rejections": 0,
            "heldout_answer_material_present": False,
            "phase12_trajectory_protocol_hash": PHASE12_PROPOSAL_PROTOCOL_HASH,
        }
    )
    return ModelGeneratorInput(
        transition_id=PHASE12_TRAJECTORY_ID,
        invocation_id="phase12-generation2-recursive-invocation-0",
        invocation_index=0,
        active_package_hash=manifest.package_hash,
        active_state_hash=active_state_hash,
        model_identity_hash=manifest.model_identity_hash,
        active_generator_hash=manifest.generator_policy_hash,
        active_planner_hash=manifest.planner_policy_hash,
        proposal_protocol_hash=PHASE12_ACTIVE_PROPOSAL_PROTOCOL_HASH,
        objective_hash=phase12_objective_hash(),
        observation_hash=observation_hash,
        budget=phase12_first_invocation_budget(),
        manual_repair_count=0,
    )


def generate_phase12_first_program(
    package_root: Path,
    generator_input: ModelGeneratorInput,
) -> GeneratorInvocationReport:
    root = package_root.resolve(strict=True)
    manifest = load_package_manifest(root)
    _validate_successor_policy(root, manifest)
    bindings = (
        (generator_input.active_package_hash, manifest.package_hash, "package"),
        (generator_input.model_identity_hash, manifest.model_identity_hash, "model"),
        (generator_input.active_generator_hash, manifest.generator_policy_hash, "generator"),
        (generator_input.active_planner_hash, manifest.planner_policy_hash, "planner"),
        (
            generator_input.proposal_protocol_hash,
            PHASE12_ACTIVE_PROPOSAL_PROTOCOL_HASH,
            "active package proposal protocol",
        ),
        (generator_input.objective_hash, phase12_objective_hash(), "objective"),
    )
    for observed, expected, label in bindings:
        if observed != expected:
            raise SchemaValidationError("phase12.generator.input", f"{label} binding mismatch")
    output = bytearray()
    steps: list[GeneratorDecodeStep] = []
    stopped = False
    for position in range(PHASE12_RECURSIVE_BANK_CAPACITY):
        state_token = PHASE12_RECURSIVE_BANK_START + position
        scores, distribution = exact_dyadic_distribution(root, state_token)
        selected = min(range(VOCAB_SIZE), key=lambda token: (-scores[token], token))
        ordered = sorted(scores, reverse=True)
        runner_up = ordered[1] if len(ordered) > 1 else ordered[0]
        steps.append(
            GeneratorDecodeStep(
                position=position,
                state_token_id=state_token,
                selected_token_id=selected,
                selected_score=scores[selected],
                runner_up_score=runner_up,
                distribution_hash=canonical_json_hash(
                    [probability.to_json() for probability in distribution]
                ),
            )
        )
        if selected == EOS_TOKEN_ID:
            stopped = True
            break
        if not 0 <= selected < 256:
            raise SchemaValidationError(
                "phase12.generator.output",
                "typed mutation output contains a non-byte token",
            )
        output.append(selected)
        if len(output) > generator_input.budget.max_output_bytes:
            raise SchemaValidationError(
                "phase12.generator.output",
                "model output exceeded the fixed invocation budget",
            )
    if not stopped:
        raise SchemaValidationError("phase12.generator.output", "model output did not terminate")
    raw = bytes(output)
    if raw != PHASE12_EXPECTED_FIRST_PROGRAM_BYTES:
        raise SchemaValidationError(
            "phase12.generator.output",
            "generation-2 package emitted an unexpected first program",
        )
    program = parse_phase11b_program(raw)
    return GeneratorInvocationReport(
        generator_input=generator_input,
        program_text=raw.decode("ascii"),
        program_raw_sha256=sha256_hex(raw),
        program=program,
        steps=tuple(steps),
        stopped_on_eos=True,
        package_hash=manifest.package_hash,
        model_identity_hash=manifest.model_identity_hash,
        generator_policy_hash=manifest.generator_policy_hash,
        planner_policy_hash=manifest.planner_policy_hash,
    )


def validate_phase12_first_program(
    invocation: GeneratorInvocationReport,
) -> Phase12StartValidationReport:
    generator_input = invocation.generator_input
    program = invocation.program
    bindings = {
        "active_package_bound": invocation.package_hash == generator_input.active_package_hash,
        "active_model_bound": invocation.model_identity_hash == generator_input.model_identity_hash,
        "active_generator_bound": (
            invocation.generator_policy_hash == generator_input.active_generator_hash
        ),
        "active_planner_bound": (
            invocation.planner_policy_hash == generator_input.active_planner_hash
        ),
        "proposal_protocol_bound": (
            generator_input.proposal_protocol_hash
            == PHASE12_ACTIVE_PROPOSAL_PROTOCOL_HASH
        ),
        "objective_bound": generator_input.objective_hash == phase12_objective_hash(),
        "model_generated": invocation.model_generated,
        "output_within_budget": invocation.output_within_budget,
        "heldout_material_hidden": not program.data_selection.heldout_material_visible,
        "manual_repair_absent": generator_input.manual_repair_count == 0,
        "program_bytes_bound": (
            invocation.program_text.encode("ascii")
            == PHASE12_EXPECTED_FIRST_PROGRAM_BYTES
        ),
    }
    reasons: set[Phase12StartReasonCode] = set()
    if not all(bindings.values()):
        reasons.add(Phase12StartReasonCode.BINDING_MISMATCH)
    if not invocation.output_within_budget:
        reasons.add(Phase12StartReasonCode.OUTPUT_BUDGET_EXCEEDED)
    if program.data_selection.heldout_material_visible:
        reasons.add(Phase12StartReasonCode.HELDOUT_ACCESS_REQUESTED)
    if generator_input.manual_repair_count != 0:
        reasons.add(Phase12StartReasonCode.MANUAL_REPAIR_REQUESTED)
    if invocation.program_text.encode("ascii") != PHASE12_EXPECTED_FIRST_PROGRAM_BYTES:
        reasons.add(Phase12StartReasonCode.PROGRAM_MISMATCH)
    selected = set(program.selected_update_classes)
    generation_stale = (
        "generator_update" in selected
        and program.successor_generator_generation
        <= PHASE12_ACTIVE_GENERATOR_GENERATION
    ) or (
        "planner_update" in selected
        and program.successor_planner_generation
        <= PHASE12_ACTIVE_PLANNER_GENERATION
    )
    if generation_stale:
        reasons.add(Phase12StartReasonCode.GENERATION_NOT_ADVANCED)
    return Phase12StartValidationReport(
        invocation_hash=invocation.report_hash,
        program_hash=program.program_hash,
        active_generator_generation=PHASE12_ACTIVE_GENERATOR_GENERATION,
        active_planner_generation=PHASE12_ACTIVE_PLANNER_GENERATION,
        requested_generator_generation=program.successor_generator_generation,
        requested_planner_generation=program.successor_planner_generation,
        binding_checks=bindings,
        reason_codes=tuple(reasons),
    )


__all__ = [
    "generate_phase12_first_program",
    "phase12_first_invocation_budget",
    "phase12_generator_input",
    "phase12_objective_hash",
    "phase12_package_tree_hash",
    "validate_phase12_first_program",
]
