from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest

from rcp_rclm_runtime_v4.phase14.constants import (
    PHASE14_OBJECTIVE_ID,
    PHASE14_ROUTE_MARKER,
    PHASE14_SEARCH_COST_PER_ATTEMPT,
    PHASE14_SLOT_COUNT,
    PHASE14_SLOT_START,
    UPDATE_FAMILIES,
    UPDATE_KINDS_BY_FAMILY,
    ProgramVariant,
    UpdateFamily,
    cast_update_family,
    commitment_requires_probe,
)
from rcp_rclm_runtime_v4.phase14.records import (
    Phase14MutationProgram,
    Phase14ProposalEnumeration,
    Phase14SearchHistory,
)

_GENERATOR_POLICY_PATH: Final[str] = "policies/generator_policy.json"
_PLANNER_POLICY_PATH: Final[str] = "policies/planner_policy.json"
_RNG_STATE_PATH: Final[str] = "runtime/rng_state.json"


def package_tree_hash(root: Path) -> str:
    return semantic_tree_hash(build_tree_records(root.resolve(strict=True)))


def slot_from_commitment(commitment_hash: str) -> int:
    if len(commitment_hash) != 64 or any(character not in "0123456789abcdef" for character in commitment_hash):
        raise SchemaValidationError(
            "phase14.challenge_commitment_hash",
            "expected lowercase SHA-256",
        )
    return PHASE14_SLOT_START + int(commitment_hash[:8], 16) % PHASE14_SLOT_COUNT


def _object(path: Path, label: str) -> dict[str, object]:
    value = load_json_strict(path.read_bytes(), require_canonical=True)
    if not isinstance(value, dict):
        raise SchemaValidationError(label, "expected canonical JSON object")
    return value


def _policy_seed(root: Path, history_hash: str) -> tuple[str, str, str]:
    manifest = load_package_manifest(root)
    generator = _object(root / _GENERATOR_POLICY_PATH, "phase14.generator_policy")
    planner = _object(root / _PLANNER_POLICY_PATH, "phase14.planner_policy")
    rng = _object(root / _RNG_STATE_PATH, "phase14.rng_state")
    generator_hash = canonical_json_hash(generator)
    planner_hash = canonical_json_hash(planner)
    if generator_hash != manifest.generator_policy_hash:
        raise SchemaValidationError("phase14.generator_policy", "manifest binding mismatch")
    if planner_hash != manifest.planner_policy_hash:
        raise SchemaValidationError("phase14.planner_policy", "manifest binding mismatch")
    seed = canonical_json_hash(
        {
            "schema_id": "runtime.v4.phase14.package_policy_seed.v1",
            "semantic_package_hash": manifest.package_hash,
            "model_identity_hash": manifest.model_identity_hash,
            "generator_policy_hash": generator_hash,
            "planner_policy_hash": planner_hash,
            "rng_state_hash": canonical_json_hash(rng),
            "history_hash": history_hash,
            "policy": "package_bound_hash_ranked_family_enumeration_v1",
        }
    )
    return seed, generator_hash, planner_hash


def _ranked_families(
    *,
    policy_seed_hash: str,
    challenge_commitment_hash: str,
    attempted_families: Sequence[UpdateFamily],
    history: Phase14SearchHistory,
) -> Sequence[UpdateFamily]:
    attempted = set(attempted_families)
    remaining = tuple(family for family in UPDATE_FAMILIES if family not in attempted)
    if not remaining:
        raise SchemaValidationError(
            "phase14.proposal.remaining_families",
            "the bounded update-family search space is exhausted",
        )
    accepted_counts = {
        family: sum(
            entry.verdict == "accept" and entry.update_family == family
            for entry in history.entries
        )
        for family in UPDATE_FAMILIES
    }
    return tuple(
        sorted(
            remaining,
            key=lambda family: (
                accepted_counts[family],
                canonical_json_hash(
                    {
                        "policy_seed_hash": policy_seed_hash,
                        "challenge_commitment_hash": challenge_commitment_hash,
                        "update_family": family,
                    }
                ),
            ),
        )
    )


def _program_variant(
    challenge_commitment_hash: str,
    attempted_families: Sequence[UpdateFamily],
) -> ProgramVariant:
    if attempted_families:
        return "recover"
    if commitment_requires_probe(challenge_commitment_hash):
        return "probe"
    return "direct"


