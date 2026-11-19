"""Materialize and freshly evaluate the inherited 21-task capability frontier.

Default: prepare 13 Lean obligations without claiming formal success. Opt in to
--require-lean only with the existing pinned toolchain/dependencies installed.
No model training, active-store mutation, promotion, network bootstrap or Git write.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--require-lean',action='store_true')
    parser.add_argument('--toolchain-root',type=Path)
    parser.add_argument('--lean-workspace',type=Path,help='Operator-provided existing repository with the SAME pinned formal root and prepared dependencies')
    parser.add_argument('--candidate-transcript',type=Path)
    parser.add_argument('--transcript-sha256')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    sys.path[:0]=[str(root/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
    from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
    from rcp_rclm_runtime_v5.phase17.materialized import materialize_package, require
    from rcp_rclm_runtime_v5.phase17.frontier_recertification import prepare_frontier, evaluate_candidate_package
    from rcp_rclm_runtime_v5.phase17.lean_frontier_gate import recertify_package, root_source_fingerprint, TOOLCHAIN
    require((args.candidate_transcript is None)==(args.transcript_sha256 is None), 'candidate transcript and anchor required together')
    require(args.require_lean or (args.toolchain_root is None and args.lean_workspace is None), 'Lean workspace/toolchain options require --require-lean')
    output=args.output.resolve()
    require(not output.exists() and output!=root and root not in output.parents,'new output outside repository required')
    head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    tree=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD^{tree}'],text=True).strip()
    require(not subprocess.check_output(['git','-C',str(root),'status','--porcelain']), 'clean committed source required')
    bundle=root/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
    capture=root/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
    closure=root/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
    parent=reopen_phase16(capture_archive=capture,closure_archive=closure,phase15_bundle=bundle)
    transcript=None if args.candidate_transcript is None else args.candidate_transcript.read_bytes()
    root_fingerprint=root_source_fingerprint(root)
    output.mkdir(parents=True)
    package=materialize_package(output/'package',parent,bundle,transcript=transcript,
                                expected_transcript_hash=args.transcript_sha256)
    prepared=prepare_frontier(package,parent,bundle=bundle,capture=capture,transcript=transcript,
                              expected_transcript_hash=args.transcript_sha256)
    (output/'prepared_frontier.json').write_bytes(prepared.report_bytes)
    proofs=output/'proof_sources';proofs.mkdir()
    for name,raw in prepared.sources:(proofs/(name+'.lean')).write_bytes(raw)
    candidate_report=None
    if transcript is not None:
        candidate_report=evaluate_candidate_package(package,parent,bundle=bundle,transcript=transcript,
                                                     expected_transcript_hash=args.transcript_sha256)
    gate={'status':'not_requested','toolchain':TOOLCHAIN,'fresh_lean_verified':False,
          'capability_frontier_recertified':False,'root_transition_verified':False,
          'promotion_authorized':False,'phase17_exit_closed':False,'gate_e_closed':False}
    if args.require_lean:
        lean_workspace=root if args.lean_workspace is None else args.lean_workspace.resolve()
        gate=recertify_package(package,parent,repository=lean_workspace,bundle=bundle,capture=capture,
                              toolchain_root=args.toolchain_root,transcript=transcript,
                              expected_transcript_hash=args.transcript_sha256)
    after=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    require(after==head and not subprocess.check_output(['git','-C',str(root),'status','--porcelain']),
            'source changed during preparation')
    require(root_source_fingerprint(root)==root_fingerprint,'formal root source changed')
    summary={'schema':'rcp-rclm.phase17d.package-gate-run.v1','source_commit':head,'source_tree':tree,
             'os':platform.system(),'python_version':platform.python_version(),
             'package_hash':package.package_hash,'base_parameter_count':13625920,
             'capability_tasks_evaluated':21,'lean_obligations_prepared':13,
             'python_frontier_evaluation_passed':True,'lean_gate':gate,
             'candidate_evaluation':candidate_report,
             'full_transformer_inference':False,'recursive_productivity_recertified':False,
             'full_frontier_recertified':False,'root_transition_verified':False,
             'promotion_performed':False,'phase17_exit_closed':False,'gate_e_closed':False,
             'egc0_started':False,'source_unchanged':True}
    (output/'execution.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n',encoding='utf-8',newline='\n')
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(output).as_posix()+'\n'
                     for p in sorted(output.rglob('*')) if p.is_file())
    (output/'SHA256SUMS.txt').write_bytes(manifest.encode())
    print(json.dumps({k:summary[k] for k in ('source_commit','package_hash','capability_tasks_evaluated',
          'lean_obligations_prepared','lean_gate','promotion_performed','phase17_exit_closed','gate_e_closed')},indent=2))
    return 0 if not args.require_lean or gate['status']=='passed' else 2


if __name__=='__main__':
    raise SystemExit(main())
