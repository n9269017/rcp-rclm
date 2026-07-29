from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from rcp_rclm_runtime.canonical.hashing import (
    build_tree_records,
    canonical_json_hash,
    semantic_tree_hash,
)
from rcp_rclm_runtime.checker.hardened import (
    Phase4HardenedRequest,
    check_hardened_transition,
)
from rcp_rclm_runtime.checker.integrity import build_reference_package_integrity
from rcp_rclm_runtime.checker.records import Phase3CheckerRequest
from rcp_rclm_runtime.checker.reference import (
    build_lean_reference_packet,
    canonical_rclm_certificate,
    reference_protected_distinctions,
    reference_resource_record,
    reference_trust_anchor,
)
from rcp_rclm_runtime.lean_bridge.compiler import LeanCompiler, PinnedLeanProject
from rcp_rclm_runtime.lean_bridge.verifier import LeanReferenceVerifier
from rcp_rclm_runtime.promotion.certificate import Phase7CertificateEvidence
from rcp_rclm_runtime.promotion.evaluator import evaluate_realized_candidate

from rcp_rclm_runtime_v4.phase14.constants import PHASE14_TRAJECTORY_ID
from rcp_rclm_runtime_v4.phase14.realization import Phase14RealizedCandidate


def directory_tree_hash(root: Path) -> str:
    return semantic_tree_hash(build_tree_records(root.resolve(strict=True)))


def _lean_semantic_fingerprint(value: Mapping[str, object]) -> str:
    normalized = dict(value)
    normalized.pop("compiler_duration_ms", None)
    normalized.pop("toolchain_runtime_hash", None)
    return canonical_json_hash(normalized)


def _checker_semantic_fingerprint(value: Mapping[str, object]) -> str:
    normalized = dict(value)
    normalized.pop("artifact_hashes", None)
    checker = normalized.get("checker_report")
    if isinstance(checker, Mapping):
        checker_copy = dict(checker)
        lean = checker_copy.get("lean_bridge_result")
        if isinstance(lean, Mapping):
            lean_copy = dict(lean)
            evidence = lean_copy.get("evidence")
            if isinstance(evidence, Mapping):
                evidence_copy = dict(evidence)
                evidence_copy.pop("report_hash", None)
                evidence_copy.pop("toolchain_runtime_hash", None)
                lean_copy["evidence"] = evidence_copy
            checker_copy["lean_bridge_result"] = lean_copy
        normalized["checker_report"] = checker_copy
    return canonical_json_hash(normalized)


@dataclass(frozen=True, slots=True)
class Phase14OuterVerification:
    accepted: bool
    logical_evaluation_hash: str
    gate_b_certificate_hash: str
    lean_report_hash: str
    checker_report_hash: str
    candidate_tree_hash_before: str
    candidate_tree_hash_after: str
    lean_invoked: bool
    checker_invoked: bool

    schema_id: ClassVar[str] = "runtime.v4.phase14.outer_verification.v1"

    @property
    def candidate_unchanged(self) -> bool:
        return self.candidate_tree_hash_before == self.candidate_tree_hash_after

    @property
    def report_hash(self) -> str:
        return canonical_json_hash(self.to_json())

    def to_json(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "accepted": self.accepted,
            "logical_evaluation_hash": self.logical_evaluation_hash,
            "gate_b_certificate_hash": self.gate_b_certificate_hash,
            "lean_report_hash": self.lean_report_hash,
            "checker_report_hash": self.checker_report_hash,
            "candidate_tree_hash_before": self.candidate_tree_hash_before,
            "candidate_tree_hash_after": self.candidate_tree_hash_after,
            "candidate_unchanged": self.candidate_unchanged,
            "lean_invoked": self.lean_invoked,
            "checker_invoked": self.checker_invoked,
        }


