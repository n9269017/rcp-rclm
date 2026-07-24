from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import (
    require_string,
    require_structural_integer,
    strict_object,
)


PHASE13_TRAJECTORY_BUNDLE_VERSION = "rcp-rclm-executable-v3-phase-13-trajectory-bundle-v1"
PHASE13_STRUCTURAL_REPLAY_VERSION = "rcp-rclm-executable-v3-phase-13-structural-replay-v1"
PHASE13_PINNED_REPLAY_VERSION = "rcp-rclm-executable-v3-phase-13-pinned-replay-v1"
PHASE13_EXIT_VERSION = "rcp-rclm-executable-v3-phase-13-exit-v1"


def _safe_relative_path(value: object, path: str) -> str:
    result = require_string(value, path)
    parts = result.split("/")
    if (
        result.startswith("/")
        or "\\" in result
        or not parts
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise SchemaValidationError(path, "expected a safe POSIX relative path")
    return result


def _ordered_paths(values: Sequence[str], path: str) -> Sequence[str]:
    result = tuple(
        _safe_relative_path(item, f"{path}[{index}]")
        for index, item in enumerate(values)
    )
    if len(result) != len(set(result)):
        raise SchemaValidationError(path, "entries must be unique")
    expected = tuple(sorted(result, key=lambda item: item.encode("utf-8")))
    if result != expected:
        raise SchemaValidationError(path, "entries must be sorted by UTF-8 bytes")
    return result


def _ordered_strings(values: Sequence[str], path: str) -> Sequence[str]:
    result = tuple(require_string(item, f"{path}[{index}]") for index, item in enumerate(values))
    if len(result) != len(set(result)):
        raise SchemaValidationError(path, "entries must be unique")
    expected = tuple(sorted(result, key=lambda item: item.encode("utf-8")))
    if result != expected:
        raise SchemaValidationError(path, "entries must be sorted by UTF-8 bytes")
    return result


def _ordered_checks(values: Mapping[str, bool], path: str) -> Mapping[str, bool]:
    result = dict(values)
    if tuple(result) != tuple(sorted(result, key=lambda item: item.encode("utf-8"))):
        raise SchemaValidationError(path, "check names must be UTF-8 sorted")
    if not result:
        raise SchemaValidationError(path, "at least one check is required")
    for name, value in result.items():
        require_string(name, f"{path}.name")
        if not isinstance(value, bool):
            raise SchemaValidationError(f"{path}.{name}", "expected Boolean")
    return result


def _parse_checks(value: object, path: str) -> Mapping[str, bool]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, "expected an object")
    result: dict[str, bool] = {}
    for key, item in value.items():
        name = require_string(key, f"{path}.key")
        if not isinstance(item, bool):
            raise SchemaValidationError(f"{path}.{name}", "expected Boolean")
        result[name] = item
    return _ordered_checks(result, path)


