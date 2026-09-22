from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final, Literal, cast

from rcp_rclm_runtime.errors import SchemaValidationError

PHASE16_CONTRACT_VERSION: Final[str] = "rcp-rclm-executable-v4-phase-16-v1"
PHASE16_CAMPAIGN_SCHEMA_ID: Final[str] = "runtime.v4.phase16.campaign.v1"
PHASE16_REPLAY_SCHEMA_ID: Final[str] = "runtime.v4.phase16.replay_report.v1"
PHASE16_CLOSURE_SCHEMA_ID: Final[str] = "runtime.v4.phase16.closure_report.v1"
PHASE16_ATTACK_SCHEMA_ID: Final[str] = "runtime.v4.phase16.attack_suite.v1"
PHASE16_BOOTSTRAP_SCHEMA_ID: Final[str] = "runtime.v4.phase16.bootstrap.v1"
PHASE16_CAPTURE_SCHEMA_ID: Final[str] = "runtime.v4.phase16.capture.v1"
PHASE16_FOUNDATION_SCHEMA_ID: Final[str] = "runtime.v4.phase16.foundation.v1"

PHASE16_EXPECTED_PARENT_HEAD: Final[str] = (
    "f6155bb0a6136eb33be40b851fd642905502cfdf"
)
PHASE16_PHASE15_SOURCE_HEAD: Final[str] = (
    "ba9163c4ab4e3dbc7496cacb004af7f7fe4289da"
)
PHASE16_PHASE15_SOURCE_TREE: Final[str] = (
    "6c709a75c0c575aae44a8b9551b7dd48a408d4ec"
)
PHASE16_PHASE15_FINAL_ARTIFACT_ID: Final[int] = 8917973439
PHASE16_PHASE15_FINAL_ARCHIVE_SHA256: Final[str] = (
    "197465275e7716a7a51eb4ffdc255696bd92129cdf0910e9712b7ca22028053e"
)
PHASE16_PHASE15_BUNDLE_ARTIFACT_ID: Final[int] = 8916353526
PHASE16_PHASE15_BUNDLE_ARCHIVE_SHA256: Final[str] = (
    "56003f95ded054be21dd3f743c2145fdf6e92543af28bb350f64ec8f4fee00b5"
)
PHASE16_PHASE15_CLOSURE_HASH: Final[str] = (
    "3c4d0b90143fddd5bcb1f8d9af266cda7b330dbec774fbe7d43708476fe99e49"
)
PHASE16_PHASE15_TRAJECTORY_HASH: Final[str] = (
    "0ed512aee0a7b75a8e533e189a2dec9840995ba9d583de175981dc931adc5b94"
)
PHASE16_PHASE15_BUNDLE_MANIFEST_HASH: Final[str] = (
    "2426a8f5d4c4f0d327d55970b43441c274ca9b672a4280914a37a55b2ee31661"
)
PHASE16_PHASE15_M9_SEMANTIC_PACKAGE_HASH: Final[str] = (
    "a20e01b73f6b6ab069ce93bcbb43d5b745d3210268a4f958be5e744057e53dc6"
)
PHASE16_PHASE15_FINAL_STORE_HASH: Final[str] = (
    "2fd9aad1e508dae645e20b2545e274c1034fde109b6c2f4d5659eb17497bf472"
)
PHASE16_PHASE15_PLANNER_MANIFEST_HASH: Final[str] = (
    "67045ba2da9dd897b851bba31f05ed0e9faf93fa665245f87803904cfa5fe6d7"
)
PHASE16_PHASE15_PLANNER_WEIGHTS_SHA256: Final[str] = (
    "19869eac5b0da770505214a6c5817b94dfda05730f97598bf2f855aff82d6c8d"
)
PHASE16_PHASE15_PLANNER_MANIFEST_PATH: Final[str] = (
    "campaign/candidate_freeze/multidomain/semantic_candidate/model/"
    "phase15_planner/manifest.json"
)
PHASE16_PHASE15_PLANNER_WEIGHTS_PATH: Final[str] = (
    "campaign/candidate_freeze/multidomain/semantic_candidate/model/"
    "phase15_planner/weights.i16le.bin"
)
PHASE16_FIXED_VERIFIER_HASH: Final[str] = (
    "fc4cf15ec370547b14fc67ae360269cea71cbc10d773536d1a77891acbe3bf7e"
)
PHASE16_PINNED_OUTER_VERIFICATION_HASH: Final[str] = (
    "57f8b2fc389935652279988f7c36b4a79ff9efde0eee080db234dc1a4fb9882e"
)
PHASE16_DIAGONAL_SEMANTICS_ID: Final[str] = (
    "gate-c-diagonal-qre-kl-fixed-semantics-v1"
)
PHASE16_RANKING_POLICY_ID: Final[str] = (
    "phase16-inherited-m9-planner-ranking-novelty-rejection-v1"
)
PHASE16_ENUMERATOR_ID: Final[str] = "phase16-fair-bounded-enumerator-v1"
PHASE16_RESOURCE_POLICY_ID: Final[str] = "phase16-expanding-resource-envelope-v1"
PHASE16_CHALLENGE_POLICY_ID: Final[str] = (
    "phase16-post-freeze-independent-successor-availability-stream-v1"
)

