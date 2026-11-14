"""Phase17G source-bound scoped semantic refinement; inactive synthetic fixture.

Reuse the unchanged Phase17F candidate proof only after exact source/artifact
identity checks. Execute NEW semantic proofs with real Lean when requested.
No broad root acceptance, promotion, live campaign, or resource-closure claim.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
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
from rcp_rclm_runtime_v5.phase17.materialized import require,sha,materialize_package,verify_package
from rcp_rclm_runtime_v5.phase17.conservative_extension import prepare_conservative
from rcp_rclm_runtime_v5.phase17.conservative_lean import render,check_conservative,BRIDGE_PATH,NAMES
from rcp_rclm_runtime_v5.phase17.successor_evidence import FALSE_CLAIMS
from rcp_rclm_runtime_v5.phase17.lean_frontier_gate import root_source_fingerprint

BASE='7de254018946dd4a782f758dc21913d0796273c1'
PRIOR='artifacts/development/phase17f/op-84a6e45ed4d7-utf8/gate/execution.json'
PRIOR_SHA='eeafc1a64b173578860c0ac1cb144973e67b9cf3a48e112df331626665a1d1bc'


def reused_candidate_proof(prepared,root:Path) -> dict:
    raw=(root/PRIOR).read_bytes()
    require(sha(raw)==PRIOR_SHA,'retained Phase17F execution changed')
    report=json.loads(raw)
    require(report['synthetic_fixture'] is True and report['capability_tasks_evaluated']==21,
            'wrong historical candidate evidence')
    require(report['candidate_package_hash']==prepared.packet['bindings']['candidate_physical_hash'],
            'prior proof belongs to another package')
    require(report['finite_successor_gate']['packet_sha256']==prepared.packet['phase17f_packet_sha256'],
            'fresh candidate facts differ from the prior checked packet')
    inherited=report['inherited_capability_gate']
    require(inherited['status']=='passed' and inherited['fresh_lean_verified'] is True and
            len(inherited['proofs'])==13,'prior capability proof incomplete')
    # Reject ANY changed existing executable in the relevant source trees. New
    # Phase17G files are absent from BASE and separately source-bound by the run.
    prefixes=('python/', 'lean/', 'scripts/')
    modified=git(root,'diff','--name-only','--diff-filter=MDRTUXB',BASE,'HEAD').decode('utf-8').splitlines()
    require(not any(p.startswith(prefixes) for p in modified),'existing semantics changed; prior proof cannot be reused')
    return {'retained_execution_sha256':PRIOR_SHA,'source_commit':report['source_commit'],
            'candidate_package_hash':report['candidate_package_hash'],
            'inherited_obligations_retained_not_rerun':13,
            'prior_four_finite_audits_retained_not_rerun':4,
            'freshly_recomputed_packet_matches':True}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--test-fixture',action='store_true',required=True)
    ap.add_argument('--require-lean',action='store_true')
    ap.add_argument('--lean-workspace',type=Path)
    ap.add_argument('--toolchain-root',type=Path)
    args=ap.parse_args(argv)
    require(args.require_lean==(args.lean_workspace is not None),'formal mode requires existing pinned workspace')
    require(args.require_lean or args.toolchain_root is None,'unused toolchain argument')
    output=args.output.absolute()
    require(not output.exists() and ROOT not in output.parents,'new external output required')
    require(all(not p.is_symlink() and not (hasattr(p,'is_junction') and p.is_junction())
                for p in (output.parent,*output.parents)),'linked output path')
    source=git(ROOT,'rev-parse','HEAD').decode().strip();tree=git(ROOT,'rev-parse','HEAD^{tree}').decode().strip()
    require(not git(ROOT,'status','--porcelain'),'clean committed source required')
    output.mkdir(parents=True)
    report={'schema':'rcp-rclm.phase17g.conservative-run.v1','source_commit':source,'source_tree':tree,
            'started_at_utc':datetime.now(timezone.utc).isoformat(),'python_version':platform.python_version(),
            'os':platform.system(),'synthetic_fixture':True,'automatic_retries':0,
            'local_increment_checks_passed':False,'claims':{k:False for k in FALSE_CLAIMS}}
    try:
        bundle=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
        capture=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
        closure=ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
        fixture=ROOT/'python/rcp_rclm_runtime_v5/tests_phase17d/fixtures/known_candidate_pass.json'
        raw=fixture.read_bytes();require(sha(raw)==FIXTURE_HASH,'fixture changed')
        parent=reopen_phase16(capture_archive=capture,closure_archive=closure,phase15_bundle=bundle)
        before=materialize_package(output/'p',parent,bundle)
        after=materialize_package(output/'c',parent,bundle,transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        prepared=prepare_conservative(before,after,parent,bundle=bundle,capture=capture,
                                      transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        (output/'packet.json').write_bytes(prepared.packet_bytes)
        template=(ROOT/BRIDGE_PATH).read_bytes()
        positive,negative=render(prepared,template),render(prepared,template,negative=True)
        (output/'Conservative.lean').write_bytes(positive);(output/'Shadowed.lean').write_bytes(negative)
        report.update(packet_sha256=sha(prepared.packet_bytes),candidate_package_hash=after.package_hash,
                      inherited_execution_checks=len(prepared.packet['inherited_execution_checks']),
                      candidate_execution_checks=len(prepared.packet['candidate_execution_checks']),
                      protected_file_count=prepared.packet['protected_file_count'],
                      physical_inverse_exact=True,base_obligation_count=11,
                      named_audits=list(NAMES),operational_recursive_tasks_recertified=[],
                      resource_scope='candidate evaluation credits only')
        report['semantic_gate']={'status':'not_requested','scoped_base_obligations_checked':False}
        if args.require_lean:
            report['reused_phase17f']=reused_candidate_proof(prepared,ROOT)
            workspace=args.lean_workspace.resolve(strict=True)
            require({k:v['canonical_sha256'] for k,v in root_source_fingerprint(ROOT).items()}==
                    {k:v['canonical_sha256'] for k,v in root_source_fingerprint(workspace).items()},'root differs')
            with exclusive(workspace):
                checked=check_conservative(prepared,source_root=ROOT,lean_workspace=workspace,toolchain_root=args.toolchain_root)
            report['semantic_gate']=checked
            require(checked['status']=='passed','new scoped semantic gate failed')
        verify_package(before.root,parent,bundle,expected_package_hash=before.package_hash)
        verify_package(after.root,parent,bundle,expected_package_hash=after.package_hash,
                       transcript=raw,expected_transcript_hash=FIXTURE_HASH)
        require((ROOT/BRIDGE_PATH).read_bytes()==template and fixture.read_bytes()==raw,'inputs changed')
        require((output/'packet.json').read_bytes()==prepared.packet_bytes and
                (output/'Conservative.lean').read_bytes()==positive and (output/'Shadowed.lean').read_bytes()==negative,
                'retained evidence bytes changed')
        require(git(ROOT,'rev-parse','HEAD').decode().strip()==source and not git(ROOT,'status','--porcelain'), 'source changed')
        report.update(local_increment_checks_passed=True,source_unchanged=True,
                      proof_mode='real_pinned_lean' if args.require_lean else 'preparation_only')
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        report['failure']={'type':type(exc).__name__,'reason':str(exc)}
    report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    write(output/'execution.json',report)
    files=[p for p in output.rglob('*') if p.is_file() and p.relative_to(output).parts[0] not in ('p','c')]
    (output/'SHA256SUMS.txt').write_bytes(''.join(sha(p.read_bytes())+'  '+p.relative_to(output).as_posix()+'\n'
                                               for p in sorted(files)).encode())
    print(json.dumps(report,indent=2))
    return 0 if report['local_increment_checks_passed'] else 2

if __name__=='__main__':raise SystemExit(main())
