"""CLI interruption boundaries; mocked orchestration is not proof evidence."""
from contextlib import ExitStack
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('phase17ah_gate_fixture',
    ROOT / 'scripts/run_phase17_producer_domain_gate.py')
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class GateBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / 'output'

    def test_scope_requires_all_exact_false_booleans(self):
        claims = {name: False for name in gate.FALSE_CLAIMS}
        self.assertTrue(gate.false_claims(claims))
        for value in (True, 0, None, 'false'):
            changed = dict(claims)
            changed['root_transition_verified'] = value
            self.assertFalse(gate.false_claims(changed))

    def test_scope_rejects_missing_extra_and_nonmapping_claims(self):
        claims = {name: False for name in gate.FALSE_CLAIMS}
        missing = dict(claims)
        del missing['root_transition_verified']
        for changed in (missing, dict(claims, undeclared_claim=False), [], None):
            self.assertFalse(gate.false_claims(changed))

    def test_verify_requires_external_execution_hash(self):
        with self.assertRaisesRegex(ValueError, 'independently retained execution hash'):
            gate.main(['--output', str(self.out), '--verify-only'])

    def test_verify_cannot_request_compilation(self):
        with self.assertRaisesRegex(ValueError, 'requires only output'):
            gate.main(['--output', str(self.out), '--verify-only', '--expected-execution-sha256', 'a'*64,
                       '--require-lean'])

    def test_parent_requires_independent_hash(self):
        with self.assertRaisesRegex(ValueError, 'parent path and hash'):
            gate.main(['--output', str(self.out), '--resume-from', str(self.out / 'completion.json')])

    def test_resume_requires_original_plan_hash(self):
        with self.assertRaisesRegex(ValueError, 'retained plan hash'):
            gate.main(['--output', str(self.out), '--resume-from', str(self.out / 'completion.json'),
                       '--expected-parent-sha256', 'a'*64])

    def test_existing_plan_cannot_retarget_toolchain(self):
        with self.assertRaisesRegex(ValueError, 'immutable execution inputs'):
            gate.main(['--output', str(self.out), '--expected-plan-sha256', 'a'*64,
                       '--toolchain-root', str(self.out / 'other-tool')])

    def test_source_tree_cannot_hold_execution_output(self):
        with self.assertRaisesRegex(ValueError, 'external AH output'):
            gate.main(['--output', str(ROOT / 'danger-output')])

    def test_final_stage_parent_can_finalize_without_new_execution(self):
        self.out.mkdir()
        parent = self.out / 'compilation/invocations' / ('1'*32) / 'completion.json'
        parent.parent.mkdir(parents=True)
        parent.write_text('controlled fixture, not formal evidence')
        config = {'stages': [object(), object()]}
        with ExitStack() as stack:
            stack.enter_context(patch.object(gate, 'reconstruct', return_value=({}, 'p'*64, {}, {})))
            stack.enter_context(patch.object(gate, 'configuration', return_value=config))
            stack.enter_context(patch.object(gate.checkpoints, 'verify_manifest',
                return_value={'steps': [{}, {}], 'unresolved_invocations': []}))
            stack.enter_context(patch.object(gate.checker, 'validate_lineage', return_value={}))
            finish = stack.enter_context(patch.object(gate, 'complete'))
            execute = stack.enter_context(patch.object(gate.checkpoints, 'run_stage'))
            self.assertEqual(gate.main(['--output', str(self.out), '--expected-plan-sha256', 'p'*64,
                '--resume-from', str(parent), '--expected-parent-sha256', 'h'*64]), 0)
            finish.assert_called_once()
            execute.assert_not_called()

    def test_final_aggregation_rejects_new_unresolved_reference(self):
        self.out.mkdir()
        parent = self.out / 'compilation/invocations' / ('1'*32) / 'completion.json'
        config = {'stages': [object(), object()]}
        with ExitStack() as stack:
            stack.enter_context(patch.object(gate, 'reconstruct', return_value=({}, 'p'*64, {}, {})))
            stack.enter_context(patch.object(gate, 'configuration', return_value=config))
            stack.enter_context(patch.object(gate.checkpoints, 'verify_manifest',
                return_value={'steps': [{}, {}], 'unresolved_invocations': []}))
            stack.enter_context(patch.object(gate.checker, 'validate_lineage', return_value={}))
            finish = stack.enter_context(patch.object(gate, 'complete'))
            execute = stack.enter_context(patch.object(gate.checkpoints, 'run_stage'))
            with self.assertRaisesRegex(ValueError, 'cannot add unresolved invocation references'):
                gate.main(['--output', str(self.out), '--expected-plan-sha256', 'p'*64,
                    '--resume-from', str(parent), '--expected-parent-sha256', 'h'*64,
                    '--unresolved-invocation', '3'*32])
            finish.assert_not_called()
            execute.assert_not_called()

    def test_final_aggregation_accepts_repeated_retained_reference(self):
        self.out.mkdir()
        parent = self.out / 'compilation/invocations' / ('1'*32) / 'completion.json'
        config = {'stages': [object(), object()]}
        with ExitStack() as stack:
            stack.enter_context(patch.object(gate, 'reconstruct', return_value=({}, 'p'*64, {}, {})))
            stack.enter_context(patch.object(gate, 'configuration', return_value=config))
            stack.enter_context(patch.object(gate.checkpoints, 'verify_manifest',
                return_value={'steps': [{}, {}], 'unresolved_invocations': ['3'*32]}))
            stack.enter_context(patch.object(gate.checker, 'validate_lineage', return_value={}))
            finish = stack.enter_context(patch.object(gate, 'complete'))
            execute = stack.enter_context(patch.object(gate.checkpoints, 'run_stage'))
            self.assertEqual(gate.main(['--output', str(self.out), '--expected-plan-sha256', 'p'*64,
                '--resume-from', str(parent), '--expected-parent-sha256', 'h'*64,
                '--unresolved-invocation', '3'*32]), 0)
            finish.assert_called_once()
            execute.assert_not_called()

    def test_partial_parent_and_exact_hash_reach_new_stage_unchanged(self):
        self.out.mkdir()
        parent = self.out / 'compilation/invocations' / ('1'*32) / 'completion.json'
        config = {'stages': [object(), object(), object()]}
        identity = '2'*32
        result = {'manifest_path': str(self.out / 'compilation/invocations' / identity / 'completion.json'),
                  'manifest_sha256': 'b'*64, 'manifest': {'invocation_id': identity},
                  'completed_stage_count': 2, 'all_stages_completed': False}
        restore_check = object()
        with ExitStack() as stack:
            stack.enter_context(patch.object(gate, 'reconstruct', return_value=({}, 'p'*64, {}, {})))
            stack.enter_context(patch.object(gate, 'configuration', return_value=config))
            verify = stack.enter_context(patch.object(gate.checkpoints, 'verify_manifest',
                return_value={'steps': [{}], 'unresolved_invocations': []}))
            stack.enter_context(patch.object(gate.checker, 'restore_validator', return_value=restore_check))
            stack.enter_context(patch.object(gate.checker, 'validate_lineage', return_value={'status': 'incomplete'}))
            finish = stack.enter_context(patch.object(gate, 'complete'))
            execute = stack.enter_context(patch.object(gate.checkpoints, 'run_stage', return_value=result))
            self.assertEqual(gate.main(['--output', str(self.out), '--expected-plan-sha256', 'p'*64,
                '--resume-from', str(parent), '--expected-parent-sha256', 'h'*64,
                '--unresolved-invocation', '3'*32, '--one-stage']), 0)
            verify.assert_called_once_with(parent, 'h'*64, **config)
            execute.assert_called_once_with(self.out / 'compilation', **config,
                parent_manifest=parent, expected_parent_sha256='h'*64,
                restore_validator=restore_check, unresolved_invocations=('3'*32,))
            finish.assert_not_called()

    def test_one_stage_retains_result_and_does_not_launch_successor(self):
        self.out.mkdir()
        identity = '2'*32
        result = {'manifest_path': str(self.out / 'compilation/invocations' / identity / 'completion.json'),
                  'manifest_sha256': 'b'*64, 'manifest': {'invocation_id': identity},
                  'completed_stage_count': 1, 'all_stages_completed': False}
        with ExitStack() as stack:
            stack.enter_context(patch.object(gate, 'reconstruct', return_value=({}, 'p'*64, {}, {})))
            stack.enter_context(patch.object(gate, 'configuration', return_value={}))
            stack.enter_context(patch.object(gate.checker, 'restore_validator', return_value=object()))
            stack.enter_context(patch.object(gate.checker, 'validate_lineage', return_value={'status': 'incomplete'}))
            execute = stack.enter_context(patch.object(gate.checkpoints, 'run_stage', return_value=result))
            finish = stack.enter_context(patch.object(gate, 'complete'))
            self.assertEqual(gate.main(['--output', str(self.out), '--expected-plan-sha256', 'p'*64,
                                       '--one-stage']), 0)
            execute.assert_called_once()
            finish.assert_not_called()
            receipt = gate.checkpoints._load(self.out / 'progress' / (identity + '.json'))
            self.assertEqual(receipt['manifest_sha256'], 'b'*64)
            self.assertEqual(receipt['formal']['status'], 'incomplete')


