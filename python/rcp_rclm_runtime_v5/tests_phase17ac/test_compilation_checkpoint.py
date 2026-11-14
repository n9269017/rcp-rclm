"""Real tiny subprocess/storage checks; these fixtures are not Lean evidence."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import compilation_checkpoint as checkpoint


FIXTURE = b'''from pathlib import Path
import sys,time
# These are synthetic protocol bytes. Keep them identical on Windows, where
# ordinary text stdout/stderr otherwise translate LF to CRLF.
sys.stdout.reconfigure(encoding="utf-8", newline="\\n")
sys.stderr.reconfigure(encoding="utf-8", newline="\\n")
action=sys.argv[1]
work=Path(sys.argv[2])
if action=="one":
    (work/"One.olean").write_bytes(b"compiled-one:"+(work/"Source.lean").read_bytes())
elif action=="two":
    assert (work/"One.olean").read_bytes()==b"compiled-one:fixed source\\n"
    (work/"Two.olean").write_bytes(b"compiled-two")
elif action=="negative":
    print("intended False")
    sys.exit(1)
elif action=="failure":
    print("unrelated failure",file=sys.stderr)
    sys.exit(2)
elif action=="timeout":
    time.sleep(10)
elif action=="extra":
    (work/"undeclared.olean").write_bytes(b"unexpected")
elif action=="mutate":
    Path(sys.argv[3]).write_bytes(b"changed external input")
print(action)
'''


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate(stage, record):
    expected = 'intended False\n' if stage.label == 'negative' else stage.label + '\n'
    code = 1 if stage.label == 'negative' else 0
    checkpoint._need(record['returncode'] == code and record['stdout'] == expected and
                     record['stderr'] == '' and record['native_wait_completed'] is True and
                     record['timed_out'] is False, 'intended fixture result missing')
    return {'scope': 'synthetic subprocess fixture only', 'label': stage.label,
            'intended_negative': stage.label == 'negative'}


class BoundedFileReadTests(unittest.TestCase):
    """Portable byte/metadata regressions; injected observations are explicit."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name).resolve() / 'binary-input'
        self.raw = b'\x00\xffbefore\r\nafter\x1aend\r\n\x80'
        self.path.write_bytes(self.raw)

    @staticmethod
    def changed(result, **changes):
        fields = {name: getattr(result, name) for name in dir(result)
                  if name.startswith('st_')}
        fields.update(changes)
        return SimpleNamespace(**fields)

    def test_binary_capture_preserves_crlf_ctrl_z_and_arbitrary_bytes(self):
        self.assertEqual(checkpoint._read(self.path, len(self.raw)), self.raw)
        # On Windows this opens in CRT text mode first. FileIO's 'rb' wrapper
        # must still suppress CRLF/Ctrl-Z translation; missing O_BINARY alone
        # is therefore not evidence that the former implementation translated.
        flags = os.O_RDONLY | getattr(os, 'O_TEXT', 0)
        with os.fdopen(os.open(self.path, flags), 'rb') as stream:
            self.assertEqual(stream.read(), self.raw)

    def test_low_level_opens_request_binary_mode_when_available(self):
        real_open = os.open
        binary_flag = getattr(os, 'O_BINARY', 1 << 29)
        native_has_binary = hasattr(os, 'O_BINARY')
        observed = []

        def capture(path, flags, *args, **kwargs):
            observed.append(flags)
            if not native_has_binary:
                flags &= ~binary_flag
            return real_open(path, flags, *args, **kwargs)

        # Linux has no O_BINARY. Supply only the flag constant and strip it
        # before the native open, so the portable branch is exercised there.
        with patch.object(os, 'O_BINARY', binary_flag, create=True), \
                patch.object(os, 'open', capture):
            self.assertEqual(checkpoint._read(self.path), self.raw)
        self.assertTrue(observed)
        self.assertTrue(all(flags & binary_flag for flags in observed))

    def test_path_and_descriptor_ctime_can_differ_for_an_unchanged_file(self):
        real_stat = Path.stat

        def path_stat(path, *args, **kwargs):
            result = real_stat(path, *args, **kwargs)
            if path == self.path:
                # Model Windows creation-time stat versus change-time fstat.
                return self.changed(result, st_ctime_ns=result.st_ctime_ns - 1_000_000_000)
            return result

        with patch.object(Path, 'stat', path_stat):
            self.assertEqual(checkpoint._read(self.path), self.raw)

    def test_descriptor_ctime_only_mutation_is_rejected(self):
        real_fstat = os.fstat
        calls = 0

        def fstat(fd):
            nonlocal calls
            calls += 1
            result = real_fstat(fd)
            if calls > 1:
                return self.changed(result, st_ctime_ns=result.st_ctime_ns + 1)
            return result

        with patch.object(os, 'fstat', fstat), self.assertRaisesRegex(
                checkpoint.CheckpointError, 'descriptor metadata st_ctime_ns'):
            checkpoint._read(self.path)

    def test_each_descriptor_identity_and_content_field_remains_checked(self):
        real_fstat = os.fstat
        for field in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns'):
            calls = 0

            def fstat(fd):
                nonlocal calls
                calls += 1
                result = real_fstat(fd)
                if calls == 2:
                    return self.changed(result, **{field: getattr(result, field) + 1})
                return result

            with self.subTest(field=field), patch.object(os, 'fstat', fstat), \
                    self.assertRaisesRegex(checkpoint.CheckpointError, 'descriptor metadata ' + field):
                checkpoint._read(self.path)

    def test_actual_size_change_during_capture_is_rejected(self):
        real_fstat = os.fstat
        calls = 0

        def fstat(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.path.write_bytes(self.raw + b'more')
            return real_fstat(fd)

        with patch.object(os, 'fstat', fstat), self.assertRaisesRegex(
                checkpoint.CheckpointError, 'descriptor metadata .*st_size'):
            checkpoint._read(self.path)

    def test_actual_same_size_content_change_during_capture_is_rejected(self):
        real_fstat = os.fstat
        initial = self.path.stat()
        calls = 0

        def fstat(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.path.write_bytes(b'x' * len(self.raw))
                # Force a visible timestamp even on a coarse-resolution FS.
                os.utime(self.path, ns=(initial.st_atime_ns, initial.st_mtime_ns + 2_000_000_000))
            return real_fstat(fd)

        with patch.object(os, 'fstat', fstat), self.assertRaisesRegex(
                checkpoint.CheckpointError, 'descriptor metadata .*st_mtime_ns'):
            checkpoint._read(self.path)

    def test_reopened_path_cannot_substitute_another_file_with_identical_bytes(self):
        replacement = self.path.with_name('replacement')
        replacement.write_bytes(self.raw)
        initial = self.path.stat()
        os.utime(replacement, ns=(initial.st_atime_ns, initial.st_mtime_ns))
        real_open = os.open
        calls = 0

        def reopen(path, flags, *args, **kwargs):
            nonlocal calls
            calls += 1
            # Explicitly model replacement at the second open. This exercises
            # identity verification even on Windows denying rename-open files.
            return real_open(replacement if calls == 2 else path, flags, *args, **kwargs)

        with patch.object(os, 'open', reopen), self.assertRaisesRegex(
                checkpoint.CheckpointError, 'descriptor metadata .*st_ino'):
            checkpoint._read(self.path)

    def test_final_path_identity_is_checked_after_both_descriptors(self):
        real_fstat, real_stat = os.fstat, Path.stat
        calls = 0

        def fstat(fd):
            nonlocal calls
            calls += 1
            return real_fstat(fd)

        def path_stat(path, *args, **kwargs):
            result = real_stat(path, *args, **kwargs)
            if path == self.path and calls >= 3:
                return self.changed(result, st_ino=result.st_ino + 1)
            return result

        with patch.object(os, 'fstat', fstat), patch.object(Path, 'stat', path_stat), \
                self.assertRaisesRegex(checkpoint.CheckpointError, 'path metadata st_ino'):
            checkpoint._read(self.path)

    def test_final_path_link_observation_is_rejected(self):
        real_fstat, real_is_symlink = os.fstat, Path.is_symlink
        calls = 0

        def fstat(fd):
            nonlocal calls
            calls += 1
            return real_fstat(fd)

        def is_symlink(path):
            return (path == self.path and calls >= 3) or real_is_symlink(path)

        with patch.object(os, 'fstat', fstat), patch.object(Path, 'is_symlink', is_symlink), \
                self.assertRaisesRegex(checkpoint.CheckpointError, 'linked or junction'):
            checkpoint._read(self.path)

    def test_nonregular_and_oversized_inputs_remain_rejected(self):
        with self.assertRaisesRegex(checkpoint.CheckpointError, 'nonregular or oversized'):
            checkpoint._read(self.path, len(self.raw) - 1)
        real_fstat = os.fstat
        with patch.object(os, 'fstat', lambda fd: self.changed(real_fstat(fd), st_mode=stat.S_IFIFO)), \
                self.assertRaisesRegex(checkpoint.CheckpointError, 'nonregular or oversized'):
            checkpoint._read(self.path)


class CompilationCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'run'
        self.binding = self.base / 'trusted-input'
        self.binding.write_bytes(b'fixed trusted fixture input')
        self.python = str(Path(sys.executable).resolve())
        environment = {k: v for k, v in os.environ.items()
                       if k.upper() in {'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'TEMP', 'TMP', 'PATH'}}
        environment['CHECKPOINT_WORKSPACE'] = '{workspace}'
        self.config = {
            'plan_context': {'test_fixture': True, 'platform': os.name,
                             'not_lean_or_application_evidence': True},
            'stages': (self.stage('one', ('One.olean',)), self.stage('two', ('Two.olean',)),
                       self.stage('positive'), self.stage('negative')),
            'input_files': {'trusted_fixture': self.binding, 'python': Path(self.python)},
            'expected_input_sha256': {'trusted_fixture': sha(self.binding.read_bytes()),
                                      'python': sha(Path(self.python).read_bytes())},
            'workspace_files': {'fixture.py': FIXTURE, 'Source.lean': b'fixed source\n'},
            'environment': environment, 'cwd': self.base, 'validate_result': validate,
            'max_completed_seconds': 60,
        }

    def stage(self, label, artifacts=(), *, timeout=5, args=()):
        return checkpoint.Stage(label, (self.python, '-I', '-S', '-B',
                                        '{workspace}/fixture.py', label, '{workspace}', *args),
                                timeout, artifacts)

    def advance(self, parent=None, *, config=None, restore=None, refs=()):
        options = dict(config or self.config)
        if parent:
            options.update(parent_manifest=Path(parent['manifest_path']),
                           expected_parent_sha256=parent['manifest_sha256'],
                           restore_validator=restore or self.restore)
        return checkpoint.run_stage(self.root, unresolved_invocations=refs, **options)

    @staticmethod
    def restore(workspace, artifacts):
        for name, item in artifacts.items():
            checkpoint._need(sha((workspace / name).read_bytes()) == item['sha256'],
                             'synthetic restored import differs')
        return {'scope': 'synthetic import check only', 'artifacts': sorted(artifacts)}

    def verify(self, result, **overrides):
        config = dict(self.config, **overrides)
        return checkpoint.verify_manifest(Path(result['manifest_path']), result['manifest_sha256'], **config)

    def rewrite(self, result, change):
        path = Path(result['manifest_path'])
        record = json.loads(path.read_bytes())
        change(record)
        raw = checkpoint._canonical(record)
        path.write_bytes(raw)
        return dict(result, manifest_sha256=sha(raw), manifest=record)

    def test_complete_lineage_retains_sources_logs_and_original_producers(self):
        first = self.advance()
        second = self.advance(first)
        third = self.advance(second)
        final = self.advance(third)
        self.assertTrue(final['all_stages_completed'])
        record = self.verify(final)
        self.assertEqual(len(record['steps']), 4)
        self.assertEqual(record['steps'][0]['producer_invocation'], first['manifest']['invocation_id'])
        self.assertEqual(record['artifacts']['One.olean']['producer_invocation'], first['manifest']['invocation_id'])
        self.assertEqual(record['steps'][-1]['command']['returncode'], 1)
        self.assertFalse(record['complete_resource_accounting'])
        self.assertGreater(record['completed_lineage_active_ns'], 0)
        self.assertEqual(record['completed_lineage_active_ns'], sum(s['active_elapsed_ns'] for s in record['steps']))

    def test_manifest_hash_is_external_and_required_before_launch(self):
        first = self.advance()
        with patch.object(checkpoint.subprocess, 'Popen') as launch:
            with self.assertRaises(checkpoint.CheckpointError):
                self.advance(dict(first, manifest_sha256='f' * 64))
            launch.assert_not_called()

    def test_changed_source_or_stage_plan_cannot_reuse_parent(self):
        first = self.advance()
        for config in (dict(self.config, workspace_files={'fixture.py': FIXTURE, 'Source.lean': b'changed'}),
                       dict(self.config, stages=(self.stage('one', ('One.olean',), timeout=4), *self.config['stages'][1:]))):
            with self.subTest(config=config.keys()), self.assertRaises(checkpoint.CheckpointError):
                self.advance(first, config=config)

    def test_current_external_input_must_match_pin(self):
        first = self.advance()
        self.binding.write_bytes(b'changed input')
        with self.assertRaises(checkpoint.CheckpointError):
            self.verify(first)

    def test_source_and_artifact_bytes_are_reopened(self):
        first = self.advance()
        workspace = Path(first['manifest_path']).parent / 'workspace'
        for name in ('Source.lean', 'One.olean'):
            original = (workspace / name).read_bytes()
            (workspace / name).write_bytes(b'corrupted')
            with self.subTest(name=name), self.assertRaises(checkpoint.CheckpointError):
                self.verify(first)
            (workspace / name).write_bytes(original)
        self.verify(first)

    def test_saved_raw_log_tamper_is_rejected(self):
        first = self.advance()
        (Path(first['manifest_path']).parent / 'logs/000.stdout.bin').write_bytes(b'invented pass\n')
        with self.assertRaises(checkpoint.CheckpointError):
            self.verify(first)

    def test_rehashed_semantic_receipt_is_recomputed(self):
        first = self.advance()
        changed = self.rewrite(first, lambda r: r['steps'][0].update(semantic_receipt={'invented': True}))
        with self.assertRaises(checkpoint.CheckpointError):
            self.verify(changed)

    def test_rehashed_argv_environment_or_wait_tamper_is_rejected(self):
        for field, value in [('argv', ['untrusted-command']), ('environment_sha256', 'f' * 64),
                             ('native_wait_completed', False), ('timed_out', True), ('elapsed_ns', -1)]:
            first = self.advance()
            changed = self.rewrite(first, lambda r: r['steps'][0]['command'].update({field: value}))
            with self.subTest(field=field), self.assertRaises(checkpoint.CheckpointError):
                self.verify(changed)

    def test_missing_artifact_cannot_be_claimed_completed(self):
        first = self.advance()
        (Path(first['manifest_path']).parent / 'workspace/One.olean').unlink()
        with self.assertRaises(checkpoint.CheckpointError):
            self.verify(first)

    def test_unknown_invocation_is_not_taken_over_or_assigned_an_outcome(self):
        first = self.advance()
        unknown = 'a' * 32
        orphan = self.root / 'invocations' / unknown
        orphan.mkdir()
        (orphan / 'start.json').write_bytes(b'preserved unresolved original record')
        second = self.advance(first, refs=(unknown,))
        record = self.verify(second)
        self.assertEqual(record['unresolved_invocations'], [unknown])
        self.assertEqual((orphan / 'start.json').read_bytes(), b'preserved unresolved original record')
        self.assertFalse((orphan / 'completion.json').exists())
        self.assertNotEqual(record['invocation_id'], unknown)

    def test_unseen_explicit_reference_does_not_establish_failure(self):
        first = self.advance(refs=('b' * 32,))
        self.assertEqual(self.verify(first)['unresolved_invocations'], ['b' * 32])
        self.assertIn('no unseen outcome inferred', first['manifest']['unresolved_observation_scope'])

    def test_two_explicit_forks_have_separate_output_workspaces(self):
        first = self.advance()
        second_a = self.advance(first)
        second_b = self.advance(first)
        self.assertNotEqual(second_a['manifest_path'], second_b['manifest_path'])
        self.assertEqual(second_a['manifest']['parent_manifest_sha256'], first['manifest_sha256'])
        self.assertEqual(second_b['manifest']['parent_manifest_sha256'], first['manifest_sha256'])
        self.verify(first); self.verify(second_a); self.verify(second_b)

    def test_parent_path_without_pin_is_rejected(self):
        first = self.advance()
        with self.assertRaises(checkpoint.CheckpointError):
            checkpoint.run_stage(self.root, parent_manifest=Path(first['manifest_path']), **self.config)

    def test_continuation_requires_current_import_preflight(self):
        first = self.advance()
        with self.assertRaises(checkpoint.CheckpointError):
            checkpoint.run_stage(self.root, parent_manifest=Path(first['manifest_path']),
                                 expected_parent_sha256=first['manifest_sha256'], **self.config)

    def test_rejected_import_preflight_does_not_launch_next_stage(self):
        first = self.advance()
        def reject(workspace, artifacts):
            raise checkpoint.CheckpointError('wrong import location')
        with patch.object(checkpoint.subprocess, 'Popen') as launch:
            with self.assertRaises(checkpoint.StageFailure) as context:
                self.advance(first, restore=reject)
            launch.assert_not_called()
        failure = json.loads((context.exception.invocation / 'failure.json').read_bytes())
        self.assertIsNone(failure['command'])
        self.assertFalse((context.exception.invocation / 'completion.json').exists())
        self.verify(first)

    def test_restore_callback_cannot_mutate_source_or_add_unlisted_file(self):
        first = self.advance()
        def mutate(workspace, artifacts):
            (workspace / 'Source.lean').write_bytes(b'substitution')
            return {'passed': True}
        with self.assertRaises(checkpoint.StageFailure):
            self.advance(first, restore=mutate)

    def test_unrelated_nonzero_exit_is_retained_but_not_reusable(self):
        config = dict(self.config, stages=(self.stage('failure'),))
        with self.assertRaises(checkpoint.StageFailure) as context:
            self.advance(config=config)
        directory = context.exception.invocation
        failure = json.loads((directory / 'failure.json').read_bytes())
        self.assertEqual(failure['command']['returncode'], 2)
        self.assertTrue(failure['command']['native_wait_completed'])
        self.assertFalse((directory / 'completion.json').exists())
        self.assertTrue((directory / 'native-result.json').exists())
        self.assertEqual((directory / 'logs/000.stderr.bin').read_bytes(), b'unrelated failure\n')

    def test_timeout_is_reaped_retained_and_never_semantically_accepted(self):
        callback = unittest.mock.Mock(wraps=validate)
        config = dict(self.config, stages=(self.stage('timeout', timeout=1),), validate_result=callback)
        with self.assertRaises(checkpoint.StageFailure) as context:
            self.advance(config=config)
        failure = json.loads((context.exception.invocation / 'failure.json').read_bytes())
        self.assertTrue(failure['command']['timed_out'])
        self.assertTrue(failure['command']['native_wait_completed'])
        callback.assert_not_called()

    def test_undeclared_output_blocks_completion(self):
        config = dict(self.config, stages=(self.stage('extra'),))
        with self.assertRaises(checkpoint.StageFailure) as context:
            self.advance(config=config)
        self.assertTrue((context.exception.invocation / 'workspace/undeclared.olean').exists())
        self.assertFalse((context.exception.invocation / 'completion.json').exists())

    def test_input_change_during_stage_blocks_completion(self):
        config = dict(self.config, stages=(self.stage('mutate', args=(str(self.binding),)),))
        with self.assertRaises(checkpoint.StageFailure):
            self.advance(config=config)
        self.assertEqual(self.binding.read_bytes(), b'changed external input')

    def test_cumulative_budget_tamper_is_rejected_even_with_new_outer_hash(self):
        first = self.advance()
        changed = self.rewrite(first, lambda r: r.update(completed_lineage_active_ns=0))
        with self.assertRaises(checkpoint.CheckpointError):
            self.verify(changed)

    def test_budget_overrun_does_not_publish_completed_stage(self):
        config = dict(self.config, max_completed_seconds=1)
        real_clock = checkpoint.time.monotonic_ns
        calls = 0
        def later():
            nonlocal calls
            calls += 1
            return real_clock() + (2_000_000_000 if calls >= 2 else 0)
        with patch.object(checkpoint.time, 'monotonic_ns', side_effect=later), \
             patch.object(checkpoint.subprocess, 'Popen') as launch:
            with self.assertRaises(checkpoint.StageFailure):
                self.advance(config=config)
            launch.assert_not_called()

    def test_missing_or_altered_step_chain_is_rejected(self):
        first = self.advance(); second = self.advance(first)
        changed = self.rewrite(second, lambda r: r['steps'][1].update(previous_step_sha256='e' * 64))
        with self.assertRaises(checkpoint.CheckpointError):
            self.verify(changed)

    def test_completion_marker_cannot_move_to_another_invocation_identity(self):
        first = self.advance()
        original = Path(first['manifest_path']).parent
        other = original.parent / ('c' * 32)
        shutil.copytree(original, other)
        with self.assertRaises(checkpoint.CheckpointError):
            checkpoint.verify_manifest(other / 'completion.json', first['manifest_sha256'], **self.config)

    def test_no_extra_execution_after_complete_plan(self):
        config = dict(self.config, stages=(self.stage('one', ('One.olean',)),))
        first = self.advance(config=config)
        with patch.object(checkpoint.subprocess, 'Popen') as launch:
            with self.assertRaises(checkpoint.CheckpointError):
                self.advance(first, config=config)
            launch.assert_not_called()

    def test_atomic_publication_failure_preserves_failure_and_no_completion(self):
        original_link = checkpoint.os.link
        def fail_completion(src, dst):
            if Path(dst).name == 'completion.json':
                raise OSError('simulated publication failure')
            return original_link(src, dst)
        with patch.object(checkpoint.os, 'link', side_effect=fail_completion):
            with self.assertRaises(checkpoint.StageFailure) as context:
                self.advance()
        self.assertTrue((context.exception.invocation / 'failure.json').exists())
        self.assertFalse((context.exception.invocation / 'completion.json').exists())
        self.assertTrue((context.exception.invocation / 'native-result.json').exists())

    def test_failed_native_launch_is_preserved_without_a_pass(self):
        with patch.object(checkpoint.subprocess, 'Popen', side_effect=OSError('simulated launch failure')):
            with self.assertRaises(checkpoint.StageFailure) as context:
                self.advance()
        failure = json.loads((context.exception.invocation / 'failure.json').read_bytes())
        self.assertIsNone(failure['command']['pid'])
        self.assertFalse(failure['command']['native_wait_completed'])
        self.assertFalse((context.exception.invocation / 'completion.json').exists())

    def test_duplicate_json_keys_are_rejected_even_when_rehashed(self):
        first = self.advance()
        path = Path(first['manifest_path'])
        raw = path.read_bytes().replace(b'{', b'{"schema":"duplicate",', 1)
        path.write_bytes(raw)
        with self.assertRaises(checkpoint.CheckpointError):
            self.verify(dict(first, manifest_sha256=sha(raw)))

    def test_symlink_payload_is_rejected(self):
        first = self.advance()
        path = Path(first['manifest_path']).parent / 'workspace/One.olean'
        external = self.base / 'external-object'
        external.write_bytes(path.read_bytes()); path.unlink()
        try:
            path.symlink_to(external)
        except OSError:
            # Windows may require a separate privilege to create a symlink.
            # Exercise the guard using an explicit controlled link observation;
            # do not skip the test or claim physical Windows link creation.
            real_is_symlink = Path.is_symlink
            with patch.object(Path, 'is_symlink', lambda p: p == path or real_is_symlink(p)):
                with self.assertRaises(checkpoint.CheckpointError):
                    self.verify(first)
            return
        with self.assertRaises(checkpoint.CheckpointError):
            self.verify(first)

    def test_portable_names_reject_reserved_trailing_and_case_collisions(self):
        for name in ('CON', 'folder/NUL.txt', 'file.', 'file ', 'x:y', '../outside', 'a\\b'):
            with self.subTest(name=name), self.assertRaises(checkpoint.CheckpointError):
                checkpoint.Stage('bad', (self.python,), 1, (name,))
        config = dict(self.config, workspace_files=dict(self.config['workspace_files'], **{'source.lean': b'collision'}))
        with self.assertRaises(checkpoint.CheckpointError):
            self.advance(config=config)

    def test_outputs_cannot_replace_inputs_or_other_stage_outputs(self):
        for stages in ((self.stage('one', ('Source.lean',)),),
                       (self.stage('one', ('One.olean',)), self.stage('two', ('One.olean',)))):
            with self.subTest(stages=stages), self.assertRaises(checkpoint.CheckpointError):
                self.advance(config=dict(self.config, stages=stages))

    def test_recorded_command_duration_cannot_exceed_stage_timeout(self):
        first = self.advance()
        def overrun(record):
            record['steps'][0]['command']['elapsed_ns'] = 6_000_000_000
            record['steps'][0]['active_elapsed_ns'] = 6_000_000_000
            record['completed_lineage_active_ns'] = 6_000_000_000
        changed = self.rewrite(first, overrun)
        with self.assertRaises(checkpoint.CheckpointError):
            self.verify(changed)

    def test_native_terminal_record_is_bound_and_reopened(self):
        first = self.advance()
        path = Path(first['manifest_path']).parent / 'native-result.json'
        row = json.loads(path.read_bytes()); row['returncode'] = 99
        path.write_bytes(checkpoint._canonical(row))
        with self.assertRaises(checkpoint.CheckpointError):
            self.verify(first)

    def test_conflicting_failure_marker_blocks_reuse(self):
        first = self.advance()
        (Path(first['manifest_path']).parent / 'failure.json').write_bytes(b'conflicting result')
        with self.assertRaises(checkpoint.CheckpointError):
            self.verify(first)

    def test_executable_must_be_present_in_verified_input_inventory(self):
        config = dict(self.config, input_files={'trusted_fixture': self.binding},
                      expected_input_sha256={'trusted_fixture': sha(self.binding.read_bytes())})
        with patch.object(checkpoint.subprocess, 'Popen') as launch:
            with self.assertRaises(checkpoint.CheckpointError):
                self.advance(config=config)
            launch.assert_not_called()

    def test_complete_invocation_can_relocate_without_relabeling_its_producer(self):
        first = self.advance()
        old = Path(first['manifest_path']).parent
        restored = self.base / 'restored/invocations' / old.name
        shutil.copytree(old, restored)
        shutil.rmtree(old)
        first = dict(first, manifest_path=str(restored / 'completion.json'))
        self.verify(first)
        second = self.advance(first)
        self.verify(second)
        self.assertEqual(second['manifest']['steps'][0]['command']['workspace'], str(old / 'workspace'))
        self.assertNotEqual(second['manifest']['steps'][1]['command']['workspace'], str(old / 'workspace'))

    def test_environment_path_rebinding_is_not_silently_accepted(self):
        first = self.advance()
        environment = dict(self.config['environment'], EXTRA_UNBOUND_PATH='/different/environment')
        with self.assertRaises(checkpoint.CheckpointError):
            self.advance(first, config=dict(self.config, environment=environment))


if __name__ == '__main__':
    unittest.main()