@dataclass(frozen=True, slots=True)
class Phase13BundleFileRecord:
    path: str
    size: int
    sha256: str

    schema_id: ClassVar[str] = "runtime.v3.phase13.bundle_file.v1"

    def __post_init__(self) -> None:
        _safe_relative_path(self.path, "phase13.bundle_file.path")
        require_structural_integer(self.size, "phase13.bundle_file.size", minimum=0)
        validate_hash256(self.sha256, "phase13.bundle_file.sha256")

    @classmethod
    def from_json(cls, value: object) -> Phase13BundleFileRecord:
        obj = strict_object(
            value,
            "phase13.bundle_file",
            {"schema_id", "path", "size", "sha256"},
        )
        if obj["schema_id"] != cls.schema_id:
            raise SchemaValidationError("phase13.bundle_file.schema_id", f"expected {cls.schema_id}")
        return cls(
            path=_safe_relative_path(obj["path"], "phase13.bundle_file.path"),
            size=require_structural_integer(obj["size"], "phase13.bundle_file.size", minimum=0),
            sha256=require_string(obj["sha256"], "phase13.bundle_file.sha256"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "path": self.path,
            "size": self.size,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class Phase13TrajectoryBundleManifest:
    source_head: str
    closure_report_hash: str
    closure_bytes_sha256: str
    trajectory_content_hash: str
    files: Sequence[Phase13BundleFileRecord]
    empty_directories: Sequence[str]
    required_roots: Sequence[str]
    contract_version: str = PHASE13_TRAJECTORY_BUNDLE_VERSION

    schema_id: ClassVar[str] = "runtime.v3.phase13.trajectory_bundle_manifest.v1"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.source_head, str)
            or len(self.source_head) != 40
            or any(character not in "0123456789abcdef" for character in self.source_head)
        ):
            raise SchemaValidationError("phase13.bundle.source_head", "expected a lowercase 40-character Git SHA")
        validate_hash256(self.closure_report_hash, "phase13.bundle.closure_report_hash")
        validate_hash256(self.closure_bytes_sha256, "phase13.bundle.closure_bytes_sha256")
        validate_hash256(self.trajectory_content_hash, "phase13.bundle.trajectory_content_hash")
        if self.contract_version != PHASE13_TRAJECTORY_BUNDLE_VERSION:
            raise SchemaValidationError(
                "phase13.bundle.contract_version",
                f"expected {PHASE13_TRAJECTORY_BUNDLE_VERSION}",
            )
        files = tuple(self.files)
        paths = tuple(item.path for item in files)
        if paths != tuple(sorted(paths, key=lambda item: item.encode("utf-8"))):
            raise SchemaValidationError("phase13.bundle.files", "files must be path sorted")
        if len(paths) != len(set(paths)):
            raise SchemaValidationError("phase13.bundle.files", "duplicate file path")
        empty_directories = _ordered_paths(
            self.empty_directories, "phase13.bundle.empty_directories"
        )
        file_paths = set(paths)
        for relative in empty_directories:
            if relative in file_paths or any(path.startswith(f"{relative}/") for path in paths):
                raise SchemaValidationError(
                    "phase13.bundle.empty_directories",
                    "declared empty directory contains a manifested file",
                )
        required = _ordered_paths(self.required_roots, "phase13.bundle.required_roots")
        expected_content_hash = canonical_json_hash(
            {
                "empty_directories": list(empty_directories),
                "files": [item.to_json() for item in files],
            }
        )
        if self.trajectory_content_hash != expected_content_hash:
            raise SchemaValidationError("phase13.bundle.trajectory_content_hash", "file-record hash mismatch")
        object.__setattr__(self, "files", files)
        object.__setattr__(self, "empty_directories", empty_directories)
        object.__setattr__(self, "required_roots", required)

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def total_bytes(self) -> int:
        return sum(item.size for item in self.files)

    @property
    def manifest_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "source_head": self.source_head,
            "closure_report_hash": self.closure_report_hash,
            "closure_bytes_sha256": self.closure_bytes_sha256,
            "trajectory_content_hash": self.trajectory_content_hash,
            "file_count": self.file_count,
            "empty_directory_count": len(self.empty_directories),
            "total_bytes": self.total_bytes,
            "empty_directories": list(self.empty_directories),
            "required_roots": list(self.required_roots),
            "files": [item.to_json() for item in self.files],
        }

    def to_json(self) -> dict[str, object]:
        result = self.content_json()
        result["manifest_hash"] = self.manifest_hash
        return result

    @classmethod
    def from_json(cls, value: object) -> Phase13TrajectoryBundleManifest:
        obj = strict_object(
            value,
            "phase13.bundle",
            {
                "schema_id",
                "contract_version",
                "source_head",
                "closure_report_hash",
                "closure_bytes_sha256",
                "trajectory_content_hash",
                "file_count",
                "empty_directory_count",
                "total_bytes",
                "empty_directories",
                "required_roots",
                "files",
                "manifest_hash",
            },
        )
        if obj["schema_id"] != cls.schema_id:
            raise SchemaValidationError("phase13.bundle.schema_id", f"expected {cls.schema_id}")
        raw_files = obj["files"]
        raw_empty_directories = obj["empty_directories"]
        raw_roots = obj["required_roots"]
        if not isinstance(raw_files, Sequence) or isinstance(raw_files, (str, bytes, bytearray)):
            raise SchemaValidationError("phase13.bundle.files", "expected an array")
        if not isinstance(raw_empty_directories, Sequence) or isinstance(
            raw_empty_directories, (str, bytes, bytearray)
        ):
            raise SchemaValidationError("phase13.bundle.empty_directories", "expected an array")
        if not isinstance(raw_roots, Sequence) or isinstance(raw_roots, (str, bytes, bytearray)):
            raise SchemaValidationError("phase13.bundle.required_roots", "expected an array")
        result = cls(
            source_head=require_string(obj["source_head"], "phase13.bundle.source_head"),
            closure_report_hash=require_string(
                obj["closure_report_hash"], "phase13.bundle.closure_report_hash"
            ),
            closure_bytes_sha256=require_string(
                obj["closure_bytes_sha256"], "phase13.bundle.closure_bytes_sha256"
            ),
            trajectory_content_hash=require_string(
                obj["trajectory_content_hash"], "phase13.bundle.trajectory_content_hash"
            ),
            files=tuple(Phase13BundleFileRecord.from_json(item) for item in raw_files),
            empty_directories=tuple(
                _safe_relative_path(item, f"phase13.bundle.empty_directories[{index}]")
                for index, item in enumerate(raw_empty_directories)
            ),
            required_roots=tuple(
                _safe_relative_path(item, f"phase13.bundle.required_roots[{index}]")
                for index, item in enumerate(raw_roots)
            ),
            contract_version=require_string(obj["contract_version"], "phase13.bundle.contract_version"),
        )
        if require_structural_integer(obj["file_count"], "phase13.bundle.file_count", minimum=0) != result.file_count:
            raise SchemaValidationError("phase13.bundle.file_count", "count mismatch")
        if require_structural_integer(
            obj["empty_directory_count"],
            "phase13.bundle.empty_directory_count",
            minimum=0,
        ) != len(result.empty_directories):
            raise SchemaValidationError("phase13.bundle.empty_directory_count", "count mismatch")
        if require_structural_integer(obj["total_bytes"], "phase13.bundle.total_bytes", minimum=0) != result.total_bytes:
            raise SchemaValidationError("phase13.bundle.total_bytes", "byte total mismatch")
        if require_string(obj["manifest_hash"], "phase13.bundle.manifest_hash") != result.manifest_hash:
            raise SchemaValidationError("phase13.bundle.manifest_hash", "content hash mismatch")
        return result


