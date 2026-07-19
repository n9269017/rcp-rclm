from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_string, strict_object

from rcp_rclm_runtime_v3.contract.common import (
    ALLOWED_TASK_PARTITIONS,
    CERTIFICATION_SCHEMA_ID,
    FRONTIER_SCHEMA_ID,
    LEDGER_SCHEMA_ID,
    SELECTED_TASK_CLASS,
    SELECTED_VERIFIER_KIND,
    TASK_SCHEMA_ID,
    TaskPartition,
    cast_task_partition,
    normalize_sorted_unique_strings,
    require_hash,
    require_schema,
    require_string_array,
)


@dataclass(frozen=True, slots=True)
class TaskRecord:
    task_id: str
    task_class: str
    prompt_hash: str
    verifier_spec_hash: str
    partition: TaskPartition

    schema_id: ClassVar[str] = TASK_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.task_id, "phase9.task.task_id")
        if self.task_class != SELECTED_TASK_CLASS:
            raise SchemaValidationError(
                "phase9.task.task_class",
                f"expected selected task class {SELECTED_TASK_CLASS}",
            )
        require_hash(self.prompt_hash, "phase9.task.prompt_hash")
        require_hash(self.verifier_spec_hash, "phase9.task.verifier_spec_hash")
        if self.partition not in ALLOWED_TASK_PARTITIONS:
            raise SchemaValidationError("phase9.task.partition", "unsupported task partition")

    @classmethod
    def from_json(cls, value: object) -> TaskRecord:
        obj = strict_object(
            value,
            "phase9.task",
            {"schema_id", "task_id", "task_class", "prompt_hash", "verifier_spec_hash", "partition"},
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase9.task.schema_id")
        partition = require_string(obj["partition"], "phase9.task.partition")
        if partition not in ALLOWED_TASK_PARTITIONS:
            raise SchemaValidationError("phase9.task.partition", "unsupported task partition")
        return cls(
            task_id=require_string(obj["task_id"], "phase9.task.task_id"),
            task_class=require_string(obj["task_class"], "phase9.task.task_class"),
            prompt_hash=require_hash(obj["prompt_hash"], "phase9.task.prompt_hash"),
            verifier_spec_hash=require_hash(
                obj["verifier_spec_hash"], "phase9.task.verifier_spec_hash"
            ),
            partition=cast_task_partition(partition),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "task_id": self.task_id,
            "task_class": self.task_class,
            "prompt_hash": self.prompt_hash,
            "verifier_spec_hash": self.verifier_spec_hash,
            "partition": self.partition,
        }


@dataclass(frozen=True, slots=True)
class CertificationRecord:
    task_id: str
    model_identity_hash: str
    verifier_report_hash: str
    verified_output_hash: str
    verifier_kind: str = SELECTED_VERIFIER_KIND

    schema_id: ClassVar[str] = CERTIFICATION_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.task_id, "phase9.certification.task_id")
        require_hash(self.model_identity_hash, "phase9.certification.model_identity_hash")
        require_hash(self.verifier_report_hash, "phase9.certification.verifier_report_hash")
        require_hash(self.verified_output_hash, "phase9.certification.verified_output_hash")
        if self.verifier_kind != SELECTED_VERIFIER_KIND:
            raise SchemaValidationError(
                "phase9.certification.verifier_kind",
                f"expected {SELECTED_VERIFIER_KIND}",
            )

    @classmethod
    def from_json(cls, value: object) -> CertificationRecord:
        obj = strict_object(
            value,
            "phase9.certification",
            {
                "schema_id",
                "task_id",
                "model_identity_hash",
                "verifier_report_hash",
                "verified_output_hash",
                "verifier_kind",
            },
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase9.certification.schema_id")
        return cls(
            task_id=require_string(obj["task_id"], "phase9.certification.task_id"),
            model_identity_hash=require_hash(
                obj["model_identity_hash"], "phase9.certification.model_identity_hash"
            ),
            verifier_report_hash=require_hash(
                obj["verifier_report_hash"], "phase9.certification.verifier_report_hash"
            ),
            verified_output_hash=require_hash(
                obj["verified_output_hash"], "phase9.certification.verified_output_hash"
            ),
            verifier_kind=require_string(
                obj["verifier_kind"], "phase9.certification.verifier_kind"
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "task_id": self.task_id,
            "model_identity_hash": self.model_identity_hash,
            "verifier_report_hash": self.verifier_report_hash,
            "verified_output_hash": self.verified_output_hash,
            "verifier_kind": self.verifier_kind,
        }


@dataclass(frozen=True, slots=True)
class CapabilityFrontier:
    task_ids: Sequence[str]

    schema_id: ClassVar[str] = FRONTIER_SCHEMA_ID

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "task_ids",
            normalize_sorted_unique_strings(tuple(self.task_ids), "phase9.frontier.task_ids"),
        )

    @property
    def frontier_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(cls, value: object) -> CapabilityFrontier:
        obj = strict_object(value, "phase9.frontier", {"schema_id", "task_ids"})
        require_schema(obj["schema_id"], cls.schema_id, "phase9.frontier.schema_id")
        return cls(task_ids=require_string_array(obj["task_ids"], "phase9.frontier.task_ids"))

    def to_json(self) -> dict[str, object]:
        return {"schema_id": self.schema_id, "task_ids": list(self.task_ids)}


@dataclass(frozen=True, slots=True)
class TaskLedger:
    tasks: Sequence[TaskRecord]
    certifications: Sequence[CertificationRecord]

    schema_id: ClassVar[str] = LEDGER_SCHEMA_ID

    def __post_init__(self) -> None:
        task_tuple = tuple(self.tasks)
        certification_tuple = tuple(self.certifications)
        task_ids = tuple(task.task_id for task in task_tuple)
        certification_ids = tuple(record.task_id for record in certification_tuple)
        if len(set(task_ids)) != len(task_ids):
            raise SchemaValidationError("phase9.ledger.tasks", "duplicate task identifier")
        if len(set(certification_ids)) != len(certification_ids):
            raise SchemaValidationError(
                "phase9.ledger.certifications", "duplicate certification task identifier"
            )
        ordered_tasks = tuple(sorted(task_tuple, key=lambda item: item.task_id.encode("utf-8")))
        ordered_certifications = tuple(
            sorted(certification_tuple, key=lambda item: item.task_id.encode("utf-8"))
        )
        if task_tuple != ordered_tasks:
            raise SchemaValidationError("phase9.ledger.tasks", "tasks must be sorted by task_id")
        if certification_tuple != ordered_certifications:
            raise SchemaValidationError(
                "phase9.ledger.certifications", "certifications must be sorted by task_id"
            )
        unknown = sorted(set(certification_ids) - set(task_ids))
        if unknown:
            raise SchemaValidationError(
                "phase9.ledger.certifications",
                f"certification references unknown task: {', '.join(unknown)}",
            )
        object.__setattr__(self, "tasks", task_tuple)
        object.__setattr__(self, "certifications", certification_tuple)

    @property
    def task_by_id(self) -> Mapping[str, TaskRecord]:
        return {task.task_id: task for task in self.tasks}

    @property
    def certification_by_task_id(self) -> Mapping[str, CertificationRecord]:
        return {record.task_id: record for record in self.certifications}

    @property
    def ledger_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(cls, value: object) -> TaskLedger:
        obj = strict_object(
            value, "phase9.ledger", {"schema_id", "tasks", "certifications"}
        )
        require_schema(obj["schema_id"], cls.schema_id, "phase9.ledger.schema_id")
        raw_tasks = obj["tasks"]
        raw_certifications = obj["certifications"]
        if not isinstance(raw_tasks, Sequence) or isinstance(raw_tasks, (str, bytes, bytearray)):
            raise SchemaValidationError("phase9.ledger.tasks", "expected an array")
        if not isinstance(raw_certifications, Sequence) or isinstance(
            raw_certifications, (str, bytes, bytearray)
        ):
            raise SchemaValidationError("phase9.ledger.certifications", "expected an array")
        return cls(
            tasks=tuple(TaskRecord.from_json(item) for item in raw_tasks),
            certifications=tuple(
                CertificationRecord.from_json(item) for item in raw_certifications
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "tasks": [task.to_json() for task in self.tasks],
            "certifications": [record.to_json() for record in self.certifications],
        }


__all__ = ["CapabilityFrontier", "CertificationRecord", "TaskLedger", "TaskRecord"]
