from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v3.phase13.full_records import Phase13ExitReport
from rcp_rclm_runtime_v3.phase13.source import discover_repository_head


_PLATFORMS = ("macos", "ubuntu", "windows")


def _object(path: Path) -> dict[str, object]:
    value = load_json_strict(path.resolve(strict=True).read_bytes(), require_canonical=True)
    if not isinstance(value, dict):
        raise SchemaValidationError(
            "phase13.closure.entry",
            f"expected object at {path}",
        )
    return value


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, "expected object")
    return value


def _verified_entry(path: Path, schema_id: str) -> dict[str, object]:
    entry = _object(path)
    if entry.get("schema_id") != schema_id:
        raise SchemaValidationError(
            "phase13.closure.schema_id",
            f"expected {schema_id}",
        )
    claimed = entry.get("entry_hash")
    if not isinstance(claimed, str):
        raise SchemaValidationError(
            "phase13.closure.entry_hash",
            "expected hash",
        )
    content = {key: value for key, value in entry.items() if key != "entry_hash"}
    if canonical_json_hash(content) != claimed:
        raise SchemaValidationError(
            "phase13.closure.entry_hash",
            "hash mismatch",
        )
    return entry


def _require_platform_set(values: Mapping[str, Path], path: str) -> None:
    if tuple(sorted(values)) != _PLATFORMS:
        raise ValueError(f"{path} requires macos, ubuntu, and windows")


def close_phase13(
    *,
    portable_entries: Mapping[str, Path],
    pinned_entries: Mapping[str, Path],
    repo_root: Path,
    expected_source_head: str,
) -> Phase13ExitReport:
    _require_platform_set(portable_entries, "portable Phase 13 closure")
    _require_platform_set(pinned_entries, "pinned Phase 13 closure")
    actual_head = discover_repository_head(repo_root)
    portable: dict[str, dict[str, object]] = {
        platform: _verified_entry(
            portable_entries[platform],
            "runtime.v3.phase13.structural_replay_entry.v1",
        )
        for platform in _PLATFORMS
    }
    pinned: dict[str, dict[str, object]] = {
        platform: _verified_entry(
            pinned_entries[platform],
            "runtime.v3.phase13.pinned_replay_entry.v1",
        )
        for platform in _PLATFORMS
    }
    pinned_reports = {
        platform: _mapping(
            pinned[platform].get("pinned_report"),
            f"phase13.closure.pinned_report.{platform}",
        )
        for platform in _PLATFORMS
    }
    first_portable = portable["ubuntu"]
    first_pinned = pinned["ubuntu"]
    bundle_hash = first_portable.get("bundle_manifest_hash")
    structural_hash = first_portable.get("structural_report_hash")
    phase13a_hash = first_pinned.get("phase13a_report_hash")
    pinned_report_hash = first_pinned.get("pinned_report_hash")
    if not all(
        isinstance(value, str)
        for value in (
            bundle_hash,
            structural_hash,
            phase13a_hash,
            pinned_report_hash,
        )
    ):
        raise SchemaValidationError(
            "phase13.closure.hashes",
            "expected string hashes",
        )
    checks = {
        "all_pinned_entries_accepted": all(
            item.get("accepted") is True for item in pinned.values()
        ),
        "all_pinned_entries_labeled": all(
            pinned[platform].get("platform_label") == platform
            for platform in _PLATFORMS
        ),
        "all_pinned_entries_not_prematurely_exit_closed": all(
            item.get("phase13_exit_closed") is False for item in pinned.values()
        ),
        "all_pinned_reports_hash_recomputed": all(
            canonical_json_hash(pinned_reports[platform])
            == pinned[platform].get("pinned_report_hash")
            for platform in _PLATFORMS
        ),
        "all_pinned_slices_closed": all(
            report.get("phase13c_slice_closed") is True
            for report in pinned_reports.values()
        ),
        "all_portable_entries_accepted": all(
            item.get("accepted") is True for item in portable.values()
        ),
        "all_portable_entries_labeled": all(
            portable[platform].get("platform_label") == platform
            for platform in _PLATFORMS
        ),
        "all_portable_reports_are_phase13b_closed": all(
            _mapping(
                item.get("structural_report"),
                "phase13.closure.structural_report",
            ).get("phase13b_slice_closed")
            is True
            for item in portable.values()
        ),
        "all_source_heads_match": all(
            item.get("source_head") == expected_source_head
            for item in (*portable.values(), *pinned.values())
        )
        and all(
            report.get("source_head") == expected_source_head
            for report in pinned_reports.values()
        ),
        "bundle_manifest_hash_cross_platform_identical": all(
            item.get("bundle_manifest_hash") == bundle_hash
            for item in (*portable.values(), *pinned.values())
        ),
        "phase13a_report_hash_cross_platform_identical": all(
            item.get("phase13a_report_hash") == phase13a_hash
            for item in pinned.values()
        ),
        "pinned_report_hash_cross_platform_identical": all(
            item.get("pinned_report_hash") == pinned_report_hash
            for item in pinned.values()
        ),
        "repository_head_bound": actual_head == expected_source_head,
        "structural_report_hash_cross_platform_identical": all(
            item.get("structural_report_hash") == structural_hash
            for item in (*portable.values(), *pinned.values())
        ),
    }
    report = Phase13ExitReport(
        source_head=expected_source_head,
        bundle_manifest_hash=str(bundle_hash),
        phase13a_report_hash=str(phase13a_hash),
        structural_report_hash=str(structural_hash),
        pinned_report_hash=str(pinned_report_hash),
        pinned_entry_hashes={
            platform: str(pinned[platform]["entry_hash"])
            for platform in _PLATFORMS
        },
        portable_entry_hashes={
            platform: str(portable[platform]["entry_hash"])
            for platform in _PLATFORMS
        },
        closure_checks={key: checks[key] for key in sorted(checks)},
    )
    if not report.accepted:
        failed = [
            key
            for key, accepted in report.closure_checks.items()
            if not accepted
        ]
        raise ValueError(
            f"Phase 13 exit did not close: {', '.join(failed)}"
        )
    return report


def write_phase13_exit_report(
    report: Phase13ExitReport,
    output_path: Path,
) -> None:
    payload = report.to_json()
    payload["report_hash"] = report.report_hash
    output = output_path.resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(payload))


__all__ = ["close_phase13", "write_phase13_exit_report"]
