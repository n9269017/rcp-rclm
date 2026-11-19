"""Synthetic namespace-contract tests; these are not native isolation evidence."""
from __future__ import annotations

import copy
import errno
import hashlib
import json
from pathlib import PurePosixPath, PureWindowsPath
import unittest

from rcp_rclm_runtime_v5.phase17 import protected_authority_isolation as boundary


def synthetic_specification(role='frontend', platform='linux', source_root=None):
    windows = platform == 'win32'; P = PureWindowsPath if windows else PurePosixPath
    repo = P(source_root or ('C:\\synthetic\\source' if windows else '/synthetic/source'))
    runtime = P('C:\\runtime' if windows else '/synthetic/runtime')
    python = runtime / ('python.exe' if windows else 'bin/python3')
    scratch = P('C:\\synthetic\\scratch' if windows else '/synthetic/scratch')
    private = P('C:\\synthetic\\protected' if windows else '/synthetic/protected')
    profile = boundary.launch_profile(role, platform)
    command = [str(python), '-I', '-S', '-B', '-u', str(repo / profile['fixed_target'])]
    readonly = [repo / 'scripts/phase17_protected_isolation_probe.py',
                repo / 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/protected_authority_isolation.py',
                repo / profile['fixed_target'], python]
    return {'schema': 'phase17an.protected-isolation-spec.v1', 'profile': profile,
        'observation_id': 'a' * 32, 'command': command, 'repo': str(repo), 'scratch_directory': str(scratch),
        'protected_targets': [{'path': str(private), 'kind': 'directory'}], 'runtime_prefix': str(runtime),
        'python_executable': str(python), 'python_alias': str(python),
        'bwrap_executable': None if windows else '/usr/bin/bwrap',
        'unshare_executable': None if windows else '/usr/bin/unshare',
        'host_pid': 111, 'host_uid': None if windows else 1000, 'host_gid': None if windows else 1000,
        'host_namespaces': None if windows else {name: name + ':[100]' for name in boundary.PRIVATE_NAMESPACES},
        'readonly_files': {str(p): '5' * 64 for p in readonly},
        'shell': False, 'close_fds': True, 'pass_fds': []}


def synthetic_observation(spec):
    if spec['profile']['platform'] == 'win32': return None
    return {'schema': 'phase17an.protected-boundary-observation.v1',
        'observation_id': spec['observation_id'],
        'specification_sha256': hashlib.sha256(boundary._canonical(spec)).hexdigest(),
        'profile': copy.deepcopy(spec['profile']), 'pid': 1, 'uid': 1000, 'gid': 1000,
        'process_start_ticks': 1000,
        'namespaces': {name: name + ':[200]' for name in boundary.PRIVATE_NAMESPACES},
        'capabilities': {name: '0000000000000000' for name in boundary.CAPABILITIES},
        'no_new_privs': '1', 'cwd': spec['scratch_directory'],
        'descriptor_targets': {'0': 'pipe:[10]', '1': 'pipe:[11]', '2': '/synthetic/capture.err'},
        'checks': [{'name': name, 'path': path, 'denied': True,
                    'errno': errno.EROFS if name.startswith('readonly-') else errno.ENOENT,
                    'exception': 'OSError'} for name, path in boundary._expected_checks(spec)],
        'readonly_files': copy.deepcopy(spec['readonly_files']), 'network_interfaces': None,
        'independent_host_principal_established': False, 'physical_attestation': False}


class ProtectedBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.spec = synthetic_specification(); self.observation = synthetic_observation(self.spec)

    def test_synthetic_observation_is_a_contract_fixture_only(self):
        self.assertTrue(boundary.validate_observation(self.spec, self.observation))

    def test_both_linux_roles_require_private_network_without_secret_mounts(self):
        for role in ('frontend', 'worker'):
            p = boundary.launch_profile(role, 'linux')
            self.assertTrue(p['private_network_required'])
            for key in ('credential_mounts', 'retained_anchor_mounts', 'authority_root_mounts',
                        'independent_host_principal_established', 'physical_attestation'):
                self.assertIs(p[key], False)

    def test_exact_outer_namespace_constructor_is_required(self):
        argv = boundary._prefix(self.spec)
        self.assertEqual(argv[:7], ['/usr/bin/unshare', '--user', '--map-current-user', '--net', '--',
                                    '/usr/bin/bwrap', '--unshare-all'])
        self.assertEqual(boundary.specification_from_command(argv), self.spec)
        argv.remove('--net')
        with self.assertRaises(ValueError): boundary.specification_from_command(argv)

    def test_arbitrary_writable_or_credential_mount_cannot_be_added(self):
        argv = boundary._prefix(self.spec)
        argv[7:7] = ['--bind', '/synthetic/protected', '/synthetic/protected']
        with self.assertRaises(ValueError): boundary.specification_from_command(argv)

    def test_fixed_target_cannot_be_replaced(self):
        self.spec['command'][-1] = '/synthetic/source/scripts/other.py'
        with self.assertRaises(ValueError): boundary._prefix(self.spec)

    def test_profile_boolean_integer_alias_is_rejected(self):
        self.spec['profile']['credential_mounts'] = 0
        with self.assertRaises(ValueError): boundary._prefix(self.spec)

    def test_secret_target_cannot_overlap_source_or_scratch(self):
        for path in (self.spec['repo'], self.spec['scratch_directory']):
            item = copy.deepcopy(self.spec); item['protected_targets'][0]['path'] = path
            with self.subTest(path=path), self.assertRaises(ValueError): boundary._prefix(item)

    def test_missing_or_duplicate_protected_targets_fail_closed(self):
        for targets in ([], self.spec['protected_targets'] * 2):
            item = copy.deepcopy(self.spec); item['protected_targets'] = targets
            with self.assertRaises(ValueError): boundary._prefix(item)

    def test_all_six_namespaces_must_differ_from_host(self):
        for name in boundary.PRIVATE_NAMESPACES:
            item = copy.deepcopy(self.observation); item['namespaces'][name] = self.spec['host_namespaces'][name]
            with self.subTest(namespace=name), self.assertRaises(ValueError): boundary.validate_observation(self.spec, item)

    def test_retained_capability_is_rejected(self):
        self.observation['capabilities']['CapEff'] = '0000000000000001'
        with self.assertRaises(ValueError): boundary.validate_observation(self.spec, self.observation)

    def test_privilege_gain_is_rejected(self):
        self.observation['no_new_privs'] = '0'
        with self.assertRaises(ValueError): boundary.validate_observation(self.spec, self.observation)

    def test_inherited_descriptor_is_rejected(self):
        self.observation['descriptor_targets']['3'] = '/synthetic/protected/key'
        with self.assertRaises(ValueError): boundary.validate_observation(self.spec, self.observation)

    def test_nonpipe_protocol_channel_is_rejected(self):
        self.observation['descriptor_targets']['0'] = '/synthetic/protected/key'
        with self.assertRaises(ValueError): boundary.validate_observation(self.spec, self.observation)

    def test_successful_protected_read_is_not_an_accepted_denial(self):
        self.observation['checks'][0].update(denied=False, errno=None, exception=None)
        with self.assertRaises(ValueError): boundary.validate_observation(self.spec, self.observation)

    def test_arbitrary_probe_error_is_not_an_accepted_denial(self):
        self.observation['checks'][0]['errno'] = errno.EIO
        with self.assertRaises(ValueError): boundary.validate_observation(self.spec, self.observation)

    def test_missing_or_reordered_probe_inventory_is_rejected(self):
        for checks in (self.observation['checks'][:-1], list(reversed(self.observation['checks']))):
            item = copy.deepcopy(self.observation); item['checks'] = checks
            with self.assertRaises(ValueError): boundary.validate_observation(self.spec, item)

    def test_specification_binding_is_required(self):
        self.observation['specification_sha256'] = '0' * 64
        with self.assertRaises(ValueError): boundary.validate_observation(self.spec, self.observation)

    def test_boolean_pid_does_not_alias_private_pid_one(self):
        self.observation['pid'] = True
        with self.assertRaises(ValueError): boundary.validate_observation(self.spec, self.observation)

    def test_readonly_inventory_order_is_canonical_after_json_roundtrip(self):
        ordered = json.loads(boundary._canonical(self.spec))
        self.assertTrue(boundary.validate_observation(ordered, self.observation))

    def test_frame_requires_complete_exact_canonical_bytes(self):
        raw = boundary.FRAME_PREFIX + boundary._canonical(self.observation) + b'\n'
        self.assertEqual(boundary.parse_boundary_frame(raw), self.observation)
        for wrong in (raw[:-1], b'X' + raw, raw + b'\n',
                      boundary.FRAME_PREFIX + json.dumps(self.observation, indent=2).encode() + b'\n'):
            with self.assertRaises(ValueError): boundary.parse_boundary_frame(wrong)

    def test_platform_scope_cannot_be_escalated(self):
        self.observation['independent_host_principal_established'] = True
        with self.assertRaises(ValueError): boundary.validate_observation(self.spec, self.observation)

    def test_windows_paths_are_parsed_as_windows_on_every_host(self):
        spec = synthetic_specification(platform='win32')
        self.assertEqual(boundary._prefix(spec), spec['command'])
        self.assertTrue(boundary.validate_observation(spec, None))

    def test_windows_reference_cannot_claim_linux_observation(self):
        spec = synthetic_specification(platform='win32')
        with self.assertRaises(ValueError): boundary.validate_observation(spec, self.observation)

    def test_windows_reference_cannot_supply_linux_namespace_specification(self):
        spec = synthetic_specification(platform='win32'); spec['host_namespaces'] = self.spec['host_namespaces']
        with self.assertRaises(ValueError): boundary._prefix(spec)

    def test_windows_command_and_secret_inventory_remain_exact(self):
        spec = synthetic_specification(platform='win32'); spec['protected_targets'][0]['path'] = spec['repo']
        with self.assertRaises(ValueError): boundary._prefix(spec)


if __name__ == '__main__':
    unittest.main()
