"""Fixed two-session development validation, not a target-length runtime policy.

The production transaction takes no target count. This finite harness creates two
new challenges once, retains either outcome, reopens one budget, then denies more
work. It never searches for a passing seed or authorizes a successor.
"""
from __future__ import annotations
from pathlib import Path
import secrets

from rcp_rclm_runtime.canonical.json import load_json_strict
from .campaign_budget import CampaignAuthority, replay
from .campaign_transaction import (
    FALSE_CLAIMS, UNMEASURED, audit_campaign, context_for, load_predecessor, run_campaign_session,
)
from .resource_ledger import Policy, ResourceExhausted, canonical, cost, full_grammar_policy, require

PROFILE = 'phase17o.fixed-parent-two-session-development.v1'
CREDITS = 2
SESSIONS = 2  # Validation coverage, never an input to the runtime controller.


def execute_profile(root: Path, output: Path) -> dict:
    require(output.is_dir() and not any(output.iterdir()), 'new empty evidence directory required')
    predecessor = load_predecessor(root)
    ctx = context_for(predecessor, secrets.token_hex(32))
    per_session = full_grammar_policy(len(predecessor.accepted_programs), candidate_limit=CREDITS)
    policy = Policy(tuple(x * SESSIONS for x in per_session.limits), per_session.cost_limit * SESSIONS)
    (output/'context.json').write_bytes(canonical(ctx))
    (output/'policy.json').write_bytes(canonical(policy.to_json()))
    journal = output/'campaign.jsonl'
    retained = {}
    anchors = []
    head = None
    for index in range(SESSIONS):
        with CampaignAuthority(journal, policy=policy, expected_context=ctx, expected_head=head) as authority:
            before = authority.state
            records = run_campaign_session(authority, predecessor, candidate_credits=CREDITS,
                                            prior_sessions=retained)
            session = load_json_strict(records['session.json'])
            require(session['session_index'] == index and before.session_count == index, 'session ordinal changed')
            folder = output/'sessions'/str(index)
            folder.mkdir(parents=True)
            for name, raw in records.items():
                (folder/name).write_bytes(raw)
            retained[session['grant_hash']] = records
            head = authority.state.head
            anchors.append(head)
            (output/'anchors.json').write_bytes(canonical(anchors))
        # Both lock and file descriptors are closed. A fresh authority must load
        # the external exact head and independently validate the retained history.
    with CampaignAuthority(journal, policy=policy, expected_context=ctx, expected_head=head) as authority:
        before = authority.state
        try:
            run_campaign_session(authority, predecessor, candidate_credits=CREDITS, prior_sessions=retained)
        except ResourceExhausted:
            pass
        else:
            raise ValueError('third worker session was not denied')
        require(authority.state.status == 'resource_exhausted' and authority.state.session_count == SESSIONS and
                authority.state.reserved == before.reserved, 'denial changed prior reservations')
        head = authority.state.head
    (output/'expected-head.txt').write_bytes(head.encode('ascii') + b'\n')
    checked = audit_campaign(predecessor, journal.read_bytes(), expected_head=head,
                              policy=policy, expected_context=ctx, sessions=retained)
    (output/'audit.json').write_bytes(canonical(checked))

    # No worker is launched in these separate admission/recovery controls.
    controls = {}
    for name in ('zero-budget', 'failed-grant', 'abandoned-grant'):
        path = output/(name+'.jsonl')
        control_policy = Policy((0,0,0,0),0) if name == 'zero-budget' else per_session
        with CampaignAuthority(path, policy=control_policy, expected_context=ctx) as authority:
            try:
                authority.reserve(objective_freeze_hash='8'*64, candidate_credits=CREDITS)
            except ResourceExhausted:
                require(name == 'zero-budget', 'unexpected control denial')
            if name == 'failed-grant':
                authority.fail()
            control_head = authority.state.head
        if name == 'abandoned-grant':
            with CampaignAuthority(path, policy=control_policy, expected_context=ctx,
                                   expected_head=control_head) as authority:
                require(authority.state.status == 'pending', 'pending reservation disappeared')
                authority.fail(interrupted=True)
                control_head = authority.state.head
        state = replay(path.read_bytes(), expected_head=control_head, policy=control_policy, expected_context=ctx)
        controls[name] = {'policy': control_policy.to_json(), 'head': control_head,
            'status': state.status, 'reserved': list(state.reserved), 'reserved_cost': state.charged_cost,
            'worker_launched': False, 'simulated_failure_or_abandonment': name != 'zero-budget'}
    (output/'controls.json').write_bytes(canonical(controls))
    return verify_profile(root, output)


