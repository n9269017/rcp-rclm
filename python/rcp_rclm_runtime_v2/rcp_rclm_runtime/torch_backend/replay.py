from __future__ import annotations

import ast
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Final, Literal, cast

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
    sha256_hex,
    validate_hash256,
)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict
from rcp_rclm_runtime.checker.hardened import (
    Phase4HardenedRequest,
    check_hardened_transition,
)
from rcp_rclm_runtime.checker.integrity import (
    PackageIntegrityRecord,
    build_reference_package_integrity,
)
from rcp_rclm_runtime.checker.records import Phase3CheckerRequest
from rcp_rclm_runtime.checker.reference import (
    build_lean_reference_packet,
    canonical_rclm_certificate,
    reference_protected_distinctions,
    reference_resource_record,
    reference_trust_anchor,
)
from rcp_rclm_runtime.errors import CanonicalizationError, SchemaValidationError
from rcp_rclm_runtime.lean_bridge.packet import LeanReferencePacket
from rcp_rclm_runtime.lean_bridge.source_generator import generate_reference_source
from rcp_rclm_runtime.lean_bridge.source_guard import scan_source_bytes
from rcp_rclm_runtime.lean_bridge.verifier import (
    LeanBridgeVerificationEvidence,
    LeanBridgeVerificationReport,
)
from rcp_rclm_runtime.promotion.certificate import Phase7CertificateEvidence
from rcp_rclm_runtime.promotion.evaluator import evaluate_realized_candidate
from rcp_rclm_runtime.promotion.record_attempt import Phase7AttemptReport
from rcp_rclm_runtime.promotion.record_report import Phase7ControllerReport
from rcp_rclm_runtime.promotion.store import (
    load_active_phase7_store,
    verify_immutable_phase7_package,
)
from rcp_rclm_runtime.schema._common import (
    FrozenJson,
    FrozenJsonArray,
    FrozenJsonObject,
    freeze_json,
    require_string,
    require_structural_integer,
    strict_object,
    thaw_json,
)
from rcp_rclm_runtime.schema.verdict import FrozenHashMap
from rcp_rclm_runtime.successor.package_builder import (
    build_candidate_package,
    verify_candidate_package,
)
from rcp_rclm_runtime.successor.records import Phase6PackageReport, Phase6SelectionRecord
from rcp_rclm_runtime.successor.rollback_io import verify_rollback_snapshot_archive
from rcp_rclm_runtime.successor.workspace import load_predecessor_package, write_canonical_json
from rcp_rclm_runtime.torch_backend.adapter import (
    build_host_phase6_selection,
    validate_pytorch_proposal_output,
)
from rcp_rclm_runtime.torch_backend.exact_evaluator import evaluate_quantized_transition
from rcp_rclm_runtime.torch_backend.pilot_data import (
    pilot_heldout_evaluation_data,
    pilot_training_data_manifest,
)
from rcp_rclm_runtime.torch_backend.pilot_policy import (
    PYTORCH_PILOT_CONTROLLER_ENVIRONMENT_HASH,
    pytorch_pilot_phase7_budget,
    pytorch_pilot_phase7_policy,
)
from rcp_rclm_runtime.torch_backend.protocol import PilotRequestBinding

LeanVerifierCallable = Callable[[LeanReferencePacket], LeanBridgeVerificationEvidence]
ReplayVerdict = Literal["accept", "reject", "indeterminate"]
REPLAY_GUARD_VERSION: Final[str] = "rcp-rclm-pytorch-pilot-replay-guard-v1"
_REPLAY_FILES: Final[Sequence[str]] = (
    "adapter.py",
    "exact_evaluator.py",
    "pilot_data.py",
    "pilot_policy.py",
    "protocol.py",
    "replay.py",
)
_FORBIDDEN_IMPORT_ROOTS: Final[frozenset[str]] = frozenset(
    {
        "aiohttp",
        "httpx",
        "numpy",
        "random",
        "requests",
        "secrets",
        "socket",
        "subprocess",
        "torch",
        "urllib",
    }
)
_FORBIDDEN_MODULE_PARTS: Final[Sequence[str]] = (
    "torch_backend.process",
    "torch_backend.proposal_backend",
)
_STAGE_ORDER: Final[Sequence[str]] = (
    "source_binding",
    "generator_evidence",
    "proposal_validation",
    "selection_outcome",
    "realization_outcome",
    "evaluation_outcome",
    "certificate_outcome",
    "lean_outcome",
    "checker_outcome",
    "resource_outcome",
    "rollback_outcome",
    "parent_link",
)


class PilotReplayReason(StrEnum):
    SOURCE_GUARD_FAILED = "PYTORCH_REPLAY_SOURCE_GUARD_FAILED"
    STORE_INVALID = "PYTORCH_REPLAY_STORE_INVALID"
    SOURCE_BINDING_MISMATCH = "PYTORCH_REPLAY_SOURCE_BINDING_MISMATCH"
    GENERATOR_EVIDENCE_MISMATCH = "PYTORCH_REPLAY_GENERATOR_EVIDENCE_MISMATCH"
    PROPOSAL_MISMATCH = "PYTORCH_REPLAY_PROPOSAL_MISMATCH"
    SELECTION_MISMATCH = "PYTORCH_REPLAY_SELECTION_MISMATCH"
    REALIZATION_MISMATCH = "PYTORCH_REPLAY_REALIZATION_MISMATCH"
    EVALUATION_MISMATCH = "PYTORCH_REPLAY_EVALUATION_MISMATCH"
    CERTIFICATE_MISMATCH = "PYTORCH_REPLAY_CERTIFICATE_MISMATCH"
    LEAN_MISMATCH = "PYTORCH_REPLAY_LEAN_MISMATCH"
    CHECKER_MISMATCH = "PYTORCH_REPLAY_CHECKER_MISMATCH"
    RESOURCE_MISMATCH = "PYTORCH_REPLAY_RESOURCE_MISMATCH"
    ROLLBACK_MISMATCH = "PYTORCH_REPLAY_ROLLBACK_MISMATCH"
    PARENT_MISMATCH = "PYTORCH_REPLAY_PARENT_MISMATCH"
    TRAINING_BACKEND_DETECTED = "PYTORCH_REPLAY_TRAINING_BACKEND_DETECTED"
    INTERNAL_ERROR = "PYTORCH_REPLAY_INTERNAL_ERROR"


