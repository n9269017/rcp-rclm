from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Final, Literal, Mapping, TypeAlias

from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.mathematics.diagonal_quantum import SelectedChannelRecord
from rcp_rclm_runtime.schema._common import (
    TypedArtifactRecord,
    require_schema_id,
    require_string,
    strict_object,
)

ClassicalBinaryUpdateName: TypeAlias = Literal["stay", "improve"]
QuantumUpdateName: TypeAlias = Literal["stay", "swap"]

CLASSICAL_BINARY_UPDATE_SCHEMA_ID: Final[str] = "gate_b.binary_update.v2"
QUANTUM_UPDATE_SCHEMA_ID: Final[str] = "gate_c.quantum_update.v2"
RCLM_UPDATE_SCHEMA_ID: Final[str] = "rclm.update.v2"


@dataclass(frozen=True, slots=True)
class ClassicalBinaryUpdateRecord:
    update: ClassicalBinaryUpdateName

    schema_id: ClassVar[str] = CLASSICAL_BINARY_UPDATE_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.update not in {"stay", "improve"}:
            raise SchemaValidationError("binary_update.update", f"unknown update: {self.update}")

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "binary_update",
    ) -> ClassicalBinaryUpdateRecord:
        obj = strict_object(value, path, {"schema_id", "update"})
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        update = require_string(obj["update"], f"{path}.update")
        if update not in {"stay", "improve"}:
            raise SchemaValidationError(f"{path}.update", f"unknown binary update: {update}")
        return cls(update=update)

    def to_json(self) -> dict[str, object]:
        return {"schema_id": self.schema_id, "update": self.update}


@dataclass(frozen=True, slots=True)
class QuantumUpdateRecord:
    update: QuantumUpdateName
    channel: SelectedChannelRecord

    schema_id: ClassVar[str] = QUANTUM_UPDATE_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.update not in {"stay", "swap"}:
            raise SchemaValidationError("quantum_update.update", f"unknown update: {self.update}")
        expected_kind = "identity" if self.update == "stay" else "basis_swap"
        if self.channel.kind != expected_kind:
            raise SchemaValidationError(
                "quantum_update.channel",
                f"update {self.update} requires selected channel {expected_kind}",
            )

    @classmethod
    def canonical(cls, update: QuantumUpdateName) -> QuantumUpdateRecord:
        if update == "stay":
            return cls(update="stay", channel=SelectedChannelRecord.identity())
        if update == "swap":
            return cls(update="swap", channel=SelectedChannelRecord.basis_swap())
        raise SchemaValidationError("quantum_update.update", f"unknown update: {update}")

    @classmethod
    def from_json(cls, value: object, path: str = "quantum_update") -> QuantumUpdateRecord:
        obj = strict_object(value, path, {"schema_id", "update", "channel"})
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        update = require_string(obj["update"], f"{path}.update")
        if update not in {"stay", "swap"}:
            raise SchemaValidationError(f"{path}.update", f"unknown quantum update: {update}")
        channel = SelectedChannelRecord.from_json(obj["channel"], f"{path}.channel")
        return cls(update=update, channel=channel)

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "update": self.update,
            "channel": self.channel.to_json(),
        }


RcpUpdateRecord: TypeAlias = ClassicalBinaryUpdateRecord | QuantumUpdateRecord


def parse_rcp_update(value: object, path: str = "rcp_update") -> RcpUpdateRecord:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, "expected an object")
    schema_id = value.get("schema_id")
    if schema_id == ClassicalBinaryUpdateRecord.schema_id:
        return ClassicalBinaryUpdateRecord.from_json(value, path)
    if schema_id == QuantumUpdateRecord.schema_id:
        return QuantumUpdateRecord.from_json(value, path)
    raise SchemaValidationError(f"{path}.schema_id", f"unknown RCP update schema: {schema_id}")


@dataclass(frozen=True, slots=True)
class RclmUpdateRecord:
    core: RcpUpdateRecord
    parameters: TypedArtifactRecord
    architecture: TypedArtifactRecord
    memory: TypedArtifactRecord
    verifier: TypedArtifactRecord
    semantics: TypedArtifactRecord
    tools: TypedArtifactRecord
    resources: TypedArtifactRecord

    schema_id: ClassVar[str] = RCLM_UPDATE_SCHEMA_ID

    @classmethod
    def from_json(cls, value: object, path: str = "rclm_update") -> RclmUpdateRecord:
        fields = {
            "schema_id",
            "core",
            "parameters",
            "architecture",
            "memory",
            "verifier",
            "semantics",
            "tools",
            "resources",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            core=parse_rcp_update(obj["core"], f"{path}.core"),
            parameters=TypedArtifactRecord.from_json(obj["parameters"], f"{path}.parameters"),
            architecture=TypedArtifactRecord.from_json(
                obj["architecture"], f"{path}.architecture"
            ),
            memory=TypedArtifactRecord.from_json(obj["memory"], f"{path}.memory"),
            verifier=TypedArtifactRecord.from_json(obj["verifier"], f"{path}.verifier"),
            semantics=TypedArtifactRecord.from_json(obj["semantics"], f"{path}.semantics"),
            tools=TypedArtifactRecord.from_json(obj["tools"], f"{path}.tools"),
            resources=TypedArtifactRecord.from_json(obj["resources"], f"{path}.resources"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "core": self.core.to_json(),
            "parameters": self.parameters.to_json(),
            "architecture": self.architecture.to_json(),
            "memory": self.memory.to_json(),
            "verifier": self.verifier.to_json(),
            "semantics": self.semantics.to_json(),
            "tools": self.tools.to_json(),
            "resources": self.resources.to_json(),
        }