@dataclass(frozen=True, slots=True)
class Phase13CheckRecord:
    record_id: str
    checks: Mapping[str, bool]
    evidence_hashes: Mapping[str, str]

    schema_id: ClassVar[str] = "runtime.v3.phase13.check_record.v1"

    def __post_init__(self) -> None:
        require_string(self.record_id, "phase13.check.record_id")
        checks = _ordered_checks(self.checks, "phase13.check.checks")
        evidence = dict(self.evidence_hashes)
        if tuple(evidence) != tuple(sorted(evidence, key=lambda item: item.encode("utf-8"))):
            raise SchemaValidationError("phase13.check.evidence_hashes", "keys must be UTF-8 sorted")
        for name, digest in evidence.items():
            require_string(name, "phase13.check.evidence_hashes.name")
            validate_hash256(digest, f"phase13.check.evidence_hashes.{name}")
        object.__setattr__(self, "checks", checks)
        object.__setattr__(self, "evidence_hashes", evidence)

    @property
    def accepted(self) -> bool:
        return all(self.checks.values())

    @property
    def record_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "record_id": self.record_id,
            "checks": dict(self.checks),
            "evidence_hashes": dict(self.evidence_hashes),
            "accepted": self.accepted,
        }

    @classmethod
    def from_json(cls, value: object) -> Phase13CheckRecord:
        obj = strict_object(
            value,
            "phase13.check",
            {"schema_id", "record_id", "checks", "evidence_hashes", "accepted"},
        )
        if obj["schema_id"] != cls.schema_id:
            raise SchemaValidationError("phase13.check.schema_id", f"expected {cls.schema_id}")
        raw_evidence = obj["evidence_hashes"]
        if not isinstance(raw_evidence, Mapping):
            raise SchemaValidationError("phase13.check.evidence_hashes", "expected an object")
        result = cls(
            record_id=require_string(obj["record_id"], "phase13.check.record_id"),
            checks=_parse_checks(obj["checks"], "phase13.check.checks"),
            evidence_hashes={
                require_string(key, "phase13.check.evidence_hashes.key"): require_string(
                    digest, f"phase13.check.evidence_hashes.{key}"
                )
                for key, digest in raw_evidence.items()
            },
        )
        if obj["accepted"] is not result.accepted:
            raise SchemaValidationError("phase13.check.accepted", "derived acceptance mismatch")
        return result


