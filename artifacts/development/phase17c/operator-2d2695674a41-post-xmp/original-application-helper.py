"""Apply Phase 17C through a disposable full checkout, validate, then fast-forward.

No reset, amend, force-push, main merge, hosted rerun or billing operation.
On validation failure the user's original checkout remains at its original head;
the isolated checkout and logs are retained under this kit's runs directory.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid

BASE='bb1f8669311c099938cc299c2b4fd9f5f77be9e3'
BRANCH='agent/rcp-rclm-v5-phase-17-controller'
STATUS='docs/executable_core_v5/PHASE_17_LOCAL_VALIDATION.json'
IMPLEMENTATION='docs/executable_core_v5/PHASE_17_IMPLEMENTATION.md'
ROOT_MANIFEST='SHA256SUMS.txt'
EVIDENCE_ROOT='artifacts/development/phase17c'
EXPECTED_STATUS_BLOB='0c6851b0c425b08569691f7cedfb0e3610e7d1f9'
FOUNDATION_TESTS=110
PROCESS_TESTS=18
ARCHIVE_TESTS=10
ORIGINS={'https://github.com/n9269017/rcp-rclm','https://github.com/n9269017/rcp-rclm.git',
         'git@github.com:n9269017/rcp-rclm','git@github.com:n9269017/rcp-rclm.git',
         'ssh://git@github.com/n9269017/rcp-rclm','ssh://git@github.com/n9269017/rcp-rclm.git'}
ALLOWED_PREFIXES=('python/rcp_rclm_runtime_v5/','scripts/','docs/executable_core_v5/',EVIDENCE_ROOT+'/')


def sha(data):return hashlib.sha256(data).hexdigest()

def now():return datetime.now(timezone.utc).isoformat()

def json_write(path,value):
    path.write_bytes((json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode())

def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE)

def git_text(repo,*args):return git(repo,*args).decode('utf-8').strip()

def checked(repo,*args):
    subprocess.run(['git','-C',str(repo),*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

def require(test,message):
    if not test:raise ValueError(message)

def relative(value):
    require(type(value)is str and value and not any(c in value for c in '\\:\x00\r\n'), 'unsafe payload path')
    p=PurePosixPath(value)
    require(not p.is_absolute() and '..' not in p.parts and p.as_posix()==value, 'unsafe payload path')
    return value

def safe_file(root,rel):
    path=root/relative(rel)
    require(not path.is_symlink() and all(not p.is_symlink() for p in path.parents if p!=root.parent),
            'symlink in payload/destination path')
    require(root.resolve() in path.resolve().parents,'path escapes root')
    return path

def clean(repo):
    require(not git(repo,'status','--porcelain','--untracked-files=all'),'checkout has local changes; preserve them')

def remote_head(repo):
    lines=git_text(repo,'ls-remote','--exit-code','origin',f'refs/heads/{BRANCH}').splitlines()
    require(len(lines)==1,'remote development branch not uniquely resolved')
    return lines[0].split()[0]

def load_payload(kit):
    obj=json.loads((kit/'PAYLOAD_MANIFEST.json').read_bytes())
    require(set(obj)=={'base_commit','branch','files'} and obj['base_commit']==BASE and obj['branch']==BRANCH,
            'kit target mismatch')
    require(type(obj['files'])is dict and bool(obj['files']),'empty payload')
    entries={}
    for rel,d in obj['files'].items():
        relative(rel)
        require(rel.startswith(ALLOWED_PREFIXES) and not rel.startswith('.github/'),'unexpected destination')
        require(re.fullmatch('[0-9a-f]{64}',d) is not None,'invalid payload hash')
        path=safe_file(kit/'payload',rel)
        require(path.is_file() and sha(path.read_bytes())==d,'payload mismatch: '+rel)
        entries[rel]=path.read_bytes()
    require(not any(p.is_symlink() for p in (kit/'payload').rglob('*')), 'payload symlink rejected')
    observed={p.relative_to(kit/'payload').as_posix() for p in (kit/'payload').rglob('*') if p.is_file()}
    require(observed==set(entries),'payload file set mismatch')
    return entries

def require_test_log(data,expected):
    text=data.decode('utf-8',errors='replace')
    matches=re.findall(r'^Ran (\d+) tests? in ',text,re.M)
    require(matches==[str(expected)] and re.search(r'^OK\s*$',text,re.M) is not None and
            not re.search(r'^FAILED|^OK \(|\.\.\. skipped',text,re.M),
            f'expected exactly {expected} passing tests, with no skips')

def verify_manifest(directory):
    manifest=directory/'SHA256SUMS.txt';listed={}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        d,rel=line.split('  ',1);relative(rel)
        require(rel not in listed and re.fullmatch('[0-9a-f]{64}',d),'bad evidence manifest entry')
        path=safe_file(directory,rel)
        require(path.is_file() and sha(path.read_bytes())==d,'evidence hash mismatch: '+rel)
        listed[rel]=d
    actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p!=manifest}
    require(actual==set(listed),'evidence membership mismatch')
    return sha(manifest.read_bytes())

def tracked_equal(repo,entries):
    for rel,data in entries.items():
        require(git(repo,'cat-file','blob',':'+rel)==data,'staged bytes changed: '+rel)

def refresh(repo):
    subprocess.run([sys.executable,'scripts/phase17_refresh_checksums.py','--write'],cwd=repo,check=True)
    checked(repo,'add','--',ROOT_MANIFEST)
    subprocess.run([sys.executable,'scripts/phase17_refresh_checksums.py'],cwd=repo,check=True)

def commit(repo,message,hooks):
    checked(repo,'-c','core.hooksPath='+str(hooks),'commit','-m',message)
    clean(repo)
    return git_text(repo,'rev-parse','HEAD')

def staged_paths(repo):return set(git(repo,'diff','--cached','--name-only','-z').decode().strip('\0').split('\0'))

def update_status_for_code(repo):
    status=json.loads((repo/STATUS).read_bytes())
    require(status['phase17_exit_closed']is False and status['gate_e_closed']is False and
            status['egc0_started']is False and status['main_merge_authorized']is False,'unexpected closure boundary')
    status['stage']='phase17c_bounded_post_freeze_evaluation'
    status['implemented_scope'].update({
        'post_freeze_challenge_service':True,'bounded_dsl_candidate_realization':True,
        'bounded_dsl_reference_evaluation':True,'process_and_protocol_separation':True,
        'hostile_same_user_security_sandbox':False,'sealed_transcript_recomputation':True,
        'single_turn_controller_evaluator_integration':True,
    })
    status['validation']['new_bootstrap_windows']='operator_passed_10_archive_tests_and_constructor_at_52c3b8f33293'
    status['validation']['local_evidence_tool_windows']='capture_and_verify_passed_at_52c3b8f33293; separate_unit_suite_not_run'
    status['validation']['historical_assistant_phase17b_checkout_scope']=status['validation'].pop('source_checkout_scope')
    status['validation']['phase17c_operator_validation']='pending'
    status['validation']['phase17c_assistant_validation']='see source-hashed assistant report; not full current checkout'
    status['evidence_records']['phase17c_assistant_validation']=EVIDENCE_ROOT+'/assistant-validation.json'
    status['unimplemented']=[x for x in status['unimplemented'] if x not in
                            ('post_freeze_challenge_isolation','independent_candidate_evaluation')]
    status['unimplemented'] += ['hostile_executable_evaluator_sandbox',
        'full_model_realization_and_independent_evaluation','durable_cross_session_challenge_consumption']
    json_write(repo/STATUS,status)
    with (repo/IMPLEMENTATION).open('a',encoding='utf-8',newline='\n') as f:
        f.write('\n## Phase 17C — bounded post-freeze evaluation\n\n'
                'See [PHASE_17_CHALLENGE_TRANSACTION.md](PHASE_17_CHALLENGE_TRANSACTION.md). '
                'This adds one evaluator-separated bounded DSL turn, not full-model evaluation, '
                'a hostile-code sandbox, promotion, or phase closure. '
                'The Phase 17B Windows capture and bootstrap passed at `52c3b8f33293`; '
                'older `not_run` summary labels have been reconciled without changing historical evidence.\n')

def command(stage,evidence,name,argv,timeout=900):
    logs=evidence/'command-logs';logs.mkdir(exist_ok=True)
    out=logs/(name+'.stdout.txt');err=logs/(name+'.stderr.txt')
    start=now();tick=time.monotonic_ns()
    with out.open('wb') as stdout,err.open('wb') as stderr:
        try:
            result=subprocess.run(argv,cwd=stage,stdout=stdout,stderr=stderr,timeout=timeout,
                                  env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
            rc=result.returncode
        except subprocess.TimeoutExpired:
            rc=-999
    summary={'name':name,'argv':[str(a) if i else 'python' for i,a in enumerate(argv)],
             'started_at_utc':start,'finished_at_utc':now(),'duration_ms':(time.monotonic_ns()-tick)//1000000,
             'returncode':rc,'stdout_sha256':sha(out.read_bytes()),'stderr_sha256':sha(err.read_bytes())}
    # Don't publish machine-local absolute paths; raw logs remain separately retained.
    summary['argv']=[Path(x).name if os.path.isabs(x) else x for x in summary['argv']]
    print(f'{name}: exit {rc}',flush=True)
    if rc:
        for path in (out,err,evidence/'foundation/logs/foundation-tests.stderr.txt'):
            if path.exists():
                print('\n===== '+str(path)+' =====')
                print('\n'.join(path.read_text(encoding='utf-8',errors='replace').splitlines()[-120:]))
        json_write(evidence/'FAILED_COMMAND.json',summary)
        raise RuntimeError(name+' failed; original checkout not changed')
    return summary


def validate(stage,evidence,source):
    commands=[]
    commands.append(command(stage,evidence,'compile-new-scripts',[
        sys.executable,'-m','compileall','-q','scripts/phase17_evaluator_worker.py',
        'scripts/run_phase17_challenge_tests.py','scripts/run_phase17_challenge_transaction.py']))
    commands.append(command(stage,evidence,'foundation-capture',[
        sys.executable,'scripts/phase17_local_evidence.py','capture','--output',str(evidence/'foundation'),
        '--expected-head',source]))
    report=json.loads((evidence/'foundation/evidence.json').read_bytes())
    require(report['local_checks_passed']is True and report['source_unchanged']is True and
            report['source']['commit']==source,'foundation source/result mismatch')
    require_test_log((evidence/'foundation/logs/foundation-tests.stderr.txt').read_bytes(),FOUNDATION_TESTS)
    anchor=verify_manifest(evidence/'foundation')
    commands.append(command(stage,evidence,'foundation-verify',[
        sys.executable,'scripts/phase17_local_evidence.py','verify','--bundle',str(evidence/'foundation'),
        '--expected-head',source,'--expected-manifest-sha256',anchor]))
    commands.append(command(stage,evidence,'historical-archives',[
        sys.executable,'scripts/run_phase17_bootstrap_tests.py']))
    require_test_log((evidence/'command-logs/historical-archives.stderr.txt').read_bytes(),ARCHIVE_TESTS)
    commands.append(command(stage,evidence,'process-and-differential',[
        sys.executable,'scripts/run_phase17_challenge_tests.py']))
    require_test_log((evidence/'command-logs/process-and-differential.stderr.txt').read_bytes(),PROCESS_TESTS)
    commands.append(command(stage,evidence,'single-fresh-transaction',[
        sys.executable,'scripts/run_phase17_challenge_transaction.py','--output',str(evidence/'transaction'),
        '--candidate-credits','32']))
    txanchor=verify_manifest(evidence/'transaction')
    tx=json.loads((evidence/'transaction/transaction.json').read_bytes())
    require(tx['local_transaction_verified']is True and tx['separate_process']is True and
            tx['worker_exited_cleanly']is True and all(x is False for x in tx['claims'].values()),
            'transaction result/claim mismatch')
    require(tx['terminal_action'] in ('search_exhausted','await_root_verification'), 'unsupported full-budget terminal')
    require(1<=tx['candidate_evaluations']<=32,'bad evaluation count')
    if tx['terminal_action']=='search_exhausted':require(tx['candidate_evaluations']==32,'incomplete exhaustion')
    clean(stage);require(git_text(stage,'rev-parse','HEAD')==source,'source moved during validation')
    result={'schema':'rcp-rclm.phase17c.operator-validation.v1','tested_code_commit':source,
            'tested_code_tree':git_text(stage,'rev-parse','HEAD^{tree}'),'previous_base':BASE,
            'recorded_at_utc':now(),'environment':{'os':platform.system(),'os_release':platform.release(),
                        'python_version':platform.python_version(),'machine':platform.machine()},
            'foundation_tests':FOUNDATION_TESTS,'historical_archive_tests':ARCHIVE_TESTS,
            'process_and_differential_tests':PROCESS_TESTS,'failures':0,'skipped':0,
            'foundation_manifest_sha256':anchor,'transaction_manifest_sha256':txanchor,
            'single_transaction_terminal':tx['terminal_action'],'single_transaction_evaluations':tx['candidate_evaluations'],
            'commands':commands,'fresh_git_checkout':True,'isolated_python_environment':False,
            'github_hosted_ci_passed':False,'cross_platform_validation':False,
            'phase17_exit_closed':False,'gate_e_closed':False,'egc0_started':False,
            'fresh_lean_verification':False,'full_frontier_recertified':False,
            'os_security_sandbox':False,'phase18_independent_replay':False,'promotion_performed':False}
    json_write(evidence/'operator-validation.json',result)
    return result


def build_evidence_commit(stage,evidence,source,result,hooks):
    rel=EVIDENCE_ROOT+'/operator-'+source[:12]
    target=stage/rel;require(not target.exists(),'evidence target already exists')
    shutil.copytree(evidence,target)
    (target/'.gitattributes').write_bytes(b'** -text\n')
    entries={p.relative_to(stage).as_posix():p.read_bytes() for p in target.rglob('*') if p.is_file()}
    manifest=''.join(f'{sha(b)}  {Path(n).relative_to(rel).as_posix()}\n' for n,b in sorted(entries.items())).encode()
    (target/'SHA256SUMS.txt').write_bytes(manifest)
    entries[rel+'/SHA256SUMS.txt']=manifest
    checked(stage,'add','-f','--',*sorted(entries))
    tracked_equal(stage,entries)
    status=json.loads((stage/STATUS).read_bytes())
    status['evidence_records']['phase17c_operator_capture']=rel+'/operator-validation.json'
    status['validation']['phase17c_operator_validation']='passed_110_foundation_18_process_differential_10_archive_tests'
    status['validation']['phase17c_operator_platform']=result['environment']['os']
    status['validation']['phase17c_tested_code_commit']=source
    status['validation']['full_updated_checkout_suite']='operator_local_passed_110_at_'+source
    status['validation']['phase17c_single_turn']=result['single_transaction_terminal']
    json_write(stage/STATUS,status)
    checked(stage,'add','--',STATUS);refresh(stage)
    require(staged_paths(stage)==set(entries)|{STATUS,ROOT_MANIFEST},'unexpected evidence-only diff')
    return commit(stage,'Retain Phase 17C local validation and sealed transaction [skip ci]',hooks)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--push',action='store_true')
    args=parser.parse_args(argv)
    require(sys.version_info >= (3, 11), "Python 3.11 or later is required")
    kit=Path(__file__).resolve().parent;repo=args.repo.resolve()
    entries=load_payload(kit)
    require(Path(git_text(repo,'rev-parse','--show-toplevel')).resolve()==repo,'exact repository root required')
    require(git_text(repo,'branch','--show-current')==BRANCH,'switch to the existing Phase 17 branch first')
    require(git_text(repo,'rev-parse','HEAD')==BASE,'local branch moved; do not reset it')
    clean(repo)
    origin=git_text(repo,'remote','get-url','origin');require(origin in ORIGINS,'unexpected origin')
    require(remote_head(repo)==BASE,'remote branch moved; no overwrite is permitted')
    require(git_text(repo,'rev-parse','HEAD:'+STATUS)==EXPECTED_STATUS_BLOB,'unexpected baseline status file')
    for rel in entries:
        require(not safe_file(repo,rel).exists(),'payload targets an existing file: '+rel)
    name=git_text(repo,'config','user.name');email=git_text(repo,'config','user.email')
    require(name and email,'Git author identity not configured')
    run=kit/'runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    run.mkdir(parents=True,exist_ok=False);hooks=run/'empty-hooks';hooks.mkdir()
    stage=run/'checkout';evidence=run/'evidence';evidence.mkdir()
    print('Validation workspace: '+str(run),flush=True)
    try:
        subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(repo),str(stage)],check=True,
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        checked(stage,'config','core.autocrlf','false')
        checked(stage,'config','user.name',name);checked(stage,'config','user.email',email)
        checked(stage,'-c','core.hooksPath='+str(hooks),'checkout','--detach',BASE)
        subprocess.run([sys.executable,'scripts/phase17_refresh_checksums.py'],cwd=stage,check=True)
        for rel,data in entries.items():
            path=safe_file(stage,rel);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        update_status_for_code(stage)
        approved=set(entries)|{STATUS,IMPLEMENTATION,ROOT_MANIFEST}
        checked(stage,'add','-f','--',*sorted(set(entries)|{STATUS,IMPLEMENTATION}))
        tracked_equal(stage,entries);refresh(stage)
        require(staged_paths(stage)==approved,'unexpected implementation diff')
        source=commit(stage,'Implement Phase 17C bounded post-freeze evaluation [skip ci]',hooks)
        json_write(run/'progress.json',{'tested_code_commit':source,'original_checkout_changed':False,'pushed':False})
        result=validate(stage,evidence,source)
        evidence_head=build_evidence_commit(stage,evidence,source,result,hooks)
        # Keep user checkout unchanged until all checks and evidence commits exist.
        clean(repo);require(git_text(repo,'rev-parse','HEAD')==BASE,'original checkout moved during validation')
        require(remote_head(repo)==BASE,'remote moved during validation; no force push')
        for rel in entries:require(not safe_file(repo,rel).exists(),'new local file conflicts with validated update')
        checked(repo,'fetch',str(stage),evidence_head)
        checked(repo,'-c','core.hooksPath='+str(hooks),'merge','--ff-only',evidence_head)
        clean(repo);require(git_text(repo,'rev-parse','HEAD')==evidence_head,'local fast-forward mismatch')
        if args.push:
            subprocess.run(['git','-C',str(repo),'push','origin',f'HEAD:refs/heads/{BRANCH}'],check=True)
        pr=('## Phase 17A-C local-first development\n\nKeep PR #68 draft and unmerged.\n\n'
            f'Current evidence head: `{evidence_head}`. Tested Phase 17C source: `{source}`.\n\n'
            'Implemented: historical bootstrap and objective freeze; present-only controller; '
            'fresh evaluator-owned challenge after freeze; separate worker with bounded JSON/data-only protocol; '
            'candidate artifact freezing, independent DSL semantics, single-turn integration and sealed transcript recomputation.\n\n'
            f'Owner local validation: {FOUNDATION_TESTS} foundation, {PROCESS_TESTS} subprocess/differential, '
            f'{ARCHIVE_TESTS} archive tests, zero failures/skips. OS: {result["environment"]["os"]}; '
            f'Python: {result["environment"]["python_version"]}. '
            f'One unfiltered fresh trial: `{result["single_transaction_terminal"]}`, '
            f'{result["single_transaction_evaluations"]} evaluated candidates. '
            f'Evidence: `{EVIDENCE_ROOT}/operator-{source[:12]}/operator-validation.json`.\n\n'
            'This is bounded integer-vector DSL evaluation, not full model evaluation, '
            'a hostile-process sandbox, fresh Lean verification, full-frontier recertification, '
            'promotion, Phase 18 independent replay, or a completed open-horizon campaign. '
            'Global challenge replay protection and restart durability remain unimplemented.\n\n'
            'The earlier Phase 17B failure and successful Windows evidence remain preserved. '
            'Hosted CI is blocked by the previously reported billing lock; no hosted success claimed. '
            '`phase17_exit_closed=false`, `gate_e_closed=false`, `egc0_started=false`. '
            'No main merge, release/tag/DOI change, reset or force push.\n')
        (run/'PR_UPDATE.md').write_text(pr,encoding='utf-8',newline='\n')
        summary={'completed':True,'tested_code_head':source,'evidence_head':evidence_head,
                 'pushed':bool(args.push),'pr_description_file':str(run/'PR_UPDATE.md'),
                 'foundation_tests':FOUNDATION_TESTS,'process_and_differential_tests':PROCESS_TESTS,
                 'historical_archive_tests':ARCHIVE_TESTS,'phase17_exit_closed':False,
                 'gate_e_closed':False,'egc0_started':False,'pr68_keep_draft':True}
        json_write(run/'progress.json',summary);print(json.dumps(summary,indent=2))
        return 0
    except Exception as exc:
        message=str(exc)
        if isinstance(exc,subprocess.CalledProcessError) and exc.stderr:
            message += '\n'+exc.stderr.decode('utf-8',errors='replace')[-4000:]
        print('STOP: '+message,file=sys.stderr)
        print('Workspace and logs retained at '+str(run),file=sys.stderr)
        print('No reset, force push or merge to main performed. Inspect progress.json before retrying.',file=sys.stderr)
        return 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print('STOP before validation: '+str(exc),file=sys.stderr);raise SystemExit(1)
