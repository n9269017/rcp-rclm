from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase16.constants import ARCHIVE_KINDS


@dataclass(slots=True)
class ExperimentArchive:
    bootstrap_hash: str
    records: list[dict[str, object]] = field(default_factory=list)
    schema_id: str = "runtime.v4.phase16.experiment_archive.v1"
    _root_hash: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        validate_hash256(self.bootstrap_hash, "phase16.archive.bootstrap_hash")
        existing = list(self.records)
        self.records = []
        self._root_hash = self.bootstrap_hash
        for record in existing:
            self._append_existing(record)

    @property
    def root_hash(self) -> str:
        return self._root_hash

    def append(self, kind: str, payload: Mapping[str, object]) -> str:
        if kind not in ARCHIVE_KINDS:
            raise SchemaValidationError("phase16.archive.kind", f"unsupported kind: {kind}")
        sequence_number = len(self.records)
        base = {
            "schema_id": "runtime.v4.phase16.archive_record.v1",
            "sequence_number": sequence_number,
            "kind": kind,
            "parent_record_hash": self.root_hash,
            "payload_hash": canonical_json_hash(payload),
            "payload": dict(payload),
        }
        record = dict(base)
        record_hash = canonical_json_hash(base)
        record["record_hash"] = record_hash
        self.records.append(record)
        self._root_hash = record_hash
        return record_hash

    def _append_existing(self, record: Mapping[str, object]) -> None:
        expected_sequence = len(self.records)
        if record.get("sequence_number") != expected_sequence:
            raise SchemaValidationError("phase16.archive.sequence_number", "noncontiguous sequence")
        kind = record.get("kind")
        if kind not in ARCHIVE_KINDS:
            raise SchemaValidationError("phase16.archive.kind", f"unsupported kind: {kind}")
        if record.get("parent_record_hash") != self.root_hash:
            raise SchemaValidationError("phase16.archive.parent_record_hash", "hash-chain mismatch")
        payload = record.get("payload")
        if not isinstance(payload, Mapping):
            raise SchemaValidationError("phase16.archive.payload", "expected object")
        if record.get("payload_hash") != canonical_json_hash(payload):
            raise SchemaValidationError("phase16.archive.payload_hash", "payload hash mismatch")
        base = dict(record)
        observed = base.pop("record_hash", None)
        expected = canonical_json_hash(base)
        if observed != expected:
            raise SchemaValidationError("phase16.archive.record_hash", "record hash mismatch")
        self.records.append(dict(record))
        self._root_hash = expected

    def kinds_present(self) -> tuple[str, ...]:
        return tuple(sorted({str(record["kind"]) for record in self.records}))

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "bootstrap_hash": self.bootstrap_hash,
            "record_count": len(self.records),
            "records": list(self.records),
            "root_hash": self.root_hash,
            "kinds_present": list(self.kinds_present()),
            "untrusted_for_acceptance": True,
        }

    @classmethod
    def from_json(cls, value: object) -> ExperimentArchive:
        if not isinstance(value, Mapping):
            raise SchemaValidationError("phase16.archive", "expected object")
        if value.get("schema_id") != "runtime.v4.phase16.experiment_archive.v1":
            raise SchemaValidationError("phase16.archive.schema_id", "unexpected schema")
        records = value.get("records")
        if not isinstance(records, Sequence) or isinstance(records, (str, bytes, bytearray)):
            raise SchemaValidationError("phase16.archive.records", "expected array")
        archive = cls(
            bootstrap_hash=str(value.get("bootstrap_hash")),
            records=[dict(item) for item in records if isinstance(item, Mapping)],
        )
        if len(archive.records) != len(records):
            raise SchemaValidationError("phase16.archive.records", "record is not an object")
        if value.get("root_hash") != archive.root_hash:
            raise SchemaValidationError("phase16.archive.root_hash", "root hash mismatch")
        if value.get("record_count") != len(archive.records):
            raise SchemaValidationError("phase16.archive.record_count", "record count mismatch")
        if value.get("untrusted_for_acceptance") is not True:
            raise SchemaValidationError(
                "phase16.archive.untrusted_for_acceptance",
                "archive cannot authorize acceptance",
            )
        return archive


__all__ = ["ExperimentArchive"]
