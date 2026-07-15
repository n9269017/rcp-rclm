from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.schema._common import require_schema_id, require_string, strict_object
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.successor._record_common import PHASE6_ENVIRONMENT_SCHEMA_ID, frozen_hash_map

@dataclass(frozen=True, slots=True)
class Phase6EnvironmentRecord:
    realizer_policy_id: str
    python_implementation: str
    python_version: str
    os_name: str
    platform_system: str
    platform_machine: str
    filesystem_encoding: str
    environment_value_hashes: FrozenHashMap

    schema_id: ClassVar[str] = PHASE6_ENVIRONMENT_SCHEMA_ID

    def __post_init__(self) -> None:
        for name, value in (
            ("realizer_policy_id", self.realizer_policy_id),
            ("python_implementation", self.python_implementation),
            ("python_version", self.python_version),
            ("os_name", self.os_name),
            ("platform_system", self.platform_system),
            ("platform_machine", self.platform_machine),
            ("filesystem_encoding", self.filesystem_encoding),
        ):
            require_string(value, f"phase6_environment.{name}")

    @property
    def environment_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase6_environment",
    ) -> Phase6EnvironmentRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "realizer_policy_id",
                "python_implementation",
                "python_version",
                "os_name",
                "platform_system",
                "platform_machine",
                "filesystem_encoding",
                "environment_value_hashes",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        return cls(
            realizer_policy_id=require_string(
                obj["realizer_policy_id"], f"{path}.realizer_policy_id"
            ),
            python_implementation=require_string(
                obj["python_implementation"], f"{path}.python_implementation"
            ),
            python_version=require_string(
                obj["python_version"], f"{path}.python_version"
            ),
            os_name=require_string(obj["os_name"], f"{path}.os_name"),
            platform_system=require_string(
                obj["platform_system"], f"{path}.platform_system"
            ),
            platform_machine=require_string(
                obj["platform_machine"], f"{path}.platform_machine"
            ),
            filesystem_encoding=require_string(
                obj["filesystem_encoding"], f"{path}.filesystem_encoding"
            ),
            environment_value_hashes=frozen_hash_map(
                obj["environment_value_hashes"],
                f"{path}.environment_value_hashes",
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "realizer_policy_id": self.realizer_policy_id,
            "python_implementation": self.python_implementation,
            "python_version": self.python_version,
            "os_name": self.os_name,
            "platform_system": self.platform_system,
            "platform_machine": self.platform_machine,
            "filesystem_encoding": self.filesystem_encoding,
            "environment_value_hashes": self.environment_value_hashes.to_json(),
        }