def generate_proposal_enumeration(
    active_semantic_root: Path,
    challenge_commitment_hash: str,
    history: Phase14SearchHistory,
) -> Phase14ProposalEnumeration:
    root = active_semantic_root.resolve(strict=True)
    manifest = load_package_manifest(root)
    tree_before = package_tree_hash(root)
    seed, generator_hash, planner_hash = _policy_seed(root, history.history_hash)
    attempted = history.attempted_families(challenge_commitment_hash)
    ranked = _ranked_families(
        policy_seed_hash=seed,
        challenge_commitment_hash=challenge_commitment_hash,
        attempted_families=attempted,
        history=history,
    )
    slot = slot_from_commitment(challenge_commitment_hash)
    variant = _program_variant(challenge_commitment_hash, attempted)
    route_marker = slot if variant == "probe" else PHASE14_ROUTE_MARKER
    programs = tuple(
        Phase14MutationProgram(
            active_semantic_package_hash=manifest.package_hash,
            active_model_identity_hash=manifest.model_identity_hash,
            active_generator_hash=generator_hash,
            active_planner_hash=planner_hash,
            challenge_commitment_hash=challenge_commitment_hash,
            history_hash=history.history_hash,
            objective_id=PHASE14_OBJECTIVE_ID,
            update_family=family,
            variant=variant,
            slot_token_id=slot,
            route_marker_token_id=route_marker,
            update_kinds=tuple(
                sorted(UPDATE_KINDS_BY_FAMILY[family], key=lambda item: item.encode("utf-8"))
            ),
            search_cost=PHASE14_SEARCH_COST_PER_ATTEMPT,
        )
        for family in ranked
    )
    tree_after = package_tree_hash(root)
    return Phase14ProposalEnumeration(
        active_semantic_package_hash=manifest.package_hash,
        active_model_identity_hash=manifest.model_identity_hash,
        generator_policy_hash=generator_hash,
        planner_policy_hash=planner_hash,
        challenge_commitment_hash=challenge_commitment_hash,
        history_hash=history.history_hash,
        policy_seed_hash=seed,
        programs=programs,
        package_tree_hash_before=tree_before,
        package_tree_hash_after=tree_after,
    )


def _worker_environment() -> dict[str, str]:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONHASHSEED": "0",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }
    python_path = os.environ.get("PYTHONPATH")
    if python_path:
        environment["PYTHONPATH"] = python_path
    return environment


def run_proposal_worker_twice(
    active_semantic_root: Path,
    challenge_commitment_hash: str,
    history: Phase14SearchHistory,
    output_root: Path,
) -> tuple[Phase14ProposalEnumeration, bytes, bytes]:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 14 proposal output already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    request = {
        "schema_id": "runtime.v4.phase14.proposal_worker_request.v1",
        "active_semantic_root": str(active_semantic_root.resolve(strict=True)),
        "challenge_commitment_hash": challenge_commitment_hash,
        "history": history.to_json(),
        "network_permitted": False,
        "heldout_material_visible": False,
        "manual_repair_permitted": False,
    }
    request_path = root / "request.json"
    request_path.write_bytes(canonical_json_bytes(request))
    outputs: list[bytes] = []
    for index in range(2):
        output_path = root / f"enumeration-{index}.json"
        completed = subprocess.run(
            (
                sys.executable,
                "-m",
                "rcp_rclm_runtime_v4.phase14.proposal_worker",
                "--request",
                str(request_path),
                "--out",
                str(output_path),
            ),
            check=False,
            capture_output=True,
            env=_worker_environment(),
            timeout=120,
        )
        if completed.returncode != 0:
            raise SchemaValidationError(
                "phase14.proposal_worker",
                f"worker failed: stdout={completed.stdout!r} stderr={completed.stderr!r}",
            )
        if completed.stdout or completed.stderr:
            raise SchemaValidationError(
                "phase14.proposal_worker",
                "successful worker must produce empty stdout and stderr",
            )
        outputs.append(output_path.read_bytes())
    if outputs[0] != outputs[1]:
        raise SchemaValidationError(
            "phase14.proposal_worker",
            "two isolated proposal executions are not byte-identical",
        )
    value = json.loads(outputs[0].decode("utf-8"))
    report = Phase14ProposalEnumeration.from_json(value)
    if report.to_json() != value:
        raise SchemaValidationError(
            "phase14.proposal_worker",
            "canonical report round trip mismatch",
        )
    return report, outputs[0], outputs[1]


__all__ = [
    "generate_proposal_enumeration",
    "package_tree_hash",
    "run_proposal_worker_twice",
    "slot_from_commitment",
]