@dataclass(frozen=True, slots=True)
class Phase13StructuralReplayReport:
    source_reference_hash: str
    package_records: Sequence[Phase13CheckRecord]
    promotion_records: Sequence[Phase13CheckRecord]
    rejection_records: Sequence[Phase13CheckRecord]
    information_records: Sequence[Phase13CheckRecord]
    lifecycle_records: Sequence[Phase13CheckRecord]
    invocation_checks: Mapping[str, bool]
    contract_version: str = PHASE13_STRUCTURAL_REPLAY_VERSION

    schema_id: ClassVar[str] = "runtime.v3.phase13.structural_replay_report.v1"

    def __post_init__(self) -> None:
        validate_hash256(self.source_reference_hash, "phase13.structural.source_reference_hash")
        if self.contract_version != PHASE13_STRUCTURAL_REPLAY_VERSION:
            raise SchemaValidationError(
                "phase13.structural.contract_version",
                f"expected {PHASE13_STRUCTURAL_REPLAY_VERSION}",
            )
        for name in (
            "package_records",
            "promotion_records",
            "rejection_records",
            "information_records",
            "lifecycle_records",
        ):
            records = tuple(getattr(self, name))
            ids = tuple(item.record_id for item in records)
            if ids != tuple(sorted(ids, key=lambda item: item.encode("utf-8"))):
                raise SchemaValidationError(f"phase13.structural.{name}", "records must be ID sorted")
            if len(ids) != len(set(ids)):
                raise SchemaValidationError(f"phase13.structural.{name}", "duplicate record ID")
            object.__setattr__(self, name, records)
        object.__setattr__(
            self,
            "invocation_checks",
            _ordered_checks(self.invocation_checks, "phase13.structural.invocation_checks"),
        )

    @property
    def accepted(self) -> bool:
        groups = (
            self.package_records,
            self.promotion_records,
            self.rejection_records,
            self.information_records,
            self.lifecycle_records,
        )
        return all(record.accepted for group in groups for record in group) and all(
            self.invocation_checks.values()
        )

    @property
    def phase13b_slice_closed(self) -> bool:
        return self.accepted

    @property
    def phase13_exit_closed(self) -> bool:
        return False

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "source_reference_hash": self.source_reference_hash,
            "package_records": [item.to_json() for item in self.package_records],
            "promotion_records": [item.to_json() for item in self.promotion_records],
            "rejection_records": [item.to_json() for item in self.rejection_records],
            "information_records": [item.to_json() for item in self.information_records],
            "lifecycle_records": [item.to_json() for item in self.lifecycle_records],
            "invocation_checks": dict(self.invocation_checks),
            "accepted": self.accepted,
            "phase13b_slice_closed": self.phase13b_slice_closed,
            "phase13_exit_closed": self.phase13_exit_closed,
        }



def _validate_source_head(value: str, path: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise SchemaValidationError(path, "expected a lowercase 40-character Git SHA")
    return value


def _ordered_records(
    values: Sequence[Phase13CheckRecord],
    path: str,
) -> Sequence[Phase13CheckRecord]:
    result = tuple(values)
    ids = tuple(item.record_id for item in result)
    if ids != tuple(sorted(ids, key=lambda item: item.encode("utf-8"))):
        raise SchemaValidationError(path, "records must be ID sorted")
    if len(ids) != len(set(ids)):
        raise SchemaValidationError(path, "duplicate record ID")
    return result


def _ordered_hash_mapping(values: Mapping[str, str], path: str) -> Mapping[str, str]:
    result = dict(values)
    if tuple(result) != tuple(sorted(result, key=lambda item: item.encode("utf-8"))):
        raise SchemaValidationError(path, "keys must be UTF-8 sorted")
    for name, digest in result.items():
        require_string(name, f"{path}.name")
        validate_hash256(digest, f"{path}.{name}")
    return result


@dataclass(frozen=True, slots=True)
class Phase13PinnedReplayReport:
    source_head: str
    bundle_manifest_hash: str
    phase13a_report_hash: str
    structural_report_hash: str
    store_records: Sequence[Phase13CheckRecord]
    task_records: Sequence[Phase13CheckRecord]
    hardened_records: Sequence[Phase13CheckRecord]
    boundary_checks: Mapping[str, bool]
    contract_version: str = PHASE13_PINNED_REPLAY_VERSION

    schema_id: ClassVar[str] = "runtime.v3.phase13.pinned_replay_report.v1"

    def __post_init__(self) -> None:
        _validate_source_head(self.source_head, "phase13.pinned.source_head")
        for name in (
            "bundle_manifest_hash",
            "phase13a_report_hash",
            "structural_report_hash",
        ):
            validate_hash256(getattr(self, name), f"phase13.pinned.{name}")
        if self.contract_version != PHASE13_PINNED_REPLAY_VERSION:
            raise SchemaValidationError(
                "phase13.pinned.contract_version",
                f"expected {PHASE13_PINNED_REPLAY_VERSION}",
            )
        for name in ("store_records", "task_records", "hardened_records"):
            object.__setattr__(
                self,
                name,
                _ordered_records(getattr(self, name), f"phase13.pinned.{name}"),
            )
        object.__setattr__(
            self,
            "boundary_checks",
            _ordered_checks(self.boundary_checks, "phase13.pinned.boundary_checks"),
        )

    @property
    def accepted(self) -> bool:
        return (
            all(self.boundary_checks.values())
            and all(item.accepted for item in self.store_records)
            and all(item.accepted for item in self.task_records)
            and all(item.accepted for item in self.hardened_records)
        )

    @property
    def phase13c_slice_closed(self) -> bool:
        return self.accepted

    @property
    def phase13_exit_closed(self) -> bool:
        return False

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "source_head": self.source_head,
            "bundle_manifest_hash": self.bundle_manifest_hash,
            "phase13a_report_hash": self.phase13a_report_hash,
            "structural_report_hash": self.structural_report_hash,
            "store_records": [item.to_json() for item in self.store_records],
            "task_records": [item.to_json() for item in self.task_records],
            "hardened_records": [item.to_json() for item in self.hardened_records],
            "boundary_checks": dict(self.boundary_checks),
            "accepted": self.accepted,
            "phase13c_slice_closed": self.phase13c_slice_closed,
            "phase13_exit_closed": self.phase13_exit_closed,
        }


