from __future__ import annotations

from typing import Final

from rcp_rclm_runtime.canonical.json import canonical_json_bytes

STATE_PATH: Final[str] = "state/rclm_state.json"
VERIFICATION_POLICY_PATH: Final[str] = "policies/verification_policy.json"
MEMORY_POLICY_PATH: Final[str] = "policies/memory_policy.json"
RETRIEVAL_POLICY_PATH: Final[str] = "policies/retrieval_policy.json"
TOOL_POLICY_PATH: Final[str] = "policies/tool_policy.json"
ARCHITECTURE_PATH: Final[str] = "architecture/reference_runtime.py"


def baseline_verification_policy() -> dict[str, object]:
    return {
        "schema_id": "runtime.reference_verification_policy.v2",
        "policy_id": "reference.verification.baseline.v1",
        "policy_semantics": {
            "candidate_assertions_authoritative": False,
            "evidence_binding": [
                "candidate",
                "certificate",
            ],
            "failure_mode": "reject",
            "required_verifiers": [
                "phase3_checker",
            ],
        },
    }


def hardened_verification_policy() -> dict[str, object]:
    return {
        "schema_id": "runtime.reference_verification_policy.v2",
        "policy_id": "reference.verification.hardened.v1",
        "policy_semantics": {
            "candidate_assertions_authoritative": False,
            "evidence_binding": [
                "candidate",
                "certificate",
                "parent_manifest",
                "resource_record",
                "trust_anchor",
            ],
            "failure_mode": "reject",
            "required_verifiers": [
                "phase3_checker",
                "phase4_hardened_checker",
                "pinned_lean_bridge",
            ],
        },
    }


def baseline_memory_policy() -> dict[str, object]:
    return {
        "schema_id": "runtime.reference_memory_policy.v2",
        "policy_id": "reference.memory.bounded.v1",
        "policy_semantics": {
            "history_mode": "bounded_snapshot",
            "parent_hash_required": True,
            "replay_index": "local",
            "rollback_snapshot": "optional",
            "tree_hash_required": True,
        },
    }


def content_addressed_memory_policy() -> dict[str, object]:
    return {
        "schema_id": "runtime.reference_memory_policy.v2",
        "policy_id": "reference.memory.content_addressed.v1",
        "policy_semantics": {
            "history_mode": "append_only_content_addressed",
            "parent_hash_required": True,
            "replay_index": "content_addressed",
            "rollback_snapshot": "required",
            "tree_hash_required": True,
        },
    }


def fixed_retrieval_policy() -> dict[str, object]:
    return {
        "schema_id": "runtime.reference_retrieval_policy.v2",
        "policy_id": "reference.retrieval.fixed.v1",
        "policy_semantics": {
            "network_access": False,
            "reference_answer_access": False,
            "source": "predecessor_package_only",
        },
    }


def fixed_tool_policy() -> dict[str, object]:
    return {
        "schema_id": "runtime.reference_tool_policy.v2",
        "policy_id": "reference.tools.fixed.v1",
        "policy_semantics": {
            "checker_write_access": False,
            "promotion_ledger_write_access": False,
            "trust_anchor_access": False,
            "workspace_scope": "isolated_candidate_only",
        },
    }


def reference_architecture_source() -> bytes:
    return (
        "from __future__ import annotations\n"
        "\n"
        "REFERENCE_RUNTIME_ARCHITECTURE = (\n"
        "    'generator-proposal',\n"
        "    'host-selection',\n"
        "    'isolated-realization',\n"
        "    'fail-closed-checking',\n"
        ")\n"
    ).encode("utf-8")


def policy_bytes(value: dict[str, object]) -> bytes:
    return canonical_json_bytes(value)