PHASE16_INHERITED_PLANNER_PROJECTION: Final[Sequence[tuple[int, int]]] = (
    (0, -1), (17, -1), (33, -1), (65, -1), (66, -1), (67, -1),
    (68, -1), (69, -1), (70, -1), (71, -1), (72, -1), (73, -1),
    (74, -1), (75, -1), (76, -1), (77, -1), (78, -1), (79, -1),
    (80, -1), (81, -1), (1027, -1), (1031, 1), (1044, -1),
    (1047, 1), (1062, 1), (1066, 1), (1076, -1), (1081, -1),
    (2049, -1), (2065, 2), (2068, -1), (2081, 1), (2103, -1),
    (3075, -1), (3077, -1), (3092, 3), (3093, -1), (3108, -1),
    (3124, -1), (3127, 1), (3129, 1), (4117, 1), (4118, -1),
    (4132, 1), (4133, -1), (5142, 1), (5143, -1), (5157, 1),
    (5158, -1), (6145, 2), (6150, -1), (6161, -1), (6177, 1),
    (6185, -1), (7169, -1), (7171, 2), (7173, -1), (7201, -1),
    (7220, 1), (8197, 2), (8199, -1), (8212, -1), (8234, -1),
    (8244, 1), (9216, 1), (9222, 1), (9257, 1), (12353, 1),
    (13378, 1), (14403, 1), (15428, 1), (16453, 1), (17478, 1),
    (18503, 1), (19528, 1), (20553, 1), (21578, 1), (22603, 1),
    (23628, 1), (24653, 1), (25678, 1), (26703, 1), (27728, 1),
    (28753, 1),
)

PHASE16_SCALING_LADDER: Final[Sequence[int]] = (8, 16, 32, 64)
PHASE16_STRETCH_TARGET: Final[int] = 100
PHASE16_VARIANTS_PER_FAMILY: Final[int] = 4
PHASE16_LEARNED_PREFIX: Final[int] = 4
PHASE16_RESOURCE_STEPS: Final[Sequence[int]] = (4, 8, 16, 32)
PHASE16_ENUMERATION_STRIDE: Final[int] = 17
PHASE16_FAMILY_STRIDE: Final[int] = 5

UpdateFamily = Literal[
    "memory_policy",
    "retrieval_policy",
    "planner_policy",
    "adapter_policy",
    "optimizer_policy",
    "verification_automation_policy",
    "tool_policy",
    "architecture_policy",
]

UPDATE_FAMILIES: Final[Sequence[UpdateFamily]] = (
    "adapter_policy",
    "architecture_policy",
    "memory_policy",
    "optimizer_policy",
    "planner_policy",
    "retrieval_policy",
    "tool_policy",
    "verification_automation_policy",
)

