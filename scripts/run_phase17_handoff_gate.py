"""Phase17P mandatory inactive handoff gate. No old proof or campaign reruns."""
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
from rcp_rclm_runtime_v5.phase17.handoff_validation import execute_profile,verify_profile
from rcp_rclm_runtime_v5.phase17.campaign_transaction import FALSE_CLAIMS

BASE='11e866f7a843bccb95f4a8e3f86a10aa594ff677'
O_PATH='artifacts/development/phase17o/op-f96ec5214212/gate/execution.json'
O_HASH='7c7d0d68ab78ae08069839e54453bb5a1fe376189a393e62062e6a9a2f4a0d62'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(ROOT),*args]).decode().strip()
def source_paths(root=ROOT):
    paths={p.relative_to(root).as_posix() for p in (root/'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17').glob('*.py')}
    paths.update('python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase16/'+n+'.py' for n in ('constants','grammar','ranking','records','codec'))
    paths.update(('scripts/phase17_campaign_worker.py','scripts/run_phase17_handoff_gate.py',
        'scripts/run_phase17_handoff_tests.py','python/rcp_rclm_runtime_v5/tests_phase17p/test_handoff.py',
        'python/rcp_rclm_runtime_v5/tests_phase17k/fixtures/ordered_known_challenge.json'))
    return sorted(paths)
def snapshot():return {p:sha((ROOT/p).read_bytes()) for p in source_paths()}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--packages',type=Path,help='new external scratch directory; required for execution')
    ap.add_argument('--preparation-only',action='store_true',help='explicitly not accepted by installer; records no Git provenance')
    ap.add_argument('--verify-only',action='store_true',help='recompute retained profile; launches no workers or proofs')
    args=ap.parse_args()
    out=args.output.resolve()
    if args.verify_only:
        report=json.loads((out/'execution.json').read_bytes())
        actual=verify_profile(ROOT,out/'profile')
        if report['profile']!=actual:raise ValueError('profile execution report differs')
        if report['source_sha256']!=snapshot():raise ValueError('current source differs from recorded source')
        print('PASS: inactive handoff evidence and physical candidates reconstructed; no workers, new entropy or proofs')
        return 0
    if out.exists():raise ValueError('new output directory required; preserve existing evidence')
    if out==ROOT or ROOT in out.parents:raise ValueError('evidence output must be outside source checkout')
    before=snapshot()
    source=tree=None;retained=None
    if not args.preparation_only:
        source,tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}')
        if git('status','--porcelain'):raise ValueError('clean committed source required')
        subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',BASE,source],check=True)
        raw=(ROOT/O_PATH).read_bytes()
        if sha(raw)!=O_HASH:raise ValueError('retained Phase17O identity changed')
        n=json.loads(raw)
        if n['local_increment_checks_passed'] is not True or n['source_commit']!='f96ec5214212abc393eec46a161b1627f1dcccd7':
            raise ValueError('retained Phase17O record differs')
        retained={'path':O_PATH,'sha256':O_HASH,'sessions_rerun':False}
    if args.packages is None:raise ValueError('external --packages path required')
    packages=args.packages.absolute()
    from rcp_rclm_runtime_v5.phase17.resource_ledger import _no_links
    _no_links(packages);_no_links(out)
    if packages.exists() or packages==ROOT or ROOT in packages.parents or packages==out or out in packages.parents or packages in out.parents:
        raise ValueError('new nonoverlapping package workspace required')
    packages.mkdir(parents=True)
    out.mkdir(parents=True);(out/'profile').mkdir()
    report={'schema':'rcp-rclm.phase17p.handoff-run.v1','source_commit':source,'source_tree':tree,
        'preparation_only':args.preparation_only,'source_sha256':before,'os':platform.system(),
        'python_version':platform.python_version(),'started_at_utc':datetime.now(timezone.utc).isoformat(),
        'retained_phase17o':retained,'new_lean_audits':0,'old_proofs_rerun':False,
        'automatic_retries':0,'local_increment_checks_passed':False,'claims':dict(FALSE_CLAIMS)}
    try:
        report['profile']=execute_profile(ROOT,out/'profile',packages)
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
