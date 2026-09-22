from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v4.phase15.constants import CandidateVariant, cast_candidate_variant


def _hash(value: str, path: str) -> str:
    validate_hash256(value, path)
    return value


def _ordered(values: Sequence[str]) -> tuple[str, ...]:
    result = tuple(values)
    if result != tuple(sorted(set(result), key=lambda item: item.encode("utf-8"))):
        raise SchemaValidationError("phase15.records.sequence", "values must be sorted and unique")
    return result


@dataclass(frozen=True, slots=True)
class Phase15AttemptSummary:
    attempt_index: int
    variant: CandidateVariant
    candidate_semantic_package_hash: str
    candidate_freeze_hash: str
    decoder_manifest_hash: str
    training_result_hash: str
    candidate_phase6_tree_hash: str
    verdict: str
    reason_codes: Sequence[str]
    protected_report_hashes: Sequence[str]
    predecessor_dynamic_report_hashes: Sequence[str]
    candidate_dynamic_report_hashes: Sequence[str]
    information_report_hash: str
    recursive_productivity_report_hash: str
    gate_d_report_hash: str
    gate_e_report_hash: str
    gate_e_validation_hash: str
    outer_verification_hash: str | None
    active_store_package_hash_before: str
    active_store_package_hash_after: str
    phase7_ledger_entry_hash: str
    rejection_evidence_hash: str | None

    schema_id: ClassVar[str] = "runtime.v4.phase15.attempt_summary.v1"

    def __post_init__(self) -> None:
        if isinstance(self.attempt_index, bool) or self.attempt_index < 0:
            raise SchemaValidationError("phase15.attempt.attempt_index", "expected nonnegative integer")
        cast_candidate_variant(self.variant)
        for name in (
            "candidate_semantic_package_hash",
            "candidate_freeze_hash",
            "decoder_manifest_hash",
            "training_result_hash",
            "candidate_phase6_tree_hash",
            "information_report_hash",
            "recursive_productivity_report_hash",
            "gate_d_report_hash",
            "gate_e_report_hash",
            "gate_e_validation_hash",
            "active_store_package_hash_before",
            "active_store_package_hash_after",
            "phase7_ledger_entry_hash",
        ):
            _hash(getattr(self, name), f"phase15.attempt.{name}")
        for name in (
            "protected_report_hashes",
            "predecessor_dynamic_report_hashes",
            "candidate_dynamic_report_hashes",
            "reason_codes",
        ):
            object.__setattr__(self, name, _ordered(getattr(self, name)))
        if self.verdict not in {"accept", "reject"}:
            raise SchemaValidationError("phase15.attempt.verdict", "unsupported verdict")
        if self.verdict == "accept":
            if self.reason_codes or self.outer_verification_hash is None or self.rejection_evidence_hash is not None:
                raise SchemaValidationError("phase15.attempt", "invalid accepted attempt evidence")
            _hash(self.outer_verification_hash, "phase15.attempt.outer_verification_hash")
            if self.active_store_package_hash_before == self.active_store_package_hash_after:
                raise SchemaValidationError("phase15.attempt", "accepted attempt did not advance store")
        else:
            if not self.reason_codes or self.rejection_evidence_hash is None:
                raise SchemaValidationError("phase15.attempt", "rejection evidence is required")
            _hash(self.rejection_evidence_hash, "phase15.attempt.rejection_evidence_hash")
            if self.outer_verification_hash is not None:
                raise SchemaValidationError("phase15.attempt", "rejected attempt cannot contain outer acceptance")
            if self.active_store_package_hash_before != self.active_store_package_hash_after:
                raise SchemaValidationError("phase15.attempt", "rejection changed active package")

    @property
    def summary_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "attempt_index": self.attempt_index,
            "variant": self.variant,
            "candidate_semantic_package_hash": self.candidate_semantic_package_hash,
            "candidate_freeze_hash": self.candidate_freeze_hash,
            "decoder_manifest_hash": self.decoder_manifest_hash,
            "training_result_hash": self.training_result_hash,
            "candidate_phase6_tree_hash": self.candidate_phase6_tree_hash,
            "verdict": self.verdict,
            "reason_codes": list(self.reason_codes),
            "protected_report_hashes": list(self.protected_report_hashes),
            "predecessor_dynamic_report_hashes": list(self.predecessor_dynamic_report_hashes),
            "candidate_dynamic_report_hashes": list(self.candidate_dynamic_report_hashes),
            "information_report_hash": self.information_report_hash,
            "recursive_productivity_report_hash": self.recursive_productivity_report_hash,
            "gate_d_report_hash": self.gate_d_report_hash,
            "gate_e_report_hash": self.gate_e_report_hash,
            "gate_e_validation_hash": self.gate_e_validation_hash,
            "outer_verification_hash": self.outer_verification_hash,
            "active_store_package_hash_before": self.active_store_package_hash_before,
            "active_store_package_hash_after": self.active_store_package_hash_after,
            "phase7_ledger_entry_hash": self.phase7_ledger_entry_hash,
            "rejection_evidence_hash": self.rejection_evidence_hash,
            "manual_repairs": 0,
            "heldout_material_visible_before_freeze": False,
            "host_provided_successful_route": False,
        }

    @classmethod
    def from_json(cls, value: object) -> "Phase15AttemptSummary":
        if not isinstance(value, dict):
            raise SchemaValidationError("phase15.attempt", "expected object")
        sequence_names = (
            "reason_codes",
            "protected_report_hashes",
            "predecessor_dynamic_report_hashes",
            "candidate_dynamic_report_hashes",
        )
        for name in sequence_names:
            if not isinstance(value.get(name), list):
                raise SchemaValidationError(f"phase15.attempt.{name}", "expected array")
        result = cls(
            attempt_index=int(value["attempt_index"]),
            variant=cast_candidate_variant(str(value["variant"])),
            candidate_semantic_package_hash=str(value["candidate_semantic_package_hash"]),
            candidate_freeze_hash=str(value["candidate_freeze_hash"]),
            decoder_manifest_hash=str(value["decoder_manifest_hash"]),
            training_result_hash=str(value["training_result_hash"]),
            candidate_phase6_tree_hash=str(value["candidate_phase6_tree_hash"]),
            verdict=str(value["verdict"]),
            reason_codes=tuple(str(item) for item in value["reason_codes"]),
            protected_report_hashes=tuple(str(item) for item in value["protected_report_hashes"]),
            predecessor_dynamic_report_hashes=tuple(str(item) for item in value["predecessor_dynamic_report_hashes"]),
            candidate_dynamic_report_hashes=tuple(str(item) for item in value["candidate_dynamic_report_hashes"]),
            information_report_hash=str(value["information_report_hash"]),
            recursive_productivity_report_hash=str(value["recursive_productivity_report_hash"]),
            gate_d_report_hash=str(value["gate_d_report_hash"]),
            gate_e_report_hash=str(value["gate_e_report_hash"]),
            gate_e_validation_hash=str(value["gate_e_validation_hash"]),
            outer_verification_hash=(None if value.get("outer_verification_hash") is None else str(value["outer_verification_hash"])),
            active_store_package_hash_before=str(value["active_store_package_hash_before"]),
            active_store_package_hash_after=str(value["active_store_package_hash_after"]),
            phase7_ledger_entry_hash=str(value["phase7_ledger_entry_hash"]),
            rejection_evidence_hash=(None if value.get("rejection_evidence_hash") is None else str(value["rejection_evidence_hash"])),
        )
        return result


__all__ = ["Phase15AttemptSummary"]
