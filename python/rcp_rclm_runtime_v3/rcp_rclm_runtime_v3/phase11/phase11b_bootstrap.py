from __future__ import annotations

import copy
import os
import shutil
import struct
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.contract.common import SELECTED_TASK_CLASS
from rcp_rclm_runtime_v3.contract.state import (
    LearnedRCLMState,
    PolicyIdentity,
    SelfHostingBinding,
)
from rcp_rclm_runtime_v3.contract.tasks import (
    CapabilityFrontier,
    CertificationRecord,
    TaskLedger,
    TaskRecord,
)
from rcp_rclm_runtime_v3.phase10.adapters import empty_adapter_manifest
from rcp_rclm_runtime_v3.phase10.constants import EOS_TOKEN_ID, MODEL_WIDTH
from rcp_rclm_runtime_v3.phase10.learned_data import HELDOUT_TASK, PROTECTED_TASK
from rcp_rclm_runtime_v3.phase10.learned_package import _support_hashes
from rcp_rclm_runtime_v3.phase10.learned_reference import PINNED_LEAN_TOOLCHAIN
from rcp_rclm_runtime_v3.phase10.package import (
    ADAPTER_MANIFEST_PATH,
    PACKAGE_MANIFEST_PATH,
    SUPPORT_HASH_FIELD_BY_PATH,
    TENSOR_MANIFEST_PATH,
    ModelPackageManifest,
    _manifest_from_components,
    _payload_tree_hash,
    load_package_components,
    load_package_manifest,
)
from rcp_rclm_runtime_v3.phase10.sparse_profile import decode_completion, transition_tensor_path
from rcp_rclm_runtime_v3.phase10.tasks import TaskVerifierReport, expected_success_report
from rcp_rclm_runtime_v3.phase10.tensors import TensorManifest, TensorRecord
from rcp_rclm_runtime_v3.phase11.bootstrap import Phase11BootstrapFixture, build_phase11_bootstrap
from rcp_rclm_runtime_v3.phase11.phase11b_constants import (
    ACTIVE_GENERATOR_GENERATION,
    ACTIVE_PLANNER_GENERATION,
    BANK_CAPACITY,
    BANK_START_BY_INVOCATION,
    PHASE11B_ACTIVE_PACKAGE_ID,
    PHASE11B_CONTRACT_VERSION,
    PHASE11B_FROZEN_AUTHORITIES,
    PHASE11B_GENERATOR_PROFILE,
    PHASE11B_OBJECTIVE,
    PHASE11B_PROPOSAL_PROTOCOL_HASH,
    PROGRAM_BY_INVOCATION,
)
from rcp_rclm_runtime_v3.phase11.phase11b_tasks import phase11b_training_manifest
from rcp_rclm_runtime_v3.phase11.records import InvocationBudget, default_phase11_budget


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _file_sha256(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def _install_three_program_banks(predecessor_bytes: bytes) -> bytes:
    expected_size = MODEL_WIDTH * MODEL_WIDTH * 2
    if len(predecessor_bytes) != expected_size:
        raise SchemaValidationError(
            "phase11b.bootstrap.transition_tensor",
            "unexpected transition tensor byte length",
        )
    payload = bytearray(predecessor_bytes)
    occupied: set[int] = set()
    for invocation_index in sorted(PROGRAM_BY_INVOCATION):
        program = PROGRAM_BY_INVOCATION[invocation_index]
        bank_start = BANK_START_BY_INVOCATION[invocation_index]
        if len(program) + 1 > BANK_CAPACITY:
            raise SchemaValidationError("phase11b.bootstrap.bank", "program exceeds bank capacity")
        for position in range(BANK_CAPACITY):
            state_token = bank_start + position
            if state_token >= 260 or state_token in occupied:
                raise SchemaValidationError("phase11b.bootstrap.bank", "state bank is invalid")
            occupied.add(state_token)
            for target in range(MODEL_WIDTH):
                struct.pack_into(
                    "<h",
                    payload,
                    (target * MODEL_WIDTH + state_token) * 2,
                    0,
                )
        for position, target_token in enumerate((*program, EOS_TOKEN_ID)):
            state_token = bank_start + position
            struct.pack_into(
                "<h",
                payload,
                (target_token * MODEL_WIDTH + state_token) * 2,
                24_576,
            )
    return bytes(payload)


def _support_from_package(root: Path) -> dict[str, dict[str, object]]:
    values: dict[str, dict[str, object]] = {}
    for path in SUPPORT_HASH_FIELD_BY_PATH:
        observed = load_json_strict((root / path).read_bytes(), require_canonical=True)
        if not isinstance(observed, dict):
            raise SchemaValidationError("phase11b.bootstrap.support", f"expected object at {path}")
        values[path] = copy.deepcopy(observed)
    return values


def _phase11b_support(source_root: Path, budget: InvocationBudget) -> dict[str, dict[str, object]]:
    values = _support_from_package(source_root)
    values["training/data_curriculum.json"] = phase11b_training_manifest(
        "training_partition_alpha"
    )
    generator_policy: dict[str, object] = {
        "schema_id": "runtime.v3.phase11b.generator_policy.v1",
        "policy": "active_model_three_attempt_typed_mutation_generator",
        "learned_proposal_authority": True,
        "generator_profile": PHASE11B_GENERATOR_PROFILE,
        "generation": ACTIVE_GENERATOR_GENERATION,
        "proposal_protocol_hash": PHASE11B_PROPOSAL_PROTOCOL_HASH,
        "direct_candidate_write": False,
        "heldout_material_visible": False,
    }
    for invocation_index in sorted(PROGRAM_BY_INVOCATION):
        program = PROGRAM_BY_INVOCATION[invocation_index]
        generator_policy[f"program_{invocation_index}_bank_start"] = (
            BANK_START_BY_INVOCATION[invocation_index]
        )
        generator_policy[f"program_{invocation_index}_length"] = len(program)
        generator_policy[f"program_{invocation_index}_sha256"] = sha256_hex(program)
    values["policies/generator_policy.json"] = generator_policy
    values["policies/planner_policy.json"] = {
        "schema_id": "runtime.v3.phase11b.planner_policy.v1",
        "policy": "active_model_rejection_conditioned_experiment_planner",
        "generation": ACTIVE_PLANNER_GENERATION,
        "objective": PHASE11B_OBJECTIVE,
        "proposal_protocol_hash": PHASE11B_PROPOSAL_PROTOCOL_HASH,
        "invalid_proposal_then_two_candidates": True,
        "fresh_invocation_after_rejection": True,
        "typed_mutation_program_required": True,
        "open_ended_across_runs": True,
        "bounded_within_run": True,
    }
    values["policies/resource_policy.json"] = {
        "schema_id": "runtime.v3.phase11b.resource_policy.v1",
        "invocation_budget": budget.to_json(),
        "invocation_budget_hash": budget.budget_hash,
        "frozen_authorities": list(PHASE11B_FROZEN_AUTHORITIES),
        "candidate_direct_write": False,
        "training_backend_untrusted": True,
    }
    values["self_model/manifest.json"] = {
        "schema_id": "runtime.v3.phase11b.self_model.v1",
        "declared_model_family": "compact_decoder_only_transformer_v1",
        "phase": 11,
        "claim": "host_finalized_three_invocation_active_predecessor",
        "active_generator_generation": ACTIVE_GENERATOR_GENERATION,
        "active_planner_generation": ACTIVE_PLANNER_GENERATION,
        "recursive_use_of_modified_generator": False,
    }
    values["runtime/resource_measurement.json"] = {
        "schema_id": "runtime.v3.phase11b.resource_measurement.v1",
        "base_parameter_count": 13_195_840,
        "bootstrap_training_invocations": 0,
        "generator_invocations": 0,
        "candidate_realizations": 0,
        "candidate_evaluations": 0,
        "manual_repairs": 0,
    }
    return values


def _rebuild_tensor_manifest(root: Path, old: TensorManifest) -> TensorManifest:
    records = tuple(
        TensorRecord(spec=record.spec, sha256=_file_sha256(root / record.spec.path))
        for record in old.records
    )
    result = TensorManifest(
        architecture_hash=old.architecture_hash,
        records=records,
        parameter_count=old.parameter_count,
    )
    _write_json(root / TENSOR_MANIFEST_PATH, result.serialized_json())
    return result


def _policy_identity(manifest: ModelPackageManifest) -> PolicyIdentity:
    return PolicyIdentity(
        training_policy_hash=manifest.training_policy_hash,
        optimizer_policy_hash=manifest.optimizer_state_hash,
        data_curriculum_hash=manifest.data_curriculum_hash,
        generator_policy_hash=manifest.generator_policy_hash,
        planner_policy_hash=manifest.planner_policy_hash,
        retrieval_policy_hash=manifest.retrieval_index_hash,
        memory_state_hash=manifest.memory_manifest_hash,
        tool_policy_hash=manifest.tool_policy_hash,
        verification_policy_hash=manifest.verification_policy_hash,
        resource_policy_hash=manifest.resource_policy_hash,
        self_model_hash=manifest.self_model_hash,
    )


def _task_record(task: object) -> TaskRecord:
    return TaskRecord(
        task_id=getattr(task, "task_id"),
        task_class=SELECTED_TASK_CLASS,
        prompt_hash=getattr(task, "prompt_hash"),
        verifier_spec_hash=canonical_json_hash(
            {
                "verifier": "pinned_lean_theorem_verifier_v1",
                "source_prefix_hash": getattr(task, "source_prefix_hash"),
            }
        ),
        partition=getattr(task, "partition"),
    )


def _certification(report: TaskVerifierReport) -> CertificationRecord:
    return CertificationRecord(
        task_id=report.task_id,
        model_identity_hash=report.model_identity_hash,
        verifier_report_hash=report.report_hash,
        verified_output_hash=report.completion_hash,
    )


def _active_state(
    manifest: ModelPackageManifest,
    protected_report: TaskVerifierReport,
    phase10_heldout_report: TaskVerifierReport,
) -> LearnedRCLMState:
    policies = _policy_identity(manifest)
    reports = tuple(
        sorted(
            (protected_report, phase10_heldout_report),
            key=lambda item: item.task_id.encode("utf-8"),
        )
    )
    tasks = tuple(
        sorted(
            (_task_record(PROTECTED_TASK), _task_record(HELDOUT_TASK)),
            key=lambda item: item.task_id.encode("utf-8"),
        )
    )
    frontier = tuple(report.task_id for report in reports)
    return LearnedRCLMState(
        package_id=manifest.package_id,
        parent_package_id=manifest.parent_package_id,
        base_state_hash=canonical_json_hash(
            {
                "phase": 11,
                "bootstrap": "host_finalized_three_invocation_active_predecessor",
                "counted_as_autonomous_improvement": False,
            }
        ),
        model=manifest.model_identity(),
        policies=policies,
        self_hosting=SelfHostingBinding(
            generator_component_hash=policies.generator_policy_hash,
            planner_component_hash=policies.planner_policy_hash,
            proposal_protocol_hash=PHASE11B_PROPOSAL_PROTOCOL_HASH,
            self_hosting_contract_hash=canonical_json_hash(
                {
                    "phase11_self_hosting_contract": "active_package_proposes_three_typed_programs",
                    "recursive_use_of_modified_generator": False,
                }
            ),
        ),
        task_ledger=TaskLedger(
            tasks=tasks,
            certifications=tuple(_certification(report) for report in reports),
        ),
        capability_frontier=CapabilityFrontier(task_ids=frontier),
    )


def _build_active_package(
    source_root: Path,
    output_root: Path,
    budget: InvocationBudget,
) -> ModelPackageManifest:
    source = source_root.resolve(strict=True)
    output = output_root.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"Phase 11B active package already exists: {output}")
    source_manifest = load_package_manifest(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase11b-active-", dir=output.parent) as temporary:
        staging = Path(temporary) / "package"
        shutil.copytree(source, staging, symlinks=False)
        transition_path = transition_tensor_path(staging)
        transition_path.write_bytes(_install_three_program_banks(transition_path.read_bytes()))
        _, architecture, tokenizer, old_tensors, _ = load_package_components(staging)
        tensors = _rebuild_tensor_manifest(staging, old_tensors)
        adapter = empty_adapter_manifest(architecture, tensors.weights_tree_hash)
        _write_json(staging / ADAPTER_MANIFEST_PATH, adapter.serialized_json())
        support = _phase11b_support(source, budget)
        for path, value in support.items():
            _write_json(staging / path, value)
        if (staging / PACKAGE_MANIFEST_PATH).exists():
            (staging / PACKAGE_MANIFEST_PATH).unlink()
        manifest = _manifest_from_components(
            package_id=PHASE11B_ACTIVE_PACKAGE_ID,
            parent_package_id=source_manifest.package_id,
            architecture=architecture,
            tokenizer=tokenizer,
            tensors=tensors,
            adapter=adapter,
            support_hashes=_support_hashes(support),
            payload_tree_hash=_payload_tree_hash(staging),
        )
        _write_json(staging / PACKAGE_MANIFEST_PATH, manifest.to_json())
        os.replace(staging, output)
    return manifest


def validate_phase11b_active_package(
    phase11a_root: Path,
    active_root: Path,
    budget: InvocationBudget,
) -> dict[str, object]:
    source = phase11a_root.resolve(strict=True)
    active = active_root.resolve(strict=True)
    source_manifest, source_architecture, source_tokenizer, source_tensors, _ = (
        load_package_components(source)
    )
    active_manifest, active_architecture, active_tokenizer, active_tensors, active_adapter = (
        load_package_components(active)
    )
    failures: list[str] = []
    if transition_tensor_path(active).read_bytes() != _install_three_program_banks(
        transition_tensor_path(source).read_bytes()
    ):
        failures.append("three_program_bank_tensor_mismatch")
    if active_manifest.payload_tree_hash != _payload_tree_hash(active):
        failures.append("payload_tree_hash_mismatch")
    if active_manifest.parent_package_id != source_manifest.package_id:
        failures.append("parent_package_id_mismatch")
    if active_architecture != source_architecture:
        failures.append("architecture_changed")
    if active_tokenizer != source_tokenizer:
        failures.append("tokenizer_changed")
    if active_tensors.parameter_count != source_tensors.parameter_count:
        failures.append("parameter_count_changed")
    if active_adapter.status != "absent":
        failures.append("adapter_not_absent")
    expected_support = _phase11b_support(source, budget)
    for path, expected in expected_support.items():
        observed = load_json_strict((active / path).read_bytes(), require_canonical=True)
        if observed != expected:
            failures.append(f"support_mismatch:{path}")
        field_name = SUPPORT_HASH_FIELD_BY_PATH[path]
        if getattr(active_manifest, field_name) != canonical_json_hash(expected):
            failures.append(f"support_hash_mismatch:{path}")
    protected_decode = decode_completion(active, PROTECTED_TASK.model_prompt)
    phase10_heldout_decode = decode_completion(active, HELDOUT_TASK.model_prompt)
    if protected_decode.completion_text != PROTECTED_TASK.expected_completion:
        failures.append("protected_task_not_retained")
    if phase10_heldout_decode.completion_text != HELDOUT_TASK.expected_completion:
        failures.append("phase10_heldout_task_not_retained")
    content = {
        "schema_id": "runtime.v3.phase11b.active_validation.v1",
        "contract_version": PHASE11B_CONTRACT_VERSION,
        "phase11a_active_package_hash": source_manifest.package_hash,
        "active_package_hash": active_manifest.package_hash,
        "phase11a_model_identity_hash": source_manifest.model_identity_hash,
        "active_model_identity_hash": active_manifest.model_identity_hash,
        "active_generator_hash": active_manifest.generator_policy_hash,
        "active_planner_hash": active_manifest.planner_policy_hash,
        "proposal_protocol_hash": PHASE11B_PROPOSAL_PROTOCOL_HASH,
        "budget_hash": budget.budget_hash,
        "protected_decode_hash": protected_decode.result_hash,
        "phase10_heldout_decode_hash": phase10_heldout_decode.result_hash,
        "failures": sorted(set(failures)),
        "accepted": not failures,
        "claim_boundary": {
            "host_finalized_bootstrap": True,
            "bootstrap_counted_as_autonomous_improvement": False,
            "phase11_exit_closed": False,
        },
    }
    result = dict(content)
    result["report_hash"] = canonical_json_hash(content)
    return result


@dataclass(frozen=True, slots=True)
class Phase11BActiveFixture:
    root: Path
    phase11a: Phase11BootstrapFixture
    active_package_root: Path
    active_manifest: ModelPackageManifest
    active_state: LearnedRCLMState
    protected_report: TaskVerifierReport
    phase10_heldout_report: TaskVerifierReport
    validation_report: Mapping[str, object]
    budget: InvocationBudget

    schema_id: ClassVar[str] = "runtime.v3.phase11b.active_fixture.v1"

    @property
    def accepted(self) -> bool:
        return (
            self.phase11a.accepted
            and self.validation_report["accepted"] is True
            and self.protected_report.solved
            and self.phase10_heldout_report.solved
            and self.active_state.policies.generator_policy_hash
            == self.active_manifest.generator_policy_hash
            and self.active_state.policies.planner_policy_hash
            == self.active_manifest.planner_policy_hash
        )

    @property
    def fixture_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "phase11a_fixture_hash": self.phase11a.fixture_hash,
            "active_manifest": self.active_manifest.to_json(),
            "active_state": self.active_state.to_json(),
            "protected_report": self.protected_report.to_json(),
            "phase10_heldout_report": self.phase10_heldout_report.to_json(),
            "validation_report": dict(self.validation_report),
            "budget": self.budget.to_json(),
            "claim_boundary": {
                "host_finalized_bootstrap": True,
                "bootstrap_counted_as_autonomous_improvement": False,
                "phase11_exit_closed": False,
            },
        }


