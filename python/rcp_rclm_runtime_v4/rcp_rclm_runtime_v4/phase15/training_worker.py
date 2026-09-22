from __future__ import annotations

import argparse
import json
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase15.constants import (
    PHASE15_TRAINING_EPOCHS,
    cast_candidate_variant,
)
from rcp_rclm_runtime_v4.phase15.curriculum import (
    CurriculumExample,
    curriculum_manifest,
    public_curriculum,
)
from rcp_rclm_runtime_v4.phase15.decoder import (
    DecoderManifest,
    vocabulary_json,
    weights_bytes,
    train_perceptron,
)


def _read_request(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SchemaValidationError("phase15.training.request", "expected object")
    allowed = {
        "schema_id",
        "variant",
        "active_semantic_package_hash",
        "active_model_identity_hash",
        "public_curriculum_manifest",
        "epochs",
        "private_challenge_material_present",
        "heldout_prompt_present",
        "heldout_reference_answer_present",
    }
    if set(value) != allowed:
        raise SchemaValidationError("phase15.training.request", "unexpected request fields")
    if value.get("schema_id") != "runtime.v4.phase15.training_request.v1":
        raise SchemaValidationError("phase15.training.request.schema_id", "unexpected schema")
    if value.get("private_challenge_material_present") is not False:
        raise SchemaValidationError("phase15.training.request", "private challenge material forbidden")
    if value.get("heldout_prompt_present") is not False:
        raise SchemaValidationError("phase15.training.request", "heldout prompt forbidden")
    if value.get("heldout_reference_answer_present") is not False:
        raise SchemaValidationError("phase15.training.request", "heldout answer forbidden")
    return value


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def run_worker(request_path: Path, output_root: Path) -> dict[str, object]:
    request = _read_request(request_path.resolve(strict=True))
    output = output_root.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"training output exists: {output}")
    output.mkdir(parents=True, exist_ok=False)
    variant = cast_candidate_variant(str(request["variant"]))
    epochs = request["epochs"]
    if isinstance(epochs, bool) or not isinstance(epochs, int) or epochs != PHASE15_TRAINING_EPOCHS:
        raise SchemaValidationError("phase15.training.request.epochs", "unexpected epoch count")
    expected_curriculum = curriculum_manifest(variant)
    if request["public_curriculum_manifest"] != expected_curriculum:
        raise SchemaValidationError("phase15.training.request", "public curriculum mismatch")
    examples = public_curriculum(variant)
    weights = train_perceptron(examples, epochs=epochs)
    payload = weights_bytes(weights)
    weights_path = output / "weights.i16le.bin"
    weights_path.write_bytes(payload)
    vocabulary = vocabulary_json()
    vocabulary_hash = canonical_json_hash(vocabulary)
    training_content = {
        "schema_id": "runtime.v4.phase15.training_report.v1",
        "variant": variant,
        "backend": "deterministic_integer_multiclass_perceptron_v1",
        "device": "cpu",
        "native_float_used": False,
        "epochs": epochs,
        "example_count": len(examples),
        "curriculum_manifest_hash": expected_curriculum["manifest_hash"],
        "weights_sha256": sha256_hex(payload),
        "parameter_count": len(payload) // 2,
        "private_challenge_material_present": False,
        "heldout_prompt_present": False,
        "heldout_reference_answer_present": False,
        "candidate_self_report_authoritative": False,
    }
    training_report = dict(training_content)
    training_report["report_hash"] = canonical_json_hash(training_content)
    supported_domains = (
        ("lean_multistep",)
        if variant == "lean_only"
        else ("integer_program", "lean_multistep")
    )
    manifest = DecoderManifest(
        variant=variant,
        supported_domains=supported_domains,
        curriculum_manifest_hash=str(expected_curriculum["manifest_hash"]),
        training_report_hash=str(training_report["report_hash"]),
        weights_sha256=sha256_hex(payload),
        vocabulary_hash=vocabulary_hash,
        active_semantic_package_hash=str(request["active_semantic_package_hash"]),
        active_model_identity_hash=str(request["active_model_identity_hash"]),
    )
    _write(output / "public_curriculum.json", expected_curriculum)
    _write(output / "vocabulary.json", vocabulary)
    _write(output / "training_report.json", training_report)
    _write(output / "manifest.json", manifest.to_json())
    result_content = {
        "schema_id": "runtime.v4.phase15.training_worker_result.v1",
        "variant": variant,
        "weights_sha256": manifest.weights_sha256,
        "decoder_manifest_hash": manifest.manifest_hash,
        "training_report_hash": training_report["report_hash"],
        "curriculum_manifest_hash": expected_curriculum["manifest_hash"],
        "output_files": [
            "manifest.json",
            "public_curriculum.json",
            "training_report.json",
            "vocabulary.json",
            "weights.i16le.bin",
        ],
    }
    result = dict(result_content)
    result["result_hash"] = canonical_json_hash(result_content)
    _write(output / "worker_result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    run_worker(args.request, args.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
