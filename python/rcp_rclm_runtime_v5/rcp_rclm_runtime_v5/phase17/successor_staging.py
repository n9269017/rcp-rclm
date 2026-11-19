"""Phase17P: consumed, parent-linked, INACTIVE physical candidate handoff.

No caller success report can authorize activation. The only candidate outcome is
blocked_missing_root_witnesses, after fresh physical and joint Python checks.
The immutable root, old proofs and active stores are never written or invoked.
"""
from __future__ import annotations
import os
from pathlib import Path
import tempfile
from rcp_rclm_runtime.canonical.json import load_json_strict
from .campaign_transaction import FALSE_CLAIMS, UNMEASURED, load_predecessor
from .handoff_source import Handoff, checked_handoff
from .joint_evidence import prepare_joint
from .materialized import expected_package, materialize_package, verify_package
from .resource_ledger import canonical, digest, exact, require, sha, _no_links
from .transition_journal import TransitionJournal, binding, replay, transaction_id

BLOCKERS = [
    'complete_compatible_base_RCP_RCLM_obligations',
    'physical_observation_refinement',
    'full_goal_and_information_semantics',
    'complete_resource_measurement_and_enforcement',
    'same_candidate_root_checked_capability_and_recursive_productivity',
    'complete_learned_and_autonomous_accepted_step',
    'active_atomic_promotion_and_rollback',
]
EXCLUDED = [*UNMEASURED, 'candidate_materialization', 'joint_evidence_recomputation']


