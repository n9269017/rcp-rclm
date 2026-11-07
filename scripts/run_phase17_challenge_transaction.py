"""Execute one fresh evaluator-separated Phase 17C turn; never promote a package."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--candidate-credits',type=int,default=32)
    args=parser.parse_args()
    if not 0<=args.candidate_credits<=32:parser.error('candidate credits must be in [0,32]')
    root=Path(__file__).resolve().parents[1]
    output=args.output.resolve()
    if output.exists() or output==root or root in output.parents:
        raise SystemExit('Output must be a NEW directory outside the source repository')
    if subprocess.check_output(['git','-C',str(root),'status','--porcelain']):
        raise SystemExit('A clean committed source checkout is required')
    head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    subprocess.run([sys.executable,str(root/'scripts/phase17_refresh_checksums.py')],cwd=root,check=True)
    sys.path[:0]=[str(root/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
    from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
    from rcp_rclm_runtime_v5.phase17.challenge_transaction import run_bounded_transaction
    parent=reopen_phase16(
        capture_archive=root/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip',
        closure_archive=root/('artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/'
                              'runtime-v4-phase16-final-closure-31153935872-1.zip'),
        phase15_bundle=root/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip')
    output.mkdir(parents=True,exist_ok=False)
    # Fresh public nonce is not the evaluator entropy; no hidden seed CLI exists.
    try:
        records=run_bounded_transaction(parent,candidate_credits=args.candidate_credits,
                                        public_nonce_hash=secrets.token_hex(32))
        if subprocess.check_output(['git','-C',str(root),'status','--porcelain']) or head!=subprocess.check_output(
                ['git','-C',str(root),'rev-parse','HEAD'],text=True).strip():
            raise RuntimeError('source changed during transaction')
        records['source.json']=(json.dumps({'source_commit':head,'python_version':sys.version,
            'fresh_clean_checkout_only':False,'phase17_exit_closed':False,'gate_e_closed':False,
            'egc0_started':False},sort_keys=True,indent=2)+'\n').encode()
        lines=[]
        for name,data in sorted(records.items()):
            (output/name).write_bytes(data)
            lines.append(f'{hashlib.sha256(data).hexdigest()}  {name}\n')
        manifest=''.join(lines).encode('ascii');(output/'SHA256SUMS.txt').write_bytes(manifest)
        result=json.loads(records['transaction.json'])
        print(json.dumps({'local_transaction_verified':True,'terminal_action':result['terminal_action'],
              'candidate_evaluations':result['candidate_evaluations'],'manifest_sha256':hashlib.sha256(manifest).hexdigest(),
              'phase17_exit_closed':False,'gate_e_closed':False,'egc0_started':False},sort_keys=True))
        return 0
    except Exception:
        (output/'FAILURE.json').write_text('{"local_transaction_verified":false,"phase17_exit_closed":false}\n',encoding='utf-8')
        raise


if __name__=='__main__':raise SystemExit(main())
