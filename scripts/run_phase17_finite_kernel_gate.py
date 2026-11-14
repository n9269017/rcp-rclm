"""Phase17Q finite-observation certificate; no worker, promotion, or old campaign."""
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
sys.path[:0] = [str(ROOT / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 3, 4, 5)]
from rcp_rclm_runtime_v5.phase17.finite_kernel import (
    BASE, P_EXECUTION, P_EXECUTION_SHA, RETAINED_PINS, FALSE_CLAIMS, UNMEASURED,
    PreparedFiniteKernel, prepare_finite_kernel, verify_packet_bytes, canonical, require, sha,
)
from rcp_rclm_runtime_v5.phase17.finite_kernel_lean import (
    render, check, NAMES, LABELS, validate_result,
)
from rcp_rclm_runtime_v5.phase17.resource_ledger import _no_links
from rcp_rclm_runtime.canonical.json import load_json_strict

SCHEMA = 'rcp-rclm.phase17q.finite-observation-run.v1'


def git(*args):
    return subprocess.check_output(['git', '--no-optional-locks', '-C', str(ROOT), *args]).decode('utf-8').strip()


def source_paths(root=ROOT):
    names = {p.relative_to(root).as_posix()
             for p in (root / 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17').glob('*.py')}
    names.update(p.relative_to(root).as_posix() for p in (root / 'lean/phase17_bridge').glob('*.lean'))
    names.update(p.relative_to(root).as_posix()
                 for p in (root / 'python/rcp_rclm_runtime_v5/tests_phase17q').glob('test_*.py'))
    names.update(('scripts/run_phase17_finite_kernel_gate.py', 'scripts/run_phase17_finite_kernel_tests.py',
                  'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/lean_root_pins.json'))
    return sorted(names)


def snapshot():
    result = {}
    for name in source_paths():
        path = ROOT / name
        _no_links(path)
        require(path.is_file(), 'missing Q source: ' + name)
        result[name] = sha(path.read_bytes())
    return result


def write(path: Path, value):
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf-8'))


def summary(prepared):
    p = prepared.packet
    return {'packet_sha256': sha(prepared.packet_bytes),
            'protected_packet_sha256': p['protected_packet_sha256'],
            'joint_packet_sha256': p['protected_packet']['joint_packet_sha256'],
            'bindings': p['bindings'], 'staging': p['staging'],
            'resource': p['resource'], 'retained_sha256': p['retained_sha256'],
            'synthetic_fixture': True, 'fixture_is_live_result': False,
            'selected_frontier': [21, 22], 'protected_task_count': 11,
            'teacher_forced_position_count': 28, 'conditional_rows_per_package': 260,
            'production_row_comparisons': 520,
            'full_root_assessment': 'blocked_missing_physical_and_full_semantic_witnesses'}


def verify_only(out: Path) -> int:
    _no_links(out)
    require(out.is_dir(), 'retained Q output missing')
    raw_report = (out / 'execution.json').read_bytes()
    report = load_json_strict(raw_report, require_canonical=False)
    require(type(report) is dict and 'failure' not in report, 'failed or malformed Q execution')
    start_snapshot = snapshot()
    start_head, start_tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    require(report['schema'] == SCHEMA and report['source_sha256'] == snapshot(), 'Q execution source differs')
    require(report['source_commit'] == start_head and report['source_tree'] == start_tree and not git('status', '--porcelain'),
            'reconstruction requires the original clean tested source')
    require(report['preparation_checks_passed'] is True and report['source_unchanged'] is True, 'Q preparation did not pass')
    require(canonical(report['claims']) == canonical({k: False for k in FALSE_CLAIMS}), 'unsupported Q claim')
    require(canonical(report['retained_phase17p']) == canonical({'path': P_EXECUTION, 'sha256': P_EXECUTION_SHA, 'sessions_rerun': False}),
            'P evidence attribution differs')
    require(report['new_named_audits'] == list(NAMES) and report['negative_controls'] == list(LABELS[1:]) and
            report['unmeasured'] == list(UNMEASURED) and report['historical_success_reports_reassigned'] is False and
            type(report['automatic_retries']) is int and report['automatic_retries'] == 0,
            'Q audit or execution scope metadata differs')
    raw = (out / 'packet.json').read_bytes()
    with tempfile.TemporaryDirectory(prefix='r17q-replay-') as tmp:
        recomputed = prepare_finite_kernel(ROOT, Path(tmp) / 'packages')
        verify_packet_bytes(raw, recomputed, expected_sha256=report['packet_sha256'])
        require(all(canonical(report[k]) == canonical(v) for k, v in summary(recomputed).items()), 'Q summary differs from reconstruction')
        sources = {label: render(recomputed, source_root=ROOT, negative=None if label == LABELS[0] else label)
                   for label in LABELS}
    require(report['proof_source_sha256'] == {n: sha(b) for n, b in sources.items()}, 'Q source inventory differs')
    for name, data in sources.items():
        require((out / (name + '.lean')).read_bytes() == data, 'retained generated source differs')
    require(type(report['local_increment_checks_passed']) is bool, 'formal result must be a boolean')
    if report['local_increment_checks_passed'] is True:
        require(report['proof_mode'] == 'real_pinned_lean' and report['preparation_only'] is False and
                report['finite_observation_kernel_checked'] is True, 'formal mode escalation')
        validate_result(report['finite_kernel_gate'], sources, report['packet_sha256'])
    else:
        require(report['proof_mode'] == 'preparation_only' and report['preparation_only'] is True and
                report['finite_observation_kernel_checked'] is False, 'inconsistent preparation mode')
    require(type(report['fresh_worker_sessions']) is int and report['fresh_worker_sessions'] == 0 and
            type(report['fresh_live_challenges']) is int and report['fresh_live_challenges'] == 0 and
            report['old_proof_campaigns_rerun'] is False, 'execution scope differs')
    require(snapshot() == start_snapshot and git('rev-parse', 'HEAD') == start_head and
            git('rev-parse', 'HEAD^{tree}') == start_tree and not git('status', '--porcelain') and
            (out / 'execution.json').read_bytes() == raw_report and (out / 'packet.json').read_bytes() == raw,
            'source or evidence changed during retained verification')
    print('PASS: finite snapshot and retained inputs reconstructed; no workers, fresh challenges, or compiler runs')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--test-fixture', action='store_true')
    ap.add_argument('--require-lean', action='store_true')
    ap.add_argument('--lean-workspace', type=Path)
    ap.add_argument('--toolchain-root', type=Path)
    ap.add_argument('--verify-only', action='store_true')
    args = ap.parse_args(argv)
    out = args.output.absolute()
    _no_links(out)
    out = out.resolve()
    require(out != ROOT and ROOT not in out.parents, 'external Q output required')
    if args.verify_only:
        require(not args.require_lean and args.lean_workspace is None and args.toolchain_root is None,
                'retained verification does not invoke Lean')
        return verify_only(out)
    require(args.test_fixture, 'explicit synthetic-fixture mode required')
    require(args.require_lean == (args.lean_workspace is not None), 'formal mode requires prepared pinned workspace')
    require(args.require_lean or args.toolchain_root is None, 'unused toolchain root')
    require(not out.exists(), 'new Q output required; retain earlier attempts')
    packages = out.with_name(out.name + '-packages')
    _no_links(packages)
    require(not packages.exists(), 'new Q physical workspace required; retain earlier attempts')
    require(not git('status', '--porcelain'), 'clean committed source required')
    source, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', BASE, source], check=True)
    # The reconstruction is additive. No frozen foundation or earlier execution
    # implementation is edited to make the new selected certificate pass.
    require(not git('diff', '--name-only', '--diff-filter=MDRTUXB', BASE, 'HEAD', '--', 'python', 'lean', 'scripts'),
            'preexisting execution or formal source changed')
    before = snapshot()
    out.mkdir(parents=True)
    report = {'schema': SCHEMA, 'source_commit': source, 'source_tree': tree,
              'source_sha256': before, 'os': platform.system(), 'python_version': platform.python_version(),
              'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'preparation_only': not args.require_lean,
              'proof_mode': 'real_pinned_lean' if args.require_lean else 'preparation_only',
              'preparation_checks_passed': False, 'local_increment_checks_passed': False,
              'finite_observation_kernel_checked': False,
              'retained_phase17p': {'path': P_EXECUTION, 'sha256': P_EXECUTION_SHA, 'sessions_rerun': False},
              'fresh_worker_sessions': 0, 'fresh_live_challenges': 0, 'automatic_retries': 0,
              'old_proof_campaigns_rerun': False, 'historical_success_reports_reassigned': False,
              'new_named_audits': list(NAMES), 'negative_controls': list(LABELS[1:]),
              'claims': {k: False for k in FALSE_CLAIMS}, 'unmeasured': list(UNMEASURED)}
    try:
        prepared = prepare_finite_kernel(ROOT, packages)
        (out / 'packet.json').write_bytes(prepared.packet_bytes)
        report.update(summary(prepared))
        sources = {label: render(prepared, source_root=ROOT, negative=None if label == LABELS[0] else label)
                   for label in LABELS}
        for name, data in sources.items():
            (out / (name + '.lean')).write_bytes(data)
        report['proof_source_sha256'] = {n: sha(b) for n, b in sources.items()}
        if args.require_lean:
            formal = check(prepared, source_root=ROOT, lean_workspace=args.lean_workspace,
                           toolchain_root=args.toolchain_root)
            report['finite_kernel_gate'] = formal
            validate_result(formal, sources, report['packet_sha256'])
        else:
            report['finite_kernel_gate'] = {'status': 'not_requested'}
        for name, data in sources.items():
            require((out / (name + '.lean')).read_bytes() == data, 'saved proof source changed')
        verify_packet_bytes((out / 'packet.json').read_bytes(), prepared, expected_sha256=report['packet_sha256'])
        require(snapshot() == before and git('rev-parse', 'HEAD') == source and not git('status', '--porcelain'),
                'source changed during Q gate')
        report.update(source_unchanged=True, preparation_checks_passed=True,
                      local_increment_checks_passed=args.require_lean,
                      finite_observation_kernel_checked=args.require_lean)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        report['failure'] = {'type': type(exc).__name__, 'reason': str(exc)}
    finally:
        report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        write(out / 'execution.json', report)
        files = {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}
        (out / 'SHA256SUMS.txt').write_bytes(''.join(sha(raw) + '  ' + name + '\n'
            for name, raw in sorted(files.items())).encode('ascii'))
        print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report['preparation_checks_passed'] and (not args.require_lean or report['local_increment_checks_passed']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
