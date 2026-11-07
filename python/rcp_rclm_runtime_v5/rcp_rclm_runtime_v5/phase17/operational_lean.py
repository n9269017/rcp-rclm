"""Real pinned semantics checks for model-decoded plans over the selected domain.

These prove the generated plans' arithmetic meaning, not the correctness of the
Python neural decoder, filesystem parser, all recursive tasks, or root transition.
The production runner independently regenerates the witness packet first.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
import subprocess
import tempfile
from . import lean_frontier_gate as gate
from .materialized import require, sha
from .operational_witnesses import (CASES, INTEGER_X, SCHEMA, CONTRACT_BYTES, CONTRACT_SHA256,
    PreparedOperational, expected_tokens, parse_plan, PLAN_CONTRACT, TOOL_CONTRACT)
from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical
from .successor_evidence import FALSE_CLAIMS

NAMES = tuple('Phase17PlannerProfiles.case_' + str(i).zfill(3) for i in range(len(CASES)))


def checked_cases(prepared: PreparedOperational) -> list[dict]:
    require(type(prepared) is PreparedOperational, 'exact operational witness type required')
    p = prepared.packet
    require(p['schema_id'] == SCHEMA and p['contract_sha256'] == CONTRACT_SHA256 and
            canonical(p['contract']) == CONTRACT_BYTES, 'operational contract substituted')
    allowed_claims = set(FALSE_CLAIMS) | {'full_learned_semantic_refinement', 'full_transformer_inference', 'training_performed'}
    require(set(p['claims']) == allowed_claims and all(v is False for v in p['claims'].values()),
            'unsupported authorization claim')
    require(p['predecessor'] == p['candidate'], 'retention mismatch')
    cases = p['candidate']['cases']
    require(len(cases) == len(CASES) == 172, 'complete contract case coverage required')
    for i, (row, (domain, a, b)) in enumerate(zip(cases, CASES, strict=True)):
        require(all(type(row[k]) is int for k in ('index', 'a', 'b', 'decoded_a', 'decoded_b')),
                'integer witness literals required')
        require((row['index'], row['domain'], row['a'], row['b']) == (i, domain, a, b), 'case order or task changed')
        require(type(row['tokens']) is list and all(type(t) is int for t in row['tokens']), 'token integer shape')
        require(tuple(row['tokens']) == expected_tokens(domain, a, b), 'decoded plan not expected task')
        require(parse_plan(domain, tuple(row['tokens'])) == (row['decoded_a'], row['decoded_b']), 'decoded literals changed')
        outputs = row['tool_outputs']
        require(type(outputs) is list and all(type(n) is int for n in outputs), 'integer tool outputs required')
        require(outputs == ([a*x+b for x in INTEGER_X] if domain == 'integer_program' else []), 'tool outputs differ')
    return cases


def render_operational(prepared: PreparedOperational, *, negative: bool = False) -> bytes:
    require(type(negative) is bool, 'boolean negative-control selector required')
    cases = checked_cases(prepared)
    lines = ['import Mathlib', '', 'namespace Phase17PlannerProfiles',
             '-- Packet SHA256: ' + sha(prepared.packet_bytes),
             '-- Contract SHA256: ' + CONTRACT_SHA256,
             '-- PUBLIC exhaustive recertification; no hidden-task or improvement claim.',
             'set_option maxRecDepth 8192', 'set_option maxHeartbeats 1000000', '']
    for i, row in enumerate(cases):
        da, db, a, b = (row[k] for k in ('decoded_a', 'decoded_b', 'a', 'b'))
        short = NAMES[i].split('.')[-1]
        if row['domain'] == 'integer_program':
            # Defining expression is from parsed MODEL TOKENS. RHS is the fixed
            # contract's task oracle. The negative control changes only RHS #0.
            ref_a = a + (1 if negative and i == 0 else 0)
            lines += [f'def plan_{i:03d} (x : Int) : Int := ({da}) * x + ({db})',
                      f'theorem {short} (x : Int) : plan_{i:03d} x = ({ref_a}) * x + ({b}) := by',
                      '  rfl', '']
        else:
            lines += [f'theorem {short} (x : Nat) : x + {a} < x + {b} := by',
                      f'  have decodedBound : {da} < {db} := by decide',
                      '  exact Nat.add_lt_add_left decodedBound x', '']
    lines += ['end Phase17PlannerProfiles', *('#print axioms '+n for n in NAMES), '']
    source = '\n'.join(lines).encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', source),
            'forbidden source token')
    return source


def parse_audits(stdout: str) -> dict:
    results, cursor = {}, 0
    for name in NAMES:
        match = re.compile(r"'"+re.escape(name)+r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*", re.S).match(stdout, cursor)
        require(match is not None, 'exact operational theorem audit sequence required')
        results[name] = gate._axioms(match[0], name)
        cursor = match.end()
    require(cursor == len(stdout), 'extra proof/audit output')
    return results


def check_operational(prepared: PreparedOperational, *, source_root: Path, lean_workspace: Path,
                      toolchain_root: Path | None = None) -> dict:
    result = {'schema_id': 'runtime.v5.phase17.operational-plan-lean.v1', 'status': 'blocked',
              'packet_sha256': sha(prepared.packet_bytes), 'contract_sha256': CONTRACT_SHA256,
              'commands': [], 'theorem_axioms': {}, 'task_semantics_checked': False,
              'negative_oracle_substitution_rejected': False, 'proof_count': 0,
              'bounded_contracts_certified': [], 'claims': {k: False for k in FALSE_CLAIMS}}
    try:
        positive, negative = render_operational(prepared), render_operational(prepared, negative=True)
        root_before = gate.root_source_fingerprint(lean_workspace)
        require({k:v['canonical_sha256'] for k,v in root_before.items()} ==
                {k:v['canonical_sha256'] for k,v in gate.root_source_fingerprint(source_root).items()}, 'root mismatch')
        deps = gate._dependency_state(lean_workspace)
        tool = gate.resolve_toolchain(toolchain_root)
        env, git = gate._lean_environment(tool)
        suffix = '.exe' if os.name == 'nt' else ''
        lean, lake = tool/'bin'/('lean'+suffix), tool/'bin'/('lake'+suffix)
        tools = {str(p): sha(gate._read_regular(p)) for p in (lean, lake, git)}
        version = gate._process([str(lean), '--version'], lean_workspace/gate.ROOT_PROJECT, env, timeout=30)
        result['commands'].append(version)
        require(version['returncode'] == 0 and not version['stderr'] and
                re.match(r'^Lean \(version 4\.31\.0(?:,|\))', version['stdout']), 'pinned Lean version mismatch')
        result['status'] = 'rejected'
        with tempfile.TemporaryDirectory(prefix='r17h-') as temp:
            directory = Path(temp).resolve(strict=True)
            good, bad = directory/'Plans.lean', directory/'WrongOracle.lean'
            good.write_bytes(positive); bad.write_bytes(negative)
            argv = [str(lake), '--keep-toolchain', '--no-cache', 'env', str(lean)]
            accepted = gate._process([*argv, str(good)], lean_workspace/gate.ROOT_PROJECT, env, timeout=900)
            result['commands'].append(accepted)
            require(accepted['returncode'] == 0 and not accepted['stderr'], 'plan semantics certificate rejected')
            audits = parse_audits(accepted['stdout'])
            rejected = gate._process([*argv, str(bad)], lean_workspace/gate.ROOT_PROJECT, env, timeout=900)
            result['commands'].append(rejected)
            diagnostic = rejected['stdout'] + rejected['stderr']
            require(rejected['returncode'] == 1 and 'error:' in diagnostic and 'rfl' in diagnostic,
                    'wrong affine oracle not rejected by compiler')
            require(good.read_bytes() == positive and bad.read_bytes() == negative, 'proof source changed')
        require(root_before == gate.root_source_fingerprint(lean_workspace) and deps == gate._dependency_state(lean_workspace),
                'root/dependency changed')
        require(tools == {str(p): sha(gate._read_regular(p)) for p in (lean, lake, git)}, 'tool changed')
        result.update(status='passed', theorem_axioms=audits, task_semantics_checked=True,
                      proof_count=172, negative_oracle_substitution_rejected=True,
                      bounded_contracts_certified=[PLAN_CONTRACT, TOOL_CONTRACT],
                      executable_sha256=tools, positive_source_sha256=sha(positive), negative_source_sha256=sha(negative),
                      physical_byte_and_token_binding_remains_trusted=True, neural_decoder_formally_verified=False,
                      trusted_import_cache_assumption=True)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        result['failure'] = {'type': type(exc).__name__, 'reason': str(exc)}
    return result