def archive_paths(root: Path) -> tuple[Path,Path]:
    return (root/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip',
            root/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip')


def binding_for(root: Path, source: bytes, *, expected_source_hash: str, mode: str) -> dict:
    parent=load_predecessor(root)
    handoff=checked_handoff(parent,source,expected_source_hash=expected_source_hash)
    r=handoff.record
    require(r['source_kind']==mode,'fixture/online mode mismatch')
    _,manifest=expected_package(parent,archive_paths(root)[0])
    return binding({'mode':mode,'scope_id':r['scope_id'],
        'predecessor_state_hash':r['predecessor_state_hash'],
        'predecessor_logical_package_hash':r['predecessor_logical_package_hash'],
        'predecessor_physical_hash':manifest['materialized_package_hash'],
        'fixed_verifier_hash':r['fixed_verifier_hash']})


def write_new(path: Path, raw: bytes) -> None:
    _no_links(path)
    require(type(raw) is bytes,'immutable output required')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:
        require(f.write(raw)==len(raw),'short evidence write')
        f.flush();os.fsync(f.fileno())


def read_tree(path: Path) -> dict[str,bytes]:
    _no_links(path);require(path.is_dir(),'evidence directory missing')
    result={};total=0
    for p in sorted(path.rglob('*')):
        _no_links(p)
        if p.is_file():
            require(p.stat().st_nlink==1,'hard-linked evidence forbidden')
            raw=p.read_bytes();total+=len(raw)
            require(total<=32*1024*1024 and len(result)<32,'evidence bounds exceeded')
            result[p.relative_to(path).as_posix()]=raw
    return result


def _construct(root: Path, handoff: Handoff, *, packages: Path, transaction: str,
               expected_binding: dict) -> dict[str,bytes]:
    """Only called AFTER challenge consumption persists. No mutable active path."""
    parent=load_predecessor(root);bundle,capture=archive_paths(root)
    require(not packages.exists(),'new isolated materialization directory required')
    _no_links(packages);packages.mkdir()
    before=materialize_package(packages/'predecessor',parent,bundle)
    require(before.package_hash==expected_binding['predecessor_physical_hash'],'physical parent differs')
    files={'source.json':handoff.source_bytes,'handoff.json':handoff.record_bytes,
           'predecessor-manifest.json':before.manifest_bytes}
    r=handoff.record;candidate=None;joint_hash=None
    if r['terminal_action']=='await_root_verification':
        after=materialize_package(packages/'candidate',parent,bundle,transcript=handoff.transcript,
                                  expected_transcript_hash=r['transcript_sha256'])
        joint=prepare_joint(before,after,parent,bundle=bundle,capture=capture,source_root=root,
                             transcript=handoff.transcript,expected_transcript_hash=r['transcript_sha256'])
        require(joint.packet['bindings']['predecessor_physical_hash']==before.package_hash and
                joint.packet['bindings']['candidate_physical_hash']==after.package_hash and
                joint.packet['bindings']['challenge_commitment_hash']==r['challenge_commitment_hash'],
                'new joint evidence binding differs')
        candidate=after.package_hash;joint_hash=sha(joint.packet_bytes)
        files.update({'candidate-manifest.json':after.manifest_bytes,'joint-evidence.json':joint.packet_bytes})
        # Reopen and measure both physical packages after the integration checks.
        verify_package(after.root,parent,bundle,expected_package_hash=candidate,
                       transcript=handoff.transcript,expected_transcript_hash=r['transcript_sha256'])
    verify_package(before.root,parent,bundle,expected_package_hash=before.package_hash)
    report={'schema':'rcp-rclm.phase17p.staged-transaction.v1','transaction_id':transaction,
        'binding':expected_binding,'source_sha256':handoff.source_hash,'handoff_sha256':sha(handoff.record_bytes),
        'source_kind':r['source_kind'],'campaign_head':r['campaign_head'],'grant_hash':r['grant_hash'],
        'challenge_commitment_hash':r['challenge_commitment_hash'],'transcript_sha256':r['transcript_sha256'],
        'terminal_action':r['terminal_action'],'candidate_evaluations':r['candidate_evaluations'],
        'session_reserved':r['session_reserved'],'worker_spent':r['worker_spent'],
        'predecessor_logical_hash':r['predecessor_logical_package_hash'],
        'predecessor_physical_hash':before.package_hash,'candidate_physical_hash':candidate,
        'joint_packet_sha256':joint_hash,
        'outcome':'blocked_missing_root_witnesses' if candidate is not None else 'no_candidate',
        'physical_candidate_staged':candidate is not None,
        'fresh_joint_python_evidence_checked':candidate is not None,
        'root_acceptance_evaluated':False,'root_blockers':list(BLOCKERS),
        'old_success_reports_reassigned':False,'new_lean_audits':0,
        'active_store_written':False,'challenge_consumption_scope':'one_externally_anchored_parent_journal',
        'campaign_reservations_unchanged':True,'unmeasured':list(EXCLUDED),'claims':dict(FALSE_CLAIMS)}
    files['assessment.json']=canonical(report)
    return files


def _check_binding(b:dict,handoff:Handoff) -> None:
    r=handoff.record
    require(b['mode']==r['source_kind'] and b['scope_id']==r['scope_id'] and
            b['predecessor_state_hash']==r['predecessor_state_hash'] and
            b['predecessor_logical_package_hash']==r['predecessor_logical_package_hash'] and
            b['fixed_verifier_hash']==r['fixed_verifier_hash'],'handoff parent, scope or mode mismatch')


def verify_dossier(root:Path, folder:Path, begin:dict, completion:dict, expected_binding:dict) -> dict:
    """Reconstruct packages in a fresh scratch directory; no original worker/entropy."""
    files=read_tree(folder)
    require({'source.json','handoff.json','assessment.json','predecessor-manifest.json'}<=set(files),
            'incomplete transaction dossier')
    require(sha(files['assessment.json']) == completion['report_sha256'], 'assessment identity differs')
    h=checked_handoff(load_predecessor(root),files['source.json'],expected_source_hash=begin['source_sha256'])
    _check_binding(expected_binding,h)
    require(h.record_bytes==files['handoff.json'] and sha(h.record_bytes)==begin['handoff_sha256'],
            'handoff record differs')
    r=h.record
    require(r['challenge_commitment_hash']==begin['challenge_commitment_hash'] and
            r['transcript_sha256']==begin['transcript_sha256'] and r['terminal_action']==begin['terminal_action'],
            'consumed challenge differs')
    with tempfile.TemporaryDirectory(prefix='r17p-replay-') as tmp:
        wanted=_construct(root,h,packages=Path(tmp)/'packages',transaction=begin['transaction_id'],
                          expected_binding=expected_binding)
    require(files==wanted,'dossier differs from independent physical reconstruction')
    report=load_json_strict(files['assessment.json'])
    require(completion['report_sha256']==sha(files['assessment.json']) and
            completion['outcome']==report['outcome'],'completion report differs')
    return report


def audit_staging(root:Path,evidence:Path,*,expected_head:str,expected_binding:dict) -> dict:
    _no_links(evidence)
    state=replay((evidence/'journal.jsonl').read_bytes(),expected_head=expected_head,expected_binding=expected_binding)
    reports=[];expected_ids=set()
    for row in state.completed:
        entry=load_json_strict(row);tid=entry['begin']['transaction_id'];expected_ids.add(tid)
        reports.append(verify_dossier(root,evidence/'transactions'/tid,entry['begin'],entry['completion'],expected_binding))
    # Pending/failed dossiers are intentionally preserved for diagnostics. They
    # cannot be treated as completed. For a clean open journal there are no extras.
    if state.status in ('open','external_stop'):
        tx=evidence/'transactions'
        actual=set() if not tx.exists() else {p.name for p in tx.iterdir()}
        require(actual==expected_ids,'extra or missing transaction dossier')
    return {'schema':'rcp-rclm.phase17p.staging-audit.v1','head':state.head,'status':state.status,
            'completed':len(reports),'consumed_challenges':list(state.consumed),
            'reports':reports,'pending_retained':state.pending is not None,'claims':dict(FALSE_CLAIMS)}


def stage_handoff(root:Path,journal:TransitionJournal,source:bytes,*,expected_source_hash:str,
                  packages_root:Path) -> dict:
    """Trusted public entry; no caller callback, decision, proof report or candidate path.

    Source, prior dossiers and parent are independently verified before consume.
    Failures after consume retain that challenge and fail closed. No auto-retry.
    """
    require(type(journal) is TransitionJournal,'exact transition journal required')
    parent=load_predecessor(root)
    h=checked_handoff(parent,source,expected_source_hash=expected_source_hash)
    _check_binding(journal.binding,h)
    _, manifest = expected_package(parent, archive_paths(root)[0])
    require(manifest['materialized_package_hash'] == journal.binding['predecessor_physical_hash'],
            'physical parent anchor differs before consumption')
    evidence=journal.path.parent
    canonical_root=root.resolve()
    require(evidence!=canonical_root and canonical_root not in evidence.parents and evidence not in canonical_root.parents,
            'evidence workspace overlaps source checkout')
    require(journal.path.name=='journal.jsonl','fixed transition journal filename required')
    audit_staging(root,evidence,expected_head=journal.state.head,expected_binding=journal.binding)
    require(journal.state.status=='open','pending or halted transition cannot proceed')
    r=h.record
    tid=transaction_id(h.source_hash,journal.binding['predecessor_physical_hash'])
    folder=evidence/'transactions'/tid
    require(not folder.exists(),'transaction output already exists')
    packages_root=Path(packages_root).absolute();_no_links(packages_root)
    require(packages_root.is_dir(),'existing external package-work root required')
    canonical_root = root.resolve()
    require(packages_root != canonical_root and canonical_root not in packages_root.parents and
            packages_root not in canonical_root.parents, 'package workspace overlaps source checkout')
    require(packages_root!=evidence and evidence not in packages_root.parents and packages_root not in evidence.parents,
            'package work and evidence must not overlap')
    packages=packages_root/tid
    require(not packages.exists(),'materialization destination already exists')
    # This is the consumption linearization point; no candidate work precedes it.
    journal.consume(source_sha256=h.source_hash,handoff_sha256=sha(h.record_bytes),
        challenge_commitment_hash=r['challenge_commitment_hash'],transcript_sha256=r['transcript_sha256'],
        terminal_action=r['terminal_action'])
    try:
        # Retain the exact source as soon as consumption succeeds, before
        # materialization. An interrupted dossier is evidence, never acceptance.
        write_new(folder/'source.json',h.source_bytes)
        write_new(folder/'handoff.json',h.record_bytes)
        files=_construct(root,h,packages=packages,transaction=tid,expected_binding=journal.binding)
        for name,raw in files.items():
            if name in ('source.json','handoff.json'):
                require((folder/name).read_bytes()==raw,'frozen handoff evidence changed')
            else:write_new(folder/name,raw)
        # Verify copied evidence bytes before completing. The root relation is
        # still deliberately not evaluated: required concrete witnesses absent.
        require(read_tree(folder)==files,'staging evidence changed while writing')
        report=load_json_strict(files['assessment.json'])
        journal.complete(transaction=tid,outcome=report['outcome'],report_sha256=sha(files['assessment.json']))
        return report
    except BaseException:
        # If the append itself failed, the journal is poisoned and its last bytes
        # remain for explicit investigation. Never erase consumption to recover.
        try:
            if journal.state.status=='pending':journal.abort()
        except BaseException:
            pass
        raise
