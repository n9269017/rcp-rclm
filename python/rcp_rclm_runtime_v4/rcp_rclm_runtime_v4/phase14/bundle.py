from __future__ import annotations

import os
import shutil
import stat
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.canonical.paths import validate_semantic_path
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase14.trajectory import Phase14TrajectoryReport


@dataclass(frozen=True, slots=True)
class Phase14BundleFile:
    path: str
    size_bytes: int
    sha256: str

    schema_id: ClassVar[str] = "runtime.v4.phase14.bundle_file.v1"

    def __post_init__(self) -> None:
        validate_semantic_path(self.path)
        if isinstance(self.size_bytes, bool) or self.size_bytes < 0:
            raise SchemaValidationError(
                "phase14.bundle_file.size_bytes",
                "expected nonnegative integer",
            )
        if len(self.sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.sha256
        ):
            raise SchemaValidationError(
                "phase14.bundle_file.sha256",
                "expected lowercase SHA-256",
            )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }

    @classmethod
    def from_json(cls, value: object) -> Phase14BundleFile:
        if not isinstance(value, dict):
            raise SchemaValidationError("phase14.bundle_file", "expected object")
        return cls(
            path=str(value["path"]),
            size_bytes=int(value["size_bytes"]),
            sha256=str(value["sha256"]),
        )


@dataclass(frozen=True, slots=True)
class Phase14BundleManifest:
    source_head: str
    source_tree: str
    trajectory_report_hash: str
    files: Sequence[Phase14BundleFile]
    empty_directories: Sequence[str]

    schema_id: ClassVar[str] = "runtime.v4.phase14.bundle_manifest.v1"

    def __post_init__(self) -> None:
        for name in ("source_head", "source_tree", "trajectory_report_hash"):
            value = getattr(self, name)
            if len(value) not in {40, 64} or any(
                character not in "0123456789abcdef" for character in value
            ):
                raise SchemaValidationError(
                    f"phase14.bundle.{name}",
                    "expected lowercase hexadecimal identity",
                )
        records = tuple(self.files)
        paths = tuple(record.path for record in records)
        if paths != tuple(sorted(paths, key=lambda item: item.encode("utf-8"))):
            raise SchemaValidationError(
                "phase14.bundle.files",
                "file records must be sorted by path",
            )
        if len(set(paths)) != len(paths):
            raise SchemaValidationError(
                "phase14.bundle.files",
                "duplicate file path",
            )
        empty = tuple(self.empty_directories)
        for path in empty:
            validate_semantic_path(path)
        if empty != tuple(sorted(empty, key=lambda item: item.encode("utf-8"))):
            raise SchemaValidationError(
                "phase14.bundle.empty_directories",
                "empty directories must be sorted",
            )
        if len(set(empty)) != len(empty):
            raise SchemaValidationError(
                "phase14.bundle.empty_directories",
                "duplicate empty directory",
            )
        object.__setattr__(self, "files", records)
        object.__setattr__(self, "empty_directories", empty)

    @property
    def manifest_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "source_head": self.source_head,
            "source_tree": self.source_tree,
            "trajectory_report_hash": self.trajectory_report_hash,
            "files": [record.to_json() for record in self.files],
            "empty_directories": list(self.empty_directories),
        }

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["manifest_hash"] = self.manifest_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> Phase14BundleManifest:
        if not isinstance(value, dict):
            raise SchemaValidationError("phase14.bundle", "expected object")
        raw_files = value.get("files")
        raw_empty = value.get("empty_directories")
        if not isinstance(raw_files, list) or not isinstance(raw_empty, list):
            raise SchemaValidationError(
                "phase14.bundle",
                "expected file and empty-directory arrays",
            )
        result = cls(
            source_head=str(value["source_head"]),
            source_tree=str(value["source_tree"]),
            trajectory_report_hash=str(value["trajectory_report_hash"]),
            files=tuple(Phase14BundleFile.from_json(item) for item in raw_files),
            empty_directories=tuple(str(item) for item in raw_empty),
        )
        if value.get("manifest_hash") != result.manifest_hash:
            raise SchemaValidationError(
                "phase14.bundle.manifest_hash",
                "content hash mismatch",
            )
        return result


