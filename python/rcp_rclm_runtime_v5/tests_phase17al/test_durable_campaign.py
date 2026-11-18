"""AL protocol tests; replay fixtures are not fresh worker/native evidence."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from rcp_rclm_runtime.canonical.json import load_json_strict
from rcp_rclm_runtime_v5.phase17 import durable_campaign as dc
from rcp_rclm_runtime_v5.phase17 import campaign_budget as budget
from rcp_rclm_runtime_v5.phase17.campaign_transaction import load_predecessor, check_controller, FALSE_CLAIMS, UNMEASURED
from rcp_rclm_runtime_v5.phase17.challenge_protocol import PROTOCOL, transcript_bytes, realize_candidate
from rcp_rclm_runtime_v5.phase17.controller import Action, ControlError, decide, record_evaluation
from rcp_rclm_runtime_v5.phase17.metered_worker import MeteredEvaluatorSession, verify_metered_transcript
from rcp_rclm_runtime_v5.phase17.phase16_adapter import bind_phase16_search
from rcp_rclm_runtime_v5.phase17.resource_ledger import (Policy, ResourceError, ResourceExhausted,
    canonical, full_grammar_policy, sha)

ROOT = Path(__file__).resolve().parents[3]
PARENT = None


def parent():
    global PARENT
    if PARENT is None:
        PARENT = load_predecessor(ROOT)
    return PARENT


def pool(multiplier=2):
    one = full_grammar_policy(len(parent().accepted_programs), candidate_limit=2)
    return Policy(tuple(x * multiplier for x in one.limits), one.cost_limit * multiplier)


def fixture_session(authority, *, reverse=False):
    """Explicit deterministic replay fixture, never used as native evidence."""
    permit = authority.snapshot['pending']['permit']
    grant, objective, freeze = permit['grant'], permit['objective'], permit['freeze']
    evaluator = MeteredEvaluatorSession(parent(), grant)
    opening = {'protocol': PROTOCOL, 'op': 'open', 'objective': objective,
               'freeze': freeze, 'candidate_credits': grant['candidate_credits']}
    public = evaluator._handle(opening, replay_entropy=b'\x42' * 32)['payload']['public_challenge']
    binding = bind_phase16_search(parent().phase16_state(), turn_index=grant['session_index'],
        challenge_commitment_hash=public['challenge_commitment_hash'],
        public_nonce_hash=permit['request_nonce'], candidate_credits=grant['candidate_credits'])
    prefix = binding.prefix
    while decide(prefix).action == Action.EVALUATE:
        step = decide(prefix)
        chosen = step.candidate_hash
        if reverse:
            chosen = next(h for h in reversed(sorted(evaluator.programs))
                          if h not in evaluator.considered and h != chosen)
        artifact = realize_candidate(evaluator.programs[chosen], freeze)
        receipt = evaluator.handle({'protocol': PROTOCOL, 'op': 'freeze_candidate',
            'program_hash': chosen, 'artifact_hash': artifact['artifact_hash']})['payload']['receipt']
        report = evaluator.handle({'protocol': PROTOCOL, 'op': 'evaluate', 'artifact': artifact,
            'candidate_freeze_hash': receipt['candidate_freeze_hash']})['payload']
        if reverse:
            break
        prefix = record_evaluation(prefix, step, verdict=report['verdict'],
            evaluation_hash=report['evaluation_hash'], reason_codes=report['reason_codes'],
            predecessor_state_hash=report['predecessor_state_hash'],
            challenge_commitment_hash=report['challenge_commitment_hash'])
    terminal = evaluator.terminal() or Action.EXTERNAL_STOP.value
    evaluator.handle({'protocol': PROTOCOL, 'op': 'seal', 'terminal_action': terminal})
    transcript, accounting = transcript_bytes(evaluator.events), evaluator.meter.summary()
    checked = verify_metered_transcript(parent(), grant, transcript, accounting)
    completion = {'kind': 'complete', 'grant_hash': grant['grant_hash'], **checked}
    completed = dc._append_journal(authority.snapshot, authority.provision, completion)
    after = load_json_strict(bytes.fromhex(completed).splitlines()[-1])['hash']
    files = {'grant.json': canonical(grant), 'objective.json': canonical(objective),
        'objective_freeze.json': canonical(freeze), 'public_challenge.json': canonical(public),
        'sealed_transcript.json': transcript, 'worker-accounting.json': canonical(accounting),
        'controller_checkpoint.json': b'{}' if reverse else check_controller(parent(), transcript),
        'session.json': canonical({'schema': 'rcp-rclm.phase17o.session.v1',
            'session_index': grant['session_index'], 'grant_hash': grant['grant_hash'],
            'campaign_head_before': grant['previous_campaign_head'],
            'reservation_head': authority.state.head, 'campaign_head_after': after,
            'completion': completion, 'reserved': grant['envelope']['limits'],
            'worker_spent': accounting['spent'], 'controller_pid': 1001, 'worker_pid': 1002,
            'separate_process': True, 'worker_exited_cleanly': True, 'fresh_live_challenge': True,
            'automatic_retries': 0, 'claims': dict(FALSE_CLAIMS), 'unmeasured': list(UNMEASURED)})}
    return {'files_hex': {name: raw.hex() for name, raw in files.items()},
        'native_sha256': {name: sha(('TEST FIXTURE, NOT NATIVE: ' + name).encode()) for name in dc.NATIVE_FILES},
        'permit_sha256': permit['permit_sha256'], 'launch_cursor': authority.cursor,
        'owner_epoch': authority.cursor['epoch']}


class DurableCampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name) / 'authority'
        self.provisioned = dc.provision_root(self.directory, ROOT, parent(), pool(),
            authority_id='phase17al.protocol-tests', nonce='1' * 64)
        self.pin = self.provisioned['root_provision_sha256']
        self.a = self.open('2' * 64)

    def tearDown(self):
        self.a.close()
        self.tmp.cleanup()

    def open(self, nonce):
        return dc.DurableCampaignAuthority(self.directory, parent(),
            expected_root_provision_sha256=self.pin, source_root=ROOT, boot_nonce=nonce)

    def reserve(self, nonce='3' * 64):
        return self.a._reserve(self.a.cursor, nonce, 2)

    def complete_fixture(self, nonce='3' * 64):
        self.reserve(nonce); self.a._consume_launch()
        session = fixture_session(self.a)
        self.a._complete(session)
        return session

    def reopen(self, nonce='4' * 64):
        self.a.close(); self.a = self.open(nonce)

    def test_exact_provision_and_explicit_reference_scope(self):
        self.assertEqual(self.a.provision['context']['installed_count'], 8)
        self.assertEqual(self.a.provision['scope']['deployment'], 'local_reference_only')
        self.assertFalse(self.a.provision['scope']['independently_protected_deployment_established'])
        self.assertFalse(self.a.provision['scope']['complete_resource_accounting'])
        for path in ('scripts/phase17_campaign_worker.py', 'scripts/phase17_durable_campaign_service.py'):
            self.assertEqual(self.a.provision['implementation']['code_sha256'][path],
                             sha((ROOT / path).read_bytes()))

    def test_missing_root_cannot_initialize(self):
        with self.assertRaises(ResourceError):
            dc.DurableCampaignAuthority(Path(self.tmp.name) / 'missing', parent(),
                expected_root_provision_sha256=self.pin, source_root=ROOT, boot_nonce='5' * 64)

    def test_existing_root_cannot_reprovision(self):
        with self.assertRaises(ResourceError):
            dc.provision_root(self.directory, ROOT, parent(), pool(), authority_id='new', nonce='6' * 64)

    def test_wrong_independent_provision_pin_refused(self):
        self.a.close()
        with self.assertRaises(ResourceError):
            dc.DurableCampaignAuthority(self.directory, parent(), expected_root_provision_sha256='f' * 64,
                                       source_root=ROOT, boot_nonce='5' * 64)

    def test_extra_synchronization_is_required(self):
        self.assertEqual(self.a._connection.execute('PRAGMA synchronous').fetchone()[0], 3)
        self.a._connection.execute('PRAGMA synchronous=FULL')
        with self.assertRaises(ResourceError):
            self.a.export_evidence()

    def test_second_live_handle_refused(self):
        with self.assertRaises((OSError, ResourceError)):
            self.open('5' * 64)

    def test_read_export_does_not_publish(self):
        before = self.a.cursor
        self.a.export_evidence(); self.a.export_evidence()
        self.assertEqual(self.a.cursor, before)

    def test_request_checks_each_cursor_field_without_publication(self):
        before = self.a.cursor
        for key in dc.CURSOR_FIELDS:
            cursor = dict(before)
            cursor[key] = cursor[key] + 1 if key in ('epoch', 'serial') else 'f' * 64
            with self.subTest(key=key), self.assertRaises(ResourceError):
                self.a._reserve(cursor, '3' * 64, 2)
            self.assertEqual(self.a.cursor, before)

    def test_extra_cursor_field_refused(self):
        cursor = self.a.cursor; cursor['grant'] = {}
        with self.assertRaises(ResourceError):
            self.a._reserve(cursor, '3' * 64, 2)

    def test_bad_nonce_and_boolean_or_excess_credits_refused(self):
        before = self.a.cursor
        for nonce, credits in [('x', 2), ('3' * 64, True), ('3' * 64, 33), ('3' * 64, -1)]:
            with self.subTest(nonce=nonce, credits=credits), self.assertRaises(ResourceError):
                self.a._reserve(before, nonce, credits)
            self.assertEqual(self.a.cursor, before)

    def test_reservation_persists_exact_nonrefundable_envelope(self):
        permit = self.reserve()
        self.assertEqual(self.a.state.reserved, (2, 88, 352, 352))
        self.assertEqual(self.a.state.charged_cost, 2240)
        self.assertEqual(self.a.state.pending_grant, permit['grant'])
        checked = dc.verify_evidence(self.a.export_evidence(), parent(),
            expected_root_provision_sha256=self.pin, source_root=ROOT)
        self.assertEqual(checked['state'].pending_grant, permit['grant'])

    def test_pending_blocks_second_reservation(self):
        self.reserve(); before = self.a.cursor
        with self.assertRaises(ResourceError):
            self.reserve('5' * 64)
        self.assertEqual(self.a.cursor, before)

    def test_launch_consumption_changes_root_without_new_charge(self):
        self.reserve(); before = self.a.cursor; reserved = self.a.state.reserved
        self.a._consume_launch()
        self.assertEqual(self.a.cursor['serial'], before['serial'] + 1)
        self.assertEqual(self.a.cursor['journal_sha256'], before['journal_sha256'])
        self.assertEqual(self.a.state.reserved, reserved)
        self.assertEqual(self.a.snapshot['pending']['stage'], 'launch_consumed')

    def test_launch_without_reservation_refused(self):
        before = self.a.cursor
        with self.assertRaises(ResourceError): self.a._consume_launch()
        self.assertEqual(self.a.cursor, before)

    def test_second_launch_consumption_refused(self):
        self.reserve(); self.a._consume_launch(); before = self.a.cursor
        with self.assertRaises(ResourceError): self.a._consume_launch()
        self.assertEqual(self.a.cursor, before)

    def test_changed_source_refused_before_launch_consumption(self):
        self.reserve(); before = self.a.cursor
        altered = copy.deepcopy(self.a.provision['implementation'])
        altered['implementation_sha256'] = 'f' * 64
        with patch.object(dc, 'implementation_identity', return_value=altered), self.assertRaises(ResourceError):
            self.a._consume_launch()
        self.assertEqual(self.a.cursor, before)

    def test_reopen_keeps_reserved_charge_and_revokes_owner(self):
        self.reserve(); before = self.a.cursor; reserved = self.a.state.reserved
        self.reopen()
        self.assertEqual(self.a.cursor['epoch'], before['epoch'] + 1)
        self.assertEqual(self.a.state.reserved, reserved)
        self.assertIsNone(self.a.snapshot['pending']['owner_epoch'])
        self.assertEqual(self.a.snapshot['pending']['stage'], 'reserved')
        with self.assertRaises(ResourceError): self.a._consume_launch()
        with self.assertRaises(ResourceError): self.reserve('5' * 64)

    def test_reopen_keeps_consumed_launch_and_forbids_takeover(self):
        self.reserve(); self.a._consume_launch(); session = fixture_session(self.a)
        self.reopen()
        self.assertEqual(self.a.snapshot['pending']['stage'], 'launch_consumed')
        self.assertIsNone(self.a.snapshot['pending']['owner_epoch'])
        with self.assertRaises(ResourceError): self.a._complete(session)
        with self.assertRaises(ResourceError): self.a._consume_launch()

    def test_replayed_boot_nonce_refused(self):
        self.a.close()
        with self.assertRaises(ResourceError): self.open('2' * 64)

    def test_completion_requires_launch_consumption(self):
        self.reserve()
        with self.assertRaises(ResourceError): self.a._complete(fixture_session(self.a))

    def test_completion_requires_current_launch_cursor(self):
        self.reserve(); self.a._consume_launch(); session = fixture_session(self.a)
        session['launch_cursor']['epoch'] += 1
        with self.assertRaises(ResourceError): self.a._complete(session)

    def test_completion_requires_exact_issued_grant(self):
        self.reserve(); self.a._consume_launch(); session = fixture_session(self.a)
        grant = load_json_strict(bytes.fromhex(session['files_hex']['grant.json']))
        grant['candidate_credits'] += 1
        session['files_hex']['grant.json'] = canonical(grant).hex()
        with self.assertRaises(ResourceError): self.a._complete(session)

    def test_completion_requires_exact_objective_freeze(self):
        self.reserve(); self.a._consume_launch(); session = fixture_session(self.a)
        session['files_hex']['objective_freeze.json'] = canonical({'freeze_hash': 'f' * 64}).hex()
        with self.assertRaises(ResourceError): self.a._complete(session)

    def test_completion_recomputes_actual_accounting(self):
        self.reserve(); self.a._consume_launch(); session = fixture_session(self.a)
        accounting = load_json_strict(bytes.fromhex(session['files_hex']['worker-accounting.json']))
        accounting['spent'][0] += 1
        session['files_hex']['worker-accounting.json'] = canonical(accounting).hex()
        with self.assertRaisesRegex(ControlError, 'worker accounting mismatch'): self.a._complete(session)

    def test_completion_rechecks_actual_controller_order(self):
        self.reserve(); self.a._consume_launch(); session = fixture_session(self.a, reverse=True)
        with self.assertRaisesRegex(ControlError, 'proposal not the present controller choice'): self.a._complete(session)

    def test_completion_requires_exact_native_binding_inventory(self):
        self.reserve(); self.a._consume_launch(); session = fixture_session(self.a)
        del session['native_sha256']['result.json']
        with self.assertRaises(ResourceError): self.a._complete(session)

    def test_valid_completion_retains_full_not_actual_charge(self):
        session = self.complete_fixture()
        self.assertEqual(self.a.state.reserved, (2, 88, 352, 352))
        self.assertEqual(self.a.state.status, 'open')
        self.assertEqual(len(self.a.snapshot['sessions']), 1)
        self.assertIsNone(self.a.snapshot['pending'])
        self.assertEqual(self.a.snapshot['sessions'][0], session)

    def test_completed_nonce_cannot_authorize_new_session(self):
        self.complete_fixture(); before = self.a.cursor
        with self.assertRaises(ResourceError): self.reserve()
        self.assertEqual(self.a.cursor, before)

    def test_completed_session_cannot_be_completed_again(self):
        session = self.complete_fixture(); before = self.a.cursor
        with self.assertRaises(ResourceError): self.a._complete(session)
        self.assertEqual(self.a.cursor, before)

    def test_two_sessions_across_restart_share_charges(self):
        self.complete_fixture(); self.reopen()
        self.complete_fixture('5' * 64)
        self.assertEqual(self.a.state.session_count, 2)
        self.assertEqual(self.a.state.reserved, (4, 176, 704, 704))
        self.assertEqual(len(self.a.snapshot['sessions']), 2)

    def test_aggregate_denial_publishes_without_launch(self):
        self.complete_fixture(); self.complete_fixture('5' * 64)
        before = self.a.cursor
        with self.assertRaises(ResourceExhausted): self.reserve('6' * 64)
        self.assertEqual(self.a.cursor['serial'], before['serial'] + 1)
        self.assertEqual(self.a.state.status, 'resource_exhausted')
        self.assertEqual(self.a.state.reserved, (4, 176, 704, 704))
        self.assertIsNone(self.a.snapshot['pending'])
        self.assertFalse((self.directory / 'worker-native').exists())

    def test_rehashed_snapshot_cannot_erase_consumed_nonce(self):
        self.reserve()
        evidence = self.a.export_evidence()
        entry = evidence['entries'][-1]; entry['snapshot']['nonces'] = []
        event = entry['event']
        previous = dc._cursor(self.pin, evidence['entries'][-2]['event'])
        entry['event'] = dc._event(self.pin, entry['snapshot'], previous=previous, kind=event['kind'],
            epoch=event['epoch'], boot_nonce=None, request=event['request'], session=None)
        evidence['final_cursor'] = dc._cursor(self.pin, entry['event'])
        with self.assertRaises(ResourceError):
            dc.verify_evidence(evidence, parent(), expected_root_provision_sha256=self.pin, source_root=ROOT)

    def test_rehashed_reopen_cannot_restore_old_owner(self):
        self.reserve(); self.reopen()
        evidence = self.a.export_evidence(); entry = evidence['entries'][-1]
        entry['snapshot']['pending']['owner_epoch'] = entry['event']['epoch']
        event = entry['event']; previous = dc._cursor(self.pin, evidence['entries'][-2]['event'])
        entry['event'] = dc._event(self.pin, entry['snapshot'], previous=previous, kind='reopen',
            epoch=event['epoch'], boot_nonce=event['boot_nonce'], request=None, session=None)
        evidence['final_cursor'] = dc._cursor(self.pin, entry['event'])
        with self.assertRaises(ResourceError):
            dc.verify_evidence(evidence, parent(), expected_root_provision_sha256=self.pin, source_root=ROOT)

    def test_database_metadata_tamper_refused(self):
        connection = sqlite3.connect(self.directory / 'authority.sqlite3')
        try:
            connection.execute('UPDATE metadata SET image=?', (b'{}',)); connection.commit()
        finally:
            connection.close()
        with self.assertRaises(ResourceError): self.a.export_evidence()

    def test_precommit_fault_retains_old_root(self):
        def fault(stage):
            if stage == 'reserve:before_commit': raise OSError('controlled precommit failure')
        with patch.object(dc, '_fault', side_effect=fault), self.assertRaises(OSError): self.reserve()
        self.reopen()
        self.assertEqual(self.a.state.reserved, (0, 0, 0, 0))
        self.assertIsNone(self.a.snapshot['pending'])

    def test_postcommit_ack_loss_keeps_charge_and_revokes_owner(self):
        def fault(stage):
            if stage == 'reserve:after_commit': raise OSError('controlled acknowledgement loss')
        with patch.object(dc, '_fault', side_effect=fault), self.assertRaises(OSError): self.reserve()
        self.reopen()
        self.assertEqual(self.a.state.reserved, (2, 88, 352, 352))
        self.assertIsNone(self.a.snapshot['pending']['owner_epoch'])

    def test_whole_root_clone_counterexample_remains_explicit(self):
        self.a.close()
        clone = Path(self.tmp.name) / 'cloned-authority'
        shutil.copytree(self.directory, clone)
        self.a = self.open('4' * 64)
        with dc.DurableCampaignAuthority(clone, parent(), expected_root_provision_sha256=self.pin,
                                        source_root=ROOT, boot_nonce='4' * 64) as other:
            first = self.a._reserve(self.a.cursor, '3' * 64, 2)
            second = other._reserve(other.cursor, '3' * 64, 2)
            self.assertEqual(first, second)
            self.assertEqual(self.a.cursor, other.cursor)


class NativeCrashTests(unittest.TestCase):
    def crash_at(self, stage, expected_pending, expected_launch):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'root'
            provisioned = dc.provision_root(directory, ROOT, parent(), pool(),
                authority_id='phase17al.crash-test', nonce='7' * 64)
            code = "\n".join([
                'from pathlib import Path', 'import os,sys',
                'root=Path(' + repr(str(ROOT)) + ')',
                "sys.path[:0]=[str(root/'python'/('rcp_rclm_runtime_v'+str(v))) for v in (2,3,4,5)]",
                'from rcp_rclm_runtime_v5.phase17 import durable_campaign as dc',
                'from rcp_rclm_runtime_v5.phase17.campaign_transaction import load_predecessor',
                'def fault(stage):',
                '    if stage == ' + repr(stage) + ': os._exit(73)',
                'dc._fault=fault',
                'a=dc.DurableCampaignAuthority(Path(' + repr(str(directory)) + '),load_predecessor(root),'
                + 'expected_root_provision_sha256=' + repr(provisioned['root_provision_sha256'])
                + ',source_root=root,boot_nonce=' + repr('8' * 64) + ')',
                "a.run_session(expected_cursor=a.cursor,request_nonce='9'*64,credits=2)",
                'raise SystemExit(99)',
            ])
            process = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            self.assertEqual(process.returncode, 73, process.stderr.decode(errors='replace'))
            self.assertEqual(process.stdout, b''); self.assertEqual(process.stderr, b'')
            with dc.DurableCampaignAuthority(directory, parent(),
                    expected_root_provision_sha256=provisioned['root_provision_sha256'],
                    source_root=ROOT, boot_nonce='a' * 64) as authority:
                self.assertEqual(authority.state.reserved,
                                 (2, 88, 352, 352) if expected_pending else (0, 0, 0, 0))
                pending = authority.snapshot['pending']
                if expected_pending:
                    self.assertIsNone(pending['owner_epoch'])
                    self.assertEqual(pending['stage'], expected_launch)
                    with self.assertRaises(ResourceError): authority._consume_launch()
                else:
                    self.assertIsNone(pending)
                self.assertFalse((directory / 'worker-native').exists())

    def test_native_death_before_reservation_commit(self):
        self.crash_at('reserve:before_commit', False, None)

    def test_native_death_after_reservation_commit(self):
        self.crash_at('reserve:after_commit', True, 'reserved')

    def test_native_death_after_launch_consumption(self):
        self.crash_at('after_launch_consumption', True, 'launch_consumed')

    def test_native_death_immediately_before_worker_launch(self):
        self.crash_at('before_worker_launch', True, 'launch_consumed')


if __name__ == '__main__':
    unittest.main()
