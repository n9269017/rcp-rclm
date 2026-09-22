from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v3.phase10.learned_package import _support_hashes
from rcp_rclm_runtime_v3.phase10.package import (
    PACKAGE_MANIFEST_PATH,
    ModelPackageManifest,
    _manifest_from_components,
    _payload_tree_hash,
    load_package_components,
    load_package_manifest,
)
from rcp_rclm_runtime_v4.phase14.candidate import _support_values

from rcp_rclm_runtime_v4.phase15.constants import (
    PHASE15_CONTRACT_VERSION,
    PHASE15_EXPECTED_M8_SEMANTIC_PACKAGE_HASH,
    CandidateVariant,
    cast_candidate_variant,
)
from rcp_rclm_runtime_v4.phase15.decoder import (
    DECODER_CURRICULUM_PATH,
    DECODER_MANIFEST_PATH,
    DECODER_TRAINING_REPORT_PATH,
    DECODER_VOCABULARY_PATH,
    DECODER_WEIGHTS_PATH,
    DecoderManifest,
    directory_decoder_hash,
)
from rcp_rclm_runtime_v4.phase15.training import (
    IsolatedTrainingResult,
    load_isolated_training_result,
    run_isolated_training_twice,
)


@dataclass(frozen=True, slots=True)
class Phase15SemanticCandidate:
    root: Path
    variant: CandidateVariant
    active_semantic_package_hash: str
    manifest: ModelPackageManifest
    decoder_manifest: DecoderManifest
    training: IsolatedTrainingResult
    changed_paths: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v4.phase15.semantic_candidate.v1"

    @property
    def freeze_hash(self) -> str:
        return canonical_json_hash(
            {
                "schema_id": "runtime.v4.phase15.candidate_freeze.v1",
                "candidate_semantic_package_hash": self.manifest.package_hash,
                "decoder_manifest_hash": self.decoder_manifest.manifest_hash,
                "decoder_directory_hash": directory_decoder_hash(self.root),
                "variant": self.variant,
                "challenge_created": False,
            }
        )

    @property
    def candidate_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": PHASE15_CONTRACT_VERSION,
            "variant": self.variant,
            "active_semantic_package_hash": self.active_semantic_package_hash,
            "candidate_semantic_package_hash": self.manifest.package_hash,
            "candidate_model_identity_hash": self.manifest.model_identity_hash,
            "decoder_manifest_hash": self.decoder_manifest.manifest_hash,
            "decoder_directory_hash": directory_decoder_hash(self.root),
            "training_result_hash": self.training.result_hash,
            "changed_paths": list(self.changed_paths),
            "freeze_hash": self.freeze_hash,
            "private_challenge_material_present": False,
            "heldout_prompt_present": False,
            "heldout_reference_answer_present": False,
            "candidate_self_report_authoritative": False,
        }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _changed_paths(before: Path, after: Path) -> tuple[str, ...]:
    before_files = {
        path.relative_to(before).as_posix(): sha256_hex(path.read_bytes())
        for path in before.rglob("*")
        if path.is_file()
    }
    after_files = {
        path.relative_to(after).as_posix(): sha256_hex(path.read_bytes())
        for path in after.rglob("*")
        if path.is_file()
    }
    return tuple(
        sorted(
            {
                path
                for path in set(before_files) | set(after_files)
                if before_files.get(path) != after_files.get(path)
            },
            key=lambda item: item.encode("utf-8"),
        )
    )