@dataclass(frozen=True, slots=True)
class PilotReplaySourceFinding:
    path: str
    line: int
    code: str
    detail: str

    def __post_init__(self) -> None:
        for name, value in (("path", self.path), ("code", self.code), ("detail", self.detail)):
            require_string(value, f"pytorch_replay.source_finding.{name}")
        if isinstance(self.line, bool) or not isinstance(self.line, int) or self.line < 1:
            raise SchemaValidationError(
                "pytorch_replay.source_finding.line",
                "expected a positive integer",
            )

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "pytorch_replay.source_finding",
    ) -> PilotReplaySourceFinding:
        obj = strict_object(value, path, {"path", "line", "code", "detail"})
        return cls(
            path=require_string(obj["path"], f"{path}.path"),
            line=require_structural_integer(obj["line"], f"{path}.line", minimum=1),
            code=require_string(obj["code"], f"{path}.code"),
            detail=require_string(obj["detail"], f"{path}.detail"),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "code": self.code,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class PilotReplaySourceGuard:
    file_hashes: FrozenHashMap
    findings: Sequence[PilotReplaySourceFinding]

    schema_id: ClassVar[str] = "runtime.pytorch_pilot_replay_source_guard.v1"

    def __post_init__(self) -> None:
        findings = tuple(self.findings)
        object.__setattr__(self, "findings", findings)
        if len(findings) != len({(item.path, item.line, item.code, item.detail) for item in findings}):
            raise SchemaValidationError(
                "pytorch_replay.source_guard.findings",
                "source findings must be unique",
            )

    @property
    def clean(self) -> bool:
        return not self.findings

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "pytorch_replay.source_guard",
    ) -> PilotReplaySourceGuard:
        obj = strict_object(
            value,
            path,
            {"schema_id", "guard_version", "file_hashes", "findings", "clean"},
        )
        if obj["schema_id"] != cls.schema_id:
            raise SchemaValidationError(f"{path}.schema_id", f"expected {cls.schema_id}")
        if obj["guard_version"] != REPLAY_GUARD_VERSION:
            raise SchemaValidationError(
                f"{path}.guard_version",
                f"expected {REPLAY_GUARD_VERSION}",
            )
        raw_hashes = obj["file_hashes"]
        if not isinstance(raw_hashes, Mapping):
            raise SchemaValidationError(f"{path}.file_hashes", "expected an object")
        hashes: dict[str, str] = {}
        for key, item in raw_hashes.items():
            name = require_string(key, f"{path}.file_hashes.key")
            hashes[name] = validate_hash256(item, f"{path}.file_hashes.{name}")
        raw_findings = obj["findings"]
        if not isinstance(raw_findings, list):
            raise SchemaValidationError(f"{path}.findings", "expected an array")
        guard = cls(
            file_hashes=FrozenHashMap.from_mapping(hashes, f"{path}.file_hashes"),
            findings=tuple(
                PilotReplaySourceFinding.from_json(
                    item, f"{path}.findings[{index}]"
                )
                for index, item in enumerate(raw_findings)
            ),
        )
        if not isinstance(obj["clean"], bool) or obj["clean"] != guard.clean:
            raise SchemaValidationError(
                f"{path}.clean",
                "clean flag does not match findings",
            )
        return guard

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "guard_version": REPLAY_GUARD_VERSION,
            "file_hashes": self.file_hashes.to_json(),
            "findings": [item.to_json() for item in self.findings],
            "clean": self.clean,
        }


@dataclass(frozen=True, slots=True)
class PilotReplayStage:
    stage: str
    status: Literal["pass", "fail", "indeterminate", "not_evaluated"]
    reason_codes: Sequence[PilotReplayReason]
    evidence: FrozenJson

    schema_id: ClassVar[str] = "runtime.pytorch_pilot_replay_stage.v1"

    def __post_init__(self) -> None:
        require_string(self.stage, "pytorch_replay.stage.stage")
        if self.status not in {"pass", "fail", "indeterminate", "not_evaluated"}:
            raise SchemaValidationError(
                "pytorch_replay.stage.status",
                f"unsupported status: {self.status}",
            )
        reasons = tuple(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)
        if len(reasons) != len(set(reasons)):
            raise SchemaValidationError(
                "pytorch_replay.stage.reason_codes",
                "reason codes must be unique",
            )
        if self.status == "pass" and reasons:
            raise SchemaValidationError(
                "pytorch_replay.stage.reason_codes",
                "passing stage cannot contain a reason",
            )
        if self.status in {"fail", "indeterminate"} and not reasons:
            raise SchemaValidationError(
                "pytorch_replay.stage.reason_codes",
                "nonpassing evaluated stage requires a reason",
            )
        if self.status == "not_evaluated" and reasons:
            raise SchemaValidationError(
                "pytorch_replay.stage.reason_codes",
                "not-evaluated stage cannot contain a reason",
            )
        evidence = self.evidence
        if isinstance(evidence, (FrozenJsonArray, FrozenJsonObject)) or evidence is None or isinstance(evidence, (bool, int, str)):
            frozen = freeze_json(thaw_json(evidence), "pytorch_replay.stage.evidence")
        else:
            frozen = freeze_json(evidence, "pytorch_replay.stage.evidence")
        object.__setattr__(self, "evidence", frozen)

    @property
    def evidence_hash(self) -> str:
        return canonical_json_hash(thaw_json(self.evidence))

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "pytorch_replay.stage",
    ) -> PilotReplayStage:
        obj = strict_object(
            value,
            path,
            {"schema_id", "stage", "status", "reason_codes", "evidence", "evidence_hash"},
        )
        if obj["schema_id"] != cls.schema_id:
            raise SchemaValidationError(f"{path}.schema_id", f"expected {cls.schema_id}")
        status = require_string(obj["status"], f"{path}.status")
        if status not in {"pass", "fail", "indeterminate", "not_evaluated"}:
            raise SchemaValidationError(f"{path}.status", "unsupported status")
        raw_reasons = obj["reason_codes"]
        if not isinstance(raw_reasons, list):
            raise SchemaValidationError(f"{path}.reason_codes", "expected an array")
        reasons: list[PilotReplayReason] = []
        for index, item in enumerate(raw_reasons):
            text = require_string(item, f"{path}.reason_codes[{index}]")
            try:
                reasons.append(PilotReplayReason(text))
            except ValueError as exc:
                raise SchemaValidationError(
                    f"{path}.reason_codes[{index}]",
                    f"unknown replay reason: {text}",
                ) from exc
        record = cls(
            stage=require_string(obj["stage"], f"{path}.stage"),
            status=cast(
                Literal["pass", "fail", "indeterminate", "not_evaluated"],
                status,
            ),
            reason_codes=tuple(reasons),
            evidence=freeze_json(obj["evidence"], f"{path}.evidence"),
        )
        declared_hash = validate_hash256(
            obj["evidence_hash"], f"{path}.evidence_hash"
        )
        if declared_hash != record.evidence_hash:
            raise SchemaValidationError(
                f"{path}.evidence_hash",
                "evidence hash mismatch",
            )
        return record

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "stage": self.stage,
            "status": self.status,
            "reason_codes": [item.value for item in self.reason_codes],
            "evidence": thaw_json(self.evidence),
            "evidence_hash": self.evidence_hash,
        }


