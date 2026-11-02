"""Resume the exact Phase17L pre-commit ignored-log failure without editing runtime/proofs.

The pinned original installer is reused, including all tests, formal validators,
checksum checks and guarded normal advancement. Only its staging operation is
adapted: three exact payload logs may be force-added after byte verification.
The original kit and stopped workspace are read-only inputs. Nothing is retried
until it passes. A new separate checkout performs the first operator validation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
BASE = "a87631af18f9b48d1040e6c2a01b511a7675022d"
HELPER_SHA = "3015738acfc39594bb5ccac9a61d543012c5f40a4c457e63592f0ce8ec842a27"
KIT_SUMS_SHA = "1e2d6b374feb5c5459401e28ca612340013a69b79c6ce78459975df18bc8d503"
MANIFEST_SHA = "8352ebeb201e0c1225e63f5443488bf08714c1642f77b63896dc07a48678a129"
ALLOW = {
    "artifacts/development/phase17l/installer-final.out":
        "986d2ee02ee6ee2f5c1b1c0e3567ad8ae87733614a95961f03a4713e1d0817b7",
    "artifacts/development/phase17l/joint-regressions-final.out":
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "artifacts/development/phase17l/runtime-final.out":
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unlinked(path: Path) -> None:
    for part in (path, *path.parents):
        need(not part.is_symlink() and not
             (hasattr(part, 'is_junction') and part.is_junction()),
             'Linked path is not allowed: ' + str(part))


def strict_json(raw: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'Duplicate JSON key: ' + key)
            result[key] = value
        return result
    def bad_constant(value):
        raise ValueError('Nonfinite JSON value: ' + value)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=bad_constant)


def load_original(kit: Path):
    """Authenticate executable helper bytes before importing any of its functions."""
    unlinked(kit)
    helper = kit / 'apply_phase17l.py'
    unlinked(helper)
    need(helper.is_file() and sha(helper.read_bytes()) == HELPER_SHA,
         'Original Phase17L application helper hash differs.')
    spec = importlib.util.spec_from_file_location('_phase17l_pinned_installer', helper)
    need(spec is not None and spec.loader is not None, 'Cannot load pinned helper.')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    need(module.BASE == BASE, 'Original helper targets a different source.')
    sums = module.safe(kit, 'SHA256SUMS.txt').read_bytes()
    need(sha(sums) == KIT_SUMS_SHA, 'Original kit checksum manifest differs.')
    need(sha(module.safe(kit, 'PAYLOAD_MANIFEST.json').read_bytes()) == MANIFEST_SHA,
         'Original payload manifest differs.')
    seen = set()
    for line in sums.decode('utf-8').splitlines():
        m = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        need(m is not None, 'Invalid kit checksum record.')
        digest, name = m.groups()
        module.relative(name)
        need(name not in seen, 'Duplicate kit checksum record.')
        seen.add(name)
        p = module.safe(kit, name)
        need(p.is_file() and sha(p.read_bytes()) == digest, 'Kit bytes differ: ' + name)
    actual = set()
    for p in kit.rglob('*'):
        module.no_links(p)
        if p.is_file():
            actual.add(p.relative_to(kit).as_posix())
    need(actual == seen | {'SHA256SUMS.txt'}, 'Unexpected or missing kit file.')
    payload = module.verify_kit(kit)
    need(len(payload) == 36, 'Expected the exact 36-path Phase17L payload.')
    for name, digest in ALLOW.items():
        need(name in payload and sha(payload[name]) == digest,
             'Allowlisted log is not the original kit payload: ' + name)
    return module, payload


def split_paths(raw: bytes) -> set[str]:
    return {part.decode('utf-8') for part in raw.split(b'\0') if part}


def ignored_paths(a, repo: Path, names) -> set[str]:
    names = sorted({a.relative(n) for n in names})
    if not names:
        return set()
    p = subprocess.run(
        ['git', '-c', 'core.longpaths=true', '--no-optional-locks', '-C', str(repo),
         'check-ignore', '--no-index', '-z', '--stdin'],
        input=b''.join(n.encode('utf-8') + b'\0' for n in names),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    need(p.returncode in (0, 1), 'Cannot inspect ignore rules: ' +
         p.stderr.decode('utf-8', errors='replace'))
    result = split_paths(p.stdout)
    need(result <= set(names), 'Unexpected check-ignore output.')
    need(bool(result) == (p.returncode == 0), 'Inconsistent check-ignore exit.')
    return result


def snapshot_failed(a, payload, failed: Path):
    """Read-only validation of the pre-commit, pre-validation stopped checkout."""
    for path in (failed, failed/'c', failed/'e', failed/'h', failed/'progress.json'):
        a.no_links(path)
    progress_raw = (failed/'progress.json').read_bytes()
    p = strict_json(progress_raw)
    expected = dict(base=a.BASE, stage='stopped', original_checkout_changed=False, pushed=False)
    need(p == expected and p['original_checkout_changed'] is False and p['pushed'] is False,
         'Not the recorded pre-commit Phase17L staging failure; inspect progress.json.')
    c = failed/'c'
    need(Path(a.text(c, 'rev-parse', '--show-toplevel')).resolve() == c,
         'Failed checkout is not its own repository root.')
    need((c/'.git').is_dir(), 'Expected a separate clone, not a shared worktree.')
    a.no_links(c/'.git')
    need(a.text(c, 'rev-parse', 'HEAD') == a.BASE,
         'Failed checkout contains a new commit; this continuation does not apply.')
    need(a.text(c, 'branch', '--show-current') == '', 'Failed checkout is not detached.')
    need((failed/'e').is_dir() and not list((failed/'e').iterdir()),
         'Validation output already exists; do not repeat a later run.')
    need((failed/'h').is_dir() and not list((failed/'h').iterdir()),
         'Failed workspace hooks directory changed.')
    need(not a.git(c, 'ls-files', '--unmerged', '-z'), 'Unmerged index entries.')
    for name, raw in payload.items():
        f = a.safe(c, name)
        need(f.is_file() and f.read_bytes() == raw, 'Failed payload changed: ' + name)
    changed = split_paths(a.git(c, 'diff', 'HEAD', '--name-only', '--no-renames', '-z'))
    ordinary = split_paths(a.git(c, 'ls-files', '--others', '--exclude-standard', '-z'))
    ignored = split_paths(a.git(c, 'ls-files', '--others', '--ignored', '--exclude-standard', '-z'))
    need(changed | ordinary | ignored == set(payload),
         'Unexpected changed, missing, or untracked file in failed checkout.')
    # git add may have staged none or some of the allowed payload before returning
    # an error. Validate either state rather than resetting its index.
    indexed = a.staged(c)
    need(indexed <= set(payload) - set(ALLOW), 'Unexpected staged files in failed checkout.')
    for name in indexed:
        need(a.git(c, 'cat-file', 'blob', ':'+name) == payload[name],
             'Failed staged payload bytes differ: ' + name)
    need(ignored == set(ALLOW) and ignored_paths(a, c, payload) == set(ALLOW),
         'Ignored-file set differs from the three reported logs.')
    index = c/'.git/index'
    a.no_links(index)
    snapshot = {
        'base_commit': a.BASE,
        'base_tree': a.text(c, 'rev-parse', 'HEAD^{tree}'),
        'progress_sha256': sha(progress_raw),
        'index_sha256': sha(index.read_bytes()),
        'staged_paths': sorted(indexed),
        'worktree_diff_sha256': sha(a.git(c, 'diff', 'HEAD', '--binary', '--no-ext-diff', '--no-textconv')),
        'index_listing_sha256': sha(a.git(c, 'ls-files', '--stage', '-z')),
        'ignored_paths': sorted(ignored),
        'payload_sha256': {n: sha(b) for n, b in sorted(payload.items())},
        'source_commit_created': False,
        'operator_tests_or_lean_reached': False,
    }
    return snapshot, progress_raw


def make_stager(a, payload, original_stage, target, events):
    def stage_exact(repo, names):
        repo = Path(repo).resolve()
        need(target.get('checkout') == repo, 'Staging target is not the new isolated checkout.')
        ordered = sorted({a.relative(n) for n in names})
        need(ordered, 'Empty stage set.')
        blocked = ignored_paths(a, repo, ordered)
        need(blocked <= set(ALLOW), 'Unexpected ignored path; no force-add authorized: ' +
             ', '.join(sorted(blocked - set(ALLOW))))
        raw_before = {}
        for name in ordered:
            f = a.safe(repo, name)
            need(f.is_file(), 'Missing stage input: ' + name)
            raw_before[name] = f.read_bytes()
            if name in ALLOW:
                need(name in payload and raw_before[name] == payload[name] and
                     sha(raw_before[name]) == ALLOW[name], 'Bundled log hash differs: ' + name)
        normal = set(ordered) - blocked
        if normal:
            original_stage(repo, normal)
        if blocked:
            a.git(repo, '--literal-pathspecs', 'add', '--force', '--pathspec-from-file=-',
                  '--pathspec-file-nul',
                  data=b''.join(n.encode('utf-8') + b'\0' for n in sorted(blocked)))
            events.append({'paths': sorted(blocked),
                           'sha256': {n: sha(raw_before[n]) for n in sorted(blocked)}})
        for name, raw in raw_before.items():
            need(a.safe(repo, name).read_bytes() == raw and
                 a.git(repo, 'cat-file', 'blob', ':'+name) == raw,
                 'Stage byte conversion or concurrent edit: ' + name)
    return stage_exact


def run_verified(a, payload, repo, tools, work, failed, snapshot, prior_progress, push):
    """Reuse original main unmodified; adapt staging and append failure provenance only."""
    target = {}
    events = []
    original_stage, original_write, original_advance = a.stage_exact, a.write, a.advance
    original_retained = a.retained_files
    continuation_raw = Path(__file__).read_bytes()
    recovery = {
        'schema': 'rcp-rclm.phase17l.ignored-log-staging-recovery.v1',
        'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
        'prior_failed_workspace': str(failed),
        'classification': 'payload_staging_rejected_three_ignored_logs',
        'classification_basis': 'operator transcript plus current exact pre-commit workspace verification',
        'prior_state': snapshot,
        'original_installer_sha256': sha(Path(a.__file__).read_bytes()),
        'continuation_sha256': sha(continuation_raw),
        'force_add_allowlist': dict(ALLOW),
        'runtime_source_changed_by_recovery': False,
        'proofs_or_acceptance_rules_changed_by_recovery': False,
        'gitignore_changed': False,
        'prior_staging_attempt_relabelled_successful': False,
        'prior_operator_tests_reused': 0,
        'validation_required': {'new_tests': 66, 'regression_tests': 139,
                                'named_audits': 43, 'negative_controls': 5},
    }
    def checked_write(path, obj):
        path = Path(path)
        if path.name == 'progress.json' and obj.get('stage') == 'created':
            need(not target, 'Unexpected second validation workspace.')
            need(path.parent.resolve().parent == work, 'Unexpected work directory.')
            target.update(run=path.parent.resolve(), checkout=(path.parent/'c').resolve())
            d = path.parent/'e/prior-staging'
            d.mkdir()
            (d/'progress.json').write_bytes(prior_progress)
            (d/'continuation.py').write_bytes(continuation_raw)
            original_write(d/'recovery.json', recovery)
            print('Verified pre-commit staging failure. Original workspace remains untouched.', flush=True)
        if path.name == 'operator-validation.json' and obj.get('schema') == 'rcp-rclm.phase17l.operator-validation.v1':
            obj = dict(obj)
            obj['staging_recovery'] = {
                'prior_workspace_preserved': True,
                'prior_staging_failed_before_tests': True,
                'runtime_and_proof_payload_unchanged': True,
                'force_add_events': list(events),
                'retained_record': 'prior-staging/recovery.json',
            }
        original_write(path, obj)
    def checked_retained(out):
        current, raw = snapshot_failed(a, payload, failed)
        need(current == snapshot and raw == prior_progress, 'Original stopped workspace changed; evidence not committed.')
        original_write(Path(out)/'prior-staging/preservation-check.json', {
            'original_failed_workspace_unchanged': True, 'snapshot': current})
        return original_retained(out)
    def checked_advance(*args, **kwargs):
        current, raw = snapshot_failed(a, payload, failed)
        need(current == snapshot and raw == prior_progress, 'Original stopped workspace changed; no advancement.')
        need(events and {n for event in events for n in event['paths']} == set(ALLOW),
             'Expected exact three-log staging correction was not recorded.')
        pr = target['run']/'PR_UPDATE.md'
        with pr.open('ab') as out:
            out.write(b'\nStaging recovery: the earlier installation stopped before tests because three\n'
                      b'bundled .out logs were ignored. The original workspace/index remain unchanged.\n'
                      b'Only those three exact hash-verified payload files were force-added. No\n'
                      b'runtime source, Lean proof, acceptance rule, or .gitignore was changed.\n'
                      b'Prior staging progress and the continuation are retained under prior-staging/.\n')
        return original_advance(*args, **kwargs)
    a.stage_exact = make_stager(a, payload, original_stage, target, events)
    a.write = checked_write
    a.advance = checked_advance
    a.retained_files = checked_retained
    try:
        argv = ['--repo', str(repo), '--tools', str(tools), '--work-root', str(work)]
        if push:
            argv.append('--push')
        return a.main(argv)
    finally:
        a.stage_exact, a.write, a.advance = original_stage, original_write, original_advance
        a.retained_files = original_retained
        # Do not turn an earlier error into a success; this check also applies
        # when validation or a network push was rejected.
        current, raw = snapshot_failed(a, payload, failed)
        need(current == snapshot and raw == prior_progress, 'Preserved failed workspace changed unexpectedly.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('repo', 'kit', 'failed-run', 'tools'):
        parser.add_argument('--'+flag, type=Path, required=True)
    parser.add_argument('--work-root', type=Path, default=Path.home()/'.r17')
    parser.add_argument('--push', action='store_true')
    args = parser.parse_args(argv)
    for p in (args.repo, args.kit, args.failed_run, args.tools, args.work_root):
        unlinked(p.absolute())
    repo, kit, failed, tools, work = (p.resolve() for p in
        (args.repo, args.kit, args.failed_run, args.tools, args.work_root))
    need(failed.parent == work and failed.name.startswith('l-'), 'Wrong recorded failure/work-root relationship.')
    for x, y in ((repo, failed), (repo, kit), (tools, failed), (kit, failed), (kit, work)):
        need(x != y and x not in y.parents and y not in x.parents, 'Overlapping input directories.')
    a, payload = load_original(kit)
    snapshot, progress = snapshot_failed(a, payload, failed)
    # Original main independently repeats repository, clean-head, remote, origin,
    # author, tool-workspace, preimage, manifest and validation checks.
    return run_verified(a, payload, repo, tools, work, failed, snapshot, progress, args.push)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        print('Stop. Preserve the reported workspace and progress.json; do not reset or rerun blindly.', file=sys.stderr)
        raise SystemExit(2)
