"""Gate environment/control regressions, not Lean theorem verification.

The selected functions are compiled directly from the production gate's AST.
Dependency/proof-process fixtures are labeled mocks; the Git descendant test
actually starts ordinary Git. No model package or historical suite is replayed.
"""
from __future__ import annotations
import ast
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT/'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/lean_frontier_gate.py'

def require(condition, message):
    if not condition:
        raise ValueError(message)

def load_gate():
    original = ast.parse(GATE.read_text(encoding='utf-8'))
    names = {'_lean_environment', '_check_prepared_frontier', '_axioms', '_read_regular', 'resolve_toolchain'}
    selected = [n for n in original.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    require({n.name for n in selected} == names, 'required production functions absent')
    mod = types.ModuleType('production_gate_functions')
    mod.__dict__.update(os=os, Path=Path, re=re, shutil=shutil, subprocess=subprocess,
        tempfile=tempfile, require=require, sha=lambda b:hashlib.sha256(b).hexdigest(),
        TOOLCHAIN='leanprover/lean4:v4.31.0', VERSION='4.31.0',
        ROOT_PROJECT='lean/rcp_rclm_formal_core_v4',
        ALLOWED_AXIOMS={'propext','Classical.choice','Quot.sound'})
    code=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+selected,type_ignores=[])
    exec(compile(ast.fix_missing_locations(code),str(GATE),'exec'),mod.__dict__)
    return mod

