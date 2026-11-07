"""Source-bound Phase17H public exhaustive planner/tool witness validation.

Existing synthetic successor only; no live search, training, promotion, old proof
rerun, dependency installation, or claim of full recursive-frontier closure.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
from run_phase17_successor_gate import exclusive, git, write, FIXTURE_HASH
from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
from rcp_rclm_runtime_v5.phase17.materialized import require, sha, materialize_package, verify_package
from rcp_rclm_runtime_v5.phase17.operational_witnesses import prepare_operational, CONTRACT_SHA256, PLAN_CONTRACT, TOOL_CONTRACT
from rcp_rclm_runtime_v5.phase17.operational_lean import check_operational, render_operational, NAMES
from rcp_rclm_runtime_v5.phase17.successor_evidence import FALSE_CLAIMS


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--test-fixture', action='store_true', required=True)
    ap.add_argument('--require-lean', action='store_true')
    ap.add_argument('--lean-workspace', type=Path)
    ap.add_argument('--toolchain-root', type=Path)
    args = ap.parse_args(argv)
    require(args.require_lean == (args.lean_workspace is not None), 'formal mode requires pinned workspace')
    require(args.require_lean or args.toolchain_root is None, 'unused toolchain argument')
    output = args.output.absolute()
    require(not output.exists() and ROOT not in output.parents, 'new external output required')
    require(all(not p.is_symlink() and not (hasattr(p,'is_junction') and p.is_junction())
                for p in (output.parent, *output.parents)), 'linked output path')
    source = git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    tree = git(ROOT, 'rev-parse', 'HEAD^{tree}').decode().strip()
    require(not git(ROOT, 'status', '--porcelain'), 'clean committed source required')
    output.mkdir(parents=True)
    report = {'schema': 'rcp-rclm.phase17h.operational-run.v1', 'source_commit': source,
              'source_tree': tree, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'os': platform.system(), 'python_version': platform.python_version(),
              'automatic_retries': 0, 'synthetic_fixture': True,
              'local_increment_checks_passed': False, 'claims': {k:False for k in FALSE_CLAIMS}}
    try:
        bundle = ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
        capture = ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
        closure = ROOT/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
        fixture = ROOT/'python/rcp_rclm_runtime_v5/tests_phase17d/fixtures/known_candidate_pass.json'
        raw = fixture.read_bytes(); require(sha(raw) == FIXTURE_HASH, 'fixture changed')
        parent = reopen_phase16(capture_archive=capture, closure_archive=closure, phase15_bundle=bundle)
        before = materialize_package(output/'p', parent, bundle)
        after = materialize_package(output/'c', parent, bundle, transcript=raw, expected_transcript_hash=FIXTURE_HASH)
        prepared = prepare_operational(before, after, parent, bundle=bundle, capture=capture,
                                       transcript=raw, expected_transcript_hash=FIXTURE_HASH)
        positive, negative = render_operational(prepared), render_operational(prepared, negative=True)
        (output/'packet.json').write_bytes(prepared.packet_bytes)
        (output/'Plans.lean').write_bytes(positive); (output/'WrongOracle.lean').write_bytes(negative)
        p = prepared.packet
        report.update(packet_sha256=sha(prepared.packet_bytes), contract_sha256=CONTRACT_SHA256,
                      candidate_package_hash=after.package_hash, predecessor_package_hash=before.package_hash,
                      learned_component_groups=len(p['learned_component_projection']),
                      base_files_mapped=sum(len(g['files']) for g in p['learned_component_projection']),
                      plan_queries_per_package=p['candidate']['queries'],
                      decoded_tokens_per_package=p['candidate']['decoded_tokens'],
                      tool_executions_per_package=p['candidate']['integer_tool_outputs'],
                      exact_operational_retention=True, named_audits=list(NAMES),
                      bounded_contracts_python_passed=p['new_contracts_python_passed'],
                      bounded_contracts_certified=[], legacy_recursive_labels=19,
                      legacy_full_recursive_tasks_recertified=[],
                      public_recertification_not_hidden_evaluation=True,
                      neural_decoder_formally_verified=False, full_learned_semantic_refinement=False,
                      full_transformer_inference=False, training_performed=False)
        report['plan_semantics_gate'] = {'status': 'not_requested', 'task_semantics_checked': False}
        if args.require_lean:
            workspace = args.lean_workspace.resolve(strict=True)
            with exclusive(workspace):
                checked = check_operational(prepared, source_root=ROOT, lean_workspace=workspace,
                                            toolchain_root=args.toolchain_root)
            report['plan_semantics_gate'] = checked
            require(checked['status'] == 'passed', 'new operational plan semantics failed')
            report['bounded_contracts_certified'] = [PLAN_CONTRACT, TOOL_CONTRACT]
        verify_package(before.root, parent, bundle, expected_package_hash=before.package_hash)
        verify_package(after.root, parent, bundle, expected_package_hash=after.package_hash,
                       transcript=raw, expected_transcript_hash=FIXTURE_HASH)
        require(fixture.read_bytes() == raw and (output/'packet.json').read_bytes() == prepared.packet_bytes and
                (output/'Plans.lean').read_bytes() == positive and (output/'WrongOracle.lean').read_bytes() == negative,
                'input/evidence changed during run')
        require(git(ROOT,'rev-parse','HEAD').decode().strip() == source and not git(ROOT,'status','--porcelain'), 'source changed')
        report.update(local_increment_checks_passed=True, source_unchanged=True,
                      proof_mode='real_pinned_lean' if args.require_lean else 'preparation_only')
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        report['failure'] = {'type': type(exc).__name__, 'reason': str(exc)}
    report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    write(output/'execution.json', report)
    files = [p for p in output.rglob('*') if p.is_file() and p.relative_to(output).parts[0] not in ('p', 'c')]
    (output/'SHA256SUMS.txt').write_bytes(''.join(sha(p.read_bytes())+'  '+p.relative_to(output).as_posix()+'\n'
                                               for p in sorted(files)).encode('utf-8'))
    print(json.dumps(report, indent=2))
    return 0 if report['local_increment_checks_passed'] else 2

if __name__ == '__main__': raise SystemExit(main())