@dataclass(frozen=True, slots=True)
class PilotReplayReport:
    verdict: ReplayVerdict
    reason_codes: Sequence[PilotReplayReason]
    source_active_package_hash: str
    source_attempt_report_hash: str
    source_controller_report_hash: str
    source_candidate_package_tree_hash: str
    replay_candidate_package_tree_hash: str | None
    generator_invocations: int
    training_backend_modules_loaded: Sequence[str]
    stages: Sequence[PilotReplayStage]
    artifact_hashes: FrozenHashMap

    schema_id: ClassVar[str] = "runtime.pytorch_pilot_replay_report.v1"

    def __post_init__(self) -> None:
        if self.verdict not in {"accept", "reject", "indeterminate"}:
            raise SchemaValidationError(
                "pytorch_replay.report.verdict",
                f"unsupported verdict: {self.verdict}",
            )
        reasons = tuple(self.reason_codes)
        modules = tuple(self.training_backend_modules_loaded)
        stages = tuple(self.stages)
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "training_backend_modules_loaded", modules)
        object.__setattr__(self, "stages", stages)
        if len(reasons) != len(set(reasons)):
            raise SchemaValidationError(
                "pytorch_replay.report.reason_codes",
                "reason codes must be unique",
            )
        for name, value in (
            ("source_active_package_hash", self.source_active_package_hash),
            ("source_attempt_report_hash", self.source_attempt_report_hash),
            ("source_controller_report_hash", self.source_controller_report_hash),
            (
                "source_candidate_package_tree_hash",
                self.source_candidate_package_tree_hash,
            ),
        ):
            validate_hash256(value, f"pytorch_replay.report.{name}")
        if self.replay_candidate_package_tree_hash is not None:
            validate_hash256(
                self.replay_candidate_package_tree_hash,
                "pytorch_replay.report.replay_candidate_package_tree_hash",
            )
        if self.generator_invocations != 0:
            raise SchemaValidationError(
                "pytorch_replay.report.generator_invocations",
                "independent replay must record zero generator invocations",
            )
        if tuple(stage.stage for stage in stages) != tuple(_STAGE_ORDER):
            raise SchemaValidationError(
                "pytorch_replay.report.stages",
                "replay stage order differs from the frozen order",
            )
        for index, module_name in enumerate(modules):
            require_string(
                module_name,
                f"pytorch_replay.report.training_backend_modules_loaded[{index}]",
            )
        if modules:
            valid_detection = (
                self.verdict != "accept"
                and PilotReplayReason.TRAINING_BACKEND_DETECTED in reasons
            )
            if not valid_detection:
                raise SchemaValidationError(
                    "pytorch_replay.report.training_backend_modules_loaded",
                    "loaded modules require a nonaccepting training-backend detection",
                )
        if self.verdict == "accept":
            if reasons or modules or any(stage.status != "pass" for stage in stages):
                raise SchemaValidationError(
                    "pytorch_replay.report",
                    "acceptance requires no reasons, no training modules, and all passing stages",
                )
            if self.replay_candidate_package_tree_hash is None:
                raise SchemaValidationError(
                    "pytorch_replay.report.replay_candidate_package_tree_hash",
                    "acceptance requires a recomputed candidate tree hash",
                )
        elif not reasons:
            raise SchemaValidationError(
                "pytorch_replay.report.reason_codes",
                "nonaccepting report requires a reason",
            )

    @property
    def accepted(self) -> bool:
        return self.verdict == "accept"

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self._content_json())

    @classmethod
    def from_json(
        cls,
        value: object,
        path: str = "pytorch_replay.report",
    ) -> PilotReplayReport:
        obj = strict_object(
            value,
            path,
            {
                "schema_id",
                "verdict",
                "accepted",
                "reason_codes",
                "source_active_package_hash",
                "source_attempt_report_hash",
                "source_controller_report_hash",
                "source_candidate_package_tree_hash",
                "replay_candidate_package_tree_hash",
                "generator_invocations",
                "training_backend_modules_loaded",
                "stages",
                "artifact_hashes",
                "report_hash",
            },
        )
        if obj["schema_id"] != cls.schema_id:
            raise SchemaValidationError(f"{path}.schema_id", f"expected {cls.schema_id}")
        verdict_text = require_string(obj["verdict"], f"{path}.verdict")
        if verdict_text not in {"accept", "reject", "indeterminate"}:
            raise SchemaValidationError(f"{path}.verdict", "unsupported verdict")
        raw_reasons = obj["reason_codes"]
        if not isinstance(raw_reasons, list):
            raise SchemaValidationError(f"{path}.reason_codes", "expected an array")
        reasons: list[PilotReplayReason] = []
        for index, item in enumerate(raw_reasons):
            text = require_string(item, f"{path}.reason_codes[{index}]")
            try:
                reasons.append(PilotReplayReason(text))
            except ValueError as exc:
                raise SchemaValidationError(
                    f"{path}.reason_codes[{index}]",
                    f"unknown replay reason: {text}",
                ) from exc
        raw_modules = obj["training_backend_modules_loaded"]
        if not isinstance(raw_modules, list):
            raise SchemaValidationError(
                f"{path}.training_backend_modules_loaded",
                "expected an array",
            )
        raw_stages = obj["stages"]
        if not isinstance(raw_stages, list):
            raise SchemaValidationError(f"{path}.stages", "expected an array")
        raw_artifacts = obj["artifact_hashes"]
        if not isinstance(raw_artifacts, Mapping):
            raise SchemaValidationError(f"{path}.artifact_hashes", "expected an object")
        artifacts: dict[str, str] = {}
        for key, item in raw_artifacts.items():
            name = require_string(key, f"{path}.artifact_hashes.key")
            artifacts[name] = validate_hash256(
                item, f"{path}.artifact_hashes.{name}"
            )
        replay_hash_raw = obj["replay_candidate_package_tree_hash"]
        replay_hash = (
            None
            if replay_hash_raw is None
            else validate_hash256(
                replay_hash_raw,
                f"{path}.replay_candidate_package_tree_hash",
            )
        )
        report = cls(
            verdict=cast(ReplayVerdict, verdict_text),
            reason_codes=tuple(reasons),
            source_active_package_hash=validate_hash256(
                obj["source_active_package_hash"],
                f"{path}.source_active_package_hash",
            ),
            source_attempt_report_hash=validate_hash256(
                obj["source_attempt_report_hash"],
                f"{path}.source_attempt_report_hash",
            ),
            source_controller_report_hash=validate_hash256(
                obj["source_controller_report_hash"],
                f"{path}.source_controller_report_hash",
            ),
            source_candidate_package_tree_hash=validate_hash256(
                obj["source_candidate_package_tree_hash"],
                f"{path}.source_candidate_package_tree_hash",
            ),
            replay_candidate_package_tree_hash=replay_hash,
            generator_invocations=require_structural_integer(
                obj["generator_invocations"],
                f"{path}.generator_invocations",
                minimum=0,
                maximum=0,
            ),
            training_backend_modules_loaded=tuple(
                require_string(
                    item,
                    f"{path}.training_backend_modules_loaded[{index}]",
                )
                for index, item in enumerate(raw_modules)
            ),
            stages=tuple(
                PilotReplayStage.from_json(item, f"{path}.stages[{index}]")
                for index, item in enumerate(raw_stages)
            ),
            artifact_hashes=FrozenHashMap.from_mapping(
                artifacts, f"{path}.artifact_hashes"
            ),
        )
        if not isinstance(obj["accepted"], bool) or obj["accepted"] != report.accepted:
            raise SchemaValidationError(
                f"{path}.accepted",
                "accepted flag does not match verdict",
            )
        declared_hash = validate_hash256(obj["report_hash"], f"{path}.report_hash")
        if declared_hash != report.report_hash:
            raise SchemaValidationError(f"{path}.report_hash", "report hash mismatch")
        return report

    def _content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "verdict": self.verdict,
            "accepted": self.accepted,
            "reason_codes": [item.value for item in self.reason_codes],
            "source_active_package_hash": self.source_active_package_hash,
            "source_attempt_report_hash": self.source_attempt_report_hash,
            "source_controller_report_hash": self.source_controller_report_hash,
            "source_candidate_package_tree_hash": self.source_candidate_package_tree_hash,
            "replay_candidate_package_tree_hash": self.replay_candidate_package_tree_hash,
            "generator_invocations": self.generator_invocations,
            "training_backend_modules_loaded": list(
                self.training_backend_modules_loaded
            ),
            "stages": [stage.to_json() for stage in self.stages],
            "artifact_hashes": self.artifact_hashes.to_json(),
        }

    def to_json(self) -> dict[str, object]:
        value = self._content_json()
        value["report_hash"] = self.report_hash
        return value