class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        # Windows TEMP may use an 8.3 alias; compare canonical fixture paths.
        self.root=Path(self.temp.name).resolve(strict=True);self.g=load_gate()
        self.tool=self.root/'lean directory';(self.tool/'bin').mkdir(parents=True)
        self.git=self.root/'Git with spaces'/'cmd'/('git.exe' if os.name=='nt' else 'git')
        self.git.parent.mkdir(parents=True);self.git.write_bytes(b'fixture, not executed')
    def tearDown(self):self.temp.cleanup()
    def fixture_env(self):
        with patch.object(self.g.shutil,'which',return_value=str(self.git)):
            return self.g._lean_environment(self.tool)
    def test_git_directory_retained(self):
        env,exe=self.fixture_env();self.assertIn(str(self.git.parent),env['PATH'].split(os.pathsep));self.assertEqual(exe,self.git)
    def test_toolchain_is_first(self):
        env,_=self.fixture_env();self.assertEqual(env['PATH'].split(os.pathsep)[0],str(self.tool/'bin'))
    def test_caller_path_not_forwarded_wholesale(self):
        with patch.dict(os.environ,{'PATH':str(self.root/'unrelated-secret-tools')},clear=False):
            env,_=self.fixture_env()
        self.assertNotIn('unrelated-secret-tools',env['PATH'])
    def test_secrets_and_injection_settings_not_forwarded(self):
        keys=('GITHUB_TOKEN','AWS_SECRET_ACCESS_KEY','PYTHONPATH','LEAN_PATH','LEAN_SRC_PATH','LAKE_HOME','GIT_DIR','GIT_WORK_TREE','GIT_CONFIG_COUNT','GIT_SSH_COMMAND','GIT_ASKPASS','LD_PRELOAD')
        with patch.dict(os.environ,{k:'do-not-forward' for k in keys},clear=False):env,_=self.fixture_env()
        for k in keys:self.assertNotIn(k,env)
    def test_pinned_toolchain_and_noninteractive_git(self):
        env,_=self.fixture_env();self.assertEqual(env['ELAN_TOOLCHAIN'],'leanprover/lean4:v4.31.0')
        self.assertEqual(env['GIT_TERMINAL_PROMPT'],'0');self.assertEqual(env['GIT_CONFIG_GLOBAL'],os.devnull)
        self.assertEqual(env['GIT_CONFIG_NOSYSTEM'],'1');self.assertEqual(env['LAKE_NO_CACHE'],'true')
    def test_missing_git_is_error(self):
        with patch.object(self.g.shutil,'which',return_value=None),self.assertRaisesRegex(ValueError,'ordinary Git'):
            self.g._lean_environment(self.tool)
    def test_relative_git_is_error(self):
        with patch.object(self.g.shutil,'which',return_value='git'),self.assertRaisesRegex(ValueError,'ordinary Git'):
            self.g._lean_environment(self.tool)
    def test_disappeared_git_is_error(self):
        self.git.unlink()
        with patch.object(self.g.shutil,'which',return_value=str(self.git)),self.assertRaises(OSError):self.g._lean_environment(self.tool)
    def test_relative_default_path_entries_excluded(self):
        with patch.object(os,'defpath','.'+os.pathsep+'relative'+os.pathsep+str(self.root/'system-bin')):env,_=self.fixture_env()
        self.assertTrue(all(Path(p).is_absolute() for p in env['PATH'].split(os.pathsep)))
    def test_windows_systemroot_retained_without_full_path(self):
        with patch.dict(os.environ,{'SystemRoot':str(self.root/'Windows')},clear=True):env,_=self.fixture_env()
        self.assertIn(str(self.root/'Windows'/'System32'),env['PATH'].split(os.pathsep))
        self.assertEqual(env['SYSTEMROOT'],str(self.root/'Windows'))
    def test_relative_systemroot_rejected(self):
        with patch.dict(os.environ,{'SYSTEMROOT':'relative'},clear=True),self.assertRaises(ValueError):self.fixture_env()
    def test_wrong_resolution_rejected(self):
        with patch.object(self.g.shutil,'which',side_effect=[str(self.git),str(self.root/'other-git')]),self.assertRaisesRegex(ValueError,'restricted PATH'):
            self.g._lean_environment(self.tool)
    def test_environment_is_not_mutated(self):
        before=dict(os.environ);self.fixture_env();self.assertEqual(dict(os.environ),before)
    def test_missing_child_git_reproduced_and_corrected(self):
        # Recreate a default PATH without Git, analogous to the Windows gate.
        # This uses a real copied Git executable, not a mocked successful process.
        actual=shutil.which('git');self.assertIsNotNone(actual)
        selected=Path(actual).resolve()
        if os.name!='nt':
            shutil.copyfile(selected,self.git);self.git.chmod(0o755);selected=self.git
        child="import subprocess,sys; p=subprocess.run(['git','--version'],capture_output=True); sys.stdout.buffer.write(p.stdout); sys.stderr.buffer.write(p.stderr); sys.exit(p.returncode)"
        restricted_default=str(self.root/'no-system-git')
        with patch.dict(os.environ,{'PATH':str(selected.parent)},clear=False),patch.object(os,'defpath',restricted_default):
            corrected,_=self.g._lean_environment(self.tool)
        broken=dict(corrected,PATH=str(self.tool/'bin')+os.pathsep+restricted_default)
        bad=subprocess.run([sys.executable,'-I','-S','-B','-c',child],env=broken,cwd=self.root,capture_output=True,timeout=30)
        good=subprocess.run([sys.executable,'-I','-S','-B','-c',child],env=corrected,cwd=self.root,capture_output=True,timeout=30)
        self.assertNotEqual(bad.returncode,0);self.assertEqual(good.returncode,0,good.stderr)
        self.assertTrue(good.stdout.startswith(b'git version '))
    def test_real_child_can_launch_git_with_restricted_environment(self):
        env,exe=self.g._lean_environment(self.tool)
        script="import subprocess,sys; p=subprocess.run(['git','--version'],capture_output=True); sys.stdout.buffer.write(p.stdout); sys.stderr.buffer.write(p.stderr); sys.exit(p.returncode)"
        got=subprocess.run([sys.executable,'-I','-S','-B','-c',script],env=env,cwd=self.root,capture_output=True,timeout=30)
        self.assertEqual(got.returncode,0,got.stderr);self.assertTrue(got.stdout.startswith(b'git version '))
        self.assertTrue(exe.is_file())

class GateControlTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.g=load_gate()
        self.tool=self.root/'tool';(self.tool/'bin').mkdir(parents=True)
        suffix='.exe' if os.name=='nt' else ''
        for name in ('lean','lake'):(self.tool/'bin'/(name+suffix)).write_bytes(b'control fixture, not Lean')
        self.sources=tuple(('phase17_'+format(i,'024x'),('theorem fixture_'+str(i)).encode()) for i in range(13))
        self.report={'task_reports':[{'proof_name':n,'source_sha256':hashlib.sha256(b).hexdigest(),'lean_required':True} for n,b in self.sources],
                     'complete_capability_coverage':True,'capability_count':21,'report_hash':'a'*64}
        self.prepared=types.SimpleNamespace(report=self.report,sources=self.sources)
        self.envs=[];self.cmds=[]
    def tearDown(self):self.temp.cleanup()
    def run_gate(self,mode='ok'):
        def proc(argv,cwd,env,**kwargs):
            self.cmds.append(argv);self.envs.append(env)
            if argv[-1]=='--version':return dict(returncode=0,stderr='',stdout='Lean (version 4.31.0, mock)\n')
            name=Path(argv[-1]).stem
            if mode=='wrong-name':name='unrelated'
            if mode=='mutate-lean':(self.tool/'bin'/('lean.exe' if os.name=='nt' else 'lean')).write_bytes(b'mutated')
            return dict(returncode=1 if mode=='reject' else 0,stderr='warning' if mode=='stderr' else '',
                        stdout=f"'{name}' depends on axioms: ["+('sorryAx' if mode=='axiom' else 'propext')+"]\n")
        self.g.root_source_fingerprint=lambda repository:{'fixed':'value'}
        self.g._dependency_state=lambda repository:{'pinned':'state'}
        self.g._process=proc
        return self.g._check_prepared_frontier(self.prepared,self.root,toolchain_root=self.tool)
    def test_mock_success_all_13_no_promotion(self):
        out=self.run_gate();self.assertEqual(out['status'],'passed');self.assertEqual(len(out['proofs']),13)
        for k in ('promotion_authorized','root_transition_verified','recursive_productivity_recertified','phase17_exit_closed','gate_e_closed'):self.assertIs(out[k],False)
        self.assertTrue(Path(out['git_executable']['path']).is_file())
    def test_git_visible_in_all_tool_invocations(self):
        self.run_gate()
        for env in self.envs:self.assertIsNotNone(shutil.which('git',path=env['PATH']))
        for argv in self.cmds[1:]:self.assertEqual(argv[1:4],['--keep-toolchain','--no-cache','env'])
    def test_proof_rejection_still_rejects(self):self.assertFalse(self.run_gate('reject')['fresh_lean_verified'])
    def test_stderr_still_rejects(self):self.assertFalse(self.run_gate('stderr')['fresh_lean_verified'])
    def test_wrong_theorem_still_rejects(self):self.assertFalse(self.run_gate('wrong-name')['fresh_lean_verified'])
    def test_unapproved_axiom_still_rejects(self):self.assertFalse(self.run_gate('axiom')['fresh_lean_verified'])
    def test_changed_tool_still_rejects(self):self.assertFalse(self.run_gate('mutate-lean')['fresh_lean_verified'])
    def test_missing_git_never_reaches_proof_process(self):
        with patch.object(shutil,'which',return_value=None):out=self.run_gate()
        self.assertEqual(out['status'],'blocked');self.assertEqual(self.cmds,[]);self.assertEqual(out['proofs'],[])
    def test_omitted_obligation_still_rejected(self):
        self.prepared.sources=self.sources[:-1]
        with self.assertRaises(ValueError):self.run_gate()

if __name__=='__main__':unittest.main(verbosity=2)
