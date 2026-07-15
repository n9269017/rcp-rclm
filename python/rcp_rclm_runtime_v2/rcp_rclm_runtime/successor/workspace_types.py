from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import SemanticFileRecord
from rcp_rclm_runtime.schema.state import RclmStateRecord
from rcp_rclm_runtime.successor.records import (
    Phase6CommandRecord,
    Phase6PredecessorManifestRecord,
    Phase6ReasonCode,
)


class Phase6WorkspaceError(ValueError):
    __slots__ = ("reason_code", "detail")

    def __init__(self, reason_code: Phase6ReasonCode, detail: str) -> None:
        super().__init__(reason_code.value, detail)
        self.reason_code = reason_code
        self.detail = detail

    def __str__(self) -> str:
        return f"{self.reason_code.value}: {self.detail}"


@dataclass(frozen=True, slots=True)
class PayloadMeasurement:
    records: Sequence[SemanticFileRecord]
    tree_hash: str
    file_count: int
    total_bytes: int


@dataclass(frozen=True, slots=True)
class LoadedPredecessorPackage:
    root: Path
    payload_root: Path
    manifest: Phase6PredecessorManifestRecord
    measurement: PayloadMeasurement
    state: RclmStateRecord


@dataclass(frozen=True, slots=True)
class OperationApplication:
    commands: Sequence[Phase6CommandRecord]
    bytes_read: int
    bytes_written: int
