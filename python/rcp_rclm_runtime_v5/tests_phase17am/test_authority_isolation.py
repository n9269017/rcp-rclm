"""Pure profile/observation checks; these tests do not confer Linux run credit."""
import copy
import errno
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import sys
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17 import authority_isolation as isolation


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.repo = self.root / 'repo'; self.client = self.root / 'client'
        self.native = self.root / 'native'; self.state = self.root / 'state'
        self.authority = self.root / 'authority'
        for p in [self.repo, self.client, self.native, self.state, self.authority]: p.mkdir()
        for p in [self.repo / 'scripts/phase17_authority_isolation_probe.py',
                  self.repo / 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/authority_isolation.py']:
            p.parent.mkdir(parents=True, exist_ok=True); p.write_text('fixture source')
        for name in isolation.CLIENT_FILES: (self.client / name).write_text('fixture ' + name)
        (self.authority / 'server.key').write_text('fixture authority secret')
        self.command = [sys.executable, '-c', 'print("fixture, not live evidence")']
        self.patches = [patch.object(isolation.sys, 'platform', 'linux'),
                        patch.object(isolation.shutil, 'which', return_value=sys.executable),
                        patch.object(isolation.os, 'getuid', return_value=1000, create=True),
                        patch.object(isolation.os, 'getgid', return_value=1000, create=True),
                        patch.object(isolation, '_namespaces', return_value={n: n + '-host' for n in (*isolation.PRIVATE_NAMESPACES, 'net')})]
        if os.name == 'nt':
            # These cases test host filesystem guards and observation structure.
            # They do not pretend Windows temp paths are executable Linux paths.
            # The full Linux prefix is separately tested with fixed POSIX input
            # by PureReplayProfileTests on every platform, without patching it.
            self.patches.append(patch.object(isolation, '_profile_prefix', side_effect=lambda spec: [
                'CONTROLLED-WINDOWS-STRUCTURAL-FIXTURE', '--share-net', '--disable-userns']))
        for p in self.patches: p.start()

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()

    def build(self, **kwargs):
        params = dict(state_directory=self.state, protected_paths=[self.authority, self.authority / 'server.key'])
        params.update(kwargs)
        return isolation.build_client_command(self.repo, self.client, self.native, self.command, **params)

    @staticmethod
    def record():
        # Saved Linux observations have POSIX paths even when the verifier runs
        # on Windows. Keep them separate from the host filesystem build fixture.
        spec = PureReplayProfileTests.specification()
        spec['protected_targets'] = [spec['protected_targets'][0], spec['protected_targets'][2]]
        spec = json.loads(isolation._canonical(spec))
        record = {'schema': 'phase17am.controller-isolation-observation.v1', 'profile': isolation.PROFILE,
                  'probe_name': spec['probe_name'], 'spec_sha256': isolation.hashlib.sha256(isolation._canonical(spec)).hexdigest(),
                  'command': spec['command'], 'pid': 2, 'uid': spec['host_uid'], 'gid': spec['host_gid'],
                  'namespaces': {**{n: n + '-child' for n in isolation.PRIVATE_NAMESPACES}, 'net': spec['host_namespaces']['net']},
                  'proc_pids': [1, 2], 'security_status': {**{n: '0000000000000000' for n in isolation.CAPABILITIES}, 'NoNewPrivs': '1', 'Seccomp': '2'},
                  'descriptor_targets': {'0': '/dev/null', '1': 'pipe:[1]', '2': 'pipe:[2]'},
                  'nested_user_namespace': {'returncode': -1, 'errno': errno.ENOSPC},
                  'readonly_hashes': spec['readonly_files'],
                  'checks': [{'name': n, 'path': p, 'denied': True, 'errno': errno.EROFS if n.startswith('readonly-') else errno.ENOENT}
                             for n, p in isolation._expected_checks(spec)],
                  'network_scope': 'shared_host_namespace_unrestricted',
                  'authority_workers_confined': False, 'independent_principal_established': False}
        return spec, record

    def test_exact_bundle_readonly_and_shared_network_explicit(self):
        argv = self.build(); spec = isolation.specification_from_command(argv)
        self.assertIn('--share-net', argv); self.assertIn('--disable-userns', argv)
        self.assertEqual(spec['network_scope'], 'shared_host_namespace_unrestricted')
        self.assertEqual(spec['command'], self.command)
        self.assertFalse(spec['authority_workers_confined'])

    def test_server_private_key_in_bundle_refused(self):
        (self.client / 'server.key').write_text('must not expose')
        with self.assertRaises(isolation.IsolationError): self.build()

    def test_bundle_symlink_refused(self):
        # Structural guard fixture; Windows need not grant symlink creation.
        with patch.object(type(self.client), 'is_symlink', return_value=True):
            with self.assertRaises(isolation.IsolationError): self.build()

    def test_protected_target_in_mounted_tree_refused(self):
        with self.assertRaises(isolation.IsolationError): self.build(protected_paths=[self.client / 'client.key'])

    def test_empty_or_absent_protected_targets_refused(self):
        with self.assertRaises(isolation.IsolationError): self.build(protected_paths=[])
        with self.assertRaises(FileNotFoundError): self.build(protected_paths=[self.authority / 'absent'])

    def test_windows_explicitly_unavailable(self):
        with patch.object(isolation.sys, 'platform', 'win32'):
            with self.assertRaises(isolation.IsolationUnavailable): self.build()

    def test_no_unconfined_fallback_when_bwrap_absent(self):
        with patch.object(isolation.shutil, 'which', return_value=None):
            with self.assertRaises(isolation.IsolationUnavailable): self.build()

    def test_host_retained_frame_fixture_accepted_as_structure_only(self):
        spec, record = self.record()
        result = isolation.verify_boundary_observation(record, spec)
        self.assertEqual(result['denial_checks'], 17)
        line = isolation.FRAME_PREFIX + json.dumps(record) + '\n'
        self.assertEqual(isolation.parse_boundary_frame(line, spec), record)

    def test_file_stdout_or_inherited_fd_refused(self):
        spec, record = self.record()
        for change in [{'1': '/host/rewritable-stdout.txt'}, {'3': '/host/authority.key'}]:
            modified = copy.deepcopy(record); modified['descriptor_targets'].update(change)
            with self.assertRaises(isolation.IsolationError): isolation.verify_boundary_observation(modified, spec)

    def test_namespace_caps_or_readonly_mutation_refused(self):
        spec, record = self.record()
        for kind in ['namespace', 'caps', 'source']:
            modified = copy.deepcopy(record)
            if kind == 'namespace': modified['namespaces']['pid'] = spec['host_namespaces']['pid']
            elif kind == 'caps': modified['security_status']['CapEff'] = '0000000000000001'
            else: modified['readonly_hashes'] = {p: '0' * 64 for p in spec['readonly_files']}
            with self.assertRaises(isolation.IsolationError): isolation.verify_boundary_observation(modified, spec)

    def test_missing_or_allowed_protected_operation_refused(self):
        spec, record = self.record()
        for kind in ['missing', 'allowed', 'wrong_errno']:
            modified = copy.deepcopy(record)
            if kind == 'missing': modified['checks'].pop()
            elif kind == 'allowed': modified['checks'][0]['denied'] = False
            else: modified['checks'][0]['errno'] = errno.EINVAL
            with self.assertRaises(isolation.IsolationError): isolation.verify_boundary_observation(modified, spec)

    def test_false_network_or_deployment_claim_refused(self):
        spec, record = self.record()
        for field, value in [('network_scope', 'loopback_only'), ('authority_workers_confined', True), ('independent_principal_established', True)]:
            modified = copy.deepcopy(record); modified[field] = value
            with self.assertRaises(isolation.IsolationError): isolation.verify_boundary_observation(modified, spec)


class PureReplayProfileTests(unittest.TestCase):
    """Full POSIX launch reconstruction; no host paths, tools or Linux required."""
    @staticmethod
    def specification():
        repo = '/source/repo'; client = '/physical/client'
        return {'schema': 'phase17am.controller-isolation-spec.v1', 'profile': isolation.PROFILE,
                'probe_name': 'pure-fixture', 'command': ['/runtime/python/bin/python3', '-B', '/source/repo/scripts/client.py'],
                'host_pid': 100, 'host_uid': 1000, 'host_gid': 1000,
                'host_namespaces': {n: n + ':[100]' for n in (*isolation.PRIVATE_NAMESPACES, 'net')},
                'repo': repo, 'client_bundle': client, 'native_output': '/physical/native/action',
                'state_directory': '/physical/client-state', 'runtime_prefix': '/runtime/python',
                'bwrap_executable': '/usr/bin/bwrap', 'wrapper_executable': '/runtime/python/bin/python3.12',
                'python_alias': '/runtime/python/bin/python3',
                'protected_targets': [{'path': '/physical/authority', 'kind': 'directory'},
                                      {'path': '/physical/authority/db', 'kind': 'file'},
                                      {'path': '/physical/pki/server.key', 'kind': 'file'}],
                'readonly_files': {repo + '/scripts/phase17_authority_isolation_probe.py': '1' * 64,
                    repo + '/python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/authority_isolation.py': '2' * 64,
                    client + '/client.key': '3' * 64},
                'network_scope': 'shared_host_namespace_unrestricted',
                'authority_workers_confined': False, 'independent_principal_established': False}

    def command(self, spec=None):
        spec = self.specification() if spec is None else spec
        return isolation._profile_prefix(spec) + ['--probe-spec', isolation._canonical(spec).decode(), '--', *spec['command']]

    def test_exact_posix_profile_replays_without_filesystem(self):
        with patch.object(Path, 'resolve', side_effect=AssertionError('replay must not resolve files')):
            self.assertEqual(isolation.specification_from_command(self.command()), self.specification())
        spec, record = ProfileTests.record()
        expected = [
            ('protected-0-exists', '/physical/authority'),
            ('protected-0-read', '/physical/authority'),
            ('protected-0-write', '/physical/authority'),
            ('protected-0-replace-parent', '/physical/authority'),
            ('protected-0-proc1-read', '/proc/1/root/physical/authority'),
            ('protected-0-outerproc-read', '/proc/100/root/physical/authority'),
            ('protected-0-dotdot-read', '/repo/../../physical/authority'),
            ('protected-1-exists', '/physical/pki/server.key'),
            ('protected-1-read', '/physical/pki/server.key'),
            ('protected-1-write', '/physical/pki/server.key'),
            ('protected-1-replace-parent', '/physical/pki/server.key'),
            ('protected-1-proc1-read', '/proc/1/root/physical/pki/server.key'),
            ('protected-1-outerproc-read', '/proc/100/root/physical/pki/server.key'),
            ('protected-1-dotdot-read', '/repo/../../physical/pki/server.key'),
            ('readonly-0-write', '/physical/client/client.key'),
            ('readonly-1-write', '/source/repo/python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/authority_isolation.py'),
            ('readonly-2-write', '/source/repo/scripts/phase17_authority_isolation_probe.py'),
        ]
        frame = isolation.FRAME_PREFIX + json.dumps(record) + '\n'
        for host_path in (PurePosixPath, PureWindowsPath):
            with self.subTest(host_path=host_path.__name__), patch.object(isolation, 'Path', host_path):
                self.assertEqual(isolation._expected_checks(spec), expected)
                self.assertEqual(isolation.specification_from_command(self.command(spec)), spec)
                self.assertTrue(isolation.verify_boundary_observation(record, spec)['checked'])
                self.assertEqual(isolation.parse_boundary_frame(frame, spec), record)
        forbidden = AssertionError('saved replay must not construct host paths or perform file I/O')
        with patch.object(isolation, 'Path', side_effect=forbidden), \
                patch('builtins.open', side_effect=forbidden), \
                patch.object(isolation.os, 'open', side_effect=forbidden):
            self.assertEqual(isolation.specification_from_command(self.command(spec)), spec)
            self.assertEqual(isolation._expected_checks(spec), expected)
            self.assertTrue(isolation.verify_boundary_observation(record, spec)['checked'])
            self.assertEqual(isolation.parse_boundary_frame(frame, spec), record)

    def test_removed_namespace_or_privilege_flags_refused(self):
        for flag in ['--unshare-all', '--unshare-user', '--disable-userns', '--clearenv', '--share-net', '--new-session']:
            with self.subTest(flag=flag):
                argv = self.command(); argv.remove(flag)
                with self.assertRaises(isolation.IsolationError): isolation.specification_from_command(argv)

    def test_added_protected_or_writable_mount_refused(self):
        for extra in [['--bind', '/physical/authority', '/authority'], ['--ro-bind', '/', '/host']]:
            argv = self.command(); argv[1:1] = extra
            with self.assertRaises(isolation.IsolationError): isolation.specification_from_command(argv)

    def test_readonly_source_changed_to_writable_refused(self):
        argv = self.command()
        i = next(i for i, value in enumerate(argv) if value == '--ro-bind' and argv[i + 1] == '/source/repo')
        argv[i] = '--bind'
        with self.assertRaises(isolation.IsolationError): isolation.specification_from_command(argv)

    def test_root_runtime_or_exposed_protected_path_refused(self):
        for target in ['/', '/physical', '/source/repo']:
            spec = self.specification(); spec['runtime_prefix'] = target
            with self.assertRaises(isolation.IsolationError): self.command(spec)

    def test_noncanonical_or_alias_collision_paths_refused(self):
        for value in ['/source/../source/repo', '/source//repo', '/repo/inside', 'C:\\source\\repo']:
            spec = self.specification(); spec['repo'] = value
            with self.assertRaises(isolation.IsolationError): self.command(spec)

    def test_client_state_or_native_exposure_refused(self):
        for field in ['state_directory', 'native_output', 'client_bundle']:
            spec = self.specification(); spec[field] = '/physical/authority'
            with self.assertRaises(isolation.IsolationError): self.command(spec)

    def test_changed_interpreter_or_source_inventory_refused(self):
        spec = self.specification(); spec['command'][0] = '/other/python'
        with self.assertRaises(isolation.IsolationError): self.command(spec)
        spec = self.specification(); spec['readonly_files']['/physical/pki/server.key'] = '4' * 64
        with self.assertRaises(isolation.IsolationError): self.command(spec)

    def test_noncanonical_json_or_extra_spec_field_refused(self):
        argv = self.command(); index = argv.index('--probe-spec') + 1
        argv[index] = json.dumps(self.specification(), indent=2)
        with self.assertRaises(isolation.IsolationError): isolation.specification_from_command(argv)
        spec = self.specification(); spec['extra_hidden_profile'] = True
        with self.assertRaises(isolation.IsolationError): self.command(spec)


if __name__ == '__main__':
    unittest.main()
