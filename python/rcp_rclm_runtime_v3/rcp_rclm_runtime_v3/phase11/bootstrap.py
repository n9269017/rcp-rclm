from __future__ import annotations

import copy
import os
import shutil
import struct
import tempfile
from collections.abc import Mapping, Sequence
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
from rcp_rclm_runtime_v3.phase10.learned_data import (
    HELDOUT_TASK,
    PROTECTED_TASK,
)
from rcp_rclm_runtime_v3.phase10.learned_package import _support_hashes
from rcp_rclm_runtime_v3.phase10.learned_reference import (
    PINNED_LEAN_TOOLCHAIN,
    Phase10LearnedReference,
    build_phase10_learned_reference,
)
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
from rcp_rclm_runtime_v3.phase10.sparse_profile import (
    decode_completion,
    transition_tensor_path,
)
from rcp_rclm_runtime_v3.phase10.tasks import (
    TaskVerifierReport,
    expected_success_report,
)
from rcp_rclm_runtime_v3.phase10.tensors import TensorManifest, TensorRecord
from rcp_rclm_runtime_v3.phase11.constants import (
    ACCEPTED_BANK_CAPACITY,
    ACCEPTED_BANK_START,
    ACCEPTED_PROGRAM_BYTES,
    ACTIVE_GENERATOR_GENERATION,
    ACTIVE_PLANNER_GENERATION,
    FROZEN_AUTHORITIES,
    PHASE11_BOOTSTRAP_PACKAGE_ID,
    PHASE11_GENERATOR_PROFILE,
    PHASE11_OBJECTIVE,
    PROPOSAL_PROTOCOL_HASH,
    REJECTED_BANK_CAPACITY,
    REJECTED_BANK_START,
    REJECTED_PROGRAM_BYTES,
)
from rcp_rclm_runtime_v3.phase11.records import InvocationBudget, default_phase11_budget


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _file_sha256(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def _expected_bank_bytes(predecessor_bytes: bytes) -> bytes:
    expected_size = MODEL_WIDTH * MODEL_WIDTH * 2
    if len(predecessor_bytes) != expected_size:
        raise SchemaValidationError(
            "phase11.bootstrap.transition_tensor",
            "unexpected transition tensor byte length",
        )
    payload = bytearray(predecessor_bytes)
    banks = (
        (REJECTED_BANK_START, REJECTED_BANK_CAPACITY, REJECTED_PROGRAM_BYTES),
        (ACCEPTED_BANK_START, ACCEPTED_BANK_CAPACITY, ACCEPTED_PROGRAM_BYTES),
    )
    occupied: set[int] = set()
    for bank_start, capacity, program in banks:
        required = len(program) + 1
        if required > capacity:
            raise SchemaValidationError("phase11.bootstrap.bank", "program exceeds bank capacity")
        for position in range(capacity):
            state_token = bank_start + position
            if state_token >= MODEL_WIDTH or state_token in occupied:
                raise SchemaValidationError("phase11.bootstrap.bank", "state bank is invalid")
            occupied.add(state_token)
            for target in range(MODEL_WIDTH):
                struct.pack_into(
                    "<h",
                    payload,
                    (target * MODEL_WIDTH + state_token) * 2,
                    0,
                )
        outputs = (*program, EOS_TOKEN_ID)
        for position, target_token in enumerate(outputs):
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
        value = load_json_strict((root / path).read_bytes(), require_canonical=True)
        if not isinstance(value, dict):
            raise SchemaValidationError("phase11.bootstrap.support", f"expected object at {path}")
        values[path] = copy.deepcopy(value)
    return values


def _phase11_support(
    predecessor_root: Path,
    budget: InvocationBudget,
) -> dict[str, dict[str, object]]:
    values = _support_from_package(predecessor_root)
    values["policies/generator_policy.json"] = {
        "schema_id": "runtime.v3.phase11.generator_policy.v1",
        "policy": "active_model_typed_mutation_generator",
        "learned_proposal_authority": True,
        "generator_profile": PHASE11_GENERATOR_PROFILE,
        "generation": ACTIVE_GENERATOR_GENERATION,
        "proposal_protocol_hash": PROPOSAL_PROTOCOL_HASH,
        "rejected_bank_start": REJECTED_BANK_START,
        "rejected_program_length": len(REJECTED_PROGRAM_BYTES),
        "rejected_program_sha256": sha256_hex(REJECTED_PROGRAM_BYTES),
        "accepted_bank_start": ACCEPTED_BANK_START,
        "accepted_program_length": len(ACCEPTED_PROGRAM_BYTES),
        "accepted_program_sha256": sha256_hex(ACCEPTED_PROGRAM_BYTES),
        "direct_candidate_write": False,
        "heldout_material_visible": False,
    }
    values["policies/planner_policy.json"] = {
        "schema_id": "runtime.v3.phase11.planner_policy.v1",
        "policy": "active_model_bounded_experiment_planner",
        "generation": ACTIVE_PLANNER_GENERATION,
        "objective": PHASE11_OBJECTIVE,
        "proposal_protocol_hash": PROPOSAL_PROTOCOL_HASH,
        "fresh_invocation_after_rejection": True,
        "typed_mutation_program_required": True,
        "open_ended_across_runs": True,
        "bounded_within_run": True,
    }
    values["policies/resource_policy.json"] = {
        "schema_id": "runtime.v3.phase11.resource_policy.v1",
        "invocation_budget": budget.to_json(),
        "invocation_budget_hash": budget.budget_hash,
        "frozen_authorities": list(FROZEN_AUTHORITIES),
        "candidate_direct_write": False,
        "training_backend_untrusted": True,
    }
    values["self_model/manifest.json"] = {
        "schema_id": "runtime.v3.phase11.self_model.v1",
        "declared_model_family": "compact_decoder_only_transformer_v1",
        "phase": 11,
        "claim": "host_installed_active_generator_bootstrap",
        "active_generator_generation": ACTIVE_GENERATOR_GENERATION,
        "active_planner_generation": ACTIVE_PLANNER_GENERATION,
        "recursive_use_of_modified_generator": False,
    }
    values["runtime/resource_measurement.json"] = {
        "schema_id": "runtime.v3.phase11.resource_measurement.v1",
        "base_parameter_count": 13_195_840,
        "bootstrap_training_invocations": 0,
        "generator_invocations": 0,
        "candidate_realizations": 0,
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


def _build_active_package(
    predecessor_root: Path,
    output_root: Path,
    budget: InvocationBudget,
) -> ModelPackageManifest:
    predecessor = predecessor_root.resolve(strict=True)
    output = output_root.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"Phase 11 bootstrap package already exists: {output}")
    predecessor_manifest = load_package_manifest(predecessor)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase11-bootstrap-", dir=output.parent) as temporary:
        staging = Path(temporary) / "package"
        shutil.copytree(predecessor, staging, symlinks=False)
        transition_path = transition_tensor_path(staging)
        transition_path.write_bytes(_expected_bank_bytes(transition_path.read_bytes()))
        old_manifest, architecture, tokenizer, old_tensors, _ = load_package_components(staging)
        del old_manifest
        tensors = _rebuild_tensor_manifest(staging, old_tensors)
        adapter = empty_adapter_manifest(architecture, tensors.weights_tree_hash)
        _write_json(staging / ADAPTER_MANIFEST_PATH, adapter.serialized_json())
        support = _phase11_support(predecessor, budget)
        for path, value in support.items():
            _write_json(staging / path, value)
        if (staging / PACKAGE_MANIFEST_PATH).exists():
            (staging / PACKAGE_MANIFEST_PATH).unlink()
        manifest = _manifest_from_components(
            package_id=PHASE11_BOOTSTRAP_PACKAGE_ID,
            parent_package_id=predecessor_manifest.package_id,
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


def _expected_file_set(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }


def validate_phase11_bootstrap_package(
    predecessor_root: Path,
    active_root: Path,
    budget: InvocationBudget,
) -> dict[str, object]:
    predecessor = predecessor_root.resolve(strict=True)
    active = active_root.resolve(strict=True)
    predecessor_manifest, predecessor_architecture, predecessor_tokenizer, predecessor_tensors, _ = (
        load_package_components(predecessor)
    )
    active_manifest, active_architecture, active_tokenizer, active_tensors, active_adapter = (
        load_package_components(active)
    )
    failures: list[str] = []
    expected_transition = _expected_bank_bytes(transition_tensor_path(predecessor).read_bytes())
    if transition_tensor_path(active).read_bytes() != expected_transition:
        failures.append("generator_bank_tensor_mismatch")
    if active_manifest.payload_tree_hash != _payload_tree_hash(active):
        failures.append("payload_tree_hash_mismatch")
    if active_manifest.parent_package_id != predecessor_manifest.package_id:
        failures.append("parent_package_id_mismatch")
    if active_architecture != predecessor_architecture:
        failures.append("architecture_changed")
    if active_tokenizer != predecessor_tokenizer:
        failures.append("tokenizer_changed")
    if active_tensors.parameter_count != predecessor_tensors.parameter_count:
        failures.append("parameter_count_changed")
    if active_adapter.status != "absent":
        failures.append("adapter_not_absent")
    if active_manifest.model_identity_hash == predecessor_manifest.model_identity_hash:
        failures.append("model_identity_unchanged")
    if active_manifest.generator_policy_hash == predecessor_manifest.generator_policy_hash:
        failures.append("generator_policy_unchanged")
    if active_manifest.planner_policy_hash == predecessor_manifest.planner_policy_hash:
        failures.append("planner_policy_unchanged")
    expected_support = _phase11_support(predecessor, budget)
    for path, expected in expected_support.items():
        observed = load_json_strict((active / path).read_bytes(), require_canonical=True)
        if observed != expected:
            failures.append(f"support_mismatch:{path}")
        field_name = SUPPORT_HASH_FIELD_BY_PATH[path]
        if getattr(active_manifest, field_name) != canonical_json_hash(expected):
            failures.append(f"support_hash_mismatch:{path}")
    if _expected_file_set(predecessor) != _expected_file_set(active):
        failures.append("package_file_set_changed")

    protected_decode = decode_completion(active, PROTECTED_TASK.model_prompt)
    heldout_decode = decode_completion(active, HELDOUT_TASK.model_prompt)
    if protected_decode.completion_text != PROTECTED_TASK.expected_completion:
        failures.append("protected_task_not_retained")
    if heldout_decode.completion_text != HELDOUT_TASK.expected_completion:
        failures.append("phase10_heldout_task_not_retained")

    content = {
        "schema_id": "runtime.v3.phase11.bootstrap_validation.v1",
        "predecessor_package_hash": predecessor_manifest.package_hash,
        "active_package_hash": active_manifest.package_hash,
        "predecessor_model_identity_hash": predecessor_manifest.model_identity_hash,
        "active_model_identity_hash": active_manifest.model_identity_hash,
        "active_generator_hash": active_manifest.generator_policy_hash,
        "active_planner_hash": active_manifest.planner_policy_hash,
        "proposal_protocol_hash": PROPOSAL_PROTOCOL_HASH,
        "budget_hash": budget.budget_hash,
        "protected_decode_hash": protected_decode.result_hash,
        "phase10_heldout_decode_hash": heldout_decode.result_hash,
        "failures": sorted(set(failures)),
        "accepted": not failures,
        "claim_boundary": {
            "host_installed_bootstrap": True,
            "bootstrap_counted_as_autonomous_improvement": False,
            "phase11_exit_closed": False,
        },
    }
    result = dict(content)
    result["report_hash"] = canonical_json_hash(content)
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
    task_id = getattr(task, "task_id")
    prompt_hash = getattr(task, "prompt_hash")
    source_prefix_hash = getattr(task, "source_prefix_hash")
    partition = getattr(task, "partition")
    return TaskRecord(
        task_id=task_id,
        task_class=SELECTED_TASK_CLASS,
        prompt_hash=prompt_hash,
        verifier_spec_hash=canonical_json_hash(
            {
                "verifier": "pinned_lean_theorem_verifier_v1",
                "source_prefix_hash": source_prefix_hash,
            }
        ),
        partition=partition,
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
    heldout_report: TaskVerifierReport,
) -> LearnedRCLMState:
    policies = _policy_identity(manifest)
    reports = tuple(sorted((protected_report, heldout_report), key=lambda item: item.task_id))
    tasks = tuple(
        sorted(
            (_task_record(PROTECTED_TASK), _task_record(HELDOUT_TASK)),
            key=lambda item: item.task_id.encode("utf-8"),
        )
    )
    certifications = tuple(
        sorted((_certification(report) for report in reports), key=lambda item: item.task_id.encode("utf-8"))
    )
    frontier_ids = tuple(sorted((report.task_id for report in reports), key=lambda item: item.encode("utf-8")))
    return LearnedRCLMState(
        package_id=manifest.package_id,
        parent_package_id=manifest.parent_package_id,
        base_state_hash=canonical_json_hash(
            {
                "phase": 11,
                "bootstrap": "host_installed_active_generator",
                "counted_as_autonomous_improvement": False,
            }
        ),
        model=manifest.model_identity(),
        policies=policies,
        self_hosting=SelfHostingBinding(
            generator_component_hash=policies.generator_policy_hash,
            planner_component_hash=policies.planner_policy_hash,
            proposal_protocol_hash=PROPOSAL_PROTOCOL_HASH,
            self_hosting_contract_hash=canonical_json_hash(
                {
                    "phase11_self_hosting_contract": "active_package_proposes_typed_program",
                    "recursive_use_of_modified_generator": False,
                }
            ),
        ),
        task_ledger=TaskLedger(tasks=tasks, certifications=certifications),
        capability_frontier=CapabilityFrontier(task_ids=frontier_ids),
    )


@dataclass(frozen=True, slots=True)
class Phase11BootstrapFixture:
    root: Path
    phase10_reference: Phase10LearnedReference
    active_package_root: Path
    active_manifest: ModelPackageManifest
    active_state: LearnedRCLMState
    protected_report: TaskVerifierReport
    heldout_report: TaskVerifierReport
    validation_report: Mapping[str, object]
    budget: InvocationBudget

    schema_id: ClassVar[str] = "runtime.v3.phase11.bootstrap_fixture.v1"

    @property
    def accepted(self) -> bool:
        return (
            self.validation_report["accepted"] is True
            and self.protected_report.solved
            and self.heldout_report.solved
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
            "phase10_candidate_package_hash": self.phase10_reference.candidate_manifest.package_hash,
            "active_manifest": self.active_manifest.to_json(),
            "active_state": self.active_state.to_json(),
            "protected_report": self.protected_report.to_json(),
            "heldout_report": self.heldout_report.to_json(),
            "validation_report": dict(self.validation_report),
            "budget": self.budget.to_json(),
            "claim_boundary": {
                "host_installed_bootstrap": True,
                "bootstrap_counted_as_autonomous_improvement": False,
                "active_model_proposal_executed": False,
                "phase11_exit_closed": False,
            },
        }


def build_phase11_bootstrap(output_root: Path) -> Phase11BootstrapFixture:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"Phase 11 bootstrap root already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    phase10_reference = build_phase10_learned_reference(root / "phase10_source")
    budget = default_phase11_budget()
    active_root = root / "active_package"
    active_manifest = _build_active_package(
        root / "phase10_source" / "candidate",
        active_root,
        budget,
    )
    validation = validate_phase11_bootstrap_package(
        root / "phase10_source" / "candidate",
        active_root,
        budget,
    )
    protected_decode = decode_completion(active_root, PROTECTED_TASK.model_prompt)
    heldout_decode = decode_completion(active_root, HELDOUT_TASK.model_prompt)
    protected_report = expected_success_report(
        protected_decode,
        PROTECTED_TASK,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    heldout_report = expected_success_report(
        heldout_decode,
        HELDOUT_TASK,
        lean_toolchain=PINNED_LEAN_TOOLCHAIN,
    )
    state = _active_state(active_manifest, protected_report, heldout_report)
    fixture = Phase11BootstrapFixture(
        root=root,
        phase10_reference=phase10_reference,
        active_package_root=active_root,
        active_manifest=active_manifest,
        active_state=state,
        protected_report=protected_report,
        heldout_report=heldout_report,
        validation_report=validation,
        budget=budget,
    )
    if not fixture.accepted:
        raise ValueError("Phase 11 active-generator bootstrap did not validate")
    return fixture


__all__ = [
    "Phase11BootstrapFixture",
    "build_phase11_bootstrap",
    "validate_phase11_bootstrap_package",
]
