"""One bounded turn: historical objective -> fresh challenge -> sealed evaluation.

No active-store writes, model-weight training, frontier certification, Lean,
promotion, or cross-turn continuation. Any candidate pass is only a handoff.
"""
from __future__ import annotations
from dataclasses import asdict
import hashlib
import os
import time

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime_v5.phase17.bootstrap import HistoricalPredecessor
from rcp_rclm_runtime_v5.phase17.challenge_client import EvaluatorClient
from rcp_rclm_runtime_v5.phase17.challenge_protocol import (
    CLAIMS, digest, realize_candidate, reference_grammar, verify_transcript, require,
)
from rcp_rclm_runtime_v5.phase17.controller import (
    Action, checkpoint, decide, record_evaluation, restore, exhaustion_record,
)
from rcp_rclm_runtime_v5.phase17.objectives import select_bootstrap_objective, freeze_bootstrap_objective
from rcp_rclm_runtime_v5.phase17.phase16_adapter import bind_phase16_search


def run_bounded_transaction(predecessor: HistoricalPredecessor, *, candidate_credits: int,
                            public_nonce_hash: str) -> dict[str, bytes]:
    """Return evidence only; no authoritative success or successor package."""
    started=time.monotonic_ns()
    decision=select_bootstrap_objective(predecessor,turn_index=0,public_nonce_hash=public_nonce_hash)
    freeze=freeze_bootstrap_objective(decision,predecessor,turn_index=0,public_nonce_hash=public_nonce_hash)
    with EvaluatorClient() as evaluator:
        public=evaluator.request('open',objective=decision.to_json(),freeze=freeze,
                                  candidate_credits=candidate_credits)['public_challenge']
        binding=bind_phase16_search(predecessor.phase16_state(),turn_index=0,
                    challenge_commitment_hash=public['challenge_commitment_hash'],
                    public_nonce_hash=public_nonce_hash,candidate_credits=candidate_credits)
        actual=[q.to_json() for q in sorted(binding.programs.values(),key=lambda q:q.program_hash)]
        expected=list(reference_grammar(predecessor.state,0,public_nonce_hash))
        require(actual==expected and digest(actual)==public['grammar_hash'],
                'Phase 16 and evaluator grammar disagree')
        prefix=binding.prefix
        while decide(prefix).action==Action.EVALUATE:
            step=decide(prefix)
            artifact=realize_candidate(binding.programs[step.candidate_hash].to_json(),freeze)
            candidate_freeze=evaluator.request('freeze_candidate',program_hash=artifact['program_hash'],
                                               artifact_hash=artifact['artifact_hash'])['receipt']
            report=evaluator.request('evaluate',artifact=artifact,
                        candidate_freeze_hash=candidate_freeze['candidate_freeze_hash'])
            require(report['event']=='candidate_evaluated' and
                    report['program_hash']==step.candidate_hash and
                    report['artifact_hash']==artifact['artifact_hash'] and
                    report['candidate_freeze_hash']==candidate_freeze['candidate_freeze_hash'] and
                    report['evaluation_index']==len(prefix.observations) and
                    report['evaluation_hash']==digest({k:v for k,v in report.items() if k!='evaluation_hash'}),
                    'candidate/evaluation binding mismatch')
            prefix=record_evaluation(prefix,step,verdict=report['verdict'],
                    evaluation_hash=report['evaluation_hash'],reason_codes=report['reason_codes'],
                    predecessor_state_hash=report['predecessor_state_hash'],
                    challenge_commitment_hash=report['challenge_commitment_hash'])
        terminal=decide(prefix).action.value
        sealed=evaluator.request('seal',terminal_action=terminal)
        transcript=evaluator.transcript()
        evaluator_pid=evaluator.process.pid
        worker_exited=evaluator.process.returncode==0
    transcript_hash=hashlib.sha256(transcript).hexdigest()
    replay=verify_transcript(predecessor,transcript,expected_transcript_hash=transcript_hash)
    require(replay.candidate_evaluations==len(prefix.observations) and replay.terminal_action==terminal and
            sealed['selected_candidate_hash']==replay.selected_candidate_hash,
            'controller/evaluator transcript disagreement')
    restored=restore(checkpoint(prefix),expected_prefix_hash=prefix.prefix_hash)
    require(restored==prefix,'controller checkpoint restoration mismatch')
    records={
        'objective.json':canonical_json_bytes(decision.to_json()),
        'objective_freeze.json':canonical_json_bytes(freeze),
        'public_challenge.json':canonical_json_bytes(public),
        'controller_checkpoint.json':checkpoint(prefix),
        'sealed_transcript.json':transcript,
        'transcript_verification.json':canonical_json_bytes({**asdict(replay),**CLAIMS}),
        'transaction.json':canonical_json_bytes({
            'schema_id':'runtime.v5.phase17.bounded_transaction.v1',
            'scope':'single_historical_predecessor_bounded_dsl_turn',
            'local_transaction_verified':True,'terminal_action':terminal,
            'candidate_evaluations':len(prefix.observations),'candidate_credits':candidate_credits,
            'prefix_hash':prefix.prefix_hash,'transcript_sha256':transcript_hash,
            'controller_pid':os.getpid(),'evaluator_pid':evaluator_pid,
            'separate_process':evaluator_pid!=os.getpid(),'worker_exited_cleanly':worker_exited,
            'elapsed_ns':time.monotonic_ns()-started,'complete_resource_accounting':False,
            'claims':dict(CLAIMS),
        }),
    }
    if terminal==Action.SEARCH_EXHAUSTED.value:
        records['bounded_exhaustion.json']=canonical_json_bytes(exhaustion_record(prefix))
    return records
