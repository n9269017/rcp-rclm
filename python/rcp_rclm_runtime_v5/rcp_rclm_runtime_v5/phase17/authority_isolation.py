"""AM's narrow Linux controller boundary and retained pre-exec observations.

The trusted launcher must use stdout=PIPE, close_fds=True and no pass_fds. It
retains the first framed line outside every writable sandbox mount. The wrapper
then execs the actual client in the same namespaces. This is observed namespace
confinement under kernel/bwrap trust, not an independent host principal, physical
attestation, complete resource containment, or confinement of authority workers.
Networking intentionally shares the host namespace and is not contained.
"""
from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import uuid

PROFILE = 'phase17am.linux-bwrap-controller.v1'
FRAME_PREFIX = 'PHASE17AM_BOUNDARY '
CLIENT_FILES = frozenset({'ca.pem', 'server.pem', 'client.pem', 'client.key', 'commission.json'})
PRIVATE_NAMESPACES = ('mnt', 'pid', 'ipc', 'uts', 'user')
CAPABILITIES = ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')
DENIED = frozenset({errno.ENOENT, errno.EACCES, errno.EROFS})


class IsolationError(ValueError):
    pass


class IsolationUnavailable(IsolationError):
    pass


def _need(value, message):
    if not value:
        raise IsolationError(message)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _absolute(path, *, directory=None):
    path = Path(path)
    _need(path.is_absolute(), 'boundary paths must be absolute')
    _need(path.resolve(strict=True) == path, 'boundary path cannot contain symlinks or dot traversal')
    if directory is not None:
        _need(path.is_dir() == directory, 'unexpected boundary path kind')
    return path


def _overlap(first, second):
    return first == second or first in second.parents or second in first.parents


def _namespaces():
    return {name: os.readlink('/proc/self/ns/' + name) for name in (*PRIVATE_NAMESPACES, 'net')}


def _bundle(path):
    _need({p.name for p in path.iterdir()} == CLIENT_FILES,
          'client bundle must contain exactly ca.pem, server.pem, client.pem, client.key, commission.json')
    for p in path.iterdir():
        _need(p.is_file() and not p.is_symlink(), 'client bundle files must be regular and not symlinks')


def _recorded_path(value):
    _need(type(value) is str and value.startswith('/') and '\\' not in value and '\x00' not in value,
          'recorded Linux profile requires an absolute POSIX path')
    path = PurePosixPath(value)
    _need(path.as_posix() == value and '..' not in path.parts and value != '/',
          'recorded profile path must be normalized and non-root')
    return path


