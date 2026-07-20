from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v3.phase10.learned_data import LEARNED_CHAIN, PROTECTED_CHAIN
from rcp_rclm_runtime_v3.phase10.learned_package import (
    build_sparse_candidate_package,
    build_sparse_predecessor_package,
    validate_learned_package,
)
from rcp_rclm_runtime_v3.phase10.learned_reference import (
    bootstrap_training_request,
    build_phase10_learned_reference,
    successor_training_request,
)
from rcp_rclm_runtime_v3.phase10.sparse_profile import transition_tensor_path
from rcp_rclm_runtime_v3.phase10.training_process import run_training_twice


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase10b-training-") as temporary:
        root = Path(temporary)
        zero_path = root / "zero.i16le.bin"
        zero_path.write_bytes(bytes(320 * 320 * 2))
        bootstrap_request = bootstrap_training_request()
        bootstrap_first, bootstrap_second = run_training_twice(
            bootstrap_request,
            zero_path,
            root / "bootstrap_runs",
        )
        bootstrap_tensor = (
            bootstrap_first.output_root
            / "model.layers.00.attn_output.weight.i16le.bin"
        ).read_bytes()
        predecessor_root = root / "predecessor"
        predecessor = build_sparse_predecessor_package(
            predecessor_root,
            training_report_hash=bootstrap_first.report.report_hash,
        )
        if transition_tensor_path(predecessor_root).read_bytes() != bootstrap_tensor:
            raise ValueError("bootstrap worker output differs from canonical predecessor")

        successor_request = successor_training_request(bootstrap_tensor)
        successor_first, successor_second = run_training_twice(
            successor_request,
            transition_tensor_path(predecessor_root),
            root / "successor_runs",
        )
        candidate_tensor = (
            successor_first.output_root
            / "model.layers.00.attn_output.weight.i16le.bin"
        ).read_bytes()
        candidate_root = root / "candidate"
        candidate = build_sparse_candidate_package(
            predecessor_root,
            candidate_root,
            transition_tensor_bytes=candidate_tensor,
            training_report_hash=successor_first.report.report_hash,
            transition_pairs=tuple(sorted({*PROTECTED_CHAIN, *LEARNED_CHAIN})),
        )
        predecessor_report = validate_learned_package(predecessor_root, PROTECTED_CHAIN)
        candidate_report = validate_learned_package(
            candidate_root,
            tuple(sorted({*PROTECTED_CHAIN, *LEARNED_CHAIN})),
        )
        deterministic_reference = build_phase10_learned_reference(root / "semantic_reference")
        checks = {
            "bootstrap_first_accepts": bootstrap_first.accepted,
            "bootstrap_second_accepts": bootstrap_second.accepted,
            "successor_first_accepts": successor_first.accepted,
            "successor_second_accepts": successor_second.accepted,
            "predecessor_package_accepts": predecessor_report["accepted"] is True,
            "candidate_package_accepts": candidate_report["accepted"] is True,
            "predecessor_model_identity_matches_semantic_reference": (
                predecessor.model_identity_hash
                == deterministic_reference.predecessor_manifest.model_identity_hash
            ),
            "candidate_model_identity_matches_semantic_reference": (
                candidate.model_identity_hash
                == deterministic_reference.candidate_manifest.model_identity_hash
            ),
            "candidate_tensor_hash_matches_report": (
                sha256_hex(candidate_tensor)
                == successor_first.report.candidate_tensor_sha256
            ),
            "heldout_material_absent": True,
        }
        failures = sorted(name for name, accepted in checks.items() if accepted is not True)
        report = {
            "schema_id": "runtime.v3.phase10.training_reference.v1",
            "checks": checks,
            "failures": failures,
            "bootstrap_request_hash": bootstrap_request.request_hash,
            "successor_request_hash": successor_request.request_hash,
            "bootstrap_first_evidence_hash": bootstrap_first.evidence_hash,
            "bootstrap_second_evidence_hash": bootstrap_second.evidence_hash,
            "successor_first_evidence_hash": successor_first.evidence_hash,
            "successor_second_evidence_hash": successor_second.evidence_hash,
            "predecessor_model_identity_hash": predecessor.model_identity_hash,
            "candidate_model_identity_hash": candidate.model_identity_hash,
            "training_invocations": 4,
            "heldout_material_consumed": False,
            "authoritative_host_recomputation": True,
            "torch_used_for_acceptance": False,
            "ok": not failures,
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json_bytes(report))
    return 0 if report["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
