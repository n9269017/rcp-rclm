"""One-candidate typed/task/producer composition, not a full transition.

The explicitly synthetic ordered fixture is materialized once, and all three
layers are rebuilt from it. No historical proof report is relabeled. Real mode
rechecks 37 existing audits/propositions and six new composition audits in one
certificate, plus five separate negative controls. Missing concrete base/goal/
resource/information/autonomous witnesses never become a promotion decision.
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
from rcp_rclm_runtime_v5.phase17.materialized import materialize_package,verify_package,sha,require
from rcp_rclm_runtime_v5.phase17.joint_evidence import prepare_joint,verify_joint_bytes,CLAIMS,KINDS,REMAINING
from rcp_rclm_runtime_v5.phase17.joint_lean import render_joint,check_joint,NEW_NAMES,RECHECKED_NAMES,LABELS
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
BASE='a87631af18f9b48d1040e6c2a01b511a7675022d'
FIXTURE_HASH='16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f'
CANDIDATE_HASH='b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e'


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
    report={'schema':'rcp-rclm.phase17l.joint-run.v1','source_commit':source,'source_tree':tree,
        'started_at_utc':datetime.now(timezone.utc).isoformat(),'os':platform.system(),'python_version':platform.python_version(),
        'synthetic_fixture':True,'automatic_retries':0,'local_increment_checks_passed':False,
        'preparation_checks_passed':False,'claims':{k:False for k in CLAIMS}}
    try:
        require(not git(ROOT,'diff','--name-only','--diff-filter=MDRTUXB','-z',BASE,'HEAD','--','python','lean','scripts'),
                'preexisting execution/root source changed')
        bundle=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
        capture=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
        closure=ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
        parent=reopen_phase16(capture_archive=capture,closure_archive=closure,phase15_bundle=bundle)
        raw=(ROOT/'python/rcp_rclm_runtime_v5/tests_phase17k/fixtures/ordered_known_challenge.json').read_bytes()
        require(sha(raw)==FIXTURE_HASH,'synthetic ordered fixture differs')
        before=materialize_package(out/'p',parent,bundle)
        after=materialize_package(out/'c',parent,bundle,transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        require(after.package_hash==CANDIDATE_HASH,'ordered candidate identity differs')
        prepared=prepare_joint(before,after,parent,bundle=bundle,capture=capture,source_root=ROOT,
                               transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        p=prepared.packet;j=p['task_meanings'];k=p['producer_provenance']
        require(len(j['before']['declared_ids'])==21 and len(j['after']['declared_ids'])==22 and
                len(k['trace']['steps'])==9,'selected fixture coverage differs')
        (out/'packet.json').write_bytes(prepared.packet_bytes);(out/'ordered_transcript.json').write_bytes(raw)
        for name in KINDS:(out/(name+'.json')).write_bytes(canonical(p[name]))
        sources={label:render_joint(prepared,source_root=ROOT,negative=None if label=='Joint' else label) for label in LABELS}
        for label,data in sources.items():(out/(label+'.lean')).write_bytes(data)
        report.update(packet_sha256=sha(prepared.packet_bytes),component_sha256=p['component_sha256'],
            transcript_sha256=FIXTURE_HASH,bindings=p['bindings'],predecessor_package_hash=before.package_hash,
            candidate_package_hash=after.package_hash,new_named_audits=list(NEW_NAMES),
            rechecked_named_audits=list(RECHECKED_NAMES),rechecked_subcertificate_audits=24,
            inherited_theorem_propositions_rechecked=13,selected_before_size=21,selected_after_size=22,
            proposal_count=9,rejection_count=8,component_groups=12,inherited_component_files=164,
            source_sha256={label:sha(data) for label,data in sources.items()},
            remaining_witness_classes=list(REMAINING),full_root_assessment='blocked_missing_semantic_witnesses',
            complete_learned_kernel_constructed=False,full_learned_step_instantiated=False,
            conditional_learned_step_assembler=True,physical_observation_refinement_formally_verified=False,
            historical_capability_reports_reassigned=False,phase17h_plan_proofs_rerun=False,
            self_hosted_neural_generator=False,historical_execution_attested=False,
            live_challenge_generated=False,training_performed=False,new_recursive_tasks_closed=[])
        if args.require_lean:
            result=check_joint(prepared,source_root=ROOT,lean_workspace=args.lean_workspace,toolchain_root=args.toolchain_root)
            report['joint_gate']=result
            require(result['status']=='passed','joint Lean gate did not pass')
            require(result['source_sha256']==report['source_sha256'],'executed sources differ')
        else:report['joint_gate']={'status':'not_requested','claims':{k:False for k in CLAIMS}}
        for label,data in sources.items():require((out/(label+'.lean')).read_bytes()==data,'saved proof source changed')
        verify_joint_bytes((out/'packet.json').read_bytes(),prepared,expected_sha256=report['packet_sha256'])
        require((out/'ordered_transcript.json').read_bytes()==raw,'saved transcript changed')
        for name in KINDS:require((out/(name+'.json')).read_bytes()==canonical(p[name]),'saved subpacket changed')
        verify_package(before.root,parent,bundle,expected_package_hash=before.package_hash)
        verify_package(after.root,parent,bundle,expected_package_hash=after.package_hash,transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        require(not git(ROOT,'status','--porcelain') and git(ROOT,'rev-parse','HEAD').decode().strip()==source,'source changed')
        report.update(source_unchanged=True,preparation_checks_passed=True,
            local_increment_checks_passed=args.require_lean,proof_mode='real_pinned_lean' if args.require_lean else 'preparation_only')
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as exc:
        report['failure']={'type':type(exc).__name__,'reason':str(exc)}
    report['finished_at_utc']=datetime.now(timezone.utc).isoformat();write(out/'execution.json',report)
    files={p.name:p.read_bytes() for p in out.iterdir() if p.is_file()}
    (out/'SHA256SUMS.txt').write_bytes(''.join(sha(raw)+'  '+n+'\n' for n,raw in sorted(files.items())).encode())
    import json
    print(json.dumps(report,indent=2))
    return 0 if report['preparation_checks_passed'] and (not args.require_lean or report['local_increment_checks_passed']) else 2

if __name__=='__main__':raise SystemExit(main())
