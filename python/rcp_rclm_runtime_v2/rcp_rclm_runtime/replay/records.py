from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Literal, TypeAlias, cast

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import (
    FrozenJson,
    freeze_json,
    require_schema_id,
    require_string,
    require_structural_integer,
    strict_object,
    thaw_json,
)
from rcp_rclm_runtime.schema.verdict import FrozenHashMap

PHASE8_ATTEMPT_INDEX_SCHEMA_ID = "runtime.phase8_attempt_index.v2"
PHASE8_BUNDLE_MANIFEST_SCHEMA_ID = "runtime.phase8_replay_bundle_manifest.v2"
PHASE8_STAGE_RESULT_SCHEMA_ID = "runtime.phase8_stage_result.v2"
PHASE8_ATTEMPT_REPORT_SCHEMA_ID = "runtime.phase8_attempt_replay_report.v2"
PHASE8_REPLAY_REPORT_SCHEMA_ID = "runtime.phase8_replay_report.v2"

ReplayVerdict: TypeAlias = Literal["accept", "reject", "indeterminate"]
ReplayStageStatus: TypeAlias = Literal["pass", "fail", "indeterminate", "not_evaluated"]
LedgerEvent: TypeAlias = Literal["promotion", "rejection", "indeterminate"]
AttemptVerdict: TypeAlias = Literal["accept", "reject", "indeterminate"]


class Phase8ReasonCode(StrEnum):
    BUNDLE_SCHEMA_INVALID = "PHASE8_BUNDLE_SCHEMA_INVALID"
    BUNDLE_LAYOUT_INVALID = "PHASE8_BUNDLE_LAYOUT_INVALID"
    BUNDLE_HASH_MISMATCH = "PHASE8_BUNDLE_HASH_MISMATCH"
    STORE_VERIFICATION_FAILED = "PHASE8_STORE_VERIFICATION_FAILED"
    LEDGER_CHAIN_MISMATCH = "PHASE8_LEDGER_CHAIN_MISMATCH"
    PACKAGE_CHAIN_MISMATCH = "PHASE8_PACKAGE_CHAIN_MISMATCH"
    GENERATOR_INPUT_MISMATCH = "PHASE8_GENERATOR_INPUT_MISMATCH"
    GENERATOR_OUTPUT_MALFORMED = "PHASE8_GENERATOR_OUTPUT_MALFORMED"
    GENERATOR_REPLAY_MISMATCH = "PHASE8_GENERATOR_REPLAY_MISMATCH"
    PROPOSAL_VALIDATION_FAILED = "PHASE8_PROPOSAL_VALIDATION_FAILED"
    SELECTION_REPLAY_MISMATCH = "PHASE8_SELECTION_REPLAY_MISMATCH"
    REALIZATION_REPLAY_MISMATCH = "PHASE8_REALIZATION_REPLAY_MISMATCH"
    EVALUATION_REPLAY_MISMATCH = "PHASE8_EVALUATION_REPLAY_MISMATCH"
    CERTIFICATE_REPLAY_MISMATCH = "PHASE8_CERTIFICATE_REPLAY_MISMATCH"
    LEAN_REPLAY_FAILED = "PHASE8_LEAN_REPLAY_FAILED"
    CHECKER_REPLAY_MISMATCH = "PHASE8_CHECKER_REPLAY_MISMATCH"
    REJECTION_REPLAY_MISMATCH = "PHASE8_REJECTION_REPLAY_MISMATCH"
    RESOURCE_REPLAY_MISMATCH = "PHASE8_RESOURCE_REPLAY_MISMATCH"
    ROLLBACK_REPLAY_MISMATCH = "PHASE8_ROLLBACK_REPLAY_MISMATCH"
    PARENT_LINK_MISMATCH = "PHASE8_PARENT_LINK_MISMATCH"
    GENERATOR_INVOCATION_DETECTED = "PHASE8_GENERATOR_INVOCATION_DETECTED"
    INTERNAL_ERROR = "PHASE8_INTERNAL_ERROR"


