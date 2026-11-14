"""Real subprocess checks using retained historical archives, no simulated worker."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import queue
import sys
import unittest
from unittest.mock import patch

from rcp_rclm_runtime_v5.phase17.bootstrap import reopen_phase16
from rcp_rclm_runtime_v5.phase17.challenge_client import EvaluatorClient, worker_environment
from rcp_rclm_runtime_v5.phase17.challenge_protocol import (
    realize_candidate, reference_grammar, verify_transcript, digest, CLAIMS,
)
from rcp_rclm_runtime_v5.phase17.controller import Action, ControlError
from rcp_rclm_runtime_v5.phase17.objectives import select_bootstrap_objective, freeze_bootstrap_objective

ROOT=Path(__file__).resolve().parents[3]


def historical_parent():
    return reopen_phase16(
        capture_archive=ROOT/'artifacts/development/phase17b/phase16-capture-31153935872-1.zip',
        closure_archive=ROOT/('artifacts/releases/v4.5-phase15-phase16-results/original-artifacts/'
                              'runtime-v4-phase16-final-closure-31153935872-1.zip'),
        phase15_bundle=ROOT/'artifacts/private_phase16/bootstrap/runtime-v4-phase15-bundle-30969783629-1.zip')


class ProcessBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=historical_parent()
        cls.objective=select_bootstrap_objective(cls.parent,turn_index=0,public_nonce_hash='8'*64)
        cls.freeze=freeze_bootstrap_objective(cls.objective,cls.parent,turn_index=0,public_nonce_hash='8'*64)

    def opened(self,client,credits=2):
        return client.request('open',objective=self.objective.to_json(),freeze=self.freeze,candidate_credits=credits)

    def test_real_worker_has_distinct_pid_and_sealed_recomputation(self):
        with EvaluatorClient() as client:
            public=self.opened(client,0)
            self.assertNotEqual(client.process.pid,os.getpid())
            self.assertEqual(public['claims'],CLAIMS)
            client.request('seal',terminal_action=Action.RESOURCE_EXHAUSTED.value)
            data=client.transcript()
            result=verify_transcript(self.parent,data,expected_transcript_hash=hashlib.sha256(data).hexdigest())
            self.assertEqual(result.candidate_evaluations,0)
            self.assertEqual(client.process.returncode,0)

    def test_real_worker_freeze_and_evaluate(self):
        with EvaluatorClient() as client:
            public=self.opened(client,1)['public_challenge']
            programs=reference_grammar(self.parent.state,0,self.freeze['public_nonce_hash'])
            self.assertEqual(public['grammar_hash'],digest(list(programs)))
            artifact=realize_candidate(programs[0],self.freeze)
            receipt=client.request('freeze_candidate',program_hash=artifact['program_hash'],artifact_hash=artifact['artifact_hash'])['receipt']
            result=client.request('evaluate',candidate_freeze_hash=receipt['candidate_freeze_hash'],artifact=artifact)
            action=Action.AWAIT_ROOT_VERIFICATION if result['verdict']=='candidate_passed' else Action.RESOURCE_EXHAUSTED
            client.request('seal',terminal_action=action.value)
            data=client.transcript()
            self.assertEqual(verify_transcript(self.parent,data,expected_transcript_hash=hashlib.sha256(data).hexdigest()).candidate_evaluations,1)

    def test_live_worker_no_seed_override(self):
        with EvaluatorClient() as client:
            with self.assertRaises(ControlError):
                client.request('open',objective=self.objective.to_json(),freeze=self.freeze,candidate_credits=1,seed='0'*64)
            self.assertTrue(client.closed)
            self.assertIsNotNone(client.process.returncode)

    def test_live_worker_no_early_reveal(self):
        with EvaluatorClient() as client:
            self.opened(client)
            with self.assertRaises(ControlError):client.request('reveal')
            self.assertTrue(client.closed)

    def test_live_worker_no_caller_path_or_executable(self):
        with EvaluatorClient() as client:
            with self.assertRaises(ControlError):
                client.request('open',objective=self.objective.to_json(),freeze=self.freeze,candidate_credits=1,executor='arbitrary.py')

    def test_live_worker_bad_freeze_rejected(self):
        with EvaluatorClient() as client:
            bad=dict(self.freeze,predecessor_state_hash='0'*64)
            with self.assertRaises(ControlError):client.request('open',objective=self.objective.to_json(),freeze=bad,candidate_credits=1)

    def test_timeout_kills_worker_without_success(self):
        with EvaluatorClient() as client:
            self.opened(client)
            with patch.object(client._responses,'get',side_effect=queue.Empty):
                with self.assertRaises(ControlError):client.request('seal',terminal_action=Action.EXTERNAL_STOP.value)
            self.assertTrue(client.closed)
            self.assertFalse(client.sealed)
            self.assertIsNotNone(client.process.returncode)

    def test_worker_death_fails_closed(self):
        with EvaluatorClient() as client:
            self.opened(client)
            client.process.kill();client.process.wait(timeout=10)
            with self.assertRaises(ControlError):client.request('seal',terminal_action=Action.EXTERNAL_STOP.value)
            self.assertFalse(client.sealed)

    def test_fresh_worker_commitments_differ(self):
        commitments=[]
        for _ in range(2):
            with EvaluatorClient() as client:
                commitments.append(self.opened(client,0)['public_challenge']['challenge_commitment_hash'])
                client.request('seal',terminal_action=Action.RESOURCE_EXHAUSTED.value)
        self.assertNotEqual(*commitments)

    def test_seal_prevents_more_requests(self):
        with EvaluatorClient() as client:
            self.opened(client,0);client.request('seal',terminal_action=Action.RESOURCE_EXHAUSTED.value)
            with self.assertRaises(ControlError):self.opened(client)

    def test_environment_does_not_forward_credentials_or_pythonpath(self):
        with patch.dict(os.environ,{'PHASE17_PRIVATE_SEED':'no','GITHUB_TOKEN':'no','PYTHONPATH':'no'}):
            env=worker_environment()
            for key in ('PHASE17_PRIVATE_SEED','GITHUB_TOKEN','PYTHONPATH'):
                self.assertNotIn(key,env)

    def test_client_timeout_profile_validated(self):
        for value in (0,-1,True,float('nan'),float('inf'),121):
            with self.subTest(value=value),self.assertRaises(ControlError):EvaluatorClient(response_timeout=value)


if __name__=='__main__':unittest.main(verbosity=2)
