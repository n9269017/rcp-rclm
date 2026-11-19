"""Phase17Z selected evaluator outputs and producer verdict-prefix refinement; no workers, promotion, or old campaigns."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'python' / f'rcp_rclm_runtime_v{version}') for version in (2, 3, 4, 5)]
from rcp_rclm_runtime_v5.phase17.evaluation_trace import (
    BASE, Y_EXECUTION, Y_EXECUTION_SHA, Y_PACKET_SHA, FALSE_CLAIMS, UNMEASURED,
    PreparedEvaluationTrace, prepare_evaluation_trace, summary as evaluation_summary,
    verify_packet_bytes, canonical, require, sha,
)
from rcp_rclm_runtime_v5.phase17.evaluation_trace_lean import (
    generated_sources, NAMES, LABELS, DEPENDENCY_LABELS, AUXILIARY_LABELS,
    restore_w_dependency, w_dependency_provenance,
)
from rcp_rclm_runtime_v5.phase17.evaluation_trace_check import check, validate_result
from rcp_rclm_runtime_v5.phase17.protected_semantics import SOURCE_PINS
from rcp_rclm_runtime_v5.phase17.resource_ledger import _no_links
from rcp_rclm_runtime.canonical.json import load_json_strict

SCHEMA = 'rcp-rclm.phase17z.evaluation-trace-execution.v1'


def git(*args):
    return subprocess.check_output(['git', '--no-optional-locks', '-C', str(ROOT), *args]).decode('utf-8').strip()


def source_paths(root=ROOT):
    # Bind complete runtime Python source, including original task definitions,
    # manifest readers and canonical parsing. These modules are not re-tested.
    names = set()
    for version in (2, 3, 4, 5):
        package = 'rcp_rclm_runtime' if version == 2 else 'rcp_rclm_runtime_v' + str(version)
        base = root / 'python' / ('rcp_rclm_runtime_v' + str(version)) / package
        names.update(path.relative_to(root).as_posix() for path in base.rglob('*.py'))
    names.update(path.relative_to(root).as_posix() for path in (root / 'lean/phase17_bridge').glob('*.lean'))
    for phase in ('q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'):
        names.update(path.relative_to(root).as_posix() for path in
                     (root / ('python/rcp_rclm_runtime_v5/tests_phase17' + phase)).glob('test_*.py'))
    names.update(SOURCE_PINS)
    names.update(('scripts/run_phase17_finite_kernel_gate.py', 'scripts/run_phase17_finite_kernel_tests.py',
                  'scripts/run_phase17_sparse_refinement_gate.py', 'scripts/run_phase17_sparse_refinement_tests.py',
                  'scripts/run_phase17_prompt_routing_gate.py', 'scripts/run_phase17_prompt_routing_tests.py',
                  'scripts/run_phase17_captured_json_gate.py', 'scripts/run_phase17_captured_json_tests.py',
                  'scripts/run_phase17_planner_refinement_gate.py', 'scripts/run_phase17_planner_refinement_tests.py',
                  'scripts/run_phase17_program_metadata_gate.py', 'scripts/run_phase17_program_metadata_tests.py',
                  'scripts/run_phase17_producer_preimages_gate.py', 'scripts/run_phase17_producer_preimages_tests.py',
                  'scripts/run_phase17_producer_sha256_gate.py', 'scripts/run_phase17_producer_sha256_tests.py',
                  'scripts/run_phase17_objective_context_gate.py', 'scripts/run_phase17_objective_context_tests.py',
                  'scripts/run_phase17_evaluation_trace_gate.py', 'scripts/run_phase17_evaluation_trace_tests.py',
                  'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/lean_root_pins.json'))
    return sorted(names)


def snapshot():
    result = {}
    for name in source_paths():
        path = ROOT / name
        _no_links(path)
        require(path.is_file(), 'missing Z source: ' + name)
        result[name] = sha(path.read_bytes())
    return result


def write(path: Path, value):
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf-8'))


def summary(prepared: PreparedEvaluationTrace):
    packet = prepared.packet
    return {'packet_sha256': sha(prepared.packet_bytes),
            'objective_context_packet_sha256': Y_PACKET_SHA, 'bindings': packet['bindings'],
            'retained_objective_context': packet['retained_y'],
            'evaluation_trace': evaluation_summary(prepared),
            'synthetic_fixture': True, 'fixture_is_live_result': False,
            'selected_frontier': [21, 22], 'new_frontier_gain_demonstrated': False,
            'full_root_assessment': 'blocked_missing_physical_and_full_semantic_witnesses'}


def dependency_proof_refactoring(sources):
    factored = sources['Phase17WDependency']
    original = restore_w_dependency(factored)
    return w_dependency_provenance(original, factored)


def verify_only(out: Path) -> int:
    _no_links(out)
    require(out.is_dir(), 'retained Z output missing')
    report_path = out / 'execution.json'
    raw_report = report_path.read_bytes()
    report = load_json_strict(raw_report, require_canonical=False)
    require(type(report) is dict and 'failure' not in report, 'failed or malformed Z execution')
    before = snapshot()
    head, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    require(report['schema'] == SCHEMA and report['source_sha256'] == before and
            report['source_commit'] == head and report['source_tree'] == tree and not git('status', '--porcelain'),
            'reconstruction requires the original clean tested Z source')
    require(report['preparation_checks_passed'] is True and report['source_unchanged'] is True,
            'Z preparation did not pass')
    require(canonical(report['claims']) == canonical({name: False for name in FALSE_CLAIMS}),
            'unsupported Z authority claim')
    require(canonical(report['retained_phase17y']) == canonical(
        {'path': Y_EXECUTION, 'sha256': Y_EXECUTION_SHA, 'sessions_rerun': False}), 'Z attribution differs')
    require(report['new_named_audits'] == list(NAMES) and report['negative_controls'] == list(LABELS[1:]) and
            report['unmeasured'] == list(UNMEASURED) and report['historical_success_reports_reassigned'] is False and
            type(report['automatic_retries']) is int and report['automatic_retries'] == 0,
            'Z audit/execution scope differs')
    raw_packet = (out / 'packet.json').read_bytes()
    with tempfile.TemporaryDirectory(prefix='r17z-replay-') as temp:
        prepared = prepare_evaluation_trace(ROOT, Path(temp) / 'packages')
        verify_packet_bytes(raw_packet, prepared, expected_sha256=report['packet_sha256'])
        require(all(canonical(report[key]) == canonical(value) for key, value in summary(prepared).items()),
                'Z summary differs from retained-preimage reconstruction')
        sources = generated_sources(prepared, source_root=ROOT)
    require(report['proof_source_sha256'] == {name: sha(raw) for name, raw in sources.items()},
            'Z generated source inventory differs')
    require(canonical(report['dependency_proof_refactoring']) ==
            canonical(dependency_proof_refactoring(sources)),
            'Z inherited W proof refactoring provenance differs')
    for name, raw in sources.items():
        path = out / (name + '.lean')
        _no_links(path)
        require(path.read_bytes() == raw, 'retained Z generated source differs')
    require(type(report['local_increment_checks_passed']) is bool, 'Z formal result must be boolean')
    if report['local_increment_checks_passed']:
        require(report['proof_mode'] == 'real_pinned_lean' and report['preparation_only'] is False and
                report['evaluator_outputs_from_opening_checked'] is True and
                report['producer_verdict_prefix_checked'] is True and
                type(report['same_run_dependency_compilations']) is int and
                report['same_run_dependency_compilations'] == len(DEPENDENCY_LABELS) and
                type(report['same_run_auxiliary_compilations']) is int and
                report['same_run_auxiliary_compilations'] == len(AUXILIARY_LABELS) and
                type(report['same_run_total_compilations']) is int and
                report['same_run_total_compilations'] == len(DEPENDENCY_LABELS) + len(AUXILIARY_LABELS),
                'Z formal mode differs')
        formal = report['evaluation_trace_gate']
        validate_result(formal, sources, report['packet_sha256'])
        progress = (out / 'formal-progress.json').read_bytes()
        require(sha(progress) == report['formal_progress_sha256'] and
                canonical(load_json_strict(progress, require_canonical=False)) == canonical(formal),
                'retained compiler progress differs from completed result')
    else:
        require(report['proof_mode'] == 'preparation_only' and report['preparation_only'] is True and
                report['evaluator_outputs_from_opening_checked'] is False and
                report['producer_verdict_prefix_checked'] is False and
                type(report['same_run_dependency_compilations']) is int and
                report['same_run_dependency_compilations'] == 0 and
                type(report['same_run_auxiliary_compilations']) is int and report['same_run_auxiliary_compilations'] == 0 and
                type(report['same_run_total_compilations']) is int and report['same_run_total_compilations'] == 0 and
                report['formal_progress_sha256'] is None,
                'inconsistent Z preparation mode')
    require(type(report['fresh_worker_sessions']) is int and report['fresh_worker_sessions'] == 0 and
            type(report['fresh_live_challenges']) is int and report['fresh_live_challenges'] == 0 and
            report['old_proof_campaigns_rerun'] is False, 'Z campaign scope differs')
    require(snapshot() == before and git('rev-parse', 'HEAD') == head and git('rev-parse', 'HEAD^{tree}') == tree and
            not git('status', '--porcelain') and report_path.read_bytes() == raw_report and
            (out / 'packet.json').read_bytes() == raw_packet, 'Z source/evidence changed during reconstruction')
    print('PASS: complete selected evaluator outputs, verdict prefix, reference work and retained Q/R/S/T/U/V/W/X/Y/Z proof inputs reconstructed; no workers, challenges, or compiler runs')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--test-fixture', action='store_true')
    parser.add_argument('--require-lean', action='store_true')
    parser.add_argument('--lean-workspace', type=Path)
    parser.add_argument('--toolchain-root', type=Path)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args(argv)
    out = args.output.absolute()
    _no_links(out)
    out = out.resolve()
    require(out != ROOT and ROOT not in out.parents, 'external Z output required')
    if args.verify_only:
        require(not args.require_lean and args.lean_workspace is None and args.toolchain_root is None,
                'retained Z verification does not invoke Lean')
        return verify_only(out)
    require(args.test_fixture, 'explicit synthetic-fixture mode required')
    require(args.require_lean == (args.lean_workspace is not None), 'Z formal mode requires prepared pinned workspace')
    require(args.require_lean or args.toolchain_root is None, 'unused Z toolchain root')
    require(not out.exists(), 'new Z output required; preserve earlier attempts')
    packages = out.with_name(out.name + '-packages')
    _no_links(packages)
    require(not packages.exists(), 'new Z physical workspace required; preserve earlier attempts')
    require(not git('status', '--porcelain'), 'clean committed Z source required')
    source, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', BASE, source], check=True)
    require(not git('diff', '--name-only', '--diff-filter=MDRTUXB', BASE, 'HEAD', '--', 'python', 'lean', 'scripts'),
            'preexisting execution/formal source changed')
    before = snapshot()
    out.mkdir(parents=True)
    report = {'schema': SCHEMA, 'source_commit': source, 'source_tree': tree, 'source_sha256': before,
              'os': platform.system(), 'python_version': platform.python_version(),
              'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'preparation_only': not args.require_lean,
              'proof_mode': 'real_pinned_lean' if args.require_lean else 'preparation_only',
              'preparation_checks_passed': False, 'local_increment_checks_passed': False,
              'evaluator_outputs_from_opening_checked': False, 'producer_verdict_prefix_checked': False,
              'retained_phase17y': {'path': Y_EXECUTION, 'sha256': Y_EXECUTION_SHA, 'sessions_rerun': False},
              'fresh_worker_sessions': 0, 'fresh_live_challenges': 0, 'automatic_retries': 0,
              'old_proof_campaigns_rerun': False, 'historical_success_reports_reassigned': False,
              'same_run_dependency_compilations': 0, 'same_run_auxiliary_compilations': 0,
              'same_run_total_compilations': 0, 'formal_progress_sha256': None,
              'new_named_audits': list(NAMES), 'negative_controls': list(LABELS[1:]),
              'claims': {name: False for name in FALSE_CLAIMS}, 'unmeasured': list(UNMEASURED)}
    write(out / 'execution.json', report)
    try:
        prepared = prepare_evaluation_trace(ROOT, packages)
        (out / 'packet.json').write_bytes(prepared.packet_bytes)
        report.update(summary(prepared))
        sources = generated_sources(prepared, source_root=ROOT)
        for name, raw in sources.items():
            (out / (name + '.lean')).write_bytes(raw)
        report['proof_source_sha256'] = {name: sha(raw) for name, raw in sources.items()}
        report['dependency_proof_refactoring'] = dependency_proof_refactoring(sources)
        write(out / 'execution.json', report)
        if args.require_lean:
            formal = check(prepared, source_root=ROOT, lean_workspace=args.lean_workspace,
                           toolchain_root=args.toolchain_root, progress_path=out / 'formal-progress.json')
            report['evaluation_trace_gate'] = formal
            report['formal_progress_sha256'] = sha((out / 'formal-progress.json').read_bytes())
            validate_result(formal, sources, report['packet_sha256'])
            report['same_run_dependency_compilations'] = len(DEPENDENCY_LABELS)
            report['same_run_auxiliary_compilations'] = len(AUXILIARY_LABELS)
            report['same_run_total_compilations'] = len(DEPENDENCY_LABELS) + len(AUXILIARY_LABELS)
        else:
            report['evaluation_trace_gate'] = {'status': 'not_requested'}
        for name, raw in sources.items():
            require((out / (name + '.lean')).read_bytes() == raw, 'saved Z proof source changed')
        verify_packet_bytes((out / 'packet.json').read_bytes(), prepared, expected_sha256=report['packet_sha256'])
        require(snapshot() == before and git('rev-parse', 'HEAD') == source and not git('status', '--porcelain'),
                'source changed during Z gate')
        report.update(source_unchanged=True, preparation_checks_passed=True,
                      local_increment_checks_passed=args.require_lean,
                      evaluator_outputs_from_opening_checked=args.require_lean,
                      producer_verdict_prefix_checked=args.require_lean)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        report['failure'] = {'type': type(exc).__name__, 'reason': str(exc)}
    finally:
        report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        write(out / 'execution.json', report)
        files = {path.name: path.read_bytes() for path in out.iterdir() if path.is_file()}
        (out / 'SHA256SUMS.txt').write_bytes(''.join(sha(raw) + '  ' + name + '\n'
            for name, raw in sorted(files.items())).encode('ascii'))
        print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report['preparation_checks_passed'] and (not args.require_lean or report['local_increment_checks_passed']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
