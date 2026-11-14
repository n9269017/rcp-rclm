"""Typed learned-state/evidence integration; no root acceptance or active promotion.

The selected Phase17H proof report is reused only for its exact checked package,
operational packet, contract, and generated sources. Eight NEW Lean audits must
run in formal mode. No old proof, live search, or tool setup is repeated.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
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
from rcp_rclm_runtime_v5.phase17.learned_state_binding import prepare_learned_binding, verify_retained_operational, CLAIMS, GROUPS
from rcp_rclm_runtime_v5.phase17.learned_binding_lean import check_learned_binding, render_binding, NAMES

BASE='3826d94cd3af510e9fbdc1b38a8e83071b8c0aec'
RETAINED_PATH='artifacts/development/phase17h/op-eb78c099106d/gate/execution.json'
RETAINED_HASH='6cfacc08015a8e2ace156c3ddb3de68e380c9e840d2e19f83b01fffd2981fdac'
RETAINED_SOURCE='eb78c099106d1d9e5b6523646a5139a0c5c8dff5'


def unchanged_existing_execution_source():
    """Old result is reused only with no changed existing execution/proof source.

    New files are permitted; any edit/delete/rename of a preexisting Python,
    script or Lean file since the pinned completed H boundary blocks reuse.
    The original historical result is retained, not declared newly executed.
    """
    changes=git(ROOT,'diff','--name-only','--diff-filter=MDRTUXB','-z',BASE,'HEAD','--','python','lean','scripts')
    require(not changes,'existing execution/proof source changed since retained Phase17H')


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--test-fixture',action='store_true',required=True)
    ap.add_argument('--require-lean',action='store_true')
    ap.add_argument('--lean-workspace',type=Path)
    ap.add_argument('--toolchain-root',type=Path)
    args=ap.parse_args(argv)
    require(args.require_lean==(args.lean_workspace is not None),'formal mode requires pinned workspace')
    require(args.require_lean or args.toolchain_root is None,'unused toolchain argument')
    out=args.output.absolute()
    require(not out.exists() and ROOT not in out.parents,'new external output required')
    require(all(not p.is_symlink() and not (hasattr(p,'is_junction') and p.is_junction())
                for p in (out,*out.parents)),'linked output path')
    source=git(ROOT,'rev-parse','HEAD').decode().strip();tree=git(ROOT,'rev-parse','HEAD^{tree}').decode().strip()
    require(not git(ROOT,'status','--porcelain'),'clean committed source required')
    out.mkdir(parents=True)
    report={'schema':'rcp-rclm.phase17i.typed-learned-binding-run.v1','source_commit':source,'source_tree':tree,
        'started_at_utc':datetime.now(timezone.utc).isoformat(),'os':platform.system(),'python_version':platform.python_version(),
        'synthetic_fixture':True,'automatic_retries':0,'local_increment_checks_passed':False,
        'claims':{k:False for k in CLAIMS}}
    try:
        unchanged_existing_execution_source()
        bundle=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
        capture=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
        closure=ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
        fixture=ROOT/'python/rcp_rclm_runtime_v5/tests_phase17d/fixtures/known_candidate_pass.json'
        raw=fixture.read_bytes();require(sha(raw)==FIXTURE_HASH,'synthetic fixture changed')
        retained=ROOT/RETAINED_PATH
        require(retained.is_file() and not retained.is_symlink(),'retained Phase17H evidence absent or linked')
        prior=retained.read_bytes();require(sha(prior)==RETAINED_HASH,'retained Phase17H evidence changed')
        parent=reopen_phase16(capture_archive=capture,closure_archive=closure,phase15_bundle=bundle)
        before=materialize_package(out/'p',parent,bundle)
        after=materialize_package(out/'c',parent,bundle,transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        prepared,operational=prepare_learned_binding(before,after,parent,bundle=bundle,capture=capture,
            transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        reuse=verify_retained_operational(operational,prior,expected_sha256=RETAINED_HASH,expected_source=RETAINED_SOURCE)
        positive=render_binding(prepared,source_root=ROOT);negative=render_binding(prepared,source_root=ROOT,negative=True)
        (out/'packet.json').write_bytes(prepared.packet_bytes)
        (out/'operational_packet.json').write_bytes(operational.packet_bytes)
        (out/'Binding.lean').write_bytes(positive);(out/'ChangedComponent.lean').write_bytes(negative)
        p=prepared.packet
        report.update(packet_sha256=sha(prepared.packet_bytes),operational_packet_sha256=sha(operational.packet_bytes),
            candidate_package_hash=after.package_hash,predecessor_package_hash=before.package_hash,
            learned_component_groups=len(GROUPS),base_files_mapped=sum(len(p['predecessor'][g]) for g in GROUPS),
            root_type=p['root_type'],root_admission=p['root_admission'],named_audits=list(NAMES),
            reused_phase17h=reuse,existing_execution_source_unchanged=True,
            prospective_registry_sizes=[len(p['predecessor']['base']),len(p['candidate']['base'])],
            prospective_frontier_sizes=[len(p['predecessor']['capabilityFrontier']),len(p['candidate']['capabilityFrontier'])],
            legacy_full_recursive_tasks_recertified=[],new_operational_contracts_certified=[],
            plan_queries_recomputed_per_package=operational.packet['candidate']['queries'],
            integer_tool_executions_recomputed_per_package=operational.packet['candidate']['integer_tool_outputs'],
            prior_proofs_rerun=False,training_performed=False,public_recertification_not_hidden_evaluation=True)
        report['typed_binding_gate']={'status':'not_requested','typed_learned_state_binding_checked':False}
        if args.require_lean:
            workspace=args.lean_workspace.resolve(strict=True)
            with exclusive(workspace):
                gate=check_learned_binding(prepared,source_root=ROOT,lean_workspace=workspace,toolchain_root=args.toolchain_root)
            report['typed_binding_gate']=gate
            require(gate['status']=='passed','new typed learned-state gate failed')
        verify_package(before.root,parent,bundle,expected_package_hash=before.package_hash)
        verify_package(after.root,parent,bundle,expected_package_hash=after.package_hash,
            transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        require(fixture.read_bytes()==raw and retained.read_bytes()==prior and
                (out/'packet.json').read_bytes()==prepared.packet_bytes and
                (out/'operational_packet.json').read_bytes()==operational.packet_bytes and
                (out/'Binding.lean').read_bytes()==positive and (out/'ChangedComponent.lean').read_bytes()==negative,
                'input or evidence changed during run')
        unchanged_existing_execution_source()
        require(git(ROOT,'rev-parse','HEAD').decode().strip()==source and not git(ROOT,'status','--porcelain'),'source changed')
        report.update(local_increment_checks_passed=True,source_unchanged=True,
                      proof_mode='real_pinned_lean' if args.require_lean else 'preparation_only')
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as exc:
        report['failure']={'type':type(exc).__name__,'reason':str(exc)}
    report['finished_at_utc']=datetime.now(timezone.utc).isoformat();write(out/'execution.json',report)
    files=[p for p in out.rglob('*') if p.is_file() and p.relative_to(out).parts[0] not in ('p','c')]
    (out/'SHA256SUMS.txt').write_bytes(''.join(sha(p.read_bytes())+'  '+p.relative_to(out).as_posix()+'\n'
                                            for p in sorted(files)).encode('utf-8'))
    print(json.dumps(report,indent=2))
    return 0 if report['local_increment_checks_passed'] else 2

if __name__=='__main__':raise SystemExit(main())