@dataclass(frozen=True, slots=True)
class Phase8AttemptIndexRecord:
    ledger_sequence_number: int
    ledger_event: LedgerEvent
    run_id: str
    attempt_index: int
    attempt_verdict: AttemptVerdict
    predecessor_package_hash: str
    successor_package_hash: str
    ledger_entry_hash: str
    controller_report_hash: str
    attempt_report_hash: str
    generator_input_hash: str
    proposal_hash: str | None
    selection_hash: str | None
    phase6_report_hash: str | None
    candidate_package_tree_hash: str | None
    evaluation_hash: str | None
    certificate_hash: str | None
    lean_report_hash: str | None
    checker_report_hash: str | None
    artifact_hashes: FrozenHashMap
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = PHASE8_ATTEMPT_INDEX_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.run_id, "phase8_attempt_index.run_id")
        for name, value in (
            ("ledger_sequence_number", self.ledger_sequence_number),
            ("attempt_index", self.attempt_index),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SchemaValidationError(
                    f"phase8_attempt_index.{name}",
                    "expected a nonnegative integer",
                )
        if self.ledger_sequence_number < 1:
            raise SchemaValidationError(
                "phase8_attempt_index.ledger_sequence_number",
                "replay attempts begin after the bootstrap entry",
            )
        if self.ledger_event not in {"promotion", "rejection", "indeterminate"}:
            raise SchemaValidationError(
                "phase8_attempt_index.ledger_event",
                "unsupported ledger event",
            )
        if self.attempt_verdict not in {"accept", "reject", "indeterminate"}:
            raise SchemaValidationError(
                "phase8_attempt_index.attempt_verdict",
                "unsupported attempt verdict",
            )
        for name, value in (
            ("predecessor_package_hash", self.predecessor_package_hash),
            ("successor_package_hash", self.successor_package_hash),
            ("ledger_entry_hash", self.ledger_entry_hash),
            ("controller_report_hash", self.controller_report_hash),
            ("attempt_report_hash", self.attempt_report_hash),
            ("generator_input_hash", self.generator_input_hash),
        ):
            validate_hash256(value, f"phase8_attempt_index.{name}")
        for name, value in (
            ("proposal_hash", self.proposal_hash),
            ("selection_hash", self.selection_hash),
            ("phase6_report_hash", self.phase6_report_hash),
            ("candidate_package_tree_hash", self.candidate_package_tree_hash),
            ("evaluation_hash", self.evaluation_hash),
            ("certificate_hash", self.certificate_hash),
            ("lean_report_hash", self.lean_report_hash),
            ("checker_report_hash", self.checker_report_hash),
        ):
            if value is not None:
                validate_hash256(value, f"phase8_attempt_index.{name}")
        if self.ledger_event == "promotion":
            if self.attempt_verdict != "accept":
                raise SchemaValidationError(
                    "phase8_attempt_index.attempt_verdict",
                    "promotion requires an accepted source attempt",
                )
            if self.predecessor_package_hash == self.successor_package_hash:
                raise SchemaValidationError(
                    "phase8_attempt_index.successor_package_hash",
                    "promotion must change the active package",
                )
            required = (
                self.proposal_hash,
                self.selection_hash,
                self.phase6_report_hash,
                self.candidate_package_tree_hash,
                self.evaluation_hash,
                self.certificate_hash,
                self.lean_report_hash,
                self.checker_report_hash,
            )
            if any(value is None for value in required):
                raise SchemaValidationError(
                    "phase8_attempt_index",
                    "promoted replay entry requires the complete verification chain",
                )
        else:
            expected_verdict = "reject" if self.ledger_event == "rejection" else "indeterminate"
            if self.attempt_verdict != expected_verdict:
                raise SchemaValidationError(
                    "phase8_attempt_index.attempt_verdict",
                    "ledger event and source attempt verdict differ",
                )
            if self.predecessor_package_hash != self.successor_package_hash:
                raise SchemaValidationError(
                    "phase8_attempt_index.successor_package_hash",
                    "nonpromotion must preserve the active package",
                )
        required_artifact_keys = {
            "attempt_report",
            "controller_report",
            "first_generator_input",
            "first_generator_stderr",
            "first_generator_stdout",
            "first_process_report",
            "first_source_guard",
            "generator_input",
            "proposal",
            "second_generator_input",
            "second_generator_stderr",
            "second_generator_stdout",
            "second_process_report",
            "second_source_guard",
        }
        observed_artifact_keys = {key for key, _ in self.artifact_hashes.entries}
        if not required_artifact_keys.issubset(observed_artifact_keys):
            missing = ", ".join(sorted(required_artifact_keys - observed_artifact_keys))
            raise SchemaValidationError(
                "phase8_attempt_index.artifact_hashes",
                f"missing required replay artifacts: {missing}",
            )
        if self.ledger_event == "promotion":
            promotion_keys = {
                "candidate_package_tree",
                "certificate",
                "checker_request",
                "evaluation",
                "generated_lean_source",
                "generated_source_record",
                "hardened_checker_report",
                "lean_report",
                "lean_source_guard",
                "package_integrity",
                "phase6_report",
                "resource_usage",
                "rollback_archive",
                "rollback_record",
                "selection",
            }
            if not promotion_keys.issubset(observed_artifact_keys):
                missing = ", ".join(sorted(promotion_keys - observed_artifact_keys))
                raise SchemaValidationError(
                    "phase8_attempt_index.artifact_hashes",
                    f"promoted replay entry is missing artifacts: {missing}",
                )
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase8_attempt_index.contract_version",
                f"expected {CONTRACT_VERSION}",
            )

    @property
    def index_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase8_attempt_index",
    ) -> Phase8AttemptIndexRecord:
        fields = {
            "schema_id",
            "contract_version",
            "ledger_sequence_number",
            "ledger_event",
            "run_id",
            "attempt_index",
            "attempt_verdict",
            "predecessor_package_hash",
            "successor_package_hash",
            "ledger_entry_hash",
            "controller_report_hash",
            "attempt_report_hash",
            "generator_input_hash",
            "proposal_hash",
            "selection_hash",
            "phase6_report_hash",
            "candidate_package_tree_hash",
            "evaluation_hash",
            "certificate_hash",
            "lean_report_hash",
            "checker_report_hash",
            "artifact_hashes",
            "index_hash",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        record = cls(
            ledger_sequence_number=require_structural_integer(
                obj["ledger_sequence_number"],
                f"{path}.ledger_sequence_number",
                minimum=1,
            ),
            ledger_event=cast(
                LedgerEvent,
                _literal(
                    obj["ledger_event"],
                    f"{path}.ledger_event",
                    {"promotion", "rejection", "indeterminate"},
                ),
            ),
            run_id=require_string(obj["run_id"], f"{path}.run_id"),
            attempt_index=require_structural_integer(
                obj["attempt_index"],
                f"{path}.attempt_index",
                minimum=0,
            ),
            attempt_verdict=cast(
                AttemptVerdict,
                _literal(
                    obj["attempt_verdict"],
                    f"{path}.attempt_verdict",
                    {"accept", "reject", "indeterminate"},
                ),
            ),
            predecessor_package_hash=_required_hash(
                obj["predecessor_package_hash"],
                f"{path}.predecessor_package_hash",
            ),
            successor_package_hash=_required_hash(
                obj["successor_package_hash"],
                f"{path}.successor_package_hash",
            ),
            ledger_entry_hash=_required_hash(
                obj["ledger_entry_hash"],
                f"{path}.ledger_entry_hash",
            ),
            controller_report_hash=_required_hash(
                obj["controller_report_hash"],
                f"{path}.controller_report_hash",
            ),
            attempt_report_hash=_required_hash(
                obj["attempt_report_hash"],
                f"{path}.attempt_report_hash",
            ),
            generator_input_hash=_required_hash(
                obj["generator_input_hash"],
                f"{path}.generator_input_hash",
            ),
            proposal_hash=_optional_hash(obj["proposal_hash"], f"{path}.proposal_hash"),
            selection_hash=_optional_hash(obj["selection_hash"], f"{path}.selection_hash"),
            phase6_report_hash=_optional_hash(
                obj["phase6_report_hash"],
                f"{path}.phase6_report_hash",
            ),
            candidate_package_tree_hash=_optional_hash(
                obj["candidate_package_tree_hash"],
                f"{path}.candidate_package_tree_hash",
            ),
            evaluation_hash=_optional_hash(
                obj["evaluation_hash"],
                f"{path}.evaluation_hash",
            ),
            certificate_hash=_optional_hash(
                obj["certificate_hash"],
                f"{path}.certificate_hash",
            ),
            lean_report_hash=_optional_hash(
                obj["lean_report_hash"],
                f"{path}.lean_report_hash",
            ),
            checker_report_hash=_optional_hash(
                obj["checker_report_hash"],
                f"{path}.checker_report_hash",
            ),
            artifact_hashes=_parse_hash_map(
                obj["artifact_hashes"],
                f"{path}.artifact_hashes",
            ),
            contract_version=require_string(
                obj["contract_version"],
                f"{path}.contract_version",
            ),
        )
        if _required_hash(obj["index_hash"], f"{path}.index_hash") != record.index_hash:
            raise SchemaValidationError(f"{path}.index_hash", "attempt index hash mismatch")
        return record

    def _content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "ledger_sequence_number": self.ledger_sequence_number,
            "ledger_event": self.ledger_event,
            "run_id": self.run_id,
            "attempt_index": self.attempt_index,
            "attempt_verdict": self.attempt_verdict,
            "predecessor_package_hash": self.predecessor_package_hash,
            "successor_package_hash": self.successor_package_hash,
            "ledger_entry_hash": self.ledger_entry_hash,
            "controller_report_hash": self.controller_report_hash,
            "attempt_report_hash": self.attempt_report_hash,
            "generator_input_hash": self.generator_input_hash,
            "proposal_hash": self.proposal_hash,
            "selection_hash": self.selection_hash,
            "phase6_report_hash": self.phase6_report_hash,
            "candidate_package_tree_hash": self.candidate_package_tree_hash,
            "evaluation_hash": self.evaluation_hash,
            "certificate_hash": self.certificate_hash,
            "lean_report_hash": self.lean_report_hash,
            "checker_report_hash": self.checker_report_hash,
            "artifact_hashes": self.artifact_hashes.to_json(),
        }

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value["index_hash"] = self.index_hash
        return value


