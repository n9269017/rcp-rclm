from __future__ import annotations

from typing import Final

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import JsonValue, load_json_strict
from rcp_rclm_runtime.errors import CanonicalizationError
from rcp_rclm_runtime.successor.records import (
    Phase6ReasonCode,
    SubstantiveComponentKind,
)
from rcp_rclm_runtime.successor.workspace_types import Phase6WorkspaceError

_METADATA_ONLY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "created_at",
        "index",
        "manifest_hash",
        "name",
        "package_id",
        "parent_manifest_hash",
        "parent_package_id",
        "policy_id",
        "schema_id",
        "sequence",
        "timestamp",
        "updated_at",
        "version",
    }
)


def semantic_content_hash(
    content: bytes | None,
    path: str,
    component_kind: SubstantiveComponentKind | None,
) -> str | None:
    if content is None:
        return None
    if component_kind is None:
        return sha256_hex(content)
    if path.endswith(".json"):
        try:
            parsed = load_json_strict(content, require_canonical=True)
        except CanonicalizationError as exc:
            raise Phase6WorkspaceError(
                Phase6ReasonCode.WORKSPACE_INVALID,
                f"substantive JSON component is not canonical: {path}: {exc}",
            ) from exc
        return canonical_json_hash(strip_metadata(parsed))
    return sha256_hex(content)


def strip_metadata(value: JsonValue) -> JsonValue:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, list):
        return [strip_metadata(item) for item in value]
    return {
        key: strip_metadata(item)
        for key, item in sorted(value.items())
        if key not in _METADATA_ONLY_KEYS
    }
