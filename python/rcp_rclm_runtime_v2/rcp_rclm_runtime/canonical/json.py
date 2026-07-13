from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass
from typing import TypeAlias

from rcp_rclm_runtime.errors import CanonicalizationError

JsonScalar: TypeAlias = None | bool | int | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class DuplicateKeyError(ValueError):
    def __init__(self, key: str) -> None:
        super().__init__(f"duplicate object key: {key}")
        self.key = key


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def _reject_float(text: str) -> object:
    raise CanonicalizationError("json", f"native JSON floating-point value is forbidden: {text}")


def _reject_constant(text: str) -> object:
    raise CanonicalizationError("json", f"nonfinite JSON value is forbidden: {text}")


def canonicalize(value: object, path: str = "$", allow_structural_integers: bool = True) -> JsonValue:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, int):
        if not allow_structural_integers:
            raise CanonicalizationError(path, "raw integer is not permitted in this semantic position")
        return value
    if isinstance(value, float):
        raise CanonicalizationError(path, "native floating-point values are forbidden")
    to_json = getattr(value, "to_json", None)
    if callable(to_json):
        return canonicalize(to_json(), path, allow_structural_integers)
    if is_dataclass(value):
        raise CanonicalizationError(
            path,
            "dataclass must expose an explicit to_json method before canonicalization",
        )
    if isinstance(value, Mapping):
        normalized: dict[str, JsonValue] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                raise CanonicalizationError(path, "object keys must be strings")
            key = unicodedata.normalize("NFC", raw_key)
            if key in normalized:
                raise CanonicalizationError(path, f"keys collide after NFC normalization: {key}")
            normalized[key] = canonicalize(
                raw_value,
                f"{path}.{key}",
                allow_structural_integers,
            )
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            canonicalize(item, f"{path}[{index}]", allow_structural_integers)
            for index, item in enumerate(value)
        ]
    raise CanonicalizationError(path, f"unsupported canonical value type: {type(value).__name__}")


def canonical_json_bytes(value: object) -> bytes:
    normalized = canonicalize(value)
    text = json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return text.encode("utf-8")


def canonical_json_text(value: object) -> str:
    return canonical_json_bytes(value).decode("utf-8")


def load_json_strict(data: bytes, require_canonical: bool = True) -> JsonValue:
    if data.startswith(b"\xef\xbb\xbf"):
        raise CanonicalizationError("json", "UTF-8 BOM is forbidden")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CanonicalizationError("json", f"invalid UTF-8: {exc}") from exc
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except DuplicateKeyError as exc:
        raise CanonicalizationError("json", str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise CanonicalizationError("json", f"invalid JSON: {exc.msg}") from exc
    normalized = canonicalize(parsed)
    canonical = canonical_json_bytes(normalized)
    if require_canonical and canonical != data:
        raise CanonicalizationError("json", "input bytes are not canonical RCPRCLM-CJSON-V2")
    return normalized


def load_json_text_strict(text: str, require_canonical: bool = True) -> JsonValue:
    return load_json_strict(text.encode("utf-8"), require_canonical=require_canonical)