def _policy_updates(
    support: dict[str, dict[str, object]],
    *,
    variant: CandidateVariant,
    training: IsolatedTrainingResult,
) -> None:
    decoder_hash = training.manifest.manifest_hash
    curriculum_hash = training.curriculum_manifest["manifest_hash"]
    training_hash = training.training_report["report_hash"]
    support["training/training_policy.json"] = {
        "schema_id": "runtime.v4.phase15.training_policy.v1",
        "backend_authority": "untrusted_external_only",
        "reference_backend": "deterministic_integer_multiclass_perceptron_v1",
        "cpu_reference_execution": True,
        "untrusted_accelerator_permitted": True,
        "deterministic_canonical_export_required": True,
        "authoritative_evaluation_permitted": False,
        "decoder_manifest_hash": decoder_hash,
        "training_report_hash": training_hash,
        "heldout_prompts_visible": False,
        "heldout_reference_answers_visible": False,
        "private_challenge_source_visible": False,
    }
    old_optimizer = support["training/optimizer_state.json"]
    support["training/optimizer_state.json"] = {
        **old_optimizer,
        "schema_id": "runtime.v4.phase15.optimizer_state.v1",
        "optimizer": "integer_multiclass_perceptron",
        "epochs": training.training_report["epochs"],
        "example_count": training.training_report["example_count"],
        "step": int(old_optimizer.get("step", 0)) + int(training.training_report["epochs"]),
        "parent_optimizer_hash": canonical_json_hash(old_optimizer),
        "training_report_hash": training_hash,
        "weights_sha256": training.manifest.weights_sha256,
        "native_float_used": False,
    }
    support["training/data_curriculum.json"] = {
        "schema_id": "runtime.v4.phase15.data_curriculum.v1",
        "task_class": "bounded_multidomain_plan_generation_v1",
        "variant": variant,
        "domains": list(training.manifest.supported_domains),
        "public_curriculum_manifest_hash": curriculum_hash,
        "training_examples": training.training_report["example_count"],
        "heldout_task_ids_visible": False,
        "heldout_prompts_visible": False,
        "heldout_reference_answers_visible": False,
        "dynamic_challenges_generated_after_candidate_freeze": True,
    }
    old_generator = support["policies/generator_policy.json"]
    support["policies/generator_policy.json"] = {
        **old_generator,
        "schema_id": "runtime.v4.phase15.generator_policy.v1",
        "phase15_plan_decoder_manifest_hash": decoder_hash,
        "multi_token_plan_generation": True,
        "dynamic_hidden_challenge_answers_visible": False,
        "manual_repair_permitted": False,
        "proposal_protocol_hash": canonical_json_hash(
            {
                "protocol": "phase15-post-freeze-multidomain-plan-generation-v1",
                "decoder_manifest_hash": decoder_hash,
                "active_generator_parent_hash": canonical_json_hash(old_generator),
            }
        ),
    }
    old_planner = support["policies/planner_policy.json"]
    support["policies/planner_policy.json"] = {
        **old_planner,
        "schema_id": "runtime.v4.phase15.planner_policy.v1",
        "phase15_plan_decoder_manifest_hash": decoder_hash,
        "bounded_autoregressive_execution": True,
        "maximum_plan_tokens": 16,
        "supported_domains": list(training.manifest.supported_domains),
        "fresh_dynamic_challenge_after_freeze": True,
        "manual_repair_permitted": False,
        "proposal_protocol_hash": support["policies/generator_policy.json"]["proposal_protocol_hash"],
    }
    old_tool = support["policies/tool_policy.json"]
    allowed = tuple(
        sorted(
            {
                *(str(item) for item in old_tool.get("allowed_tools", [])),
                "phase15_integer_program_exhaustive_verifier",
                "phase15_lean_plan_interpreter",
                "phase15_quantized_plan_decoder",
            },
            key=lambda item: item.encode("utf-8"),
        )
    )
    support["policies/tool_policy.json"] = {
        "schema_id": "runtime.v4.phase15.tool_policy.v1",
        "allowed_tools": list(allowed),
        "decoder_manifest_path": DECODER_MANIFEST_PATH,
        "decoder_manifest_hash": decoder_hash,
        "decoder_weights_path": DECODER_WEIGHTS_PATH,
        "decoder_weights_sha256": training.manifest.weights_sha256,
        "dynamic_code_loading": False,
        "candidate_self_report_authoritative": False,
    }
    support["policies/verification_policy.json"] = {
        "schema_id": "runtime.v4.phase15.verification_policy.v1",
        "protected_frontier_verifier": "pinned_lean_theorem_verifier_v1",
        "dynamic_lean_verifier": "pinned_lean_multistep_plan_verifier_v1",
        "dynamic_program_verifier": "exhaustive_integer_plus_pinned_lean_v1",
        "candidate_self_report_authoritative": False,
        "predecessor_failure_recomputed": True,
        "candidate_freeze_required_before_challenge_generation": True,
    }
    old_self = support["self_model/manifest.json"]
    support["self_model/manifest.json"] = {
        **old_self,
        "schema_id": "runtime.v4.phase15.self_model.v1",
        "phase": 15,
        "claim": "package_bound_quantized_autoregressive_plan_extension",
        "phase15_decoder_manifest_hash": decoder_hash,
        "extension_parameter_count": training.manifest.parameter_count,
        "base_model_identity_unchanged": True,
        "full_transformer_equivalence_claimed": False,
    }


