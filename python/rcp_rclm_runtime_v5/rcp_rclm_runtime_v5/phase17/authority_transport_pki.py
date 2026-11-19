"""Fresh reference TLS identities. Private material is never publication evidence.

OpenSSL is an identified external dependency, not a verified implementation.
This local CA does not authenticate an independent production issuer.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import secrets
import shutil
import ssl
import subprocess
import time

from .resource_ledger import canonical


def find_openssl(explicit=None):
    candidates = []
    if explicit is not None:
        candidates.append(Path(explicit))
    else:
        found = shutil.which('openssl')
        if found:
            candidates.append(Path(found))
        git = shutil.which('git')
        if git:
            for parent in Path(git).resolve().parents:
                candidates.extend((parent / 'usr/bin/openssl.exe', parent / 'mingw64/bin/openssl.exe'))
        for variable in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
            value = os.environ.get(variable)
            if value:
                candidates.extend((Path(value) / 'Git/usr/bin/openssl.exe',
                                   Path(value) / 'Programs/Git/usr/bin/openssl.exe'))
    for path in candidates:
        if path.is_file():
            return path.resolve()
    raise ValueError('OpenSSL executable required; no identity fixture is substituted')


def certificate_der(path):
    return ssl.PEM_cert_to_DER_cert(Path(path).read_text(encoding='ascii'))


def generate_reference_pki(directory, openssl=None):
    """Create a new private directory with fresh reference server/client keys.

    The two negative-control client identities are distinct: one shares the
    authorized CA but is not pinned, and the other uses a foreign CA.
    Return paths and original command observations, never private key bytes.
    """
    root = Path(directory).absolute()
    if root.exists():
        raise ValueError('reference PKI directory must be absent')
    root.mkdir(parents=True, mode=0o700)
    executable = find_openssl(openssl)
    commands = []
    records = root / 'command-records'
    records.mkdir(mode=0o700)

    def run(*arguments):
        command = [str(executable), *map(str, arguments)]
        begin = time.monotonic_ns()
        observation = {'command': command, 'cwd': str(root), 'returncode': None,
            'stdout_hex': '', 'stderr_hex': '', 'native_wait_completed': False,
            'shell': False, 'timed_out': False, 'error_type': None}
        process = None
        try:
            process = subprocess.Popen(command, cwd=root, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, close_fds=True)
            observation['child_pid'] = process.pid
            try:
                output, error = process.communicate(timeout=60)
            except subprocess.TimeoutExpired:
                observation['timed_out'] = True
                process.kill()
                output, error = process.communicate(timeout=10)
            observation.update({'returncode': process.returncode, 'stdout_hex': output.hex(),
                                'stderr_hex': error.hex(), 'native_wait_completed': True})
        except BaseException as failure:
            observation['error_type'] = type(failure).__name__
            raise
        finally:
            observation['elapsed_ns'] = time.monotonic_ns() - begin
            path = records / ('command-%04d.json' % len(commands))
            with path.open('xb') as stream:
                stream.write(canonical(observation)); stream.flush(); os.fsync(stream.fileno())
            commands.append(observation)
        if observation['returncode'] or observation['timed_out']:
            raise ValueError('reference certificate command failed; private directory retained')

    run('version')

    def ca(name, label):
        run('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-sha256',
            '-keyout', root / (name + '.key'), '-out', root / (name + '.pem'),
            '-days', '2', '-subj', '/CN=' + label,
            '-addext', 'basicConstraints=critical,CA:TRUE',
            '-addext', 'keyUsage=critical,keyCertSign,cRLSign')

    def leaf(name, issuer, label, server=False):
        extensions = ('basicConstraints=critical,CA:FALSE\n'
            'keyUsage=critical,digitalSignature,keyEncipherment\n'
            'extendedKeyUsage=' + ('serverAuth' if server else 'clientAuth') + '\n'
            'subjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid,issuer\n')
        if server:
            extensions += 'subjectAltName=DNS:localhost,IP:127.0.0.1\n'
        (root / (name + '.ext')).write_text(extensions, encoding='ascii')
        run('req', '-new', '-newkey', 'rsa:2048', '-nodes', '-sha256',
            '-keyout', root / (name + '.key'), '-out', root / (name + '.csr'),
            '-subj', '/CN=' + label)
        run('x509', '-req', '-in', root / (name + '.csr'), '-CA', root / (issuer + '.pem'),
            '-CAkey', root / (issuer + '.key'), '-set_serial', str(secrets.randbits(128) + 1),
            '-out', root / (name + '.pem'), '-days', '2', '-sha256',
            '-extfile', root / (name + '.ext'))

    ca('ca', 'Phase17AM reference CA')
    leaf('server', 'ca', 'localhost', server=True)
    leaf('client', 'ca', 'Phase17AM admitted controller')
    leaf('other-client', 'ca', 'Phase17AM unauthorized same-CA client')
    ca('foreign-ca', 'Phase17AM foreign reference CA')
    leaf('foreign-client', 'foreign-ca', 'Phase17AM foreign client')
    private = {}
    public = {}
    identities = {}
    for name in ('ca', 'server', 'client', 'other-client', 'foreign-ca', 'foreign-client'):
        key = root / (name + '.key')
        os.chmod(key, 0o600)
        private[name] = str(key)
        public[name] = str(root / (name + '.pem'))
        identities[name] = {'pem_sha256': hashlib.sha256(Path(public[name]).read_bytes()).hexdigest(),
                            'der_sha256': hashlib.sha256(certificate_der(public[name])).hexdigest()}
    return {'schema': 'phase17am.reference-pki-generation.v1', 'directory': str(root),
        'openssl_path': str(executable), 'openssl_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
        'commands': commands, 'command_records_directory': str(records),
        'public': public, 'private': private, 'identities': identities,
        'independent_production_issuer_established': False,
        'private_material_is_publication_evidence': False}