@dataclass(frozen=True, slots=True)
class Phase8ReplayBundleManifestRecord:
    replay_id: str
    source_phase7_policy_hash: str
    source_store_tree_hash: str
    final_active_pointer_hash: str
    final_active_package_hash: str
    ledger_head_hash: str
    ledger_entry_hashes: Sequence[str]
    package_chain: Sequence[str]
    attempts: Sequence[Phase8AttemptIndexRecord]
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = PHASE8_BUNDLE_MANIFEST_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.replay_id, "phase8_bundle.replay_id")
        for name, value in (
            ("source_phase7_policy_hash", self.source_phase7_policy_hash),
            ("source_store_tree_hash", self.source_store_tree_hash),
            ("final_active_pointer_hash", self.final_active_pointer_hash),
            ("final_active_package_hash", self.final_active_package_hash),
            ("ledger_head_hash", self.ledger_head_hash),
        ):
            validate_hash256(value, f"phase8_bundle.{name}")
        ledger_hashes = tuple(self.ledger_entry_hashes)
        package_chain = tuple(self.package_chain)
        attempts = tuple(self.attempts)
        object.__setattr__(self, "ledger_entry_hashes", ledger_hashes)
        object.__setattr__(self, "package_chain", package_chain)
        object.__setattr__(self, "attempts", attempts)
        if len(ledger_hashes) < 2 or len(ledger_hashes) != len(set(ledger_hashes)):
            raise SchemaValidationError(
                "phase8_bundle.ledger_entry_hashes",
                "replay requires a unique bootstrap-plus-transition ledger chain",
            )
        for index, value in enumerate(ledger_hashes):
            validate_hash256(value, f"phase8_bundle.ledger_entry_hashes[{index}]")
        if len(package_chain) < 2 or len(package_chain) != len(set(package_chain)):
            raise SchemaValidationError(
                "phase8_bundle.package_chain",
                "replay requires a finite unique package chain",
            )
        for index, value in enumerate(package_chain):
            validate_hash256(value, f"phase8_bundle.package_chain[{index}]")
        if package_chain[-1] != self.final_active_package_hash:
            raise SchemaValidationError(
                "phase8_bundle.final_active_package_hash",
                "final active package must end the package chain",
            )
        sequence_numbers = [attempt.ledger_sequence_number for attempt in attempts]
        if sequence_numbers != sorted(sequence_numbers):
            raise SchemaValidationError(
                "phase8_bundle.attempts",
                "attempt index records must follow ledger order",
            )
        if len(sequence_numbers) != len(set(sequence_numbers)):
            raise SchemaValidationError(
                "phase8_bundle.attempts",
                "duplicate ledger sequence number",
            )
        if len(attempts) != len(ledger_hashes) - 1:
            raise SchemaValidationError(
                "phase8_bundle.attempts",
                "every non-bootstrap ledger entry requires one replay attempt",
            )
        if tuple(attempt.ledger_entry_hash for attempt in attempts) != ledger_hashes[1:]:
            raise SchemaValidationError(
                "phase8_bundle.attempts",
                "attempt index ledger hashes do not match the manifest ledger chain",
            )
        observed_chain = [package_chain[0]]
        for attempt in attempts:
            if attempt.predecessor_package_hash != observed_chain[-1]:
                raise SchemaValidationError(
                    "phase8_bundle.attempts",
                    "attempt predecessor does not match the active package chain",
                )
            if attempt.ledger_event == "promotion":
                observed_chain.append(attempt.successor_package_hash)
        if tuple(observed_chain) != package_chain:
            raise SchemaValidationError(
                "phase8_bundle.package_chain",
                "promotion attempts do not reconstruct the package chain",
            )
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase8_bundle.contract_version",
                f"expected {CONTRACT_VERSION}",
            )

    @property
    def promotion_count(self) -> int:
        return sum(attempt.ledger_event == "promotion" for attempt in self.attempts)

    @property
    def rejection_count(self) -> int:
        return sum(attempt.ledger_event == "rejection" for attempt in self.attempts)

    @property
    def indeterminate_count(self) -> int:
        return sum(attempt.ledger_event == "indeterminate" for attempt in self.attempts)

    @property
    def manifest_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase8_bundle",
    ) -> Phase8ReplayBundleManifestRecord:
        fields = {
            "schema_id",
            "contract_version",
            "replay_id",
            "source_phase7_policy_hash",
            "source_store_tree_hash",
            "final_active_pointer_hash",
            "final_active_package_hash",
            "ledger_head_hash",
            "ledger_entry_hashes",
            "package_chain",
            "attempts",
            "promotion_count",
            "rejection_count",
            "indeterminate_count",
            "manifest_hash",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        ledger_raw = _require_array(obj["ledger_entry_hashes"], f"{path}.ledger_entry_hashes")
        package_raw = _require_array(obj["package_chain"], f"{path}.package_chain")
        attempts_raw = _require_array(obj["attempts"], f"{path}.attempts")
        record = cls(
            replay_id=require_string(obj["replay_id"], f"{path}.replay_id"),
            source_phase7_policy_hash=_required_hash(
                obj["source_phase7_policy_hash"],
                f"{path}.source_phase7_policy_hash",
            ),
            source_store_tree_hash=_required_hash(
                obj["source_store_tree_hash"],
                f"{path}.source_store_tree_hash",
            ),
            final_active_pointer_hash=_required_hash(
                obj["final_active_pointer_hash"],
                f"{path}.final_active_pointer_hash",
            ),
            final_active_package_hash=_required_hash(
                obj["final_active_package_hash"],
                f"{path}.final_active_package_hash",
            ),
            ledger_head_hash=_required_hash(
                obj["ledger_head_hash"],
                f"{path}.ledger_head_hash",
            ),
            ledger_entry_hashes=tuple(
                _required_hash(item, f"{path}.ledger_entry_hashes[{index}]")
                for index, item in enumerate(ledger_raw)
            ),
            package_chain=tuple(
                _required_hash(item, f"{path}.package_chain[{index}]")
                for index, item in enumerate(package_raw)
            ),
            attempts=tuple(
                Phase8AttemptIndexRecord.from_json(item, f"{path}.attempts[{index}]")
                for index, item in enumerate(attempts_raw)
            ),
            contract_version=require_string(
                obj["contract_version"],
                f"{path}.contract_version",
            ),
        )
        if require_structural_integer(
            obj["promotion_count"],
            f"{path}.promotion_count",
            minimum=0,
        ) != record.promotion_count:
            raise SchemaValidationError(f"{path}.promotion_count", "promotion count mismatch")
        if require_structural_integer(
            obj["rejection_count"],
            f"{path}.rejection_count",
            minimum=0,
        ) != record.rejection_count:
            raise SchemaValidationError(f"{path}.rejection_count", "rejection count mismatch")
        if require_structural_integer(
            obj["indeterminate_count"],
            f"{path}.indeterminate_count",
            minimum=0,
        ) != record.indeterminate_count:
            raise SchemaValidationError(
                f"{path}.indeterminate_count",
                "indeterminate count mismatch",
            )
        if _required_hash(obj["manifest_hash"], f"{path}.manifest_hash") != record.manifest_hash:
            raise SchemaValidationError(f"{path}.manifest_hash", "bundle manifest hash mismatch")
        return record

    def _content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "replay_id": self.replay_id,
            "source_phase7_policy_hash": self.source_phase7_policy_hash,
            "source_store_tree_hash": self.source_store_tree_hash,
            "final_active_pointer_hash": self.final_active_pointer_hash,
            "final_active_package_hash": self.final_active_package_hash,
            "ledger_head_hash": self.ledger_head_hash,
            "ledger_entry_hashes": list(self.ledger_entry_hashes),
            "package_chain": list(self.package_chain),
            "attempts": [attempt.to_json() for attempt in self.attempts],
            "promotion_count": self.promotion_count,
            "rejection_count": self.rejection_count,
            "indeterminate_count": self.indeterminate_count,
        }

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value["manifest_hash"] = self.manifest_hash
        return value


