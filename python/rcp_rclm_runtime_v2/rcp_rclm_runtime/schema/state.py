from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Final, Literal, Mapping, TypeAlias

from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.mathematics.diagonal_quantum import (
    DiagonalDensityRecord,
    quantum_state_density,
)
from rcp_rclm_runtime.schema._common import (
    TypedArtifactRecord,
    require_schema_id,
    require_string,
    strict_object,
)

ClassicalBinaryStateName: TypeAlias = Literal["outside", "initial", "target"]
QuantumStateName: TypeAlias = Literal["outside", "source", "target"]

CLASSICAL_BINARY_STATE_SCHEMA_ID: Final[str] = "gate_b.binary_state.v2"
QUANTUM_STATE_SCHEMA_ID: Final[str] = "gate_c.quantum_state.v2"
RCLM_STATE_SCHEMA_ID: Final[str] = "rclm.state.v2"


@dataclass(frozen=True, slots=True)
class ClassicalBinaryStateRecord:
    state: ClassicalBinaryStateName

    schema_id: ClassVar[str] = CLASSICAL_BINARY_STATE_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.state not in {"outside", "initial", "target"}:
            raise SchemaValidationError("binary_state.state", f"unknown state: {self.state}")

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "binary_state",
    ) -> ClassicalBinaryStateRecord:
        obj = strict_object(value, path, {"schema_id", "state"})
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        state = require_string(obj["state"], f"{path}.state")
        if state not in {"outside", "initial", "target"}:
            raise SchemaValidationError(f"{path}.state", f"unknown binary state: {state}")
        return cls(state=state)

    def to_json(self) -> dict[str, object]:
        return {"schema_id": self.schema_id, "state": self.state}


@dataclass(frozen=True, slots=True)
class QuantumStateRecord:
    state: QuantumStateName
    density: DiagonalDensityRecord

    schema_id: ClassVar[str] = QUANTUM_STATE_SCHEMA_ID

    def __post_init__(self) -> None:
        if self.state not in {"outside", "source", "target"}:
            raise SchemaValidationError("quantum_state.state", f"unknown state: {self.state}")
        expected = quantum_state_density(self.state)
        if self.density != expected:
            raise SchemaValidationError(
                "quantum_state.density",
                "density must equal the selected formal state-density mapping",
            )

    @classmethod
    def canonical(cls, state: QuantumStateName) -> QuantumStateRecord:
        return cls(state=state, density=quantum_state_density(state))

    @classmethod
    def from_json(cls, value: object, path: str = "quantum_state") -> QuantumStateRecord:
        obj = strict_object(value, path, {"schema_id", "state", "density"})
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        state = require_string(obj["state"], f"{path}.state")
        if state not in {"outside", "source", "target"}:
            raise SchemaValidationError(f"{path}.state", f"unknown quantum state: {state}")
        density = DiagonalDensityRecord.from_json(obj["density"], f"{path}.density")
        return cls(state=state, density=density)

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "state": self.state,
            "density": self.density.to_json(),
        }


RcpStateRecord: TypeAlias = ClassicalBinaryStateRecord | QuantumStateRecord


def parse_rcp_state(value: object, path: str = "rcp_state") -> RcpStateRecord:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, "expected an object")
    schema_id = value.get("schema_id")
    if schema_id == ClassicalBinaryStateRecord.schema_id:
        return ClassicalBinaryStateRecord.from_json(value, path)
    if schema_id == QuantumStateRecord.schema_id:
        return QuantumStateRecord.from_json(value, path)
    raise SchemaValidationError(f"{path}.schema_id", f"unknown RCP state schema: {schema_id}")


@dataclass(frozen=True, slots=True)
class RclmStateRecord:
    core: RcpStateRecord
    language: TypedArtifactRecord
    world_reference: TypedArtifactRecord
    human_reference: TypedArtifactRecord
    definitiveness: TypedArtifactRecord
    ambiguity: TypedArtifactRecord
    memory: TypedArtifactRecord
    verifier: TypedArtifactRecord
    resources: TypedArtifactRecord
    self_model: TypedArtifactRecord

    schema_id: ClassVar[str] = RCLM_STATE_SCHEMA_ID

    @classmethod
    def from_json(cls, value: object, path: str = "rclm_state") -> RclmStateRecord:
        fields = {
            "schema_id",
            "core",
            "language",
            "world_reference",
            "human_reference",
            "definitiveness",
            "ambiguity",
            "memory",
            "verifier",
            "resources",
            "self_model",
        }
        obj = strict_object(value, path, fields)
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            core=parse_rcp_state(obj["core"], f"{path}.core"),
            language=TypedArtifactRecord.from_json(obj["language"], f"{path}.language"),
            world_reference=TypedArtifactRecord.from_json(
                obj["world_reference"], f"{path}.world_reference"
            ),
            human_reference=TypedArtifactRecord.from_json(
                obj["human_reference"], f"{path}.human_reference"
            ),
            definitiveness=TypedArtifactRecord.from_json(
                obj["definitiveness"], f"{path}.definitiveness"
            ),
            ambiguity=TypedArtifactRecord.from_json(obj["ambiguity"], f"{path}.ambiguity"),
            memory=TypedArtifactRecord.from_json(obj["memory"], f"{path}.memory"),
            verifier=TypedArtifactRecord.from_json(obj["verifier"], f"{path}.verifier"),
            resources=TypedArtifactRecord.from_json(obj["resources"], f"{path}.resources"),
            self_model=TypedArtifactRecord.from_json(obj["self_model"], f"{path}.self_model"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "core": self.core.to_json(),
            "language": self.language.to_json(),
            "world_reference": self.world_reference.to_json(),
            "human_reference": self.human_reference.to_json(),
            "definitiveness": self.definitiveness.to_json(),
            "ambiguity": self.ambiguity.to_json(),
            "memory": self.memory.to_json(),
            "verifier": self.verifier.to_json(),
            "resources": self.resources.to_json(),
            "self_model": self.self_model.to_json(),
        }
