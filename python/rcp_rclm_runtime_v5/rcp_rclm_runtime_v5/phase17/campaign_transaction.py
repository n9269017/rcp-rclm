"""Online bounded sessions under one persistent external resource authority.

These are repeated evaluations of a fixed historical predecessor, not accepted
self-improvement transitions. There is no active model update or promotion.
The session ordinal is history, not a target trajectory length or winning route.
"""
from __future__ import annotations
import os
from pathlib import Path
import secrets

from rcp_rclm_runtime.canonical.json import load_json_strict
from .bootstrap import HistoricalPredecessor, reopen_phase16
from .campaign_budget import CampaignAuthority, context, replay
from .campaign_client import CampaignEvaluatorClient
from .challenge_protocol import digest, realize_candidate, reference_grammar, require, CLAIMS
from .controller import Action, checkpoint, decide, record_evaluation, restore, FIXED_VERIFIER
from .objectives import select_bootstrap_objective, freeze_bootstrap_objective
from .phase16_adapter import bind_phase16_search
from .resource_ledger import Policy, canonical, sha, exact, nat

FALSE_CLAIMS = {name: False for name in (
    'complete_resource_accounting', 'os_resource_containment', 'historical_cost_recovered',
    'physical_execution_attested', 'physical_projection_formally_verified', 'root_transition_verified',
    'promotion_authorized', 'promotion_performed', 'phase17_exit_closed', 'gate_e_closed', 'egc0_started',
    'live_capability_gain_demonstrated', 'recursive_productivity_recertified', 'full_frontier_recertified',
    'full_learned_step_instantiated', 'complete_learned_kernel_constructed', 'campaign_budget_authority_integrated',
    'full_goal_interpretation_supplied', 'full_information_interpretation_supplied', 'training_performed',
    'old_proofs_rerun', 'github_hosted_ci_passed', 'cross_platform_validation', 'phase18_independent_replay',
)}

UNMEASURED = ['cpu_time', 'accelerator_time', 'memory', 'storage', 'energy',
              'bootstrap_and_validation', 'journal_io', 'python_runtime_overhead',
              'formal_verification', 'ipc_and_process_startup', 'transcript_recomputation']


def load_predecessor(root: Path) -> HistoricalPredecessor:
    return reopen_phase16(
        capture_archive=root / 'artifacts/development/phase17b/phase16-capture-31153935872-1.zip',
        closure_archive=root / ('artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/'
                                'runtime-v4-phase16-final-closure-31153935872-1.zip'),
        phase15_bundle=root / 'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip')


def context_for(parent: HistoricalPredecessor, campaign_id: str) -> dict:
    require(type(parent) is HistoricalPredecessor, 'historical predecessor required')
    parent.validate()
    return context({'campaign_id': campaign_id, 'predecessor_state_hash': digest(parent.state),
                    'predecessor_package_hash': parent.state['active_package_hash'],
                    'fixed_verifier_hash': FIXED_VERIFIER, 'installed_count': len(parent.accepted_programs)})


def check_controller(predecessor: HistoricalPredecessor, transcript: bytes) -> bytes:
    """Check proposal order against the actual unchanged controller and adapter."""
    events = load_json_strict(transcript)['events']
    public = events[0]['response']['payload']['public_challenge']
    binding = bind_phase16_search(predecessor.phase16_state(), turn_index=public['turn_index'],
        challenge_commitment_hash=public['challenge_commitment_hash'],
        public_nonce_hash=public['public_nonce_hash'], candidate_credits=public['candidate_credits'])
    expected = list(reference_grammar(predecessor.state, public['turn_index'], public['public_nonce_hash']))
    actual = [q.to_json() for q in sorted(binding.programs.values(), key=lambda q: q.program_hash)]
    require(actual == expected and digest(actual) == public['grammar_hash'], 'independent grammar mismatch')
    prefix = binding.prefix
    for event in events[1:]:
        req, response = event['request'], event['response']['payload']
        if req['op'] == 'freeze_candidate':
            step = decide(prefix)
            require(step.action == Action.EVALUATE and req['program_hash'] == step.candidate_hash,
                    'proposal not the present controller choice')
        elif req['op'] == 'evaluate':
            step = decide(prefix)
            require(step.action == Action.EVALUATE and response['program_hash'] == step.candidate_hash,
                    'evaluation not the present controller choice')
            prefix = record_evaluation(prefix, step, verdict=response['verdict'],
                evaluation_hash=response['evaluation_hash'], reason_codes=response['reason_codes'],
                predecessor_state_hash=response['predecessor_state_hash'],
                challenge_commitment_hash=response['challenge_commitment_hash'])
        elif req['op'] == 'seal':
            action = decide(prefix).action
            require(response['terminal_action'] == action.value if action != Action.EVALUATE else
                    response['terminal_action'] in (Action.EXTERNAL_STOP.value, Action.SAFETY_HALT.value),
                    'controller terminal differs')
    raw = checkpoint(prefix)
    require(restore(raw, expected_prefix_hash=prefix.prefix_hash) == prefix, 'checkpoint round trip differs')
    return raw