class ReferenceJournalRetentionTests(unittest.TestCase):
    """Controlled bytes test preservation; they are not execution evidence."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / 'gate'
        self.packages = self.root / 'packages'
        original = self.packages / 'reference-sessions'
        original.mkdir(parents=True)
        self.images = {spec['name'] + '.jsonl':
            ('controlled journal fixture: ' + spec['name'] + '\n').encode()
            for spec in gate.case_specs()}
        self.packet = {'cases': [{'name': spec['name'], 'result': {'resource': {
            'journal_hex': self.images[spec['name'] + '.jsonl'].hex(),
            'journal_sha256': gate.sha(self.images[spec['name'] + '.jsonl'])}}}
            for spec in gate.case_specs()]}
        for name, raw in self.images.items():
            (original / name).write_bytes(raw)

    def test_exact_original_journals_are_preserved_and_hash_bound(self):
        hashes = gate.retain_reference_journals(self.out, self.packet, self.packages)
        self.assertEqual(hashes, {name: gate.sha(raw) for name, raw in self.images.items()})
        self.assertEqual(gate.verify_reference_journals(self.out, self.packet), hashes)
        for name, raw in self.images.items():
            self.assertEqual((self.out / 'reference-journals' / name).read_bytes(), raw)

    def test_changed_original_cannot_be_replaced_by_packet_image(self):
        name = next(iter(self.images))
        (self.packages / 'reference-sessions' / name).write_bytes(b'changed original')
        with self.assertRaisesRegex(ValueError, 'original AH reference journal differs'):
            gate.retain_reference_journals(self.out, self.packet, self.packages)

    def test_retained_bytes_and_exact_inventory_are_checked(self):
        gate.retain_reference_journals(self.out, self.packet, self.packages)
        name = next(iter(self.images))
        path = self.out / 'reference-journals' / name
        path.write_bytes(b'changed saved journal')
        with self.assertRaisesRegex(ValueError, 'retained AH reference journal bytes differ'):
            gate.verify_reference_journals(self.out, self.packet)
        path.write_bytes(self.images[name])
        extra = path.with_name('unexpected.jsonl')
        extra.write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'retained AH reference journal inventory differs'):
            gate.verify_reference_journals(self.out, self.packet)
        extra.unlink()
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'retained AH reference journal inventory differs'):
            gate.verify_reference_journals(self.out, self.packet)


class PacketFinalizationTests(unittest.TestCase):
    """Real packet/journal bytes; controlled lineage is not formal evidence."""
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.fixture.cleanup)
        cls.packages = Path(cls.fixture.name) / 'packages'
        cls.prepared = gate.prepare_producer_domain(ROOT, cls.packages,
                                                   persist_reference_journals=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / 'gate'
        self.out.mkdir()
        self.raw = self.prepared.packet_bytes
        (self.out / 'packet.json').write_bytes(self.raw)
        journals = gate.retain_reference_journals(self.out, self.prepared.packet, self.packages)
        self.plan = {'packet_sha256': gate.sha(self.raw),
                     'reference_journal_sha256': journals, 'source_commit': '1'*40,
                     'source_tree': '2'*40, 'source_sha256': {}}
        self.result = {'manifest_path': str(self.out / 'compilation/completion.json'),
                       'manifest_sha256': '3'*64}

    def finish(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(gate.checkpoints, 'verify_manifest', return_value={}))
            stack.enter_context(patch.object(gate.checker, 'validate_lineage',
                                            return_value={'controlled_test_fixture': True}))
            stack.enter_context(patch.object(gate, 'source_identity',
                                            return_value=('1'*40, '2'*40, {})))
            stack.enter_context(patch('sys.stdout', new=io.StringIO()))
            return gate.complete(self.out, self.plan, '4'*64, self.result, {})

    def test_finalization_accepts_real_canonical_packet_and_original_journals(self):
        self.assertFalse(self.raw.endswith(b'\n'))
        self.assertTrue(any(byte >= 128 for byte in self.raw))
        digest = self.finish()
        record = gate.checkpoints._load(self.out / 'execution.json', digest)
        self.assertIs(record['completed'], True)
        self.assertTrue(gate.false_claims(record['claims']))
        self.assertEqual((self.out / 'packet.json').read_bytes(), self.raw)

    def test_finalization_rejects_stale_packet_anchor(self):
        self.plan['packet_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'retained packet hash differs'):
            self.finish()
        self.assertFalse((self.out / 'execution.json').exists())

    def test_finalization_rejects_valid_json_packet_substitution(self):
        changed = self.prepared.packet
        changed['base_commit'] = '0'*40
        (self.out / 'packet.json').write_bytes(gate.canonical(changed))
        with self.assertRaisesRegex(ValueError, 'retained packet hash differs'):
            self.finish()
        self.assertFalse((self.out / 'execution.json').exists())

    def test_finalization_rejects_self_rehashed_noncanonical_or_wrong_identity(self):
        changed = self.prepared.packet
        changed['schema'] = 'wrong-schema'
        bad_images = [self.raw + b'\n',
                      json.dumps(self.prepared.packet, sort_keys=True,
                                 separators=(',', ':'), ensure_ascii=True).encode() + b'\n',
                      b'{"schema":"duplicate",' + self.raw[1:], gate.canonical(changed)]
        for raw in bad_images:
            with self.subTest(bytes=len(raw)):
                (self.out / 'packet.json').write_bytes(raw)
                self.plan['packet_sha256'] = gate.sha(raw)
                with self.assertRaises(ValueError):
                    self.finish()
                self.assertFalse((self.out / 'execution.json').exists())

    def test_finalization_rejects_changed_retained_journal(self):
        name = next(iter(self.plan['reference_journal_sha256']))
        (self.out / 'reference-journals' / name).write_bytes(b'changed retained journal')
        with self.assertRaisesRegex(ValueError, 'retained AH reference journal bytes differ'):
            self.finish()
        self.assertFalse((self.out / 'execution.json').exists())


if __name__ == '__main__':
    unittest.main()