@dataclass(frozen=True, slots=True)
class Phase8StageResult:
    stage: str
    status: ReplayStageStatus
    reason_codes: Sequence[Phase8ReasonCode]
    evidence: FrozenJson

    schema_id: ClassVar[str] = PHASE8_STAGE_RESULT_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.stage, "phase8_stage.stage")
        if self.status not in {"pass", "fail", "indeterminate", "not_evaluated"}:
            raise SchemaValidationError("phase8_stage.status", "unsupported stage status")
        reasons = tuple(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "evidence", freeze_json(thaw_json(self.evidence)))
        if len(reasons) != len(set(reasons)):
            raise SchemaValidationError("phase8_stage.reason_codes", "duplicate reason code")
        if self.status == "pass" and reasons:
            raise SchemaValidationError("phase8_stage.reason_codes", "passing stage cannot fail")
        if self.status in {"fail", "indeterminate"} and not reasons:
            raise SchemaValidationError(
                "phase8_stage.reason_codes",
                "nonpassing stage requires a reason code",
            )
        if self.status == "not_evaluated" and reasons:
            raise SchemaValidationError(
                "phase8_stage.reason_codes",
                "not-evaluated stage cannot have reasons",
            )

    @property
    def evidence_hash(self) -> str:
        return canonical_json_hash(thaw_json(self.evidence))

    @classmethod
    def build(
        cls,
        stage: str,
        status: ReplayStageStatus,
        reason_codes: Sequence[Phase8ReasonCode],
        evidence: object,
    ) -> Phase8StageResult:
        return cls(stage, status, tuple(reason_codes), freeze_json(evidence))

    @classmethod
    def from_json(cls, value: object, path: str = "phase8_stage") -> Phase8StageResult:
        fields = {"schema_id", "stage", "status", "reason_codes", "evidence", "evidence_hash"}
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        record = cls(
            stage=require_string(obj["stage"], f"{path}.stage"),
            status=cast(
                ReplayStageStatus,
                _literal(
                    obj["status"],
                    f"{path}.status",
                    {"pass", "fail", "indeterminate", "not_evaluated"},
                ),
            ),
            reason_codes=_parse_reason_array(obj["reason_codes"], f"{path}.reason_codes"),
            evidence=freeze_json(obj["evidence"], f"{path}.evidence"),
        )
        if _required_hash(obj["evidence_hash"], f"{path}.evidence_hash") != record.evidence_hash:
            raise SchemaValidationError(f"{path}.evidence_hash", "stage evidence hash mismatch")
        return record

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "stage": self.stage,
            "status": self.status,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "evidence": thaw_json(self.evidence),
            "evidence_hash": self.evidence_hash,
        }


