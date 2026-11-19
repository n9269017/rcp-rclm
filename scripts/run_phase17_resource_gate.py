"""Phase17N finite work-envelope evidence and pinned resource adapter checking.

Fresh metered DSL re-execution, not a new hidden-task campaign, old proof rerun,
complete physical resource profile, or full root-accepted successor.
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
from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
from rcp_rclm_runtime_v5.phase17.resource_ledger import Ledger, Policy, ResourceExhausted, replay, sha, require
from rcp_rclm_runtime_v5.phase17.metered_evaluation import run_selected_profile, selected_binding, FALSE_CLAIMS, TRANSCRIPT
from rcp_rclm_runtime_v5.phase17 import resource_lean

BASE='a54e67b9b4b4f9f519b20f3999ce604b724ab401'
RETAINED_M='artifacts/development/phase17m/op-f39cc8c31d52-proof/gate/execution.json'
RETAINED_M_SHA='58991d82335214500d9c8b2d721d90444b1b9812f90edbbffae7b6cea899a922'
M_SOURCE='f39cc8c31d52030c3b07c28a024b38ab12090362'


def git(*args):
    p=subprocess.run(['git','--no-optional-locks','-C',str(ROOT),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    require(p.returncode==0,'Git read failed: '+p.stderr.decode('utf-8',errors='replace'))
    return p.stdout


def write(path,obj):path.write_bytes((json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8'))


def retained_semantic_binding():
    path=ROOT/RETAINED_M
    require(path.is_file() and not path.is_symlink(),'retained M evidence missing/linked')
    raw=path.read_bytes();require(sha(raw)==RETAINED_M_SHA,'retained M evidence bytes differ')
    e=json.loads(raw)
    require(e['schema']=='rcp-rclm.phase17m.protected-semantics-run.v1' and e['source_commit']==M_SOURCE,
            'retained M identity differs')
    anchors=selected_binding()
    require(e['predecessor_package_hash']==anchors['predecessor_package_hash'] and
            e['candidate_package_hash']==anchors['candidate_package_hash'] and e['transcript_sha256']==TRANSCRIPT,
            'M and N transaction binding differs')
    require(e['protected_semantics_gate']['status']=='passed' and e['physical_projection_formally_verified'] is False,
            'retained M scope differs')
    return {'path':RETAINED_M,'sha256':RETAINED_M_SHA,'tested_source':M_SOURCE,'proofs_rerun':False}


def control_profiles(out):
    b=selected_binding();p=Policy((0,1,4,4),24);calls=[]
    class InjectedFailure(RuntimeError):pass
    def failed_work():calls.append(1);raise InjectedFailure('declared failure control')
    with Ledger(out/'failed-work.jsonl',policy=p,expected_binding=b) as l:
        try:l.perform('vector','injected:failure','1'*64,failed_work)
        except InjectedFailure:pass
        else:raise ValueError('failure control did not fail')
        s=l.state
        require(calls==[1] and s.status=='safety_halt' and s.spent==(0,1,4,4),'failure refunded/retried')
        f={'status':s.status,'spent':list(s.spent),'charged_cost':s.charged_cost,
           'charge_sequence':list(s.charges),'journal_head':s.head,'journal_sha256':sha(l.journal_bytes()),
           'injected_failure':True,'operation_calls':len(calls)}
        replay(l.journal_bytes(),expected_head=s.head,policy=p,expected_binding=b)
    calls=[]
    with Ledger(out/'exhausted-work.jsonl',policy=Policy((0,0,0,0),0),expected_binding=b) as l:
        try:l.perform('vector','forbidden:work','2'*64,lambda:calls.append(1))
        except ResourceExhausted:pass
        else:raise ValueError('zero budget admitted work')
        s=l.state
        require(calls==[] and s.status=='resource_exhausted' and s.spent==(0,0,0,0),'exhaustion control failed')
        x={'status':s.status,'journal_head':s.head,'journal_sha256':sha(l.journal_bytes()),'spent':list(s.spent),
           'operation_calls':0,'complete_search_exhaustion':False}
    with Ledger(out/'interrupted-work.jsonl',policy=p,expected_binding=b) as l:
        l.reserve('vector','interrupted:work','3'*64);anchor=l.state.head
    with Ledger(out/'interrupted-work.jsonl',policy=p,expected_binding=b,expected_head=anchor) as l:
        require(l.state.status=='pending','pending state lost')
        l.abandon_interrupted();s=l.state
        require(s.charged_cost==24 and s.status=='safety_halt','interrupted charge refunded')
        interrupted={'status':s.status,'journal_head':s.head,'journal_sha256':sha(l.journal_bytes()),
                     'spent':list(s.spent),'charged_cost':s.charged_cost,'simulation_not_process_crash':True}
    return f,x,interrupted


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--test-fixture',action='store_true',required=True)
    ap.add_argument('--require-lean',action='store_true')
    ap.add_argument('--lean-workspace',type=Path)
    ap.add_argument('--toolchain-root',type=Path)
    args=ap.parse_args(argv)
    require(args.require_lean==(args.lean_workspace is not None),'formal mode requires prepared workspace')
    require(args.require_lean or args.toolchain_root is None,'unused toolchain argument')
    out=args.output.absolute()
    require(not out.exists() and out!=ROOT and ROOT not in out.parents,'new external output directory required')
    require(all(not p.is_symlink() and not (hasattr(p,'is_junction') and p.is_junction()) for p in (out,*out.parents)),
            'linked output path')
    require(not git('status','--porcelain'),'clean source required')
    git('merge-base','--is-ancestor',BASE,'HEAD')
    require(not git('diff','--name-only','--diff-filter=MDRTUXB','-z',BASE,'HEAD','--','python','lean','scripts'),
            'preexisting runtime or proof source changed')
    source=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip()
    out.mkdir(parents=True)
    report={'schema':'rcp-rclm.phase17n.resource-run.v1','source_commit':source,'source_tree':tree,
            'started_at_utc':datetime.now(timezone.utc).isoformat(),'os':platform.system(),
            'python_version':platform.python_version(),'preparation_checks_passed':False,
            'local_increment_checks_passed':False,'automatic_retries':0,'synthetic_fixture':True,
            'claims':{k:False for k in FALSE_CLAIMS}}
    try:
        report['retained_phase17m']=retained_semantic_binding()
        parent=reopen_phase16(capture_archive=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip',
            closure_archive=ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip',
            phase15_bundle=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip')
        transcript=(ROOT/'python/rcp_rclm_runtime_v5/tests_phase17k/fixtures/ordered_known_challenge.json').read_bytes()
        profile=run_selected_profile(parent,transcript,journal=out/'resource-journal.jsonl')
        f,x,interrupted=control_profiles(out)
        write(out/'profile.json',profile);write(out/'failed-profile.json',f)
        write(out/'exhausted-profile.json',x);write(out/'interrupted-profile.json',interrupted)
        sources={n:resource_lean.render(profile,f,source_root=ROOT,negative=None if n=='Resource' else n) for n in resource_lean.LABELS}
        for name,raw in sources.items():(out/(name+'.lean')).write_bytes(raw)
        report.update(profile=profile,failed_profile=f,exhausted_profile=x,interrupted_profile=interrupted,
            source_sha256={n:sha(b) for n,b in sources.items()},new_named_audits=list(resource_lean.NAMES),
            resource_scope='declared_candidate_and_four_value_reference_calls_only',
            old_proofs_rerun=False,live_challenge_generated=False,training_performed=False,
            full_root_assessment='blocked_missing_semantic_witnesses',complete_learned_kernel_constructed=False,
            full_goal_interpretation_supplied=False,full_information_interpretation_supplied=False,
            physical_projection_formally_verified=False,campaign_budget_authority_integrated=False)
        if args.require_lean:
            report['resource_gate']=resource_lean.check(profile,f,source_root=ROOT,lean_workspace=args.lean_workspace,
                                                      toolchain_root=args.toolchain_root)
            require(report['resource_gate']['status']=='passed','new resource Lean gate did not pass')
            require(report['resource_gate']['source_sha256']==report['source_sha256'],'compiled source differs')
        else:report['resource_gate']={'status':'not_requested','claims':{k:False for k in FALSE_CLAIMS}}
        for name,raw in sources.items():require((out/(name+'.lean')).read_bytes()==raw,'stored certificate changed')
        require(sha((out/'resource-journal.jsonl').read_bytes())==profile['journal_sha256'],'stored main journal changed')
        for name,obj in [('failed-work.jsonl',f),('exhausted-work.jsonl',x),('interrupted-work.jsonl',interrupted)]:
            require(sha((out/name).read_bytes())==obj['journal_sha256'],'stored control journal changed')
        require(retained_semantic_binding()==report['retained_phase17m'],'old evidence changed')
        require(not git('status','--porcelain') and git('rev-parse','HEAD').decode().strip()==source,'source changed')
        report.update(preparation_checks_passed=True,local_increment_checks_passed=args.require_lean,source_unchanged=True,
                      proof_mode='real_pinned_lean' if args.require_lean else 'preparation_only')
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as exc:
        report['failure']={'type':type(exc).__name__,'reason':str(exc)}
    report['finished_at_utc']=datetime.now(timezone.utc).isoformat();write(out/'execution.json',report)
    files={p.name:p.read_bytes() for p in out.iterdir() if p.is_file() and not p.name.endswith('.lock')}
    (out/'SHA256SUMS.txt').write_bytes(''.join(sha(b)+'  '+n+'\n' for n,b in sorted(files.items())).encode())
    print(json.dumps(report,indent=2))
    return 0 if report['preparation_checks_passed'] and (not args.require_lean or report['local_increment_checks_passed']) else 2

if __name__=='__main__':raise SystemExit(main())
