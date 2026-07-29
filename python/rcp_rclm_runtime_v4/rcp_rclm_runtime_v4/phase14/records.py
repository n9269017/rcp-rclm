from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, validate_hash256
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase14.constants import (
    PHASE14_CONTRACT_VERSION,
    PHASE14_OBJECTIVE_ID,
    PHASE14_ROUTE_MARKER,
    ProgramVariant,
    UPDATE_KINDS_BY_FAMILY,
    UpdateFamily,
    cast_program_variant,
    cast_update_family,
)


def _text(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaValidationError(path, "expected nonempty string")
    return value


def _nonnegative(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SchemaValidationError(path, "expected nonnegative integer")
    return value



def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(path, "expected object")
    return value


def _sequence(value: object, path: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray)
    ):
        raise SchemaValidationError(path, "expected array")
    return value


def _ordered_unique(values: Sequence[str], path: str, *, nonempty: bool = False) -> tuple[str, ...]:
    result = tuple(_text(value, f"{path}[{index}]") for index, value in enumerate(values))
    if nonempty and not result:
        raise SchemaValidationError(path, "at least one value is required")
    if len(set(result)) != len(result):
        raise SchemaValidationError(path, "duplicate value")
    expected = tuple(sorted(result, key=lambda item: item.encode("utf-8")))
    if result != expected:
        raise SchemaValidationError(path, "values must be sorted by UTF-8 bytes")
    return result


@dataclass(frozen=True, slots=True)
class Phase14SearchHistoryEntry:
    sequence_number: int
    challenge_commitment_hash: str
    attempt_index: int
    update_family: UpdateFamily
    program_variant: ProgramVariant
    program_hash: str
    candidate_semantic_package_hash: str
    verdict: str
    reason_codes: Sequence[str]
    active_package_hash_before: str
    active_package_hash_after: str
    rejection_evidence_hash: str | None

    schema_id: ClassVar[str] = "runtime.v4.phase14.search_history_entry.v1"

    def __post_init__(self) -> None:
        _nonnegative(self.sequence_number, "phase14.history.sequence_number")
        _nonnegative(self.attempt_index, "phase14.history.attempt_index")
        validate_hash256(self.challenge_commitment_hash, "phase14.history.challenge_commitment_hash")
        cast_update_family(self.update_family, "phase14.history.update_family")
        cast_program_variant(
            self.program_variant,
            "phase14.history.program_variant",
        )
        for name in (
            "program_hash",
            "candidate_semantic_package_hash",
            "active_package_hash_before",
            "active_package_hash_after",
        ):
            validate_hash256(getattr(self, name), f"phase14.history.{name}")
        if self.verdict not in {"accept", "reject"}:
            raise SchemaValidationError("phase14.history.verdict", "unsupported verdict")
        object.__setattr__(
            self,
            "reason_codes",
            _ordered_unique(self.reason_codes, "phase14.history.reason_codes"),
        )
        if self.verdict == "accept":
            if self.reason_codes or self.rejection_evidence_hash is not None:
                raise SchemaValidationError(
                    "phase14.history",
                    "accepted history cannot contain rejection evidence",
                )
            if self.active_package_hash_before == self.active_package_hash_after:
                raise SchemaValidationError(
                    "phase14.history.active_package_hash_after",
                    "accepted history must advance the active package",
                )
        else:
            if not self.reason_codes or self.rejection_evidence_hash is None:
                raise SchemaValidationError(
                    "phase14.history",
                    "rejected history requires reason codes and evidence",
                )
            validate_hash256(
                self.rejection_evidence_hash,
                "phase14.history.rejection_evidence_hash",
            )
            if self.active_package_hash_before != self.active_package_hash_after:
                raise SchemaValidationError(
                    "phase14.history.active_package_hash_after",
                    "rejection must preserve the active package",
                )

    @classmethod
    def from_json(cls, value: object) -> Phase14SearchHistoryEntry:
        obj = _mapping(value, "phase14.history_entry")
        reasons = _sequence(obj.get("reason_codes"), "phase14.history_entry.reason_codes")
        rejection = obj.get("rejection_evidence_hash")
        return cls(
            sequence_number=_nonnegative(
                obj.get("sequence_number"),
                "phase14.history_entry.sequence_number",
            ),
            challenge_commitment_hash=_text(
                obj.get("challenge_commitment_hash"),
                "phase14.history_entry.challenge_commitment_hash",
            ),
            attempt_index=_nonnegative(
                obj.get("attempt_index"),
                "phase14.history_entry.attempt_index",
            ),
            update_family=cast_update_family(
                _text(
                    obj.get("update_family"),
                    "phase14.history_entry.update_family",
                )
            ),
            program_variant=cast_program_variant(
                _text(
                    obj.get("program_variant"),
                    "phase14.history_entry.program_variant",
                )
            ),
            program_hash=_text(
                obj.get("program_hash"),
                "phase14.history_entry.program_hash",
            ),
            candidate_semantic_package_hash=_text(
                obj.get("candidate_semantic_package_hash"),
                "phase14.history_entry.candidate_semantic_package_hash",
            ),
            verdict=_text(
                obj.get("verdict"),
                "phase14.history_entry.verdict",
            ),
            reason_codes=tuple(str(item) for item in reasons),
            active_package_hash_before=_text(
                obj.get("active_package_hash_before"),
                "phase14.history_entry.active_package_hash_before",
            ),
            active_package_hash_after=_text(
                obj.get("active_package_hash_after"),
                "phase14.history_entry.active_package_hash_after",
            ),
            rejection_evidence_hash=(
                None if rejection is None else _text(
                    rejection,
                    "phase14.history_entry.rejection_evidence_hash",
                )
            ),
        )

    @property
    def entry_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "sequence_number": self.sequence_number,
            "challenge_commitment_hash": self.challenge_commitment_hash,
            "attempt_index": self.attempt_index,
            "update_family": self.update_family,
            "program_variant": self.program_variant,
            "program_hash": self.program_hash,
            "candidate_semantic_package_hash": self.candidate_semantic_package_hash,
            "verdict": self.verdict,
            "reason_codes": list(self.reason_codes),
            "active_package_hash_before": self.active_package_hash_before,
            "active_package_hash_after": self.active_package_hash_after,
            "rejection_evidence_hash": self.rejection_evidence_hash,
        }