@dataclass(frozen=True, slots=True)
class Phase8AttemptReplayReport:
    ledger_sequence_number: int
    run_id: str
    attempt_index: int
    source_attempt_report_hash: str
    source_ledger_entry_hash: str
    verdict: ReplayVerdict
    reason_codes: Sequence[Phase8ReasonCode]
    generator_invocations: int
    stages: Sequence[Phase8StageResult]
    recomputed_hashes: FrozenHashMap
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = PHASE8_ATTEMPT_REPORT_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.run_id, "phase8_attempt_report.run_id")
        for name, value in (
            ("ledger_sequence_number", self.ledger_sequence_number),
            ("attempt_index", self.attempt_index),
            ("generator_invocations", self.generator_invocations),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SchemaValidationError(
                    f"phase8_attempt_report.{name}",
                    "expected a nonnegative integer",
                )
        if self.generator_invocations != 0:
            raise SchemaValidationError(
                "phase8_attempt_report.generator_invocations",
                "independent replay must not invoke the generator",
            )
        validate_hash256(
            self.source_attempt_report_hash,
            "phase8_attempt_report.source_attempt_report_hash",
        )
        validate_hash256(
            self.source_ledger_entry_hash,
            "phase8_attempt_report.source_ledger_entry_hash",
        )
        if self.verdict not in {"accept", "reject", "indeterminate"}:
            raise SchemaValidationError("phase8_attempt_report.verdict", "unsupported verdict")
        reasons = tuple(self.reason_codes)
        stages = tuple(self.stages)
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "stages", stages)
        if len(reasons) != len(set(reasons)):
            raise SchemaValidationError("phase8_attempt_report.reason_codes", "duplicate reason")
        if self.verdict == "accept" and reasons:
            raise SchemaValidationError(
                "phase8_attempt_report.reason_codes",
                "accepted replay cannot contain failure reasons",
            )
        if self.verdict != "accept" and not reasons:
            raise SchemaValidationError(
                "phase8_attempt_report.reason_codes",
                "nonaccepting replay requires a reason",
            )
        if self.verdict == "accept" and any(stage.status != "pass" for stage in stages):
            raise SchemaValidationError(
                "phase8_attempt_report.stages",
                "accepted replay requires every stage to pass",
            )
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase8_attempt_report.contract_version",
                f"expected {CONTRACT_VERSION}",
            )

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase8_attempt_report",
    ) -> Phase8AttemptReplayReport:
        fields = {
            "schema_id",
            "contract_version",
            "ledger_sequence_number",
            "run_id",
            "attempt_index",
            "source_attempt_report_hash",
            "source_ledger_entry_hash",
            "verdict",
            "reason_codes",
            "generator_invocations",
            "stages",
            "recomputed_hashes",
            "report_hash",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        stages_raw = _require_array(obj["stages"], f"{path}.stages")
        record = cls(
            ledger_sequence_number=require_structural_integer(
                obj["ledger_sequence_number"],
                f"{path}.ledger_sequence_number",
                minimum=1,
            ),
            run_id=require_string(obj["run_id"], f"{path}.run_id"),
            attempt_index=require_structural_integer(
                obj["attempt_index"],
                f"{path}.attempt_index",
                minimum=0,
            ),
            source_attempt_report_hash=_required_hash(
                obj["source_attempt_report_hash"],
                f"{path}.source_attempt_report_hash",
            ),
            source_ledger_entry_hash=_required_hash(
                obj["source_ledger_entry_hash"],
                f"{path}.source_ledger_entry_hash",
            ),
            verdict=cast(
                ReplayVerdict,
                _literal(obj["verdict"], f"{path}.verdict", {"accept", "reject", "indeterminate"}),
            ),
            reason_codes=_parse_reason_array(obj["reason_codes"], f"{path}.reason_codes"),
            generator_invocations=require_structural_integer(
                obj["generator_invocations"],
                f"{path}.generator_invocations",
                minimum=0,
                maximum=0,
            ),
            stages=tuple(
                Phase8StageResult.from_json(item, f"{path}.stages[{index}]")
                for index, item in enumerate(stages_raw)
            ),
            recomputed_hashes=_parse_hash_map(
                obj["recomputed_hashes"],
                f"{path}.recomputed_hashes",
            ),
            contract_version=require_string(
                obj["contract_version"],
                f"{path}.contract_version",
            ),
        )
        if _required_hash(obj["report_hash"], f"{path}.report_hash") != record.report_hash:
            raise SchemaValidationError(f"{path}.report_hash", "attempt replay report hash mismatch")
        return record

    def _content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "ledger_sequence_number": self.ledger_sequence_number,
            "run_id": self.run_id,
            "attempt_index": self.attempt_index,
            "source_attempt_report_hash": self.source_attempt_report_hash,
            "source_ledger_entry_hash": self.source_ledger_entry_hash,
            "verdict": self.verdict,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "generator_invocations": self.generator_invocations,
            "stages": [stage.to_json() for stage in self.stages],
            "recomputed_hashes": self.recomputed_hashes.to_json(),
        }

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value["report_hash"] = self.report_hash
        return value