@dataclass(frozen=True, slots=True)
class Phase13ExitReport:
    source_head: str
    bundle_manifest_hash: str
    phase13a_report_hash: str
    structural_report_hash: str
    pinned_report_hash: str
    pinned_entry_hashes: Mapping[str, str]
    portable_entry_hashes: Mapping[str, str]
    closure_checks: Mapping[str, bool]
    contract_version: str = PHASE13_EXIT_VERSION

    schema_id: ClassVar[str] = "runtime.v3.phase13.exit_report.v1"

    def __post_init__(self) -> None:
        _validate_source_head(self.source_head, "phase13.exit.source_head")
        for name in (
            "bundle_manifest_hash",
            "phase13a_report_hash",
            "structural_report_hash",
            "pinned_report_hash",
        ):
            validate_hash256(getattr(self, name), f"phase13.exit.{name}")
        if self.contract_version != PHASE13_EXIT_VERSION:
            raise SchemaValidationError(
                "phase13.exit.contract_version",
                f"expected {PHASE13_EXIT_VERSION}",
            )
        pinned_entries = _ordered_hash_mapping(
            self.pinned_entry_hashes,
            "phase13.exit.pinned_entry_hashes",
        )
        if set(pinned_entries) != {"macos", "ubuntu", "windows"}:
            raise SchemaValidationError(
                "phase13.exit.pinned_entry_hashes",
                "expected exactly macos, ubuntu, and windows",
            )
        object.__setattr__(self, "pinned_entry_hashes", pinned_entries)
        portable = _ordered_hash_mapping(
            self.portable_entry_hashes,
            "phase13.exit.portable_entry_hashes",
        )
        if set(portable) != {"macos", "ubuntu", "windows"}:
            raise SchemaValidationError(
                "phase13.exit.portable_entry_hashes",
                "expected exactly macos, ubuntu, and windows",
            )
        object.__setattr__(self, "portable_entry_hashes", portable)
        object.__setattr__(
            self,
            "closure_checks",
            _ordered_checks(self.closure_checks, "phase13.exit.closure_checks"),
        )

    @property
    def accepted(self) -> bool:
        return all(self.closure_checks.values())

    @property
    def phase13_exit_closed(self) -> bool:
        return self.accepted

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "source_head": self.source_head,
            "bundle_manifest_hash": self.bundle_manifest_hash,
            "phase13a_report_hash": self.phase13a_report_hash,
            "structural_report_hash": self.structural_report_hash,
            "pinned_report_hash": self.pinned_report_hash,
            "pinned_entry_hashes": dict(self.pinned_entry_hashes),
            "portable_entry_hashes": dict(self.portable_entry_hashes),
            "closure_checks": dict(self.closure_checks),
            "accepted": self.accepted,
            "phase13_exit_closed": self.phase13_exit_closed,
            "next_phase": 14,
        }


__all__ = [
    "PHASE13_EXIT_VERSION",
    "PHASE13_PINNED_REPLAY_VERSION",
    "PHASE13_STRUCTURAL_REPLAY_VERSION",
    "PHASE13_TRAJECTORY_BUNDLE_VERSION",
    "Phase13BundleFileRecord",
    "Phase13CheckRecord",
    "Phase13ExitReport",
    "Phase13PinnedReplayReport",
    "Phase13StructuralReplayReport",
    "Phase13TrajectoryBundleManifest",
]