@dataclass(frozen=True, slots=True)
class Phase14SearchHistory:
    entries: Sequence[Phase14SearchHistoryEntry]

    schema_id: ClassVar[str] = "runtime.v4.phase14.search_history.v1"

    def __post_init__(self) -> None:
        values = tuple(self.entries)
        expected = tuple(range(len(values)))
        observed = tuple(item.sequence_number for item in values)
        if observed != expected:
            raise SchemaValidationError(
                "phase14.history.entries",
                "history sequence numbers must be contiguous from zero",
            )
        object.__setattr__(self, "entries", values)

    @classmethod
    def from_json(cls, value: object) -> Phase14SearchHistory:
        obj = _mapping(value, "phase14.history")
        entries = _sequence(obj.get("entries"), "phase14.history.entries")
        return cls(
            entries=tuple(
                Phase14SearchHistoryEntry.from_json(item) for item in entries
            )
        )

    @property
    def history_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def attempted_families(self, commitment_hash: str) -> tuple[UpdateFamily, ...]:
        result = tuple(
            item.update_family
            for item in self.entries
            if item.challenge_commitment_hash == commitment_hash
        )
        return result

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "entries": [entry.to_json() for entry in self.entries],
        }


@dataclass(frozen=True, slots=True)
class Phase14MutationProgram:
    active_semantic_package_hash: str
    active_model_identity_hash: str
    active_generator_hash: str
    active_planner_hash: str
    challenge_commitment_hash: str
    history_hash: str
    objective_id: str
    update_family: UpdateFamily
    variant: ProgramVariant
    slot_token_id: int
    route_marker_token_id: int
    update_kinds: Sequence[str]
    search_cost: int
    manual_repair_count: int = 0
    heldout_material_visible: bool = False
    contract_version: str = PHASE14_CONTRACT_VERSION

    schema_id: ClassVar[str] = "runtime.v4.phase14.mutation_program.v1"

    def __post_init__(self) -> None:
        for name in (
            "active_semantic_package_hash",
            "active_model_identity_hash",
            "active_generator_hash",
            "active_planner_hash",
            "challenge_commitment_hash",
            "history_hash",
        ):
            validate_hash256(getattr(self, name), f"phase14.program.{name}")
        if self.objective_id != PHASE14_OBJECTIVE_ID:
            raise SchemaValidationError("phase14.program.objective_id", "unexpected objective")
        family = cast_update_family(self.update_family, "phase14.program.update_family")
        variant = cast_program_variant(self.variant, "phase14.program.variant")
        expected_kinds = tuple(sorted(UPDATE_KINDS_BY_FAMILY[family], key=lambda item: item.encode("utf-8")))
        observed_kinds = _ordered_unique(
            self.update_kinds,
            "phase14.program.update_kinds",
            nonempty=True,
        )
        if observed_kinds != expected_kinds:
            raise SchemaValidationError(
                "phase14.program.update_kinds",
                "update kinds do not match the selected family",
            )
        object.__setattr__(self, "update_kinds", observed_kinds)
        if not 0 <= self.slot_token_id < 256:
            raise SchemaValidationError("phase14.program.slot_token_id", "slot must be one byte")
        if not 0 <= self.route_marker_token_id < 256:
            raise SchemaValidationError(
                "phase14.program.route_marker_token_id",
                "route marker must be one byte",
            )
        if variant == "probe":
            if self.route_marker_token_id != self.slot_token_id:
                raise SchemaValidationError(
                    "phase14.program.route_marker_token_id",
                    "probe programs must retain the unsolved commitment slot",
                )
        elif self.route_marker_token_id != PHASE14_ROUTE_MARKER:
            raise SchemaValidationError(
                "phase14.program.route_marker_token_id",
                "direct and recovery programs must target the certified M4 route marker",
            )
        if self.search_cost != 1:
            raise SchemaValidationError("phase14.program.search_cost", "one search unit is required")
        if self.manual_repair_count != 0:
            raise SchemaValidationError("phase14.program.manual_repair_count", "manual repair is forbidden")
        if self.heldout_material_visible:
            raise SchemaValidationError("phase14.program.heldout_material_visible", "held-out access is forbidden")
        if self.contract_version != PHASE14_CONTRACT_VERSION:
            raise SchemaValidationError("phase14.program.contract_version", "contract version mismatch")

    @classmethod
    def from_json(cls, value: object) -> Phase14MutationProgram:
        obj = _mapping(value, "phase14.program")
        update_kinds = _sequence(
            obj.get("update_kinds"),
            "phase14.program.update_kinds",
        )
        result = cls(
            active_semantic_package_hash=_text(
                obj.get("active_semantic_package_hash"),
                "phase14.program.active_semantic_package_hash",
            ),
            active_model_identity_hash=_text(
                obj.get("active_model_identity_hash"),
                "phase14.program.active_model_identity_hash",
            ),
            active_generator_hash=_text(
                obj.get("active_generator_hash"),
                "phase14.program.active_generator_hash",
            ),
            active_planner_hash=_text(
                obj.get("active_planner_hash"),
                "phase14.program.active_planner_hash",
            ),
            challenge_commitment_hash=_text(
                obj.get("challenge_commitment_hash"),
                "phase14.program.challenge_commitment_hash",
            ),
            history_hash=_text(
                obj.get("history_hash"),
                "phase14.program.history_hash",
            ),
            objective_id=_text(
                obj.get("objective_id"),
                "phase14.program.objective_id",
            ),
            update_family=cast_update_family(
                _text(
                    obj.get("update_family"),
                    "phase14.program.update_family",
                )
            ),
            variant=cast_program_variant(
                _text(
                    obj.get("variant"),
                    "phase14.program.variant",
                )
            ),
            slot_token_id=_nonnegative(
                obj.get("slot_token_id"),
                "phase14.program.slot_token_id",
            ),
            route_marker_token_id=_nonnegative(
                obj.get("route_marker_token_id"),
                "phase14.program.route_marker_token_id",
            ),
            update_kinds=tuple(str(item) for item in update_kinds),
            search_cost=_nonnegative(
                obj.get("search_cost"),
                "phase14.program.search_cost",
            ),
            manual_repair_count=_nonnegative(
                obj.get("manual_repair_count"),
                "phase14.program.manual_repair_count",
            ),
            heldout_material_visible=bool(
                obj.get("heldout_material_visible")
            ),
            contract_version=_text(
                obj.get("contract_version"),
                "phase14.program.contract_version",
            ),
        )
        if obj.get("program_hash") != result.program_hash:
            raise SchemaValidationError(
                "phase14.program.program_hash",
                "content hash mismatch",
            )
        return result

    @property
    def program_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": self.contract_version,
            "active_semantic_package_hash": self.active_semantic_package_hash,
            "active_model_identity_hash": self.active_model_identity_hash,
            "active_generator_hash": self.active_generator_hash,
            "active_planner_hash": self.active_planner_hash,
            "challenge_commitment_hash": self.challenge_commitment_hash,
            "history_hash": self.history_hash,
            "objective_id": self.objective_id,
            "update_family": self.update_family,
            "variant": self.variant,
            "slot_token_id": self.slot_token_id,
            "route_marker_token_id": self.route_marker_token_id,
            "update_kinds": list(self.update_kinds),
            "search_cost": self.search_cost,
            "manual_repair_count": self.manual_repair_count,
            "heldout_material_visible": self.heldout_material_visible,
        }

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["program_hash"] = self.program_hash
        return value


