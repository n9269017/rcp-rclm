from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v3.phase10.constants import PACKAGE_REPORT_SCHEMA_ID

PackageReasonCode = Literal[
    "PHASE10_PACKAGE_ACCEPT",
    "PHASE10_PACKAGE_PARSE_FAILED",
    "PHASE10_ARCHITECTURE_BINDING_FAILED",
    "PHASE10_TOKENIZER_BINDING_FAILED",
    "PHASE10_TENSOR_BINDING_FAILED",
    "PHASE10_ADAPTER_BINDING_FAILED",
    "PHASE10_SUPPORT_BINDING_FAILED",
    "PHASE10_MODEL_IDENTITY_FAILED",
    "PHASE10_PAYLOAD_TREE_FAILED",
    "PHASE10_PACKAGE_FILE_SET_FAILED",
]


@dataclass(frozen=True, slots=True)
class Phase10PackageReport:
    accepted: bool
    reason_codes: Sequence[PackageReasonCode]
    package_id: str
    package_hash: str
    model_identity_hash: str
    architecture_hash: str
    weights_tree_hash: str
    adapter_manifest_hash: str
    payload_tree_hash: str
    parameter_count: int
    file_count: int
    total_size_bytes: int
    semantic_report_hash: str

    schema_id: ClassVar[str] = PACKAGE_REPORT_SCHEMA_ID

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "reason_codes": list(self.reason_codes),
            "package_id": self.package_id,
            "package_hash": self.package_hash,
            "model_identity_hash": self.model_identity_hash,
            "architecture_hash": self.architecture_hash,
            "weights_tree_hash": self.weights_tree_hash,
            "adapter_manifest_hash": self.adapter_manifest_hash,
            "payload_tree_hash": self.payload_tree_hash,
            "parameter_count": self.parameter_count,
            "file_count": self.file_count,
            "total_size_bytes": self.total_size_bytes,
        }

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["semantic_report_hash"] = self.semantic_report_hash
        return value


def package_report(
    *,
    accepted: bool,
    reasons: Sequence[PackageReasonCode],
    package_id: str,
    package_hash: str,
    model_identity_hash: str,
    architecture_hash: str,
    weights_tree_hash: str,
    adapter_manifest_hash: str,
    payload_tree_hash: str,
    parameter_count: int,
    file_count: int,
    total_size_bytes: int,
) -> Phase10PackageReport:
    report_reasons: Sequence[PackageReasonCode] = (
        ("PHASE10_PACKAGE_ACCEPT",) if accepted else tuple(reasons)
    )
    content = {
        "schema_id": Phase10PackageReport.schema_id,
        "accepted": accepted,
        "reason_codes": list(report_reasons),
        "package_id": package_id,
        "package_hash": package_hash,
        "model_identity_hash": model_identity_hash,
        "architecture_hash": architecture_hash,
        "weights_tree_hash": weights_tree_hash,
        "adapter_manifest_hash": adapter_manifest_hash,
        "payload_tree_hash": payload_tree_hash,
        "parameter_count": parameter_count,
        "file_count": file_count,
        "total_size_bytes": total_size_bytes,
    }
    return Phase10PackageReport(
        accepted=accepted,
        reason_codes=report_reasons,
        package_id=package_id,
        package_hash=package_hash,
        model_identity_hash=model_identity_hash,
        architecture_hash=architecture_hash,
        weights_tree_hash=weights_tree_hash,
        adapter_manifest_hash=adapter_manifest_hash,
        payload_tree_hash=payload_tree_hash,
        parameter_count=parameter_count,
        file_count=file_count,
        total_size_bytes=total_size_bytes,
        semantic_report_hash=canonical_json_hash(content),
    )


def empty_package_report(reason: PackageReasonCode) -> Phase10PackageReport:
    zero = "0" * 64
    return package_report(
        accepted=False,
        reasons=(reason,),
        package_id="unparsed",
        package_hash=zero,
        model_identity_hash=zero,
        architecture_hash=zero,
        weights_tree_hash=zero,
        adapter_manifest_hash=zero,
        payload_tree_hash=zero,
        parameter_count=0,
        file_count=0,
        total_size_bytes=0,
    )


__all__ = [
    "PackageReasonCode",
    "Phase10PackageReport",
    "empty_package_report",
    "package_report",
]
