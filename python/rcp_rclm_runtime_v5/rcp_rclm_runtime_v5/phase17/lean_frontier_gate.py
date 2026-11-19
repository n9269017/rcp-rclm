"""Opt-in real Lean checking of prepared capability obligations; no None-success.

No installation, network bootstrap, implicit toolchain upgrade, generated user
code, or active-store mutation. The existing pinned Lean/Mathlib workspace must
already be prepared by its operator. Toolchain/cached-library integrity is a
trusted-environment premise, not hardware attestation.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from rcp_rclm_runtime.canonical.json import load_json_strict, canonical_json_bytes as canonical
from rcp_rclm_runtime_v5.phase17.materialized import require, sha
from rcp_rclm_runtime_v5.phase17.frontier_recertification import PreparedFrontier

VERSION = '4.31.0'
TOOLCHAIN = 'leanprover/lean4:v'+VERSION
PINS_SHA256 = 'ec2226ce520783d965a8e8370dcccce550751e90935fb79ba76ebc137bfc658f'
ROOT_PROJECT = 'lean/rcp_rclm_formal_core_v4'
ALLOWED_AXIOMS = {'propext','Classical.choice','Quot.sound'}


def _read_regular(path: Path) -> bytes:
    require(path.is_file() and not path.is_symlink(), 'missing/linked pinned file: '+str(path))
    return path.read_bytes()


def root_source_fingerprint(repository: Path) -> dict:
    raw_pins = _read_regular(Path(__file__).with_name('lean_root_pins.json')).replace(b'\r\n', b'\n')
    require(sha(raw_pins) == PINS_SHA256, 'root pin table modified')
    pins = json.loads(raw_pins)
    require(pins['toolchain'] == TOOLCHAIN, 'root toolchain policy changed')
    observed = {}
    for rel, expected in pins['files'].items():
        path = repository/rel
        raw = _read_regular(path)
        # These are text-only project files. Allow checkout CRLF without changing
        # the trusted canonical bytes or accepting any other content difference.
        normalized = raw.replace(b'\r\n',b'\n')
        require(sha(normalized) == expected, 'pinned root source differs: '+rel)
        observed[rel] = {'canonical_sha256':expected, 'checkout_sha256':sha(raw)}
    for v in (2,3,4):
        project = repository/f'lean/rcp_rclm_formal_core_v{v}'
        actual = {p.relative_to(repository).as_posix() for p in project.rglob('*')
                  if p.is_file() and '.lake' not in p.relative_to(project).parts and
                  '.git' not in p.relative_to(project).parts}
        wanted = {p for p in pins['files'] if p.startswith(f'lean/rcp_rclm_formal_core_v{v}/')}
        require(actual == wanted, 'unexpected root source file set')
    return observed


def _dependency_state(repository: Path) -> dict:
    """Require pinned dependency checkouts AND prebuilt Mathlib; never download."""
    project = repository/ROOT_PROJECT
    lock = json.loads(_read_regular(project/'lake-manifest.json'))
    result = {}
    for entry in lock['packages']:
        if entry['type'] != 'git':
            continue
        candidates = [repository/f'lean/rcp_rclm_formal_core_v{v}/.lake/packages'/entry['name']
                      for v in (4,3,2)]
        matches = [p for p in candidates if (p/'.git').exists()]
        require(bool(matches), 'pinned dependency not installed: '+entry['name'])
        states = []
        for p in matches:
            head = subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],timeout=30).decode().strip()
            dirty = subprocess.check_output(['git','--no-optional-locks','-C',str(p),'status','--porcelain',
                                            '--untracked-files=no'],timeout=30)
            require(head == entry['rev'] and not dirty, 'pinned dependency source differs: '+entry['name'])
            states.append({'path':str(p.resolve()),'head':head})
        result[entry['name']] = states
    mathlibs = [Path(p['path']) for p in result.get('mathlib',[])]
    require(any((p/'.lake/build/lib/lean/Mathlib.olean').is_file() for p in mathlibs),
            'prebuilt pinned Mathlib is missing; no implicit installation')
    return result


def resolve_toolchain(root: Path | None = None) -> Path:
    if root is None:
        home = Path(os.environ.get('ELAN_HOME', str(Path.home()/'.elan')))
        require(home.is_absolute(), 'ELAN_HOME must be absolute')
        root = home/'toolchains'/('leanprover--lean4---v'+VERSION)
    root = root.resolve()
    suffix = '.exe' if os.name == 'nt' else ''
    require((root/'bin'/('lean'+suffix)).is_file() and (root/'bin'/('lake'+suffix)).is_file(),
            'pinned Lean '+VERSION+' is not installed; refusing simulated verification')
    return root


def _lean_environment(tool: Path) -> tuple[dict, Path]:
    """Keep the tool PATH narrow, but make ordinary Git visible to Lake.

    Resolve Git before discarding the caller's PATH. Neither the full caller
    environment nor Git/Lean search-path overrides are forwarded. This is
    environment hygiene, not an operating-system or network sandbox.
    """
    found = shutil.which('git')
    require(found is not None and Path(found).is_absolute(),
            'ordinary Git is required by the pinned Lake capability gate')
    git = Path(found).resolve(strict=True)
    require(git.is_file() and not git.is_symlink(), 'Git executable is not a regular file')
    allowed = {'SYSTEMROOT','WINDIR','SYSTEMDRIVE','TEMP','TMP','HOME','USERPROFILE',
               'LANG','LC_ALL'}
    env = {k.upper():v for k,v in os.environ.items() if k.upper() in allowed}
    paths = [str(tool.resolve()/'bin'), str(git.parent)]
    if env.get('SYSTEMROOT'):
        system = Path(env['SYSTEMROOT'])
        require(system.is_absolute(), 'SystemRoot must be absolute')
        paths.extend((str(system/'System32'), str(system)))
    # In particular, do not carry Windows os.defpath's current-directory entry.
    paths.extend(p for p in os.defpath.split(os.pathsep) if p and Path(p).is_absolute())
    paths = list(dict.fromkeys(paths))
    env.update(PATH=os.pathsep.join(paths), ELAN_TOOLCHAIN=TOOLCHAIN,
               GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1',
               GIT_CONFIG_GLOBAL=os.devnull, LAKE_NO_CACHE='true',
               LAKE_ARTIFACT_CACHE='false', NoDefaultCurrentDirectoryInExePath='1')
    resolved = shutil.which(git.name, path=env['PATH'])
    require(resolved is not None and Path(resolved).resolve() == git,
            'restricted PATH does not resolve to the selected Git executable')
    return env, git


def _process(argv: list[str], cwd: Path, env: dict, *, timeout: int = 600) -> dict:
    start = datetime.now(timezone.utc).isoformat(); clock = time.monotonic_ns()
    try:
        result = subprocess.run(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                timeout=timeout,check=False)
        code, stdout, stderr = result.returncode,result.stdout,result.stderr
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = -999,exc.stdout or b'',exc.stderr or b''
    require(len(stdout)+len(stderr) < 2*1024*1024,'Lean output bound exceeded')
    return {'argv':argv,'returncode':code,'stdout':stdout.decode('utf-8',errors='replace'),
            'stderr':stderr.decode('utf-8',errors='replace'),'stdout_sha256':sha(stdout),
            'stderr_sha256':sha(stderr),'started_at_utc':start,
            'elapsed_ns':time.monotonic_ns()-clock}


def _axioms(stdout: str, theorem: str) -> list[str]:
    # Exact requested theorem; no substring match on an unrelated successful proof.
    pattern = r"'"+re.escape(theorem)+r"' depends on axioms: \[([^\]]*)\]\s*"
    if re.fullmatch("'"+re.escape(theorem)+"' does not depend on any axioms\\s*",stdout):
        return []
    match = re.fullmatch(pattern,stdout,re.S)
    require(match is not None,'missing/unexpected axiom-audit output')
    names = [s.strip() for s in match[1].split(',') if s.strip()]
    require(len(names) == len(set(names)) and set(names) <= ALLOWED_AXIOMS,
            'proof depends on an unapproved axiom')
    return names


def _check_prepared_frontier(prepared: PreparedFrontier, repository: Path, *,
                            toolchain_root: Path | None = None) -> dict:
    """Run real tools or return blocked/rejected; never a passing test stub.

    This helper consumes a freshly recomputed frontier in the trusted verifier.
    It is not a public acceptance API for candidate-supplied report/source bytes.
    """
    report = prepared.report
    sources = dict(prepared.sources)
    wanted = {r['proof_name']:r['source_sha256'] for r in report['task_reports'] if r['lean_required']}
    require(len(sources) == len(prepared.sources) == len(wanted) == 13 and
            {name:sha(raw) for name,raw in sources.items()} == wanted,
            'Lean obligations are incomplete or substituted')
    require(report['complete_capability_coverage'] is True and report['capability_count'] == 21,
            'incomplete capability coverage')
    result = {'schema_id':'runtime.v5.phase17.lean-capability-check.v1','status':'blocked',
              'toolchain':TOOLCHAIN,'capability_frontier_report_hash':report['report_hash'],
              'obligation_count':13,'commands':[], 'proofs':[],
              'fresh_lean_verified':False,'capability_frontier_recertified':False,
              'recursive_productivity_recertified':False,'root_transition_verified':False,
              'promotion_authorized':False,'phase17_exit_closed':False,'gate_e_closed':False}
    try:
        before = root_source_fingerprint(repository)
        deps_before = _dependency_state(repository)
        tool = resolve_toolchain(toolchain_root)
        suffix = '.exe' if os.name == 'nt' else ''
        lean, lake = tool/'bin'/('lean'+suffix), tool/'bin'/('lake'+suffix)
        binary_hashes = {p.name:sha(_read_regular(p)) for p in (lean,lake)}
        env, git = _lean_environment(tool)
        git_identity = {'path':str(git), 'sha256':sha(_read_regular(git))}
        result['git_executable'] = git_identity
        version = _process([str(lean),'--version'],repository/ROOT_PROJECT,env,timeout=30)
        result['commands'].append(version)
        require(version['returncode'] == 0 and not version['stderr'] and
                re.match(r'^Lean \(version 4\.31\.0(?:,|\))',version['stdout']) is not None,
                'Lean executable version mismatch')
        result['status']='rejected'
        with tempfile.TemporaryDirectory(prefix='phase17-frontier-lean-') as temporary:
            directory=Path(temporary)
            for name,raw in prepared.sources:
                require(re.fullmatch('phase17_[0-9a-f]{24}',name) is not None,'unsafe proof filename')
                path=directory/(name+'.lean');path.write_bytes(raw)
                record=_process([str(lake),'--keep-toolchain','--no-cache','env',str(lean),str(path)],repository/ROOT_PROJECT,env)
                result['commands'].append(record)
                require(record['returncode']==0 and not record['stderr'], 'pinned Lean task rejected')
                used=_axioms(record['stdout'],name)
                require(path.read_bytes()==raw,'proof source changed during checking')
                result['proofs'].append({'name':name,'source_sha256':sha(raw),'axioms':used,'checked':True})
        require(root_source_fingerprint(repository)==before and _dependency_state(repository)==deps_before,
                'root or dependencies changed during verification')
        require({p.name:sha(_read_regular(p)) for p in (lean,lake)}==binary_hashes,
                'toolchain executable changed')
        require(sha(_read_regular(git)) == git_identity['sha256'], 'Git executable changed')
        result.update(status='passed',fresh_lean_verified=True,capability_frontier_recertified=True,
                      root_source_fingerprint=before,dependencies=deps_before,executable_sha256=binary_hashes,
                      trusted_import_cache_assumption=True)
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        result['failure']={'type':type(exc).__name__,'reason':str(exc)}
    return result


def recertify_package(package, parent, *, repository: Path, bundle: Path, capture: Path,
                      toolchain_root: Path | None = None, transcript: bytes | None = None,
                      expected_transcript_hash: str | None = None) -> dict:
    """Production boundary always recomputes actual package/frontier, never trusts a pass JSON."""
    from rcp_rclm_runtime_v5.phase17.frontier_recertification import prepare_frontier
    from rcp_rclm_runtime_v5.phase17.materialized import verify_package
    prepared = prepare_frontier(package,parent,bundle=bundle,capture=capture,
                                transcript=transcript,expected_transcript_hash=expected_transcript_hash)
    result = _check_prepared_frontier(prepared,repository,toolchain_root=toolchain_root)
    verify_package(package.root,parent,bundle,expected_package_hash=package.package_hash,
                   transcript=transcript,expected_transcript_hash=expected_transcript_hash)
    return result
