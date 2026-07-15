from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.generator.reference import reference_generator_input
from rcp_rclm_runtime.successor.package_builder import build_candidate_package
from rcp_rclm_runtime.successor.record_predecessor import Phase6PredecessorManifestRecord
from rcp_rclm_runtime.successor.record_resource import Phase6ResourceBudgetRecord
from rcp_rclm_runtime.successor.record_selection import Phase6SelectionRecord
from rcp_rclm_runtime.successor.reference import build_reference_predecessor_package
from rcp_rclm_runtime.successor.workspace import (
    load_predecessor_package,
    measure_payload_tree,
    write_canonical_json,
)
from rcp_rclm_runtime.torch_backend.proposal_backend import (
    evaluate_model_root_exact,
    fixed_heldout_evaluation_data,
    initialize_predecessor_model,
    make_default_request,
)


def _tree_hash(root: Path) -> str:
    records: list[dict[str, object]] = []
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix().encode("utf-8"),
    ):
        content = path.read_bytes()
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    return hashlib.sha256(canonical_json_bytes(records)).hexdigest()


def _add_model_to_phase6_predecessor(
    predecessor_root: Path,
    model_root: Path,
) -> None:
    manifest_value = load_json_strict(
        (predecessor_root / "manifest.json").read_bytes(),
        require_canonical=True,
    )
    manifest = Phase6PredecessorManifestRecord.from_json(manifest_value)
    destination = predecessor_root / "payload" / "model"
    if destination.exists():
        raise RuntimeError("reference predecessor already contains a model directory")
    shutil.copytree(model_root / "model", destination)
    measurement = measure_payload_tree(predecessor_root / "payload")
    updated = Phase6PredecessorManifestRecord(
        package_id=manifest.package_id,
        phase5_manifest_hash=manifest.phase5_manifest_hash,
        payload_tree_hash=measurement.tree_hash,
        state_path=manifest.state_path,
        state_hash=manifest.state_hash,
        file_count=measurement.file_count,
        total_bytes=measurement.total_bytes,
    )
    write_canonical_json(predecessor_root / "manifest.json", updated.to_json())
    loaded = load_predecessor_package(predecessor_root)
    if loaded.manifest != updated:
        raise RuntimeError("augmented predecessor failed public verification")


