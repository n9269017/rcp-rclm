from __future__ import annotations

import os
import tempfile
from collections.abc import Sequence
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import CanonicalizationError, SchemaValidationError

from rcp_rclm_runtime_v3.phase13.full_records import (
    Phase13BundleFileRecord,
    Phase13TrajectoryBundleManifest,
)

PHASE13_BUNDLE_MANIFEST_NAME = "manifest.json"
PHASE13_BUNDLE_CLOSURE_NAME = "phase12_closure.json"
PHASE13_BUNDLE_SOURCE_BINDING_NAME = "source_binding.json"
PHASE13_BUNDLE_TRAJECTORY_NAME = "trajectory"
PHASE13_REQUIRED_WORK_ROOTS = (
    "promotion_evidence",
    "reference",
    "store",
)
PHASE13_REQUIRED_EMPTY_WORK_DIRECTORIES = ("store/runs",)


class Phase13BundleError(ValueError):
    __slots__ = ("detail",)

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _regular_files(root: Path) -> Sequence[Path]:
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise Phase13BundleError(f"expected a directory: {resolved}")
    files: list[Path] = []
    seen_inodes: dict[tuple[int, int], str] = {}
    for current_root, directory_names, file_names in os.walk(resolved, followlinks=False):
        current = Path(current_root)
        directory_names.sort(key=lambda item: item.encode("utf-8"))
        file_names.sort(key=lambda item: item.encode("utf-8"))
        for directory_name in directory_names:
            path = current / directory_name
            if path.is_symlink():
                raise Phase13BundleError(f"symlink directory is forbidden: {path}")
        for file_name in file_names:
            path = current / file_name
            status = path.lstat()
            if path.is_symlink() or not path.is_file():
                raise Phase13BundleError(f"only regular files are permitted: {path}")
            key = (status.st_dev, status.st_ino)
            relative = path.relative_to(resolved).as_posix()
            if key in seen_inodes:
                raise Phase13BundleError(
                    f"hard-link aliases are forbidden: {relative} aliases {seen_inodes[key]}"
                )
            seen_inodes[key] = relative
            files.append(path)
    return tuple(
        sorted(
            files,
            key=lambda item: item.relative_to(resolved).as_posix().encode("utf-8"),
        )
    )


def _empty_directories(root: Path) -> Sequence[str]:
    resolved = root.resolve(strict=True)
    empty: list[str] = []
    for current_root, directory_names, file_names in os.walk(
        resolved,
        topdown=False,
        followlinks=False,
    ):
        current = Path(current_root)
        if current == resolved:
            continue
        for directory_name in directory_names:
            if (current / directory_name).is_symlink():
                raise Phase13BundleError(
                    f"symlink directory is forbidden: {current / directory_name}"
                )
        if not directory_names and not file_names:
            empty.append(current.relative_to(resolved).as_posix())
    return tuple(sorted(empty, key=lambda item: item.encode("utf-8")))


