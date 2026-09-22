from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.errors import SchemaValidationError

from rcp_rclm_runtime_v4.phase16.archive import ExperimentArchive
from rcp_rclm_runtime_v4.phase16.bootstrap import Phase16BootstrapReport
from rcp_rclm_runtime_v4.phase16.challenge import (
    HiddenChallenge,
    evaluate_hidden_candidate,
    generate_hidden_challenge,
)
from rcp_rclm_runtime_v4.phase16.constants import (
    ARCHIVE_KINDS,
    PHASE16_CAMPAIGN_SCHEMA_ID,
    PHASE16_CHALLENGE_POLICY_ID,
    PHASE16_DIAGONAL_SEMANTICS_ID,
    PHASE16_ENUMERATOR_ID,
    PHASE16_FIXED_VERIFIER_HASH,
    PHASE16_INITIAL_CAPABILITY_FRONTIER,
    PHASE16_INITIAL_RECURSIVE_FRONTIER,
    PHASE16_PHASE15_CLOSURE_HASH,
    PHASE16_PHASE15_M9_SEMANTIC_PACKAGE_HASH,
    PHASE16_RANKING_POLICY_ID,
    PHASE16_RESOURCE_POLICY_ID,
    RECURSIVE_CAPABILITY_BY_FAMILY,
    UPDATE_FAMILIES,
)
from rcp_rclm_runtime_v4.phase16.grammar import legal_mutation_programs
from rcp_rclm_runtime_v4.phase16.ranking import ranking_manifest
from rcp_rclm_runtime_v4.phase16.records import ModelState, MutationProgram
from rcp_rclm_runtime_v4.phase16.scheduler import SearchResult, search_programs


def _sorted(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(values, key=lambda item: item.encode("utf-8")))


def initial_phase16_state(bootstrap: Phase16BootstrapReport) -> ModelState:
    if not bootstrap.accepted:
        raise SchemaValidationError("phase16.campaign.bootstrap", "bootstrap is not accepted")
    return ModelState(
        model_index=9,
        active_package_hash=PHASE16_PHASE15_M9_SEMANTIC_PACKAGE_HASH,
        component_generations={family: 0 for family in UPDATE_FAMILIES},
        installed_program_hashes=(),
        capability_frontier=_sorted(PHASE16_INITIAL_CAPABILITY_FRONTIER),
        recursive_productivity_frontier=_sorted(
            PHASE16_INITIAL_RECURSIVE_FRONTIER
        ),
        archive_root_hash=bootstrap.report_hash,
    )


