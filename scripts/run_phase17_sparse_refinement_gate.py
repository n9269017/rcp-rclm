"""Phase17R captured-byte refinement; no workers, promotion, or old campaigns."""
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
from rcp_rclm_runtime_v5.phase17.sparse_refinement import (
    BASE, Q_EXECUTION, Q_EXECUTION_SHA, Q_PACKET_SHA, FALSE_CLAIMS, UNMEASURED,
    TENSOR_BYTES, VOCAB, PreparedSparseRefinement, prepare_sparse_refinement,
    verify_packet_bytes, canonical, require, sha,
)
from rcp_rclm_runtime_v5.phase17.sparse_refinement_lean import generated_sources, NAMES, LABELS
from rcp_rclm_runtime_v5.phase17.sparse_refinement_check import check, validate_result
from rcp_rclm_runtime_v5.phase17.protected_semantics import SOURCE_PINS
from rcp_rclm_runtime_v5.phase17.resource_ledger import _no_links
from rcp_rclm_runtime.canonical.json import load_json_strict

SCHEMA = 'rcp-rclm.phase17r.sparse-byte-refinement-execution.v1'


def git(*args):
    return subprocess.check_output(['git', '--no-optional-locks', '-C', str(ROOT), *args]).decode('utf-8').strip()


def source_paths(root=ROOT):
    names = {path.relative_to(root).as_posix()
             for path in (root / 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17').glob('*.py')}
    names.update(path.relative_to(root).as_posix() for path in (root / 'lean/phase17_bridge').glob('*.lean'))
    for phase in ('q', 'r'):
        names.update(path.relative_to(root).as_posix() for path in
                     (root / ('python/rcp_rclm_runtime_v5/tests_phase17' + phase)).glob('test_*.py'))
    names.update(SOURCE_PINS)
    names.update(('scripts/run_phase17_finite_kernel_gate.py', 'scripts/run_phase17_finite_kernel_tests.py',
                  'scripts/run_phase17_sparse_refinement_gate.py', 'scripts/run_phase17_sparse_refinement_tests.py',
                  'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/lean_root_pins.json'))
    return sorted(names)


def snapshot():
    result = {}
    for name in source_paths():
        path = ROOT / name
        _no_links(path)
        require(path.is_file(), 'missing R source: ' + name)
        result[name] = sha(path.read_bytes())
    return result


def write(path: Path, value):
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf-8'))


def summary(prepared: PreparedSparseRefinement):
    packet = prepared.packet
    return {'packet_sha256': sha(prepared.packet_bytes),
            'finite_packet_sha256': Q_PACKET_SHA, 'bindings': packet['bindings'],
            'retained_sha256': packet['retained_q'], 'tensor_sha256': packet['tensor_sha256'],
            'tensor_bytes_per_package': TENSOR_BYTES,
            'nonzero_bytes_per_package': {side: len(packet[side]['nonzero_bytes']) for side in ('before', 'after')},
            'score_cells_per_package': VOCAB * VOCAB, 'conditional_rows_per_package': VOCAB,
            'production_row_comparisons': 2 * VOCAB,
            'protected_task_count': len(packet['markers']),
            'protected_target_positions': sum(map(len, packet['targets'])),
            'greedy_continuation_comparisons': 2 * len(packet['markers']),
            'synthetic_fixture': True, 'fixture_is_live_result': False,
            'selected_frontier': [21, 22], 'new_frontier_gain_demonstrated': False,
            'full_root_assessment': 'blocked_missing_physical_and_full_semantic_witnesses'}


def verify_only(out: Path) -> int:
    _no_links(out)
    require(out.is_dir(), 'retained R output missing')
    report_path = out / 'execution.json'
    raw_report = report_path.read_bytes()
    report = load_json_strict(raw_report, require_canonical=False)
    require(type(report) is dict and 'failure' not in report, 'failed or malformed R execution')
    before = snapshot()
    head, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    require(report['schema'] == SCHEMA and report['source_sha256'] == before and
            report['source_commit'] == head and report['source_tree'] == tree and not git('status', '--porcelain'),
            'reconstruction requires the original clean tested R source')
    require(report['preparation_checks_passed'] is True and report['source_unchanged'] is True,
            'R preparation did not pass')
    require(canonical(report['claims']) == canonical({name: False for name in FALSE_CLAIMS}),
            'unsupported R authority claim')
    require(canonical(report['retained_phase17q']) == canonical(
        {'path': Q_EXECUTION, 'sha256': Q_EXECUTION_SHA, 'sessions_rerun': False}), 'Q attribution differs')
    require(report['new_named_audits'] == list(NAMES) and report['negative_controls'] == list(LABELS[1:]) and
            report['unmeasured'] == list(UNMEASURED) and report['historical_success_reports_reassigned'] is False and
            type(report['automatic_retries']) is int and report['automatic_retries'] == 0,
            'R audit/execution scope differs')
    raw_packet = (out / 'packet.json').read_bytes()
    with tempfile.TemporaryDirectory(prefix='r17r-replay-') as temp:
        prepared = prepare_sparse_refinement(ROOT, Path(temp) / 'packages')
        verify_packet_bytes(raw_packet, prepared, expected_sha256=report['packet_sha256'])
        require(all(canonical(report[key]) == canonical(value) for key, value in summary(prepared).items()),
                'R summary differs from captured-byte reconstruction')
        sources = generated_sources(prepared, source_root=ROOT)
    require(report['proof_source_sha256'] == {name: sha(raw) for name, raw in sources.items()},
            'R generated source inventory differs')
    for name, raw in sources.items():
        path = out / (name + '.lean')
        _no_links(path)
        require(path.read_bytes() == raw, 'retained R generated source differs')
    require(type(report['local_increment_checks_passed']) is bool, 'R formal result must be boolean')
    if report['local_increment_checks_passed']:
        require(report['proof_mode'] == 'real_pinned_lean' and report['preparation_only'] is False and
                report['sparse_tensor_projection_checked'] is True and
                report['protected_sparse_decoder_checked'] is True and
                type(report['same_run_dependency_compilations']) is int and
                report['same_run_dependency_compilations'] == 1, 'R formal mode differs')
        formal = report['sparse_refinement_gate']
        validate_result(formal, sources, report['packet_sha256'])
        progress = (out / 'formal-progress.json').read_bytes()
        require(sha(progress) == report['formal_progress_sha256'] and
                canonical(load_json_strict(progress, require_canonical=False)) == canonical(formal),
                'retained compiler progress differs from completed result')
    else:
        require(report['proof_mode'] == 'preparation_only' and report['preparation_only'] is True and
                report['sparse_tensor_projection_checked'] is False and
                report['protected_sparse_decoder_checked'] is False and
                type(report['same_run_dependency_compilations']) is int and
                report['same_run_dependency_compilations'] == 0 and report['formal_progress_sha256'] is None,
                'inconsistent R preparation mode')
    require(type(report['fresh_worker_sessions']) is int and report['fresh_worker_sessions'] == 0 and
            type(report['fresh_live_challenges']) is int and report['fresh_live_challenges'] == 0 and
            report['old_proof_campaigns_rerun'] is False, 'R campaign scope differs')
    require(snapshot() == before and git('rev-parse', 'HEAD') == head and git('rev-parse', 'HEAD^{tree}') == tree and
            not git('status', '--porcelain') and report_path.read_bytes() == raw_report and
            (out / 'packet.json').read_bytes() == raw_packet, 'R source/evidence changed during reconstruction')
    print('PASS: complete tensor bytes, sparse semantics and retained proof inputs reconstructed; no workers, challenges, or compiler runs')
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
    require(out != ROOT and ROOT not in out.parents, 'external R output required')
    if args.verify_only:
        require(not args.require_lean and args.lean_workspace is None and args.toolchain_root is None,
                'retained R verification does not invoke Lean')
        return verify_only(out)
    require(args.test_fixture, 'explicit synthetic-fixture mode required')
    require(args.require_lean == (args.lean_workspace is not None), 'R formal mode requires prepared pinned workspace')
    require(args.require_lean or args.toolchain_root is None, 'unused R toolchain root')
    require(not out.exists(), 'new R output required; preserve earlier attempts')
    packages = out.with_name(out.name + '-packages')
    _no_links(packages)
    require(not packages.exists(), 'new R physical workspace required; preserve earlier attempts')
    require(not git('status', '--porcelain'), 'clean committed R source required')
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
              'sparse_tensor_projection_checked': False, 'protected_sparse_decoder_checked': False,
              'retained_phase17q': {'path': Q_EXECUTION, 'sha256': Q_EXECUTION_SHA, 'sessions_rerun': False},
              'fresh_worker_sessions': 0, 'fresh_live_challenges': 0, 'automatic_retries': 0,
              'old_proof_campaigns_rerun': False, 'historical_success_reports_reassigned': False,
              'same_run_dependency_compilations': 0, 'formal_progress_sha256': None,
              'new_named_audits': list(NAMES), 'negative_controls': list(LABELS[1:]),
              'claims': {name: False for name in FALSE_CLAIMS}, 'unmeasured': list(UNMEASURED)}
    write(out / 'execution.json', report)
    try:
        prepared = prepare_sparse_refinement(ROOT, packages)
        (out / 'packet.json').write_bytes(prepared.packet_bytes)
        report.update(summary(prepared))
        sources = generated_sources(prepared, source_root=ROOT)
        for name, raw in sources.items():
            (out / (name + '.lean')).write_bytes(raw)
        report['proof_source_sha256'] = {name: sha(raw) for name, raw in sources.items()}
        write(out / 'execution.json', report)
        if args.require_lean:
            formal = check(prepared, source_root=ROOT, lean_workspace=args.lean_workspace,
                           toolchain_root=args.toolchain_root, progress_path=out / 'formal-progress.json')
            report['sparse_refinement_gate'] = formal
            report['formal_progress_sha256'] = sha((out / 'formal-progress.json').read_bytes())
            validate_result(formal, sources, report['packet_sha256'])
            report['same_run_dependency_compilations'] = 1
        else:
            report['sparse_refinement_gate'] = {'status': 'not_requested'}
        for name, raw in sources.items():
            require((out / (name + '.lean')).read_bytes() == raw, 'saved R proof source changed')
        verify_packet_bytes((out / 'packet.json').read_bytes(), prepared, expected_sha256=report['packet_sha256'])
        require(snapshot() == before and git('rev-parse', 'HEAD') == source and not git('status', '--porcelain'),
                'source changed during R gate')
        report.update(source_unchanged=True, preparation_checks_passed=True,
                      local_increment_checks_passed=args.require_lean,
                      sparse_tensor_projection_checked=args.require_lean,
                      protected_sparse_decoder_checked=args.require_lean)
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
