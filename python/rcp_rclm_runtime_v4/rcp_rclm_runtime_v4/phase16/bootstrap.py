from __future__ import annotations

import hashlib
import json
import struct
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase16.constants import (
    PHASE16_BOOTSTRAP_SCHEMA_ID,
    PHASE16_DIAGONAL_SEMANTICS_ID,
    PHASE16_FIXED_VERIFIER_HASH,
    PHASE16_INHERITED_PLANNER_PROJECTION,
    PHASE16_PHASE15_BUNDLE_ARCHIVE_SHA256,
    PHASE16_PHASE15_BUNDLE_MANIFEST_HASH,
    PHASE16_PHASE15_CLOSURE_HASH,
    PHASE16_PHASE15_FINAL_ARCHIVE_SHA256,
    PHASE16_PHASE15_FINAL_STORE_HASH,
    PHASE16_PHASE15_M9_SEMANTIC_PACKAGE_HASH,
    PHASE16_PHASE15_PLANNER_MANIFEST_HASH,
    PHASE16_PHASE15_PLANNER_MANIFEST_PATH,
    PHASE16_PHASE15_PLANNER_WEIGHTS_PATH,
    PHASE16_PHASE15_PLANNER_WEIGHTS_SHA256,
    PHASE16_PHASE15_SOURCE_HEAD,
    PHASE16_PHASE15_SOURCE_TREE,
    PHASE16_PHASE15_TRAJECTORY_HASH,
    PHASE16_PINNED_OUTER_VERIFICATION_HASH,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_members(archive: zipfile.ZipFile, path: str) -> tuple[str, ...]:
    names = tuple(archive.namelist())
    if not names:
        raise SchemaValidationError(path, "archive is empty")
    if len(set(names)) != len(names):
        raise SchemaValidationError(path, "archive contains duplicate paths")
    for name in names:
        pure = PurePosixPath(name)
        if pure.is_absolute() or ".." in pure.parts:
            raise SchemaValidationError(path, f"unsafe archive path: {name}")
    return names


def _json_member(archive: zipfile.ZipFile, name: str, path: str) -> Mapping[str, object]:
    try:
        value = json.loads(archive.read(name).decode("utf-8"))
    except (KeyError, UnicodeError, json.JSONDecodeError) as exc:
        raise SchemaValidationError(path, f"could not read {name}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, f"{name} is not an object")
    return value


def _verify_bound_hash(value: Mapping[str, object], field: str, path: str) -> str:
    observed = value.get(field)
    if not isinstance(observed, str):
        raise SchemaValidationError(path, f"missing {field}")
    payload = dict(value)
    del payload[field]
    expected = canonical_json_hash(payload)
    if observed != expected:
        raise SchemaValidationError(
            path,
            f"{field} mismatch: expected={expected} observed={observed}",
        )
    return observed


def _planner_projection(weights: bytes) -> tuple[tuple[int, int], ...]:
    if len(weights) % 2:
        raise SchemaValidationError("phase16.bootstrap.planner_weights", "odd byte length")
    values = struct.unpack(f"<{len(weights) // 2}h", weights)
    return tuple((index, value) for index, value in enumerate(values) if value != 0)


@dataclass(frozen=True, slots=True)
class Phase16BootstrapReport:
    phase15_closure_archive_sha256: str
    phase15_bundle_archive_sha256: str
    phase15_closure_report_hash: str
    phase15_bundle_manifest_hash: str
    phase15_trajectory_report_hash: str
    phase15_source_head: str
    phase15_source_tree: str
    phase15_final_store_hash: str
    phase15_m9_semantic_package_hash: str
    inherited_planner_manifest_hash: str
    inherited_planner_weights_sha256: str
    inherited_planner_projection_hash: str
    inherited_planner_nonzero_count: int
    fixed_verifier_hash: str
    pinned_outer_verification_hash: str
    semantics_id: str

    schema_id: ClassVar[str] = PHASE16_BOOTSTRAP_SCHEMA_ID

    @property
    def accepted(self) -> bool:
        return (
            self.phase15_closure_archive_sha256
            == PHASE16_PHASE15_FINAL_ARCHIVE_SHA256
            and self.phase15_bundle_archive_sha256
            == PHASE16_PHASE15_BUNDLE_ARCHIVE_SHA256
            and self.phase15_closure_report_hash == PHASE16_PHASE15_CLOSURE_HASH
            and self.phase15_bundle_manifest_hash
            == PHASE16_PHASE15_BUNDLE_MANIFEST_HASH
            and self.phase15_trajectory_report_hash == PHASE16_PHASE15_TRAJECTORY_HASH
            and self.phase15_source_head == PHASE16_PHASE15_SOURCE_HEAD
            and self.phase15_source_tree == PHASE16_PHASE15_SOURCE_TREE
            and self.phase15_final_store_hash == PHASE16_PHASE15_FINAL_STORE_HASH
            and self.phase15_m9_semantic_package_hash
            == PHASE16_PHASE15_M9_SEMANTIC_PACKAGE_HASH
            and self.inherited_planner_manifest_hash
            == PHASE16_PHASE15_PLANNER_MANIFEST_HASH
            and self.inherited_planner_weights_sha256
            == PHASE16_PHASE15_PLANNER_WEIGHTS_SHA256
            and self.inherited_planner_projection_hash
            == canonical_json_hash(
                {
                    "schema_id": "runtime.v4.phase16.planner_projection.v1",
                    "nonzero_coefficients": [
                        [index, value]
                        for index, value in PHASE16_INHERITED_PLANNER_PROJECTION
                    ],
                }
            )
            and self.inherited_planner_nonzero_count
            == len(PHASE16_INHERITED_PLANNER_PROJECTION)
            and self.fixed_verifier_hash == PHASE16_FIXED_VERIFIER_HASH
            and self.pinned_outer_verification_hash
            == PHASE16_PINNED_OUTER_VERIFICATION_HASH
            and self.semantics_id == PHASE16_DIAGONAL_SEMANTICS_ID
        )

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "phase15_closure_archive_sha256": self.phase15_closure_archive_sha256,
            "phase15_bundle_archive_sha256": self.phase15_bundle_archive_sha256,
            "phase15_closure_report_hash": self.phase15_closure_report_hash,
            "phase15_bundle_manifest_hash": self.phase15_bundle_manifest_hash,
            "phase15_trajectory_report_hash": self.phase15_trajectory_report_hash,
            "phase15_source_head": self.phase15_source_head,
            "phase15_source_tree": self.phase15_source_tree,
            "phase15_final_store_hash": self.phase15_final_store_hash,
            "phase15_m9_semantic_package_hash": self.phase15_m9_semantic_package_hash,
            "inherited_planner_manifest_hash": self.inherited_planner_manifest_hash,
            "inherited_planner_weights_sha256": self.inherited_planner_weights_sha256,
            "inherited_planner_projection_hash": self.inherited_planner_projection_hash,
            "inherited_planner_nonzero_count": self.inherited_planner_nonzero_count,
            "fixed_verifier_hash": self.fixed_verifier_hash,
            "pinned_outer_verification_hash": self.pinned_outer_verification_hash,
            "semantics_id": self.semantics_id,
            "exact_phase15_closure_retained": True,
            "exact_phase15_bundle_retained": True,
            "candidate_self_report_authoritative": False,
            "manual_repairs": 0,
            "accepted": self.accepted,
            "phase16_exit_closed": False,
            "gate_e_closed": False,
            "next_phase": 16,
        }

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["report_hash"] = self.report_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> Phase16BootstrapReport:
        if not isinstance(value, Mapping):
            raise SchemaValidationError("phase16.bootstrap", "expected object")
        result = cls(
            phase15_closure_archive_sha256=str(
                value.get("phase15_closure_archive_sha256")
            ),
            phase15_bundle_archive_sha256=str(
                value.get("phase15_bundle_archive_sha256")
            ),
            phase15_closure_report_hash=str(
                value.get("phase15_closure_report_hash")
            ),
            phase15_bundle_manifest_hash=str(
                value.get("phase15_bundle_manifest_hash")
            ),
            phase15_trajectory_report_hash=str(
                value.get("phase15_trajectory_report_hash")
            ),
            phase15_source_head=str(value.get("phase15_source_head")),
            phase15_source_tree=str(value.get("phase15_source_tree")),
            phase15_final_store_hash=str(value.get("phase15_final_store_hash")),
            phase15_m9_semantic_package_hash=str(
                value.get("phase15_m9_semantic_package_hash")
            ),
            inherited_planner_manifest_hash=str(
                value.get("inherited_planner_manifest_hash")
            ),
            inherited_planner_weights_sha256=str(
                value.get("inherited_planner_weights_sha256")
            ),
            inherited_planner_projection_hash=str(
                value.get("inherited_planner_projection_hash")
            ),
            inherited_planner_nonzero_count=int(
                value.get("inherited_planner_nonzero_count", -1)
            ),
            fixed_verifier_hash=str(value.get("fixed_verifier_hash")),
            pinned_outer_verification_hash=str(
                value.get("pinned_outer_verification_hash")
            ),
            semantics_id=str(value.get("semantics_id")),
        )
        if value.get("report_hash") != result.report_hash:
            raise SchemaValidationError("phase16.bootstrap.report_hash", "hash mismatch")
        if value.get("accepted") is not result.accepted or not result.accepted:
            raise SchemaValidationError("phase16.bootstrap.accepted", "bootstrap did not close")
        return result


def verify_phase16_bootstrap(
    *,
    phase15_closure_archive: Path,
    phase15_bundle_archive: Path,
) -> Phase16BootstrapReport:
    closure_path = phase15_closure_archive.resolve(strict=True)
    bundle_path = phase15_bundle_archive.resolve(strict=True)
    closure_sha = _sha256(closure_path)
    bundle_sha = _sha256(bundle_path)
    if closure_sha != PHASE16_PHASE15_FINAL_ARCHIVE_SHA256:
        raise SchemaValidationError(
            "phase16.bootstrap.phase15_closure_archive",
            f"SHA-256 mismatch: {closure_sha}",
        )
    if bundle_sha != PHASE16_PHASE15_BUNDLE_ARCHIVE_SHA256:
        raise SchemaValidationError(
            "phase16.bootstrap.phase15_bundle_archive",
            f"SHA-256 mismatch: {bundle_sha}",
        )

    with zipfile.ZipFile(closure_path) as archive:
        names = _safe_members(archive, "phase16.bootstrap.phase15_closure_archive")
        if set(names) != {"phase15_exit.json", "phase15_exit.log"}:
            raise SchemaValidationError(
                "phase16.bootstrap.phase15_closure_archive",
                "unexpected closure archive surface",
            )
        closure = _json_member(
            archive,
            "phase15_exit.json",
            "phase16.bootstrap.phase15_closure",
        )
    closure_hash = _verify_bound_hash(
        closure,
        "report_hash",
        "phase16.bootstrap.phase15_closure",
    )
    expected_closure_fields = {
        "accepted": True,
        "phase15_exit_closed": True,
        "gate_e_closed": False,
        "next_phase": 16,
        "manual_repairs": 0,
        "source_head": PHASE16_PHASE15_SOURCE_HEAD,
        "source_tree": PHASE16_PHASE15_SOURCE_TREE,
        "trajectory_report_hash": PHASE16_PHASE15_TRAJECTORY_HASH,
        "bundle_manifest_hash": PHASE16_PHASE15_BUNDLE_MANIFEST_HASH,
        "final_store_package_hash": PHASE16_PHASE15_FINAL_STORE_HASH,
        "final_m9_semantic_package_hash": PHASE16_PHASE15_M9_SEMANTIC_PACKAGE_HASH,
    }
    for field, expected in expected_closure_fields.items():
        if closure.get(field) != expected:
            raise SchemaValidationError(
                f"phase16.bootstrap.phase15_closure.{field}",
                f"expected={expected!r} observed={closure.get(field)!r}",
            )
    if closure_hash != PHASE16_PHASE15_CLOSURE_HASH:
        raise SchemaValidationError(
            "phase16.bootstrap.phase15_closure.report_hash",
            "unexpected authoritative closure identity",
        )

    with zipfile.ZipFile(bundle_path) as archive:
        names = set(_safe_members(archive, "phase16.bootstrap.phase15_bundle_archive"))
        required = {
            "manifest.json",
            "campaign/phase15_trajectory.json",
            PHASE16_PHASE15_PLANNER_MANIFEST_PATH,
            PHASE16_PHASE15_PLANNER_WEIGHTS_PATH,
        }
        missing = sorted(required.difference(names))
        if missing:
            raise SchemaValidationError(
                "phase16.bootstrap.phase15_bundle_archive",
                f"missing required paths: {missing}",
            )
        manifest = _json_member(
            archive,
            "manifest.json",
            "phase16.bootstrap.phase15_bundle_manifest",
        )
        trajectory = _json_member(
            archive,
            "campaign/phase15_trajectory.json",
            "phase16.bootstrap.phase15_trajectory",
        )
        planner_manifest = _json_member(
            archive,
            PHASE16_PHASE15_PLANNER_MANIFEST_PATH,
            "phase16.bootstrap.inherited_planner_manifest",
        )
        planner_weights = archive.read(PHASE16_PHASE15_PLANNER_WEIGHTS_PATH)

    manifest_hash = _verify_bound_hash(
        manifest,
        "manifest_hash",
        "phase16.bootstrap.phase15_bundle_manifest",
    )
    trajectory_hash = _verify_bound_hash(
        trajectory,
        "report_hash",
        "phase16.bootstrap.phase15_trajectory",
    )
    planner_manifest_hash = _verify_bound_hash(
        planner_manifest,
        "manifest_hash",
        "phase16.bootstrap.inherited_planner_manifest",
    )
    planner_weights_sha = hashlib.sha256(planner_weights).hexdigest()
    projection = _planner_projection(planner_weights)
    if projection != tuple(PHASE16_INHERITED_PLANNER_PROJECTION):
        raise SchemaValidationError(
            "phase16.bootstrap.inherited_planner_projection",
            "nonzero planner projection changed",
        )
    projection_hash = canonical_json_hash(
        {
            "schema_id": "runtime.v4.phase16.planner_projection.v1",
            "nonzero_coefficients": [[index, value] for index, value in projection],
        }
    )
    report = Phase16BootstrapReport(
        phase15_closure_archive_sha256=closure_sha,
        phase15_bundle_archive_sha256=bundle_sha,
        phase15_closure_report_hash=closure_hash,
        phase15_bundle_manifest_hash=manifest_hash,
        phase15_trajectory_report_hash=trajectory_hash,
        phase15_source_head=str(manifest.get("source_head")),
        phase15_source_tree=str(manifest.get("source_tree")),
        phase15_final_store_hash=str(closure.get("final_store_package_hash")),
        phase15_m9_semantic_package_hash=str(
            closure.get("final_m9_semantic_package_hash")
        ),
        inherited_planner_manifest_hash=planner_manifest_hash,
        inherited_planner_weights_sha256=planner_weights_sha,
        inherited_planner_projection_hash=projection_hash,
        inherited_planner_nonzero_count=len(projection),
        fixed_verifier_hash=PHASE16_FIXED_VERIFIER_HASH,
        pinned_outer_verification_hash=PHASE16_PINNED_OUTER_VERIFICATION_HASH,
        semantics_id=PHASE16_DIAGONAL_SEMANTICS_ID,
    )
    if planner_manifest.get("weights_sha256") != planner_weights_sha:
        raise SchemaValidationError(
            "phase16.bootstrap.inherited_planner_manifest.weights_sha256",
            "manifest-to-weight binding failed",
        )
    if not report.accepted:
        raise SchemaValidationError("phase16.bootstrap", "bootstrap predicates failed")
    return report


__all__ = ["Phase16BootstrapReport", "verify_phase16_bootstrap"]
