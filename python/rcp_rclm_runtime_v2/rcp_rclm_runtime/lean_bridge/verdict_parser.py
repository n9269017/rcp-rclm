from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import validate_hash256
from rcp_rclm_runtime.canonical.json import load_json_text_strict
from rcp_rclm_runtime.errors import RuntimeValidationError, SchemaValidationError
from rcp_rclm_runtime.lean_bridge.source_generator import (
    LEAN_VERDICT_MARKER_PREFIX,
    LEAN_VERDICT_SCHEMA_ID,
    SOURCE_GENERATOR_VERSION,
)
from rcp_rclm_runtime.schema._common import require_schema_id, require_string, strict_object


class LeanVerdictParseError(RuntimeValidationError):
    def __init__(self, detail: str) -> None:
        super().__init__("LEAN_VERDICT_PARSE_FAILED", "lean_stdout", detail)


@dataclass(frozen=True, slots=True)
class LeanReferenceVerdict:
    case_id: str
    scope: str
    rcp_accepted: bool
    rclm_accepted: bool
    packet_hash: str
    theorem_surface_hash: str
    source_generator_version: str

    schema_id: ClassVar[str] = LEAN_VERDICT_SCHEMA_ID

    def __post_init__(self) -> None:
        require_string(self.case_id, "lean_reference_verdict.case_id")
        if self.scope not in {"gate_b_classical", "gate_c_diagonal_quantum"}:
            raise SchemaValidationError(
                "lean_reference_verdict.scope",
                f"unsupported bridge scope: {self.scope}",
            )
        if not isinstance(self.rcp_accepted, bool):
            raise SchemaValidationError(
                "lean_reference_verdict.rcp_accepted",
                "expected a Boolean",
            )
        if not isinstance(self.rclm_accepted, bool):
            raise SchemaValidationError(
                "lean_reference_verdict.rclm_accepted",
                "expected a Boolean",
            )
        validate_hash256(self.packet_hash, "lean_reference_verdict.packet_hash")
        validate_hash256(
            self.theorem_surface_hash,
            "lean_reference_verdict.theorem_surface_hash",
        )
        if self.source_generator_version != SOURCE_GENERATOR_VERSION:
            raise SchemaValidationError(
                "lean_reference_verdict.source_generator_version",
                f"expected {SOURCE_GENERATOR_VERSION}",
            )

    @property
    def layers_agree(self) -> bool:
        return self.rcp_accepted == self.rclm_accepted

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "lean_reference_verdict",
    ) -> LeanReferenceVerdict:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "case_id",
                "scope",
                "rcp_accepted",
                "rclm_accepted",
                "packet_hash",
                "theorem_surface_hash",
                "source_generator_version",
            },
        )
        require_schema_id(obj["schema_id"], f"{path}.schema_id", cls.schema_id)
        rcp_accepted = obj["rcp_accepted"]
        rclm_accepted = obj["rclm_accepted"]
        if not isinstance(rcp_accepted, bool):
            raise SchemaValidationError(f"{path}.rcp_accepted", "expected a Boolean")
        if not isinstance(rclm_accepted, bool):
            raise SchemaValidationError(f"{path}.rclm_accepted", "expected a Boolean")
        return cls(
            case_id=require_string(obj["case_id"], f"{path}.case_id"),
            scope=require_string(obj["scope"], f"{path}.scope"),
            rcp_accepted=rcp_accepted,
            rclm_accepted=rclm_accepted,
            packet_hash=require_string(obj["packet_hash"], f"{path}.packet_hash"),
            theorem_surface_hash=require_string(
                obj["theorem_surface_hash"],
                f"{path}.theorem_surface_hash",
            ),
            source_generator_version=require_string(
                obj["source_generator_version"],
                f"{path}.source_generator_version",
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "case_id": self.case_id,
            "scope": self.scope,
            "rcp_accepted": self.rcp_accepted,
            "rclm_accepted": self.rclm_accepted,
            "layers_agree": self.layers_agree,
            "packet_hash": self.packet_hash,
            "theorem_surface_hash": self.theorem_surface_hash,
            "source_generator_version": self.source_generator_version,
        }


def parse_lean_reference_verdict(stdout: bytes) -> LeanReferenceVerdict:
    try:
        text = stdout.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise LeanVerdictParseError(f"Lean stdout is not valid UTF-8: {exc}") from exc
    payloads = [
        line[len(LEAN_VERDICT_MARKER_PREFIX) :]
        for line in text.splitlines()
        if line.startswith(LEAN_VERDICT_MARKER_PREFIX)
    ]
    if not payloads:
        raise LeanVerdictParseError("no structured verdict marker was emitted")
    if len(payloads) != 1:
        raise LeanVerdictParseError(
            f"expected one structured verdict marker, found {len(payloads)}"
        )
    try:
        parsed = load_json_text_strict(payloads[0], require_canonical=True)
        return LeanReferenceVerdict.from_json(parsed)
    except RuntimeValidationError as exc:
        raise LeanVerdictParseError(str(exc)) from exc
