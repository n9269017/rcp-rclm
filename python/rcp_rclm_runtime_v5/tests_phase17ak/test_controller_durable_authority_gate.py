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
SPEC = importlib.util.spec_from_file_location('phase17ak_gate_fixture',
    ROOT / 'scripts/run_phase17_controller_durable_authority_gate.py')
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
        with self.assertRaisesRegex(ValueError, 'external AK output'):
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



class NativeLifetimeInventoryTests(unittest.TestCase):
    def test_duplicate_native_invocation_identity_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            packet = {'native_boots': [{'name': 'a'}, {'name': 'b'}]}
            for name in ('a', 'b'):
                path = out / 'durable-native' / name / 'start.json'
                path.parent.mkdir(parents=True)
                path.write_bytes(gate.canonical({'invocation_id': 'a'*32, 'python_sha256': 'b'*64}))
            with patch.object(gate, 'verify_durable_native_records', return_value={'fixture': 'c'*64}):
                with self.assertRaisesRegex(ValueError, 'reuse an invocation identity'):
                    gate.verify_authority_native(out, packet)

    def test_different_native_interpreter_identity_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            packet = {'native_boots': [{'name': 'a'}, {'name': 'b'}]}
            for name in ('a', 'b'):
                path = out / 'durable-native' / name / 'start.json'
                path.parent.mkdir(parents=True)
                path.write_bytes(gate.canonical({'invocation_id': name*32, 'python_sha256': name*64}))
            with patch.object(gate, 'verify_durable_native_records', return_value={'fixture': 'c'*64}):
                with self.assertRaisesRegex(ValueError, 'inconsistent interpreter'):
                    gate.verify_authority_native(out, packet)


class PacketBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.packet = {'schema': gate.PACKET_SCHEMA, 'policy': gate.PACKET_POLICY,
                       'base_commit': gate.BASE, 'purpose': 'controlled parser fixture only'}

    def save(self, packet=None):
        raw = gate.canonical(self.packet if packet is None else packet)
        path = self.out / 'packet.json'; path.write_bytes(raw)
        return path, gate.sha(raw)

    def test_canonical_packet_load_requires_exact_hash(self):
        path, digest = self.save()
        self.assertEqual(gate.load_retained_packet(path, digest), self.packet)
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            gate.load_retained_packet(path, '0'*64)

    def test_packet_rejects_other_phase_schema(self):
        changed = dict(self.packet, schema='rcp-rclm.phase17aj.controller-witness-packet.v1')
        path, digest = self.save(changed)
        with self.assertRaisesRegex(ValueError, 'identity differs'):
            gate.load_retained_packet(path, digest)

    def test_packet_rejects_other_base(self):
        path, digest = self.save(dict(self.packet, base_commit='1'*40))
        with self.assertRaisesRegex(ValueError, 'identity differs'):
            gate.load_retained_packet(path, digest)

    def test_packet_rejects_other_policy(self):
        path, digest = self.save(dict(self.packet, policy='untrusted'))
        with self.assertRaisesRegex(ValueError, 'identity differs'):
            gate.load_retained_packet(path, digest)

    def test_packet_rejects_pretty_json_in_canonical_slot(self):
        raw = json.dumps(self.packet, indent=2).encode()
        path = self.out / 'packet.json'; path.write_bytes(raw)
        with self.assertRaises(ValueError):
            gate.load_retained_packet(path, gate.sha(raw))

    def test_packet_rejects_duplicate_json_keys(self):
        raw = b'{"schema":"one","schema":"two"}'
        path = self.out / 'packet.json'; path.write_bytes(raw)
        with self.assertRaises(ValueError):
            gate.load_retained_packet(path, gate.sha(raw))


if __name__ == '__main__':
    unittest.main()