def _copy_regular_tree(source: Path, destination: Path) -> None:
    resolved_source = source.resolve(strict=True)
    if destination.exists():
        raise Phase13BundleError(f"copy destination already exists: {destination}")
    destination.mkdir(parents=True, exist_ok=False)
    for current_root, directory_names, _ in os.walk(resolved_source, followlinks=False):
        current = Path(current_root)
        directory_names.sort(key=lambda item: item.encode("utf-8"))
        for directory_name in directory_names:
            source_directory = current / directory_name
            if source_directory.is_symlink():
                raise Phase13BundleError(
                    f"symlink directory is forbidden: {source_directory}"
                )
            relative = source_directory.relative_to(resolved_source)
            (destination / relative).mkdir(parents=True, exist_ok=True)
    for source_path in _regular_files(resolved_source):
        relative = source_path.relative_to(resolved_source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        content = source_path.read_bytes()
        target.write_bytes(content)
        if target.read_bytes() != content:
            raise Phase13BundleError(f"copied evidence differs: {relative.as_posix()}")


def _file_records(root: Path) -> Sequence[Phase13BundleFileRecord]:
    resolved = root.resolve(strict=True)
    records = []
    for path in _regular_files(resolved):
        relative = path.relative_to(resolved).as_posix()
        if relative == PHASE13_BUNDLE_MANIFEST_NAME:
            continue
        content = path.read_bytes()
        records.append(
            Phase13BundleFileRecord(
                path=relative,
                size=len(content),
                sha256=sha256_hex(content),
            )
        )
    return tuple(records)


def _trajectory_content_hash(
    files: Sequence[Phase13BundleFileRecord],
    empty_directories: Sequence[str],
) -> str:
    return canonical_json_hash(
        {
            "empty_directories": list(empty_directories),
            "files": [item.to_json() for item in files],
        }
    )


def _closure_report(path: Path) -> tuple[dict[str, object], bytes]:
    content = path.resolve(strict=True).read_bytes()
    value = load_json_strict(content, require_canonical=True)
    if not isinstance(value, dict):
        raise Phase13BundleError("Phase 12 closure report must be an object")
    if value.get("accepted") is not True or value.get("phase12_exit_closed") is not True:
        raise Phase13BundleError("Phase 12 closure report is not closed")
    claimed_hash = value.get("report_hash")
    if not isinstance(claimed_hash, str):
        raise Phase13BundleError("Phase 12 closure report lacks report_hash")
    content_without_hash = dict(value)
    del content_without_hash["report_hash"]
    if canonical_json_hash(content_without_hash) != claimed_hash:
        raise Phase13BundleError("Phase 12 closure report hash does not recompute")
    return value, content


def build_phase13_trajectory_bundle(
    work_root: Path,
    closure_report_path: Path,
    output_root: Path,
    *,
    source_head: str,
) -> Phase13TrajectoryBundleManifest:
    source = work_root.resolve(strict=True)
    output = output_root.resolve(strict=False)
    if output.exists():
        raise Phase13BundleError(f"bundle output already exists: {output}")
    observed_roots = {entry.name for entry in source.iterdir() if entry.is_dir()}
    expected_roots = set(PHASE13_REQUIRED_WORK_ROOTS)
    if observed_roots != expected_roots:
        raise Phase13BundleError(
            "closure work root must contain exactly: "
            + ", ".join(PHASE13_REQUIRED_WORK_ROOTS)
        )
    for relative in PHASE13_REQUIRED_EMPTY_WORK_DIRECTORIES:
        path = source / relative
        if path.is_symlink() or not path.is_dir() or any(path.iterdir()):
            raise Phase13BundleError(
                f"required empty closure directory is missing or nonempty: {relative}"
            )
    closure, closure_bytes = _closure_report(closure_report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix="rcp-rclm-phase13-bundle-",
            dir=output.parent,
        ) as temporary:
            staging = Path(temporary) / "bundle"
            staging.mkdir(parents=True, exist_ok=False)
            trajectory = staging / PHASE13_BUNDLE_TRAJECTORY_NAME
            trajectory.mkdir(parents=True, exist_ok=False)
            for name in PHASE13_REQUIRED_WORK_ROOTS:
                _copy_regular_tree(source / name, trajectory / name)
            (staging / PHASE13_BUNDLE_CLOSURE_NAME).write_bytes(closure_bytes)
            source_binding = {
                "schema_id": "runtime.v3.phase13.source_binding.v1",
                "source_head": source_head,
                "phase12_closure_report_hash": closure["report_hash"],
                "phase12_exit_closed": True,
            }
            (staging / PHASE13_BUNDLE_SOURCE_BINDING_NAME).write_bytes(
                canonical_json_bytes(source_binding)
            )
            files = _file_records(staging)
            empty_directories = _empty_directories(staging)
            manifest = Phase13TrajectoryBundleManifest(
                source_head=source_head,
                closure_report_hash=str(closure["report_hash"]),
                closure_bytes_sha256=sha256_hex(closure_bytes),
                trajectory_content_hash=_trajectory_content_hash(
                    files,
                    empty_directories,
                ),
                files=files,
                empty_directories=empty_directories,
                required_roots=tuple(
                    sorted(
                        (
                            f"{PHASE13_BUNDLE_TRAJECTORY_NAME}/{name}"
                            for name in PHASE13_REQUIRED_WORK_ROOTS
                        ),
                        key=lambda item: item.encode("utf-8"),
                    )
                ),
            )
            (staging / PHASE13_BUNDLE_MANIFEST_NAME).write_bytes(
                canonical_json_bytes(manifest.to_json())
            )
            verified = verify_phase13_trajectory_bundle(staging)
            if verified != manifest:
                raise Phase13BundleError(
                    "public bundle verifier returned a different manifest"
                )
            os.replace(staging, output)
    except Phase13BundleError:
        raise
    except (
        CanonicalizationError,
        SchemaValidationError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise Phase13BundleError(
            f"trajectory-bundle construction failed: {type(exc).__name__}: {exc}"
        ) from exc
    return manifest


def verify_phase13_trajectory_bundle(
    bundle_root: Path,
) -> Phase13TrajectoryBundleManifest:
    try:
        root = bundle_root.resolve(strict=True)
        if not root.is_dir():
            raise Phase13BundleError("trajectory bundle root must be a directory")
        observed = {entry.name for entry in root.iterdir()}
        expected = {
            PHASE13_BUNDLE_MANIFEST_NAME,
            PHASE13_BUNDLE_CLOSURE_NAME,
            PHASE13_BUNDLE_SOURCE_BINDING_NAME,
            PHASE13_BUNDLE_TRAJECTORY_NAME,
        }
        if observed != expected:
            raise Phase13BundleError(
                "trajectory bundle layout is incomplete or contains unknown entries"
            )
        manifest_path = root / PHASE13_BUNDLE_MANIFEST_NAME
        manifest = Phase13TrajectoryBundleManifest.from_json(
            load_json_strict(manifest_path.read_bytes(), require_canonical=True)
        )
        observed_files = _file_records(root)
        if observed_files != tuple(manifest.files):
            raise Phase13BundleError(
                "trajectory bundle file manifest differs from measured bytes"
            )
        observed_empty = set(_empty_directories(root))
        declared_empty = set(manifest.empty_directories)
        unknown_empty = observed_empty - declared_empty
        if unknown_empty:
            raise Phase13BundleError(
                "trajectory bundle contains undeclared empty directories: "
                + ", ".join(sorted(unknown_empty))
            )
        for relative in manifest.empty_directories:
            path = root / relative
            if path.exists() and (
                path.is_symlink() or not path.is_dir() or any(path.iterdir())
            ):
                raise Phase13BundleError(
                    f"declared empty directory is not empty: {relative}"
                )
        closure, closure_bytes = _closure_report(
            root / PHASE13_BUNDLE_CLOSURE_NAME
        )
        if closure["report_hash"] != manifest.closure_report_hash:
            raise Phase13BundleError(
                "closure report hash differs from bundle manifest"
            )
        if sha256_hex(closure_bytes) != manifest.closure_bytes_sha256:
            raise Phase13BundleError(
                "closure report bytes differ from bundle manifest"
            )
        source_binding = load_json_strict(
            (root / PHASE13_BUNDLE_SOURCE_BINDING_NAME).read_bytes(),
            require_canonical=True,
        )
        expected_binding = {
            "schema_id": "runtime.v3.phase13.source_binding.v1",
            "source_head": manifest.source_head,
            "phase12_closure_report_hash": manifest.closure_report_hash,
            "phase12_exit_closed": True,
        }
        if source_binding != expected_binding:
            raise Phase13BundleError(
                "source binding differs from bundle manifest"
            )
        for required in manifest.required_roots:
            path = root / required
            if path.is_symlink() or not path.is_dir():
                raise Phase13BundleError(
                    f"required bundle directory is missing: {required}"
                )
        return manifest
    except Phase13BundleError:
        raise
    except (
        CanonicalizationError,
        SchemaValidationError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise Phase13BundleError(
            f"trajectory-bundle verification failed: {type(exc).__name__}: {exc}"
        ) from exc


def materialize_phase13_empty_directories(
    bundle_root: Path,
) -> Phase13TrajectoryBundleManifest:
    root = bundle_root.resolve(strict=True)
    manifest = verify_phase13_trajectory_bundle(root)
    for relative in sorted(
        manifest.empty_directories,
        key=lambda item: (len(Path(item).parts), item.encode("utf-8")),
    ):
        path = root / relative
        if path.exists():
            if path.is_symlink() or not path.is_dir() or any(path.iterdir()):
                raise Phase13BundleError(
                    f"declared empty directory is not empty: {relative}"
                )
        else:
            path.mkdir(parents=True, exist_ok=False)
    if set(_empty_directories(root)) != set(manifest.empty_directories):
        raise Phase13BundleError(
            "materialized empty-directory set differs from bundle manifest"
        )
    return manifest


__all__ = [
    "PHASE13_BUNDLE_CLOSURE_NAME",
    "PHASE13_BUNDLE_MANIFEST_NAME",
    "PHASE13_BUNDLE_SOURCE_BINDING_NAME",
    "PHASE13_BUNDLE_TRAJECTORY_NAME",
    "PHASE13_REQUIRED_EMPTY_WORK_DIRECTORIES",
    "PHASE13_REQUIRED_WORK_ROOTS",
    "Phase13BundleError",
    "build_phase13_trajectory_bundle",
    "materialize_phase13_empty_directories",
    "verify_phase13_trajectory_bundle",
]