def run_campaign_session(authority: CampaignAuthority, predecessor: HistoricalPredecessor, *,
                         candidate_credits: int, public_nonce_hash: str | None = None,
                         prior_sessions: dict[str, dict[str, bytes]] | None = None) -> dict[str, bytes]:
    """One new worker, once. No retries, winning-seed choice, promotion or reset.

    public_nonce_hash is present public context, not the worker's hidden entropy.
    It never supplies a challenge seed, objective family, successful route or
    desired number of promotions. None is an argument of this function.
    """
    require(type(authority) is CampaignAuthority, 'exact campaign authority required')
    require(authority.context == context_for(predecessor, authority.context['campaign_id']), 'wrong campaign parent')
    before = authority.state
    require(before.status == 'open', 'campaign unresolved or terminated')
    audit_campaign(predecessor, authority.journal_bytes(), expected_head=before.head,
                   policy=authority.policy, expected_context=authority.context,
                   sessions={} if prior_sessions is None else prior_sessions)
    nonce = secrets.token_hex(32) if public_nonce_hash is None else public_nonce_hash
    index = before.session_count
    objective = select_bootstrap_objective(predecessor, turn_index=index, public_nonce_hash=nonce)
    freeze = freeze_bootstrap_objective(objective, predecessor, turn_index=index, public_nonce_hash=nonce)
    grant = authority.reserve(objective_freeze_hash=freeze['freeze_hash'], candidate_credits=candidate_credits)
    reservation_head = authority.state.head
    # Nothing below may launch until reserve has successfully persisted and fsynced.
    try:
        with CampaignEvaluatorClient(grant) as worker:
            public = worker.request('open', objective=objective.to_json(), freeze=freeze,
                                    candidate_credits=candidate_credits)['public_challenge']
            binding = bind_phase16_search(predecessor.phase16_state(), turn_index=index,
                challenge_commitment_hash=public['challenge_commitment_hash'],
                public_nonce_hash=nonce, candidate_credits=candidate_credits)
            actual = [q.to_json() for q in sorted(binding.programs.values(), key=lambda q: q.program_hash)]
            require(actual == list(reference_grammar(predecessor.state, index, nonce)) and
                    digest(actual) == public['grammar_hash'], 'grammar disagreement')
            prefix = binding.prefix
            while decide(prefix).action == Action.EVALUATE:
                step = decide(prefix)
                artifact = realize_candidate(binding.programs[step.candidate_hash].to_json(), freeze)
                frozen = worker.request('freeze_candidate', artifact_hash=artifact['artifact_hash'],
                                        program_hash=artifact['program_hash'])['receipt']
                report = worker.request('evaluate', artifact=artifact,
                                        candidate_freeze_hash=frozen['candidate_freeze_hash'])
                require(report['event'] == 'candidate_evaluated' and
                        report['program_hash'] == step.candidate_hash and
                        report['artifact_hash'] == artifact['artifact_hash'] and
                        report['candidate_freeze_hash'] == frozen['candidate_freeze_hash'] and
                        report['evaluation_index'] == len(prefix.observations) and
                        report['evaluation_hash'] == digest({k: v for k, v in report.items() if k != 'evaluation_hash'}),
                        'evaluation receipt mismatch')
                prefix = record_evaluation(prefix, step, verdict=report['verdict'],
                    evaluation_hash=report['evaluation_hash'], reason_codes=report['reason_codes'],
                    predecessor_state_hash=report['predecessor_state_hash'],
                    challenge_commitment_hash=report['challenge_commitment_hash'])
            terminal = decide(prefix).action.value
            worker.request('seal', terminal_action=terminal)
            transcript, accounting = worker.transcript(), worker.accounting
            worker_pid = worker.process.pid
            require(worker.process.returncode == 0, 'worker failed on close')
        # Evaluator semantics, work inventory AND the producer order are rechecked.
        checked_checkpoint = check_controller(predecessor, transcript)
        require(checked_checkpoint == checkpoint(prefix), 'controller transcript mismatch')
        completion = authority.complete(predecessor, transcript=transcript, accounting=accounting)
    except BaseException:
        # No implicit retry or refund. If recording failure itself fails, retain
        # the pending grant on disk for explicit externally anchored handling.
        if authority.state.status == 'pending':
            authority.fail()
        raise
    return {
        'grant.json': canonical(grant), 'objective.json': canonical(objective.to_json()),
        'objective_freeze.json': canonical(freeze), 'public_challenge.json': canonical(public),
        'sealed_transcript.json': transcript, 'worker-accounting.json': canonical(accounting),
        'controller_checkpoint.json': checked_checkpoint,
        'session.json': canonical({'schema': 'rcp-rclm.phase17o.session.v1',
            'session_index': index, 'grant_hash': grant['grant_hash'],
            'campaign_head_before': before.head, 'reservation_head': reservation_head,
            'campaign_head_after': authority.state.head, 'completion': completion,
            'reserved': grant['envelope']['limits'], 'worker_spent': accounting['spent'],
            'controller_pid': os.getpid(), 'worker_pid': worker_pid,
            'separate_process': worker_pid != os.getpid(), 'worker_exited_cleanly': True,
            'fresh_live_challenge': True, 'automatic_retries': 0,
            'claims': dict(FALSE_CLAIMS), 'unmeasured': list(UNMEASURED)})}