@dataclass(frozen=True, slots=True)
class Phase8ReplayReport:
    replay_id: str
    bundle_manifest_hash: str
    verdict: ReplayVerdict
    reason_codes: Sequence[Phase8ReasonCode]
    package_chain: Sequence[str]
    attempts: Sequence[Phase8AttemptReplayReport]
    generator_invocations: int
    artifact_hashes: FrozenHashMap
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = PHASE8_REPLAY_REPORT_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.replay_id, "phase8_replay_report.replay_id")
        validate_hash256(self.bundle_manifest_hash, "phase8_replay_report.bundle_manifest_hash")
        if self.verdict not in {"accept", "reject", "indeterminate"}:
            raise SchemaValidationError("phase8_replay_report.verdict", "unsupported verdict")
        reasons = tuple(self.reason_codes)
        package_chain = tuple(self.package_chain)
        attempts = tuple(self.attempts)
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "package_chain", package_chain)
        object.__setattr__(self, "attempts", attempts)
        if len(reasons) != len(set(reasons)):
            raise SchemaValidationError("phase8_replay_report.reason_codes", "duplicate reason")
        if self.verdict == "accept" and reasons:
            raise SchemaValidationError(
                "phase8_replay_report.reason_codes",
                "accepted replay cannot contain failure reasons",
            )
        if self.verdict != "accept" and not reasons:
            raise SchemaValidationError(
                "phase8_replay_report.reason_codes",
                "nonaccepting replay requires a reason",
            )
        if isinstance(self.generator_invocations, bool) or self.generator_invocations != 0:
            raise SchemaValidationError(
                "phase8_replay_report.generator_invocations",
                "independent replay must invoke the generator zero times",
            )
        if len(package_chain) < 2:
            raise SchemaValidationError(
                "phase8_replay_report.package_chain",
                "finite replay requires at least one promoted transition",
            )
        for index, value in enumerate(package_chain):
            validate_hash256(value, f"phase8_replay_report.package_chain[{index}]")
        if self.verdict == "accept" and any(attempt.verdict != "accept" for attempt in attempts):
            raise SchemaValidationError(
                "phase8_replay_report.attempts",
                "accepted replay requires every source attempt to reproduce",
            )
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase8_replay_report.contract_version",
                f"expected {CONTRACT_VERSION}",
            )

    @property
    def accepted(self) -> bool:
        return self.verdict == "accept"

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    @classmethod
    def from_json(cls, value: object, path: str = "phase8_replay_report") -> Phase8ReplayReport:
        fields = {
            "schema_id",
            "contract_version",
            "replay_id",
            "bundle_manifest_hash",
            "verdict",
            "accepted",
            "reason_codes",
            "package_chain",
            "attempts",
            "generator_invocations",
            "artifact_hashes",
            "report_hash",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        package_raw = _require_array(obj["package_chain"], f"{path}.package_chain")
        attempts_raw = _require_array(obj["attempts"], f"{path}.attempts")
        record = cls(
            replay_id=require_string(obj["replay_id"], f"{path}.replay_id"),
            bundle_manifest_hash=_required_hash(
                obj["bundle_manifest_hash"],
                f"{path}.bundle_manifest_hash",
            ),
            verdict=cast(
                ReplayVerdict,
                _literal(obj["verdict"], f"{path}.verdict", {"accept", "reject", "indeterminate"}),
            ),
            reason_codes=_parse_reason_array(obj["reason_codes"], f"{path}.reason_codes"),
            package_chain=tuple(
                _required_hash(item, f"{path}.package_chain[{index}]")
                for index, item in enumerate(package_raw)
            ),
            attempts=tuple(
                Phase8AttemptReplayReport.from_json(item, f"{path}.attempts[{index}]")
                for index, item in enumerate(attempts_raw)
            ),
            generator_invocations=require_structural_integer(
                obj["generator_invocations"],
                f"{path}.generator_invocations",
                minimum=0,
                maximum=0,
            ),
            artifact_hashes=_parse_hash_map(
                obj["artifact_hashes"],
                f"{path}.artifact_hashes",
            ),
            contract_version=require_string(
                obj["contract_version"],
                f"{path}.contract_version",
            ),
        )
        if _required_bool(obj["accepted"], f"{path}.accepted") != record.accepted:
            raise SchemaValidationError(f"{path}.accepted", "accepted flag mismatch")
        if _required_hash(obj["report_hash"], f"{path}.report_hash") != record.report_hash:
            raise SchemaValidationError(f"{path}.report_hash", "replay report hash mismatch")
        return record

    def _content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "replay_id": self.replay_id,
            "bundle_manifest_hash": self.bundle_manifest_hash,
            "verdict": self.verdict,
            "accepted": self.accepted,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "package_chain": list(self.package_chain),
            "attempts": [attempt.to_json() for attempt in self.attempts],
            "generator_invocations": self.generator_invocations,
            "artifact_hashes": self.artifact_hashes.to_json(),
        }

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value["report_hash"] = self.report_hash
        return value


