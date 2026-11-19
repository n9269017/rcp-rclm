"""Check selected task meanings and the actual learned-root frontier field adapter.

The positive candidate is the explicit historical synthetic fixture, not a live
improvement. This runner recomputes both packages and rechecks 13 inherited proof
propositions as proof arguments in the NEW combined certificate. It does not
rerun the 172 Phase17H proofs, authorize promotion, or complete root acceptance.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
import platform
import subprocess
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
from run_phase17_successor_gate import exclusive, git, write, FIXTURE_HASH
from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
from rcp_rclm_runtime_v5.phase17.materialized import require, sha, materialize_package, verify_package
from rcp_rclm_runtime_v5.phase17.frontier_meanings import prepare_meanings, verify_meaning_bytes, CLAIMS, HISTORICAL_CATALOG_SHA256
from rcp_rclm_runtime_v5.phase17.frontier_meaning_lean import render_meanings, check_meanings, NEW_NAMES, INHERITED_NAMES
BASE='97bd7b334be7b91aa87f9965180e5522dce14a3b'


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
    require(all(not p.is_symlink() and not (hasattr(p,'is_junction') and p.is_junction())
                for p in (out,*out.parents)),'linked output')
    require(not git(ROOT,'status','--porcelain'),'clean committed source required')
    source=git(ROOT,'rev-parse','HEAD').decode().strip();tree=git(ROOT,'rev-parse','HEAD^{tree}').decode().strip()
    out.mkdir(parents=True)
    report={'schema':'rcp-rclm.phase17j.task-meaning-run.v1','source_commit':source,'source_tree':tree,
        'started_at_utc':datetime.now(timezone.utc).isoformat(),'os':platform.system(),'python_version':platform.python_version(),
        'synthetic_fixture':True,'automatic_retries':0,'local_increment_checks_passed':False,
        'claims':{k:False for k in CLAIMS}}
    try:
        # Existing execution and root sources are immutable in this increment.
        require(not git(ROOT,'diff','--name-only','--diff-filter=MDRTUXB','-z',BASE,'HEAD','--','python','lean','scripts'),
                'existing execution or root source changed')
        bundle=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
        capture=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
        closure=ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
        fixture=ROOT/'python/rcp_rclm_runtime_v5/tests_phase17d/fixtures/known_candidate_pass.json'
        require(fixture.is_file() and not fixture.is_symlink(),'regular fixture required')
        raw=fixture.read_bytes();require(sha(raw)==FIXTURE_HASH,'synthetic fixture differs')
        parent=reopen_phase16(capture_archive=capture,closure_archive=closure,phase15_bundle=bundle)
        before=materialize_package(out/'p',parent,bundle)
        after=materialize_package(out/'c',parent,bundle,transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        prepared=prepare_meanings(before,after,parent,bundle=bundle,capture=capture,
                                  transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        (out/'packet.json').write_bytes(prepared.packet_bytes)
        verify_meaning_bytes((out/'packet.json').read_bytes(),prepared,expected_sha256=sha(prepared.packet_bytes))
        sources={label:render_meanings(prepared,source_root=ROOT,negative=negative)
                 for label,negative in [('TaskMeaning',None),('WrongTarget','target'),('MissingProofObservation','observation')]}
        for label,data in sources.items():(out/(label+'.lean')).write_bytes(data)
        packet=prepared.packet
        report.update(packet_sha256=sha(prepared.packet_bytes),historical_catalog_sha256=HISTORICAL_CATALOG_SHA256,
            predecessor_package_hash=before.package_hash,candidate_package_hash=after.package_hash,
            historical_proof_tasks=13,historical_single_input_vector_tasks=8,new_eight_probe_tasks=1,
            selected_catalog_size=22,selected_before_size=21,selected_after_size=22,
            predecessor_new_task_passed=packet['checks']['predecessor_new_task_passed'],
            candidate_new_task_passed=packet['checks']['candidate_new_task_passed'],
            new_named_audits=list(NEW_NAMES),inherited_theorem_audits=list(INHERITED_NAMES),
            legacy_full_recursive_tasks_recertified=[],new_operational_contracts_certified=[],
            phase17h_proofs_rerun=False,training_performed=False,
            root_fields=['frontier','solves','frontierSound'],complete_learned_kernel_constructed=False,
            root_observation_projection_formally_verified=False,universal_vector_semantics_claimed=False,
            full_root_assessment='blocked_missing_semantic_witnesses',
            source_sha256={name:sha(data) for name,data in sources.items()})
        report['task_meaning_gate']={'status':'not_requested','selected_task_meanings_checked':False}
        if args.require_lean:
            workspace=args.lean_workspace.resolve(strict=True)
            with exclusive(workspace):
                report['task_meaning_gate']=check_meanings(prepared,source_root=ROOT,
                    lean_workspace=workspace,toolchain_root=args.toolchain_root)
            require(report['task_meaning_gate']['status']=='passed','task-meaning gate did not pass')
            require(report['task_meaning_gate']['source_sha256']==report['source_sha256'],'executed proof sources differ')
        for label,data in sources.items():require((out/(label+'.lean')).read_bytes()==data,'saved proof source changed')
        verify_meaning_bytes((out/'packet.json').read_bytes(),prepared,expected_sha256=report['packet_sha256'])
        verify_package(before.root,parent,bundle,expected_package_hash=before.package_hash)
        verify_package(after.root,parent,bundle,expected_package_hash=after.package_hash,transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        require(not git(ROOT,'status','--porcelain') and git(ROOT,'rev-parse','HEAD').decode().strip()==source,
                'source changed during evaluation')
        report.update(source_unchanged=True,local_increment_checks_passed=True,
                      proof_mode='real_pinned_lean' if args.require_lean else 'preparation_only')
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as exc:
        report['failure']={'type':type(exc).__name__,'reason':str(exc)}
    report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    write(out/'execution.json',report)
    files={p.name:p.read_bytes() for p in out.iterdir() if p.is_file()}
    (out/'SHA256SUMS.txt').write_bytes(''.join(sha(raw)+'  '+name+'\n' for name,raw in sorted(files.items())).encode('utf-8'))
    import json
    print(json.dumps(report,indent=2))
    return 0 if report['local_increment_checks_passed'] else 2

if __name__=='__main__':raise SystemExit(main())