def _pilot_phase6_budget() -> Phase6ResourceBudgetRecord:
    return Phase6ResourceBudgetRecord(
        max_file_count=128,
        max_total_bytes=2_097_152,
        max_changed_files=16,
        max_written_bytes=8_388_608,
        max_commands=32,
        max_snapshot_bytes=4_194_304,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    output_root = args.outdir.resolve(strict=False)
    package_root = Path(__file__).resolve().parents[1]
    if output_root.exists():
        raise RuntimeError("output directory already exists")
    output_root.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="rcp-rclm-pytorch-pilot-reference-",
        dir=output_root.parent,
    ) as temporary:
        staging = Path(temporary) / "reference"
        staging.mkdir(parents=True, exist_ok=False)

        generator_input = reference_generator_input("target")
        predecessor = build_reference_predecessor_package(
            generator_input,
            staging / "predecessor",
        )
        standalone_model = staging / "standalone-model"
        initialize_predecessor_model(standalone_model)
        _add_model_to_phase6_predecessor(predecessor, standalone_model)
        loaded_predecessor = load_predecessor_package(predecessor)

        request = make_default_request(
            transition_id="pytorch.pilot.reference.0001",
            predecessor_package_id=loaded_predecessor.manifest.package_id,
            predecessor_manifest_hash=loaded_predecessor.manifest.manifest_hash,
            phase5_predecessor_manifest_hash=(
                loaded_predecessor.manifest.phase5_manifest_hash
            ),
            predecessor_payload_tree_hash=loaded_predecessor.measurement.tree_hash,
        )
        request_path = staging / "request.json"
        request_path.write_bytes(canonical_json_bytes(request.to_json()))

        process_results: list[dict[str, object]] = []
        proposal_roots: list[Path] = []
        for index in range(2):
            proposal_root = staging / f"proposal-{index}"
            command = (
                sys.executable,
                "-m",
                "rcp_rclm_runtime.torch_backend.proposal_backend",
                "propose",
                "--request",
                str(request_path),
                "--predecessor-root",
                str(loaded_predecessor.payload_root),
                "--output-root",
                str(proposal_root),
            )
            environment = dict(os.environ)
            existing_pythonpath = environment.get("PYTHONPATH")
            environment["PYTHONPATH"] = (
                str(package_root)
                if not existing_pythonpath
                else os.pathsep.join((str(package_root), existing_pythonpath))
            )
            environment["PYTHONHASHSEED"] = "0"
            environment["CUDA_VISIBLE_DEVICES"] = ""
            completed = subprocess.run(
                command,
                cwd=staging,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=90,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    "proposal worker failed: "
                    + completed.stdout.decode("utf-8", errors="replace")
                    + completed.stderr.decode("utf-8", errors="replace")
                )
            result = load_json_strict(
                completed.stdout.rstrip(b"\r\n"),
                require_canonical=True,
            )
            if not isinstance(result, dict) or result.get("verdict") != "success":
                raise RuntimeError("proposal worker returned a non-success result")
            process_results.append(result)
            proposal_roots.append(proposal_root)

        if process_results[0] != process_results[1]:
            raise RuntimeError("proposal process results differ")
        first_manifest = (proposal_roots[0] / "manifest.json").read_bytes()
        second_manifest = (proposal_roots[1] / "manifest.json").read_bytes()
        if first_manifest != second_manifest:
            raise RuntimeError("proposal manifests differ")
        first_tree_hash = _tree_hash(proposal_roots[0] / "files")
        second_tree_hash = _tree_hash(proposal_roots[1] / "files")
        if first_tree_hash != second_tree_hash:
            raise RuntimeError("proposal file trees differ")

        selection_value = load_json_strict(
            (proposal_roots[0] / "phase6_selection.json").read_bytes(),
            require_canonical=True,
        )
        selection = Phase6SelectionRecord.from_json(selection_value)
        package = build_candidate_package(
            predecessor,
            selection,
            _pilot_phase6_budget(),
            staging / "candidate",
        )
        if not package.report.built or package.output_root is None:
            reasons = ",".join(reason.value for reason in package.report.reason_codes)
            raise RuntimeError(f"Phase 6 candidate package failed: {reasons}")
        realization = package.report.realization
        candidate_manifest = package.report.candidate_manifest
        if realization is None or candidate_manifest is None:
            raise RuntimeError("successful Phase 6 report omitted realization evidence")
        if realization.rollback.verified is not True:
            raise RuntimeError("Phase 6 rollback snapshot did not verify")

        proposal = load_json_strict(
            (proposal_roots[0] / "proposal.json").read_bytes(),
            require_canonical=True,
        )
        if not isinstance(proposal, dict):
            raise RuntimeError("proposal record is not an object")
        proposal_model_tree_hash = _tree_hash(proposal_roots[0] / "files" / "model")
        candidate_model_tree_hash = _tree_hash(
            package.output_root / "payload" / "model"
        )
        if proposal_model_tree_hash != candidate_model_tree_hash:
            raise RuntimeError("realized candidate model differs from proposed model files")

        torch_loaded_before_evaluation = "torch" in sys.modules
        evaluation = evaluate_model_root_exact(
            package.output_root / "payload",
            predecessor_model_hash=str(proposal["predecessor_model_hash"]),
            candidate_model_hash=str(proposal["candidate_model_hash"]),
            evaluation_data=fixed_heldout_evaluation_data(),
            output_path=staging / "evaluation.json",
        )
        torch_loaded_after_evaluation = "torch" in sys.modules
        if torch_loaded_before_evaluation or torch_loaded_after_evaluation:
            raise RuntimeError("framework-independent evaluator loaded PyTorch")
        if evaluation.result.get("evaluation_conditions_met") is not True:
            raise RuntimeError("exact evaluator did not observe the required improvement")

        summary = {
            "schema_id": "runtime.pytorch_pilot_reference_summary.v1",
            "proposal_processes": 2,
            "semantic_replay_equal": True,
            "torch_loaded_by_host_evaluator": False,
            "predecessor_package_id": loaded_predecessor.manifest.package_id,
            "predecessor_manifest_hash": loaded_predecessor.manifest.manifest_hash,
            "predecessor_payload_tree_hash": loaded_predecessor.measurement.tree_hash,
            "predecessor_model_hash": proposal["predecessor_model_hash"],
            "candidate_model_hash": proposal["candidate_model_hash"],
            "proposal_hash": proposal["proposal_hash"],
            "proposal_files_tree_hash": first_tree_hash,
            "candidate_model_tree_hash": candidate_model_tree_hash,
            "evaluation": evaluation.result,
            "phase6_selection_hash": selection.selection_hash,
            "phase6_package_report_hash": package.report.report_hash,
            "phase6_candidate_manifest_hash": candidate_manifest.manifest_hash,
            "phase6_candidate_payload_tree_hash": candidate_manifest.payload_tree_hash,
            "phase6_rollback_hash": realization.rollback.rollback_hash,
            "phase6_rollback_verified": realization.rollback.verified,
            "promotion_attempted": False,
            "formal_checker_claimed_for_model_objective": False,
            "all_expectations_met": True,
        }
        (staging / "summary.json").write_bytes(canonical_json_bytes(summary))
        shutil.rmtree(standalone_model)
        os.replace(staging, output_root)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
