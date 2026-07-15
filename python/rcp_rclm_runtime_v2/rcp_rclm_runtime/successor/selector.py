from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from rcp_rclm_runtime.canonical.hashing import (
    SemanticFileRecord,
    canonical_json_hash,
    sha256_hex,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.errors import RuntimeValidationError, SchemaValidationError
from rcp_rclm_runtime.mathematics.classical import apply_binary_update
from rcp_rclm_runtime.schema.state import ClassicalBinaryStateRecord
from rcp_rclm_runtime.schema.update import ClassicalBinaryUpdateRecord
from rcp_rclm_runtime.checker.reference import (
    canonical_rclm_state,
    canonical_rclm_update,
)
from rcp_rclm_runtime.generator.grammar import (
    update_name_for_proposal,
    validate_untrusted_proposal,
)
from rcp_rclm_runtime.generator.protocol import (
    ReferenceGeneratorInputRecord,
    ReferenceProposalRecord,
)
from rcp_rclm_runtime.successor.policies import (
    MEMORY_POLICY_PATH,
    STATE_PATH,
    VERIFICATION_POLICY_PATH,
    baseline_memory_policy,
    baseline_verification_policy,
    content_addressed_memory_policy,
    hardened_verification_policy,
    policy_bytes,
)
from rcp_rclm_runtime.successor.records import (
    Phase6ReasonCode,
    Phase6SelectionRecord,
    SelectedFileOperationRecord,
)
from rcp_rclm_runtime.successor.workspace import LoadedPredecessorPackage

PHASE6_REFERENCE_SELECTION_POLICY_ID: Final[str] = (
    "rcp-rclm-phase6-bounded-reference-selector-v1"
)


class Phase6SelectionError(ValueError):
    __slots__ = ("reason_code", "detail")

    def __init__(self, reason_code: Phase6ReasonCode, detail: str) -> None:
        super().__init__(reason_code.value, detail)
        self.reason_code = reason_code
        self.detail = detail

    def __str__(self) -> str:
        return f"{self.reason_code.value}: {self.detail}"


def select_reference_successor(
    generator_input: ReferenceGeneratorInputRecord,
    proposal: ReferenceProposalRecord,
    predecessor: LoadedPredecessorPackage,
) -> Phase6SelectionRecord:
    proposal_result = validate_untrusted_proposal(generator_input, proposal)
    if proposal_result.status != "pass":
        raise Phase6SelectionError(
            Phase6ReasonCode.PROPOSAL_INVALID,
            "untrusted proposal does not match the public bounded grammar",
        )
    if predecessor.manifest.package_id != generator_input.predecessor.package_id:
        raise Phase6SelectionError(
            Phase6ReasonCode.PREDECESSOR_MISMATCH,
            "filesystem predecessor package ID differs from generator input",
        )
    if (
        predecessor.manifest.phase5_manifest_hash
        != generator_input.predecessor.manifest_hash
    ):
        raise Phase6SelectionError(
            Phase6ReasonCode.PREDECESSOR_MISMATCH,
            "filesystem predecessor does not bind the Phase 5A manifest",
        )
    if predecessor.state.to_json() != generator_input.predecessor.state.to_json():
        raise Phase6SelectionError(
            Phase6ReasonCode.PREDECESSOR_MISMATCH,
            "filesystem predecessor state differs from generator input",
        )
    predecessor_core = predecessor.state.core
    if not isinstance(predecessor_core, ClassicalBinaryStateRecord):
        raise Phase6SelectionError(
            Phase6ReasonCode.UNSUPPORTED_SCOPE,
            "Phase 6 reference selector supports only Gate B classical states",
        )
    try:
        update_name = update_name_for_proposal(proposal.proposal)
        selected_update = canonical_rclm_update(
            ClassicalBinaryUpdateRecord(update_name)
        )
        successor_name = apply_binary_update(
            predecessor_core.state,
            selected_update.core.update,
        )
        successor = canonical_rclm_state(
            ClassicalBinaryStateRecord(successor_name)
        )
    except (RuntimeValidationError, TypeError, ValueError) as exc:
        raise Phase6SelectionError(
            Phase6ReasonCode.SELECTION_FAILED,
            f"could not derive the typed selected update: {exc}",
        ) from exc

    record_by_path = {
        record.path: record for record in predecessor.measurement.records
    }
    operations: list[SelectedFileOperationRecord] = []
    state_before = _required_file_record(record_by_path, STATE_PATH)
    state_after_content = canonical_json_bytes(successor.to_json())
    if state_before.sha256 != sha256_hex(state_after_content):
        operations.append(
            SelectedFileOperationRecord.write(
                path=STATE_PATH,
                component_kind=None,
                expected_before_hash=state_before.sha256,
                expected_before_mode=state_before.mode,
                after_mode="0644",
                content=state_after_content,
            )
        )

    if proposal.word == "improve":
        _require_exact_reference_policy(
            predecessor,
            VERIFICATION_POLICY_PATH,
            policy_bytes(baseline_verification_policy()),
        )
        policy_record = _required_file_record(
            record_by_path,
            VERIFICATION_POLICY_PATH,
        )
        operations.append(
            SelectedFileOperationRecord.write(
                path=VERIFICATION_POLICY_PATH,
                component_kind="verification_policy",
                expected_before_hash=policy_record.sha256,
                expected_before_mode=policy_record.mode,
                after_mode="0644",
                content=policy_bytes(hardened_verification_policy()),
            )
        )
    else:
        _require_exact_reference_policy(
            predecessor,
            MEMORY_POLICY_PATH,
            policy_bytes(baseline_memory_policy()),
        )
        policy_record = _required_file_record(
            record_by_path,
            MEMORY_POLICY_PATH,
        )
        operations.append(
            SelectedFileOperationRecord.write(
                path=MEMORY_POLICY_PATH,
                component_kind="memory_policy",
                expected_before_hash=policy_record.sha256,
                expected_before_mode=policy_record.mode,
                after_mode="0644",
                content=policy_bytes(content_addressed_memory_policy()),
            )
        )

    operations.sort(key=lambda item: item.path.encode("utf-8"))
    component_kinds = tuple(
        sorted(
            {
                operation.component_kind
                for operation in operations
                if operation.component_kind is not None
            }
        )
    )
    update_json = selected_update.to_json()
    return Phase6SelectionRecord(
        transition_id=generator_input.transition_id,
        proposal_hash=proposal.proposal_hash,
        generator_request_hash=generator_input.input_hash,
        predecessor_package_id=predecessor.manifest.package_id,
        predecessor_manifest_hash=predecessor.manifest.manifest_hash,
        phase5_predecessor_manifest_hash=(
            predecessor.manifest.phase5_manifest_hash
        ),
        selection_policy_id=PHASE6_REFERENCE_SELECTION_POLICY_ID,
        selected_update=update_json,
        selected_update_hash=canonical_json_hash(update_json),
        operations=tuple(operations),
        substantive_component_kinds=component_kinds,
    )


def _required_file_record(
    records: dict[str, SemanticFileRecord],
    path: str,
) -> SemanticFileRecord:
    record = records.get(path)
    if record is None:
        raise Phase6SelectionError(
            Phase6ReasonCode.PREDECESSOR_MISMATCH,
            f"predecessor is missing required file: {path}",
        )
    return record


def _require_exact_reference_policy(
    predecessor: LoadedPredecessorPackage,
    path: str,
    expected: bytes,
) -> None:
    candidate = predecessor.payload_root.joinpath(*path.split("/"))
    try:
        observed = candidate.read_bytes()
    except OSError as exc:
        raise Phase6SelectionError(
            Phase6ReasonCode.PREDECESSOR_MISMATCH,
            f"could not read required predecessor policy {path}: {exc}",
        ) from exc
    if observed != expected:
        raise Phase6SelectionError(
            Phase6ReasonCode.PREDECESSOR_MISMATCH,
            f"predecessor policy is outside the selected reference grammar: {path}",
        )
