"""One live full-grammar session plus a SEPARATE known fixture staging control.

No entropy retries. A live exhaustion is a valid no-candidate result. The fixture
covers inactive realization deterministically and is never labeled a live win.
No accepted root transition or active pointer operation exists in either path.
"""
from __future__ import annotations
from pathlib import Path
import secrets
import tempfile
from rcp_rclm_runtime.canonical.json import load_json_strict
from .campaign_budget import CampaignAuthority
from .campaign_transaction import (FALSE_CLAIMS, context_for, load_predecessor, run_campaign_session)
from .handoff_source import campaign_capsule, fixture_capsule, checked_handoff
from .resource_ledger import canonical, full_grammar_policy, require, sha, _no_links
from .successor_staging import (TransitionJournal, binding_for, stage_handoff, audit_staging,
                                EXCLUDED, read_tree, write_new)
from .transition_journal import replay

PROFILE = 'phase17p.fixed-parent-handoff-no-activation.v1'
CREDITS = 32


def execute_profile(root:Path, output:Path, packages:Path) -> dict:
    require(output.is_dir() and not any(output.iterdir()), 'new empty evidence output required')
    require(packages.is_dir() and not any(packages.iterdir()), 'new empty package-work output required')
    parent=load_predecessor(root)
    live=output/'online';live.mkdir()
    context=context_for(parent,secrets.token_hex(32))
    policy=full_grammar_policy(len(parent.accepted_programs),candidate_limit=CREDITS)
    with CampaignAuthority(live/'campaign.jsonl',policy=policy,expected_context=context) as authority:
        records=run_campaign_session(authority,parent,candidate_credits=CREDITS)
        meta=load_json_strict(records['session.json']);grant=meta['grant_hash']
        source=campaign_capsule(journal=authority.journal_bytes(),expected_head=authority.state.head,
             policy=policy,expected_context=context,sessions={grant:records},selected_grant_hash=grant)
        live_head=authority.state.head
    # The entire source snapshot contains all O evidence, not merely its pass receipt.
    write_new(live/'source.json',source)
    write_new(live/'campaign-anchor.txt',live_head.encode()+b'\n')
    write_new(live/'source-anchor.txt',sha(source).encode()+b'\n')
    controls={}
    for name,raw,mode in (('online',source,'online_campaign'),
                          ('fixture',fixture_capsule(root),'retained_synthetic_fixture')):
        scope=output/name
        if name=='fixture':
            scope.mkdir();write_new(scope/'source.json',raw);write_new(scope/'source-anchor.txt',sha(raw).encode()+b'\n')
        evidence=scope/'staging';evidence.mkdir()
        b=binding_for(root,raw,expected_source_hash=sha(raw),mode=mode)
        write_new(evidence/'binding.json',canonical(b))
        with TransitionJournal(evidence/'journal.jsonl',expected_binding=b) as journal:
            report=stage_handoff(root,journal,raw,expected_source_hash=sha(raw),packages_root=packages)
            head=journal.state.head
        # Reopen through external anchor. Duplicate handoff must not add an event.
        with TransitionJournal(evidence/'journal.jsonl',expected_binding=b,expected_head=head) as journal:
            before=journal.journal_bytes()
            try:
                stage_handoff(root,journal,raw,expected_source_hash=sha(raw),packages_root=packages)
            except ValueError:
                pass
            else: raise ValueError('duplicate challenge handoff accepted')
            require(journal.journal_bytes()==before,'duplicate rejection altered journal')
        write_new(evidence/'expected-head.txt',head.encode()+b'\n')
        controls[name]={'duplicate_rejected':True,'journal_unchanged_after_duplicate':True,
                        'outcome':report['outcome'],'source_kind':mode}
    write_new(output/'controls.json',canonical(controls))
    return verify_profile(root,output)


def _head(path:Path) -> str:
    raw=path.read_bytes();require(len(raw)==65 and raw.endswith(b'\n'),'anchor encoding differs')
    return raw[:-1].decode('ascii')