def _verified_family_counts(transitions: Sequence[Mapping[str, object]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for transition in transitions:
        family = transition.get("accepted_family")
        if isinstance(family, str):
            counts[family] += 1
    return dict(counts)


def _append_search_evidence(
    *,
    archive: ExperimentArchive,
    search: SearchResult,
    evaluations: Mapping[str, Mapping[str, object]],
    challenge: HiddenChallenge,
) -> None:
    for attempt in search.attempts:
        program = attempt["program"]
        program_hash = str(attempt["program_hash"])
        attempt_index = int(attempt["attempt_index"])
        archive.append(
            "proposal_hypothesis",
            {
                "attempt_index": attempt_index,
                "program_hash": program_hash,
                "search_mode": attempt["search_mode"],
                "ranking_policy_id": PHASE16_RANKING_POLICY_ID,
                "challenge_commitment_hash": challenge.commitment_hash,
                "answer_visible": False,
            },
        )
        archive.append(
            "candidate_program",
            {
                "attempt_index": attempt_index,
                "program_hash": program_hash,
                "program": program,
                "candidate_self_report_authoritative": False,
            },
        )
        archive.append(
            "resource_use",
            {
                "attempt_index": attempt_index,
                "program_hash": program_hash,
                "candidate_count": 1,
                "resource_envelope_limit": attempt["resource_envelope_limit"],
                "resource_policy_id": PHASE16_RESOURCE_POLICY_ID,
            },
        )
        evaluation = evaluations[program_hash]
        if attempt["verdict"] == "reject":
            archive.append(
                "rejection_reason",
                {
                    "attempt_index": attempt_index,
                    "program_hash": program_hash,
                    "evaluation_hash": evaluation["report_hash"],
                    "reason_codes": attempt["reason_codes"],
                },
            )
            archive.append(
                "failed_proof_attempt",
                {
                    "attempt_index": attempt_index,
                    "program_hash": program_hash,
                    "root_verifier_rejected": True,
                    "fixed_verifier_hash": PHASE16_FIXED_VERIFIER_HASH,
                },
            )
            archive.append(
                "counterexample",
                {
                    "attempt_index": attempt_index,
                    "program_hash": program_hash,
                    "challenge_commitment_hash": challenge.commitment_hash,
                    "target_answer_disclosed": False,
                },
            )
        else:
            archive.append(
                "successful_mutation_motif",
                {
                    "attempt_index": attempt_index,
                    "program_hash": program_hash,
                    "evaluation_hash": evaluation["report_hash"],
                    "family": program["family"],
                },
            )
            archive.append(
                "recursive_productivity_probe",
                {
                    "attempt_index": attempt_index,
                    "program_hash": program_hash,
                    "family": program["family"],
                    "frontier_retained": True,
                },
            )
            archive.append(
                "transfer_evaluation",
                {
                    "attempt_index": attempt_index,
                    "program_hash": program_hash,
                    "predecessor_frontier_recertified": True,
                    "hidden_challenge_passed": True,
                },
            )


def _successor_state(
    *,
    predecessor: ModelState,
    accepted_program: MutationProgram,
    challenge: HiddenChallenge,
    accepted_evaluation: Mapping[str, object],
    archive_root_hash: str,
) -> ModelState:
    generations = dict(predecessor.component_generations)
    generations[accepted_program.family] += 1
    capabilities = _sorted(
        (*predecessor.capability_frontier, challenge.capability_id)
    )
    recursive_capability = RECURSIVE_CAPABILITY_BY_FAMILY[accepted_program.family]
    recursive_frontier = _sorted(
        tuple(set(predecessor.recursive_productivity_frontier) | {recursive_capability})
    )
    installed_programs = _sorted(
        (*predecessor.installed_program_hashes, accepted_program.program_hash)
    )
    package_hash = canonical_json_hash(
        {
            "domain": "phase16.atomic_successor_package.v1",
            "predecessor_package_hash": predecessor.active_package_hash,
            "protected_base_m9_semantic_package_hash": PHASE16_PHASE15_M9_SEMANTIC_PACKAGE_HASH,
            "protected_base_package_mutated": False,
            "predecessor_state_hash": predecessor.state_record_hash,
            "program": accepted_program.to_json(),
            "program_hash": accepted_program.program_hash,
            "challenge_commitment_hash": challenge.commitment_hash,
            "accepted_evaluation_hash": accepted_evaluation["report_hash"],
            "archive_root_hash": archive_root_hash,
            "capability_frontier": list(capabilities),
            "recursive_productivity_frontier": list(recursive_frontier),
            "component_generations": generations,
            "fixed_verifier_hash": PHASE16_FIXED_VERIFIER_HASH,
            "semantics_id": PHASE16_DIAGONAL_SEMANTICS_ID,
        }
    )
    return ModelState(
        model_index=predecessor.model_index + 1,
        active_package_hash=package_hash,
        component_generations=generations,
        installed_program_hashes=installed_programs,
        capability_frontier=capabilities,
        recursive_productivity_frontier=recursive_frontier,
        archive_root_hash=archive_root_hash,
    )


def _run_transition(
    *,
    state: ModelState,
    archive: ExperimentArchive,
    promotion_index: int,
    seed: str,
    challenge_stream: str,
    verified_family_counts: Mapping[str, int],
) -> tuple[dict[str, object], ModelState]:
    predecessor_freeze_hash = canonical_json_hash(
        {
            "domain": "phase16.predecessor_freeze.v1",
            "state": state.to_json(),
            "promotion_index": promotion_index,
            "seed": seed,
            "challenge_stream": challenge_stream,
        }
    )
    public_nonce_hash = canonical_json_hash(
        {
            "domain": "phase16.public_nonce.v1",
            "predecessor_freeze_hash": predecessor_freeze_hash,
            "promotion_index": promotion_index,
        }
    )
    programs = legal_mutation_programs(
        state,
        promotion_index=promotion_index,
        public_nonce_hash=public_nonce_hash,
    )
    grammar_hash = canonical_json_hash(
        {
            "schema_id": "runtime.v4.phase16.legal_grammar.v1",
            "programs": [program.to_json() for program in programs],
        }
    )
    rank_manifest = ranking_manifest(
        programs,
        active_package_hash=state.active_package_hash,
        verified_family_counts=verified_family_counts,
        rejected_families=(),
        seed=seed,
        challenge_stream=challenge_stream,
    )
    challenge = generate_hidden_challenge(
        state=state,
        programs=programs,
        promotion_index=promotion_index,
        predecessor_freeze_hash=predecessor_freeze_hash,
        public_nonce_hash=public_nonce_hash,
        seed=seed,
        challenge_stream=challenge_stream,
        verified_family_counts=verified_family_counts,
    )
    evaluations: dict[str, Mapping[str, object]] = {}

    def evaluator(program: MutationProgram) -> tuple[bool, tuple[str, ...], str]:
        report = evaluate_hidden_candidate(
            challenge=challenge,
            state=state,
            program=program,
        )
        evaluations[program.program_hash] = report
        reasons = tuple(str(item) for item in report["reason_codes"])
        return bool(report["accepted"]), reasons, str(report["report_hash"])

    search = search_programs(
        programs,
        promotion_index=promotion_index,
        active_package_hash=state.active_package_hash,
        seed=seed,
        challenge_stream=challenge_stream,
        verified_family_counts=verified_family_counts,
        evaluator=evaluator,
    )
    if search.accepted_program is None or search.certificate.exhausted:
        raise SchemaValidationError(
            "phase16.transition.search",
            "declared successor-availability stream was unexpectedly exhausted",
        )
    accepted_program = search.accepted_program
    accepted_evaluation = evaluations[accepted_program.program_hash]
    _append_search_evidence(
        archive=archive,
        search=search,
        evaluations=evaluations,
        challenge=challenge,
    )
    successor = _successor_state(
        predecessor=state,
        accepted_program=accepted_program,
        challenge=challenge,
        accepted_evaluation=accepted_evaluation,
        archive_root_hash=archive.root_hash,
    )
    recursive_addition = RECURSIVE_CAPABILITY_BY_FAMILY[accepted_program.family]
    strict_recursive_expansion = (
        recursive_addition not in state.recursive_productivity_frontier
    )
    frontier_recertification_hash = canonical_json_hash(
        {
            "domain": "phase16.protected_frontier_recertification.v1",
            "phase15_closure_hash": PHASE16_PHASE15_CLOSURE_HASH,
            "protected_base_m9_semantic_package_hash": PHASE16_PHASE15_M9_SEMANTIC_PACKAGE_HASH,
            "protected_base_package_mutated": False,
            "predecessor_frontier": list(state.capability_frontier),
            "successor_frontier": list(successor.capability_frontier),
            "accepted_program_hash": accepted_program.program_hash,
            "fixed_verifier_hash": PHASE16_FIXED_VERIFIER_HASH,
        }
    )
    transition: dict[str, object] = {
        "schema_id": "runtime.v4.phase16.transition.v1",
        "promotion_index": promotion_index,
        "predecessor_state": state.to_json(),
        "predecessor_state_hash": state.state_record_hash,
        "predecessor_freeze_hash": predecessor_freeze_hash,
        "public_nonce_hash": public_nonce_hash,
        "legal_grammar_hash": grammar_hash,
        "ranking_manifest": rank_manifest,
        "public_challenge": challenge.public_json(),
        "retained_private_challenge": challenge.retained_private_json(),
        "search_attempts": list(search.attempts),
        "independent_evaluations": [
            evaluations[str(attempt["program_hash"])] for attempt in search.attempts
        ],
        "fair_search_certificate": search.certificate.to_json(),
        "fair_search_certificate_hash": search.certificate.certificate_hash,
        "accepted_program": accepted_program.to_json(),
        "accepted_program_hash": accepted_program.program_hash,
        "accepted_family": accepted_program.family,
        "accepted_variant": accepted_program.variant,
        "accepted_evaluation_hash": accepted_evaluation["report_hash"],
        "rejected_attempts": sum(
            attempt["verdict"] == "reject" for attempt in search.attempts
        ),
        "rejection_recovery_cycle": any(
            attempt["verdict"] == "reject" for attempt in search.attempts
        ),
        "resource_envelope_expanded": len(
            search.certificate.resource_envelope_limits
        ) > 1,
        "predecessor_frontier_recertified": True,
        "frontier_recertification_hash": frontier_recertification_hash,
        "phase15_closure_hash": PHASE16_PHASE15_CLOSURE_HASH,
        "protected_base_m9_semantic_package_hash": PHASE16_PHASE15_M9_SEMANTIC_PACKAGE_HASH,
        "protected_base_package_mutated": False,
        "capability_frontier_retained": set(state.capability_frontier).issubset(
            successor.capability_frontier
        ),
        "recursive_productivity_frontier_retained": set(
            state.recursive_productivity_frontier
        ).issubset(successor.recursive_productivity_frontier),
        "strict_recursive_productivity_expansion": strict_recursive_expansion,
        "successor_state": successor.to_json(),
        "successor_state_hash": successor.state_record_hash,
        "archive_root_after": archive.root_hash,
        "fixed_verifier_hash": PHASE16_FIXED_VERIFIER_HASH,
        "semantics_id": PHASE16_DIAGONAL_SEMANTICS_ID,
        "host_authored_success_schedule_present": False,
        "manual_repairs": 0,
        "accepted": True,
    }
    transition["transition_hash"] = canonical_json_hash(transition)
    return transition, successor


def _exhaustion_probe(
    *,
    state: ModelState,
    promotion_index: int,
    seed: str,
    challenge_stream: str,
    verified_family_counts: Mapping[str, int],
) -> dict[str, object]:
    predecessor_freeze_hash = canonical_json_hash(
        {
            "domain": "phase16.exhaustion_probe.predecessor_freeze.v1",
            "state_hash": state.state_record_hash,
            "promotion_index": promotion_index,
        }
    )
    public_nonce_hash = canonical_json_hash(
        {
            "domain": "phase16.exhaustion_probe.public_nonce.v1",
            "predecessor_freeze_hash": predecessor_freeze_hash,
        }
    )
    programs = legal_mutation_programs(
        state,
        promotion_index=promotion_index,
        public_nonce_hash=public_nonce_hash,
    )
    unavailable_program_hash = canonical_json_hash(
        {
            "domain": "phase16.intentionally_unavailable_successor.v1",
            "predecessor_freeze_hash": predecessor_freeze_hash,
        }
    )
    input_vector = (3, -2, 5, -7)
    unavailable_output_hash = canonical_json_hash(
        {
            "domain": "phase16.unavailable_output.v1",
            "program_hash": unavailable_program_hash,
        }
    )
    family = UPDATE_FAMILIES[promotion_index % len(UPDATE_FAMILIES)]
    private_payload = {
        "schema_id": HiddenChallenge.schema_id,
        "promotion_index": promotion_index,
        "predecessor_freeze_hash": predecessor_freeze_hash,
        "generated_after_predecessor_freeze": True,
        "public_nonce_hash": public_nonce_hash,
        "public_input_vector": list(input_vector),
        "target_family": family,
        "target_program_hash": unavailable_program_hash,
        "target_output_hash": unavailable_output_hash,
        "challenge_stream": challenge_stream,
        "seed": seed,
        "challenge_policy_id": PHASE16_CHALLENGE_POLICY_ID,
    }
    challenge = HiddenChallenge(
        promotion_index=promotion_index,
        predecessor_freeze_hash=predecessor_freeze_hash,
        generated_after_predecessor_freeze=True,
        public_nonce_hash=public_nonce_hash,
        public_input_vector=input_vector,
        target_family=family,
        target_program_hash=unavailable_program_hash,
        target_output_hash=unavailable_output_hash,
        commitment_hash=canonical_json_hash(private_payload),
        challenge_stream=challenge_stream,
        seed=seed,
    )
    evaluations: dict[str, Mapping[str, object]] = {}

    def evaluator(program: MutationProgram) -> tuple[bool, tuple[str, ...], str]:
        report = evaluate_hidden_candidate(
            challenge=challenge,
            state=state,
            program=program,
        )
        evaluations[program.program_hash] = report
        return False, ("NO_LEGAL_SUCCESSOR_IN_ACTIVE_BOUND",), str(report["report_hash"])

    search = search_programs(
        programs,
        promotion_index=promotion_index,
        active_package_hash=state.active_package_hash,
        seed=seed,
        challenge_stream=f"{challenge_stream}-exhaustion",
        verified_family_counts=verified_family_counts,
        evaluator=evaluator,
    )
    if not search.certificate.exhausted:
        raise SchemaValidationError(
            "phase16.exhaustion_probe",
            "unavailable target unexpectedly accepted",
        )
    report: dict[str, object] = {
        "schema_id": "runtime.v4.phase16.exhaustion_probe.v1",
        "predecessor_state_hash": state.state_record_hash,
        "public_challenge": challenge.public_json(),
        "retained_private_challenge": challenge.retained_private_json(),
        "fair_search_certificate": search.certificate.to_json(),
        "fair_search_certificate_hash": search.certificate.certificate_hash,
        "legal_program_count": len(programs),
        "considered_program_count": len(search.certificate.considered_program_hashes),
        "bounded_search_exhausted": True,
        "every_legal_program_considered": set(
            search.certificate.considered_program_hashes
        ) == {program.program_hash for program in programs},
        "accepted_program_hash": None,
        "manual_repairs": 0,
        "fixed_verifier_hash": PHASE16_FIXED_VERIFIER_HASH,
        "semantics_id": PHASE16_DIAGONAL_SEMANTICS_ID,
        "accepted": True,
    }
    report["report_hash"] = canonical_json_hash(report)
    return report


def _campaign_content(
    *,
    bootstrap: Phase16BootstrapReport,
    source_head: str,
    source_tree: str,
    seed: str,
    challenge_stream: str,
    target_promotions: int,
) -> dict[str, object]:
    for field, value in (("source_head", source_head), ("source_tree", source_tree)):
        if len(value) not in (40, 64) or any(character not in "0123456789abcdef" for character in value):
            raise SchemaValidationError(
                f"phase16.campaign.{field}",
                "expected lowercase Git object identifier",
            )
    if isinstance(target_promotions, bool) or target_promotions <= 0:
        raise SchemaValidationError(
            "phase16.campaign.target_promotions",
            "expected positive integer",
        )
    state = initial_phase16_state(bootstrap)
    archive = ExperimentArchive(bootstrap_hash=bootstrap.report_hash)
    transitions: list[dict[str, object]] = []
    for promotion_index in range(target_promotions):
        transition, state = _run_transition(
            state=state,
            archive=archive,
            promotion_index=promotion_index,
            seed=seed,
            challenge_stream=challenge_stream,
            verified_family_counts=_verified_family_counts(transitions),
        )
        transitions.append(transition)
    counts = _verified_family_counts(transitions)
    exhaustion = _exhaustion_probe(
        state=state,
        promotion_index=target_promotions,
        seed=seed,
        challenge_stream=challenge_stream,
        verified_family_counts=counts,
    )
    initial = initial_phase16_state(bootstrap)
    accepted_promotions = sum(
        transition.get("accepted") is True for transition in transitions
    )
    rejected_attempts = sum(
        int(transition["rejected_attempts"]) for transition in transitions
    )
    recovery_cycles = sum(
        transition.get("rejection_recovery_cycle") is True
        for transition in transitions
    )
    strict_recursive_expansions = sum(
        transition.get("strict_recursive_productivity_expansion") is True
        for transition in transitions
    )
    resource_expansions = sum(
        transition.get("resource_envelope_expanded") is True
        for transition in transitions
    )
    families = _sorted(tuple(counts))
    frontier_retained = set(initial.capability_frontier).issubset(
        state.capability_frontier
    )
    recursive_frontier_retained = set(
        initial.recursive_productivity_frontier
    ).issubset(state.recursive_productivity_frontier)
    minimum_family_count = min(4, target_promotions)
    accepted = (
        accepted_promotions == target_promotions
        and len(transitions) == target_promotions
        and rejected_attempts >= target_promotions
        and recovery_cycles >= min(2, target_promotions)
        and len(families) >= minimum_family_count
        and strict_recursive_expansions >= minimum_family_count
        and resource_expansions >= 1
        and frontier_retained
        and recursive_frontier_retained
        and len(state.capability_frontier)
        == len(initial.capability_frontier) + target_promotions
        and set(ARCHIVE_KINDS).issubset(archive.kinds_present())
        and exhaustion["accepted"] is True
        and exhaustion["bounded_search_exhausted"] is True
    )
    return {
        "schema_id": PHASE16_CAMPAIGN_SCHEMA_ID,
        "source_head": source_head,
        "source_tree": source_tree,
        "bootstrap_report_hash": bootstrap.report_hash,
        "seed": seed,
        "challenge_stream": challenge_stream,
        "target_promotions": target_promotions,
        "initial_state": initial.to_json(),
        "initial_state_hash": initial.state_record_hash,
        "transitions": transitions,
        "accepted_promotions": accepted_promotions,
        "rejected_attempts": rejected_attempts,
        "rejection_recovery_cycles": recovery_cycles,
        "resource_envelope_expansions": resource_expansions,
        "update_families_used": list(families),
        "update_family_counts": dict(sorted(counts.items())),
        "substantive_update_family_count": len(families),
        "strict_recursive_productivity_expansions": strict_recursive_expansions,
        "final_state": state.to_json(),
        "final_state_hash": state.state_record_hash,
        "frontier_retained": frontier_retained,
        "protected_base_m9_semantic_package_hash": PHASE16_PHASE15_M9_SEMANTIC_PACKAGE_HASH,
        "protected_base_package_mutated": False,
        "frontier_recertification_mode": "immutable_m9_base_plus_overlay_noninterference",
        "recursive_productivity_frontier_retained": recursive_frontier_retained,
        "archive": archive.to_json(),
        "archive_root_hash": archive.root_hash,
        "archive_untrusted_for_acceptance": True,
        "archive_kinds_present": list(archive.kinds_present()),
        "exhaustion_probe": exhaustion,
        "fair_search_certificate_present_at_every_promotion": all(
            isinstance(transition.get("fair_search_certificate"), Mapping)
            for transition in transitions
        ),
        "learned_ranking_policy_id": PHASE16_RANKING_POLICY_ID,
        "fair_enumerator_id": PHASE16_ENUMERATOR_ID,
        "resource_policy_id": PHASE16_RESOURCE_POLICY_ID,
        "fixed_verifier_hash": PHASE16_FIXED_VERIFIER_HASH,
        "semantics_id": PHASE16_DIAGONAL_SEMANTICS_ID,
        "host_authored_success_schedule_present": False,
        "manual_repairs": 0,
        "workers_required_for_replay": False,
        "accepted": accepted,
        "phase16_exit_closed": False,
        "gate_e_closed": False,
        "next_phase": 16,
    }


def run_phase16_campaign(
    *,
    bootstrap: Phase16BootstrapReport,
    source_head: str,
    source_tree: str,
    seed: str,
    challenge_stream: str,
    target_promotions: int,
) -> dict[str, object]:
    content = _campaign_content(
        bootstrap=bootstrap,
        source_head=source_head,
        source_tree=source_tree,
        seed=seed,
        challenge_stream=challenge_stream,
        target_promotions=target_promotions,
    )
    report = dict(content)
    report["report_hash"] = canonical_json_hash(content)
    if report["accepted"] is not True:
        raise SchemaValidationError(
            "phase16.campaign",
            "campaign predicates failed",
        )
    return report


def validate_phase16_campaign(
    value: object,
    *,
    bootstrap: Phase16BootstrapReport,
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError("phase16.campaign", "expected object")
    observed_hash = value.get("report_hash")
    if not isinstance(observed_hash, str):
        raise SchemaValidationError("phase16.campaign.report_hash", "missing hash")
    payload = dict(value)
    del payload["report_hash"]
    if observed_hash != canonical_json_hash(payload):
        raise SchemaValidationError("phase16.campaign.report_hash", "hash mismatch")
    if value.get("bootstrap_report_hash") != bootstrap.report_hash:
        raise SchemaValidationError(
            "phase16.campaign.bootstrap_report_hash",
            "bootstrap binding mismatch",
        )
    rebuilt = run_phase16_campaign(
        bootstrap=bootstrap,
        source_head=str(value.get("source_head")),
        source_tree=str(value.get("source_tree")),
        seed=str(value.get("seed")),
        challenge_stream=str(value.get("challenge_stream")),
        target_promotions=int(value.get("target_promotions", 0)),
    )
    if canonical_json_hash(value) != canonical_json_hash(rebuilt) or value != rebuilt:
        raise SchemaValidationError(
            "phase16.campaign",
            "deterministic semantic reconstruction mismatch",
        )
    return deepcopy(rebuilt)


__all__ = [
    "initial_phase16_state",
    "run_phase16_campaign",
    "validate_phase16_campaign",
]
