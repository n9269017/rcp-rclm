"""CLI interruption boundaries; mocked orchestration is not proof evidence."""
from contextlib import ExitStack
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('phase17ac_gate_fixture',
    ROOT / 'scripts/run_phase17_controller_continuation_gate.py')
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class GateBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / 'output'

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
        with self.assertRaisesRegex(ValueError, 'external AC output'):
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


if __name__ == '__main__':
    unittest.main()