def verify_profile(root:Path,output:Path) -> dict:
    parent=load_predecessor(root);reports={};expected={'controls.json'}
    for name,mode in (('online','online_campaign'),('fixture','retained_synthetic_fixture')):
        scope=output/name
        raw=(scope/'source.json').read_bytes();source_hash=_head(scope/'source-anchor.txt')
        handoff=checked_handoff(parent,raw,expected_source_hash=source_hash)
        require(handoff.record['source_kind']==mode,'live and fixture evidence mixed')
        evidence=scope/'staging'
        b=binding_for(root,raw,expected_source_hash=source_hash,mode=mode)
        require((evidence/'binding.json').read_bytes()==canonical(b),'physical parent binding differs')
        head=_head(evidence/'expected-head.txt')
        audit=audit_staging(root,evidence,expected_head=head,expected_binding=b)
        require(audit['status']=='open' and audit['completed']==1 and not audit['pending_retained'],
                'handoff not completed at required boundary')
        require(audit['consumed_challenges']==[handoff.record['challenge_commitment_hash']],
                'consumption inventory differs')
        report=audit['reports'][0]
        require(report['source_sha256']==source_hash,'source binding differs')
        reports[name]=report
        expected.update({name+'/source.json',name+'/source-anchor.txt',name+'/staging/binding.json',
            name+'/staging/expected-head.txt',name+'/staging/journal.jsonl'})
        tid=report['transaction_id']
        names={'source.json','handoff.json','assessment.json','predecessor-manifest.json'}
        if report['physical_candidate_staged']: names|={'candidate-manifest.json','joint-evidence.json'}
        expected.update(name+'/staging/transactions/'+tid+'/'+n for n in names)
        if name=='online':
            source_record=load_json_strict(raw)
            require(_head(scope/'campaign-anchor.txt')==source_record['campaign_head'] and
                    (scope/'campaign.jsonl').read_bytes().hex()==source_record['journal_hex'],
                    'campaign source changed after handoff')
            expected.update({'online/campaign-anchor.txt','online/campaign.jsonl'})
            ctx=source_record['context'];pol=source_record['policy']
            require(pol==full_grammar_policy(len(parent.accepted_programs),candidate_limit=CREDITS).to_json(),
                    'online grammar budget differs')
    require(reports['fixture']['outcome']=='blocked_missing_root_witnesses' and
            reports['fixture']['candidate_physical_hash']=='b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e',
            'named fixture positive stage missing')
    require(reports['online']['terminal_action'] in ('await_root_verification','search_exhausted'),
            'full grammar online outcome differs')
    controls=load_json_strict((output/'controls.json').read_bytes())
    wanted={name:{'duplicate_rejected':True,'journal_unchanged_after_duplicate':True,
                   'outcome':reports[name]['outcome'],'source_kind':reports[name]['source_kind']} for name in reports}
    require(canonical(controls)==canonical(wanted),'control claims differ')
    # Reconstruct the duplicate failure from consumed identities, not just flags.
    for name in reports:
        r=reports[name];scope=output/name/'staging'
        b=load_json_strict((scope/'binding.json').read_bytes());head=_head(scope/'expected-head.txt')
        state=replay((scope/'journal.jsonl').read_bytes(),expected_head=head,expected_binding=b)
        require(state.source_hashes==(r['source_sha256'],) and len(state.consumed)==1,'duplicate control state differs')
    actual=set()
    for p in output.rglob('*'):
        _no_links(p)
        if p.is_file() and not p.name.endswith('.lock'): actual.add(p.relative_to(output).as_posix())
    require(actual==expected,'extra or missing profile evidence')
    return {'schema':'rcp-rclm.phase17p.handoff-profile.v1','profile':PROFILE,
            'fresh_worker_sessions':1,'fresh_live_challenges':1,'candidate_credits':CREDITS,
            'online_terminal':reports['online']['terminal_action'],'online_outcome':reports['online']['outcome'],
            'online_candidate_staged':reports['online']['physical_candidate_staged'],
            'fixture_candidate_staged':True,'fixture_is_live_result':False,
            'both_sources_recomputed':True,'challenge_consumption_recomputed':True,
            'root_verification_pending':True,'parent_unchanged':True,'new_lean_audits':0,
            'automatic_retries':0,'winner_filtering':False,'old_proofs_rerun':False,
            'online':reports['online'],'fixture':reports['fixture'],'controls':controls,
            'claims':dict(FALSE_CLAIMS),'unmeasured':list(EXCLUDED)}
