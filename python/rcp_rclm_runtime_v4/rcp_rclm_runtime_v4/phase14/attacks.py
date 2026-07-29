from __future__ import annotations

import copy
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError
from rcp_rclm_runtime_v4.gatee.records import RouteHintPolicy

from rcp_rclm_runtime_v4.phase14.candidate import (
    build_semantic_candidate,
    validate_semantic_candidate,
)
from rcp_rclm_runtime_v4.phase14.challenges import (
    answer_store_json,
    challenges_from_answer_store,
    development_challenge_suite,
)
from rcp_rclm_runtime_v4.phase14.constants import (
    PHASE14_OBJECTIVE_ID,
    PHASE14_ROUTE_MARKER,
    UPDATE_KINDS_BY_FAMILY,
)
from rcp_rclm_runtime_v4.phase14.proposal import slot_from_commitment
from rcp_rclm_runtime_v4.phase14.records import (
    Phase14MutationProgram,
    Phase14SearchHistoryEntry,
)
from rcp_rclm_runtime_v3.phase10.package import load_package_manifest


@dataclass(frozen=True, slots=True)
class Phase14AttackResult:
    attack_id: str
    rejected: bool
    reason: str

    schema_id: ClassVar[str] = "runtime.v4.phase14.attack_result.v1"

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "attack_id": self.attack_id,
            "rejected": self.rejected,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class Phase14AttackSuiteReport:
    cases: Sequence[Phase14AttackResult]

    schema_id: ClassVar[str] = "runtime.v4.phase14.attack_suite.v1"

    @property
    def accepted(self) -> bool:
        return len(self.cases) >= 8 and all(case.rejected for case in self.cases)

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.content_json())

    def content_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "cases": [case.to_json() for case in self.cases],
            "case_count": len(self.cases),
            "accepted": self.accepted,
        }

    def to_json(self) -> dict[str, object]:
        value = self.content_json()
        value["report_hash"] = self.report_hash
        return value

    @classmethod
    def from_json(cls, value: object) -> Phase14AttackSuiteReport:
        if not isinstance(value, dict):
            raise SchemaValidationError("phase14.attacks", "expected object")
        raw_cases = value.get("cases")
        if not isinstance(raw_cases, list):
            raise SchemaValidationError("phase14.attacks.cases", "expected array")
        cases: list[Phase14AttackResult] = []
        for index, item in enumerate(raw_cases):
            if not isinstance(item, dict):
                raise SchemaValidationError(
                    f"phase14.attacks.cases[{index}]",
                    "expected object",
                )
            cases.append(
                Phase14AttackResult(
                    attack_id=str(item["attack_id"]),
                    rejected=bool(item["rejected"]),
                    reason=str(item["reason"]),
                )
            )
        result = cls(cases=tuple(cases))
        if value.get("report_hash") != result.report_hash:
            raise SchemaValidationError(
                "phase14.attacks.report_hash",
                "content hash mismatch",
            )
        if value.get("accepted") is not result.accepted:
            raise SchemaValidationError(
                "phase14.attacks.accepted",
                "derived flag mismatch",
            )
        return result


def _expect_rejection(attack_id: str, action) -> Phase14AttackResult:
    try:
        action()
    except (SchemaValidationError, ValueError, FileNotFoundError) as exc:
        return Phase14AttackResult(
            attack_id=attack_id,
            rejected=True,
            reason=f"{type(exc).__name__}:{exc}",
        )
    return Phase14AttackResult(
        attack_id=attack_id,
        rejected=False,
        reason="attack unexpectedly accepted",
    )


def _valid_program(active_root: Path) -> Phase14MutationProgram:
    manifest = load_package_manifest(active_root)
    challenge = development_challenge_suite()[0]
    family = "memory_retrieval"
    return Phase14MutationProgram(
        active_semantic_package_hash=manifest.package_hash,
        active_model_identity_hash=manifest.model_identity_hash,
        active_generator_hash=manifest.generator_policy_hash,
        active_planner_hash=manifest.planner_policy_hash,
        challenge_commitment_hash=challenge.commitment_hash,
        history_hash=canonical_json_hash(
            {"schema_id": "runtime.v4.phase14.empty_history_attack_fixture.v1"}
        ),
        objective_id=PHASE14_OBJECTIVE_ID,
        update_family=family,
        variant="direct",
        slot_token_id=slot_from_commitment(challenge.commitment_hash),
        route_marker_token_id=PHASE14_ROUTE_MARKER,
        update_kinds=tuple(
            sorted(
                UPDATE_KINDS_BY_FAMILY[family],
                key=lambda item: item.encode("utf-8"),
            )
        ),
        search_cost=1,
    )


