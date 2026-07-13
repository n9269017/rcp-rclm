from __future__ import annotations

import re
import unicodedata
from pathlib import PurePosixPath
from typing import Final

from rcp_rclm_runtime.errors import CanonicalizationError

_DRIVE_PREFIX: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z]:")
ALLOWED_FILE_MODES: Final[frozenset[str]] = frozenset({"0644", "0755"})


def normalize_semantic_path(path: str) -> str:
    if not isinstance(path, str):
        raise CanonicalizationError("path", "semantic path must be a string")
    return unicodedata.normalize("NFC", path)


def validate_semantic_path(path: str) -> str:
    if not isinstance(path, str):
        raise CanonicalizationError("path", "semantic path must be a string")
    if not path:
        raise CanonicalizationError("path", "semantic path must be nonempty")
    if "\x00" in path:
        raise CanonicalizationError("path", "NUL byte is forbidden")
    if "\\" in path:
        raise CanonicalizationError("path", "backslash is forbidden")
    if path != unicodedata.normalize("NFC", path):
        raise CanonicalizationError("path", "semantic path must already be NFC normalized")
    if path.startswith("/") or path.startswith("//"):
        raise CanonicalizationError("path", "absolute and UNC paths are forbidden")
    if _DRIVE_PREFIX.match(path) is not None:
        raise CanonicalizationError("path", "drive-letter paths are forbidden")
    segments = path.split("/")
    if any(segment == "" for segment in segments):
        raise CanonicalizationError("path", "empty path segments are forbidden")
    if any(segment in {".", ".."} for segment in segments):
        raise CanonicalizationError("path", "dot path segments are forbidden")
    pure = PurePosixPath(path)
    if pure.is_absolute():
        raise CanonicalizationError("path", "absolute path is forbidden")
    if pure.as_posix() != path:
        raise CanonicalizationError("path", "path is not in canonical POSIX form")
    return path


def validate_file_mode(mode: str) -> str:
    if mode not in ALLOWED_FILE_MODES:
        raise CanonicalizationError("mode", "semantic file mode must be 0644 or 0755")
    return mode
