"""Source-bound prospective successor check. No activation, promotion or phase closure.

The supplied positive fixture is synthetic and is used only with --test-fixture.
A real transcript requires its independently retained SHA256. The selected old
capability gate and new finite certificate are checked separately with real Lean
when --require-lean is supplied. No tool installation or network setup occurs.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
FIXTURE_HASH = '369c30c469090fa357633aca596cb0c7ad3de31f2ecf16ca78e7699e79c79e6e'


def git(root: Path, *args) -> bytes:
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', '--no-optional-locks', '-C', str(root), *args])


def write(path: Path, obj) -> None:
    path.write_bytes((json.dumps(obj, sort_keys=True, indent=2, allow_nan=False)+'\n').encode())


@contextmanager
def exclusive(workspace: Path):
    # Same cache lock as Phase17E. Never delete a lock belonging to another run.
    for path in (workspace, *workspace.parents):
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise ValueError('linked formal workspace')
    lock = workspace.parent / 'in-use.lock'
    token = (str(os.getpid()) + ' phase17f ' + uuid.uuid4().hex + '\n').encode()
    with lock.open('xb') as handle:
        handle.write(token)
    try:
        yield
    finally:
        if not lock.is_file() or lock.is_symlink() or lock.read_bytes() != token:
            raise ValueError('formal workspace lock changed; it was not removed')
        lock.unlink()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--test-fixture', action='store_true')
    group.add_argument('--transcript', type=Path)
    ap.add_argument('--transcript-sha256')
    ap.add_argument('--require-lean', action='store_true')
    ap.add_argument('--lean-workspace', type=Path)
    ap.add_argument('--toolchain-root', type=Path)
    args = ap.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root/'python'/f'rcp_rclm_runtime_v{v}') for v in (2,3,4,5)]
    from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
    from rcp_rclm_runtime_v5.phase17.materialized import require, sha, materialize_package, verify_package
    from rcp_rclm_runtime_v5.phase17.successor_evidence import prepare_successor, verify_packet_bytes, FALSE_CLAIMS
    from rcp_rclm_runtime_v5.phase17.successor_lean import render, _check_finite_successor, BRIDGE_PATH, NAMES
    from rcp_rclm_runtime_v5.phase17.lean_frontier_gate import recertify_package, root_source_fingerprint
    require(args.test_fixture == (args.transcript is None), 'choose exactly one evidence origin')
    require(args.transcript is None or args.transcript_sha256 is not None, 'independent transcript anchor required')
    require(not args.test_fixture or args.transcript_sha256 is None, 'fixture identity is fixed internally')
    require(args.require_lean == (args.lean_workspace is not None), '--require-lean and existing --lean-workspace required together')
    require(args.require_lean or args.toolchain_root is None, 'no unused toolchain option')
    output = args.output.absolute()
    require(not output.exists() and root not in output.parents, 'new external output required')
    require(all(not p.is_symlink() and not (hasattr(p,'is_junction') and p.is_junction())
                for p in (output.parent, *output.parents)), 'linked output parent')
    output.parent.mkdir(parents=True, exist_ok=True)
    source = git(root,'rev-parse','HEAD').decode().strip()
    tree = git(root,'rev-parse','HEAD^{tree}').decode().strip()
    require(not git(root,'status','--porcelain'), 'clean committed source required')
    path = root/'python/rcp_rclm_runtime_v5/tests_phase17d/fixtures/known_candidate_pass.json' if args.test_fixture else args.transcript
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 2*1024*1024, 'regular bounded transcript required')
    raw = path.read_bytes()
    anchor = FIXTURE_HASH if args.test_fixture else args.transcript_sha256
    require(sha(raw) == anchor, 'transcript identity differs')
    bundle = root/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip'
    capture = root/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip'
    closure = root/'artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip'
    output.mkdir()
    summary = {'schema': 'rcp-rclm.phase17f.prospective-successor-run.v1', 'source_commit': source, 'source_tree': tree,
               'started_at_utc': datetime.now(timezone.utc).isoformat(), 'os': platform.system(),
               'python_version': platform.python_version(), 'synthetic_fixture': args.test_fixture,
               'automatic_retries': 0, 'runtime_promotion_requested': False,
               'local_increment_checks_passed': False, 'claims': {k: False for k in FALSE_CLAIMS}}
    try:
        parent = reopen_phase16(capture_archive=capture, closure_archive=closure, phase15_bundle=bundle)
        before = materialize_package(output/'p',parent,bundle)
        after = materialize_package(output/'c',parent,bundle,transcript=raw,expected_transcript_hash=anchor)
        prepared = prepare_successor(before,after,parent,bundle=bundle,capture=capture,
                                     transcript=raw,expected_transcript_hash=anchor)
        (output/'packet.json').write_bytes(prepared.packet_bytes)
        verify_packet_bytes((output/'packet.json').read_bytes(),prepared,expected_sha256=sha(prepared.packet_bytes))
        template = (root/BRIDGE_PATH).read_bytes()
        (output/'Certificate.lean').write_bytes(render(prepared,template))
        (output/'Negative.lean').write_bytes(render(prepared,template,negative_control=True))
        summary.update(packet_sha256=sha(prepared.packet_bytes),
                       predecessor_package_hash=before.package_hash,candidate_package_hash=after.package_hash,
                       physical_protected_files=173,capability_tasks_evaluated=21,prospective_capability_count=22,
                       inherited_recursive_labels=19,scoped_recursive_probes=3,root_obligation_fields=35,
                       new_lean_audit_names=list(NAMES),dsl_regression_cases_prepared=128,
                       runtime_source_instrumented=False)
        summary['inherited_capability_gate']={'status':'not_requested','fresh_lean_verified':False}
        summary['finite_successor_gate']={'status':'not_requested','finite_successor_facts_verified':False}
        if args.require_lean:
            workspace = args.lean_workspace.resolve(strict=True)
            # No edits to the old root. Check both source roots before using caches.
            a=root_source_fingerprint(root);b=root_source_fingerprint(workspace)
            require({k:v['canonical_sha256'] for k,v in a.items()} == {k:v['canonical_sha256'] for k,v in b.items()},
                    'formal source mismatch')
            with exclusive(workspace):
                finite = _check_finite_successor(prepared,source_root=root,lean_workspace=workspace,
                                                toolchain_root=args.toolchain_root)
                summary['finite_successor_gate']=finite
                require(finite['status']=='passed','finite successor certificate did not pass')
                inherited = recertify_package(after,parent,repository=workspace,bundle=bundle,capture=capture,
                            toolchain_root=args.toolchain_root,transcript=raw,expected_transcript_hash=anchor)
                summary['inherited_capability_gate']=inherited
                require(inherited['status']=='passed','candidate inherited-capability gate did not pass')
        verify_package(before.root,parent,bundle,expected_package_hash=before.package_hash)
        verify_package(after.root,parent,bundle,expected_package_hash=after.package_hash,
                       transcript=raw,expected_transcript_hash=anchor)
        require(git(root,'rev-parse','HEAD').decode().strip()==source and not git(root,'status','--porcelain'),
                'source changed during successor checking')
        require((output/'packet.json').read_bytes()==prepared.packet_bytes and path.read_bytes()==raw,
                'retained packet/transcript changed')
        require((root/BRIDGE_PATH).read_bytes()==template, 'source template changed')
        require((output/'Certificate.lean').read_bytes()==render(prepared,template) and
                (output/'Negative.lean').read_bytes()==render(prepared,template,negative_control=True),
                'retained proof-source bytes changed')
        summary.update(local_increment_checks_passed=True,source_unchanged=True,
                       proof_mode='real_pinned_lean' if args.require_lean else 'preparation_only')
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        summary['failure']={'type':type(exc).__name__,'reason':str(exc)}
    summary['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    write(output/'execution.json',summary)
    retained = [p for p in output.rglob('*') if p.is_file() and p.relative_to(output).parts[0] not in ('p','c')]
    (output/'SHA256SUMS.txt').write_bytes(''.join(sha(p.read_bytes())+'  '+p.relative_to(output).as_posix()+'\n'
                                              for p in sorted(retained)).encode())
    print(json.dumps(summary,indent=2))
    return 0 if summary['local_increment_checks_passed'] else 2


if __name__=='__main__':
    raise SystemExit(main())
