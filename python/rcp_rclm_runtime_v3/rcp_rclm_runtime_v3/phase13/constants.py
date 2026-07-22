from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

PHASE13A_CONTRACT_VERSION: Final[str] = "rcp-rclm-executable-v3-phase-13a"
PHASE13A_REPLAY_PROFILE: Final[str] = "retained_evidence_worker_free_replay_v1"
PHASE13A_ATTACK_SUITE_VERSION: Final[str] = "phase13-adversarial-closure-v1"

PHASE13_ATTACKS: Final[Sequence[tuple[str, str]]] = (
    ("adapter-base-mismatch", "PHASE13_ADAPTER_BASE_MISMATCH"),
    ("architecture-manifest-forgery", "PHASE13_ARCHITECTURE_MANIFEST_FORGERY"),
    ("benchmark-memorization-markers", "PHASE13_BENCHMARK_MEMORIZATION_MARKER"),
    ("capability-ledger-forgery", "PHASE13_CAPABILITY_LEDGER_FORGERY"),
    ("deletion-of-previously-solved-tasks", "PHASE13_PROTECTED_TASK_DELETION"),
    ("dynamic-code-loading", "PHASE13_DYNAMIC_CODE_LOADING"),
    ("evaluation-set-cherry-picking", "PHASE13_EVALUATION_SET_SUBSTITUTION"),
    ("generator-package-substitution", "PHASE13_GENERATOR_PACKAGE_SUBSTITUTION"),
    ("goal-drift-substitution", "PHASE13_GOAL_DRIFT_SUBSTITUTION"),
    ("held-out-task-leakage", "PHASE13_HELDOUT_TASK_LEAKAGE"),
    ("hidden-reference-answer-access", "PHASE13_REFERENCE_ANSWER_ACCESS"),
    ("model-tokenizer-mismatch", "PHASE13_MODEL_TOKENIZER_MISMATCH"),
    ("parent-chain-substitution", "PHASE13_PARENT_CHAIN_SUBSTITUTION"),
    ("poisoned-retrieval-index", "PHASE13_RETRIEVAL_INDEX_POISONING"),
    ("post-check-generator-mutation", "PHASE13_POST_CHECK_GENERATOR_MUTATION"),
    ("proposal-generated-by-unbound-external-model", "PHASE13_UNBOUND_PROPOSAL_SOURCE"),
    ("replay-requiring-original-learned-modules", "PHASE13_ORIGINAL_MODULE_DEPENDENCY"),
    ("resource-accounting-evasion", "PHASE13_RESOURCE_ACCOUNTING_EVASION"),
    ("self-reported-model-capability", "PHASE13_SELF_REPORTED_CAPABILITY"),
    ("task-manifest-substitution", "PHASE13_TASK_MANIFEST_SUBSTITUTION"),
    ("trainer-replay-disguised-as-evaluation", "PHASE13_TRAINER_REPLAY_DETECTED"),
)

ATTACK_REASON_BY_ID: Final[Mapping[str, str]] = dict(PHASE13_ATTACKS)

FORBIDDEN_REPLAY_MODULE_PREFIXES: Final[Sequence[str]] = (
    "rcp_rclm_runtime_v3.phase10.training_process",
    "rcp_rclm_runtime_v3.phase11.phase11b_training",
    "rcp_rclm_runtime_v3.phase12.phase12b_training",
    "rcp_rclm_runtime_v3.phase12.phase12e_training",
    "torch",
)

FORBIDDEN_REPLAY_PATH_SUFFIXES: Final[Sequence[str]] = (
    "phase10/training_process.py",
    "phase11/phase11b_training.py",
    "phase12/phase12b_training.py",
    "phase12/phase12e_training.py",
    "tools/phase10_training_worker.py",
    "tools/phase11b_training_worker.py",
    "tools/phase12e_training_worker.py",
    "tools/run_phase10_training_reference.py",
    "tools/run_phase11b_training_reference.py",
    "tools/run_phase12b_training_reference.py",
    "tools/run_phase12e_training_reference.py",
)

PHASE12_COMPLETE_REQUIRED_PATHS: Final[Sequence[str]] = (
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase12/phase12e_program.py",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase12/phase12e_tasks.py",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase12/phase12e_candidate.py",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase12/phase12e_lifecycle.py",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase12/phase12e_closure.py",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase12/phase12e_training.py",
    "python/rcp_rclm_executable_core_v3/contract/phase_12_complete_trajectory.schema.json",
    ".github/workflows/runtime-v3-phase-12-complete.yml",
)

PHASE13A_RETAINED_SOURCE_PATHS: Final[Sequence[str]] = (
    "python/rcp_rclm_runtime_v3/phase_10_closure_manifest.json",
    "python/rcp_rclm_runtime_v3/phase_11_closure_manifest.json",
    "docs/executable_core_v3/PHASE_12_VALIDATION.md",
    "docs/executable_core_v3/PHASE_12_EXIT_CRITERIA.md",
    "scripts/run_phase12_complete.py",
    "python/rcp_rclm_runtime_v3/tools/run_phase12d_closure.py",
    "python/rcp_rclm_runtime_v3/tools/run_phase12e_closure.py",
)

PHASE13A_CONTRACT_HASH: Final[str] = canonical_json_hash(
    {
        "schema_id": "runtime.v3.phase13a.contract.v1",
        "contract_version": PHASE13A_CONTRACT_VERSION,
        "replay_profile": PHASE13A_REPLAY_PROFILE,
        "attack_suite_version": PHASE13A_ATTACK_SUITE_VERSION,
        "attacks": [list(item) for item in PHASE13_ATTACKS],
        "forbidden_module_prefixes": list(FORBIDDEN_REPLAY_MODULE_PREFIXES),
        "forbidden_path_suffixes": list(FORBIDDEN_REPLAY_PATH_SUFFIXES),
        "training_invocations": 0,
        "generator_invocations": 0,
        "planner_invocations": 0,
    }
)

__all__ = [name for name in globals() if name.isupper()]
