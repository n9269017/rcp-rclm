"""AN protected fixed-worker adapter over AL's unchanged durable transitions.

Reservation, once-only launch consumption, completion, reopening and root
verification remain AL operations. Only the actual worker launcher and its
native record validator are replaced by explicit AN implementations. No global
module object, captured native command or historical AL record is patched.
"""
from __future__ import annotations

import os
from pathlib import Path

from rcp_rclm_runtime.canonical.json import load_json_strict
from .durable_campaign import (DurableCampaignAuthority, _fault, _same, _copy,
    _append_journal, require, canonical, sha, SCOPE, OLD_FALSE_CLAIMS, UNMEASURED,
    bind_phase16_search, reference_grammar, digest, decide, Action, realize_candidate,
    record_evaluation, check_controller, checkpoint, verify_metered_transcript)


class ProtectedCampaignAuthority(DurableCampaignAuthority):
    def __init__(self, *args, protected_paths=(), **kwargs):
        super().__init__(*args, **kwargs)
        targets = [self.root_directory, *[Path(p).absolute() for p in protected_paths]]
        self.protected_paths = tuple(dict.fromkeys(targets))

    def run_session(self, *, expected_cursor, request_nonce, credits):
        permit = self._reserve(expected_cursor, request_nonce, credits)
        self._consume_launch()
        launch_cursor = self.cursor
        grant = permit['grant']; objective = permit['objective']; freeze = permit['freeze']
        reservation_head = self._state.head
        native_directory = self.root_directory / 'worker-native' / grant['grant_hash']
        _fault('before_worker_launch')
        from .protected_campaign_native import ProtectedCampaignEvaluatorClient, verify_native_records
        try:
            with ProtectedCampaignEvaluatorClient(grant, native_directory=native_directory,
                    protected_paths=self.protected_paths) as worker:
                public = worker.request('open', objective=objective, freeze=freeze,
                                        candidate_credits=credits)['public_challenge']
                binding = bind_phase16_search(self.parent.phase16_state(), turn_index=grant['session_index'],
                    challenge_commitment_hash=public['challenge_commitment_hash'],
                    public_nonce_hash=request_nonce, candidate_credits=credits)
                actual = [q.to_json() for q in sorted(binding.programs.values(), key=lambda q: q.program_hash)]
                require(actual == list(reference_grammar(self.parent.state, grant['session_index'], request_nonce)) and
                        digest(actual) == public['grammar_hash'], 'live campaign grammar disagreement')
                prefix = binding.prefix
                while decide(prefix).action == Action.EVALUATE:
                    step = decide(prefix)
                    artifact = realize_candidate(binding.programs[step.candidate_hash].to_json(), freeze)
                    receipt = worker.request('freeze_candidate', artifact_hash=artifact['artifact_hash'],
                                             program_hash=artifact['program_hash'])['receipt']
                    report = worker.request('evaluate', artifact=artifact,
                                             candidate_freeze_hash=receipt['candidate_freeze_hash'])
                    require(report['event'] == 'candidate_evaluated' and
                        report['program_hash'] == step.candidate_hash and report['artifact_hash'] == artifact['artifact_hash'] and
                        report['candidate_freeze_hash'] == receipt['candidate_freeze_hash'] and
                        report['evaluation_index'] == len(prefix.observations) and
                        report['evaluation_hash'] == digest({k: v for k, v in report.items() if k != 'evaluation_hash'}),
                        'live campaign evaluation receipt differs')
                    prefix = record_evaluation(prefix, step, verdict=report['verdict'],
                        evaluation_hash=report['evaluation_hash'], reason_codes=report['reason_codes'],
                        predecessor_state_hash=report['predecessor_state_hash'],
                        challenge_commitment_hash=report['challenge_commitment_hash'])
                worker.request('seal', terminal_action=decide(prefix).action.value)
                transcript, accounting = worker.transcript(), worker.accounting
                worker_pid = worker.worker_pid
                require(worker.process.returncode == 0, 'authorized campaign worker did not exit cleanly')
            native = worker.evidence()
            require(type(native) is dict and native and all(type(raw) is bytes for raw in native.values()),
                    'original completed native worker evidence required')
            _same(verify_native_records(native_directory, grant, transcript, accounting,
                                       source_root=self.source_root),
                  {name: sha(raw) for name, raw in native.items()},
                  'original native worker records differ from completed semantics')
            checked_checkpoint = check_controller(self.parent, transcript)
            require(checked_checkpoint == checkpoint(prefix), 'actual live controller transcript differs')
            checked = verify_metered_transcript(self.parent, grant, transcript, accounting)
            completion = {'kind': 'complete', 'grant_hash': grant['grant_hash'], **checked}
            completed_journal = _append_journal(self._snapshot, self._provision, completion)
            completed_head = load_json_strict(bytes.fromhex(completed_journal).splitlines()[-1])['hash']
            files = {'grant.json': canonical(grant), 'objective.json': canonical(objective),
                'objective_freeze.json': canonical(freeze), 'public_challenge.json': canonical(public),
                'sealed_transcript.json': transcript, 'worker-accounting.json': canonical(accounting),
                'controller_checkpoint.json': checked_checkpoint,
                'session.json': canonical({'schema': 'rcp-rclm.phase17o.session.v1',
                    'session_index': grant['session_index'], 'grant_hash': grant['grant_hash'],
                    'campaign_head_before': grant['previous_campaign_head'], 'reservation_head': reservation_head,
                    'campaign_head_after': completed_head, 'completion': completion,
                    'reserved': grant['envelope']['limits'], 'worker_spent': accounting['spent'],
                    'controller_pid': os.getpid(), 'worker_pid': worker_pid,
                    'separate_process': worker_pid != os.getpid(), 'worker_exited_cleanly': True,
                    'fresh_live_challenge': True, 'automatic_retries': 0,
                    'claims': dict(OLD_FALSE_CLAIMS), 'unmeasured': list(UNMEASURED)})}
            session = {'files_hex': {name: raw.hex() for name, raw in files.items()},
                'native_sha256': {name: sha(raw) for name, raw in native.items()},
                'permit_sha256': permit['permit_sha256'], 'launch_cursor': launch_cursor,
                'owner_epoch': launch_cursor['epoch']}
            self._complete(session)
            files['durable-session.json'] = canonical({'schema': 'phase17al.authorized-session.v1',
                'permit': permit, 'launch_cursor': launch_cursor, 'completion_cursor': self.cursor,
                'native_sha256': session['native_sha256'], 'scope': _copy(SCOPE)})
            return files
        except BaseException:
            # Do not synthesize a failed/completed/refunded state from missing
            # process evidence. A fresh lifetime retains the unresolved charge.
            self._poisoned = True
            raise

