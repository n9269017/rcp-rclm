from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, TypeAlias

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.canonical.json import JsonValue, canonicalize
from rcp_rclm_runtime.errors import SchemaValidationError

_SCHEMA_ID: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9][a-z0-9_.-]*\.v2$")

FrozenJsonScalar: TypeAlias = None | bool | int | str


@dataclass(frozen=True, slots=True)
class FrozenJsonArray:
    items: Sequence["FrozenJson"]

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))


@dataclass(frozen=True, slots=True)
class FrozenJsonObject:
    items: Sequence[tuple[str, "FrozenJson"]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))


FrozenJson: TypeAlias = FrozenJsonScalar | FrozenJsonArray | FrozenJsonObject


def strict_object(value: object, path: str, expected_fields: set[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, "expected an object")
    keys = set(value.keys())
    if any(not isinstance(key, str) for key in keys):
        raise SchemaValidationError(path, "all object keys must be strings")
    missing = sorted(expected_fields - keys)
    unknown = sorted(keys - expected_fields)
    if missing or unknown:
        parts: list[str] = []
        if missing:
            parts.append(f"missing fields: {', '.join(missing)}")
        if unknown:
            parts.append(f"unknown fields: {', '.join(str(item) for item in unknown)}")
        raise SchemaValidationError(path, "; ".join(parts))
    return value


def require_string(value: object, path: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        raise SchemaValidationError(path, "expected a string")
    normalized = unicodedata.normalize("NFC", value)
    if value != normalized:
        raise SchemaValidationError(path, "string must already be NFC normalized")
    if nonempty and not value:
        raise SchemaValidationError(path, "string must be nonempty")
    return value


def require_structural_integer(
    value: object,
    path: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaValidationError(path, "expected an integer")
    if minimum is not None and value < minimum:
        raise SchemaValidationError(path, f"expected value at least {minimum}")
    if maximum is not None and value > maximum:
        raise SchemaValidationError(path, f"expected value at most {maximum}")
    return value


def require_schema_id(value: object, path: str, expected: str | None = None) -> str:
    text = require_string(value, path)
    if _SCHEMA_ID.fullmatch(text) is None:
        raise SchemaValidationError(path, "invalid schema identifier")
    if expected is not None and text != expected:
        raise SchemaValidationError(path, f"expected schema identifier {expected}")
    return text


def freeze_json(value: object, path: str = "value") -> FrozenJson:
    canonical = canonicalize(value, path)
    return _freeze_canonical(canonical)


def _freeze_canonical(value: JsonValue) -> FrozenJson:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, list):
        return FrozenJsonArray(tuple(_freeze_canonical(item) for item in value))
    return FrozenJsonObject(
        tuple((key, _freeze_canonical(item)) for key, item in sorted(value.items()))
    )


def thaw_json(value: FrozenJson) -> JsonValue:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, FrozenJsonObject):
        return {key: thaw_json(item) for key, item in value.items}
    return [thaw_json(item) for item in value.items]


@dataclass(frozen=True, slots=True)
class TypedArtifactRecord:
    schema_id: str
    content_hash: str
    value: FrozenJson

    def __post_init__(self) -> None:
        require_schema_id(self.schema_id, "typed_artifact.schema_id")
        validate_hash256(self.content_hash, "typed_artifact.content_hash")
        if isinstance(self.value, (FrozenJsonArray, FrozenJsonObject)) or self.value is None or isinstance(
            self.value, (bool, int, str)
        ):
            frozen = freeze_json(thaw_json(self.value), "typed_artifact.value")
        else:
            frozen = freeze_json(self.value, "typed_artifact.value")
        object.__setattr__(self, "value", frozen)
        actual_hash = canonical_json_hash(thaw_json(frozen))
        if actual_hash != self.content_hash:
            raise SchemaValidationError(
                "typed_artifact.content_hash",
                f"content hash mismatch: expected {self.content_hash}, computed {actual_hash}",
            )

    @classmethod
    def from_value(cls, schema_id: str, value: object) -> TypedArtifactRecord:
        frozen = freeze_json(value)
        content_hash = canonical_json_hash(thaw_json(frozen))
        return cls(schema_id=schema_id, content_hash=content_hash, value=frozen)

    @classmethod
    def from_json(cls, value: object, path: str = "typed_artifact") -> TypedArtifactRecord:
        obj = strict_object(value, path, {"schema_id", "content_hash", "value"})
        schema_id = require_schema_id(obj["schema_id"], f"{path}.schema_id")
        content_hash = require_string(obj["content_hash"], f"{path}.content_hash")
        validate_hash256(content_hash, f"{path}.content_hash")
        frozen = freeze_json(obj["value"], f"{path}.value")
        return cls(schema_id=schema_id, content_hash=content_hash, value=frozen)

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "content_hash": self.content_hash,
            "value": thaw_json(self.value),
        }