def build_phase15_candidate(
    active_semantic_root: Path,
    *,
    variant: CandidateVariant,
    output_root: Path,
    training_work_root: Path,
    runtime_package_root: Path,
) -> Phase15SemanticCandidate:
    cast_candidate_variant(variant)
    active = active_semantic_root.resolve(strict=True)
    active_manifest, architecture, tokenizer, tensors, adapter = load_package_components(active)
    if active_manifest.package_hash != PHASE15_EXPECTED_M8_SEMANTIC_PACKAGE_HASH:
        raise SchemaValidationError("phase15.candidate.active", "expected certified M8 package")
    training = run_isolated_training_twice(
        variant=variant,
        active_semantic_package_hash=active_manifest.package_hash,
        active_model_identity_hash=active_manifest.model_identity_hash,
        work_root=training_work_root,
        package_root=runtime_package_root,
    )
    output = output_root.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"Phase 15 candidate exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase15-candidate-", dir=output.parent) as temporary:
        staging = Path(temporary) / "semantic_candidate"
        shutil.copytree(active, staging, symlinks=False)
        (staging / PACKAGE_MANIFEST_PATH).unlink()
        source_by_target = {
            DECODER_WEIGHTS_PATH: "weights.i16le.bin",
            DECODER_MANIFEST_PATH: "manifest.json",
            DECODER_VOCABULARY_PATH: "vocabulary.json",
            DECODER_TRAINING_REPORT_PATH: "training_report.json",
            DECODER_CURRICULUM_PATH: "public_curriculum.json",
        }
        for target, source in source_by_target.items():
            destination = staging / target
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((training.first_root / source).read_bytes())
        support = _support_values(active)
        _policy_updates(support, variant=variant, training=training)
        for path, value in support.items():
            _write_json(staging / path, value)
        payload_hash = _payload_tree_hash(staging)
        manifest = _manifest_from_components(
            package_id=f"phase15-{variant}-{training.manifest.manifest_hash[:12]}",
            parent_package_id=active_manifest.package_id,
            architecture=architecture,
            tokenizer=tokenizer,
            tensors=tensors,
            adapter=adapter,
            support_hashes=_support_hashes(support),
            payload_tree_hash=payload_hash,
        )
        _write_json(staging / PACKAGE_MANIFEST_PATH, manifest.to_json())
        os.replace(staging, output)
    changed = _changed_paths(active, output)
    result = Phase15SemanticCandidate(
        root=output,
        variant=variant,
        active_semantic_package_hash=active_manifest.package_hash,
        manifest=manifest,
        decoder_manifest=training.manifest,
        training=training,
        changed_paths=changed,
    )
    validate_phase15_candidate(active, result)
    return result