def run_phase14_attack_suite(
    *,
    m4_semantic_root: Path,
    repo_root: Path,
) -> Phase14AttackSuiteReport:
    root = m4_semantic_root.resolve(strict=True)
    program = _valid_program(root)
    cases: list[Phase14AttackResult] = []
    cases.append(
        _expect_rejection(
            "route_hint_expected_candidate_hash",
            lambda: RouteHintPolicy(expected_candidate_hash_present=True),
        )
    )
    cases.append(
        _expect_rejection(
            "heldout_challenge_leakage",
            lambda: replace(
                program,
                heldout_material_visible=True,
            ),
        )
    )
    cases.append(
        _expect_rejection(
            "manual_repair_marker",
            lambda: replace(
                program,
                manual_repair_count=1,
            ),
        )
    )
    wrong_kinds = ("weight_update",)
    if program.update_kinds == wrong_kinds:
        wrong_kinds = ("memory_update", "retrieval_update")
    cases.append(
        _expect_rejection(
            "update_family_forgery",
            lambda: replace(
                program,
                update_kinds=wrong_kinds,
            ),
        )
    )
    cases.append(
        _expect_rejection(
            "rejection_history_pointer_forgery",
            lambda: Phase14SearchHistoryEntry(
                sequence_number=0,
                challenge_commitment_hash=program.challenge_commitment_hash,
                attempt_index=0,
                update_family=program.update_family,
                program_variant=program.variant,
                program_hash=program.program_hash,
                candidate_semantic_package_hash=canonical_json_hash(
                    {"candidate": "forged"}
                ),
                verdict="reject",
                reason_codes=("FORGED_REJECTION",),
                active_package_hash_before=canonical_json_hash(
                    {"active": "before"}
                ),
                active_package_hash_after=canonical_json_hash(
                    {"active": "after"}
                ),
                rejection_evidence_hash=canonical_json_hash(
                    {"evidence": "forged"}
                ),
            ),
        )
    )

    answer_store = answer_store_json(development_challenge_suite())
    tampered_store = copy.deepcopy(answer_store)
    answers = tampered_store["answers"]
    if not isinstance(answers, list) or not isinstance(answers[0], dict):
        raise ValueError("attack fixture answer store is malformed")
    answers[0]["challenge_commitment_hash"] = canonical_json_hash(
        {"tampered": True}
    )
    cases.append(
        _expect_rejection(
            "private_answer_store_substitution",
            lambda: challenges_from_answer_store(tampered_store),
        )
    )

    proposal_source = (
        repo_root
        / "python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase14/proposal.py"
    ).read_text(encoding="utf-8")
    worker_source = (
        repo_root
        / "python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase14/proposal_worker.py"
    ).read_text(encoding="utf-8")

    forbidden = (
        "phase14.challenges",
        "answer_store_private",
        "theorem_statement",
        "successful_update_family",
    )
    observed = proposal_source + worker_source
    matches = tuple(item for item in forbidden if item in observed)
    cases.append(
        Phase14AttackResult(
            attack_id="proposal_worker_private_source_access",
            rejected=not matches,
            reason=(
                "private challenge source dependency absent"
                if not matches
                else f"private challenge dependency present: {matches}"
            ),
        )
    )
    cases.append(
        _expect_rejection(
            "direct_route_marker_forgery",
            lambda: replace(
                program,
                route_marker_token_id=program.slot_token_id,
            ),
        )
    )
    cases.append(
        _expect_rejection(
            "probe_route_marker_forgery",
            lambda: replace(
                program,
                variant="probe",
                route_marker_token_id=PHASE14_ROUTE_MARKER,
            ),
        )
    )

    with tempfile.TemporaryDirectory(prefix="rcp-rclm-phase14-attack-") as temporary:
        candidate = build_semantic_candidate(
            root,
            program,
            Path(temporary) / "candidate",
        )
        tamper_path = candidate.root / "policies/resource_policy.json"
        tamper_path.write_bytes(tamper_path.read_bytes() + b"\n")
        cases.append(
            _expect_rejection(
                "post_freeze_candidate_mutation",
                lambda: validate_semantic_candidate(root, candidate),
            )
        )

    result = Phase14AttackSuiteReport(cases=tuple(cases))
    if not result.accepted:
        raise SchemaValidationError(
            "phase14.attacks",
            "one or more attacks did not reject",
        )
    return result


__all__ = [
    "Phase14AttackResult",
    "Phase14AttackSuiteReport",
    "run_phase14_attack_suite",
]
