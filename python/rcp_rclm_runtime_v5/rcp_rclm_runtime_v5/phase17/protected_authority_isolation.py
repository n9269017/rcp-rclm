"""AN's observed credential-free frontend and fixed-worker process boundary.

The trusted launcher retains the first pre-exec frame outside every writable
mount. Linux uses private network, user, mount, PID, IPC and UTS namespaces.
Neither role receives an authority root, currentness anchor or credential mount.
This does not create an independently provisioned host principal. Windows is an
explicit unconfined reference execution and receives no Linux boundary credit.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import sys
import uuid

PROFILE = 'phase17an.linux-bwrap-protected.v1'
WINDOWS_PROFILE = 'phase17an.windows-unconfined-reference.v1'
FRAME_PREFIX = b'PHASE17AN_BOUNDARY '
MAX_BOUNDARY_BYTES = 512 * 1024
PRIVATE_NAMESPACES = ('mnt', 'pid', 'ipc', 'uts', 'user', 'net')
CAPABILITIES = ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')
DENIED = frozenset({errno.ENOENT, errno.EACCES, errno.EROFS})
TARGETS = {'frontend': 'scripts/phase17_protected_frontend.py',
           'worker': 'scripts/phase17_campaign_worker.py'}


class IsolationError(ValueError):
    pass


class IsolationUnavailable(IsolationError):
    pass


def _need(condition, message):
    if not condition:
        raise IsolationError(message)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def launch_profile(role, platform_name=None):
    _need(role in TARGETS, 'unknown protected execution role')
    platform_name = sys.platform if platform_name is None else platform_name
    _need(platform_name in ('linux', 'win32'), 'unsupported protected execution platform')
    confined = platform_name == 'linux'
    return {'schema': 'phase17an.protected-launch-profile.v1', 'role': role,
        'profile': PROFILE if confined else WINDOWS_PROFILE,
        'platform': platform_name, 'namespace_boundary_required': confined,
        'private_network_required': confined, 'credential_mounts': False,
        'network_constructor': 'outer_unshare_user_net' if confined else None,
        'retained_anchor_mounts': False, 'authority_root_mounts': False,
        'trusted_preexec_observer_required': confined,
        'fixed_target': TARGETS[role],
        'independent_host_principal_established': False,
        'complete_resource_containment': False, 'physical_attestation': False}


def _absolute(path, *, directory=None):
    path = Path(path)
    _need(path.is_absolute() and path.resolve(strict=True) == path,
          'protected paths must be absolute, existing and without symlinks')
    _need(path.is_file() or path.is_dir(), 'protected path is not an ordinary file or directory')
    if directory is not None:
        _need(path.is_dir() == directory, 'protected path kind differs')
    return path


def _overlap(a, b):
    return a == b or a in b.parents or b in a.parents


def _posix(value):
    _need(type(value) is str and value.startswith('/') and '\\' not in value and '\x00' not in value,
          'recorded Linux profile requires an absolute POSIX path')
    p = PurePosixPath(value)
    _need(p.as_posix() == value and '..' not in p.parts and str(p) != '/',
          'recorded Linux path is not normalized')
    return p


def _namespaces():
    return {name: os.readlink('/proc/self/ns/' + name) for name in PRIVATE_NAMESPACES}


def _validate_specification(spec):
    keys = {'schema', 'profile', 'observation_id', 'command', 'repo', 'scratch_directory',
            'protected_targets', 'runtime_prefix', 'python_executable', 'python_alias',
            'bwrap_executable', 'unshare_executable', 'host_pid', 'host_uid', 'host_gid', 'host_namespaces',
            'readonly_files', 'shell', 'close_fds', 'pass_fds'}
    _need(type(spec) is dict and set(spec) == keys and
          spec['schema'] == 'phase17an.protected-isolation-spec.v1', 'protected specification keys differ')
    profile = spec['profile']
    _need(type(profile) is dict and _canonical(profile) == _canonical(launch_profile(profile.get('role'), profile.get('platform'))),
          'protected profile differs')
    _need(type(spec['observation_id']) is str and re.fullmatch('[0-9a-f]{32}', spec['observation_id']),
          'invalid boundary observation identity')
    _need(spec['shell'] is False and spec['close_fds'] is True and spec['pass_fds'] == [],
          'protected descriptor or shell policy differs')
    command = spec['command']
    _need(type(command) is list and len(command) == 6 and
          all(type(v) is str and v and '\x00' not in v for v in command) and
          command[0] == spec['python_alias'] and command[1:5] == ['-I', '-S', '-B', '-u'],
          'protected fixed command differs')
    _need(command[-1].replace('\\', '/').endswith('/' + profile['fixed_target']),
          'protected command target differs')
    if profile['platform'] == 'win32':
        _need(spec['bwrap_executable'] is None and spec['unshare_executable'] is None and spec['host_namespaces'] is None and
              spec['host_uid'] is None and spec['host_gid'] is None,
              'Windows reference cannot supply Linux boundary observations')
        paths = {}
        for name in ('repo', 'scratch_directory', 'runtime_prefix', 'python_executable', 'python_alias'):
            value = spec[name]
            _need(type(value) is str and value and '\x00' not in value, 'invalid recorded Windows path')
            path = PureWindowsPath(value)
            _need(path.is_absolute() and '..' not in path.parts and str(path) == value,
                  'recorded Windows path must be absolute and normalized')
            paths[name] = path
        _need(command[-1] == str(paths['repo'] / profile['fixed_target']), 'Windows fixed source target differs')
        _need(not _overlap(paths['repo'], paths['scratch_directory']) and
              not _overlap(paths['runtime_prefix'], paths['scratch_directory']) and
              not _overlap(paths['runtime_prefix'], paths['repo']), 'Windows source, scratch and runtime overlap')
        _need(paths['runtime_prefix'] in paths['python_executable'].parents and
              paths['runtime_prefix'] in paths['python_alias'].parents, 'Windows interpreter outside runtime')
        expected = {str(paths['repo'] / 'scripts/phase17_protected_isolation_probe.py'),
                    str(paths['repo'] / 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/protected_authority_isolation.py'),
                    command[-1], str(paths['python_executable'])}
        _need(type(spec['readonly_files']) is dict and set(spec['readonly_files']) == expected and
              all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v) for v in spec['readonly_files'].values()),
              'Windows source inventory differs')
        _need(type(spec['host_pid']) is int and spec['host_pid'] > 0 and
              type(spec['protected_targets']) is list and 0 < len(spec['protected_targets']) <= 64,
              'Windows host process or protected target inventory differs')
        seen = set()
        for row in spec['protected_targets']:
            _need(type(row) is dict and set(row) == {'path', 'kind'} and
                  row['kind'] in ('file', 'directory') and type(row['path']) is str,
                  'invalid Windows protected target')
            path = PureWindowsPath(row['path'])
            _need(path.is_absolute() and '..' not in path.parts and str(path) == row['path'] and path not in seen,
                  'Windows protected target path differs')
            _need(all(not _overlap(path, mounted) for mounted in
                  (paths['repo'], paths['scratch_directory'], paths['runtime_prefix'])),
                  'Windows protected target overlaps execution input')
            seen.add(path)
        return spec
    paths = {n: _posix(spec[n]) for n in ('repo', 'scratch_directory', 'runtime_prefix',
             'python_executable', 'python_alias', 'bwrap_executable', 'unshare_executable')}
    repo, scratch, runtime = (paths[n] for n in ('repo', 'scratch_directory', 'runtime_prefix'))
    _need(not _overlap(repo, scratch) and not _overlap(repo, runtime) and not _overlap(scratch, runtime),
          'source, scratch and runtime overlap')
    _need(runtime in paths['python_executable'].parents and runtime in paths['python_alias'].parents,
          'interpreter outside pinned runtime')
    _need(command[-1] == str(repo / profile['fixed_target']), 'fixed target not in source root')
    targets = spec['protected_targets']
    _need(type(targets) is list and 0 < len(targets) <= 64, 'protected targets missing or unbounded')
    seen = set()
    for row in targets:
        _need(type(row) is dict and set(row) == {'path', 'kind'} and row['kind'] in ('file', 'directory'),
              'protected target descriptor differs')
        path = _posix(row['path'])
        _need(path not in seen and all(not _overlap(path, mounted) for mounted in
              (repo, scratch, runtime, PurePosixPath('/usr/lib'), PurePosixPath('/usr/lib64'))),
              'protected target duplicates or overlaps a mount')
        seen.add(path)
    expected = {str(repo / 'scripts/phase17_protected_isolation_probe.py'),
                str(repo / 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/protected_authority_isolation.py'),
                str(repo / profile['fixed_target']), str(paths['python_executable'])}
    _need(type(spec['readonly_files']) is dict and set(spec['readonly_files']) == expected and
          all(type(h) is str and re.fullmatch('[0-9a-f]{64}', h) for h in spec['readonly_files'].values()),
          'protected readonly source inventory differs')
    _need(type(spec['host_namespaces']) is dict and set(spec['host_namespaces']) == set(PRIVATE_NAMESPACES) and
          all(type(v) is str and v for v in spec['host_namespaces'].values()), 'host namespace inventory differs')
    _need(all(type(spec[n]) is int and spec[n] >= (1 if n == 'host_pid' else 0)
              for n in ('host_pid', 'host_uid', 'host_gid')), 'host process/principal differs')
    return spec


def _prefix(spec):
    _validate_specification(spec)
    if spec['profile']['platform'] == 'win32':
        return list(spec['command'])
    runtime = PurePosixPath(spec['runtime_prefix'])
    executable = PurePosixPath(spec['python_executable'])
    alias = PurePosixPath(spec['python_alias'])
    # The outer constructor leaves loopback down. bwrap's own loopback setup
    # needs NETLINK_ROUTE, unavailable in some otherwise namespace-capable
    # runtimes. --share-net below shares only this already-private namespace.
    argv = [spec['unshare_executable'], '--user', '--map-current-user', '--net', '--',
            spec['bwrap_executable'], '--unshare-all', '--unshare-user', '--share-net', '--disable-userns',
            '--as-pid-1', '--die-with-parent', '--new-session', '--cap-drop', 'ALL',
            '--clearenv', '--setenv', 'PYTHONDONTWRITEBYTECODE', '1', '--setenv', 'TMPDIR', '/tmp',
            '--ro-bind', '/usr/lib', '/usr/lib', '--symlink', 'usr/lib', '/lib',
            '--ro-bind', '/usr/lib64', '/usr/lib64', '--symlink', 'usr/lib64', '/lib64']
    if runtime != PurePosixPath('/usr'):
        argv += ['--ro-bind', str(runtime), str(runtime)]
    else:
        argv += ['--dir', '/usr/bin', '--ro-bind', str(executable), str(executable)]
        if alias != executable:
            _need(alias.parent == executable.parent, 'interpreter alias parent differs')
            argv += ['--symlink', executable.name, str(alias)]
    argv += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
             '--ro-bind', spec['repo'], spec['repo'],
             '--bind', spec['scratch_directory'], spec['scratch_directory'],
             '--chdir', spec['scratch_directory'], '--', spec['python_executable'], '-I', '-S', '-B', '-u',
             str(PurePosixPath(spec['repo']) / 'scripts/phase17_protected_isolation_probe.py'),
             '--probe-spec', _canonical(spec).decode('ascii'), '--', *spec['command']]
    return argv


def build_command(repo, command, scratch_directory, protected_paths, role):
    """Construct exact launcher argv and specification; start no process."""
    profile = launch_profile(role)
    root, scratch = _absolute(repo, directory=True), _absolute(scratch_directory, directory=True)
    executable = Path(sys.executable).resolve(strict=True)
    runtime = Path(sys.base_prefix).resolve(strict=True)
    _need(type(command) in (list, tuple) and list(command) ==
          [sys.executable, '-I', '-S', '-B', '-u', str(root / TARGETS[role])],
          'caller cannot select protected executable, flags or target')
    targets = []
    for value in protected_paths:
        p = _absolute(value)
        targets.append({'path': str(p), 'kind': 'directory' if p.is_dir() else 'file'})
    readonly = [root / 'scripts/phase17_protected_isolation_probe.py',
                root / 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/protected_authority_isolation.py',
                root / TARGETS[role], executable]
    bwrap = shutil.which('bwrap') if sys.platform == 'linux' else None
    unshare = shutil.which('unshare') if sys.platform == 'linux' else None
    if sys.platform == 'linux' and (bwrap is None or unshare is None):
        raise IsolationUnavailable('Linux protected execution requires bubblewrap and unshare; no unconfined fallback')
    spec = {'schema': 'phase17an.protected-isolation-spec.v1', 'profile': profile,
        'observation_id': uuid.uuid4().hex, 'command': list(command), 'repo': str(root),
        'scratch_directory': str(scratch), 'protected_targets': targets,
        'runtime_prefix': str(runtime), 'python_executable': str(executable), 'python_alias': sys.executable,
        'bwrap_executable': str(Path(bwrap).resolve(strict=True)) if bwrap else None,
        'unshare_executable': str(Path(unshare).resolve(strict=True)) if unshare else None,
        'host_pid': os.getpid(), 'host_uid': os.getuid() if sys.platform == 'linux' else None,
        'host_gid': os.getgid() if sys.platform == 'linux' else None,
        'host_namespaces': _namespaces() if sys.platform == 'linux' else None,
        'readonly_files': {str(p): _sha(p) for p in readonly},
        'shell': False, 'close_fds': True, 'pass_fds': []}
    return _prefix(spec), spec


def specification_from_command(argv):
    _need(type(argv) is list and argv.count('--probe-spec') == 1, 'missing exact protected specification')
    i = argv.index('--probe-spec')
    _need(i + 2 < len(argv) and argv[i + 2] == '--', 'protected specification framing differs')
    spec = json.loads(argv[i + 1])
    _need(_prefix(spec) == argv, 'actual launcher argv differs from protected profile')
    return spec


def _open_close(path, flags):
    fd = os.open(path, flags)
    os.close(fd)


def _denial(name, path, action):
    try:
        action()
    except OSError as error:
        return {'name': name, 'path': str(path), 'denied': True, 'errno': error.errno,
                'exception': type(error).__name__}
    return {'name': name, 'path': str(path), 'denied': False, 'errno': None, 'exception': None}


def _expected_checks(spec):
    result = []
    for i, row in enumerate(spec['protected_targets']):
        p = PurePosixPath(row['path'])
        result += [(f'protected-{i}-exists', str(p)), (f'protected-{i}-read', str(p)),
                   (f'protected-{i}-write', str(p)), (f'protected-{i}-parent-create', str(p))]
        for label, prefix in [('proc1', PurePosixPath('/proc/1/root')),
                              ('outerproc', PurePosixPath('/proc') / str(spec['host_pid']) / 'root')]:
            result.append((f'protected-{i}-{label}-read', str(prefix / p.relative_to('/'))))
    result += [(f'readonly-{i}-write', name) for i, name in enumerate(sorted(spec['readonly_files']))]
    return result


def observe_boundary(spec):
    """Trusted fixed wrapper calls this immediately before exec in that sandbox."""
    _validate_specification(spec)
    _need(sys.platform == 'linux', 'native Linux boundary unavailable')
    checks = []
    for i, row in enumerate(spec['protected_targets']):
        p = Path(row['path'])
        checks += [_denial(f'protected-{i}-exists', p, p.stat),
                   _denial(f'protected-{i}-read', p, lambda p=p: _open_close(p, os.O_RDONLY)),
                   _denial(f'protected-{i}-write', p, lambda p=p: _open_close(p, os.O_WRONLY))]
        parent = p if row['kind'] == 'directory' else p.parent
        probe = parent / ('.phase17an-denial-' + spec['observation_id'])
        def create_probe():
            fd = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd); probe.unlink()
        checks.append(_denial(f'protected-{i}-parent-create', p, create_probe))
        for label, prefix in [('proc1', Path('/proc/1/root')),
                              ('outerproc', Path('/proc') / str(spec['host_pid']) / 'root')]:
            mapped = prefix / p.relative_to('/')
            checks.append(_denial(f'protected-{i}-{label}-read', mapped,
                                 lambda mapped=mapped: _open_close(mapped, os.O_RDONLY)))
    for i, path in enumerate(sorted(spec['readonly_files'])):
        _need(_sha(path) == spec['readonly_files'][path], 'readonly source changed before exec')
        checks.append(_denial(f'readonly-{i}-write', path,
                             lambda path=path: _open_close(path, os.O_WRONLY | os.O_APPEND)))
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    descriptors = {}
    for name in os.listdir('/proc/self/fd'):
        try:
            descriptors[name] = os.readlink('/proc/self/fd/' + name)
        except FileNotFoundError:
            pass
    stat_fields = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()
    result = {'schema': 'phase17an.protected-boundary-observation.v1',
        'observation_id': spec['observation_id'], 'specification_sha256': hashlib.sha256(_canonical(spec)).hexdigest(),
        'profile': spec['profile'], 'pid': os.getpid(), 'uid': os.getuid(), 'gid': os.getgid(),
        'process_start_ticks': int(stat_fields[19]), 'namespaces': _namespaces(),
        'capabilities': {name: status[name].strip() for name in CAPABILITIES},
        'no_new_privs': status['NoNewPrivs'].strip(), 'cwd': os.getcwd(),
        'descriptor_targets': descriptors, 'checks': checks,
        'readonly_files': spec['readonly_files'],
        'network_interfaces': sorted(p.name for p in Path('/sys/class/net').iterdir()) if Path('/sys/class/net').exists() else None,
        'independent_host_principal_established': False, 'physical_attestation': False}
    validate_observation(spec, result)
    return result


def validate_observation(spec, observation):
    _validate_specification(spec)
    if spec['profile']['platform'] == 'win32':
        _need(observation is None, 'Windows reference cannot claim a Linux boundary')
        return True
    fields = {'schema', 'observation_id', 'specification_sha256', 'profile', 'pid', 'uid', 'gid',
              'process_start_ticks', 'namespaces', 'capabilities', 'no_new_privs', 'cwd',
              'descriptor_targets', 'checks', 'readonly_files', 'network_interfaces',
              'independent_host_principal_established', 'physical_attestation'}
    _need(type(observation) is dict and set(observation) == fields and
          observation['schema'] == 'phase17an.protected-boundary-observation.v1', 'boundary observation fields differ')
    _need(observation['observation_id'] == spec['observation_id'] and _canonical(observation['profile']) == _canonical(spec['profile']) and
          observation['specification_sha256'] == hashlib.sha256(_canonical(spec)).hexdigest(), 'boundary specification binding differs')
    _need(observation['pid'] == 1 and type(observation['pid']) is int and
          type(observation['process_start_ticks']) is int and observation['process_start_ticks'] > 0,
          'protected target is not the observed private PID1')
    _need(type(observation['uid']) is int and type(observation['gid']) is int and
          observation['uid'] == spec['host_uid'] and observation['gid'] == spec['host_gid'],
          'namespace principal observation differs')
    _need(type(observation['namespaces']) is dict and set(observation['namespaces']) == set(PRIVATE_NAMESPACES) and
          all(type(observation['namespaces'][n]) is str and observation['namespaces'][n] != spec['host_namespaces'][n]
              for n in PRIVATE_NAMESPACES), 'a required namespace is shared with the host')
    _need(type(observation['capabilities']) is dict and set(observation['capabilities']) == set(CAPABILITIES) and
          all(re.fullmatch('0+', value) for value in observation['capabilities'].values()) and
          observation['no_new_privs'] == '1', 'protected target retains capabilities or privilege gain')
    _need(observation['cwd'] == spec['scratch_directory'] and
          observation['readonly_files'] == spec['readonly_files'], 'protected source/scratch view differs')
    _need(type(observation['descriptor_targets']) is dict and
          set(observation['descriptor_targets']) == {'0', '1', '2'} and
          all(type(v) is str and v for v in observation['descriptor_targets'].values()) and
          observation['descriptor_targets']['0'].startswith('pipe:[') and
          observation['descriptor_targets']['1'].startswith('pipe:['),
          'protected target inherited an extra descriptor or non-pipe protocol channel')
    _need(observation['network_interfaces'] is None, 'unmounted sysfs cannot supply interface observations')
    _need(type(observation['checks']) is list and
          [(v.get('name'), v.get('path')) for v in observation['checks']] == _expected_checks(spec),
          'boundary denial inventory differs')
    for row in observation['checks']:
        _need(set(row) == {'name', 'path', 'denied', 'errno', 'exception'} and row['denied'] is True and
              type(row['errno']) is int and row['errno'] in DENIED and type(row['exception']) is str,
              'protected access or source write was not denied')
    _need(observation['independent_host_principal_established'] is False and
          observation['physical_attestation'] is False, 'boundary scope escalated')
    return True


def parse_boundary_frame(raw):
    _need(type(raw) is bytes and len(raw) <= MAX_BOUNDARY_BYTES and raw.startswith(FRAME_PREFIX) and
          raw.endswith(b'\n'), 'invalid bounded pre-exec boundary frame')
    value = json.loads(raw[len(FRAME_PREFIX):-1])
    _need(raw == FRAME_PREFIX + _canonical(value) + b'\n', 'noncanonical pre-exec boundary frame')
    return value