@dataclass(frozen=True, slots=True)
class Phase14ProposalEnumeration:
    active_semantic_package_hash: str
    active_model_identity_hash: str
    generator_policy_hash: str
    planner_policy_hash: str
    challenge_commitment_hash: str
    history_hash: str
    policy_seed_hash: str
    programs: Sequence[Phase14MutationProgram]
    package_tree_hash_before: str
    package_tree_hash_after: str

    schema_id: ClassVar[str] = "runtime.v4.phase14.proposal_enumeration.v1"

    def __post_init__(self) -> None:
        for name in (
            "active_semantic_package_hash",
            "active_model_identity_hash",
            "generator_policy_hash",
            "planner_policy_hash",
            "challenge_commitment_hash",
            "history_hash",
            "policy_seed_hash",
            "package_tree_hash_before",
            "package_tree_hash_after",
        ):
            validate_hash256(getattr(self, name), f"phase14.enumeration.{name}")
        programs = tuple(self.programs)
        if not programs:
            raise SchemaValidationError("phase14.enumeration.programs", "at least one program is required")
        if len({item.update_family for item in programs}) != len(programs):
            raise SchemaValidationError("phase14.enumeration.programs", "duplicate update family")
        for program in programs:
            bindings = (
                program.active_semantic_package_hash == self.active_semantic_package_hash,
                program.active_model_identity_hash == self.active_model_identity_hash,
                program.active_generator_hash == self.generator_policy_hash,
                program.active_planner_hash == self.planner_policy_hash,
                program.challenge_commitment_hash == self.challenge_commitment_hash,
                program.history_hash == self.history_hash,
            )
            if not all(bindings):
                raise SchemaValidationError("phase14.enumeration.programs", "program binding mismatch")
        object.__setattr__(self, "programs", programs)
        if self.package_tree_hash_before != self.package_tree_hash_after:
            raise SchemaValidationError(
                "phase14.enumeration.package_tree_hash_after",
                "proposal worker may not mutate the active package",
            )

    @classmethod
    def from_json(cls, value: object) -> Phase14ProposalEnumeration:
        obj = _mapping(value, "phase14.enumeration")
        raw_programs = _sequence(
            obj.get("programs"),
            "phase14.enumeration.programs",
        )
        return cls(
            active_semantic_package_hash=_text(
                obj.get("active_semantic_package_hash"),
                "phase14.enumeration.active_semantic_package_hash",
            ),
            active_model_identity_hash=_text(
                obj.get("active_model_identity_hash"),
                "phase14.enumeration.active_model_identity_hash",
            ),
            generator_policy_hash=_text(
                obj.get("generator_policy_hash"),
                "phase14.enumeration.generator_policy_hash",
            ),
            planner_policy_hash=_text(
                obj.get("planner_policy_hash"),
                "phase14.enumeration.planner_policy_hash",
            ),
            challenge_commitment_hash=_text(
                obj.get("challenge_commitment_hash"),
                "phase14.enumeration.challenge_commitment_hash",
            ),
            history_hash=_text(
                obj.get("history_hash"),
                "phase14.enumeration.history_hash",
            ),
            policy_seed_hash=_text(
                obj.get("policy_seed_hash"),
                "phase14.enumeration.policy_seed_hash",
            ),
            programs=tuple(
                Phase14MutationProgram.from_json(item)
                for item in raw_programs
            ),
            package_tree_hash_before=_text(
                obj.get("package_tree_hash_before"),
                "phase14.enumeration.package_tree_hash_before",
            ),
            package_tree_hash_after=_text(
                obj.get("package_tree_hash_after"),
                "phase14.enumeration.package_tree_hash_after",
            ),
        )

    @property
    def enumeration_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "contract_version": PHASE14_CONTRACT_VERSION,
            "active_semantic_package_hash": self.active_semantic_package_hash,
            "active_model_identity_hash": self.active_model_identity_hash,
            "generator_policy_hash": self.generator_policy_hash,
            "planner_policy_hash": self.planner_policy_hash,
            "challenge_commitment_hash": self.challenge_commitment_hash,
            "history_hash": self.history_hash,
            "policy_seed_hash": self.policy_seed_hash,
            "programs": [program.to_json() for program in self.programs],
            "package_tree_hash_before": self.package_tree_hash_before,
            "package_tree_hash_after": self.package_tree_hash_after,
            "package_generated": True,
            "host_selected_objective": False,
            "host_selected_successful_family": False,
        }


