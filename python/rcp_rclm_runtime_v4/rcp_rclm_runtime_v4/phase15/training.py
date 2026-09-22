from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase15.constants import (
    PHASE15_TRAINING_EPOCHS,
    CandidateVariant,
    cast_candidate_variant,
)
from rcp_rclm_runtime_v4.phase15.curriculum import curriculum_manifest
from rcp_rclm_runtime_v4.phase15.decoder import DecoderManifest


@dataclass(frozen=True, slots=True)
class IsolatedTrainingResult:
    variant: CandidateVariant
    first_root: Path
    second_root: Path
    manifest: DecoderManifest
    training_report: dict[str, object]
    curriculum_manifest: dict[str, object]
    output_tree_hash: str
    two_run_replay_equal: bool

    schema_id: ClassVar[str] = "runtime.v4.phase15.isolated_training_result.v1"

    @property
    def result_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "variant": self.variant,
            "decoder_manifest_hash": self.manifest.manifest_hash,
            "training_report_hash": self.training_report["report_hash"],
            "curriculum_manifest_hash": self.curriculum_manifest["manifest_hash"],
            "output_tree_hash": self.output_tree_hash,
            "two_run_replay_equal": self.two_run_replay_equal,
            "private_challenge_material_present": False,
            "heldout_prompt_present": False,
            "heldout_reference_answer_present": False,
            "training_invocations": 2,
        }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _files(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (path.relative_to(root).as_posix(), path.read_bytes())
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().encode("utf-8"))
        if path.is_file()
    )


def _tree_hash(root: Path) -> str:
    return canonical_json_hash(
        [
            {"path": relative, "sha256": sha256_hex(content), "size": len(content)}
            for relative, content in _files(root)
        ]
    )


def _run(request_path: Path, output_root: Path, package_root: Path) -> None:
    environment = dict(os.environ)
    python_paths = [
        str(package_root.resolve(strict=True)),
        environment.get("PYTHONPATH", ""),
    ]
    environment["PYTHONPATH"] = os.pathsep.join(value for value in python_paths if value)
    completed = subprocess.run(
        (
            sys.executable,
            "-m",
            "rcp_rclm_runtime_v4.phase15.training_worker",
            "--request",
            str(request_path),
            "--outdir",
            str(output_root),
        ),
        cwd=package_root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Phase 15 isolated training failed: "
            + completed.stderr.decode("utf-8", errors="replace")
        )
    if completed.stdout or completed.stderr:
        raise RuntimeError("Phase 15 isolated training must be silent")


def run_isolated_training_twice(
    *,
    variant: CandidateVariant,
    active_semantic_package_hash: str,
    active_model_identity_hash: str,
    work_root: Path,
    package_root: Path,
) -> IsolatedTrainingResult:
    cast_candidate_variant(variant)
    root = work_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"training work root exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    curriculum = curriculum_manifest(variant)
    request = {
        "schema_id": "runtime.v4.phase15.training_request.v1",
        "variant": variant,
        "active_semantic_package_hash": active_semantic_package_hash,
        "active_model_identity_hash": active_model_identity_hash,
        "public_curriculum_manifest": curriculum,
        "epochs": PHASE15_TRAINING_EPOCHS,
        "private_challenge_material_present": False,
        "heldout_prompt_present": False,
        "heldout_reference_answer_present": False,
    }
    request_path = root / "training_request.json"
    _write_json(request_path, request)
    first = root / "run-1"
    second = root / "run-2"
    _run(request_path, first, package_root)
    _run(request_path, second, package_root)
    first_files = _files(first)
    second_files = _files(second)
    equal = first_files == second_files
    if not equal:
        raise SchemaValidationError("phase15.training.replay", "isolated outputs differ")
    manifest_value = load_json_strict((first / "manifest.json").read_bytes(), require_canonical=True)
    manifest = DecoderManifest.from_json(manifest_value)
    training_report = load_json_strict(
        (first / "training_report.json").read_bytes(),
        require_canonical=True,
    )
    curriculum_value = load_json_strict(
        (first / "public_curriculum.json").read_bytes(),
        require_canonical=True,
    )
    if not isinstance(training_report, dict) or not isinstance(curriculum_value, dict):
        raise SchemaValidationError("phase15.training", "expected canonical report objects")
    return IsolatedTrainingResult(
        variant=variant,
        first_root=first,
        second_root=second,
        manifest=manifest,
        training_report=training_report,
        curriculum_manifest=curriculum_value,
        output_tree_hash=_tree_hash(first),
        two_run_replay_equal=equal,
    )


def load_isolated_training_result(
    *,
    variant: CandidateVariant,
    work_root: Path,
) -> IsolatedTrainingResult:
    cast_candidate_variant(variant)
    root = work_root.resolve(strict=True)
    first = root / "run-1"
    second = root / "run-2"
    first_files = _files(first)
    second_files = _files(second)
    equal = first_files == second_files
    if not equal:
        raise SchemaValidationError("phase15.training.replay", "retained isolated outputs differ")
    manifest_value = load_json_strict((first / "manifest.json").read_bytes(), require_canonical=True)
    manifest = DecoderManifest.from_json(manifest_value)
    training_report = load_json_strict((first / "training_report.json").read_bytes(), require_canonical=True)
    curriculum_value = load_json_strict((first / "public_curriculum.json").read_bytes(), require_canonical=True)
    if not isinstance(training_report, dict) or not isinstance(curriculum_value, dict):
        raise SchemaValidationError("phase15.training", "expected canonical retained report objects")
    return IsolatedTrainingResult(
        variant=variant,
        first_root=first,
        second_root=second,
        manifest=manifest,
        training_report=training_report,
        curriculum_manifest=curriculum_value,
        output_tree_hash=_tree_hash(first),
        two_run_replay_equal=equal,
    )


__all__ = ["IsolatedTrainingResult", "load_isolated_training_result", "run_isolated_training_twice"]