def _require_array(value: object, path: str) -> list[object]:
    if not isinstance(value, list):
        raise SchemaValidationError(path, "expected an array")
    return value


def _literal(value: object, path: str, allowed: set[str]) -> str:
    text = require_string(value, path)
    if text not in allowed:
        raise SchemaValidationError(path, f"unsupported value: {text}")
    return text


def _required_hash(value: object, path: str) -> str:
    text = require_string(value, path)
    validate_hash256(text, path)
    return text


def _optional_hash(value: object, path: str) -> str | None:
    if value is None:
        return None
    return _required_hash(value, path)


def _required_bool(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise SchemaValidationError(path, "expected a Boolean")
    return value


def _parse_hash_map(value: object, path: str) -> FrozenHashMap:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, "expected an object")
    parsed: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise SchemaValidationError(path, "hash-map keys must be strings")
        parsed[require_string(key, f"{path}.key")] = _required_hash(item, f"{path}.{key}")
    return FrozenHashMap.from_mapping(parsed, path)


def _parse_reason_array(value: object, path: str) -> Sequence[Phase8ReasonCode]:
    raw = _require_array(value, path)
    reasons: list[Phase8ReasonCode] = []
    for index, item in enumerate(raw):
        text = require_string(item, f"{path}[{index}]")
        try:
            reasons.append(Phase8ReasonCode(text))
        except ValueError as exc:
            raise SchemaValidationError(
                f"{path}[{index}]",
                f"unknown Phase 8 reason code: {text}",
            ) from exc
    return tuple(reasons)
