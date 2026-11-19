"""Finish the existing Phase 17C increment after its post-XMP suite passed.

Reuses source-bound prior results, performs ONE new bounded transaction in a
separate clone, preserves prior failures and configuration evidence, and only
then optionally fast-forwards/pushes the existing development branch. No tests
are rerun, no production code is patched, and no phase closure is authorized.
Python 3.13.3 on the same Windows environment is required for this handoff.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
BASE = 'bb1f8669311c099938cc299c2b4fd9f5f77be9e3'
SOURCE = '2d2695674a417cea04947400fa617ac6b34b9d5b'
TREE = 'c0524e7f591044e3fd7329172e907251ae29e940'
BRANCH = 'agent/rcp-rclm-v5-phase-17-controller'
INSTALLER_SHA = 'd75c77726a1b8ff8e6b8bbfe073666de230284bdd8894d3f5322aa2af03aa7c9'
PREFLIGHT_SHA = 'd1df4669b198923e761956af12ff8e93dd92161c1a3ab08a7f66c52ce0295ae0'
SUITE_SHA = '60f79b6ce2c5f368189d7c0319e75b78ebf23f15f30675b5ae70552759d56585'
CONTEXT_SHA = 'e1ae780eea4b7c27a690862c192f67108405734e3fb99686a0790ada3aaf6426'
POST_SHA = '7197d203c8357a88d5b9da97110ae5e96d5e84f5c4cf8efd190edba41e6dfeae'
RECORDER_SHA = 'bc2d33f64bbb0813868c3a9efb4fa5f06cd2083f09b056a9f82c3c07281dd8a5'
STATUS = 'docs/executable_core_v5/PHASE_17_LOCAL_VALIDATION.json'
IMPL = 'docs/executable_core_v5/PHASE_17_IMPLEMENTATION.md'
EVIDENCE_REL = 'artifacts/development/phase17c/operator-2d2695674a41-post-xmp'
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_FILES = 1024
FALSE_CLAIMS = {
    'source_patch_applied': False, 'hardware_root_cause_proven': False,
    'permanent_machine_stability_certified': False,
    'all_tests_executed_after_xmp_change': False,
    'github_hosted_ci_passed': False, 'cross_platform_validation': False,
    'isolated_python_environment': False, 'fresh_lean_verification': False,
    'full_frontier_recertified': False, 'os_security_sandbox': False,
    'phase18_independent_replay': False, 'promotion_performed': False,
    'phase17_exit_closed': False, 'gate_e_closed': False,
    'egc0_started': False, 'main_merge_authorized': False,
}
# These are finite, previously reported observations, not directories selected
# after examining whether their contents are favorable. None is overwritten.
HISTORY = (
    ('isolated-worker-diagnostic', 'worker-diagnostic-20261031T094013Z-97948362', None),
    ('original-instrumented-suite', 'suite-diagnostic-20261031T095536Z-213fbd0f',
     '93b0554fd3169870d3c21ff3e3ca9ea4b7be7a257964154ef86b5bb8449f8760'),
    ('pre-change-bootstrap', 'bootstrap-integrity-20261031T185003Z-cf239cd9',
     '175feaf096b766770e468f3345e3d821ba5169489e133d6e400a97d8b78588e4'),
    ('stdlib-runtime-comparison', 'runtime-comparison-20261031T191028Z-104db8eb',
     'a657c1586c7c36342e6f8b38d8ccc3288fdd5cb5813662bd321e54b6a962e218'),
    ('post-change-bootstrap', 'bootstrap-integrity-20261031T215957Z-3073474f', POST_SHA),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def write_json(path: Path, value: object) -> None:
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2,
                                ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8'))


def read_bytes(path: Path) -> bytes:
    require(path.is_file() and not path.is_symlink(), 'Required regular file missing: ' + str(path))
    require(path.stat().st_size <= MAX_FILE, 'Evidence file exceeds limit: ' + str(path))
    return path.read_bytes()


def load_json(path: Path) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    obj = json.loads(read_bytes(path).decode('utf-8-sig'), object_pairs_hook=pairs)
    require(type(obj) is dict, 'JSON object required: ' + str(path))
    return obj


def relative(name: str) -> str:
    require(type(name) is str and bool(name) and not any(c in name for c in '\\:\x00\r\n'),
            'Unsafe evidence path')
    p = PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts and p.as_posix() == name,
            'Noncanonical evidence path')
    return name


def tree_snapshot(root: Path) -> dict[str, str]:
    require(root.is_dir() and not root.is_symlink(), 'Regular evidence directory required')
    result = {}; total = 0
    for p in sorted(root.rglob('*')):
        require(not p.is_symlink(), 'Evidence symlink forbidden')
        if p.is_dir():
            continue
        require(p.is_file(), 'Nonregular evidence object')
        name = relative(p.relative_to(root).as_posix())
        data = read_bytes(p); total += len(data)
        require(len(result) < MAX_FILES and total <= MAX_TOTAL, 'Evidence collection exceeds bound')
        result[name] = sha(data)
    return result


def manifest_check(root: Path) -> str:
    actual = tree_snapshot(root)
    require('SHA256SUMS.txt' in actual, 'Evidence manifest missing')
    listed = {}
    for line in read_bytes(root / 'SHA256SUMS.txt').decode('utf-8').splitlines():
        digest, name = line.split('  ', 1); relative(name)
        require(name not in listed and name != 'SHA256SUMS.txt' and
                re.fullmatch(r'[0-9a-f]{64}', digest) is not None, 'Invalid manifest entry')
        listed[name] = digest
    require(listed == {n: d for n, d in actual.items() if n != 'SHA256SUMS.txt'},
            'Evidence manifest membership/hash mismatch: ' + str(root))
    return actual['SHA256SUMS.txt']


def copy_preserved(source: Path, target: Path) -> dict[str, str]:
    before = tree_snapshot(source)
    require(not target.exists(), 'Evidence destination already exists')
    shutil.copytree(source, target, symlinks=True)
    require(tree_snapshot(target) == before and tree_snapshot(source) == before,
            'Evidence changed during copy')
    return before


def load_pinned(path: Path, expected: str, name: str):
    require(sha(read_bytes(path)) == expected, 'Helper identity mismatch: ' + path.name)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, 'Could not load pinned helper')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_suite(directory: Path, stage: Path, python: Path, installer) -> dict:
    manifest_check(directory)
    require(sha(read_bytes(directory / 'validation-report.json')) == SUITE_SHA,
            'Post-XMP suite report differs from the supplied result')
    result = load_json(directory / 'validation-report.json')
    require(result.get('schema') == 'rcp-rclm.phase17c.post-xmp-uninstrumented-suite.v1'
            and result.get('source_commit') == SOURCE and result.get('source_tree') == TREE,
            'Post-XMP suite source mismatch')
    for key in ('original_checkout_unchanged', 'test_checkout_unchanged',
                'retained_inputs_unchanged', 'this_uninstrumented_suite_passed'):
        require(result.get(key) is True, 'Post-XMP suite lacks ' + key)
    require(result.get('production_code_instrumented') is False and
            result.get('automatic_retries') == 0 and result.get('postcheck_errors') == [],
            'Unexpected suite instrumentation/retry/state result')
    cmd = result['command']
    require(cmd.get('runner_exit') == 0 and cmd.get('suite_passed') is True and
            cmd.get('observed_test_counts') == [18] and cmd.get('automatic_retries') == 0 and
            cmd.get('worker_timeout_changed') is False and cmd.get('launch_error') is None,
            'Suite did not pass as the original 18-test command')
    require(cmd.get('argv') == [str(python), 'scripts/run_phase17_challenge_tests.py']
            and Path(cmd.get('cwd', '')).resolve() == stage,
            'Suite command or interpreter differs')
    installer.require_test_log(read_bytes(directory / 'suite.stderr.txt'), 18)
    require(result.get('configuration_record_sha256') == CONTEXT_SHA and
            sha(read_bytes(directory / 'xmp-auto-context.json')) == CONTEXT_SHA and
            result.get('post_change_bootstrap_report_sha256') == POST_SHA and
            sha(read_bytes(directory / 'post-change-bootstrap-report.json')) == POST_SHA,
            'Suite configuration/bootstrap evidence differs')
    plan = load_json(directory / 'plan.json')
    require(plan.get('recorder_sha256') == RECORDER_SHA and plan.get('source_commit') == SOURCE,
            'Suite recorder/source identity mismatch')
    context = load_json(directory / 'xmp-auto-context.json')
    require(Path(context.get('python_executable', '')).resolve() == python and
            context.get('persisted_after_reboot_operator_reported') is True and
            context.get('python_version_verified') == '3.13.3', 'Different interpreter/context')
    mem = context.get('memory_firmware_report')
    require(type(mem) is list and len(mem) == 2 and
            all(row.get('ConfiguredClockSpeed') == 4400 for row in mem),
            'Configuration record is not the reported non-XMP configuration')
    require(all(v is False for v in result['claims'].values()), 'Unsupported suite closure claim')
    return result


def check_current_memory(out: Path) -> dict:
    """Read-only CIM inventory. Does not read/write firmware settings."""
    shell = shutil.which('powershell.exe')
    require(shell is not None, 'powershell.exe required for the configuration recheck')
    code = ("$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); "
            "@(Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity,ConfiguredClockSpeed) "
            "| ConvertTo-Json -Depth 4")
    p = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command', code],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    (out / 'memory-inventory.stdout.txt').write_bytes(p.stdout)
    (out / 'memory-inventory.stderr.txt').write_bytes(p.stderr)
    require(p.returncode == 0, 'Could not recheck current memory configuration')
    rows = json.loads(p.stdout.decode('utf-8-sig'))
    require(type(rows) is list and len(rows) == 2 and
            all(row.get('ConfiguredClockSpeed') == 4400 and
                row.get('Capacity') == 34359738368 for row in rows),
            'Memory configuration differs; do not combine evidence across an unrecorded change')
    return {'recorded_at_utc': now(), 'basis': 'Windows CIM firmware report, not a stability attestation',
            'modules': rows, 'settings_changed': False}


def validate_prior(failed: Path, suite_dir: Path, kit: Path, stage: Path, installer) -> dict:
    old = failed / 'evidence'
    foundation = load_json(old / 'foundation/evidence.json')
    require(foundation.get('local_checks_passed') is True and foundation.get('source_unchanged') is True
            and foundation.get('source', {}).get('commit') == SOURCE
            and foundation.get('source', {}).get('tree') == TREE,
            'Prior foundation is not a passing source-bound result')
    installer.require_test_log(read_bytes(old / 'foundation/logs/foundation-tests.stderr.txt'), 110)
    anchor = manifest_check(old / 'foundation')
    capture_stdout = load_json(old / 'command-logs/foundation-capture.stdout.txt')
    require(capture_stdout.get('manifest_sha256') == anchor and
            capture_stdout.get('source_commit') == SOURCE and
            capture_stdout.get('local_checks_passed') is True,
            'Prior foundation external anchor mismatch')
    installer.require_test_log(read_bytes(old / 'command-logs/historical-archives.stderr.txt'), 10)
    fail = load_json(old / 'FAILED_COMMAND.json')
    require(fail.get('name') == 'process-and-differential' and fail.get('returncode') == 1 and
            fail.get('stderr_sha256') == sha(read_bytes(old / 'command-logs/process-and-differential.stderr.txt')),
            'Original failed command is not preserved')
    prior_suite = validate_suite(suite_dir, stage, Path(sys.executable).resolve(), installer)
    histories = []
    for label, folder, expected in HISTORY:
        source = kit / 'runs' / folder
        manifest_sha = manifest_check(source)
        report_sha = sha(read_bytes(source / 'diagnostic-report.json'))
        if expected is not None:
            require(report_sha == expected, 'Prior diagnostic report changed: ' + label)
        histories.append({'label': label, 'path': source, 'report_sha256': report_sha,
                          'manifest_sha256': manifest_sha,
                          'externally_pinned_report': expected is not None})
    return {'foundation': foundation, 'foundation_anchor': anchor,
            'suite': prior_suite, 'histories': histories}


def tx_check(directory: Path) -> tuple[dict, str]:
    anchor = manifest_check(directory)
    tx = load_json(directory / 'transaction.json')
    require(tx.get('schema_id') == 'runtime.v5.phase17.bounded_transaction.v1'
            and tx.get('local_transaction_verified') is True and
            tx.get('separate_process') is True and tx.get('worker_exited_cleanly') is True,
            'Fresh transaction did not verify')
    require(tx.get('candidate_credits') == 32 and type(tx.get('candidate_evaluations')) is int
            and 1 <= tx['candidate_evaluations'] <= 32, 'Unexpected transaction budget/count')
    require(tx.get('terminal_action') in ('search_exhausted', 'await_root_verification'),
            'Fresh transaction did not reach a permitted full-budget terminal')
    if tx['terminal_action'] == 'search_exhausted':
        require(tx['candidate_evaluations'] == 32 and (directory / 'bounded_exhaustion.json').is_file(),
                'Incomplete search presented as exhaustion')
    require(type(tx.get('claims')) is dict and bool(tx['claims']) and
            all(v is False for v in tx['claims'].values()) and
            tx.get('complete_resource_accounting') is False,
            'Unsupported promotion/closure claim')
    require(tx.get('transcript_sha256') == sha(read_bytes(directory / 'sealed_transcript.json')),
            'Sealed transcript hash mismatch')
    source = load_json(directory / 'source.json')
    require(source.get('source_commit') == SOURCE, 'Transaction source identity mismatch')
    return tx, anchor


def build_evidence_commit(stage: Path, evidence: Path, result: dict, hooks: Path, installer) -> str:
    target = stage / EVIDENCE_REL
    require(not target.exists(), 'Evidence target already exists')
    copy_preserved(evidence, target)
    (target / '.gitattributes').write_bytes(b'** -text\n')
    snapshot = tree_snapshot(target)
    (target / 'SHA256SUMS.txt').write_bytes(''.join(
        f'{digest}  {name}\n' for name, digest in sorted(snapshot.items())).encode('utf-8'))
    manifest_check(target)
    entries = {p.relative_to(stage).as_posix(): p.read_bytes()
               for p in target.rglob('*') if p.is_file()}
    # Only the explicitly enumerated retained evidence paths can override ignore rules.
    installer.checked(stage, 'add', '-f', '--', *sorted(entries))
    installer.tracked_equal(stage, entries)
    status = load_json(stage / STATUS)
    for key in ('phase17_exit_closed', 'gate_e_closed', 'egc0_started', 'main_merge_authorized'):
        require(status.get(key) is False, 'Unexpected authoritative closure flag')
    status['evidence_records']['phase17c_operator_capture'] = EVIDENCE_REL + '/operator-validation.json'
    v = status['validation']
    v['phase17c_operator_validation'] = 'passed_local_multirun_evidence_not_phase_closure'
    v['phase17c_operator_platform'] = 'Windows 11 / CPython 3.13.3'
    v['phase17c_tested_code_commit'] = SOURCE
    v['phase17c_foundation_and_archives'] = 'reused_pre_configuration_change_passes; 110 and 10; not rerun'
    v['phase17c_process_differential'] = '18 passed uninstrumented after XMP Auto; zero skips; zero automatic retries'
    v['phase17c_single_turn'] = result['single_transaction_terminal']
    v['phase17c_hardware_root_cause_proven'] = False
    v['phase17c_prior_failures_preserved'] = True
    v['phase17c_configuration_comparison'] = 'XMP Profile 1/6000 before; operator Auto/firmware 4400 after; contributing factor supported, not proven'
    write_json(stage / STATUS, status)
    with (stage / IMPL).open('a', encoding='utf-8', newline='\n') as handle:
        handle.write('\n## Phase 17C local validation after memory-profile change\n\n'
            f'Tested implementation: `{SOURCE}`. Evidence: `{EVIDENCE_REL}/operator-validation.json`. '
            'This is a multi-run Windows record: the earlier 110 foundation and 10 archive passes '
            'are retained without relabeling them as post-change runs; the original failed process '
            'suite and intervening diagnostics remain preserved. After the operator changed XMP '
            'Profile 1 to Auto, firmware reported 4400 and the unchanged ordinary 18-test suite passed. '
            'One additional fresh bounded transaction was then executed and verified. No favorable '
            'terminal outcome was required, and no live challenge was retried. This supports a '
            'configuration contribution but does not prove a hardware root cause or permanent stability. '
            'No runtime source patch, full-frontier/Lean recertification, successor promotion, '
            'Phase 18 replay, phase closure, or EGC result is claimed.\n')
    installer.checked(stage, 'add', '--', STATUS, IMPL)
    installer.refresh(stage)
    require(installer.staged_paths(stage) == set(entries) | {STATUS, IMPL, 'SHA256SUMS.txt'},
            'Unexpected evidence-only staged paths')
    head = installer.commit(stage, 'Retain Phase 17C post-XMP local evidence and fresh transaction [skip ci]', hooks)
    require(installer.git_text(stage, 'rev-parse', head + '^') == SOURCE,
            'Evidence commit does not follow the tested source')
    return head


def require_unmoved(repo: Path, before: dict, installer, helper) -> None:
    require(helper.snapshot(repo) == before, 'Original checkout moved; no automatic reset permitted')
    require(installer.git_text(repo, 'remote', 'get-url', 'origin') in installer.ORIGINS and
            installer.git_text(repo, 'remote', 'get-url', '--push', 'origin') in installer.ORIGINS,
            'Unexpected fetch/push destination')
    require(installer.remote_head(repo) == BASE, 'Remote branch moved; no overwrite permitted')


def advance(repo: Path, stage: Path, head: str, hooks: Path, before: dict,
            installer, helper, push: bool, out: Path) -> None:
    require_unmoved(repo, before, installer, helper)
    added = installer.git(stage, 'diff', '--diff-filter=A', '--name-only', '-z', BASE, head)
    for name in (x.decode('utf-8') for x in added.split(b'\0') if x):
        dest = installer.safe_file(repo, name)
        require(not dest.exists(), 'Local ignored/untracked path would be overwritten: ' + name)
    installer.checked(repo, 'fetch', '--no-tags', str(stage), head)
    # Fetch is allowed to add objects/FETCH_HEAD but must not change working source.
    require_unmoved(repo, before, installer, helper)
    installer.checked(repo, '-c', 'core.hooksPath=' + str(hooks), 'merge', '--ff-only', head)
    installer.clean(repo)
    require(installer.git_text(repo, 'rev-parse', 'HEAD') == head, 'Local advancement mismatch')
    write_json(out / 'advancement.json', {'local_head': head, 'local_advanced': True, 'pushed': False})
    if push:
        require(installer.remote_head(repo) == BASE, 'Remote moved after local advancement; do not force-push')
        subprocess.run(['git', '-C', str(repo), 'push', 'origin', f'{head}:refs/heads/{BRANCH}'], check=True)
        require(installer.remote_head(repo) == head, 'Could not confirm remote post-push identity')
        write_json(out / 'advancement.json', {'local_head': head, 'local_advanced': True, 'pushed': True})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'kit', 'failed-run', 'suite-result', 'preflight-helper'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--push', action='store_true')
    args = parser.parse_args(argv)
    require(platform.system() == 'Windows' and sys.version_info[:3] == (3, 13, 3),
            'Use the same Windows CPython 3.13.3 interpreter')
    repo, kit, failed, suite_dir = (x.resolve() for x in
                                  (args.repo, args.kit, args.failed_run, args.suite_result))
    installer_path = kit / 'apply_phase17c.py'
    installer = load_pinned(installer_path, INSTALLER_SHA, '_phase17c_original_installer')
    helper_path = args.preflight_helper.resolve()
    helper = load_pinned(helper_path, PREFLIGHT_SHA, '_phase17c_readonly_preflight')
    oldstage, before_repo, before_stage = helper.preflight(repo, kit, failed)
    require(before_stage['head'] == SOURCE and before_stage['tree'] == TREE,
            'Existing test checkout no longer has the reviewed source')
    helper.source_pins(oldstage)
    require(suite_dir.parent == kit / 'runs', 'Suite result must be the retained run under this kit')
    require_unmoved(repo, before_repo, installer, helper)
    saved = validate_prior(failed, suite_dir, kit, oldstage, installer)
    prior = [('original-installation-evidence', failed / 'evidence'), ('post-xmp-suite', suite_dir)]
    prior += [(row['label'], row['path']) for row in saved['histories']]
    before_inputs = {label: tree_snapshot(path) for label, path in prior}
    original_progress = read_bytes(failed / 'progress.json')
    out = kit / 'runs' / ('finalize-post-xmp-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                        + '-' + uuid.uuid4().hex[:8])
    require(not any((p / '.git').exists() for p in (out.parent, *out.parent.parents)),
            'Finalization workspace must be outside any source checkout')
    out.mkdir(exist_ok=False); evidence = out / 'evidence'; evidence.mkdir()
    print('Finalization workspace: ' + str(out), flush=True)
    print('Reusing the retained 110/10 and post-XMP 18-test results; no test suite rerun.', flush=True)
    try:
        current_memory = check_current_memory(out)
        for label, path in prior:
            copy_preserved(path, evidence / label)
        (evidence / 'original-installation-progress.json').write_bytes(original_progress)
        (evidence / 'finalization-recorder.py').write_bytes(Path(__file__).read_bytes())
        (evidence / 'original-application-helper.py').write_bytes(read_bytes(installer_path))
        (evidence / 'readonly-preflight-helper.py').write_bytes(read_bytes(helper_path))
        write_json(evidence / 'current-memory-configuration.json', current_memory)
        stage = out / 'checkout'; hooks = out / 'empty-hooks'; hooks.mkdir()
        subprocess.run(['git', 'clone', '--no-hardlinks', '--no-checkout', str(oldstage), str(stage)],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        installer.checked(stage, 'config', 'core.autocrlf', 'false')
        for key in ('user.name', 'user.email'):
            value = installer.git_text(repo, 'config', key)
            require(bool(value), 'Missing Git author identity')
            installer.checked(stage, 'config', key, value)
        installer.checked(stage, '-c', 'core.hooksPath=' + str(hooks), 'checkout', '--detach', SOURCE)
        require(installer.git_text(stage, 'rev-parse', 'HEAD^{tree}') == TREE, 'Cloned tree mismatch')
        installer.clean(stage)
        commands = []
        commands.append(installer.command(stage, evidence, 'verify-retained-foundation', [
            sys.executable, 'scripts/phase17_local_evidence.py', 'verify',
            '--bundle', str(evidence / 'original-installation-evidence/foundation'),
            '--expected-head', SOURCE, '--expected-manifest-sha256', saved['foundation_anchor']]))
        print('Running the ONE outstanding fresh bounded transaction; no retries or winner filtering.', flush=True)
        commands.append(installer.command(stage, evidence, 'single-fresh-transaction', [
            sys.executable, 'scripts/run_phase17_challenge_transaction.py',
            '--output', str(evidence / 'transaction'), '--candidate-credits', '32']))
        tx, tx_anchor = tx_check(evidence / 'transaction')
        installer.clean(stage)
        require(installer.git_text(stage, 'rev-parse', 'HEAD') == SOURCE, 'Source moved during transaction')
        # Every original evidence byte remains at its original location as well.
        for label, path in prior:
            require(tree_snapshot(path) == before_inputs[label], 'Prior evidence changed: ' + label)
        require(read_bytes(failed / 'progress.json') == original_progress, 'Original progress changed')
        require(helper.snapshot(oldstage) == before_stage, 'Original failed checkout changed')
        require(helper.snapshot(repo) == before_repo, 'Original working checkout changed')
        require(sha(read_bytes(installer_path)) == INSTALLER_SHA and sha(read_bytes(helper_path)) == PREFLIGHT_SHA,
                'Helper identity changed during finalization')
        result = {
            'schema': 'rcp-rclm.phase17c.operator-multirun-validation.v1',
            'tested_code_commit': SOURCE, 'tested_code_tree': TREE, 'previous_base': BASE,
            'recorded_at_utc': now(), 'increment_local_validation_complete': True,
            'validation_basis': 'retained source-identical passes across two memory configurations plus one new transaction',
            'environment': {'os': platform.system(), 'os_release': platform.release(),
                            'python_version': platform.python_version(), 'machine': platform.machine()},
            'foundation_tests': 110, 'historical_archive_tests': 10,
            'foundation_and_archives_reexecuted': False,
            'foundation_and_archives_configuration': 'before operator memory-profile change; historical successful results',
            'process_and_differential_tests': 18, 'post_xmp_suite_reexecuted': False,
            'post_xmp_suite_report_sha256': SUITE_SHA, 'post_change_bootstrap_report_sha256': POST_SHA,
            'configuration_record_sha256': CONTEXT_SHA,
            'foundation_manifest_sha256': saved['foundation_anchor'],
            'transaction_manifest_sha256': tx_anchor,
            'single_transaction_terminal': tx['terminal_action'],
            'single_transaction_evaluations': tx['candidate_evaluations'],
            'fresh_transactions_executed_by_finalizer': 1, 'automatic_retries': 0,
            'original_failed_runs_preserved': True, 'all_history_reclassified_as_success': False,
            'new_commands': commands, 'prior_diagnostic_anchors': [
                {k: v for k, v in row.items() if k != 'path'} for row in saved['histories']],
            'claims': dict(FALSE_CLAIMS),
        }
        write_json(evidence / 'operator-validation.json', result)
        (evidence / 'README.md').write_text(
            '# Phase 17C multi-run local validation\n\n'
            'All original failures and diagnostics are preserved as historical evidence, not converted to passes. '
            'The foundation/archive passes occurred before the memory-profile change; the ordinary 18-test '
            'suite and this one fresh transaction occurred afterward. No production source repair was applied. '
            'This local development aggregate is not phase closure, machine-stability certification, or proof '
            'of a hardware cause. Detailed metadata/logs may include operator paths and package inventories.\n',
            encoding='utf-8', newline='\n')
        evidence_head = build_evidence_commit(stage, evidence, result, hooks, installer)
        pr = (f'## Phase 17A-C local-first development\n\nKeep PR #68 draft and unmerged.\n\n'
              f'Tested Phase 17C source: `{SOURCE}`. Evidence head: `{evidence_head}`.\n\n'
              'Phase 17C adds evaluator-owned post-freeze challenges, a separate bounded data-only worker, '
              'bounded DSL artifact freezing/reference evaluation, one-turn integration, and sealed transcript checking. '
              'It does not add full-model evaluation, full-frontier/Lean recertification, promotion, or cross-turn autonomy.\n\n'
              'Retained local results: 110 foundation and 10 archive tests passed before the memory-profile change; '
              '18 ordinary uninstrumented subprocess/differential tests passed afterward. No suite was rerun by '
              'the finalizer. Earlier failures and all selected diagnostics remain retained. The operator changed '
              'XMP Profile 1 to Auto; Windows subsequently reported 4400. A configuration contribution is supported, '
              'not a conclusively proven hardware cause.\n\n'
              f'One fresh bounded transaction: `{tx["terminal_action"]}`, {tx["candidate_evaluations"]} candidate '
              'evaluations; worker exited cleanly, sealed transcript verified; no retry/winner filtering.\n\n'
              f'Evidence: `{EVIDENCE_REL}/operator-validation.json`.\n\n'
              'Remaining: full model realization/evaluation, frontier and pinned root/Lean recertification, '
              'atomic promotion/rollback, durable cross-turn state/resource accounting, evolving objectives, '
              'autonomous campaigns, and independent/cross-platform replay. EGC-0 is unstarted.\n\n'
              '`phase17_exit_closed=false`, `gate_e_closed=false`, `egc0_started=false`, '
              '`promotion_performed=false`, `github_hosted_ci_passed=false`. No main merge or release/DOI change.\n')
        (out / 'PR_UPDATE.md').write_text(pr, encoding='utf-8', newline='\n')
        write_json(out / 'progress.json', {'validation_complete': True, 'evidence_head': evidence_head,
                    'source_commit': SOURCE, 'original_checkout_advanced': False, 'pushed': False})
        advance(repo, stage, evidence_head, hooks, before_repo, installer, helper, args.push, out)
        summary = {'completed': True, 'tested_code_head': SOURCE, 'evidence_head': evidence_head,
                   'pushed': bool(args.push), 'foundation_tests_retained_not_rerun': 110,
                   'archive_tests_retained_not_rerun': 10, 'post_xmp_process_tests_retained_not_rerun': 18,
                   'single_fresh_transaction_terminal': tx['terminal_action'],
                   'single_fresh_transaction_evaluations': tx['candidate_evaluations'],
                   'historical_failures_preserved': True, 'runtime_source_changed_by_finalizer': False,
                   'evidence_directory': str(evidence), 'pr_description_file': str(out / 'PR_UPDATE.md'),
                   'phase17_exit_closed': False, 'gate_e_closed': False, 'egc0_started': False,
                   'pr68_keep_draft': True}
        write_json(out / 'progress.json', summary)
        print(json.dumps(summary, indent=2)); return 0
    except Exception as exc:
        message = str(exc)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            message += '\n' + exc.stderr.decode('utf-8', errors='replace')[-4000:]
        write_json(out / 'FINALIZATION_STOP.json', {'error_type': type(exc).__name__, 'message': message,
                   'phase17_exit_closed': False, 'gate_e_closed': False, 'egc0_started': False})
        print('STOP: ' + message, file=sys.stderr)
        print('Preserve this workspace: ' + str(out), file=sys.stderr)
        print('No reset, force-push, or main merge performed. Inspect progress/advancement before retrying.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print('STOP before finalization: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