@dataclass(frozen=True, slots=True)
class Phase14AttemptSummary:
    global_attempt_index: int
    challenge_index: int
    challenge_commitment_hash: str
    local_attempt_index: int
    update_family: UpdateFamily
    program_variant: ProgramVariant
    program_hash: str
    proposal_enumeration_hash: str
    candidate_semantic_package_hash: str
    candidate_phase6_tree_hash: str
    verdict: str
    reason_codes: Sequence[str]
    hidden_task_report_hash: str
    gate_d_report_hash: str
    gate_e_report_hash: str
    recursive_productivity_report_hash: str
    active_store_package_hash_before: str
    active_store_package_hash_after: str
    phase7_ledger_entry_hash: str
    rejection_conditioned: bool

    schema_id: ClassVar[str] = "runtime.v4.phase14.attempt_summary.v1"

    def __post_init__(self) -> None:
        _nonnegative(self.global_attempt_index, "phase14.attempt.global_attempt_index")
        _nonnegative(self.challenge_index, "phase14.attempt.challenge_index")
        _nonnegative(self.local_attempt_index, "phase14.attempt.local_attempt_index")
        cast_update_family(self.update_family, "phase14.attempt.update_family")
        cast_program_variant(
            self.program_variant,
            "phase14.attempt.program_variant",
        )
        for name in (
            "challenge_commitment_hash",
            "program_hash",
            "proposal_enumeration_hash",
            "candidate_semantic_package_hash",
            "candidate_phase6_tree_hash",
            "hidden_task_report_hash",
            "gate_d_report_hash",
            "gate_e_report_hash",
            "recursive_productivity_report_hash",
            "active_store_package_hash_before",
            "active_store_package_hash_after",
            "phase7_ledger_entry_hash",
        ):
            validate_hash256(getattr(self, name), f"phase14.attempt.{name}")
        if self.verdict not in {"accept", "reject"}:
            raise SchemaValidationError("phase14.attempt.verdict", "unsupported verdict")
        object.__setattr__(
            self,
            "reason_codes",
            _ordered_unique(self.reason_codes, "phase14.attempt.reason_codes"),
        )
        if self.verdict == "accept" and self.reason_codes:
            raise SchemaValidationError("phase14.attempt.reason_codes", "accepted attempt has reasons")
        if self.verdict == "reject" and not self.reason_codes:
            raise SchemaValidationError("phase14.attempt.reason_codes", "rejected attempt requires reasons")

    @classmethod
    def from_json(cls, value: object) -> Phase14AttemptSummary:
        obj = _mapping(value, "phase14.attempt_summary")
        reasons = _sequence(
            obj.get("reason_codes"),
            "phase14.attempt_summary.reason_codes",
        )
        return cls(
            global_attempt_index=_nonnegative(
                obj.get("global_attempt_index"),
                "phase14.attempt_summary.global_attempt_index",
            ),
            challenge_index=_nonnegative(
                obj.get("challenge_index"),
                "phase14.attempt_summary.challenge_index",
            ),
            challenge_commitment_hash=_text(obj.get("challenge_commitment_hash"), "phase14.attempt_summary.challenge_commitment_hash"),
            local_attempt_index=_nonnegative(obj.get("local_attempt_index"), "phase14.attempt_summary.local_attempt_index"),
            update_family=cast_update_family(_text(obj.get("update_family"), "phase14.attempt_summary.update_family")),
            program_variant=cast_program_variant(
                _text(
                    obj.get("program_variant"),
                    "phase14.attempt_summary.program_variant",
                )
            ),
            program_hash=_text(obj.get("program_hash"), "phase14.attempt_summary.program_hash"),
            proposal_enumeration_hash=_text(obj.get("proposal_enumeration_hash"), "phase14.attempt_summary.proposal_enumeration_hash"),
            candidate_semantic_package_hash=_text(obj.get("candidate_semantic_package_hash"), "phase14.attempt_summary.candidate_semantic_package_hash"),
            candidate_phase6_tree_hash=_text(obj.get("candidate_phase6_tree_hash"), "phase14.attempt_summary.candidate_phase6_tree_hash"),
            verdict=_text(obj.get("verdict"), "phase14.attempt_summary.verdict"),
            reason_codes=tuple(str(item) for item in reasons),
            hidden_task_report_hash=_text(obj.get("hidden_task_report_hash"), "phase14.attempt_summary.hidden_task_report_hash"),
            gate_d_report_hash=_text(obj.get("gate_d_report_hash"), "phase14.attempt_summary.gate_d_report_hash"),
            gate_e_report_hash=_text(obj.get("gate_e_report_hash"), "phase14.attempt_summary.gate_e_report_hash"),
            recursive_productivity_report_hash=_text(obj.get("recursive_productivity_report_hash"), "phase14.attempt_summary.recursive_productivity_report_hash"),
            active_store_package_hash_before=_text(obj.get("active_store_package_hash_before"), "phase14.attempt_summary.active_store_package_hash_before"),
            active_store_package_hash_after=_text(obj.get("active_store_package_hash_after"), "phase14.attempt_summary.active_store_package_hash_after"),
            phase7_ledger_entry_hash=_text(obj.get("phase7_ledger_entry_hash"), "phase14.attempt_summary.phase7_ledger_entry_hash"),
            rejection_conditioned=bool(obj.get("rejection_conditioned")),
        )

    @property
    def summary_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "global_attempt_index": self.global_attempt_index,
            "challenge_index": self.challenge_index,
            "challenge_commitment_hash": self.challenge_commitment_hash,
            "local_attempt_index": self.local_attempt_index,
            "update_family": self.update_family,
            "program_variant": self.program_variant,
            "program_hash": self.program_hash,
            "proposal_enumeration_hash": self.proposal_enumeration_hash,
            "candidate_semantic_package_hash": self.candidate_semantic_package_hash,
            "candidate_phase6_tree_hash": self.candidate_phase6_tree_hash,
            "verdict": self.verdict,
            "reason_codes": list(self.reason_codes),
            "hidden_task_report_hash": self.hidden_task_report_hash,
            "gate_d_report_hash": self.gate_d_report_hash,
            "gate_e_report_hash": self.gate_e_report_hash,
            "recursive_productivity_report_hash": self.recursive_productivity_report_hash,
            "active_store_package_hash_before": self.active_store_package_hash_before,
            "active_store_package_hash_after": self.active_store_package_hash_after,
            "phase7_ledger_entry_hash": self.phase7_ledger_entry_hash,
            "rejection_conditioned": self.rejection_conditioned,
        }


__all__ = [
    "Phase14AttemptSummary",
    "Phase14MutationProgram",
    "Phase14ProposalEnumeration",
    "Phase14SearchHistory",
    "Phase14SearchHistoryEntry",
]
