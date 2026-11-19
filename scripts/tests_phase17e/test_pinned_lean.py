"""Execution-control unit tests. Fake compiler outputs are NOT Lean proof evidence."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SCRIPT = Path(__file__).resolve().parents[1]/'phase17_pinned_lean.py'
# Also supports this file's repository location under scripts/tests_phase17e.
if not SCRIPT.is_file(): SCRIPT = Path(__file__).resolve().parent/'phase17_pinned_lean.py'
spec=importlib.util.spec_from_file_location('pinned_lean',SCRIPT)
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def recorder(self):
        out=self.root/('report'+str(len(list(self.root.iterdir()))));out.mkdir();return p.Recorder(out)
    def test_safe_relative_accepts(self):
        self.assertEqual(p.relative('lean/module.lean'),'lean/module.lean')
    def test_traversal_and_windows_paths_reject(self):
        for name in ('../x','a/../x','/x','C:/x','a\\b','a//b','x\x00y','CON','a/nul.txt','a.','a '):
            with self.subTest(name=name),self.assertRaises(ValueError):p.relative(name)
    def test_non_string_path_rejects(self):
        for name in (None,False,1,[]):
            with self.assertRaises(ValueError):p.relative(name)
    def test_output_json_exclusive(self):
        path=self.root/'r.json';p.save(path,{'ok':False})
        with self.assertRaises(FileExistsError):p.save(path,{})
    def test_json_nan_rejects(self):
        with self.assertRaises(ValueError):p.save(self.root/'r',{'x':float('nan')})
    def test_regular_file_required(self):
        with self.assertRaises(ValueError):p.regular(self.root/'missing')
    def test_symlink_rejects(self):
        with patch.object(Path,'is_symlink',return_value=True),self.assertRaises(ValueError):p.no_links(self.root)
    def test_environment_does_not_forward_injection(self):
        with patch.dict(os.environ,{'LEAN_PATH':'evil','PYTHONPATH':'evil','GITHUB_TOKEN':'secret','LAKE_OVERRIDE_LEAN':'evil','LAKE_CONFIG':'evil'}):
            env=p.clean_environment(self.root)
        self.assertFalse({'LEAN_PATH','PYTHONPATH','GITHUB_TOKEN','LAKE_OVERRIDE_LEAN','LAKE_CONFIG'} & env.keys())
        self.assertEqual(env['ELAN_TOOLCHAIN'],p.TOOLCHAIN)
    def test_exclusive_lock_cleanup(self):
        cache=self.root/'cache'
        with p.exclusive_cache(cache):self.assertTrue((cache/'in-use.lock').exists())
        self.assertFalse((cache/'in-use.lock').exists())
    def test_second_lock_refused_without_deleting_first(self):
        cache=self.root/'cache'
        with p.exclusive_cache(cache):
            raw=(cache/'in-use.lock').read_bytes()
            with self.assertRaises(FileExistsError):
                with p.exclusive_cache(cache):pass
            self.assertEqual((cache/'in-use.lock').read_bytes(),raw)
    def test_lock_cleanup_after_exception(self):
        cache=self.root/'cache'
        with self.assertRaises(RuntimeError):
            with p.exclusive_cache(cache):raise RuntimeError('controlled')
        self.assertFalse((cache/'in-use.lock').exists())
    def test_changed_lock_is_not_deleted(self):
        cache=self.root/'cache'
        with self.assertRaises(ValueError):
            with p.exclusive_cache(cache):(cache/'in-use.lock').write_bytes(b'other')
        self.assertEqual((cache/'in-use.lock').read_bytes(),b'other')
    def test_exact_axiom_audit(self):
        names=('A.one','A.two')
        got=p.parse_axioms("'A.one' depends on axioms: [propext, Classical.choice]\n'A.two' does not depend on any axioms\n",names)
        self.assertEqual(got,{'A.one':['propext','Classical.choice'],'A.two':[]})
    def test_sorry_axiom_rejected(self):
        with self.assertRaises(ValueError):p.parse_axioms("'x' depends on axioms: [sorryAx]",('x',))
    def test_unapproved_and_duplicate_axioms(self):
        for s in ('myAxiom','propext, propext','Lean.ofReduceBool'):
            with self.assertRaises(ValueError):p.parse_axioms(f"'x' depends on axioms: [{s}]",('x',))
    def test_axiom_names_and_order_bound(self):
        with self.assertRaises(ValueError):p.parse_axioms("'B' depends on axioms: []\n'A' depends on axioms: []",('A','B'))
    def test_extra_audit_output_rejected(self):
        with self.assertRaises(ValueError):p.parse_axioms("'x' depends on axioms: []\nwarning: ignored",('x',))
    def test_missing_audit_rejected(self):
        with self.assertRaises(ValueError):p.parse_axioms('',('x',))
    def test_valid_crlf_audit(self):
        self.assertEqual(p.parse_axioms("'x' depends on axioms: [Quot.sound]\r\n",('x',)),{'x':['Quot.sound']})
    def test_recorder_executes_real_subprocess_once(self):
        r=self.recorder();row=r.checked('actual-python',[sys.executable,'-c','print("measured")'],self.root,dict(os.environ))
        self.assertEqual(row['returncode'],0);self.assertEqual(len(r.commands),1)
        self.assertEqual(r.text(row,'stdout').strip(),'measured')
        self.assertEqual(row['stdout_sha256'],p.file_sha(r.output/row['stdout_path']))
    def test_recorder_failure_preserved(self):
        r=self.recorder()
        with self.assertRaises(ValueError):r.checked('intentional-failure',[sys.executable,'-c','raise SystemExit(7)'],self.root,dict(os.environ))
        self.assertEqual(r.commands[0]['returncode'],7)
    def test_recorder_timeout_preserved(self):
        r=self.recorder();row=r.run('intentional-timeout',[sys.executable,'-c','import time;time.sleep(3)'],self.root,dict(os.environ),timeout=0.1)
        self.assertEqual(row['returncode'],-999);self.assertEqual(row['problem'],'timeout')
    def test_recorder_missing_executable_not_success(self):
        r=self.recorder();row=r.run('absent-tool',[str(self.root/'missing-exe')],self.root,dict(os.environ))
        self.assertEqual(row['returncode'],-998)
    def test_no_download_without_permission(self):
        with patch.object(p.platform,'system',return_value='Windows'),patch.object(p.platform,'machine',return_value='AMD64'),patch.object(p,'urlopen') as network:
            with self.assertRaises(ValueError):p.download_toolchain(self.root,allow_network=False)
            network.assert_not_called()
    def test_no_automatic_linux_tool_install(self):
        with patch.object(p.platform,'system',return_value='Linux'),patch.object(p,'urlopen') as network:
            with self.assertRaises(ValueError):p.download_toolchain(self.root,allow_network=True)
            network.assert_not_called()
    def test_supplied_tool_must_contain_both_executables(self):
        with self.assertRaises(ValueError):p.choose_toolchain(self.root,self.root,allow_network=False)
    def test_existing_download_wrong_hash_rejected(self):
        (self.root/'lean-4.31.0-windows.zip').write_bytes(b'bad')
        with patch.object(p.platform,'system',return_value='Windows'),patch.object(p.platform,'machine',return_value='AMD64'),self.assertRaises(ValueError):
            p.download_toolchain(self.root,allow_network=True)
    def test_partial_download_preserved(self):
        path=self.root/'lean-4.31.0-windows.zip.partial';path.write_bytes(b'partial')
        with patch.object(p.platform,'system',return_value='Windows'),patch.object(p.platform,'machine',return_value='AMD64'),patch.object(p,'urlopen') as network:
            with self.assertRaises(ValueError):p.download_toolchain(self.root,allow_network=True)
            network.assert_not_called()
        self.assertEqual(path.read_bytes(),b'partial')
    def _zip(self,names):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:
            for name in names:z.writestr(name,b'x')
        raw=data.getvalue();(self.root/'lean-4.31.0-windows.zip').write_bytes(raw)
        return dict(p.WIN_ASSET,size=len(raw),sha256=p.sha(raw))
    def test_extraction_traversal_rejected(self):
        asset=self._zip(['../evil'])
        with patch.object(p,'WIN_ASSET',asset),patch.object(p.platform,'system',return_value='Windows'),patch.object(p.platform,'machine',return_value='AMD64'),self.assertRaises(ValueError):
            p.download_toolchain(self.root,allow_network=True)
        self.assertFalse((self.root.parent/'evil').exists())
    def test_extraction_duplicate_rejected(self):
        asset=self._zip(['lean-4.31.0-windows/x','lean-4.31.0-windows/X'])
        with patch.object(p,'WIN_ASSET',asset),patch.object(p.platform,'system',return_value='Windows'),patch.object(p.platform,'machine',return_value='AMD64'),self.assertRaises(ValueError):
            p.download_toolchain(self.root,allow_network=True)
    def test_bounded_extraction_success_fixture(self):
        asset=self._zip(['lean-4.31.0-windows/bin/lean.exe','lean-4.31.0-windows/bin/lake.exe'])
        with patch.object(p,'WIN_ASSET',asset),patch.object(p.platform,'system',return_value='Windows'),patch.object(p.platform,'machine',return_value='AMD64'):
            got=p.download_toolchain(self.root,allow_network=True)
        self.assertEqual((got/'bin/lean.exe').read_bytes(),b'x')
        self.assertEqual(json.loads((self.root/'portable/verified-download.json').read_bytes()),asset)
    def test_incomplete_extraction_not_overwritten(self):
        asset=self._zip(['lean-4.31.0-windows/x']);(self.root/'portable').mkdir()
        with patch.object(p,'WIN_ASSET',asset),patch.object(p.platform,'system',return_value='Windows'),patch.object(p.platform,'machine',return_value='AMD64'),self.assertRaises(ValueError):
            p.download_toolchain(self.root,allow_network=True)
    def test_changed_pin_table_rejected(self):
        path=self.root/p.PINS_REL;path.parent.mkdir(parents=True);path.write_bytes(b'{}')
        with self.assertRaises(ValueError):p.read_pins(self.root)
    def test_existing_output_not_overwritten(self):
        out=self.root/'out';out.mkdir()
        with self.assertRaises(ValueError):p.setup_and_verify(self.root/'repo',out,self.root/'cache',toolchain_root=None,allow_network=False)
    def test_output_in_repo_rejected(self):
        repo=self.root/'repo';repo.mkdir()
        with self.assertRaises(ValueError):p.setup_and_verify(repo,repo/'out',self.root/'cache',toolchain_root=None,allow_network=False)
    def test_blocked_receipt_written_for_missing_pins(self):
        repo=self.root/'repo';repo.mkdir();out=self.root/'out'
        result=p.setup_and_verify(repo,out,self.root/'cache',toolchain_root=None,allow_network=False)
        self.assertEqual(result['status'],'blocked');self.assertFalse(result['actual_lean_capability_verification'])
        self.assertTrue((out/'verification-report.json').is_file());self.assertTrue((out/'SHA256SUMS.txt').is_file())
        self.assertFalse(any(result['claims'].values()))
    def test_no_closure_flags_in_template(self):
        self.assertFalse(any(p.FALSE_CLAIMS.values()))

class MockCompilerControlTests(unittest.TestCase):
    """These controlled fake outputs test fail-closed logic, NOT Lean semantics."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        out=self.root/'out';out.mkdir();self.r=p.Recorder(out)
        self.tool=self.root/'tool';(self.tool/'bin').mkdir(parents=True)
        suffix='.exe' if os.name=='nt' else ''
        for n in ('lean','lake'):(self.tool/'bin'/(n+suffix)).write_bytes(b'fixture')
    def tearDown(self):self.temp.cleanup()
    def fake(self,argv,**kw):
        if argv[-1]=='--version':
            text=b'Lean (version 4.31.0, x86_64, Release)\n' if 'lean' in Path(argv[0]).name else b'Lake version 5.0.0-src+fixture (Lean version 4.31.0)\n'
            kw['stdout'].write(text);return subprocess.CompletedProcess(argv,0)
        if argv[-1].endswith('Positive.lean'):
            kw['stdout'].write(b"'phase17_kernel_sentinel' does not depend on any axioms\n")
            return subprocess.CompletedProcess(argv,0)
        kw['stdout'].write(b"Negative.lean:1:0: error: tactic decide failed\n")
        return subprocess.CompletedProcess(argv,1)
    def test_version_and_probes_controlled_success(self):
        with patch.object(p.subprocess,'run',side_effect=self.fake):
            tools=p.verify_tool_versions(self.tool,self.root,{},self.r)
            p.compiler_probes(self.tool,self.root,{},self.r)
        self.assertEqual(len(tools),2);self.assertEqual(len(self.r.commands),4)
    def test_always_successful_fake_compiler_rejected(self):
        def fake(argv,**kw):
            if argv[-1].endswith('Positive.lean'):kw['stdout'].write(b"'phase17_kernel_sentinel' depends on axioms: []\n")
            return subprocess.CompletedProcess(argv,0)
        with patch.object(p.subprocess,'run',side_effect=fake),self.assertRaisesRegex(ValueError,'negative kernel'):
            p.compiler_probes(self.tool,self.root,{},self.r)
    def test_negative_probe_timeout_not_rejection(self):
        def fake(argv,**kw):
            if argv[-1].endswith('Positive.lean'):return self.fake(argv,**kw)
            raise subprocess.TimeoutExpired(argv,1)
        with patch.object(p.subprocess,'run',side_effect=fake),self.assertRaisesRegex(ValueError,'negative kernel'):
            p.compiler_probes(self.tool,self.root,{},self.r)
    def test_wrong_version_rejected(self):
        def fake(argv,**kw):
            kw['stdout'].write(b'Lean (version 4.32.0, Release)\n');return subprocess.CompletedProcess(argv,0)
        with patch.object(p.subprocess,'run',side_effect=fake),self.assertRaisesRegex(ValueError,'version mismatch'):
            p.verify_tool_versions(self.tool,self.root,{},self.r)
    def test_positive_probe_false_axiom_rejected(self):
        def fake(argv,**kw):
            kw['stdout'].write(b"'phase17_kernel_sentinel' depends on axioms: [sorryAx]\n")
            return subprocess.CompletedProcess(argv,0)
        with patch.object(p.subprocess,'run',side_effect=fake),self.assertRaises(ValueError):
            p.compiler_probes(self.tool,self.root,{},self.r)
    def test_probe_mutation_rejected(self):
        def fake(argv,**kw):
            result=self.fake(argv,**kw)
            if argv[-1].endswith('Negative.lean'):Path(argv[-1]).write_bytes(b'changed')
            return result
        with patch.object(p.subprocess,'run',side_effect=fake),self.assertRaisesRegex(ValueError,'source changed'):
            p.compiler_probes(self.tool,self.root,{},self.r)

class RootSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repository=Path(os.environ.get('PHASE17E_REFERENCE_ROOT', str(Path(__file__).resolve().parents[2])))
        cls.pins=p.read_pins(cls.repository)
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_actual_72_pinned_sources(self):
        self.assertEqual(len(p.verify_root(self.repository,self.pins)),72)
    def test_pinned_source_copy_round_trip(self):
        p.copy_root(self.repository,self.root/'formal',self.pins)
        self.assertEqual(p.verify_root(self.root/'formal',self.pins),self.pins['files'])
    def test_changed_source_rejected(self):
        p.copy_root(self.repository,self.root/'formal',self.pins)
        rel=next(iter(self.pins['files']));(self.root/'formal'/rel).write_bytes(b'changed')
        with self.assertRaises(ValueError):p.verify_root(self.root/'formal',self.pins)
    def test_crlf_checkout_allowed_without_changing_pin(self):
        p.copy_root(self.repository,self.root/'formal',self.pins)
        for rel in self.pins['files']:
            f=self.root/'formal'/rel;f.write_bytes(f.read_bytes().replace(b'\n',b'\r\n'))
        self.assertEqual(len(p.verify_root(self.root/'formal',self.pins)),72)
    def test_extra_root_source_rejected(self):
        p.copy_root(self.repository,self.root/'formal',self.pins)
        (self.root/'formal'/p.ROOT_PROJECT/'Extra.lean').write_text('')
        with self.assertRaises(ValueError):p.verify_root(self.root/'formal',self.pins)
    def test_lake_override_rejected(self):
        p.copy_root(self.repository,self.root/'formal',self.pins)
        f=self.root/'formal'/p.ROOT_PROJECT/'.lake/package-overrides.json';f.parent.mkdir();f.write_bytes(b'{}')
        with self.assertRaises(ValueError):p.verify_root(self.root/'formal',self.pins)
    def test_nine_dependencies_all_commit_locked(self):
        entries=p.locked_dependencies(self.repository)
        self.assertEqual(len(entries),9)
        self.assertEqual(next(x['rev'] for x in entries if x['name']=='mathlib'),'fabf563a7c95a166b8d7b6efca11c8b4dc9d911f')
    def test_missing_deps_refuse_offline_fetch(self):
        p.copy_root(self.repository,self.root/'formal',self.pins)
        out=self.root/'output';out.mkdir();r=p.Recorder(out)
        with self.assertRaises(ValueError):p.prepare_dependencies(self.root/'formal',Path('git'),{},r,allow_network=False)
        self.assertEqual(r.commands,[])

if __name__=='__main__':unittest.main(verbosity=2)
