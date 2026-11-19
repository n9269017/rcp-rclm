"""AK proof-generator byte/projection joins, using explicit synthetic roots.

The fixture below contains historical AJ bytes and invented root-event heads.
It tests the generator's join boundary only. It never constructs a validated
AK packet, executes a database/witness, or counts as formal acceptance. Native
root evidence, event hashes and the actual Lean run have separate gates.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime_v5.phase17 import controller_durable_authority_lean as formal
from rcp_rclm_runtime_v5.phase17 import controller_durable_authority as durable
from rcp_rclm_runtime_v5.phase17 import controller_witness as witness_runtime

ROOT = Path(__file__).resolve().parents[3]


def controlled_join_fixture():
    raw = (ROOT / 'artifacts/development/phase17aj/op-1395d6ddf5ce/gate/packet.json').read_bytes()
    aj = load_json_strict(raw)
    witness = SimpleNamespace(packet=aj, packet_bytes=raw)
    cases = []
    for case in aj['witness_cases']:
        provision = {'witness_provision': deepcopy(case['provision']),
                     'witness_provision_sha256': case['provision_sha256']}
        pid = digest(provision)
        witness_lines = bytes.fromhex(aj['journal_images'][case['name'] + '-witness.jsonl']['hex']).splitlines(keepends=True)
        authority_lines = bytes.fromhex(aj['journal_images'][case['name'] + '-authority.jsonl']['hex']).splitlines(keepends=True)
        authority_prefixes = {load_json_strict(line[:-1])['hash']: b''.join(authority_lines[:i + 1])
                              for i, line in enumerate(authority_lines)}
        events = []; before = None; epoch = 0
        for serial, line in enumerate(witness_lines):
            row = load_json_strict(line[:-1])
            kind = 'provision' if serial == 0 else case['records'][serial - 1]['kind']
            epoch += int(kind == 'reopen')
            wraw = b''.join(witness_lines[:serial + 1])
            araw = authority_prefixes[row['body']['authority_head_after']]
            pair = digest({'witness_sha256': formal.sha(wraw), 'authority_sha256': formal.sha(araw)})
            after = {'serial': serial, 'epoch': epoch, 'image_sha256': pair,
                     'witness_cursor': {'revision': serial, 'witness_head': row['hash'],
                                        'authority_head': row['body']['authority_head_after']}}
            event = {'serial': serial, 'epoch': epoch, 'kind': kind, 'before': before,
                     'after': after, 'hash': formal.sha(('SYNTHETIC ROOT ' + case['name'] + str(serial)).encode())}
            events.append({'event': event, 'witness_journal': wraw.decode(), 'authority_journal': araw.decode()})
            before = formal._cursor(pid, event)
        # A deterministic root wrapper for the exact historical first AJ
        # reservation, with SYNTHETIC root heads. No native reply is asserted.
        inner = load_json_strict(witness_lines[2][:-1])['body']['request']
        request = durable.make_request(pid, witness_runtime.PUBLIC_FIXTURE_KEY, inner,
            expected_cursor=formal._cursor(pid, events[1]['event']))
        response = {'root_provision_sha256': pid, 'commit_applied': True,
                    'cursor': formal._cursor(pid, events[2]['event']), 'request_sha256': digest(request)}
        wire = [{'request': request, 'response': response}]
        cases.append({'name': case['name'], 'ai_case_index': case['ai_case_index'], 'wire': wire,
                      'root_provision_sha256': pid, 'evidence': {'root_provision': provision,
                      'root_provision_sha256': pid, 'events': events, 'final_cursor': before}})
    packet = {'durable_cases': cases}
    return SimpleNamespace(packet=packet, packet_bytes=canonical({'synthetic_join_fixture': True}),
                           controller_witness=lambda: witness)


class GeneratorJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = controlled_join_fixture()

    def setUp(self):
        self.packet = deepcopy(self.fixture.packet)
        self.prepared = SimpleNamespace(packet=self.packet, packet_bytes=self.fixture.packet_bytes,
                                        controller_witness=self.fixture.controller_witness)
        self.typed = patch.object(formal, '_prepared', side_effect=lambda value: value)
        self.typed.start(); self.addCleanup(self.typed.stop)

    def validate(self):
        return formal._validate_cases(self.prepared)

    def event(self, case=0, serial=2):
        return self.packet['durable_cases'][case]['evidence']['events'][serial]

    def test_exact_historical_prefix_joins_are_accepted_in_isolation(self):
        _, cases = self.validate()
        self.assertEqual([len(c['evidence']['events']) for c in cases], [8, 4, 5])

    def test_witness_bytes_cannot_lose_lf_framing(self):
        row = self.event(); row['witness_journal'] = row['witness_journal'][:-1]
        with self.assertRaisesRegex(ValueError, 'exact inherited AJ prefix'):
            self.validate()

    def test_authority_image_cannot_come_from_another_case(self):
        self.event()['authority_journal'] = self.event(case=1)['authority_journal']
        with self.assertRaisesRegex(ValueError, 'exact inherited AI prefix'):
            self.validate()

    def test_rehashed_root_provision_cannot_replace_witness_policy(self):
        case = self.packet['durable_cases'][0]; ev = case['evidence']
        ev['root_provision']['witness_provision']['witness_id'] = 'substituted'
        case['root_provision_sha256'] = ev['root_provision_sha256'] = digest(ev['root_provision'])
        with self.assertRaisesRegex(ValueError, 'substituted AJ meanings'):
            self.validate()

    def test_pair_digest_is_recomputed_from_both_complete_images(self):
        self.event()['event']['after']['image_sha256'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'paired-image identity differs'):
            self.validate()

    def test_root_reopen_must_increment_epoch(self):
        event = self.event(serial=1)['event']; event['epoch'] = event['after']['epoch'] = 0
        with self.assertRaisesRegex(ValueError, 'lifetime epoch differs'):
            self.validate()

    def test_regular_mutation_cannot_claim_another_epoch(self):
        event = self.event()['event']; event['epoch'] = event['after']['epoch'] = 2
        with self.assertRaisesRegex(ValueError, 'lifetime epoch differs'):
            self.validate()

    def test_root_serial_cannot_skip_a_publication(self):
        event = self.event()['event']; event['serial'] = event['after']['serial'] = 4
        with self.assertRaisesRegex(ValueError, 'serial or exclusive lifetime'):
            self.validate()

    def test_predecessor_cursor_must_be_exact(self):
        self.event()['event']['before']['root_head'] = 'c' * 64
        with self.assertRaisesRegex(ValueError, 'substituted predecessor cursor'):
            self.validate()

    def test_root_kind_must_match_exact_aj_operation(self):
        self.event()['event']['kind'] = 'execute'
        with self.assertRaisesRegex(ValueError, 'kind differs from AJ transition'):
            self.validate()

    def test_final_cursor_cannot_name_an_earlier_state(self):
        case = self.packet['durable_cases'][0]
        case['evidence']['final_cursor'] = deepcopy(case['evidence']['events'][-1]['event']['before'])
        with self.assertRaisesRegex(ValueError, 'final root cursor differs'):
            self.validate()

    def test_case_must_preserve_authority_interpretation(self):
        self.packet['durable_cases'][0]['ai_case_index'] = 4
        with self.assertRaisesRegex(ValueError, 'root provisioning differs'):
            self.validate()

    def test_publication_cannot_be_omitted(self):
        del self.packet['durable_cases'][0]['evidence']['events'][2]
        with self.assertRaisesRegex(ValueError, 'transition inventory differ'):
            self.validate()

    def test_witness_revision_cannot_be_substituted(self):
        self.event()['event']['after']['witness_cursor']['revision'] = 3
        with self.assertRaisesRegex(ValueError, 'witness cursor differs'):
            self.validate()

    def test_witness_authority_head_cannot_be_substituted(self):
        self.event()['event']['after']['witness_cursor']['authority_head'] = 'a' * 64
        with self.assertRaisesRegex(ValueError, 'witness cursor differs'):
            self.validate()

    def test_valid_join_emits_inherited_transition_proofs(self):
        text = formal.render_selected(self.prepared, ROOT).decode()
        self.assertIn('guard0_2 Phase17AuthorityWitnessExamples.step0_2', text)
        self.assertIn('guard1_3 Phase17AuthorityWitnessExamples.step1_3', text)
        self.assertNotIn('native_decide', text)

    def test_selected_receipt_cannot_use_inner_aj_digest(self):
        wire = self.packet['durable_cases'][0]['wire'][0]
        wire['response']['request_sha256'] = digest(wire['request']['witness_request'])
        with self.assertRaisesRegex(ValueError, 'exact outer root request digest'):
            formal._first_receipt(self.packet['durable_cases'])

    def test_selected_receipt_cannot_use_wire_framing_digest(self):
        wire = self.packet['durable_cases'][0]['wire'][0]
        wire['response']['request_sha256'] = formal.sha(canonical(wire['request']) + b'\n')
        with self.assertRaisesRegex(ValueError, 'exact outer root request digest'):
            formal._first_receipt(self.packet['durable_cases'])

    def test_selected_receipt_rejects_wrong_expected_root_cursor(self):
        wire = self.packet['durable_cases'][0]['wire'][0]
        wire['request']['expected_cursor']['epoch'] = 0
        wire['response']['request_sha256'] = digest(wire['request'])
        with self.assertRaisesRegex(ValueError, 'first root cursor'):
            formal._first_receipt(self.packet['durable_cases'])

    def test_selected_receipt_rejects_rehashed_wrong_aj_request(self):
        wire = self.packet['durable_cases'][0]['wire'][0]
        wire['request']['witness_request']['body']['nonce'] = 'f' * 64
        wire['response']['request_sha256'] = digest(wire['request'])
        with self.assertRaisesRegex(ValueError, 'AJ request that produced its snapshot'):
            formal._first_receipt(self.packet['durable_cases'])

    def test_selected_receipt_requires_unique_captured_reservation(self):
        wires = self.packet['durable_cases'][0]['wire']
        wires.append(deepcopy(wires[0]))
        with self.assertRaisesRegex(ValueError, 'one captured first-reservation'):
            formal._first_receipt(self.packet['durable_cases'])


if __name__ == '__main__':
    unittest.main()