def verify_profile(root: Path, output: Path) -> dict:
    """No worker, entropy draw, training, or proof process is launched here."""
    predecessor = load_predecessor(root)
    ctx = load_json_strict((output/'context.json').read_bytes())
    require(ctx == context_for(predecessor, ctx['campaign_id']), 'profile parent differs')
    policy = Policy.from_json(load_json_strict((output/'policy.json').read_bytes()))
    one = full_grammar_policy(len(predecessor.accepted_programs), candidate_limit=CREDITS)
    require(policy == Policy(tuple(x * SESSIONS for x in one.limits), one.cost_limit * SESSIONS), 'profile budget differs')
    head_raw = (output/'expected-head.txt').read_bytes()
    require(len(head_raw) == 65 and head_raw.endswith(b'\n'), 'external head file malformed')
    head = head_raw[:-1].decode('ascii')
    expected_files = {'context.json','policy.json','campaign.jsonl','anchors.json','expected-head.txt',
                      'audit.json','controls.json','zero-budget.jsonl','failed-grant.jsonl','abandoned-grant.jsonl'}
    retained, outcomes, accounting, pids, commitments, completion_heads = {}, [], [], [], [], []
    for index in range(SESSIONS):
        folder=output/'sessions'/str(index)
        names={'grant.json','objective.json','objective_freeze.json','public_challenge.json','sealed_transcript.json',
               'worker-accounting.json','controller_checkpoint.json','session.json'}
        records={name:(folder/name).read_bytes() for name in names}
        expected_files.update('sessions/'+str(index)+'/'+name for name in names)
        report=load_json_strict(records['session.json'])
        require(type(report['session_index']) is int and report['session_index']==index,'wrong recorded session ordinal')
        require(report['grant_hash'] not in retained,'duplicate session grant')
        retained[report['grant_hash']]=records
        outcomes.append(report['completion']['terminal_action'])
        accounting.append(report['worker_spent'])
        pids.append(report['worker_pid'])
        commitments.append(report['completion']['challenge_commitment_hash'])
        completion_heads.append(report['campaign_head_after'])
    require(len(set(commitments))==SESSIONS,'challenge commitment reused')
    require(load_json_strict((output/'anchors.json').read_bytes())==completion_heads,'retained restart anchors differ')
    checked=audit_campaign(predecessor,(output/'campaign.jsonl').read_bytes(),expected_head=head,
                            policy=policy,expected_context=ctx,sessions=retained)
    require(canonical(checked)==(output/'audit.json').read_bytes(),'audit report differs')
    require(checked['completed_sessions']==SESSIONS and checked['status']=='resource_exhausted' and
            checked['reserved']==list(policy.limits) and not checked['pending_grant_retained'], 'profile not complete')
    controls=load_json_strict((output/'controls.json').read_bytes())
    require(set(controls)=={'zero-budget','failed-grant','abandoned-grant'},'control inventory differs')
    for name,record in controls.items():
        pol=Policy((0,0,0,0),0) if name=='zero-budget' else one
        state=replay((output/(name+'.jsonl')).read_bytes(),expected_head=record['head'],
                      policy=pol,expected_context=ctx)
        wanted={'policy':pol.to_json(),'head':state.head,'status':'resource_exhausted' if name=='zero-budget' else 'safety_halt',
                'reserved':[0,0,0,0] if name=='zero-budget' else list(one.limits),
                'reserved_cost':0 if name=='zero-budget' else one.cost_limit,
                'worker_launched':False,'simulated_failure_or_abandonment':name!='zero-budget'}
        require(canonical(record)==canonical(wanted) and state.status==wanted['status'] and
                list(state.reserved)==wanted['reserved'] and state.pending is None,'control outcome differs')
    # .lock files are coordination artifacts, never accepted evidence.
    for p in output.rglob('*'):
        require(not p.is_symlink() and not (hasattr(p,'is_junction') and p.is_junction()),'linked evidence')
    actual={p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file() and not p.name.endswith('.lock')}
    require(actual==expected_files,'extra or missing profile evidence')
    return {'schema':'rcp-rclm.phase17o.online-campaign-profile.v1','profile':PROFILE,
        'fixed_parent':True,'completed_worker_sessions':SESSIONS,'candidate_credits_per_session':CREDITS,
        'automatic_retries':0,'winner_filtering':False,'fresh_live_challenges':SESSIONS,
        'commitments':commitments,'worker_pids':pids,'terminal_actions':outcomes,
        'full_envelope_reservations':list(policy.limits),'reserved_cost':policy.cost_limit,
        'completed_worker_spent':checked['completed_worker_spent'],
        'completed_worker_cost':cost(checked['completed_worker_spent']),
        'worker_spent_by_session':accounting,'campaign_status':checked['status'],
        'campaign_head':head,'all_completed_sessions_recomputed':True,
        'third_worker_launch_denied':True,'authority_reopened_between_sessions':True,
        'scoped_online_budget_authority_integrated':True,'unmeasured':list(UNMEASURED),
        'claims':dict(FALSE_CLAIMS),'controls':controls,
        'execution_metadata_is_attestation':False,'new_lean_audits':0,'old_proofs_rerun':False}
