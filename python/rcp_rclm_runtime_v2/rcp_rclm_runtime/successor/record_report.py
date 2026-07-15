from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime._version import CONTRACT_VERSION
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, require_string, strict_object
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.successor._record_common import PHASE6_PACKAGE_REPORT_SCHEMA_ID, SuccessorVerdict, Phase6ReasonCode, frozen_hash_map, literal, require_exact_set, required_bool, required_hash
from rcp_rclm_runtime.successor.record_manifest import Phase6CandidateManifestRecord
from rcp_rclm_runtime.successor.record_realization import Phase6RealizationRecord
from rcp_rclm_runtime.successor.record_selection import Phase6SelectionRecord

@dataclass(frozen=True, slots=True)
class Phase6PackageReport:
    transition_id: str
    verdict: SuccessorVerdict
    reason_codes: Sequence[Phase6ReasonCode]
    predecessor_manifest_hash: str
    selection: Phase6SelectionRecord | None
    realization: Phase6RealizationRecord | None
    candidate_manifest: Phase6CandidateManifestRecord | None
    evidence_hashes: FrozenHashMap
    promotion_licensed: bool = False
    contract_version: str = CONTRACT_VERSION

    schema_id: ClassVar[str] = PHASE6_PACKAGE_REPORT_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.transition_id, "phase6_package_report.transition_id")
        require_exact_set(
            self.verdict,
            {"success", "reject", "indeterminate"},
            "phase6_package_report.verdict",
        )
        reasons = tuple(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)
        if len(reasons) != len(set(reasons)):
            raise SchemaValidationError(
                "phase6_package_report.reason_codes",
                "reason codes must be unique",
            )
        if self.verdict == "success" and reasons:
            raise SchemaValidationError(
                "phase6_package_report.reason_codes",
                "successful report cannot contain reasons",
            )
        if self.verdict != "success" and not reasons:
            raise SchemaValidationError(
                "phase6_package_report.reason_codes",
                "non-success report requires a reason code",
            )
        validate_hash256(
            self.predecessor_manifest_hash,
            "phase6_package_report.predecessor_manifest_hash",
        )
        if self.verdict == "success":
            if self.selection is None or self.realization is None or self.candidate_manifest is None:
                raise SchemaValidationError(
                    "phase6_package_report",
                    "success requires selection, realization, and candidate manifest",
                )
            if self.selection.selection_hash != self.realization.selection_hash:
                raise SchemaValidationError(
                    "phase6_package_report.realization.selection_hash",
                    "selection binding mismatch",
                )
            if (
                self.candidate_manifest.payload_tree_hash
                != self.realization.candidate_payload_tree_hash
            ):
                raise SchemaValidationError(
                    "phase6_package_report.candidate_manifest.payload_tree_hash",
                    "candidate manifest and realization payload hashes differ",
                )
            if self.candidate_manifest.parent_manifest_hash != self.predecessor_manifest_hash:
                raise SchemaValidationError(
                    "phase6_package_report.candidate_manifest.parent_manifest_hash",
                    "candidate parent manifest mismatch",
                )
        if not isinstance(self.promotion_licensed, bool) or self.promotion_licensed:
            raise SchemaValidationError(
                "phase6_package_report.promotion_licensed",
                "Phase 6 never licenses promotion",
            )
        if self.contract_version != CONTRACT_VERSION:
            raise SchemaValidationError(
                "phase6_package_report.contract_version",
                f"expected {CONTRACT_VERSION}",
            )

    @property
    def built(self) -> bool:
        return self.verdict == "success"

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase6_package_report",
    ) -> Phase6PackageReport:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "contract_version",
                "transition_id",
                "verdict",
                "built",
                "reason_codes",
                "predecessor_manifest_hash",
                "selection",
                "realization",
                "candidate_manifest",
                "evidence_hashes",
                "promotion_licensed",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        reasons_raw = obj["reason_codes"]
        if not isinstance(reasons_raw, list):
            raise SchemaValidationError(f"{path}.reason_codes", "expected an array")
        reasons: list[Phase6ReasonCode] = []
        for index, item in enumerate(reasons_raw):
            text = require_string(item, f"{path}.reason_codes[{index}]")
            try:
                reasons.append(Phase6ReasonCode(text))
            except ValueError as exc:
                raise SchemaValidationError(
                    f"{path}.reason_codes[{index}]",
                    f"unknown Phase 6 reason code: {text}",
                ) from exc
        record = cls(
            transition_id=require_string(
                obj["transition_id"], f"{path}.transition_id"
            ),
            verdict=literal(
                obj["verdict"],
                f"{path}.verdict",
                {"success", "reject", "indeterminate"},
            ),
            reason_codes=tuple(reasons),
            predecessor_manifest_hash=required_hash(
                obj["predecessor_manifest_hash"],
                f"{path}.predecessor_manifest_hash",
            ),
            selection=(
                None
                if obj["selection"] is None
                else Phase6SelectionRecord.from_json(
                    obj["selection"], f"{path}.selection"
                )
            ),
            realization=(
                None
                if obj["realization"] is None
                else Phase6RealizationRecord.from_json(
                    obj["realization"], f"{path}.realization"
                )
            ),
            candidate_manifest=(
                None
                if obj["candidate_manifest"] is None
                else Phase6CandidateManifestRecord.from_json(
                    obj["candidate_manifest"],
                    f"{path}.candidate_manifest",
                )
            ),
            evidence_hashes=frozen_hash_map(
                obj["evidence_hashes"], f"{path}.evidence_hashes"
            ),
            promotion_licensed=required_bool(
                obj["promotion_licensed"], f"{path}.promotion_licensed"
            ),
            contract_version=require_string(
                obj["contract_version"], f"{path}.contract_version"
            ),
        )
        declared_built = required_bool(obj["built"], f"{path}.built")
        if declared_built != record.built:
            raise SchemaValidationError(
                f"{path}.built",
                "built flag does not match verdict",
            )
        return record

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "transition_id": self.transition_id,
            "verdict": self.verdict,
            "built": self.built,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "predecessor_manifest_hash": self.predecessor_manifest_hash,
            "selection": None if self.selection is None else self.selection.to_json(),
            "realization": (
                None if self.realization is None else self.realization.to_json()
            ),
            "candidate_manifest": (
                None
                if self.candidate_manifest is None
                else self.candidate_manifest.to_json()
            ),
            "evidence_hashes": self.evidence_hashes.to_json(),
            "promotion_licensed": self.promotion_licensed,
        }
