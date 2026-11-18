"""AL projection and exact compiler-result contracts.

The small transition fixture is computed in memory by the actual runtime
transition functions. It launches no worker and is not native evidence or a
formal acceptance certificate. The separate application gate checks native
records and compiles the generated selected source with pinned Lean.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as object_hash
from rcp_rclm_runtime_v5.phase17 import durable_campaign_lean as formal
from rcp_rclm_runtime_v5.phase17 import durable_campaign as runtime
from rcp_rclm_runtime_v5.phase17.campaign_transaction import load_predecessor
from rcp_rclm_runtime_v5.phase17.resource_ledger import Policy, full_grammar_policy

ROOT = Path(__file__).resolve().parents[3]


def transition_fixture(parent, *, denied=False):
    envelope = full_grammar_policy(len(parent.accepted_programs), candidate_limit=2)
    policy = Policy((0, 0, 0, 0), 0) if denied else Policy(
        tuple(2 * value for value in envelope.limits), 2 * envelope.cost_limit)
    provision = runtime.make_provision(ROOT, parent, policy, 'formal-generator-unit-fixture', 'a' * 64)
    pin = object_hash(provision)
    snapshot = runtime._initial(provision)
    event = runtime._event(pin, snapshot, previous=None, kind='provision', epoch=0,
                           boot_nonce=None, request=None, session=None)
    entries = [{'event': event, 'snapshot': snapshot}]
    for kind in (('reopen', 'deny') if denied else ('reopen', 'reserve', 'launch', 'reopen')):
        before = entries[-1]
        cursor = runtime._cursor(pin, before['event'])
        epoch = cursor['epoch'] + int(kind == 'reopen')
        request = ({'expected_cursor': cursor, 'request_nonce': 'c' * 64, 'credits': 2}
                   if kind in ('reserve', 'deny') else None)
        snapshot = runtime._next_snapshot(before['snapshot'], provision, parent, cursor,
            kind=kind, epoch=epoch, request=request, session=None)
        event = runtime._event(pin, snapshot, previous=cursor, kind=kind, epoch=epoch,
            boot_nonce=('b' * 63 + str(epoch)) if kind == 'reopen' else None,
            request=request, session=None)
        entries.append({'event': event, 'snapshot': snapshot})
    return provision, entries


class ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = load_predecessor(ROOT)
        cls.provision, cls.entries = transition_fixture(cls.parent)
        cls.denied_provision, cls.denied_entries = transition_fixture(cls.parent, denied=True)

    def test_projection_uses_exact_current_root_cursor(self):
        entry = self.entries[2]
        state = formal._state_projection(entry, self.provision)
        cursor = runtime._cursor(object_hash(self.provision), entry['event'])
        self.assertEqual([state[key] for key in ('provision', 'epoch', 'serial', 'head', 'journal', 'image')],
                         [cursor[key] for key in ('root_provision_sha256', 'epoch', 'serial',
                                                 'root_head', 'journal_sha256', 'snapshot_sha256')])

    def test_reserved_vector_comes_from_replayed_campaign_journal(self):
        state = formal._state_projection(self.entries[2], self.provision)
        envelope = full_grammar_policy(len(self.parent.accepted_programs), candidate_limit=2)
        self.assertEqual(state['reserved'], list(envelope.limits))
        self.assertEqual(state['session_count'], 1)
        self.assertEqual(state['completed_work'], [0, 0, 0, 0])

    def test_launch_consumption_preserves_reserved_work(self):
        before = formal._state_projection(self.entries[2], self.provision)
        after = formal._state_projection(self.entries[3], self.provision)
        self.assertFalse(before['pending']['launched'])
        self.assertTrue(after['pending']['launched'])
        self.assertEqual(before['reserved'], after['reserved'])
        self.assertEqual(before['journal'], after['journal'])

    def test_reopen_revokes_owner_without_refund_or_reissue(self):
        before = formal._state_projection(self.entries[3], self.provision)
        after = formal._state_projection(self.entries[4], self.provision)
        self.assertEqual(before['pending']['owner_epoch'], 1)
        self.assertIsNone(after['pending']['owner_epoch'])
        self.assertTrue(after['pending']['launched'])
        self.assertEqual(after['epoch'], 2)
        self.assertEqual(before['reserved'], after['reserved'])
        self.assertEqual(before['session_count'], after['session_count'])

    def test_denial_adds_no_reservation(self):
        before = formal._state_projection(self.denied_entries[1], self.denied_provision)
        after = formal._state_projection(self.denied_entries[2], self.denied_provision)
        self.assertEqual(before['reserved'], after['reserved'])
        self.assertEqual(after['status'], 'resource_exhausted')
        self.assertEqual(after['nonces'], ['c' * 64])

    def test_admission_command_comes_from_retained_request_and_grant(self):
        command = formal._command_projection(self.entries[1], self.entries[2], self.provision)
        permit = self.entries[2]['snapshot']['pending']['permit']
        self.assertEqual(command['grant'], permit['grant']['grant_hash'])
        self.assertEqual(command['freeze'], permit['freeze']['freeze_hash'])
        self.assertEqual(command['nonce'], permit['request_nonce'])
        self.assertEqual(command['credits'], permit['grant']['candidate_credits'])

    def test_changed_admission_credits_cannot_change_projection(self):
        entry = deepcopy(self.entries[2]); entry['event']['request']['credits'] = 3
        with self.assertRaisesRegex(ValueError, 'admission body projection'):
            formal._command_projection(self.entries[1], entry, self.provision)

    def test_pending_grant_substitution_is_refused(self):
        entry = deepcopy(self.entries[2])
        entry['snapshot']['pending']['permit']['grant']['grant_hash'] = 'd' * 64
        with self.assertRaisesRegex(ValueError, 'pending authorization projection'):
            formal._state_projection(entry, self.provision)

    def test_pending_cannot_be_removed_from_projection(self):
        entry = deepcopy(self.entries[2]); entry['snapshot']['pending'] = None
        with self.assertRaisesRegex(ValueError, 'durable pending and campaign journal'):
            formal._state_projection(entry, self.provision)

    def test_truncated_journal_is_refused(self):
        entry = deepcopy(self.entries[2])
        entry['snapshot']['journal_hex'] = bytes.fromhex(entry['snapshot']['journal_hex'])[:-1].hex()
        with self.assertRaisesRegex(ValueError, 'newline'):
            formal._state_projection(entry, self.provision)

    def test_completed_sessions_cannot_be_invented(self):
        entry = deepcopy(self.entries[2]); entry['snapshot']['sessions'] = [{}]
        with self.assertRaisesRegex(ValueError, 'completed campaign projection'):
            formal._state_projection(entry, self.provision)

    def test_binding_contains_actual_source_parent_policy_and_protocols(self):
        binding = formal._binding(self.provision)
        self.assertEqual(binding['implementation'], self.provision['implementation']['implementation_sha256'])
        self.assertEqual(binding['policy'], object_hash(self.provision['policy']))
        self.assertEqual(binding['parentPackage'], self.provision['context']['predecessor_package_hash'])
        self.assertEqual(binding['objectivePolicy'], self.provision['objective_policy'])
        self.assertEqual(binding['evaluatorProtocol'], self.provision['evaluator_protocol'])
        self.assertEqual(binding['workerProtocol'], self.provision['worker_protocol'])

    def test_unknown_launch_stage_is_refused(self):
        pending = deepcopy(self.entries[2]['snapshot']['pending']); pending['stage'] = 'executed'
        with self.assertRaisesRegex(ValueError, 'unknown campaign launch'):
            formal._pending_projection(pending)

    def test_boolean_owner_or_serial_is_not_a_natural(self):
        pending = deepcopy(self.entries[2]['snapshot']['pending']); pending['owner_epoch'] = True
        with self.assertRaises(ValueError):
            formal._pending_projection(pending)
        entry = deepcopy(self.entries[2]); entry['event']['serial'] = True
        with self.assertRaises(ValueError):
            formal._state_projection(entry, self.provision)

    def test_unprepared_packet_cannot_enter_source_generator(self):
        with self.assertRaisesRegex(ValueError, 'exact prepared durable campaign'):
            formal.project(SimpleNamespace(packet={}, packet_bytes=b'{}'), ROOT)


class CompilerContractTests(unittest.TestCase):
    def audits(self):
        return ''.join("'" + name + "' does not depend on any axioms\n" for name in formal.NAMES)

    def diagnostic(self, label):
        raw = formal.render_negative(label); line, col = formal.negative_location(raw)
        return raw, f'{label}.lean:{line}:{col}: error: Tactic `decide` proved that the proposition\n  False\nis false\n'

    def test_fixed_audit_inventory_accepts_exact_output(self):
        self.assertEqual(formal.parse_audits(self.audits()), {name: [] for name in formal.NAMES})
        self.assertEqual((len(formal.MODULES), len(formal.NAMES), len(formal.NEGATIVES)), (1, 39, 20))

    def test_missing_reordered_or_extra_audit_is_refused(self):
        lines = self.audits().splitlines(keepends=True)
        for output in (''.join(lines[1:]), ''.join(lines[1:2] + lines[:1] + lines[2:]), self.audits() + 'extra\n'):
            with self.subTest(output=output[:80]), self.assertRaises(ValueError):
                formal.parse_audits(output)

    def test_unapproved_or_duplicate_axiom_is_refused(self):
        for replacement in ('[sorryAx]', '[propext, propext]'):
            output = self.audits().replace('does not depend on any axioms', 'depends on axioms: ' + replacement, 1)
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                formal.parse_audits(output)

    def test_every_negative_has_exact_designated_final_failure(self):
        for label in formal.NEGATIVES:
            raw, diagnostic = self.diagnostic(label)
            with self.subTest(label=label):
                result = formal.validate_negative(label, raw, diagnostic, '', 1)
                self.assertTrue(result['intended_rejection'])
                self.assertIn(b'theorem actual_rejection : wrongClaim = false := by decide +kernel', raw)

    def test_arbitrary_failure_missing_import_or_wrong_exit_is_refused(self):
        label = formal.NEGATIVES[0]; raw, diagnostic = self.diagnostic(label)
        for output, error, code in (('error: unknown module\n', '', 1), (diagnostic, 'crash', 1),
                                     (diagnostic, '', 0), (diagnostic, '', True), (diagnostic, '', 2)):
            with self.subTest(code=code, error=error), self.assertRaises(ValueError):
                formal.validate_negative(label, raw, output, error, code)

    def test_wrong_location_or_additional_diagnostic_is_refused(self):
        label = formal.NEGATIVES[0]; raw, diagnostic = self.diagnostic(label)
        for output in (diagnostic.replace(':10:2:', ':9:2:'), diagnostic + 'warning: ignored\n'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                formal.validate_negative(label, raw, output, '', 1)

    def test_changed_final_assertion_shape_is_refused(self):
        label = formal.NEGATIVES[0]; raw, diagnostic = self.diagnostic(label)
        with self.assertRaisesRegex(ValueError, 'negative assertion tactic'):
            formal.validate_negative(label, raw.replace(b'  decide\n', b'  trivial\n'), diagnostic, '', 1)

    def test_natural_and_usage_literals_refuse_bool_negative_and_wrong_dimensions(self):
        for value in (True, -1, 1.0, 1 << 63):
            with self.subTest(value=value), self.assertRaises(ValueError):
                formal._nat(value)
        for value in ([1, 2, 3], [1, 2, 3, True]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                formal._usage(value)


if __name__ == '__main__':
    unittest.main()