UPDATE_OPERATION_BY_FAMILY: Final[Mapping[UpdateFamily, str]] = {
    "memory_policy": "install_content_addressed_memory_motif",
    "retrieval_policy": "install_rejection_conditioned_retrieval_route",
    "planner_policy": "install_fair_search_planning_rule",
    "adapter_policy": "install_transfer_adapter_motif",
    "optimizer_policy": "install_expanding_resource_schedule",
    "verification_automation_policy": "install_untrusted_proof_search_policy",
    "tool_policy": "install_package_bound_tool_chain",
    "architecture_policy": "install_bounded_execution_route",
}

RECURSIVE_CAPABILITY_BY_FAMILY: Final[Mapping[UpdateFamily, str]] = {
    "memory_policy": "recursive.archive_rejection_context",
    "retrieval_policy": "recursive.retrieve_mutation_motifs",
    "planner_policy": "recursive.plan_fair_search_prefix",
    "adapter_policy": "recursive.transfer_verified_mutation_motif",
    "optimizer_policy": "recursive.expand_resource_envelope",
    "verification_automation_policy": "recursive.produce_root_checked_proof_attempt",
    "tool_policy": "recursive.invoke_package_bound_search_tool",
    "architecture_policy": "recursive.select_bounded_execution_route",
}

ARCHIVE_KINDS: Final[Sequence[str]] = (
    "candidate_program",
    "counterexample",
    "failed_proof_attempt",
    "proposal_hypothesis",
    "recursive_productivity_probe",
    "rejection_reason",
    "resource_use",
    "successful_mutation_motif",
    "transfer_evaluation",
)

PHASE16_INITIAL_CAPABILITY_FRONTIER: Final[Sequence[str]] = (
    "lean.phase10.heldout.linear_gap",
    "lean.phase10.protected.reflexive_seven",
    "lean.phase11.heldout.add_zero_macro",
    "lean.phase12.generation1.le_refl_macro",
    "lean.phase12.generation2.zero_le_macro",
    "lean.phase12.generation3.lt_succ_planner_macro",
    "lean.phase12.generation4.lt_add_two_adapter_macro",
    "lean.phase14.generation5_zero_lt_succ",
    "lean.phase14.generation6_lt_add_five",
    "lean.phase14.generation7_succ_le_add_two",
    "lean.phase14.generation8_le_add_four",
    "lean.phase15.dynamic.multistep.4a7a415bcd169bb8",
    "program.phase15.dynamic.affine.beb80dc125251a70",
)

PHASE16_INITIAL_RECURSIVE_FRONTIER: Final[Sequence[str]] = (
    "recursive.bind_hidden_commitment",
    "recursive.bind_post_freeze_dynamic_challenge",
    "recursive.choose_update_family",
    "recursive.generate_multi_token_plan",
    "recursive.generate_valid_program",
    "recursive.install_adapter_route",
    "recursive.install_weight_route",
    "recursive.invoke_package_bound_tool",
    "recursive.persist_search_route",
    "recursive.recover_after_rejection",
    "recursive.self_modify_generator_planner",
)

PHASE16_DEFAULT_SEEDS: Final[Sequence[str]] = (
    "phase16-seed-alpha",
    "phase16-seed-beta",
)
PHASE16_DEFAULT_STREAMS: Final[Sequence[str]] = (
    "dynamic-stream-a",
    "dynamic-stream-b",
)
PHASE16_PLATFORMS: Final[Sequence[str]] = ("macos", "ubuntu", "windows")


def cast_update_family(
    value: str,
    path: str = "phase16.update_family",
) -> UpdateFamily:
    if value not in UPDATE_FAMILIES:
        raise SchemaValidationError(path, f"unsupported update family: {value}")
    return cast(UpdateFamily, value)


__all__ = [name for name in globals() if name.startswith("PHASE16_")] + [
    "ARCHIVE_KINDS",
    "RECURSIVE_CAPABILITY_BY_FAMILY",
    "UPDATE_FAMILIES",
    "UPDATE_OPERATION_BY_FAMILY",
    "UpdateFamily",
    "cast_update_family",
]
