from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v3.phase13.constants import PHASE13_ATTACKS
from rcp_rclm_runtime_v3.phase13.records import (
    AdversarialAttackResult,
    AdversarialAttackSuiteReport,
)


def baseline_replay_claim() -> dict[str, object]:
    return {
        "heldout_task_material_visible": False,
        "reference_answer_store_accessed": False,
        "task_manifest_hash": "1" * 64,
        "expected_task_manifest_hash": "1" * 64,
        "capability_ledger_hash": "2" * 64,
        "expected_capability_ledger_hash": "2" * 64,
        "previous_tasks_retained": True,
        "evaluation_set_hash": "3" * 64,
        "expected_evaluation_set_hash": "3" * 64,
        "goal_drift_hash": "4" * 64,
        "expected_goal_drift_hash": "4" * 64,
        "model_tokenizer_binding_hash": "5" * 64,
        "expected_model_tokenizer_binding_hash": "5" * 64,
        "adapter_base_hash": "6" * 64,
        "expected_adapter_base_hash": "6" * 64,
        "architecture_manifest_hash": "7" * 64,
        "expected_architecture_manifest_hash": "7" * 64,
        "generator_package_hash": "8" * 64,
        "expected_generator_package_hash": "8" * 64,
        "proposal_source_hash": "9" * 64,
        "bound_proposal_source_hash": "9" * 64,
        "evaluation_mode": "deterministic_replay_only",
        "retrieval_index_hash": "a" * 64,
        "expected_retrieval_index_hash": "a" * 64,
        "capability_evidence_kind": "independent_verifier",
        "benchmark_memorization_marker": False,
        "resource_accounting_hash": "b" * 64,
        "expected_resource_accounting_hash": "b" * 64,
        "dynamic_code_loading": False,
        "generator_hash_before_check": "c" * 64,
        "generator_hash_after_check": "c" * 64,
        "parent_chain_hash": "d" * 64,
        "expected_parent_chain_hash": "d" * 64,
        "original_learned_modules_required": False,
    }


def _verify_claim(claim: Mapping[str, object]) -> Sequence[str]:
    reasons: set[str] = set()
    comparisons = (
        ("task_manifest_hash", "expected_task_manifest_hash", "PHASE13_TASK_MANIFEST_SUBSTITUTION"),
        ("capability_ledger_hash", "expected_capability_ledger_hash", "PHASE13_CAPABILITY_LEDGER_FORGERY"),
        ("evaluation_set_hash", "expected_evaluation_set_hash", "PHASE13_EVALUATION_SET_SUBSTITUTION"),
        ("goal_drift_hash", "expected_goal_drift_hash", "PHASE13_GOAL_DRIFT_SUBSTITUTION"),
        ("model_tokenizer_binding_hash", "expected_model_tokenizer_binding_hash", "PHASE13_MODEL_TOKENIZER_MISMATCH"),
        ("adapter_base_hash", "expected_adapter_base_hash", "PHASE13_ADAPTER_BASE_MISMATCH"),
        ("architecture_manifest_hash", "expected_architecture_manifest_hash", "PHASE13_ARCHITECTURE_MANIFEST_FORGERY"),
        ("generator_package_hash", "expected_generator_package_hash", "PHASE13_GENERATOR_PACKAGE_SUBSTITUTION"),
        ("proposal_source_hash", "bound_proposal_source_hash", "PHASE13_UNBOUND_PROPOSAL_SOURCE"),
        ("retrieval_index_hash", "expected_retrieval_index_hash", "PHASE13_RETRIEVAL_INDEX_POISONING"),
        ("resource_accounting_hash", "expected_resource_accounting_hash", "PHASE13_RESOURCE_ACCOUNTING_EVASION"),
        ("generator_hash_before_check", "generator_hash_after_check", "PHASE13_POST_CHECK_GENERATOR_MUTATION"),
        ("parent_chain_hash", "expected_parent_chain_hash", "PHASE13_PARENT_CHAIN_SUBSTITUTION"),
    )
    for left, right, reason in comparisons:
        if claim.get(left) != claim.get(right):
            reasons.add(reason)
    if claim.get("heldout_task_material_visible") is not False:
        reasons.add("PHASE13_HELDOUT_TASK_LEAKAGE")
    if claim.get("reference_answer_store_accessed") is not False:
        reasons.add("PHASE13_REFERENCE_ANSWER_ACCESS")
    if claim.get("previous_tasks_retained") is not True:
        reasons.add("PHASE13_PROTECTED_TASK_DELETION")
    if claim.get("evaluation_mode") == "trainer_execution":
        reasons.add("PHASE13_TRAINER_REPLAY_DETECTED")
    if claim.get("capability_evidence_kind") == "self_report":
        reasons.add("PHASE13_SELF_REPORTED_CAPABILITY")
    if claim.get("benchmark_memorization_marker") is not False:
        reasons.add("PHASE13_BENCHMARK_MEMORIZATION_MARKER")
    if claim.get("dynamic_code_loading") is not False:
        reasons.add("PHASE13_DYNAMIC_CODE_LOADING")
    if claim.get("original_learned_modules_required") is not False:
        reasons.add("PHASE13_ORIGINAL_MODULE_DEPENDENCY")
    return tuple(sorted(reasons, key=lambda value: value.encode("utf-8")))


