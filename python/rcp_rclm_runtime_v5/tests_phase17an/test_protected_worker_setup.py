"""Constructor regressions for canonical owned worker scratch allocation.

These tests run the actual client constructor and the strict isolation builder,
with real temporary directories. A narrow resolver shim supplies Windows 8.3
alias semantics on either host platform; no Windows execution is claimed.
Native process creation is intercepted before any worker can start.
"""
from __future__ import annotations

from pathlib import Path, PureWindowsPath
import sys
import tempfile
import unittest
from unittest import mock

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime_v5.phase17 import protected_campaign_native as native
from rcp_rclm_runtime_v5.phase17 import protected_authority_isolation as isolation
from rcp_rclm_runtime_v5.phase17.campaign_budget import make_grant
from rcp_rclm_runtime_v5.phase17.controller import FIXED_VERIFIER


REAL_TEMPORARY_DIRECTORY = tempfile.TemporaryDirectory
REAL_TEMPORARY_FILE = tempfile.TemporaryFile
SHORT_PARENT = r'C:\Users\NICOLA~1.N92\AppData\Local\Temp'


class LaunchPrevented(RuntimeError):
    """The real constructor reached the fixed launch boundary; no process ran."""


class AliasPath:
    """A controlled short spelling whose strict resolution returns a real path."""

    def __init__(self, spelling, target, resolution_error=None):
        self.spelling = spelling
        self.target = target
        self.resolution_error = resolution_error
        self.strict_resolutions = []

    def __fspath__(self):
        return self.spelling

    def __str__(self):
        return self.spelling

    def is_absolute(self):
        return PureWindowsPath(self.spelling).is_absolute()

    def resolve(self, *, strict=False):
        self.strict_resolutions.append(strict)
        if self.resolution_error is not None:
            raise self.resolution_error
        return self.target.resolve(strict=strict)

    def is_file(self):
        return self.target.is_file()

    def is_dir(self):
        return self.target.is_dir()

    def __eq__(self, other):
        return isinstance(other, AliasPath) and self.spelling == other.spelling


class OwnedDirectory:
    """Keep real ownership/cleanup while reporting the constructor's spelling."""

    def __init__(self, actual, reported_name):
        self.actual = actual
        self.name = reported_name
        self.cleaned = False

    def cleanup(self):
        self.actual.cleanup()
        self.cleaned = True


class ProtectedWorkerSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = REAL_TEMPORARY_DIRECTORY(prefix='phase17an-setup-test-')
        self.base = Path(self.tmp.name).resolve(strict=True)
        self.parent = self.base / 'canonical-temp-parent'; self.parent.mkdir()
        self.protected = self.base / 'protected'; self.protected.mkdir()
        self.native_directory = self.base / 'native-records'
        self.alias_parent = AliasPath(SHORT_PARENT, self.parent)
        self.aliases = {SHORT_PARENT: self.alias_parent}
        self.allocations = []
        self.allocation_arguments = []
        self.force_allocated_alias = False
        self.ambient_parent = SHORT_PARENT
        self.client = native.ProtectedCampaignEvaluatorClient.__new__(native.ProtectedCampaignEvaluatorClient)
        self.grant = make_grant({'campaign_id': '1' * 64, 'predecessor_state_hash': '2' * 64,
            'predecessor_package_hash': '3' * 64, 'fixed_verifier_hash': FIXED_VERIFIER,
            'installed_count': 8}, 0, '0' * 64, '4' * 64, 2)

    def tearDown(self):
        for owned in self.allocations:
            if not owned.cleaned:
                owned.cleanup()
        self.tmp.cleanup()

    def path(self, value, *parts):
        if isinstance(value, AliasPath) and not parts:
            return value
        if not parts and isinstance(value, str) and value in self.aliases:
            return self.aliases[value]
        return Path(value, *parts)

    def allocate(self, *args, **kwargs):
        self.allocation_arguments.append((args, dict(kwargs)))
        # Simulate the same existing directory reached through the ambient
        # Windows short parent. Explicit canonical parents produce canonical
        # owned names; omitted parents preserve the ambient short spelling.
        passed_parent = kwargs.get('dir')
        if passed_parent is not None:
            self.assertEqual(Path(passed_parent), self.parent)
        actual = REAL_TEMPORARY_DIRECTORY(*args, **{**kwargs, 'dir': str(self.parent)})
        real_name = str(Path(actual.name).resolve(strict=True))
        aliased = (passed_parent is None and self.ambient_parent == SHORT_PARENT) or self.force_allocated_alias
        reported = str(PureWindowsPath(SHORT_PARENT) / Path(real_name).name) if aliased else real_name
        if aliased:
            self.aliases[reported] = AliasPath(reported, Path(real_name))
        owned = OwnedDirectory(actual, reported)
        self.allocations.append(owned)
        return owned

    def construct(self, *, parent=SHORT_PARENT, build_failure=None, protected_paths=None):
        protected_paths = [self.protected] if protected_paths is None else protected_paths
        self.ambient_parent = parent
        with mock.patch.object(native, 'Path', side_effect=self.path), \
             mock.patch.object(isolation, 'Path', side_effect=self.path), \
             mock.patch.object(native.tempfile, 'gettempdir', return_value=parent), \
             mock.patch.object(native.tempfile, 'TemporaryDirectory', side_effect=self.allocate), \
             mock.patch.object(native.tempfile, 'TemporaryFile',
                 side_effect=lambda: REAL_TEMPORARY_FILE(dir=str(self.parent))), \
             mock.patch.object(isolation.shutil, 'which', return_value=sys.executable), \
             mock.patch.object(native.subprocess, 'Popen', side_effect=LaunchPrevented('native launch disabled')) as launch:
            self.launch = launch
            if build_failure is None:
                native.ProtectedCampaignEvaluatorClient.__init__(self.client, self.grant,
                    native_directory=self.native_directory, protected_paths=protected_paths)
            else:
                with mock.patch.object(isolation, 'build_command', side_effect=build_failure):
                    native.ProtectedCampaignEvaluatorClient.__init__(self.client, self.grant,
                        native_directory=self.native_directory, protected_paths=protected_paths)

    def assert_owned_cleanup(self):
        self.assertEqual(len(self.allocations), 1)
        owned = self.allocations[0]
        self.assertTrue(owned.cleaned)
        self.assertFalse(Path(owned.actual.name).exists())
        self.assertTrue(self.client.closed)
        self.assertTrue(self.client._native_input.closed)
        self.assertTrue(self.client._native_output.closed)
        self.assertTrue(self.client._stderr.closed)

    def test_short_temp_parent_reaches_fixed_launch_with_canonical_owned_scratch(self):
        with self.assertRaises(LaunchPrevented):
            self.construct()
        self.launch.assert_called_once()
        self.assertEqual(self.alias_parent.strict_resolutions, [True])
        owned = self.allocations[0]
        self.assertEqual(self.launch.call_args.kwargs['cwd'], owned.name)
        self.assertEqual(Path(owned.name).parent, self.parent)
        start = load_json_strict((self.native_directory / 'start.json').read_bytes())
        self.assertEqual(start['isolation_specification']['scratch_directory'], owned.name)
        self.assertEqual(start['command'], self.launch.call_args.args[0])
        self.assert_owned_cleanup()
        result = load_json_strict((self.native_directory / 'result.json').read_bytes())
        self.assertIs(result['native_wait_completed'], False)
        self.assertIs(result['capture_failed'], True)
        self.assertIsNone(result['child_pid'])

    def test_normal_temp_parent_also_uses_one_owned_canonical_directory(self):
        with self.assertRaises(LaunchPrevented):
            self.construct(parent=str(self.parent))
        self.launch.assert_called_once()
        self.assertEqual(Path(self.allocations[0].name).parent, self.parent)
        self.assert_owned_cleanup()

    def test_strict_parent_resolution_failure_precedes_allocation_and_launch(self):
        self.alias_parent.resolution_error = FileNotFoundError('controlled missing temp parent')
        with self.assertRaisesRegex(FileNotFoundError, 'controlled missing temp parent'):
            self.construct()
        self.assertEqual(self.alias_parent.strict_resolutions, [True])
        self.assertEqual(self.allocation_arguments, [])
        self.launch.assert_not_called()
        self.assertEqual(list(self.native_directory.iterdir()), [])

    def test_build_refusal_closes_captures_and_removes_owned_scratch(self):
        failure = isolation.IsolationError('controlled prelaunch policy refusal')
        with self.assertRaisesRegex(isolation.IsolationError, 'controlled prelaunch policy refusal'):
            self.construct(build_failure=failure)
        self.launch.assert_not_called()
        self.assert_owned_cleanup()
        self.assertEqual({p.name for p in self.native_directory.iterdir()}, {'stdin.jsonl', 'stdout.jsonl'})
        self.assertEqual((self.native_directory / 'stdin.jsonl').read_bytes(), b'')
        self.assertEqual((self.native_directory / 'stdout.jsonl').read_bytes(), b'')

    def test_canonical_scratch_still_cannot_overlap_a_protected_directory(self):
        with self.assertRaisesRegex(isolation.IsolationError, 'overlap'):
            self.construct(parent=str(self.parent), protected_paths=[self.parent])
        self.launch.assert_not_called()
        self.assert_owned_cleanup()

    def test_strict_guard_still_rejects_an_unresolved_caller_path(self):
        with mock.patch.object(isolation, 'Path', side_effect=self.path):
            with self.assertRaisesRegex(isolation.IsolationError, 'absolute, existing and without symlinks'):
                isolation._absolute(self.alias_parent, directory=True)
        self.assertEqual(self.alias_parent.strict_resolutions, [True])

    def test_an_aliased_allocated_name_is_rejected_even_after_parent_normalization(self):
        self.force_allocated_alias = True
        with self.assertRaisesRegex(isolation.IsolationError, 'absolute, existing and without symlinks'):
            self.construct()
        self.launch.assert_not_called()
        self.assert_owned_cleanup()


if __name__ == '__main__':
    unittest.main()
