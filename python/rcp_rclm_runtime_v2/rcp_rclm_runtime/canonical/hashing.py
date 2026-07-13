from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence
from typing import Final, Iterable, Mapping

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.canonical.paths import validate_file_mode, validate_semantic_path
from rcp_rclm_runtime.errors import CanonicalizationError

CANONICAL_JSON_HASH_DOMAIN: Final[bytes] = b"RCPRCLM-CANONICAL-JSON-V2\0"
TREE_HASH_DOMAIN: Final[bytes] = b"RCPRCLM-TREE-V2\0"
HASH_HEX_LENGTH: Final[int] = 64


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_hash(value: object) -> str:
    return sha256_hex(CANONICAL_JSON_HASH_DOMAIN + canonical_json_bytes(value))


def validate_hash256(value: str, path: str = "hash") -> str:
    if not isinstance(value, str):
        raise CanonicalizationError(path, "SHA-256 value must be a string")
    if len(value) != HASH_HEX_LENGTH or any(character not in "0123456789abcdef" for character in value):
        raise CanonicalizationError(path, "expected lowercase 64-character SHA-256 hex")
    return value


@dataclass(frozen=True, slots=True)
class SemanticFileRecord:
    path: str
    mode: str
    size: int
    sha256: str

    def __post_init__(self) -> None:
        validate_semantic_path(self.path)
        validate_file_mode(self.mode)
        if isinstance(self.size, bool) or not isinstance(self.size, int) or self.size < 0:
            raise CanonicalizationError("file.size", "file size must be a nonnegative integer")
        validate_hash256(self.sha256, "file.sha256")

    def to_json(self) -> dict[str, str]:
        return {
            "path": self.path,
            "mode": self.mode,
            "size": str(self.size),
            "sha256": self.sha256,
        }

    def tree_line(self) -> bytes:
        return (
            self.path.encode("utf-8")
            + b"\0"
            + self.mode.encode("ascii")
            + b"\0"
            + str(self.size).encode("ascii")
            + b"\0"
            + self.sha256.encode("ascii")
            + b"\n"
        )


def semantic_tree_hash(records: Iterable[SemanticFileRecord]) -> str:
    record_list = list(records)
    seen_paths: set[str] = set()
    for record in record_list:
        if record.path in seen_paths:
            raise CanonicalizationError("tree", f"duplicate semantic path: {record.path}")
        seen_paths.add(record.path)
    ordered = sorted(record_list, key=lambda record: record.path.encode("utf-8"))
    payload = b"".join(record.tree_line() for record in ordered)
    return sha256_hex(TREE_HASH_DOMAIN + payload)


def file_record_from_bytes(path: str, mode: str, content: bytes) -> SemanticFileRecord:
    return SemanticFileRecord(
        path=validate_semantic_path(path),
        mode=validate_file_mode(mode),
        size=len(content),
        sha256=sha256_hex(content),
    )


def build_tree_records(
    root: Path,
    declared_modes: Mapping[str, str] | None = None,
) -> Sequence[SemanticFileRecord]:
    resolved_root = root.resolve(strict=True)
    if not resolved_root.is_dir():
        raise CanonicalizationError("tree.root", "tree root must be a directory")

    inode_paths: dict[tuple[int, int], list[tuple[Path, str]]] = {}
    records: list[SemanticFileRecord] = []
    for current_root, directory_names, file_names in os.walk(resolved_root, followlinks=False):
        current_path = Path(current_root)
        for directory_name in directory_names:
            directory_path = current_path / directory_name
            if directory_path.is_symlink():
                raise CanonicalizationError("tree", f"symlink directory is forbidden: {directory_path}")
        for file_name in file_names:
            file_path = current_path / file_name
            relative = file_path.relative_to(resolved_root).as_posix()
            validate_semantic_path(relative)
            stat_result = file_path.lstat()
            if stat.S_ISLNK(stat_result.st_mode):
                raise CanonicalizationError("tree", f"symlink is forbidden: {relative}")
            if not stat.S_ISREG(stat_result.st_mode):
                raise CanonicalizationError("tree", f"non-regular file is forbidden: {relative}")
            inode_key = (stat_result.st_dev, stat_result.st_ino)
            for previous_path, previous_relative in inode_paths.get(inode_key, []):
                try:
                    aliases = os.path.samefile(file_path, previous_path)
                except OSError as exc:
                    raise CanonicalizationError(
                        "tree",
                        f"could not determine file identity for {relative}: {exc}",
                    ) from exc
                if aliases:
                    raise CanonicalizationError(
                        "tree",
                        f"hard-link alias is forbidden: {relative} aliases {previous_relative}",
                    )
            inode_paths.setdefault(inode_key, []).append((file_path, relative))
            if declared_modes is not None:
                if relative not in declared_modes:
                    raise CanonicalizationError("tree", f"missing declared mode for {relative}")
                mode = validate_file_mode(declared_modes[relative])
            else:
                mode = "0755" if (stat_result.st_mode & 0o111) else "0644"
            content = file_path.read_bytes()
            records.append(file_record_from_bytes(relative, mode, content))

    if declared_modes is not None:
        unknown = sorted(set(declared_modes) - {record.path for record in records})
        if unknown:
            raise CanonicalizationError("tree", f"declared modes reference missing files: {', '.join(unknown)}")
    return tuple(sorted(records, key=lambda record: record.path.encode("utf-8")))