def build_phase11b_active_fixture(output_root: Path) -> Phase11BActiveFixture:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 11B active fixture already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    phase11a = build_phase11_bootstrap(root / "phase11a_source")
    budget = default_phase11_budget()
    active_root = root / "active_package"
    manifest = _build_active_package(phase11a.active_package_root, active_root, budget)
    validation = validate_phase11b_active_package(
        phase11a.active_package_root,
        active_root,
        budget,
    )
    protected_report = expected_success_report(
        decode_completion(active_root, PROTECTED_TASK.model_prompt),
        PROTECTED_TASK,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    phase10_heldout_report = expected_success_report(
        decode_completion(active_root, HELDOUT_TASK.model_prompt),
        HELDOUT_TASK,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    state = _active_state(manifest, protected_report, phase10_heldout_report)
    fixture = Phase11BActiveFixture(
        root=root,
        phase11a=phase11a,
        active_package_root=active_root,
        active_manifest=manifest,
        active_state=state,
        protected_report=protected_report,
        phase10_heldout_report=phase10_heldout_report,
        validation_report=validation,
        budget=budget,
    )
    if not fixture.accepted:
        raise ValueError("Phase 11B active predecessor did not validate")
    return fixture


__all__ = [
    "Phase11BActiveFixture",
    "build_phase11b_active_fixture",
    "validate_phase11b_active_package",
]