@dataclass(frozen=True, slots=True)
class PilotReplayEvidence:
    report: PilotReplayReport
    output_root: Path | None


class _PilotReplayError(ValueError):
    __slots__ = ("stage", "reason", "detail", "indeterminate")

    def __init__(
        self,
        stage: str,
        reason: PilotReplayReason,
        detail: str,
        *,
        indeterminate: bool = False,
    ) -> None:
        super().__init__(stage, reason.value, detail)
        self.stage = stage
        self.reason = reason
        self.detail = detail
        self.indeterminate = indeterminate


def scan_pytorch_pilot_replay_source_bytes(
    path: str,
    content: bytes,
) -> Sequence[PilotReplaySourceFinding]:
    findings: list[PilotReplaySourceFinding] = []
    try:
        text = content.decode("utf-8", errors="strict")
        tree = ast.parse(text, filename=path)
    except (UnicodeDecodeError, SyntaxError) as exc:
        return (
            PilotReplaySourceFinding(
                path=path,
                line=getattr(exc, "lineno", None) or 1,
                code="PYTORCH_REPLAY_SOURCE_PARSE_FAILED",
                detail=type(exc).__name__,
            ),
        )
    for node in ast.walk(tree):
        imported: list[str] = []
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
        for module_name in imported:
            root_name = module_name.split(".", 1)[0]
            if root_name in _FORBIDDEN_IMPORT_ROOTS or any(
                part in module_name for part in _FORBIDDEN_MODULE_PARTS
            ):
                findings.append(
                    PilotReplaySourceFinding(
                        path=path,
                        line=node.lineno,
                        code="PYTORCH_REPLAY_FORBIDDEN_IMPORT",
                        detail=module_name,
                    )
                )
    findings.sort(key=lambda item: (item.path, item.line, item.code, item.detail))
    return tuple(findings)


def guard_pytorch_pilot_replay_source() -> PilotReplaySourceGuard:
    root = Path(__file__).resolve(strict=True).parent
    hashes: dict[str, str] = {}
    findings: list[PilotReplaySourceFinding] = []
    for name in _REPLAY_FILES:
        path = root / name
        content = path.read_bytes()
        hashes[f"rcp_rclm_runtime/torch_backend/{name}"] = sha256_hex(content)
        findings.extend(scan_pytorch_pilot_replay_source_bytes(name, content))
    findings.sort(key=lambda item: (item.path, item.line, item.code, item.detail))
    return PilotReplaySourceGuard(
        file_hashes=FrozenHashMap.from_mapping(hashes, "pytorch_replay.file_hashes"),
        findings=tuple(findings),
    )


