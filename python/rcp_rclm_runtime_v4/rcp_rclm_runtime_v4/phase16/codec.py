from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TypeVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError

T = TypeVar("T")


def require_mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, "expected object")
    return value


def require_sequence(value: object, path: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SchemaValidationError(path, "expected array")
    return value


def require_text(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaValidationError(path, "expected nonempty string")
    return value


def require_bool(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise SchemaValidationError(path, "expected boolean")
    return value


def require_nonnegative(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SchemaValidationError(path, "expected nonnegative integer")
    return value


def require_positive(value: object, path: str) -> int:
    result = require_nonnegative(value, path)
    if result == 0:
        raise SchemaValidationError(path, "expected positive integer")
    return result


def require_hash(value: object, path: str) -> str:
    text = require_text(value, path)
    validate_hash256(text, path)
    return text


def ordered_unique(values: Sequence[str], path: str) -> tuple[str, ...]:
    result = tuple(values)
    if len(set(result)) != len(result):
        raise SchemaValidationError(path, "duplicate value")
    expected = tuple(sorted(result, key=lambda item: item.encode("utf-8")))
    if result != expected:
        raise SchemaValidationError(path, "values must be sorted by UTF-8 bytes")
    return result


def hash_payload(value: object) -> str:
    return canonical_json_hash(value)


def bind_hash(value: Mapping[str, object], field: str = "report_hash") -> dict[str, object]:
    if field in value:
        raise SchemaValidationError(field, "hash field must be absent before binding")
    result = dict(value)
    result[field] = canonical_json_hash(result)
    return result


def verify_bound_hash(value: Mapping[str, object], field: str = "report_hash") -> str:
    observed = require_hash(value.get(field), field)
    payload = dict(value)
    del payload[field]
    expected = canonical_json_hash(payload)
    if observed != expected:
        raise SchemaValidationError(field, f"hash mismatch: expected={expected} observed={observed}")
    return observed


def hash_chain(domain: str, values: Sequence[str]) -> str:
    return canonical_json_hash(
        {
            "domain": domain,
            "values": list(values),
        }
    )


def _reject_floats(value: object, path: str = "$") -> None:
    if isinstance(value, float):
        raise SchemaValidationError(path, "floating-point JSON is forbidden")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise SchemaValidationError(path, "object key must be a string")
            _reject_floats(item, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _reject_floats(item, f"{path}[{index}]")


def read_json(path: Path) -> object:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SchemaValidationError(str(path), f"could not read JSON: {exc}") from exc
    _reject_floats(value)
    return value


def write_json(path: Path, value: object) -> None:
    _reject_floats(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


__all__ = [
    "bind_hash",
    "hash_chain",
    "hash_payload",
    "ordered_unique",
    "read_json",
    "require_bool",
    "require_hash",
    "require_mapping",
    "require_nonnegative",
    "require_positive",
    "require_sequence",
    "require_text",
    "verify_bound_hash",
    "write_json",
]