def _profile_prefix(spec):
    """Rebuild every executable/flag/mount from recorded input, without I/O."""
    _need(type(spec) is dict and spec.get('schema') == 'phase17am.controller-isolation-spec.v1'
          and spec.get('profile') == PROFILE, 'unknown recorded isolation profile')
    _need(set(spec) == {'schema', 'profile', 'probe_name', 'command', 'host_pid', 'host_uid', 'host_gid',
                       'host_namespaces', 'repo', 'client_bundle', 'native_output', 'state_directory',
                       'runtime_prefix', 'bwrap_executable', 'wrapper_executable', 'python_alias',
                       'protected_targets', 'readonly_files', 'network_scope', 'authority_workers_confined',
                       'independent_principal_established'}, 'recorded isolation specification keys differ')
    paths = {name: _recorded_path(spec[name]) for name in (
        'repo', 'client_bundle', 'native_output', 'state_directory', 'runtime_prefix',
        'bwrap_executable', 'wrapper_executable', 'python_alias')}
    repo, client, native, state, runtime = (paths[n] for n in (
        'repo', 'client_bundle', 'native_output', 'state_directory', 'runtime_prefix'))
    _need(not _overlap(repo, client) and not _overlap(repo, native) and not _overlap(repo, state)
          and not _overlap(client, native) and not _overlap(client, state) and native != state,
          'recorded source/client/writable views overlap')
    _need(all(not _overlap(p, runtime) for p in (repo, client, native, state)),
          'recorded runtime prefix overlaps an application mount')
    _need(runtime in paths['wrapper_executable'].parents and runtime in paths['python_alias'].parents,
          'recorded interpreter lies outside the runtime prefix')
    _need(type(spec['command']) is list and len(spec['command']) >= 2
          and all(type(x) is str and x and '\x00' not in x for x in spec['command'])
          and spec['command'][0] == str(paths['python_alias']), 'recorded client executable/arguments differ')
    _need(type(spec['probe_name']) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', spec['probe_name']),
          'recorded probe name invalid')
    _need(type(spec['protected_targets']) is list and spec['protected_targets'], 'recorded protected targets missing')
    protected = []
    for target in spec['protected_targets']:
        _need(type(target) is dict and set(target) == {'path', 'kind'} and target['kind'] in ('file', 'directory'),
              'recorded protected target invalid')
        p = _recorded_path(target['path'])
        _need(all(not _overlap(p, mounted) for mounted in (repo, client, native, state, runtime,
                  PurePosixPath('/usr/lib'), PurePosixPath('/usr/lib64'))),
              'recorded protected target overlaps a mounted view')
        protected.append(p)
    _need(len(set(protected)) == len(protected), 'recorded protected targets duplicate')
    _need(all(PurePosixPath(alias) not in p.parents and p != PurePosixPath(alias)
              for alias in ['/repo', '/client', '/client-state', '/native']
              for p in (repo, client, native, state)), 'recorded path collides with fixed alias')
    readonly = spec['readonly_files']
    expected_readonly = {str(repo / 'scripts/phase17_authority_isolation_probe.py'),
                         str(repo / 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/authority_isolation.py'),
                         str(client / 'client.key')}
    _need(type(readonly) is dict and set(readonly) == expected_readonly
          and all(type(h) is str and re.fullmatch(r'[0-9a-f]{64}', h) for h in readonly.values()),
          'recorded read-only source/key inventory differs')
    _need(spec['network_scope'] == 'shared_host_namespace_unrestricted'
          and spec['authority_workers_confined'] is False and spec['independent_principal_established'] is False,
          'recorded boundary scope differs')
    _need(all(type(spec[n]) is int and spec[n] >= (1 if n == 'host_pid' else 0)
              for n in ('host_pid', 'host_uid', 'host_gid')), 'recorded host principal/process invalid')
    _need(type(spec['host_namespaces']) is dict
          and set(spec['host_namespaces']) == {*PRIVATE_NAMESPACES, 'net'}
          and all(type(v) is str and v for v in spec['host_namespaces'].values()), 'recorded host namespace inventory invalid')
    argv = [str(paths['bwrap_executable']), '--unshare-all', '--unshare-user', '--share-net',
            '--disable-userns', '--die-with-parent', '--new-session', '--cap-drop', 'ALL',
            '--clearenv', '--setenv', 'PYTHONDONTWRITEBYTECODE', '1', '--setenv', 'PATH', '/usr/bin',
            '--ro-bind', '/usr/lib', '/usr/lib', '--symlink', 'usr/lib', '/lib',
            '--ro-bind', '/usr/lib64', '/usr/lib64', '--symlink', 'usr/lib64', '/lib64']
    if runtime != PurePosixPath('/usr'):
        argv += ['--ro-bind', str(runtime), str(runtime)]
    else:
        executable = paths['wrapper_executable']
        argv += ['--dir', '/usr/bin', '--ro-bind', str(executable), str(executable)]
        if paths['python_alias'] != executable:
            _need(paths['python_alias'].parent == executable.parent, 'recorded interpreter alias has a different parent')
            argv += ['--symlink', executable.name, str(paths['python_alias'])]
    argv += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp']
    for path, alias, writable in [(repo, '/repo', False), (client, '/client', False),
                                   (native, '/native', True), (state, '/client-state', True)]:
        op = '--bind' if writable else '--ro-bind'
        argv += [op, str(path), str(path), op, str(path), alias]
    return argv + ['--chdir', str(repo), '--', str(paths['wrapper_executable']), '-I', '-B',
                   str(repo / 'scripts/phase17_authority_isolation_probe.py')]


def build_client_command(repo, client_bundle, native_output, command, *,
                         state_directory=None, protected_paths=(), probe_name='client'):
    """Return fail-closed bwrap argv; this function starts no process.

    All four mounted directories must already exist. state_directory defaults to
    native_output/client-state, which the caller must also create. protected_paths
    must identify existing authority files/directories outside every mounted tree.
    Paths in the actual command remain their original absolute paths. The fixed
    /repo, /client, /client-state and /native aliases are available as well.
    """
    if sys.platform != 'linux':
        raise IsolationUnavailable('Linux controller namespace profile unavailable on this platform')
    bwrap = shutil.which('bwrap')
    if bwrap is None:
        raise IsolationUnavailable('bubblewrap is required; no unconfined fallback is permitted')
    repo = _absolute(repo, directory=True)
    client = _absolute(client_bundle, directory=True)
    native = _absolute(native_output, directory=True)
    state = _absolute(native / 'client-state' if state_directory is None else state_directory, directory=True)
    _bundle(client)
    _need(isinstance(probe_name, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', probe_name), 'invalid probe name')
    _need(isinstance(command, (list, tuple)) and len(command) >= 2
          and all(isinstance(x, str) and x and '\x00' not in x for x in command), 'invalid actual client command')
    executable = Path(sys.executable).resolve(strict=True)
    _need(Path(command[0]).resolve(strict=True) == executable, 'client must use the captured host Python interpreter')
    runtime = Path(sys.base_prefix).resolve(strict=True)
    _need(runtime in executable.parents, 'host interpreter lies outside captured runtime prefix')
    wrapper = repo / 'scripts/phase17_authority_isolation_probe.py'
    module = repo / 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/authority_isolation.py'
    _need(wrapper.is_file() and module.is_file(), 'fixed isolation wrapper/source missing')
    _need(not _overlap(repo, client) and not _overlap(repo, native) and not _overlap(repo, state)
          and not _overlap(client, native) and not _overlap(client, state), 'source/client/writable boundary trees overlap')
    _need(native != state, 'native output and client state must be distinct directories')
    targets = []
    for value in protected_paths:
        p = _absolute(value)
        _need(p.is_dir() or p.is_file(), 'protected targets must be ordinary files/directories')
        _need(all(not _overlap(p, mounted) for mounted in [repo, client, native, state, runtime, Path('/usr/lib'), Path('/usr/lib64')]),
              'protected authority target overlaps a mounted view')
        targets.append({'path': str(p), 'kind': 'directory' if p.is_dir() else 'file'})
    _need(targets and len({x['path'] for x in targets}) == len(targets), 'protected targets must be nonempty and unique')
    _need(all(Path(alias) not in p.parents and p != Path(alias) for alias in ['/repo', '/client', '/client-state', '/native']
              for p in [repo, client, native, state]), 'host paths collide with fixed aliases')
    readonly = [wrapper, module, client / 'client.key']
    spec = {'schema': 'phase17am.controller-isolation-spec.v1', 'profile': PROFILE,
            'probe_name': probe_name, 'command': list(command), 'host_pid': os.getpid(),
            'host_uid': os.getuid(), 'host_gid': os.getgid(), 'host_namespaces': _namespaces(),
            'repo': str(repo), 'client_bundle': str(client), 'native_output': str(native),
            'state_directory': str(state), 'protected_targets': targets,
            'runtime_prefix': str(runtime), 'bwrap_executable': str(Path(bwrap).resolve(strict=True)),
            'wrapper_executable': str(executable), 'python_alias': str(Path(command[0])),
            'readonly_files': {str(p): _sha(p) for p in readonly},
            'network_scope': 'shared_host_namespace_unrestricted',
            'authority_workers_confined': False, 'independent_principal_established': False}
    return _profile_prefix(spec) + ['--probe-spec', _canonical(spec).decode('ascii'), '--', *command]


def specification_from_command(argv):
    _need(isinstance(argv, (list, tuple)) and argv.count('--probe-spec') == 1, 'invalid boundary command')
    i = argv.index('--probe-spec')
    _need(i + 2 < len(argv) and argv[i + 2] == '--', 'missing boundary command separator')
    spec = json.loads(argv[i + 1])
    _need(spec.get('schema') == 'phase17am.controller-isolation-spec.v1' and spec.get('profile') == PROFILE,
          'unknown boundary specification')
    _need(spec['command'] == list(argv[i + 3:]), 'client command differs from boundary specification')
    expected = _profile_prefix(spec) + ['--probe-spec', _canonical(spec).decode('ascii'), '--', *spec['command']]
    _need(list(argv) == expected, 'exact boundary executable/flags/mount profile differs')
    return spec


def _denial(name, path, op):
    try:
        op()
    except OSError as e:
        return {'name': name, 'path': str(path), 'denied': True, 'errno': e.errno,
                'exception': type(e).__name__}
    return {'name': name, 'path': str(path), 'denied': False, 'errno': None, 'exception': None}


def _open_close(path, flags):
    fd = os.open(path, flags)
    os.close(fd)


def _replace_probe(source, target):
    # Never replace an authority file: the target is a fresh random sibling.
    _need(not target.exists(), 'replace probe target unexpectedly exists')
    os.replace(source, target)
    target.unlink()


def _expected_checks(spec):
    checks = []
    for i, target in enumerate(spec['protected_targets']):
        path = PurePosixPath(target['path'])
        checks += [(f'protected-{i}-exists', str(path)), (f'protected-{i}-read', str(path)),
                   (f'protected-{i}-write', str(path)), (f'protected-{i}-replace-parent', str(path)),
                   (f'protected-{i}-proc1-read', str(PurePosixPath('/proc/1/root') / path.relative_to('/'))),
                   (f'protected-{i}-outerproc-read', str(PurePosixPath('/proc') / str(spec['host_pid']) / 'root' / path.relative_to('/'))),
                   (f'protected-{i}-dotdot-read', str(PurePosixPath('/repo/../..') / path.relative_to('/')))]
    checks += [(f'readonly-{i}-write', path) for i, path in enumerate(spec['readonly_files'])]
    return checks


def observe_boundary(spec):
    """Executed by the pinned wrapper before it execs the actual client."""
    _need(sys.platform == 'linux', 'boundary observations require Linux')
    _bundle(Path(spec['client_bundle']))
    checks = []
    marker = uuid.uuid4().hex
    state = Path(spec['state_directory'])
    for i, target in enumerate(spec['protected_targets']):
        path = Path(target['path'])
        checks.append(_denial(f'protected-{i}-exists', path, path.stat))
        checks.append(_denial(f'protected-{i}-read', path, lambda p=path: _open_close(p, os.O_RDONLY)))
        # O_WRONLY without O_CREAT cannot modify existing authority bytes.
        checks.append(_denial(f'protected-{i}-write', path, lambda p=path: _open_close(p, os.O_WRONLY)))
        parent = path if target['kind'] == 'directory' else path.parent
        src = state / ('.probe-source-' + marker + '-' + str(i))
        dest = parent / ('.probe-target-' + marker + '-' + str(i))
        src.write_bytes(b'boundary probe')
        try:
            result = _denial(f'protected-{i}-replace-parent', path, lambda: _replace_probe(src, dest))
            result['replacement_target'] = str(dest)
            checks.append(result)
        finally:
            if src.exists(): src.unlink()
        for label, prefix in [('proc1', Path('/proc/1/root')),
                              ('outerproc', Path('/proc') / str(spec['host_pid']) / 'root'),
                              ('dotdot', Path('/repo/../..'))]:
            mapped = prefix / path.relative_to('/')
            checks.append(_denial(f'protected-{i}-{label}-read', mapped, lambda p=mapped: _open_close(p, os.O_RDONLY)))
    for i, path in enumerate(spec['readonly_files']):
        checks.append(_denial(f'readonly-{i}-write', path, lambda p=path: _open_close(p, os.O_WRONLY | os.O_APPEND)))
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    descriptor_targets = {}
    for p in Path('/proc/self/fd').iterdir():
        try: descriptor_targets[p.name] = os.readlink(p)
        except FileNotFoundError: pass
    libc = ctypes.CDLL(None, use_errno=True)
    nested_rc = libc.unshare(0x10000000)
    nested_errno = ctypes.get_errno()
    return {'schema': 'phase17am.controller-isolation-observation.v1', 'profile': PROFILE,
            'probe_name': spec['probe_name'], 'spec_sha256': hashlib.sha256(_canonical(spec)).hexdigest(),
            'command': spec['command'], 'pid': os.getpid(), 'uid': os.getuid(), 'gid': os.getgid(),
            'namespaces': _namespaces(), 'uid_map': Path('/proc/self/uid_map').read_text(),
            'proc_pids': sorted(int(p.name) for p in Path('/proc').iterdir() if p.name.isdigit()),
            'security_status': {k: status[k].strip() for k in (*CAPABILITIES, 'NoNewPrivs', 'Seccomp')},
            'descriptor_targets': descriptor_targets, 'checks': checks,
            'readonly_hashes': {p: _sha(p) for p in spec['readonly_files']},
            'nested_user_namespace': {'returncode': nested_rc, 'errno': nested_errno},
            'network_scope': spec['network_scope'], 'authority_workers_confined': False,
            'independent_principal_established': False}


def verify_boundary_observation(record, spec):
    """Check the original host-retained first-line observation without execution."""
    _profile_prefix(spec)
    _need(record.get('schema') == 'phase17am.controller-isolation-observation.v1'
          and record.get('profile') == PROFILE == spec.get('profile'), 'unknown boundary observation')
    _need(record.get('probe_name') == spec['probe_name']
          and record.get('spec_sha256') == hashlib.sha256(_canonical(spec)).hexdigest()
          and record.get('command') == spec['command'], 'boundary observation is not bound to launch')
    _need(record.get('uid') == spec['host_uid'] and record.get('gid') == spec['host_gid'], 'unexpected mapped principal')
    _need(all(record['namespaces'][n] != spec['host_namespaces'][n] for n in PRIVATE_NAMESPACES),
          'required private namespace was shared')
    _need(record['namespaces']['net'] == spec['host_namespaces']['net']
          and record['network_scope'] == 'shared_host_namespace_unrestricted', 'network scope changed or overstated')
    _need(all(record['security_status'][n] == '0000000000000000' for n in CAPABILITIES)
          and record['security_status']['NoNewPrivs'] == '1', 'capability or privilege restriction missing')
    _need(record['pid'] in record['proc_pids'] and set(record['proc_pids']) == {1, record['pid']},
          'unexpected processes visible in private PID namespace')
    _need(set(record['descriptor_targets']) == {'0', '1', '2'}, 'unexpected inherited descriptor')
    _need(record['descriptor_targets']['1'].startswith('pipe:['), 'trusted launcher must capture boundary frame through a pipe')
    _need(record['nested_user_namespace']['returncode'] == -1
          and record['nested_user_namespace']['errno'] in {errno.EPERM, errno.ENOSPC}, 'nested user namespace creation was not refused')
    _need(record['readonly_hashes'] == spec['readonly_files'], 'read-only source or client credential differs')
    expected = _expected_checks(spec)
    _need([(x['name'], x['path']) for x in record['checks']] == expected, 'boundary denial inventory differs')
    for item in record['checks']:
        _need(item['denied'] is True and item['errno'] in DENIED, 'protected path access was not denied')
        if item['name'].startswith('readonly-'):
            _need(item['errno'] == errno.EROFS, 'read-only file was not protected by a read-only mount')
    _need(record['authority_workers_confined'] is False and record['independent_principal_established'] is False,
          'boundary observation overclaims its scope')
    return {'profile': PROFILE, 'probe_name': spec['probe_name'], 'checked': True,
            'denial_checks': len(expected), 'network_scope': 'shared_host_namespace_unrestricted',
            'authority_workers_confined': False, 'independent_principal_established': False}


def parse_boundary_frame(line, spec):
    if isinstance(line, bytes): line = line.decode('utf-8')
    _need(isinstance(line, str) and line.startswith(FRAME_PREFIX) and line.endswith('\n'), 'missing complete boundary frame')
    record = json.loads(line[len(FRAME_PREFIX):])
    verify_boundary_observation(record, spec)
    return record


def wrapper_main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    _need(len(args) >= 4 and args[0] == '--probe-spec' and args[2] == '--', 'invalid isolation wrapper arguments')
    spec = json.loads(args[1])
    _need(args[3:] == spec['command'], 'actual command differs from pinned pre-exec command')
    record = observe_boundary(spec)
    verify_boundary_observation(record, spec)
    sys.stdout.write(FRAME_PREFIX + _canonical(record).decode('ascii') + '\n')
    sys.stdout.flush()
    os.execv(spec['command'][0], spec['command'])
    raise AssertionError('execv returned')
