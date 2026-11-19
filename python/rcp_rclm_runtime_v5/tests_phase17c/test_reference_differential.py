"""Differential checks against the unmodified Phase 16 implementation."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import unittest

from rcp_rclm_runtime_v4.phase16.grammar import legal_mutation_programs, execute_program
from rcp_rclm_runtime_v4.phase16.records import MutationProgram
from rcp_rclm_runtime_v5.phase17.challenge_protocol import reference_grammar, execute_reference, verify_transcript
from rcp_rclm_runtime_v5.phase17.challenge_transaction import run_bounded_transaction
from test_process_boundary import historical_parent


class ReferenceDifferentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.parent=historical_parent()

    def test_exact_grammar_for_eight_current_nonces(self):
        for turn in (0,1,3,7):
            for digit in ('3','a'):
                actual=legal_mutation_programs(self.parent.phase16_state(),promotion_index=turn,public_nonce_hash=digit*64)
                self.assertEqual(tuple(p.to_json() for p in actual),reference_grammar(self.parent.state,turn,digit*64))

    def test_reference_matches_actual_executor_all_families_and_variants(self):
        programs=legal_mutation_programs(self.parent.phase16_state(),promotion_index=0,public_nonce_hash='6'*64)
        vectors=([0,0,0,0],[1,2,3,4],[-32,32,-1,0],[5,-7,8,-11])
        for program in programs:
            for vector in vectors:
                with self.subTest(family=program.family,variant=program.variant,vector=vector):
                    self.assertEqual(execute_reference(program.to_json(),vector),execute_program(program,{'input_vector':vector})['output_vector'])

    def test_reference_matches_installed_predecessor_programs(self):
        for raw in self.parent.accepted_programs:
            obj=json.loads(raw);args={k:v for k,v in obj.items() if k!='schema_id'};program=MutationProgram(**args)
            self.assertEqual(execute_reference(obj,[-13,17,-19,23]),execute_program(program,{'input_vector':[-13,17,-19,23]})['output_vector'])

    def test_zero_credit_controller_service_transaction(self):
        records=run_bounded_transaction(self.parent,candidate_credits=0,public_nonce_hash='1'*64)
        result=json.loads(records['transaction.json']);self.assertEqual(result['terminal_action'],'resource_exhausted')
        self.assertTrue(result['separate_process']);self.assertFalse(result['claims']['promotion_authorized'])

    def test_partial_controller_service_transaction(self):
        records=run_bounded_transaction(self.parent,candidate_credits=2,public_nonce_hash='2'*64)
        result=json.loads(records['transaction.json'])
        self.assertIn(result['terminal_action'],('resource_exhausted','await_root_verification'))
        self.assertGreaterEqual(result['candidate_evaluations'],1)
        self.assertLessEqual(result['candidate_evaluations'],2)

    def test_complete_controller_service_transaction(self):
        records=run_bounded_transaction(self.parent,candidate_credits=32,public_nonce_hash='3'*64)
        result=json.loads(records['transaction.json'])
        self.assertIn(result['terminal_action'],('search_exhausted','await_root_verification'))
        replay=verify_transcript(self.parent,records['sealed_transcript.json'],
                                expected_transcript_hash=result['transcript_sha256'])
        self.assertEqual(replay.candidate_evaluations,result['candidate_evaluations'])
        if result['terminal_action']=='search_exhausted':
            self.assertEqual(result['candidate_evaluations'],32);self.assertIn('bounded_exhaustion.json',records)
        self.assertFalse(result['claims']['phase17_exit_closed'])


if __name__=='__main__':unittest.main(verbosity=2)