def validate_phase15_candidate(
    active_semantic_root: Path,
    candidate: Phase15SemanticCandidate,
) -> dict[str, object]:
    active = active_semantic_root.resolve(strict=True)
    root = candidate.root.resolve(strict=True)
    active_manifest, architecture, tokenizer, tensors, adapter = load_package_components(active)
    manifest, candidate_architecture, candidate_tokenizer, candidate_tensors, candidate_adapter = load_package_components(root)
    failures: list[str] = []
    if manifest != candidate.manifest:
        failures.append("manifest_reopen_mismatch")
    if manifest.parent_package_id != active_manifest.package_id:
        failures.append("parent_package_id_mismatch")
    if candidate_architecture != architecture or candidate_tokenizer != tokenizer:
        failures.append("base_architecture_or_tokenizer_changed")
    if candidate_tensors != tensors or candidate_adapter != adapter:
        failures.append("base_model_or_adapter_changed")
    if manifest.model_identity_hash != active_manifest.model_identity_hash:
        failures.append("base_model_identity_changed")
    if manifest.payload_tree_hash != _payload_tree_hash(root):
        failures.append("payload_tree_hash_mismatch")
    decoder_value = load_json_strict((root / DECODER_MANIFEST_PATH).read_bytes(), require_canonical=True)
    reopened_decoder = DecoderManifest.from_json(decoder_value)
    if reopened_decoder != candidate.decoder_manifest:
        failures.append("decoder_manifest_reopen_mismatch")
    if reopened_decoder.active_semantic_package_hash != active_manifest.package_hash:
        failures.append("decoder_active_package_binding_mismatch")
    if reopened_decoder.active_model_identity_hash != active_manifest.model_identity_hash:
        failures.append("decoder_model_binding_mismatch")
    support = _support_values(root)
    for path, field in (
        ("training/training_policy.json", "decoder_manifest_hash"),
        ("policies/generator_policy.json", "phase15_plan_decoder_manifest_hash"),
        ("policies/planner_policy.json", "phase15_plan_decoder_manifest_hash"),
        ("policies/tool_policy.json", "decoder_manifest_hash"),
        ("self_model/manifest.json", "phase15_decoder_manifest_hash"),
    ):
        if support[path].get(field) != reopened_decoder.manifest_hash:
            failures.append(f"decoder_policy_binding_mismatch:{path}")
    if not candidate.changed_paths or PACKAGE_MANIFEST_PATH not in candidate.changed_paths:
        failures.append("candidate_not_substantive")
    decoder_root = root / "model/phase15_planner"
    forbidden_fragments = (
        "private_answer_store",
        "challenge_id",
        "commitment_hash",
        "expected_plan_text",
    )
    for path in decoder_root.rglob("*"):
        if not path.is_file():
            continue
        payload = path.read_bytes()
        for fragment in forbidden_fragments:
            if fragment.encode("utf-8") in payload:
                failures.append(
                    f"private_material_marker_present:{path.relative_to(root).as_posix()}:{fragment}"
                )
    content = {
        "schema_id": "runtime.v4.phase15.semantic_candidate_validation.v1",
        "variant": candidate.variant,
        "active_semantic_package_hash": active_manifest.package_hash,
        "candidate_semantic_package_hash": manifest.package_hash,
        "candidate_model_identity_hash": manifest.model_identity_hash,
        "decoder_manifest_hash": reopened_decoder.manifest_hash,
        "changed_paths": list(candidate.changed_paths),
        "failures": sorted(set(failures)),
        "accepted": not failures,
    }
    result = dict(content)
    result["report_hash"] = canonical_json_hash(content)
    if failures:
        raise SchemaValidationError("phase15.candidate", ",".join(sorted(set(failures))))
    return result


def load_phase15_candidate(
    *,
    active_semantic_root: Path,
    candidate_root: Path,
    training_root: Path,
    retained_value: object,
) -> Phase15SemanticCandidate:
    if not isinstance(retained_value, Mapping):
        raise SchemaValidationError("phase15.candidate.retained", "expected object")
    variant = cast_candidate_variant(str(retained_value.get("variant")))
    changed = retained_value.get("changed_paths")
    if not isinstance(changed, list):
        raise SchemaValidationError("phase15.candidate.changed_paths", "expected array")
    training = load_isolated_training_result(variant=variant, work_root=training_root)
    root = candidate_root.resolve(strict=True)
    manifest = load_package_manifest(root)
    result = Phase15SemanticCandidate(
        root=root,
        variant=variant,
        active_semantic_package_hash=str(retained_value.get("active_semantic_package_hash")),
        manifest=manifest,
        decoder_manifest=training.manifest,
        training=training,
        changed_paths=tuple(str(item) for item in changed),
    )
    if result.to_json() != dict(retained_value):
        raise SchemaValidationError("phase15.candidate.retained", "retained candidate record differs")
    validate_phase15_candidate(active_semantic_root, result)
    return result


__all__ = [
    "Phase15SemanticCandidate",
    "build_phase15_candidate",
    "load_phase15_candidate",
    "validate_phase15_candidate",
]
