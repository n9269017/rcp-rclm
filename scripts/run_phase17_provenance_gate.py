"""Check complete selection provenance on a fixed, explicitly synthetic trace.

No live entropy, worker launch, training, temporal attestation, or promotion.
An old evaluator-valid shortcut is required to fail controller conformance.
The new trace reuses that known challenge but preserves all actual controller
choices: eight rejections and a ninth candidate pass. Historical evidence is not
rewritten and prior capability certificates are not reassigned to this new trace.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from pathlib import Path
import platform
import subprocess
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
from run_phase17_successor_gate import git,write
from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
from rcp_rclm_runtime_v5.phase17.materialized import materialize_package,verify_package,snapshot,sha,require
from rcp_rclm_runtime_v5.phase17.challenge_protocol import verify_transcript
from rcp_rclm_runtime_v5.phase17.proposal_provenance import (prepare_provenance,replay_proposals,measured_projection,
    verify_provenance_bytes,CLAIMS)
from rcp_rclm_runtime_v5.phase17.provenance_lean import render_provenance,check_provenance,NAMES,LABELS
BASE='dac5bc9c6ab41e8a18a58b45cc6c8bb3f047288a'
FIXTURE_HASH='16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f'
OLD_FIXTURE_HASH='369c30c469090fa357633aca596cb0c7ad3de31f2ecf16ca78e7699e79c79e6e'


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--test-fixture',action='store_true',required=True)
    ap.add_argument('--require-lean',action='store_true')
    ap.add_argument('--lean-workspace',type=Path)
    ap.add_argument('--toolchain-root',type=Path)
    args=ap.parse_args(argv)
    require(args.require_lean==(args.lean_workspace is not None),'formal mode requires pinned workspace')
    require(args.require_lean or args.toolchain_root is None,'unused toolchain root')
    out=args.output.absolute()
    require(not out.exists() and ROOT not in out.parents,'new external output required')
    require(all(not p.is_symlink() and not (hasattr(p,'is_junction') and p.is_junction()) for p in (out,*out.parents)),'linked output')
    require(not git(ROOT,'status','--porcelain'),'clean committed source required')
    source=git(ROOT,'rev-parse','HEAD').decode().strip();tree=git(ROOT,'rev-parse','HEAD^{tree}').decode().strip()
    out.mkdir(parents=True)
    report={'schema':'rcp-rclm.phase17k.provenance-run.v1','source_commit':source,'source_tree':tree,
        'started_at_utc':datetime.now(timezone.utc).isoformat(),'os':platform.system(),'python_version':platform.python_version(),
        'synthetic_fixture':True,'automatic_retries':0,'local_increment_checks_passed':False,'claims':{k:False for k in CLAIMS}}
    try:
        require(not git(ROOT,'diff','--name-only','--diff-filter=MDRTUXB','-z',BASE,'HEAD','--','python','lean','scripts'),
                'preexisting execution or root source changed')
        bundle=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
        capture=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
        closure=ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
        parent=reopen_phase16(capture_archive=capture,closure_archive=closure,phase15_bundle=bundle)
        raw=(ROOT/'python/rcp_rclm_runtime_v5/tests_phase17k/fixtures/ordered_known_challenge.json').read_bytes()
        require(sha(raw)==FIXTURE_HASH,'ordered synthetic fixture differs')
        before=materialize_package(out/'p',parent,bundle)
        after=materialize_package(out/'c',parent,bundle,transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        prepared=prepare_provenance(before,after,parent,bundle=bundle,source_root=ROOT,transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        old=(ROOT/'python/rcp_rclm_runtime_v5/tests_phase17d/fixtures/known_candidate_pass.json').read_bytes()
        require(sha(old)==OLD_FIXTURE_HASH,'old isolated fixture changed')
        evaluated=verify_transcript(parent,old,expected_transcript_hash=OLD_FIXTURE_HASH)
        require(evaluated.terminal_action=='await_root_verification','old evaluator fixture differs')
        try:replay_proposals(parent,old,expected_transcript_hash=OLD_FIXTURE_HASH,weights=measured_projection(snapshot(before.root),parent))
        except ValueError as exc:
            require(str(exc)=='proposal is not the current controller choice','unrelated shortcut rejection')
            old_rejection={'old_evaluator_fixture_valid':True,'producer_conformance':False,'reason':str(exc),
                           'old_transcript_sha256':OLD_FIXTURE_HASH,'historical_evidence_modified':False}
        else:raise ValueError('old shortcut incorrectly accepted as controller-produced')
        p=prepared.packet;trace=p['trace']
        require(len(trace['steps'])==9 and [r['verdict'] for r in trace['steps']]==['reject']*8+['candidate_passed'],'ordered fixture results differ')
        require(p['candidate']['program_hash']==evaluated.selected_candidate_hash,'fixture switched the passing program')
        report.update(packet_sha256=sha(prepared.packet_bytes),transcript_sha256=FIXTURE_HASH,
            predecessor_package_hash=before.package_hash,candidate_package_hash=after.package_hash,
            generator_id=p['producer']['generator_id'],producer_kind=p['producer']['producer_kind'],
            declared_generator_source_files=len(p['producer']['source_files']),physical_planner_nonzero_parameters=84,
            grammar_size=32,proposal_count=9,rejection_count=8,ranked_prefix_proposals=4,fair_fallback_proposals=5,
            terminal_action=trace['terminal'],old_shortcut=old_rejection,new_named_audits=list(NAMES),
            complete_learned_kernel_constructed=False,historical_execution_attested=False,self_hosted_neural_generator=False,
            prior_capability_proofs_reused_for_new_transcript=False,old_proofs_rerun=False,
            selection_input_policy=trace['selection_input_policy'],full_root_assessment='blocked_missing_semantic_witnesses',
            training_performed=False,live_challenge_generated=False)
        (out/'packet.json').write_bytes(prepared.packet_bytes);(out/'ordered_transcript.json').write_bytes(raw)
        write(out/'old_fixture_rejection.json',old_rejection)
        sources={label:render_provenance(prepared,source_root=ROOT,negative=neg)
                 for label,neg in zip(LABELS,(None,'prefix','parent','program'),strict=True)}
        for label,data in sources.items():(out/(label+'.lean')).write_bytes(data)
        report['source_sha256']={label:sha(data) for label,data in sources.items()}
        if args.require_lean:
            result=check_provenance(prepared,source_root=ROOT,lean_workspace=args.lean_workspace,toolchain_root=args.toolchain_root)
            report['provenance_gate']=result
            require(result['status']=='passed','new provenance Lean gate failed')
            require(result['source_sha256']==report['source_sha256'],'executed sources differ')
        else:report['provenance_gate']={'status':'not_requested','claims':{k:False for k in CLAIMS}}
        for label,data in sources.items():require((out/(label+'.lean')).read_bytes()==data,'saved proof source changed')
        verify_provenance_bytes((out/'packet.json').read_bytes(),prepared,expected_sha256=report['packet_sha256'])
        require((out/'ordered_transcript.json').read_bytes()==raw,'saved transcript changed')
        verify_package(before.root,parent,bundle,expected_package_hash=before.package_hash)
        verify_package(after.root,parent,bundle,expected_package_hash=after.package_hash,transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        require(not git(ROOT,'status','--porcelain') and git(ROOT,'rev-parse','HEAD').decode().strip()==source,'source changed during verification')
        report.update(source_unchanged=True,local_increment_checks_passed=True,
                      proof_mode='real_pinned_lean' if args.require_lean else 'preparation_only')
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as exc:
        report['failure']={'type':type(exc).__name__,'reason':str(exc)}
    report['finished_at_utc']=datetime.now(timezone.utc).isoformat();write(out/'execution.json',report)
    files={p.name:p.read_bytes() for p in out.iterdir() if p.is_file()}
    (out/'SHA256SUMS.txt').write_bytes(''.join(sha(raw)+'  '+n+'\n' for n,raw in sorted(files.items())).encode('utf-8'))
    import json
    print(json.dumps(report,indent=2))
    return 0 if report['local_increment_checks_passed'] else 2

if __name__=='__main__':raise SystemExit(main())