def replay_pytorch_pilot_store(
    store_root: Path,
    output_root: Path,
    verify_lean: LeanVerifierCallable,
) -> PilotReplayEvidence:
    source_guard = guard_pytorch_pilot_replay_source()
    resolved_output = output_root.resolve(strict=False)
    if resolved_output.exists():
        raise FileExistsError(f"pilot replay output already exists: {resolved_output}")
    if not source_guard.clean:
        report = _failure_report(
            source_guard=source_guard,
            reason=PilotReplayReason.SOURCE_GUARD_FAILED,
            source_hash="0" * 64,
            attempt_hash="0" * 64,
            controller_hash="0" * 64,
            candidate_hash="0" * 64,
            detail="replay source guard failed",
        )
        return PilotReplayEvidence(report=report, output_root=None)
    initially_loaded = _training_backend_modules_loaded()
    if initially_loaded:
        report = _failure_report(
            source_guard=source_guard,
            reason=PilotReplayReason.TRAINING_BACKEND_DETECTED,
            source_hash="0" * 64,
            attempt_hash="0" * 64,
            controller_hash="0" * 64,
            candidate_hash="0" * 64,
            detail="forbidden training backend module loaded: " + ",".join(initially_loaded),
            training_backend_modules_loaded=initially_loaded,
        )
        return PilotReplayEvidence(report=report, output_root=None)
    policy = pytorch_pilot_phase7_policy()
    try:
        snapshot = load_active_phase7_store(store_root, policy)
        active_manifest = snapshot.package_manifest
        if active_manifest.status != "promoted" or active_manifest.parent_package_hash is None:
            raise _PilotReplayError(
                "source_binding",
                PilotReplayReason.SOURCE_BINDING_MISMATCH,
                "active package is not a promoted pilot package",
            )
        parent_root = snapshot.store_root / "packages" / active_manifest.parent_package_hash
        parent_manifest = verify_immutable_phase7_package(parent_root, policy)
        parent_predecessor_root = parent_root / "predecessor"
        parent_predecessor = load_predecessor_package(parent_predecessor_root)
        source_candidate_root = snapshot.package_root / "source_candidate"
        source_candidate_manifest = verify_candidate_package(source_candidate_root)
        source_candidate_tree_hash = _tree_hash(source_candidate_root)
        evidence_root = snapshot.package_root / "evidence"
        attempt = Phase7AttemptReport.from_json(_read_json(evidence_root / "attempt_report.json"))
        run_root = snapshot.store_root / "runs" / attempt.run_id
        controller = Phase7ControllerReport.from_json(
            _read_json(run_root / "controller_report.json")
        )
        if (
            not controller.promoted
            or controller.promoted_package_hash != snapshot.pointer.active_package_hash
            or len(controller.attempts) != 1
            or controller.attempts[0] != attempt
            or attempt.verdict != "accept"
            or attempt.candidate_package_tree_hash != source_candidate_tree_hash
            or active_manifest.source_candidate_package_tree_hash != source_candidate_tree_hash
            or active_manifest.parent_package_hash != parent_manifest.package_hash
        ):
            raise _PilotReplayError(
                "source_binding",
                PilotReplayReason.SOURCE_BINDING_MISMATCH,
                "promoted store, controller, attempt, candidate, or parent bindings differ",
            )
    except _PilotReplayError as exc:
        report = _failure_report(
            source_guard=source_guard,
            reason=exc.reason,
            source_hash="0" * 64,
            attempt_hash="0" * 64,
            controller_hash="0" * 64,
            candidate_hash="0" * 64,
            detail=exc.detail,
            indeterminate=exc.indeterminate,
        )
        return PilotReplayEvidence(report=report, output_root=None)
    except Exception as exc:
        report = _failure_report(
            source_guard=source_guard,
            reason=PilotReplayReason.STORE_INVALID,
            source_hash="0" * 64,
            attempt_hash="0" * 64,
            controller_hash="0" * 64,
            candidate_hash="0" * 64,
            detail=f"{type(exc).__name__}: {exc}",
        )
        return PilotReplayEvidence(report=report, output_root=None)

    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    stages: list[PilotReplayStage] = []
    recomputed: dict[str, str] = {
        "source_guard": source_guard.report_hash,
        "source_active_package": snapshot.pointer.active_package_hash,
        "source_attempt_report": attempt.report_hash,
        "source_controller_report": controller.report_hash,
        "source_candidate_tree": source_candidate_tree_hash,
    }
    try:
        with tempfile.TemporaryDirectory(
            prefix="rcp-rclm-pytorch-replay-",
            dir=resolved_output.parent,
        ) as temporary_directory:
            staging = Path(temporary_directory) / "replay"
            staging.mkdir(parents=True, exist_ok=False)
            _append_pass(
                stages,
                "source_binding",
                {
                    "active_package_hash": snapshot.pointer.active_package_hash,
                    "parent_package_hash": parent_manifest.package_hash,
                    "attempt_report_hash": attempt.report_hash,
                    "controller_report_hash": controller.report_hash,
                    "source_candidate_package_tree_hash": source_candidate_tree_hash,
                },
            )

            request = PilotRequestBinding.from_json(_read_json(evidence_root / "request.json"))
            _verify_request_binding(request, parent_predecessor)
            first_stdout = (evidence_root / "first_stdout.bin").read_bytes()
            second_stdout = (evidence_root / "second_stdout.bin").read_bytes()
            first_stderr = (evidence_root / "first_stderr.bin").read_bytes()
            second_stderr = (evidence_root / "second_stderr.bin").read_bytes()
            first_report = _parse_process_report(
                _read_json(evidence_root / "first_process_report.json")
            )
            second_report = _parse_process_report(
                _read_json(evidence_root / "second_process_report.json")
            )
            first_guard = _read_json(evidence_root / "first_source_guard.json")
            second_guard = _read_json(evidence_root / "second_source_guard.json")
            first_output = evidence_root / "first_proposal_output"
            second_output = evidence_root / "second_proposal_output"
            if (
                first_stdout != second_stdout
                or first_stderr != second_stderr
                or first_report["verdict"] != "success"
                or second_report["verdict"] != "success"
                or first_report["stdout_hash"] != sha256_hex(first_stdout)
                or second_report["stdout_hash"] != sha256_hex(second_stdout)
                or first_report["stderr_hash"] != sha256_hex(first_stderr)
                or second_report["stderr_hash"] != sha256_hex(second_stderr)
                or first_report["proposal_hash"] != second_report["proposal_hash"]
                or first_report["output_tree_hash"] != second_report["output_tree_hash"]
                or _tree_hash(first_output) != _tree_hash(second_output)
                or first_guard != second_guard
                or not _pilot_source_guard_clean(first_guard)
            ):
                raise _PilotReplayError(
                    "generator_evidence",
                    PilotReplayReason.GENERATOR_EVIDENCE_MISMATCH,
                    "captured proposal process evidence is not equal, clean, and successful",
                )
            recomputed["request"] = request.request_hash
            recomputed["first_proposal_output"] = _tree_hash(first_output)
            _append_pass(
                stages,
                "generator_evidence",
                {
                    "request_hash": request.request_hash,
                    "raw_stdout_equal": True,
                    "raw_stderr_equal": True,
                    "source_guards_equal_and_clean": True,
                    "output_tree_hash": recomputed["first_proposal_output"],
                    "generator_invocations": 0,
                },
            )

            first_validation = validate_pytorch_proposal_output(
                request.to_json(), first_output, parent_predecessor
            )
            second_validation = validate_pytorch_proposal_output(
                request.to_json(), second_output, parent_predecessor
            )
            captured_validation = _read_json(evidence_root / "proposal_validation.json")
            if (
                first_validation.to_json() != second_validation.to_json()
                or first_validation.to_json() != captured_validation
                or first_validation.proposal.proposal_hash != attempt.proposal_hash
            ):
                raise _PilotReplayError(
                    "proposal_validation",
                    PilotReplayReason.PROPOSAL_MISMATCH,
                    "independently validated proposal differs from captured evidence",
                )
            recomputed["proposal_validation"] = first_validation.validation_hash
            recomputed["proposal"] = first_validation.proposal.proposal_hash
            _append_pass(
                stages,
                "proposal_validation",
                {
                    "proposal_hash": first_validation.proposal.proposal_hash,
                    "validation_hash": first_validation.validation_hash,
                    "candidate_reported_selection_consumed": False,
                    "candidate_acceptance_consumed": False,
                    "heldout_labels_consumed": False,
                },
            )

            host_selection = build_host_phase6_selection(
                first_validation,
                first_output,
                parent_predecessor,
            )
            captured_host_selection = _read_json(evidence_root / "host_selection.json")
            stored_selection = Phase6SelectionRecord.from_json(
                _read_json(source_candidate_root / "evidence" / "selection.json")
            )
            if (
                host_selection.to_json() != captured_host_selection
                or host_selection.selection != stored_selection
                or host_selection.selection.selection_hash != attempt.selection_hash
            ):
                raise _PilotReplayError(
                    "selection_outcome",
                    PilotReplayReason.SELECTION_MISMATCH,
                    "host-recomputed Phase 6 selection differs from the source",
                )
            recomputed["selection"] = host_selection.selection.selection_hash
            _append_pass(
                stages,
                "selection_outcome",
                {
                    "selection_hash": host_selection.selection.selection_hash,
                    "selection_constructed_outside_pytorch": True,
                    "candidate_reported_selection_consumed": False,
                    "substantive_component_kinds": ["model_weights"],
                },
            )

            replay_candidate = staging / "candidate"
            phase6 = build_candidate_package(
                parent_predecessor_root,
                host_selection.selection,
                pytorch_pilot_phase7_budget().phase6_budget,
                replay_candidate,
            )
            if not phase6.report.built or phase6.output_root is None:
                raise _PilotReplayError(
                    "realization_outcome",
                    PilotReplayReason.REALIZATION_MISMATCH,
                    "fresh Phase 6 realization failed",
                )
            replay_manifest = verify_candidate_package(replay_candidate)
            replay_candidate_tree_hash = _tree_hash(replay_candidate)
            stored_phase6 = Phase6PackageReport.from_json(
                _read_json(evidence_root / "phase6_report.json")
            )
            if (
                phase6.report != stored_phase6
                or replay_manifest != source_candidate_manifest
                or replay_candidate_tree_hash != source_candidate_tree_hash
                or replay_candidate_tree_hash != attempt.candidate_package_tree_hash
            ):
                raise _PilotReplayError(
                    "realization_outcome",
                    PilotReplayReason.REALIZATION_MISMATCH,
                    "fresh candidate package differs from the retained candidate",
                )
            recomputed["phase6_report"] = phase6.report.report_hash
            recomputed["replay_candidate_tree"] = replay_candidate_tree_hash
            _append_pass(
                stages,
                "realization_outcome",
                {
                    "phase6_report_hash": phase6.report.report_hash,
                    "candidate_manifest_hash": replay_manifest.manifest_hash,
                    "candidate_payload_tree_hash": replay_manifest.payload_tree_hash,
                    "candidate_package_tree_hash": replay_candidate_tree_hash,
                },
            )

            evaluation_data = _read_json(evidence_root / "evaluation_data.json")
            if evaluation_data != pilot_heldout_evaluation_data():
                raise _PilotReplayError(
                    "evaluation_outcome",
                    PilotReplayReason.EVALUATION_MISMATCH,
                    "captured evaluation dataset differs from the frozen held-out set",
                )
            exact_evaluation = evaluate_quantized_transition(
                parent_predecessor.payload_root,
                replay_candidate / "payload",
                evaluation_data,
            )
            logical_evaluation = evaluate_realized_candidate(
                parent_predecessor_root,
                replay_candidate,
                host_selection.selection,
            )
            combined_evaluation = {
                "schema_id": "runtime.pytorch_pilot_combined_evaluation.v1",
                "exact_model_evaluation": exact_evaluation.to_json(),
                "logical_reference_evaluation": logical_evaluation.to_json(),
                "model_objective_authoritative_source": "framework_independent_exact_integer",
                "formal_checker_model_objective_claimed": False,
                "candidate_package_tree_hash": replay_candidate_tree_hash,
            }
            combined_evaluation_hash = canonical_json_hash(combined_evaluation)
            if (
                not exact_evaluation.evaluation_conditions_met
                or combined_evaluation != _read_json(evidence_root / "evaluation.json")
                or combined_evaluation_hash != attempt.evaluation_hash
            ):
                raise _PilotReplayError(
                    "evaluation_outcome",
                    PilotReplayReason.EVALUATION_MISMATCH,
                    "exact model or logical evaluation differs from retained evidence",
                )
            recomputed["evaluation"] = combined_evaluation_hash
            _append_pass(
                stages,
                "evaluation_outcome",
                {
                    "combined_evaluation_hash": combined_evaluation_hash,
                    "exact_evaluation_hash": exact_evaluation.evaluation_hash,
                    "logical_evaluation_hash": logical_evaluation.evaluation_hash,
                    "objective_improved": True,
                    "protected_nonregression": True,
                    "torch_used_for_evaluation": False,
                },
            )

            certificate = Phase7CertificateEvidence(
                certificate_name="stability",
                certificate=canonical_rclm_certificate("gate_b_classical", "stability"),
            )
            if (
                certificate.to_json() != _read_json(evidence_root / "certificate.json")
                or certificate.certificate_hash != attempt.certificate_hash
            ):
                raise _PilotReplayError(
                    "certificate_outcome",
                    PilotReplayReason.CERTIFICATE_MISMATCH,
                    "host-reconstructed certificate differs from retained evidence",
                )
            recomputed["certificate"] = certificate.certificate_hash
            _append_pass(
                stages,
                "certificate_outcome",
                {
                    "certificate_hash": certificate.certificate_hash,
                    "certificate_name": "stability",
                    "constructed_outside_pytorch": True,
                    "model_objective_proved_by_certificate": False,
                },
            )

            packet = build_lean_reference_packet(
                logical_evaluation.predecessor.state,
                logical_evaluation.candidate,
                certificate.certificate,
            )
            expected_generated = generate_reference_source(packet)
            captured_source = (evidence_root / "generated_certificate.lean").read_bytes()
            captured_generated = _read_json(evidence_root / "generated_source.json")
            captured_guard = _read_json(evidence_root / "lean_source_guard.json")
            recomputed_guard = scan_source_bytes(captured_source)
            if (
                captured_source != expected_generated.source_bytes
                or captured_generated != expected_generated.to_json()
                or captured_guard != recomputed_guard.to_json()
                or not recomputed_guard.clean
            ):
                raise _PilotReplayError(
                    "lean_outcome",
                    PilotReplayReason.LEAN_MISMATCH,
                    "captured generated Lean source or source guard does not recompute",
                )
            replay_lean = _invoke_lean(verify_lean, packet)
            if replay_lean.report.bridge_verdict == "indeterminate" or replay_lean.report.timed_out:
                raise _PilotReplayError(
                    "lean_outcome",
                    PilotReplayReason.LEAN_MISMATCH,
                    "independent Lean verification was indeterminate",
                    indeterminate=True,
                )
            if replay_lean.report.bridge_verdict != "accept":
                raise _PilotReplayError(
                    "lean_outcome",
                    PilotReplayReason.LEAN_MISMATCH,
                    "independent Lean verification rejected",
                )
            source_checker_request = Phase3CheckerRequest.from_json(
                _read_json(evidence_root / "checker_request.json")
            )
            if _lean_semantic_fingerprint(replay_lean.report) != _lean_semantic_fingerprint(
                source_checker_request.lean_bridge_report
            ):
                raise _PilotReplayError(
                    "lean_outcome",
                    PilotReplayReason.LEAN_MISMATCH,
                    "fresh Lean semantic verdict differs from captured evidence",
                )
            replay_lean_root = staging / "lean"
            replay_lean_root.mkdir(parents=True, exist_ok=False)
            (replay_lean_root / "generated_certificate.lean").write_bytes(
                replay_lean.generated.source_bytes
            )
            write_canonical_json(
                replay_lean_root / "generated_source.json", replay_lean.generated.to_json()
            )
            write_canonical_json(
                replay_lean_root / "source_guard.json", replay_lean.source_guard.to_json()
            )
            write_canonical_json(
                replay_lean_root / "lean_report.json", replay_lean.report.to_json()
            )
            recomputed["lean_report"] = replay_lean.report.report_hash
            recomputed["lean_semantic_fingerprint"] = _lean_semantic_fingerprint(
                replay_lean.report
            )
            _append_pass(
                stages,
                "lean_outcome",
                {
                    "source_lean_report_hash": source_checker_request.lean_bridge_report.report_hash,
                    "replay_lean_report_hash": replay_lean.report.report_hash,
                    "semantic_fingerprint": recomputed["lean_semantic_fingerprint"],
                    "source_guard_clean": True,
                    "model_objective_proved_by_lean": False,
                },
            )

            expected_request_without_lean = {
                "transition_id": request.transition_id,
                "predecessor": logical_evaluation.predecessor.state.to_json(),
                "candidate": logical_evaluation.candidate.to_json(),
                "certificate": certificate.certificate.to_json(),
                "trust_anchor": reference_trust_anchor().to_json(),
                "resource_record": reference_resource_record(
                    budget_units=1,
                    consumed_units=1,
                    environment_hash=PYTORCH_PILOT_CONTROLLER_ENVIRONMENT_HASH,
                ).to_json(),
                "protected_distinctions": [
                    item.to_json()
                    for item in reference_protected_distinctions("gate_b_classical")
                ],
                "evaluation_evidence": logical_evaluation.evaluation.to_json(),
            }
            source_request_json = source_checker_request.to_json()
            for key, expected in expected_request_without_lean.items():
                if source_request_json[key] != expected:
                    raise _PilotReplayError(
                        "checker_outcome",
                        PilotReplayReason.CHECKER_MISMATCH,
                        f"captured checker request differs at {key}",
                    )
            source_integrity = PackageIntegrityRecord.from_json(
                _read_json(evidence_root / "package_integrity.json")
            )
            rebuilt_source_integrity = build_reference_package_integrity(
                source_checker_request
            )
            if source_integrity != rebuilt_source_integrity:
                raise _PilotReplayError(
                    "checker_outcome",
                    PilotReplayReason.CHECKER_MISMATCH,
                    "captured package integrity does not recompute",
                )
            source_hardened = check_hardened_transition(
                Phase4HardenedRequest(
                    checker_request=source_checker_request,
                    package_integrity=source_integrity,
                )
            )
            if (
                source_hardened.to_json()
                != _read_json(evidence_root / "hardened_checker_report.json")
                or source_hardened.report_hash != attempt.checker_report_hash
            ):
                raise _PilotReplayError(
                    "checker_outcome",
                    PilotReplayReason.CHECKER_MISMATCH,
                    "captured hardened checker report does not recompute",
                )
            replay_request = Phase3CheckerRequest(
                transition_id=request.transition_id,
                predecessor=logical_evaluation.predecessor.state,
                candidate=logical_evaluation.candidate,
                certificate=certificate.certificate,
                trust_anchor=reference_trust_anchor(),
                resource_record=reference_resource_record(
                    budget_units=1,
                    consumed_units=1,
                    environment_hash=PYTORCH_PILOT_CONTROLLER_ENVIRONMENT_HASH,
                ),
                protected_distinctions=reference_protected_distinctions(
                    "gate_b_classical"
                ),
                evaluation_evidence=logical_evaluation.evaluation,
                lean_bridge_report=replay_lean.report,
            )
            replay_integrity = build_reference_package_integrity(replay_request)
            replay_hardened = check_hardened_transition(
                Phase4HardenedRequest(
                    checker_request=replay_request,
                    package_integrity=replay_integrity,
                )
            )
            if (
                not source_hardened.accepted
                or not replay_hardened.accepted
                or _checker_semantic_fingerprint(source_hardened)
                != _checker_semantic_fingerprint(replay_hardened)
            ):
                raise _PilotReplayError(
                    "checker_outcome",
                    PilotReplayReason.CHECKER_MISMATCH,
                    "fresh checker result differs from the captured mathematical result",
                )
            recomputed["source_checker"] = source_hardened.report_hash
            recomputed["replay_checker"] = replay_hardened.report_hash
            recomputed["checker_semantic_fingerprint"] = _checker_semantic_fingerprint(
                replay_hardened
            )
            _append_pass(
                stages,
                "checker_outcome",
                {
                    "source_checker_report_hash": source_hardened.report_hash,
                    "replay_checker_report_hash": replay_hardened.report_hash,
                    "semantic_fingerprint": recomputed[
                        "checker_semantic_fingerprint"
                    ],
                    "checker_accepted": True,
                    "model_invocations_inside_checker": 0,
                    "torch_used_as_checker_authority": False,
                },
            )

            source_resources = source_candidate_root / "evidence" / "resources.json"
            replay_resources = replay_candidate / "evidence" / "resources.json"
            if source_resources.read_bytes() != replay_resources.read_bytes():
                raise _PilotReplayError(
                    "resource_outcome",
                    PilotReplayReason.RESOURCE_MISMATCH,
                    "fresh resource evidence differs from source",
                )
            recomputed["resource_usage"] = sha256_hex(replay_resources.read_bytes())
            _append_pass(
                stages,
                "resource_outcome",
                {
                    "resource_usage_hash": recomputed["resource_usage"],
                    "generator_invocations": 0,
                    "training_backend_loaded": False,
                },
            )

            source_rollback = _read_json(
                source_candidate_root / "evidence" / "rollback.json"
            )
            replay_rollback = _read_json(
                replay_candidate / "evidence" / "rollback.json"
            )
            if source_rollback != replay_rollback:
                raise _PilotReplayError(
                    "rollback_outcome",
                    PilotReplayReason.ROLLBACK_MISMATCH,
                    "fresh rollback evidence differs from source",
                )
            archive = replay_candidate / "rollback" / "predecessor.tar"
            expected_tree = _hash_field(
                replay_rollback.get("predecessor_tree_hash")
                if isinstance(replay_rollback, dict)
                else None,
                "pytorch_replay.rollback.predecessor_tree_hash",
            )
            restored_tree = verify_rollback_snapshot_archive(archive, expected_tree)
            if restored_tree != expected_tree:
                raise _PilotReplayError(
                    "rollback_outcome",
                    PilotReplayReason.ROLLBACK_MISMATCH,
                    "rollback archive did not restore predecessor tree",
                )
            recomputed["rollback_archive"] = sha256_hex(archive.read_bytes())
            _append_pass(
                stages,
                "rollback_outcome",
                {
                    "rollback_archive_hash": recomputed["rollback_archive"],
                    "restored_tree_hash": restored_tree,
                    "verified": True,
                },
            )

            if (
                active_manifest.parent_package_hash != parent_manifest.package_hash
                or active_manifest.source_candidate_package_tree_hash
                != source_candidate_tree_hash
                or snapshot.predecessor.manifest.payload_tree_hash
                != source_candidate_manifest.payload_tree_hash
            ):
                raise _PilotReplayError(
                    "parent_link",
                    PilotReplayReason.PARENT_MISMATCH,
                    "promotion parent, source candidate, or active successor binding differs",
                )
            _append_pass(
                stages,
                "parent_link",
                {
                    "parent_package_hash": parent_manifest.package_hash,
                    "successor_package_hash": snapshot.pointer.active_package_hash,
                    "source_candidate_package_tree_hash": source_candidate_tree_hash,
                    "active_successor_payload_tree_hash": snapshot.predecessor.manifest.payload_tree_hash,
                },
            )

            loaded_after_replay = _training_backend_modules_loaded()
            if loaded_after_replay:
                raise _PilotReplayError(
                    "parent_link",
                    PilotReplayReason.TRAINING_BACKEND_DETECTED,
                    "training backend loaded during replay: "
                    + ",".join(loaded_after_replay),
                )
            report = PilotReplayReport(
                verdict="accept",
                reason_codes=(),
                source_active_package_hash=snapshot.pointer.active_package_hash,
                source_attempt_report_hash=attempt.report_hash,
                source_controller_report_hash=controller.report_hash,
                source_candidate_package_tree_hash=source_candidate_tree_hash,
                replay_candidate_package_tree_hash=replay_candidate_tree_hash,
                generator_invocations=0,
                training_backend_modules_loaded=(),
                stages=tuple(stages),
                artifact_hashes=FrozenHashMap.from_mapping(
                    recomputed,
                    "pytorch_replay.artifact_hashes",
                ),
            )
            write_canonical_json(staging / "source_guard.json", source_guard.to_json())
            write_canonical_json(staging / "replay_report.json", report.to_json())
            os.replace(staging, resolved_output)
            return PilotReplayEvidence(report=report, output_root=resolved_output)
    except _PilotReplayError as exc:
        while len(stages) < len(_STAGE_ORDER):
            expected = _STAGE_ORDER[len(stages)]
            if expected == exc.stage:
                stages.append(
                    PilotReplayStage(
                        stage=expected,
                        status="indeterminate" if exc.indeterminate else "fail",
                        reason_codes=(exc.reason,),
                        evidence={
                            "detail_hash": sha256_hex(exc.detail.encode("utf-8")),
                        },
                    )
                )
            else:
                stages.append(
                    PilotReplayStage(
                        stage=expected,
                        status="not_evaluated",
                        reason_codes=(),
                        evidence={},
                    )
                )
        report = PilotReplayReport(
            verdict="indeterminate" if exc.indeterminate else "reject",
            reason_codes=(exc.reason,),
            source_active_package_hash=snapshot.pointer.active_package_hash,
            source_attempt_report_hash=attempt.report_hash,
            source_controller_report_hash=controller.report_hash,
            source_candidate_package_tree_hash=source_candidate_tree_hash,
            replay_candidate_package_tree_hash=recomputed.get("replay_candidate_tree"),
            generator_invocations=0,
            training_backend_modules_loaded=(),
            stages=tuple(stages),
            artifact_hashes=FrozenHashMap.from_mapping(
                recomputed,
                "pytorch_replay.failure_artifact_hashes",
            ),
        )
        return PilotReplayEvidence(report=report, output_root=None)
    except Exception as exc:
        report = _failure_report(
            source_guard=source_guard,
            reason=PilotReplayReason.INTERNAL_ERROR,
            source_hash=snapshot.pointer.active_package_hash,
            attempt_hash=attempt.report_hash,
            controller_hash=controller.report_hash,
            candidate_hash=source_candidate_tree_hash,
            detail=f"{type(exc).__name__}: {exc}",
        )
        return PilotReplayEvidence(report=report, output_root=None)


