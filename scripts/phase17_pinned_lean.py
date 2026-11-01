"""Phase 17E: explicit pinned-tool setup and real capability-proof execution.

No preparation-mode success. --allow-network permits setup only. It downloads an
exact official portable Windows toolchain and locked Git dependencies; it never
runs lake update. Verification uses the prepared workspace and does not authorize
promotion, a concrete Gate E transition, or complete Phase 17 closure.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import uuid
import zipfile

VERSION = '4.31.0'
TOOLCHAIN = 'leanprover/lean4:v' + VERSION
PINS_REL = 'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/lean_root_pins.json'
PINS_SHA = 'ec2226ce520783d965a8e8370dcccce550751e90935fb79ba76ebc137bfc658f'
ROOT_PROJECT = 'lean/rcp_rclm_formal_core_v4'
WIN_ASSET = {
    'url': 'https://github.com/leanprover/lean4/releases/download/v4.31.0/lean-4.31.0-windows.zip',
    'sha256': 'f73208f53dcdc901745cb35fc916c476e0e18ed0856937740e46d07848f57f19',
    'size': 823782593, 'prefix': 'lean-4.31.0-windows',
}
ALLOWED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}
ROOT_NAMES = (
    'RcpRclmFormalCoreV4.Autonomous.autonomous_accepted_step_sound',
    'RcpRclmFormalCoreV4.Autonomous.recursive_productivity_retained',
    'RcpRclmFormalCoreV4.Autonomous.recursive_productivity_strictly_expands_when_witnessed',
)
FALSE_CLAIMS = dict(phase17_exit_closed=False, gate_e_closed=False, egc0_started=False,
                    root_transition_verified=False, recursive_productivity_recertified=False,
                    full_frontier_recertified=False, promotion_authorized=False,
                    promotion_performed=False, github_hosted_ci_passed=False,
                    cross_platform_validation=False)


class VerificationBlocked(ValueError):
    """A prerequisite or exact identity is absent; never a simulated pass."""


def need(ok: bool, message: str) -> None:
    if not ok:
        raise VerificationBlocked(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def save(path: Path, value: object) -> None:
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    with path.open('xb') as handle:
        handle.write(raw)


def regular(path: Path) -> bytes:
    need(path.is_file() and not path.is_symlink(), 'missing or linked file: ' + str(path))
    need(path.stat().st_nlink == 1, 'hard-linked file not accepted: ' + str(path))
    return path.read_bytes()


def no_links(path: Path) -> None:
    for part in (path, *path.parents):
        need(not part.is_symlink() and not (hasattr(part, 'is_junction') and part.is_junction()),
             'linked/junction path not accepted: ' + str(part))


def relative(name: str) -> str:
    need(type(name) is str and name and len(name) < 1024, 'invalid relative name')
    p = PurePosixPath(name)
    need(not p.is_absolute() and p.as_posix() == name and '..' not in p.parts and
         not any(c in name for c in '\\:\0\r\n'), 'unsafe relative name')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(i) for i in range(1, 10)),
                *('LPT'+str(i) for i in range(1, 10))}
    need(all(not s.endswith((' ', '.')) and s.split('.')[0].upper() not in reserved
             for s in p.parts), 'nonportable name')
    return name


def read_pins(repository: Path) -> dict:
    raw = regular(repository / PINS_REL).replace(b'\r\n', b'\n')
    need(sha(raw) == PINS_SHA, 'formal root pin table changed')
    pins = json.loads(raw)
    need(pins['toolchain'] == TOOLCHAIN and len(pins['files']) == 72, 'root policy differs')
    return pins


def verify_root(repository: Path, pins: dict) -> dict:
    result = {}
    for rel, expected in pins['files'].items():
        relative(rel)
        path = repository / rel
        no_links(path)
        raw = regular(path)
        need(sha(raw.replace(b'\r\n', b'\n')) == expected, 'root source differs: ' + rel)
        result[rel] = expected
    for version in (2, 3, 4):
        root = repository / f'lean/rcp_rclm_formal_core_v{version}'
        wanted = {p for p in pins['files'] if p.startswith(root.relative_to(repository).as_posix() + '/')}
        found = set()
        for path in root.rglob('*'):
            parts = path.relative_to(root).parts
            if '.lake' in parts or '.git' in parts:
                continue
            no_links(path)
            if path.is_file():
                found.add(path.relative_to(repository).as_posix())
        need(found == wanted, 'unexpected formal root source set')
        need(not (root / '.lake/package-overrides.json').exists(), 'Lake package override forbidden')
    return result


def copy_root(repository: Path, destination: Path, pins: dict) -> None:
    verify_root(repository, pins)
    need(not destination.exists(), 'new formal workspace required')
    no_links(destination.parent)
    destination.mkdir()
    for rel in pins['files']:
        path = destination / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(regular(repository / rel).replace(b'\r\n', b'\n'))
    verify_root(destination, pins)


def locked_dependencies(workspace: Path) -> tuple[dict, ...]:
    lock = json.loads(regular(workspace / ROOT_PROJECT / 'lake-manifest.json'))
    entries = tuple(x for x in lock['packages'] if x['type'] == 'git')
    need(len(entries) == 9 and len({x['name'] for x in entries}) == 9, 'dependency set differs')
    for x in entries:
        need(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', x['name']) is not None, 'unsafe dependency name')
        url = urlparse(x['url'])
        need(url.scheme == 'https' and url.netloc == 'github.com' and
             re.fullmatch(r'/(leanprover|leanprover-community)/[A-Za-z0-9_.-]+', url.path) is not None
             and not url.query and not url.fragment, 'unapproved dependency origin')
        need(re.fullmatch(r'[0-9a-f]{40}', x['rev']) is not None, 'unlocked dependency revision')
    return entries


def clean_environment(toolchain: Path, git_executable: Path | None = None, *, network: bool = False) -> dict:
    allow = {'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'TEMP', 'TMP', 'HOME', 'USERPROFILE',
             'LOCALAPPDATA', 'APPDATA', 'LANG', 'LC_ALL'}
    env = {k:v for k,v in os.environ.items() if k.upper() in allow}
    paths = [str(toolchain / 'bin')]
    if git_executable is not None:
        paths.append(str(git_executable.parent))
        # Git for Windows supplies curl and its TLS support here.
        mingw = git_executable.parent.parent / 'mingw64/bin'
        if mingw.is_dir():
            paths.append(str(mingw))
    if os.name == 'nt' and env.get('SYSTEMROOT'):
        paths.append(str(Path(env['SYSTEMROOT'])/'System32'))
    paths.append(os.defpath)
    env.update(PATH=os.pathsep.join(paths), ELAN_TOOLCHAIN=TOOLCHAIN,
               GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               LAKE_NO_CACHE='true', LAKE_ARTIFACT_CACHE='false', PYTHONDONTWRITEBYTECODE='1')
    # Not an OS network sandbox; offline means no setup/download commands are requested.
    if network:
        env['LAKE_NO_CACHE'] = 'true'  # explicit mathlib cache executable is separate
    return env


class Recorder:
    def __init__(self, output: Path):
        self.output = output
        self.commands: list[dict] = []
        (output / 'commands').mkdir()

    def run(self, label: str, argv: list[str], cwd: Path, env: dict, timeout: int = 600) -> dict:
        need(re.fullmatch(r'[a-z0-9-]+', label) is not None, 'unsafe command label')
        name = f'{len(self.commands):03d}-{label}'
        stdout = self.output / 'commands' / (name + '.stdout.txt')
        stderr = self.output / 'commands' / (name + '.stderr.txt')
        start = utc(); clock = time.monotonic_ns(); problem = None
        with stdout.open('xb') as out, stderr.open('xb') as err:
            try:
                result = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                        stdout=out, stderr=err, timeout=timeout, check=False)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code, problem = -999, 'timeout'
            except OSError as exc:
                code, problem = -998, type(exc).__name__
        row = dict(label=label, argv=argv, cwd=str(cwd), returncode=code, problem=problem,
                   started_at_utc=start, finished_at_utc=utc(), elapsed_ns=time.monotonic_ns()-clock,
                   stdout_path=stdout.relative_to(self.output).as_posix(),
                   stderr_path=stderr.relative_to(self.output).as_posix(),
                   stdout_sha256=file_sha(stdout), stderr_sha256=file_sha(stderr))
        self.commands.append(row)
        print(f'{label}: exit {code}', flush=True)
        return row

    def text(self, row: dict, channel: str) -> str:
        path = self.output / row[channel + '_path']
        need(path.stat().st_size <= 16*1024*1024, 'command log exceeds inspection bound')
        return path.read_text(encoding='utf-8', errors='replace')

    def checked(self, *args, **kwargs) -> dict:
        row = self.run(*args, **kwargs)
        need(row['returncode'] == 0, row['label'] + ' failed; see ' + str(self.output / 'commands'))
        return row


def download_toolchain(cache: Path, *, allow_network: bool) -> Path:
    need(allow_network, 'pinned Lean missing; explicit --allow-network is required for download')
    need(platform.system() == 'Windows' and platform.machine().upper() in ('AMD64', 'X86_64'),
         'automatic portable-tool installation supports Windows x64 only; supply --toolchain-root on other platforms')
    archive = cache / 'lean-4.31.0-windows.zip'
    if archive.exists():
        need(archive.stat().st_size == WIN_ASSET['size'] and file_sha(archive) == WIN_ASSET['sha256'],
             'cached tool archive differs; preserved for inspection')
    else:
        partial = cache / 'lean-4.31.0-windows.zip.partial'
        need(not partial.exists(), 'partial download retained; inspect it before retrying setup')
        print('Downloading pinned official Lean ZIP ('+str(WIN_ASSET['size'])+' bytes) into '+str(cache), flush=True)
        req = Request(WIN_ASSET['url'], headers={'User-Agent':'RCP-RCLM-Phase17E/1'})
        h = hashlib.sha256(); size = 0
        with urlopen(req, timeout=90) as response, partial.open('xb') as out:
            final = urlparse(response.geturl())
            need(final.scheme == 'https' and (final.netloc == 'github.com' or
                 final.netloc.endswith('.githubusercontent.com')), 'unexpected download redirect')
            while True:
                data = response.read(1024*1024)
                if not data: break
                size += len(data); need(size <= WIN_ASSET['size'], 'oversized tool download')
                h.update(data); out.write(data)
                if size // (64*1024*1024) != (size-len(data)) // (64*1024*1024):
                    print('Lean download bytes: '+str(size)+' / '+str(WIN_ASSET['size']),flush=True)
        need(size == WIN_ASSET['size'] and h.hexdigest() == WIN_ASSET['sha256'], 'official tool archive checksum mismatch')
        partial.rename(archive)
    extracted = cache / 'portable'
    if extracted.exists():
        marker = extracted / 'verified-download.json'
        need(marker.is_file() and json.loads(regular(marker)) == WIN_ASSET, 'incomplete portable extraction retained')
        return extracted / WIN_ASSET['prefix']
    extracted.mkdir()
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist(); names = set(); size = 0
        need(len(infos) <= 150000, 'tool archive member bound')
        # Validate all members before any extraction; original name, not sanitized filename.
        for info in infos:
            raw = info.orig_filename
            need(raw == info.filename and '\x00' not in raw, 'normalized tool archive name')
            name = relative(raw.rstrip('/'))
            need(name == WIN_ASSET['prefix'] or name.startswith(WIN_ASSET['prefix'] + '/'), 'unexpected archive prefix')
            need(name.casefold() not in names, 'duplicate/case-colliding tool member')
            names.add(name.casefold()); size += info.file_size
            mode = info.external_attr >> 16
            need(not stat.S_ISLNK(mode) and not info.flag_bits & 1, 'linked/encrypted tool member')
            need(size <= 12*1024**3 and info.file_size <= 1024**3, 'tool extraction bound')
        for info in infos:
            target = extracted / info.filename
            if info.is_dir(): target.mkdir(parents=True, exist_ok=True); continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, target.open('xb') as dst:
                shutil.copyfileobj(src, dst, 1024*1024)
    save(extracted / 'verified-download.json', WIN_ASSET)
    return extracted / WIN_ASSET['prefix']


def choose_toolchain(cache: Path, supplied: Path | None, *, allow_network: bool) -> Path:
    if supplied is not None:
        tool = supplied.resolve()
    else:
        elan = Path(os.environ.get('ELAN_HOME', str(Path.home()/'.elan')))
        need(elan.is_absolute(), 'ELAN_HOME must be absolute')
        installed = elan/'toolchains'/('leanprover--lean4---v'+VERSION)
        suffix = '.exe' if os.name == 'nt' else ''
        tool = installed if (installed/'bin'/('lean'+suffix)).is_file() else download_toolchain(cache, allow_network=allow_network)
    no_links(tool)
    suffix = '.exe' if os.name == 'nt' else ''
    for name in ('lean', 'lake'):
        need((tool/'bin'/(name+suffix)).is_file(), 'missing pinned tool executable: '+name)
    return tool.resolve()


def dependency_state(workspace: Path, git: Path, env: dict) -> dict:
    result = {}
    for entry in locked_dependencies(workspace):
        path = workspace/ROOT_PROJECT/'.lake/packages'/entry['name']
        no_links(path)
        need((path/'.git').is_dir(), 'locked dependency missing: '+entry['name'])
        def read(*args):
            return subprocess.check_output([str(git), '--no-optional-locks', '-C', str(path), *args],
                                           env=env, stderr=subprocess.PIPE, timeout=60).decode('utf-8').strip()
        need(read('rev-parse','HEAD') == entry['rev'], 'dependency revision differs: '+entry['name'])
        need(read('remote','get-url','origin') == entry['url'], 'dependency origin differs: '+entry['name'])
        need(not read('status','--porcelain','--untracked-files=no'), 'dependency tracked source dirty: '+entry['name'])
        # Only ignored build products may be untracked; no untracked source overlay.
        need(not read('ls-files','--others','--exclude-standard'), 'dependency has untracked source: '+entry['name'])
        result[entry['name']] = {'revision':entry['rev'], 'tree':read('rev-parse','HEAD^{tree}'),
                                 'url':entry['url'], 'path':str(path)}
    return result


def prepare_dependencies(workspace: Path, git: Path, env: dict, recorder: Recorder, *, allow_network: bool) -> None:
    for entry in locked_dependencies(workspace):
        path = workspace/ROOT_PROJECT/'.lake/packages'/entry['name']
        if path.exists(): continue
        need(allow_network, 'dependency missing: '+entry['name']+'; setup network permission required')
        path.parent.mkdir(parents=True, exist_ok=True)
        recorder.checked('init-'+entry['name'].lower(), [str(git),'init',str(path)],workspace,env)
        for key,value in (('core.autocrlf','false'),('core.longpaths','true'),('core.hooksPath',str(workspace/'empty-hooks'))):
            recorder.checked('config-'+entry['name'].lower(), [str(git),'-C',str(path),'config',key,value],workspace,env)
        recorder.checked('remote-'+entry['name'].lower(), [str(git),'-C',str(path),'remote','add','origin',entry['url']],workspace,env)
        recorder.checked('fetch-'+entry['name'].lower(), [str(git),'-C',str(path),'fetch','--depth=1','origin',entry['rev']],workspace,env,timeout=1800)
        recorder.checked('checkout-'+entry['name'].lower(), [str(git),'-C',str(path),'checkout','--detach',entry['rev']],workspace,env)
    dependency_state(workspace,git,env)


def parse_axioms(stdout: str, names: tuple[str, ...]) -> dict:
    rest = stdout.replace('\r\n','\n').strip(); result = {}
    for name in names:
        pat = r"'"+re.escape(name)+r"' (?:depends on axioms: \[([^\]]*)\]|does not depend on any axioms)"
        match = re.match(pat,rest,re.S)
        need(match is not None, 'missing or reordered theorem audit: '+name)
        axioms = [] if match[1] is None else [x.strip() for x in match[1].split(',') if x.strip()]
        need(len(axioms) == len(set(axioms)) and set(axioms) <= ALLOWED_AXIOMS, 'unapproved theorem axiom')
        result[name] = axioms; rest = rest[match.end():].strip()
    need(not rest, 'unexpected theorem audit output')
    return result


def verify_tool_versions(tool: Path, workspace: Path, env: dict, recorder: Recorder) -> dict:
    suffix = '.exe' if os.name == 'nt' else ''
    result = {}
    for name in ('lean','lake'):
        binary = tool/'bin'/(name+suffix)
        row = recorder.checked(name+'-version',[str(binary),'--version'],workspace,env,timeout=30)
        text = recorder.text(row,'stdout')
        pat = r'^Lean \(version 4\.31\.0(?:,|\))' if name == 'lean' else r'^Lake version 5\.0\.0-src\+.*\(Lean version 4\.31\.0\)'
        if name == 'lake':
            # Lake's own release number differs from Lean's; bind the Lean version suffix.
            need(re.match(r'^Lake version [^\r\n]+\(Lean version 4\.31\.0\)\s*$',text) is not None, 'Lake version mismatch')
        else:
            need(re.match(pat,text) is not None,'Lean version mismatch')
        need(not recorder.text(row,'stderr'),'version invocation emitted stderr')
        result[name] = {'path':str(binary),'sha256':file_sha(binary),'version':text.strip()}
    return result


def compiler_probes(tool: Path, workspace: Path, env: dict, recorder: Recorder) -> None:
    suffix = '.exe' if os.name == 'nt' else ''; lean = str(tool/'bin'/('lean'+suffix))
    directory = recorder.output/'compiler-probes'; directory.mkdir()
    positive = directory/'Positive.lean'; negative = directory/'Negative.lean'
    positive.write_bytes(b'theorem phase17_kernel_sentinel : (2 : Nat) + 2 = 4 := by decide\n#print axioms phase17_kernel_sentinel\n')
    negative.write_bytes(b'theorem phase17_kernel_negative : (2 : Nat) + 2 = 5 := by decide\n')
    before = {p.name: file_sha(p) for p in (positive, negative)}
    a = recorder.checked('positive-kernel-probe',[lean,str(positive)],workspace,env)
    need(not recorder.text(a,'stderr'),'positive probe stderr')
    parse_axioms(recorder.text(a,'stdout'),('phase17_kernel_sentinel',))
    b = recorder.run('negative-kernel-probe',[lean,str(negative)],workspace,env)
    need(b['returncode'] == 1 and b['problem'] is None and
         'error:' in (recorder.text(b,'stdout') + recorder.text(b,'stderr')),
         'negative kernel probe did not produce the expected proof rejection')
    need({p.name: file_sha(p) for p in (positive, negative)} == before, 'compiler probe source changed')


def build_and_audit_root(workspace: Path, tool: Path, git: Path, env: dict, recorder: Recorder,
                         pins: dict, *, allow_network: bool) -> dict:
    project = workspace/ROOT_PROJECT
    suffix = '.exe' if os.name == 'nt' else ''; lake = str(tool/'bin'/('lake'+suffix))
    lean = str(tool/'bin'/('lean'+suffix))
    before = dependency_state(workspace,git,env); verify_root(workspace,pins)
    mathlib = project/'.lake/packages/mathlib/.lake/build/lib/lean/Mathlib.olean'
    if not mathlib.is_file():
        need(allow_network,'compiled pinned Mathlib missing; --allow-network required for explicit cache setup')
        recorder.checked('mathlib-cache-get',[lake,'--keep-toolchain','exe','cache','get'],project,env,timeout=7200)
        need(mathlib.is_file(),'Mathlib cache command returned without required module')
        need(dependency_state(workspace,git,env) == before,'dependency changed during cache setup')
        verify_root(workspace,pins)
    # Rehash all sources; local root builds are never replaced by a claim from history.
    recorder.checked('build-pinned-formal-core',[lake,'--keep-toolchain','--no-cache','--rehash','build','RcpRclmFormalCoreV4'],project,env,timeout=7200)
    audit = recorder.output/'RootAxiomAudit.lean'
    audit.write_bytes(('import RcpRclmFormalCoreV4\n\n'+''.join('#print axioms '+x+'\n' for x in ROOT_NAMES)).encode())
    row = recorder.checked('root-axiom-audit',[lake,'--keep-toolchain','--no-cache','env',lean,str(audit)],project,env)
    need(not recorder.text(row,'stderr'),'root axiom audit stderr')
    need(audit.read_bytes() == ('import RcpRclmFormalCoreV4\n\n'+''.join('#print axioms '+x+'\n' for x in ROOT_NAMES)).encode(), 'root audit source changed')
    parsed = parse_axioms(recorder.text(row,'stdout'),ROOT_NAMES)
    verify_root(workspace,pins)
    need(dependency_state(workspace,git,env) == before,'dependency state changed during root build')
    modules = {}
    for version in (2,3,4):
        p = workspace/f'lean/rcp_rclm_formal_core_v{version}/.lake/build/lib/lean'/f'RcpRclmFormalCoreV{version}.olean'
        if p.is_file(): modules[p.relative_to(workspace).as_posix()] = file_sha(p)
    need(f'{ROOT_PROJECT}/.lake/build/lib/lean/RcpRclmFormalCoreV4.olean' in modules,'root build artifact missing')
    return dict(conditional_root_theorems_rebuilt=True, theorem_axioms=parsed, modules=modules,
                mathlib_root_olean_sha256=file_sha(mathlib), dependencies=before,
                root_transition_verified=False, trusted_toolchain_and_import_cache_assumption=True)


@contextmanager
def exclusive_cache(cache: Path):
    no_links(cache)
    cache.mkdir(parents=True, exist_ok=True)
    lock = cache/'in-use.lock'
    token = f'{os.getpid()} {utc()} {uuid.uuid4().hex}\n'.encode()
    with lock.open('xb') as f: f.write(token)
    try: yield
    finally:
        need(lock.is_file() and lock.read_bytes() == token, 'workspace lock changed; not removed')
        lock.unlink()


def setup_and_verify(repository: Path, output: Path, cache: Path, *, toolchain_root: Path | None,
                     allow_network: bool) -> dict:
    need(not output.exists(),'new verification output directory required')
    no_links(output.parent); no_links(cache)
    need(repository not in output.parents and output != repository,'evidence must be outside repository')
    need(repository not in cache.parents and cache != repository,'tool workspace must be outside repository')
    need(cache not in output.parents and output not in cache.parents and output != cache,
         'evidence and tool workspaces must be separate')
    output.mkdir(parents=True)
    recorder = Recorder(output)
    result = dict(schema='rcp-rclm.phase17e.real-lean-execution.v1',status='blocked',started_at_utc=utc(),
                  actual_lean_capability_verification=False,conditional_root_theorems_rebuilt=False,
                  commands=recorder.commands,network_setup_authorized=allow_network,
                  environment=dict(os=platform.system(),python=platform.python_version()),claims=dict(FALSE_CLAIMS))
    try:
        pins = read_pins(repository); root_before = verify_root(repository,pins)
        git_path = shutil.which('git'); need(git_path is not None,'ordinary Git is required')
        git = Path(git_path).resolve()
        source = subprocess.check_output([str(git),'-C',str(repository),'rev-parse','HEAD'],timeout=30).decode().strip()
        tree = subprocess.check_output([str(git),'-C',str(repository),'rev-parse','HEAD^{tree}'],timeout=30).decode().strip()
        need(not subprocess.check_output([str(git),'-C',str(repository),'status','--porcelain'],timeout=30), 'clean committed source required')
        result.update(source_commit=source,source_tree=tree,formal_root_pins_sha256=PINS_SHA)
        with exclusive_cache(cache):
            workspace = cache/'formal-root'
            if not workspace.exists(): copy_root(repository,workspace,pins)
            verify_root(workspace,pins)
            tool = choose_toolchain(cache,toolchain_root,allow_network=allow_network)
            env = clean_environment(tool,git,network=allow_network)
            env['MATHLIB_CACHE_DIR'] = str(cache/'mathlib-cache')
            env['XDG_CACHE_HOME'] = str(cache/'cache')
            result['tools'] = verify_tool_versions(tool,workspace,env,recorder)
            compiler_probes(tool,workspace,env,recorder)
            prepare_dependencies(workspace,git,env,recorder,allow_network=allow_network)
            result['root_build'] = build_and_audit_root(workspace,tool,git,env,recorder,pins,allow_network=allow_network)
            result['conditional_root_theorems_rebuilt'] = True
            row = recorder.checked('capability-gate', [sys.executable,str(repository/'scripts/run_phase17_package_gate.py'),
                '--output',str(output/'package-run'),'--require-lean','--toolchain-root',str(tool),
                '--lean-workspace',str(workspace)], repository,
                dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),timeout=12000)
            execution = json.loads(regular(output/'package-run/execution.json'))
            gate = execution.get('lean_gate',{})
            need(execution.get('source_commit') == source and execution.get('source_tree') == tree and
                 execution.get('source_unchanged') is True,'capability report/source binding differs')
            need(execution.get('capability_tasks_evaluated') == 21 and execution.get('lean_obligations_prepared') == 13 and
                 execution.get('python_frontier_evaluation_passed') is True,'incomplete capability frontier')
            need(gate.get('status') == 'passed' and gate.get('fresh_lean_verified') is True and
                 gate.get('capability_frontier_recertified') is True and gate.get('obligation_count') == 13 and
                 len(gate.get('proofs',[])) == 13,'no real complete Lean capability result')
            names = tuple(x['name'] for x in gate['proofs'])
            need(len(set(names)) == 13 and all(x['checked'] is True and set(x['axioms']) <= ALLOWED_AXIOMS for x in gate['proofs']),
                 'invalid proof set')
            for key in ('phase17_exit_closed','gate_e_closed','root_transition_verified','full_frontier_recertified','promotion_performed'):
                need(execution.get(key) is False,'unauthorized closure claim: '+key)
            need(verify_root(repository,pins) == root_before,'original formal root changed')
            verify_root(workspace,pins)
            for name,metadata in result['tools'].items():
                need(file_sha(Path(metadata['path'])) == metadata['sha256'],'tool executable changed')
            need(dependency_state(workspace,git,env) == result['root_build']['dependencies'],'dependencies changed after checking')
            need(subprocess.check_output([str(git),'-C',str(repository),'rev-parse','HEAD'],timeout=30).decode().strip() == source and
                 not subprocess.check_output([str(git),'-C',str(repository),'status','--porcelain'],timeout=30),'source changed during verification')
            result.update(status='passed',actual_lean_capability_verification=True,
                          capability_frontier_recertified=True,execution_report_sha256=file_sha(output/'package-run/execution.json'))
    except (ValueError,OSError,subprocess.SubprocessError,zipfile.BadZipFile) as exc:
        result['failure'] = dict(type=type(exc).__name__,reason=str(exc))
        if result['commands']: result['status'] = 'incomplete_or_rejected'
    result['finished_at_utc'] = utc()
    save(output/'verification-report.json',result)
    files = sorted(p for p in output.rglob('*') if p.is_file() and 'package' not in p.relative_to(output).parts)
    manifest = ''.join(file_sha(p)+'  '+p.relative_to(output).as_posix()+'\n' for p in files)
    (output/'SHA256SUMS.txt').write_bytes(manifest.encode())
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--toolchain-root',type=Path)
    parser.add_argument('--allow-network',action='store_true',help='Permit exact portable Lean/dependency/cache downloads into the separate tools workspace')
    args = parser.parse_args(argv)
    result = setup_and_verify(args.repository.resolve(),args.output.resolve(),args.cache.resolve(),
                              toolchain_root=args.toolchain_root,allow_network=args.allow_network)
    print(json.dumps(result,indent=2))
    return 0 if result['status'] == 'passed' else 2


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print('STOP: '+str(exc),file=sys.stderr); raise SystemExit(2)
