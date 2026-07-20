from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash

from rcp_rclm_runtime_v3.phase10.constants import REFERENCE_REPORT_SCHEMA_ID
from rcp_rclm_runtime_v3.phase10.package import (
    ModelPackageManifest,
    build_reference_predecessor_package,
    build_zero_lora_extension_package,
)
from rcp_rclm_runtime_v3.phase10.validation import (
    ConservativeExtensionReport,
    Phase10PackageReport,
    validate_conservative_extension,
    validate_model_package,
)


@dataclass(frozen=True, slots=True)
class Phase10ReferenceFixture:
    predecessor: ModelPackageManifest
    successor: ModelPackageManifest
    predecessor_report: Phase10PackageReport
    successor_report: Phase10PackageReport
    extension_report: ConservativeExtensionReport

    schema_id: ClassVar[str] = REFERENCE_REPORT_SCHEMA_ID

    @property
    def accepted(self) -> bool:
        return (
            self.predecessor_report.accepted
            and self.successor_report.accepted
            and self.extension_report.accepted
        )

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "predecessor": self.predecessor.to_json(),
            "successor": self.successor.to_json(),
            "predecessor_report": self.predecessor_report.to_json(),
            "successor_report": self.successor_report.to_json(),
            "extension_report": self.extension_report.to_json(),
            "claim_boundary": {
                "canonical_compact_transformer_package": True,
                "zero_lora_conservative_extension": True,
                "actual_trained_language_model_successor": False,
                "new_lean_task_certified": False,
                "kl_qre_evidence_certified": False,
                "promotion_completed": False,
                "independent_replay_completed": False,
                "phase10_exit_closed": False,
            },
        }

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["reference_hash"] = canonical_json_hash(value)
        return value


def build_phase10_reference_fixture(output_root: Path) -> Phase10ReferenceFixture:
    root = output_root.resolve(strict=False)
    if root.exists():
        raise FileExistsError(f"reference output already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    predecessor_root = root / "predecessor"
    successor_root = root / "zero_lora_extension"
    predecessor = build_reference_predecessor_package(predecessor_root)
    successor = build_zero_lora_extension_package(predecessor_root, successor_root)
    predecessor_report = validate_model_package(predecessor_root)
    successor_report = validate_model_package(successor_root)
    extension_report = validate_conservative_extension(predecessor_root, successor_root)
    return Phase10ReferenceFixture(
        predecessor=predecessor,
        successor=successor,
        predecessor_report=predecessor_report,
        successor_report=successor_report,
        extension_report=extension_report,
    )


__all__ = ["Phase10ReferenceFixture", "build_phase10_reference_fixture"]