def _verify_request_binding(request: PilotRequestBinding, predecessor) -> None:
    training_manifest = pilot_training_data_manifest()
    expected = {
        "predecessor_package_id": predecessor.manifest.package_id,
        "predecessor_manifest_hash": predecessor.manifest.manifest_hash,
        "phase5_predecessor_manifest_hash": predecessor.manifest.phase5_manifest_hash,
        "predecessor_payload_tree_hash": predecessor.measurement.tree_hash,
        "training_data_manifest_hash": canonical_json_hash(training_manifest),
        "heldout_feature_manifest_hash": training_manifest[
            "heldout_feature_manifest_hash"
        ],
    }
    for name, value in expected.items():
        if getattr(request, name) != value:
            raise _PilotReplayError(
                "generator_evidence",
                PilotReplayReason.GENERATOR_EVIDENCE_MISMATCH,
                f"captured request binding differs at {name}",
            )


def _parse_process_report(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SchemaValidationError("pytorch_replay.process_report", "expected object")
    expected = {
        "schema_id",
        "verdict",
        "reason_codes",
        "command",
        "return_code",
        "timed_out",
        "stdout_hash",
        "stderr_hash",
        "output_tree_hash",
        "proposal_hash",
        "source_guard_hash",
        "report_hash",
    }
    if set(value) != expected:
        raise SchemaValidationError(
            "pytorch_replay.process_report", "unexpected fields"
        )
    if value["schema_id"] != "runtime.pytorch_pilot_process_report.v1":
        raise SchemaValidationError(
            "pytorch_replay.process_report.schema_id", "unsupported schema"
        )
    core = dict(value)
    declared = _hash_field(core.pop("report_hash"), "pytorch_replay.process_report.report_hash")
    if canonical_json_hash(core) != declared:
        raise SchemaValidationError(
            "pytorch_replay.process_report.report_hash", "report hash mismatch"
        )
    for name in ("stdout_hash", "stderr_hash", "source_guard_hash"):
        _hash_field(value[name], f"pytorch_replay.process_report.{name}")
    for name in ("output_tree_hash", "proposal_hash"):
        if value[name] is not None:
            _hash_field(value[name], f"pytorch_replay.process_report.{name}")
    if value["verdict"] != "success" or value["return_code"] != 0 or value["timed_out"] is not False:
        raise SchemaValidationError(
            "pytorch_replay.process_report", "captured process did not succeed"
        )
    return value


def _pilot_source_guard_clean(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    expected = {
        "schema_id",
        "guard_version",
        "source_path",
        "source_hash",
        "findings",
        "clean",
    }
    if set(value) != expected:
        return False
    try:
        _hash_field(value["source_hash"], "pytorch_replay.source_guard.source_hash")
    except (SchemaValidationError, TypeError, ValueError):
        return False
    return value["clean"] is True and value["findings"] == []


def _invoke_lean(
    verify_lean: LeanVerifierCallable,
    packet: LeanReferencePacket,
) -> LeanBridgeVerificationEvidence:
    try:
        result = verify_lean(packet)
    except Exception as exc:
        raise _PilotReplayError(
            "lean_outcome",
            PilotReplayReason.LEAN_MISMATCH,
            f"Lean verifier invocation failed: {type(exc).__name__}: {exc}",
            indeterminate=True,
        ) from exc
    if not isinstance(result, LeanBridgeVerificationEvidence):
        raise _PilotReplayError(
            "lean_outcome",
            PilotReplayReason.LEAN_MISMATCH,
            "Lean verifier returned unsupported evidence",
        )
    return result


def _lean_semantic_fingerprint(report: LeanBridgeVerificationReport) -> str:
    value = report.to_json()
    value.pop("compiler_duration_ms", None)
    return canonical_json_hash(value)


def _checker_semantic_fingerprint(report: object) -> str:
    if not hasattr(report, "checker_report") or report.checker_report is None:
        return canonical_json_hash({"checker_report": None})
    value = report.checker_report.to_json()
    value.pop("artifact_hashes", None)
    lean = value.get("lean_bridge_result")
    if isinstance(lean, dict):
        evidence = lean.get("evidence")
        if isinstance(evidence, dict):
            evidence.pop("report_hash", None)
    return canonical_json_hash(value)


def _append_pass(
    stages: list[PilotReplayStage],
    stage: str,
    evidence: object,
) -> None:
    expected = _STAGE_ORDER[len(stages)]
    if stage != expected:
        raise _PilotReplayError(
            expected,
            PilotReplayReason.INTERNAL_ERROR,
            f"stage order mismatch: expected {expected}, observed {stage}",
        )
    stages.append(
        PilotReplayStage(
            stage=stage,
            status="pass",
            reason_codes=(),
            evidence=evidence,
        )
    )


def _failure_report(
    *,
    source_guard: PilotReplaySourceGuard,
    reason: PilotReplayReason,
    source_hash: str,
    attempt_hash: str,
    controller_hash: str,
    candidate_hash: str,
    detail: str,
    indeterminate: bool = False,
    training_backend_modules_loaded: Sequence[str] = (),
) -> PilotReplayReport:
    def zero_or_hash(value: str) -> str:
        return value if len(value) == 64 else "0" * 64

    return PilotReplayReport(
        verdict="indeterminate" if indeterminate else "reject",
        reason_codes=(reason,),
        source_active_package_hash=zero_or_hash(source_hash),
        source_attempt_report_hash=zero_or_hash(attempt_hash),
        source_controller_report_hash=zero_or_hash(controller_hash),
        source_candidate_package_tree_hash=zero_or_hash(candidate_hash),
        replay_candidate_package_tree_hash=None,
        generator_invocations=0,
        training_backend_modules_loaded=tuple(training_backend_modules_loaded),
        stages=tuple(
            PilotReplayStage(
                stage=stage,
                status=(
                    "indeterminate"
                    if index == 0 and indeterminate
                    else "fail" if index == 0 else "not_evaluated"
                ),
                reason_codes=(reason,) if index == 0 else (),
                evidence=(
                    {
                        "detail_hash": sha256_hex(detail.encode("utf-8")),
                        "source_guard_hash": source_guard.report_hash,
                        "training_backend_modules_loaded": list(
                            training_backend_modules_loaded
                        ),
                    }
                    if index == 0
                    else {}
                ),
            )
            for index, stage in enumerate(_STAGE_ORDER)
        ),
        artifact_hashes=FrozenHashMap.from_mapping(
            {"source_guard": source_guard.report_hash},
            "pytorch_replay.failure_artifacts",
        ),
    )


def _training_backend_modules_loaded() -> Sequence[str]:
    import sys

    return tuple(
        name
        for name in (
            "rcp_rclm_runtime.torch_backend.process",
            "rcp_rclm_runtime.torch_backend.proposal_backend",
            "torch",
        )
        if name in sys.modules
    )


def _read_json(path: Path) -> object:
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(f"replay evidence is not a regular file: {path}")
    return load_json_strict(path.read_bytes(), require_canonical=True)


def _tree_hash(path: Path) -> str:
    return semantic_tree_hash(build_tree_records(path))


def _hash_field(value: object, path: str) -> str:
    if not isinstance(value, str):
        raise SchemaValidationError(path, "expected string")
    return validate_hash256(value, path)


__all__ = [
    "PilotReplayEvidence",
    "PilotReplayReason",
    "PilotReplayReport",
    "PilotReplaySourceGuard",
    "guard_pytorch_pilot_replay_source",
    "replay_pytorch_pilot_store",
    "scan_pytorch_pilot_replay_source_bytes",
]
