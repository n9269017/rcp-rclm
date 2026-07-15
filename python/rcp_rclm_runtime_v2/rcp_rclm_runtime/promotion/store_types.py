from __future__ import annotations
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Final, Literal
from rcp_rclm_runtime.canonical.hashing import build_tree_records, canonical_json_hash, semantic_tree_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.errors import CanonicalizationError, SchemaValidationError
from rcp_rclm_runtime.generator.reference import reference_generator_input
from rcp_rclm_runtime.schema.state import ClassicalBinaryStateRecord, RclmStateRecord
from rcp_rclm_runtime.successor.filesystem import atomic_write, safe_payload_path
from rcp_rclm_runtime.successor.package_builder import verify_candidate_package
from rcp_rclm_runtime.successor.policies import STATE_PATH
from rcp_rclm_runtime.successor.records import Phase6CandidateManifestRecord, Phase6PackageReport, Phase6PredecessorManifestRecord, Phase6SelectionRecord
from rcp_rclm_runtime.successor.workspace import LoadedPredecessorPackage, Phase6WorkspaceError, load_predecessor_package, measure_payload_tree, write_canonical_json
from rcp_rclm_runtime.promotion.records import LedgerEvent, Phase7ActivePointerRecord, Phase7AttemptReport, Phase7ControllerPolicyRecord, Phase7ImmutablePackageManifestRecord, Phase7LedgerEntryRecord, Phase7ReasonCode
ACTIVE_POINTER_NAME: Final[str] = 'active.json'
PACKAGES_DIRECTORY_NAME: Final[str] = 'packages'
LEDGER_DIRECTORY_NAME: Final[str] = 'ledger'
RUNS_DIRECTORY_NAME: Final[str] = 'runs'
LOCK_DIRECTORY_NAME: Final[str] = '.controller-lock'

class Phase7StoreError(ValueError):
    __slots__ = ('reason_code', 'detail')

    def __init__(self, reason_code: Phase7ReasonCode, detail: str) -> None:
        super().__init__(reason_code.value, detail)
        self.reason_code = reason_code
        self.detail = detail

    def __str__(self) -> str:
        return f'{self.reason_code.value}: {self.detail}'
@dataclass(frozen=True, slots=True)
class Phase7StoreSnapshot:
    store_root: Path
    pointer: Phase7ActivePointerRecord
    package_root: Path
    package_manifest: Phase7ImmutablePackageManifestRecord
    predecessor_root: Path
    predecessor: LoadedPredecessorPackage
    ledger_head: Phase7LedgerEntryRecord
@dataclass(frozen=True, slots=True)
class Phase7PromotionCommit:
    snapshot: Phase7StoreSnapshot
    ledger_entry: Phase7LedgerEntryRecord
    package_manifest: Phase7ImmutablePackageManifestRecord
class Phase7StoreLock:
    __slots__ = ('_store_root', '_owner_id', '_lock_root', '_acquired')

    def __init__(self, store_root: Path, owner_id: str) -> None:
        self._store_root = store_root.resolve(strict=True)
        self._owner_id = owner_id
        self._lock_root = self._store_root / LOCK_DIRECTORY_NAME
        self._acquired = False

    def __enter__(self) -> Phase7StoreLock:
        try:
            self._lock_root.mkdir(parents=False, exist_ok=False)
            write_canonical_json(self._lock_root / 'owner.json', {'schema_id': 'runtime.phase7_store_lock.v2', 'owner_id': self._owner_id})
        except FileExistsError as exc:
            raise Phase7StoreError(Phase7ReasonCode.STORE_LOCKED, 'another promotion controller holds the store lock') from exc
        except OSError as exc:
            raise Phase7StoreError(Phase7ReasonCode.ACTIVE_STORE_INVALID, f'could not acquire controller store lock: {exc}') from exc
        self._acquired = True
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None) -> Literal[False]:
        if self._acquired:
            owner = self._lock_root / 'owner.json'
            if owner.exists():
                owner.unlink()
            self._lock_root.rmdir()
            self._acquired = False
        return False
