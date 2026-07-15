from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime.schema._common import require_schema_id, require_string, require_structural_integer, strict_object
from rcp_rclm_runtime.successor._record_common import CommandKind, PHASE6_COMMAND_SCHEMA_ID, WorkingDirectoryPolicy, literal, require_exact_set, require_nonnegative, required_bool, required_hash, required_integer

@dataclass(frozen=True, slots=True)
class Phase6CommandRecord:
    sequence_number: int
    command_kind: CommandKind
    argv: Sequence[str]
    working_directory_policy: WorkingDirectoryPolicy
    stdin_hash: str
    stdout_hash: str
    stderr_hash: str
    exit_code: int
    internal_executor: bool

    schema_id: ClassVar[str] = PHASE6_COMMAND_SCHEMA_ID

    def __post_init__(self) -> None:
        require_nonnegative(self.sequence_number, "phase6_command.sequence_number")
        require_exact_set(
            self.command_kind,
            {
                "copy_payload",
                "write_file",
                "delete_file",
                "build_rollback",
                "verify_rollback",
                "build_package",
            },
            "phase6_command.command_kind",
        )
        argv = tuple(self.argv)
        object.__setattr__(self, "argv", argv)
        if not argv:
            raise SchemaValidationError(
                "phase6_command.argv",
                "command argv must be nonempty",
            )
        for index, item in enumerate(argv):
            require_string(item, f"phase6_command.argv[{index}]")
        require_exact_set(
            self.working_directory_policy,
            {"isolated_workspace", "candidate_package_staging"},
            "phase6_command.working_directory_policy",
        )
        for name, value in (
            ("stdin_hash", self.stdin_hash),
            ("stdout_hash", self.stdout_hash),
            ("stderr_hash", self.stderr_hash),
        ):
            validate_hash256(value, f"phase6_command.{name}")
        if isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int):
            raise SchemaValidationError(
                "phase6_command.exit_code",
                "expected an integer",
            )
        if not isinstance(self.internal_executor, bool):
            raise SchemaValidationError(
                "phase6_command.internal_executor",
                "expected a Boolean",
            )

    @property
    def command_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "phase6_command",
    ) -> Phase6CommandRecord:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "sequence_number",
                "command_kind",
                "argv",
                "working_directory_policy",
                "stdin_hash",
                "stdout_hash",
                "stderr_hash",
                "exit_code",
                "internal_executor",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        argv_raw = obj["argv"]
        if not isinstance(argv_raw, list):
            raise SchemaValidationError(f"{path}.argv", "expected an array")
        return cls(
            sequence_number=require_structural_integer(
                obj["sequence_number"], f"{path}.sequence_number", minimum=0
            ),
            command_kind=literal(
                obj["command_kind"],
                f"{path}.command_kind",
                {
                    "copy_payload",
                    "write_file",
                    "delete_file",
                    "build_rollback",
                    "verify_rollback",
                    "build_package",
                },
            ),
            argv=tuple(
                require_string(item, f"{path}.argv[{index}]")
                for index, item in enumerate(argv_raw)
            ),
            working_directory_policy=literal(
                obj["working_directory_policy"],
                f"{path}.working_directory_policy",
                {"isolated_workspace", "candidate_package_staging"},
            ),
            stdin_hash=required_hash(
                obj["stdin_hash"], f"{path}.stdin_hash"
            ),
            stdout_hash=required_hash(
                obj["stdout_hash"], f"{path}.stdout_hash"
            ),
            stderr_hash=required_hash(
                obj["stderr_hash"], f"{path}.stderr_hash"
            ),
            exit_code=required_integer(obj["exit_code"], f"{path}.exit_code"),
            internal_executor=required_bool(
                obj["internal_executor"], f"{path}.internal_executor"
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "sequence_number": self.sequence_number,
            "command_kind": self.command_kind,
            "argv": list(self.argv),
            "working_directory_policy": self.working_directory_policy,
            "stdin_hash": self.stdin_hash,
            "stdout_hash": self.stdout_hash,
            "stderr_hash": self.stderr_hash,
            "exit_code": self.exit_code,
            "internal_executor": self.internal_executor,
        }