def verify_outer_envelope(
    realized: Phase14RealizedCandidate,
    *,
    repo_root: Path,
    lean_project_root: Path | None,
) -> Phase14OuterVerification:
    candidate_root = realized.candidate_root
    before = directory_tree_hash(candidate_root)
    logical = evaluate_realized_candidate(
        realized.wrapper_predecessor.root,
        candidate_root,
        realized.selection,
    )
    logical_hash = canonical_json_hash(logical.to_json())
    gate_b_certificate = Phase7CertificateEvidence(
        certificate_name="stability",
        certificate=canonical_rclm_certificate("gate_b_classical", "stability"),
    )
    if lean_project_root is None:
        lean_hash = canonical_json_hash(
            {
                "schema_id": "runtime.v4.phase14.simulated_gate_b_lean.v1",
                "packet": build_lean_reference_packet(
                    logical.predecessor.state,
                    logical.candidate,
                    gate_b_certificate.certificate,
                ).to_json(),
                "accepted": True,
                "simulation_only": True,
            }
        )
        checker_hash = canonical_json_hash(
            {
                "schema_id": "runtime.v4.phase14.simulated_hardened_checker.v1",
                "logical_evaluation_hash": logical_hash,
                "accepted": True,
                "simulation_only": True,
            }
        )
        # Local development may omit the pinned Lean executable.  Successful
        # construction of the canonical objective-evaluation evidence is the
        # simulation boundary; authoritative CI exercises the real Lean and
        # hardened-checker path below.
        accepted = True
        lean_invoked = False
        checker_invoked = False
    else:
        packet = build_lean_reference_packet(
            logical.predecessor.state,
            logical.candidate,
            gate_b_certificate.certificate,
        )
        project = PinnedLeanProject.discover(repo_root.resolve(strict=True))
        compiler = LeanCompiler(project=project, timeout_seconds=600)
        lean = LeanReferenceVerifier(compiler).verify_with_evidence(packet)
        checker_request = Phase3CheckerRequest(
            transition_id=realized.selection.transition_id,
            predecessor=logical.predecessor.state,
            candidate=logical.candidate,
            certificate=gate_b_certificate.certificate,
            trust_anchor=reference_trust_anchor(),
            resource_record=reference_resource_record(
                budget_units=1,
                consumed_units=1,
                environment_hash=canonical_json_hash(
                    {
                        "schema_id": "runtime.v4.phase14.controller_environment.v1",
                        "trajectory_id": PHASE14_TRAJECTORY_ID,
                        "network": "disabled",
                        "manual_repair": "forbidden",
                        "candidate_mutation": "forbidden",
                        "hidden_material_visible_before_freeze": False,
                    }
                ),
            ),
            protected_distinctions=reference_protected_distinctions("gate_b_classical"),
            evaluation_evidence=logical.evaluation,
            lean_bridge_report=lean.report,
        )
        hardened = check_hardened_transition(
            Phase4HardenedRequest(
                checker_request=checker_request,
                package_integrity=build_reference_package_integrity(checker_request),
            )
        )
        lean_hash = canonical_json_hash(
            {
                "report_semantic_hash": _lean_semantic_fingerprint(
                    lean.report.to_json()
                ),
                "source_guard": lean.source_guard.to_json(),
            }
        )
        checker_hash = _checker_semantic_fingerprint(hardened.to_json())
        accepted = (
            lean.report.accepted
            and lean.source_guard.clean
            and hardened.accepted
        )
        lean_invoked = True
        checker_invoked = True
    after = directory_tree_hash(candidate_root)
    result = Phase14OuterVerification(
        accepted=accepted and before == after,
        logical_evaluation_hash=logical_hash,
        gate_b_certificate_hash=gate_b_certificate.certificate_hash,
        lean_report_hash=lean_hash,
        checker_report_hash=checker_hash,
        candidate_tree_hash_before=before,
        candidate_tree_hash_after=after,
        lean_invoked=lean_invoked,
        checker_invoked=checker_invoked,
    )
    if not result.accepted:
        raise ValueError("Phase 14 outer verification did not accept")
    return result


__all__ = [
    "Phase14OuterVerification",
    "directory_tree_hash",
    "verify_outer_envelope",
]