def _regular_files(root: Path) -> tuple[Path, ...]:
    result: list[Path] = []
    for current_root, directory_names, file_names in os.walk(
        root,
        followlinks=False,
    ):
        current = Path(current_root)
        for name in directory_names:
            if (current / name).is_symlink():
                raise SchemaValidationError(
                    "phase14.bundle",
                    "symlink directories are forbidden",
                )
        for name in file_names:
            path = current / name
            status = path.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
                raise SchemaValidationError(
                    "phase14.bundle",
                    "only regular files are permitted",
                )
            result.append(path)
    return tuple(sorted(result, key=lambda item: item.relative_to(root).as_posix().encode("utf-8")))


def _empty_directories(root: Path) -> tuple[str, ...]:
    result: list[str] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().encode("utf-8")):
        if path.is_symlink():
            raise SchemaValidationError("phase14.bundle", "symlinks are forbidden")
        if path.is_dir() and not any(path.iterdir()):
            result.append(path.relative_to(root).as_posix())
    return tuple(result)


def build_phase14_bundle(
    *,
    campaign_root: Path,
    bundle_root: Path,
) -> Phase14BundleManifest:
    source = campaign_root.resolve(strict=True)
    output = bundle_root.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"Phase 14 bundle already exists: {output}")
    trajectory_value = load_json_strict(
        (source / "phase14_trajectory.json").read_bytes(),
        require_canonical=True,
    )
    trajectory = Phase14TrajectoryReport.from_json(trajectory_value)
    output.parent.mkdir(parents=True, exist_ok=True)
    campaign_output = output / "campaign"
    shutil.copytree(source, campaign_output, symlinks=False)
    records = tuple(
        Phase14BundleFile(
            path=path.relative_to(output).as_posix(),
            size_bytes=path.stat().st_size,
            sha256=sha256_hex(path.read_bytes()),
        )
        for path in _regular_files(output)
    )
    manifest = Phase14BundleManifest(
        source_head=trajectory.source_head,
        source_tree=trajectory.source_tree,
        trajectory_report_hash=trajectory.report_hash,
        files=records,
        empty_directories=_empty_directories(output),
    )
    (output / "manifest.json").write_bytes(canonical_json_bytes(manifest.to_json()))
    return manifest


def verify_phase14_bundle(bundle_root: Path) -> Phase14BundleManifest:
    root = bundle_root.resolve(strict=True)
    manifest_value = load_json_strict(
        (root / "manifest.json").read_bytes(),
        require_canonical=True,
    )
    manifest = Phase14BundleManifest.from_json(manifest_value)
    expected_paths = tuple(record.path for record in manifest.files)
    observed_paths = tuple(
        path.relative_to(root).as_posix()
        for path in _regular_files(root)
        if path.relative_to(root).as_posix() != "manifest.json"
    )
    if observed_paths != expected_paths:
        raise SchemaValidationError(
            "phase14.bundle.files",
            "bundle file set differs from manifest",
        )
    for record in manifest.files:
        path = root / record.path
        if path.stat().st_size != record.size_bytes:
            raise SchemaValidationError(
                "phase14.bundle.files",
                f"size mismatch: {record.path}",
            )
        if sha256_hex(path.read_bytes()) != record.sha256:
            raise SchemaValidationError(
                "phase14.bundle.files",
                f"hash mismatch: {record.path}",
            )
    observed_empty = _empty_directories(root)
    if observed_empty != tuple(manifest.empty_directories):
        raise SchemaValidationError(
            "phase14.bundle.empty_directories",
            "empty-directory set differs",
        )
    trajectory_value = load_json_strict(
        (root / "campaign/phase14_trajectory.json").read_bytes(),
        require_canonical=True,
    )
    trajectory = Phase14TrajectoryReport.from_json(trajectory_value)
    if trajectory.report_hash != manifest.trajectory_report_hash:
        raise SchemaValidationError(
            "phase14.bundle.trajectory_report_hash",
            "trajectory binding mismatch",
        )
    if trajectory.source_head != manifest.source_head or trajectory.source_tree != manifest.source_tree:
        raise SchemaValidationError(
            "phase14.bundle.source",
            "source binding mismatch",
        )
    return manifest


__all__ = [
    "Phase14BundleFile",
    "Phase14BundleManifest",
    "build_phase14_bundle",
    "verify_phase14_bundle",
]
