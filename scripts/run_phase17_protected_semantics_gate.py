"""Fresh protected sparse probability/goal evidence; never full root admission."""
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
from rcp_rclm_runtime_v5.phase17.protected_semantics import prepare_protected_semantics,verify_protected_bytes,CLAIMS,CONTRACT_SHA256
from rcp_rclm_runtime_v5.phase17.protected_semantics_lean import render_protected,check_protected,NAMES,LABELS
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
BASE='a60eee75b3c4b9797fe362ffed7773d2eb6bdc85'
FIXTURE_HASH='16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f'
CANDIDATE_HASH='b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e'
JOINT_PACKET='035c570a3e4b7f1ed2fd43085d9cd6357b2596a169eebcd621c0ff5d0fe274ac'


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
    report={'schema':'rcp-rclm.phase17m.protected-semantics-run.v1','source_commit':source,'source_tree':tree,
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
        prepared=prepare_protected_semantics(before,after,parent,bundle=bundle,capture=capture,source_root=ROOT,
                                             transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        p=prepared.packet
        require(p['joint_packet_sha256']==JOINT_PACKET,'same-candidate joint evidence changed')
        (out/'packet.json').write_bytes(prepared.packet_bytes)
        (out/'joint_packet.json').write_bytes(canonical(p['joint_packet']))
        (out/'ordered_transcript.json').write_bytes(raw)
        (out/'task_contract.json').write_bytes(canonical(p['task_contract']))
        sources={label:render_protected(prepared,source_root=ROOT,negative=None if label=='Protected' else label) for label in LABELS}
        for label,data in sources.items():(out/(label+'.lean')).write_bytes(data)
        report.update(packet_sha256=sha(prepared.packet_bytes),joint_packet_sha256=p['joint_packet_sha256'],
            task_contract_sha256=CONTRACT_SHA256,transcript_sha256=FIXTURE_HASH,bindings=p['bindings'],
            predecessor_package_hash=before.package_hash,candidate_package_hash=after.package_hash,
            new_named_audits=list(NAMES),source_sha256={label:sha(data) for label,data in sources.items()},
            protected_task_count=11,teacher_forced_position_count=len(p['information_positions']),
            conditional_rows_per_package=260,production_row_comparisons=520,
            unique_conditional_rows=len(p['before']['score_dictionary']),selected_goal_drift=p['selected_goal_drift'],
            before_information=p['before_information'],after_information=p['after_information'],
            prior_joint_proofs_rerun=False,historical_success_reports_reassigned=False,
            full_root_assessment='blocked_missing_semantic_witnesses',complete_learned_kernel_constructed=False,
            full_learned_step_instantiated=False,full_goal_interpretation_supplied=False,
            full_information_interpretation_supplied=False,physical_projection_formally_verified=False,
            resource_fields_unchanged=True,live_challenge_generated=False,training_performed=False,new_recursive_tasks_closed=[])
        if args.require_lean:
            result=check_protected(prepared,source_root=ROOT,lean_workspace=args.lean_workspace,toolchain_root=args.toolchain_root)
            report['protected_semantics_gate']=result
            require(result['status']=='passed','protected semantic Lean gate did not pass')
            require(result['source_sha256']==report['source_sha256'],'executed sources differ')
        else:report['protected_semantics_gate']={'status':'not_requested','claims':{k:False for k in CLAIMS}}
        for label,data in sources.items():require((out/(label+'.lean')).read_bytes()==data,'saved proof source changed')
        verify_protected_bytes((out/'packet.json').read_bytes(),prepared,expected_sha256=report['packet_sha256'])
        require((out/'joint_packet.json').read_bytes()==canonical(p['joint_packet']) and
                (out/'task_contract.json').read_bytes()==canonical(p['task_contract']) and
                (out/'ordered_transcript.json').read_bytes()==raw,'saved input evidence changed')
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
