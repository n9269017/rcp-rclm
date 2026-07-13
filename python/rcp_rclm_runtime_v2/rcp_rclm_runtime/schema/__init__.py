from __future__ import annotations

from typing import Mapping, TypeAlias

from rcp_rclm_runtime.canonical.json import JsonValue, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.mathematics.classical import DistributionRecord
from rcp_rclm_runtime.mathematics.diagonal_quantum import (
    DiagonalDensityRecord,
    SelectedChannelRecord,
)
from rcp_rclm_runtime.schema._common import TypedArtifactRecord
from rcp_rclm_runtime.schema.candidate import CandidateRecord
from rcp_rclm_runtime.schema.certificate import RclmCertificatePacketRecord
from rcp_rclm_runtime.schema.package import PackageManifestRecord
from rcp_rclm_runtime.schema.state import (
    ClassicalBinaryStateRecord,
    QuantumStateRecord,
    RclmStateRecord,
    RcpStateRecord,
)
from rcp_rclm_runtime.schema.update import (
    ClassicalBinaryUpdateRecord,
    QuantumUpdateRecord,
    RclmUpdateRecord,
    RcpUpdateRecord,
)
from rcp_rclm_runtime.schema.verdict import CheckVerdictRecord, LeanVerifierReportRecord

RuntimeRecord: TypeAlias = (
    DistributionRecord
    | DiagonalDensityRecord
    | SelectedChannelRecord
    | CandidateRecord
    | RclmStateRecord
    | RclmUpdateRecord
    | RclmCertificatePacketRecord
    | PackageManifestRecord
    | CheckVerdictRecord
    | LeanVerifierReportRecord
)


def parse_runtime_record(value: object, path: str = "runtime_record") -> RuntimeRecord:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, "expected an object")
    schema_id = value.get("schema_id")
    if schema_id == DistributionRecord.schema_id:
        return DistributionRecord.from_json(value, path)
    if schema_id == DiagonalDensityRecord.schema_id:
        return DiagonalDensityRecord.from_json(value, path)
    if schema_id == SelectedChannelRecord.schema_id:
        return SelectedChannelRecord.from_json(value, path)
    if schema_id == CandidateRecord.schema_id:
        return CandidateRecord.from_json(value, path)
    if schema_id == RclmStateRecord.schema_id:
        return RclmStateRecord.from_json(value, path)
    if schema_id == RclmUpdateRecord.schema_id:
        return RclmUpdateRecord.from_json(value, path)
    if schema_id == RclmCertificatePacketRecord.schema_id:
        return RclmCertificatePacketRecord.from_json(value, path)
    if schema_id == PackageManifestRecord.schema_id:
        return PackageManifestRecord.from_json(value, path)
    if schema_id == CheckVerdictRecord.schema_id:
        return CheckVerdictRecord.from_json(value, path)
    if schema_id == LeanVerifierReportRecord.schema_id:
        return LeanVerifierReportRecord.from_json(value, path)
    raise SchemaValidationError(f"{path}.schema_id", f"unknown runtime schema: {schema_id}")


def parse_runtime_record_bytes(data: bytes, require_canonical: bool = True) -> RuntimeRecord:
    value: JsonValue = load_json_strict(data, require_canonical=require_canonical)
    return parse_runtime_record(value)


__all__ = [
    "CandidateRecord",
    "CheckVerdictRecord",
    "ClassicalBinaryStateRecord",
    "ClassicalBinaryUpdateRecord",
    "DiagonalDensityRecord",
    "DistributionRecord",
    "LeanVerifierReportRecord",
    "PackageManifestRecord",
    "QuantumStateRecord",
    "QuantumUpdateRecord",
    "RclmCertificatePacketRecord",
    "RclmStateRecord",
    "RclmUpdateRecord",
    "RcpStateRecord",
    "RcpUpdateRecord",
    "RuntimeRecord",
    "SelectedChannelRecord",
    "TypedArtifactRecord",
    "parse_runtime_record",
    "parse_runtime_record_bytes",
]
