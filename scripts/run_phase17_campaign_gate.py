"""Phase17O mandatory online integration gate; no old proof or campaign reruns."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
sys.dont_write_bytecode=True
from rcp_rclm_runtime_v5.phase17.campaign_validation import execute_profile,verify_profile
from rcp_rclm_runtime_v5.phase17.campaign_transaction import FALSE_CLAIMS

BASE='6e487bf8000747123942255a9f21216d4c4c3b93'
N_PATH='artifacts/development/phase17n/op-2a7186e3590f/gate/execution.json'
N_HASH='169f05f56749401bc1a348243468493ecc8bbb543fbd8a1e78844f6cea42d4db'
SOURCES=(
 'campaign_budget.py','campaign_client.py','campaign_transaction.py','campaign_validation.py','metered_worker.py',
 'resource_ledger.py','controller.py','bootstrap.py','objectives.py','phase16_adapter.py',
 'challenge_protocol.py','challenge_client.py')

def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(ROOT),*args]).decode().strip()
def snapshot():
    paths=['python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/'+s for s in SOURCES]
    paths+=['scripts/phase17_campaign_worker.py','scripts/run_phase17_campaign_gate.py',
            'scripts/run_phase17_campaign_tests.py','python/rcp_rclm_runtime_v5/tests_phase17o/test_campaign_budget.py']
    paths+=['python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase16/'+s+'.py' for s in ('constants','grammar','ranking','records','codec')]
    return {p:sha((ROOT/p).read_bytes()) for p in paths}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--preparation-only',action='store_true',help='explicitly not accepted by installer; records no Git provenance')
    ap.add_argument('--verify-only',action='store_true',help='recompute retained profile; launches no workers or proofs')
    args=ap.parse_args()
    out=args.output.resolve()
    if args.verify_only:
        report=json.loads((out/'execution.json').read_bytes())
        actual=verify_profile(ROOT,out/'profile')
        if report['profile']!=actual:raise ValueError('profile execution report differs')
        if report['source_sha256']!=snapshot():raise ValueError('current source differs from recorded source')
        print('PASS: existing campaign profile recomputed; no workers or proofs rerun')
        return 0
    if out.exists():raise ValueError('new output directory required; preserve existing evidence')
    if out==ROOT or ROOT in out.parents:raise ValueError('evidence output must be outside source checkout')
    before=snapshot()
    source=tree=None;retained=None
    if not args.preparation_only:
        source,tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}')
        if git('status','--porcelain'):raise ValueError('clean committed source required')
        subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',BASE,source],check=True)
        raw=(ROOT/N_PATH).read_bytes()
        if sha(raw)!=N_HASH:raise ValueError('retained Phase17N identity changed')
        n=json.loads(raw)
        if n['resource_gate']['status']!='passed' or n['source_commit']!='2a7186e3590fb7f77dc217f90587ec6511fb5d72':
            raise ValueError('retained Phase17N record differs')
        retained={'path':N_PATH,'sha256':N_HASH,'proofs_rerun':False}
    out.mkdir(parents=True);(out/'profile').mkdir()
    report={'schema':'rcp-rclm.phase17o.campaign-run.v1','source_commit':source,'source_tree':tree,
        'preparation_only':args.preparation_only,'source_sha256':before,'os':platform.system(),
        'python_version':platform.python_version(),'started_at_utc':datetime.now(timezone.utc).isoformat(),
        'retained_phase17n':retained,'new_lean_audits':0,'old_proofs_rerun':False,
        'automatic_retries':0,'local_increment_checks_passed':False,'claims':dict(FALSE_CLAIMS)}
    try:
        report['profile']=execute_profile(ROOT,out/'profile')
        if snapshot()!=before:raise ValueError('source changed during gate')
        if not args.preparation_only and (git('status','--porcelain') or git('rev-parse','HEAD')!=source):
            raise ValueError('checkout changed during gate')
        report.update(source_unchanged=True,local_increment_checks_passed=True)
    except Exception as exc:
        report['failure']={'type':type(exc).__name__,'reason':str(exc)}
    finally:
        report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        (out/'execution.json').write_bytes((json.dumps(report,sort_keys=True,indent=2)+'\n').encode())
        print(json.dumps(report,sort_keys=True,indent=2))
    return 0 if report['local_increment_checks_passed'] else 2

if __name__=='__main__':raise SystemExit(main())