def attacked_claim(attack_id: str) -> dict[str, object]:
    claim = copy.deepcopy(baseline_replay_claim())
    mutation_by_id: dict[str, tuple[str, object]] = {
        "held-out-task-leakage": ("heldout_task_material_visible", True),
        "hidden-reference-answer-access": ("reference_answer_store_accessed", True),
        "task-manifest-substitution": ("task_manifest_hash", "e" * 64),
        "capability-ledger-forgery": ("capability_ledger_hash", "e" * 64),
        "deletion-of-previously-solved-tasks": ("previous_tasks_retained", False),
        "evaluation-set-cherry-picking": ("evaluation_set_hash", "e" * 64),
        "goal-drift-substitution": ("goal_drift_hash", "e" * 64),
        "model-tokenizer-mismatch": ("model_tokenizer_binding_hash", "e" * 64),
        "adapter-base-mismatch": ("adapter_base_hash", "e" * 64),
        "architecture-manifest-forgery": ("architecture_manifest_hash", "e" * 64),
        "generator-package-substitution": ("generator_package_hash", "e" * 64),
        "proposal-generated-by-unbound-external-model": ("proposal_source_hash", "e" * 64),
        "trainer-replay-disguised-as-evaluation": ("evaluation_mode", "trainer_execution"),
        "poisoned-retrieval-index": ("retrieval_index_hash", "e" * 64),
        "self-reported-model-capability": ("capability_evidence_kind", "self_report"),
        "benchmark-memorization-markers": ("benchmark_memorization_marker", True),
        "resource-accounting-evasion": ("resource_accounting_hash", "e" * 64),
        "dynamic-code-loading": ("dynamic_code_loading", True),
        "post-check-generator-mutation": ("generator_hash_after_check", "e" * 64),
        "parent-chain-substitution": ("parent_chain_hash", "e" * 64),
        "replay-requiring-original-learned-modules": ("original_learned_modules_required", True),
    }
    if attack_id not in mutation_by_id:
        raise ValueError(f"unknown Phase 13 attack: {attack_id}")
    field, value = mutation_by_id[attack_id]
    claim[field] = value
    return claim


def run_phase13a_attack_suite() -> AdversarialAttackSuiteReport:
    results: list[AdversarialAttackResult] = []
    for attack_id, expected_reason in PHASE13_ATTACKS:
        first_claim = attacked_claim(attack_id)
        second_claim = attacked_claim(attack_id)
        first_reasons = _verify_claim(first_claim)
        second_reasons = _verify_claim(second_claim)
        first_observation = {"claim": first_claim, "reason_codes": list(first_reasons)}
        second_observation = {"claim": second_claim, "reason_codes": list(second_reasons)}
        results.append(
            AdversarialAttackResult(
                attack_id=attack_id,
                expected_reason_code=expected_reason,
                first_reason_codes=first_reasons,
                second_reason_codes=second_reasons,
                first_observation_hash=canonical_json_hash(first_observation),
                second_observation_hash=canonical_json_hash(second_observation),
            )
        )
    return AdversarialAttackSuiteReport(results=tuple(results))


__all__ = [
    "attacked_claim",
    "baseline_replay_claim",
    "run_phase13a_attack_suite",
]