def audit_campaign(predecessor: HistoricalPredecessor, journal: bytes, *, expected_head: str,
                   policy: Policy, expected_context: dict, sessions: dict[str, dict[str, bytes]]) -> dict:
    """Post-seal reconstruction from evidence; no worker launched and no new entropy."""
    from .metered_worker import verify_metered_transcript
    require(expected_context == context_for(predecessor, expected_context['campaign_id']), 'audit parent mismatch')
    state = replay(journal, expected_head=expected_head, policy=policy, expected_context=expected_context)
    require(type(sessions) is dict, 'exact session evidence mapping required')
    event_rows = [load_json_strict(line) for line in journal.splitlines()]
    reservations = {r['body']['grant']['grant_hash']: r for r in event_rows if r['body']['kind'] == 'reserve'}
    completions = {r['body']['grant_hash']: r for r in event_rows if r['body']['kind'] == 'complete'}
    wanted: set[str] = set()
    totals = (0, 0, 0, 0)
    from .resource_ledger import add
    for raw in state.completed:
        retained = load_json_strict(raw)
        grant, completion = retained['grant'], retained['completion']
        h = grant['grant_hash']
        wanted.add(h)
        require(h in sessions, 'completed session evidence missing')
        files = sessions[h]
        exact(files, {'grant.json', 'objective.json', 'objective_freeze.json', 'public_challenge.json',
                      'sealed_transcript.json', 'worker-accounting.json', 'controller_checkpoint.json', 'session.json'})
        require(all(type(v) is bytes for v in files.values()), 'session bytes required')
        require(files['grant.json'] == canonical(grant), 'session grant differs')
        transcript = files['sealed_transcript.json']
        accounting = load_json_strict(files['worker-accounting.json'])
        checked = verify_metered_transcript(predecessor, grant, transcript, accounting)
        require(canonical(completion) == canonical({'kind': 'complete', 'grant_hash': h, **checked}),
                'completion evidence differs from sealed transcript')
        require(check_controller(predecessor, transcript) == files['controller_checkpoint.json'],
                'retained controller checkpoint differs')
        events = load_json_strict(transcript)['events']
        opening = events[0]
        require(files['objective.json'] == canonical(opening['request']['objective']) and
                files['objective_freeze.json'] == canonical(opening['request']['freeze']) and
                files['public_challenge.json'] == canonical(opening['response']['payload']['public_challenge']),
                'retained objective/freeze/public challenge differs')
        report = load_json_strict(files['session.json'])
        exact(report, {'schema', 'session_index', 'grant_hash', 'campaign_head_before', 'reservation_head',
                      'campaign_head_after', 'completion', 'reserved', 'worker_spent', 'controller_pid',
                      'worker_pid', 'separate_process', 'worker_exited_cleanly', 'fresh_live_challenge',
                      'automatic_retries', 'claims', 'unmeasured'})
        require(nat(report['controller_pid']) > 0 and nat(report['worker_pid']) > 0 and
                report['controller_pid'] != report['worker_pid'], 'invalid reported process identities')
        expected_report = {'schema': 'rcp-rclm.phase17o.session.v1', 'session_index': grant['session_index'],
            'grant_hash': h, 'campaign_head_before': grant['previous_campaign_head'],
            'reservation_head': reservations[h]['hash'], 'campaign_head_after': completions[h]['hash'],
            'completion': completion, 'reserved': grant['envelope']['limits'], 'worker_spent': accounting['spent'],
            'controller_pid': report['controller_pid'], 'worker_pid': report['worker_pid'],
            'separate_process': True, 'worker_exited_cleanly': True, 'fresh_live_challenge': True,
            'automatic_retries': 0, 'claims': dict(FALSE_CLAIMS), 'unmeasured': list(UNMEASURED)}
        require(files['session.json'] == canonical(expected_report), 'session report differs')
        # Process IDs and "fresh" flags are recorded execution metadata, not authenticated physical facts.
        totals = add(totals, checked['worker_spent'])
    require(set(sessions) == wanted, 'extra or missing session evidence')
    return {'schema': 'rcp-rclm.phase17o.campaign-audit.v1', 'expected_head': state.head,
            'completed_sessions': len(state.completed), 'reserved': list(state.reserved),
            'reserved_cost': state.charged_cost, 'completed_worker_spent': list(totals),
            'status': state.status, 'pending_grant_retained': state.pending is not None,
            'scoped_campaign_recomputed': True, 'claims': dict(FALSE_CLAIMS)}
