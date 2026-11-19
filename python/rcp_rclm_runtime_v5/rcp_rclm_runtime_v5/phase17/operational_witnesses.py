"""Phase17H: bounded, package-bound operational witnesses, not phase acceptance.

The two v1 contracts extend the old selected probes to the complete *declared*
Phase15 plan domain (136 affine + 36 natural-inequality pairs). They do not
silently assign complete semantics to the nineteen historical recursive labels.
No candidate report, answer store, training process, or external executable is an
acceptance input. Public exhaustive recertification is NOT hidden-task evaluation.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import struct
from typing import Mapping

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from rcp_rclm_runtime_v4.phase15.decoder import decode_plan
from .bootstrap import HistoricalPredecessor, WEIGHTS_SHA256
from .materialized import PackageReceipt, require, sha, snapshot, verify_package
from .successor_evidence import FALSE_CLAIMS, prepare_successor

SCHEMA = 'runtime.v5.phase17.operational-planner-witnesses.v1'
PLAN_CONTRACT = 'phase17.recursive.multi-token-plan.exhaustive-v1'
TOOL_CONTRACT = 'phase17.recursive.affine-tool.exhaustive-v1'
WEIGHTS = 'base/model/phase15_planner/weights.i16le.bin'
PLANNER = 'base/model/phase15_planner/manifest.json'
TOOL_POLICY = 'base/policies/tool_policy.json'
VOCABULARY = 'base/model/phase15_planner/vocabulary.json'
INTEGER_X = tuple(range(-16, 17))
CASES = tuple(('integer_program', a, b) for a in range(-4, 5) if a != 0 for b in range(-8, 9)) + tuple(
    ('lean_multistep', a, b) for a in range(8) for b in range(a + 1, 9))
CONTRACT = {
    'schema_id': 'runtime.v5.phase17.operational-contract.v1',
    'plan_contract': PLAN_CONTRACT, 'tool_contract': TOOL_CONTRACT,
    'case_order': [list(c) for c in CASES], 'affine_inputs': list(INTEGER_X),
    'token_layout': {'BOS': 0, 'EOS': 1, 'LEAN_BEGIN': 2, 'LEAN_HAVE': 3,
                     'LEAN_OMEGA': 4, 'LEAN_EXACT': 5, 'PROGRAM_BEGIN': 6,
                     'PROGRAM_MUL': 7, 'PROGRAM_ADD': 8, 'PROGRAM_RETURN': 9,
                     'INT_NEG8_through_INT_8': list(range(12, 29))},
    'execution': 'existing phase15 decode_plan + independent sparse score interpreter',
    'coverage': 'public complete selected finite parameter domain; not held-out or EGC',
    'legacy_frontier_redefinition_authorized': False,
}
CONTRACT_BYTES = canonical(CONTRACT)
CONTRACT_SHA256 = sha(CONTRACT_BYTES)


def check_case(domain: str, a: int, b: int) -> None:
    require(type(domain) is str and type(a) is int and type(b) is int, 'typed plan query required')
    require((domain == 'integer_program' and 0 < abs(a) <= 4 and -8 <= b <= 8) or
            (domain == 'lean_multistep' and 0 <= a < b <= 8), 'query outside declared contract')


def expected_tokens(domain: str, a: int, b: int) -> tuple[int, ...]:
    """Oracle from frozen grammar, not production curriculum.expected_plan."""
    check_case(domain, a, b)
    if domain == 'integer_program':
        return (6, a + 20, 7, b + 20, 8, 9, 1)
    return (2, a + 20, b + 20, 3, 4, 5, 1)


def parse_plan(domain: str, tokens: tuple[int, ...]) -> tuple[int, int]:
    require(type(tokens) is tuple and len(tokens) == 7 and
            all(type(t) is int and 0 <= t < 32 for t in tokens), 'seven integer tokens required')
    if domain == 'integer_program':
        require(tuple(tokens[i] for i in (0, 2, 4, 5, 6)) == (6, 7, 8, 9, 1), 'affine opcode sequence')
        a, b = tokens[1] - 20, tokens[3] - 20
    elif domain == 'lean_multistep':
        require(tuple(tokens[i] for i in (0, 3, 4, 5, 6)) == (2, 3, 4, 5, 1), 'Lean plan opcode sequence')
        a, b = tokens[1] - 20, tokens[2] - 20
    else:
        raise ValueError('unsupported plan domain')
    check_case(domain, a, b)
    return a, b


def reference_decode(payload: bytes, domain: str, a: int, b: int) -> tuple[tuple[int, ...], tuple[dict, ...]]:
    """Independent score accumulation over nonzero int16 entries.

    Does NOT call production feature selection, argmax, decode_plan, vocabulary,
    weights parser, or curriculum expected_plan. Lowest numeric token wins ties.
    """
    check_case(domain, a, b)
    require(type(payload) is bytes and len(payload) == 65536, '32768 int16 planner parameters required')
    nonzero = tuple((i // 1024, i % 1024, value[0])
                    for i, value in enumerate(struct.iter_unpack('<h', payload)) if value[0])
    previous, result, trace = 0, [], []
    for position in range(16):
        copy_b = 3 if domain == 'integer_program' else 2
        if position in (1, copy_b):
            features = (65 + (a if position == 1 else b) + 8,)
        else:
            features = (0, 1 + (0 if domain == 'integer_program' else 16) + position, 33 + previous)
        scores = [0] * 32
        for token, feature, weight in nonzero:
            if feature in features:
                scores[token] += weight
        chosen = max(range(32), key=lambda token: (scores[token], -token))
        trace.append({'position': position, 'previous': previous, 'features': list(features),
                      'scores': scores, 'chosen': chosen})
        result.append(chosen)
        previous = chosen
        if chosen == 1:
            break
    return tuple(result), tuple(trace)


def _read_verified(package: PackageReceipt, relative: str) -> bytes:
    record = load_json_strict(package.manifest_bytes)
    matches = [r for r in record['files'] if r['path'] == relative]
    require(len(matches) == 1, 'selected file not bound by package receipt')
    p = package.root / relative
    require(p.is_file() and not p.is_symlink(), 'regular selected file required')
    data = p.read_bytes()
    require(sha(data) == matches[0]['sha256'] and len(data) == matches[0]['size'], 'selected file modified')
    return data


def tool_binding(package: PackageReceipt) -> dict:
    """Check data-only allowlist and exact decoder bindings; never exec a path."""
    raw = _read_verified(package, TOOL_POLICY)
    p = load_json_strict(raw)
    manifest = load_json_strict(_read_verified(package, PLANNER))
    required = {'phase15_integer_program_exhaustive_verifier', 'phase15_lean_plan_interpreter',
                'phase15_quantized_plan_decoder'}
    require(type(p.get('allowed_tools')) is list and len(p['allowed_tools']) == 3 and
            set(p['allowed_tools']) == required, 'unexpected package tool allowlist')
    require(p.get('dynamic_code_loading') is False and p.get('candidate_self_report_authoritative') is False,
            'tool policy authority or executable loading changed')
    require(p.get('decoder_manifest_path') == 'model/phase15_planner/manifest.json' and
            p.get('decoder_weights_path') == 'model/phase15_planner/weights.i16le.bin' and
            p.get('decoder_weights_sha256') == manifest['weights_sha256'] == WEIGHTS_SHA256 and
            p.get('decoder_manifest_hash') == manifest['manifest_hash'], 'tool/decoder binding differs')
    vocabulary = load_json_strict(_read_verified(package, VOCABULARY))
    require(digest(vocabulary) == manifest['vocabulary_hash'], 'planner vocabulary binding differs')
    wanted = {0:'BOS',1:'EOS',2:'LEAN_BEGIN',3:'LEAN_HAVE',4:'LEAN_OMEGA',5:'LEAN_EXACT',
              6:'PROGRAM_BEGIN',7:'PROGRAM_MUL',8:'PROGRAM_ADD',9:'PROGRAM_RETURN'}
    wanted.update({n + 20: ('INT_NEG'+str(-n) if n < 0 else 'INT_'+str(n)) for n in range(-8, 9)})
    rows = vocabulary['tokens']
    require(len(rows) == 32 and [r['token_id'] for r in rows] == list(range(32)), 'vocabulary ordering')
    require(all(rows[k]['name'] == name for k, name in wanted.items()), 'vocabulary token semantics differ')
    return {'policy_sha256': sha(raw), 'planner_manifest_hash': manifest['manifest_hash'],
            'weights_sha256': manifest['weights_sha256'], 'tools': sorted(required)}


def invoke_affine(package: PackageReceipt, tokens: tuple[int, ...], x: int) -> int:
    """Fixed implementation of the declared data-only tool; never Python eval."""
    require(type(x) is int and -16 <= x <= 16, 'integer-tool input bound')
    tool_binding(package)
    a, b = parse_plan('integer_program', tokens)
    return _interpret_affine(tokens, a, b, x)


def _interpret_affine(tokens: tuple[int, ...], a: int, b: int, x: int) -> int:
    # A small instruction machine, not the reference oracle expression.
    accumulator = x
    for opcode, argument in ((tokens[2], a), (tokens[4], b), (tokens[5], None)):
        if opcode == 7:
            accumulator *= argument
        elif opcode == 8:
            accumulator += argument
        elif opcode == 9:
            return accumulator
    raise ValueError('missing RETURN')


_COMPONENT_PREFIXES = {
    'modelArchitecture': ('model/architecture.json',),
    'modelWeights': ('model/tensors/', 'model/adapters/'),
    'generator': ('policies/generator_policy.json',),
    'planner': ('policies/planner_policy.json', 'model/phase15_planner/'),
    'trainingPolicy': ('training/',), 'retrievalPolicy': ('retrieval/',),
    'memory': ('memory/',), 'tokenizer': ('model/tokenizer/',),
    'verificationPolicy': ('policies/verification_policy.json',),
    'resourcePolicy': ('policies/resource_policy.json',),
    'selfModel': ('self_model/',),
    'executionContext': ('runtime/', 'policies/tool_policy.json', 'package_manifest.json'),
}


def component_projection(before: Mapping[str, bytes], after: Mapping[str, bytes]) -> list[dict]:
    """Partition every inherited base file; no field is accepted by a claimed hash.

    executionContext includes package/tool/runtime metadata not separately named
    in Learned.PackageState. This is a measured mapping, not a Lean instantiation.
    """
    selected = {p for p in before if p.startswith('base/')}
    require(selected == {p for p in after if p.startswith('base/')} and len(selected) == 164,
            'base component coverage changed')
    groups = {key: [] for key in _COMPONENT_PREFIXES}
    for name in sorted(selected):
        choices = [key for key, prefixes in _COMPONENT_PREFIXES.items()
                   if any(name[5:].startswith(prefix) if prefix.endswith('/') else name[5:] == prefix for prefix in prefixes)]
        require(len(choices) == 1, 'unmapped or ambiguous inherited component')
        require(before[name] == after[name], 'learned component changed')
        groups[choices[0]].append({'path': name, 'size': len(before[name]), 'sha256': sha(before[name])})
    require(all(groups.values()), 'empty learned component binding')
    return [{'component': key, 'files': files, 'exact_bytes_preserved': True,
             'binding_sha256': sha(canonical(files)), 'full_root_premise_discharged': False}
            for key, files in groups.items()]


def evaluate_planner(package: PackageReceipt) -> dict:
    """Execute all 172 public queries, without reading training labels or answers."""
    bound = tool_binding(package)
    payload = _read_verified(package, WEIGHTS)
    require(sha(payload) == WEIGHTS_SHA256, 'inherited planner identity changed')
    cases, trace_table = [], {}
    for index, (domain, a, b) in enumerate(CASES):
        decoded = decode_plan(package.root / 'base', domain, a, b)
        reference, trace = reference_decode(payload, domain, a, b)
        actual = tuple(decoded.tokens)
        require(decoded.stopped_on_eos and actual == reference == expected_tokens(domain, a, b),
                'actual autoregressive decode or independent oracle disagrees')
        require(decoded.decoder_manifest_hash == bound['planner_manifest_hash'], 'decoder receipt identity')
        coefficients = parse_plan(domain, actual)
        trace_ids = []
        for row in trace:
            key = sha(canonical(row)); trace_table[key] = row; trace_ids.append(key)
        outputs = []
        if domain == 'integer_program':
            # One authenticated data-only tool session per plan, then all 33
            # inputs. Outer physical snapshots must remain identical.
            tool_binding(package)
            for x in INTEGER_X:
                output = _interpret_affine(actual, *coefficients, x)
                require(output == a*x+b, 'actual token-driven tool disagrees with task oracle')
                outputs.append(output)
        cases.append({'index': index, 'domain': domain, 'a': a, 'b': b, 'tokens': list(actual),
                      'decoded_a': coefficients[0], 'decoded_b': coefficients[1],
                      'trace_ids': trace_ids, 'tool_outputs': outputs,
                      'decode_report_hash': decoded.report_hash})
    zero = bytes(65536)
    control, _ = reference_decode(zero, 'integer_program', 1, 0)
    require(control != expected_tokens('integer_program', 1, 0), 'weight ablation unexpectedly solves plan')
    return {'tool_binding': bound, 'cases': cases, 'score_traces': trace_table,
            'queries': len(cases), 'decoded_tokens': sum(len(r['tokens']) for r in cases),
            'integer_tool_outputs': sum(len(r['tool_outputs']) for r in cases),
            'zero_weight_reference_negative_control': {'expected_failure': True, 'tokens': list(control)},
            'countercheck_scope': 'offline reference ablation only; live package was not modified'}


@dataclass(frozen=True)
class PreparedOperational:
    packet_bytes: bytes

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)


def prepare_operational(predecessor: PackageReceipt, candidate: PackageReceipt, parent: HistoricalPredecessor,
                        *, bundle: Path, capture: Path, transcript: bytes,
                        expected_transcript_hash: str) -> PreparedOperational:
    # Recompute the original selected successor facts; do not consume a pass report.
    inherited = prepare_successor(predecessor, candidate, parent, bundle=bundle, capture=capture,
                                  transcript=transcript, expected_transcript_hash=expected_transcript_hash)
    before, after = snapshot(predecessor.root), snapshot(candidate.root)
    components = component_projection(before, after)
    p, c = evaluate_planner(predecessor), evaluate_planner(candidate)
    require(p == c, 'learned operational witnesses regressed after extension')
    labels = parent.state['recursive_productivity_frontier']
    supported = {'recursive.generate_multi_token_plan': PLAN_CONTRACT,
                 'recursive.invoke_package_bound_tool': TOOL_CONTRACT}
    require(len(labels) == len(set(labels)) == 19 and set(supported) <= set(labels), 'recursive-label inventory')
    packet = {
        'schema_id': SCHEMA, 'contract_sha256': CONTRACT_SHA256,
        'contract': load_json_strict(CONTRACT_BYTES),
        'bindings': {**inherited.packet['bindings'], 'phase17f_packet_sha256': sha(inherited.packet_bytes)},
        'learned_component_projection': components,
        'predecessor': p, 'candidate': c, 'exact_operational_retention': True,
        'legacy_recursive_inventory': [
            {'task_id': label, 'contract_id': supported.get(label),
             'status': 'bounded_profile_executed_formal_semantics_pending' if label in supported else 'not_executed',
             'legacy_full_task_semantics_recertified': False} for label in labels],
        'new_contracts_python_passed': [PLAN_CONTRACT, TOOL_CONTRACT],
        'new_contracts_formally_certified': [],
        'public_recertification_not_hidden_evaluation': True,
        'claims': {**{key: False for key in FALSE_CLAIMS}, 'full_learned_semantic_refinement': False,
                   'full_transformer_inference': False, 'training_performed': False},
        'trusted_boundaries': ['Python physical measurement and byte-to-literal binding',
                              'fixed decoder/tool implementations; no hostile-code isolation claim',
                              'external transcript anchor; not event-time or entropy attestation'],
    }
    require(snapshot(predecessor.root) == before and snapshot(candidate.root) == after, 'package changed during witnesses')
    verify_package(predecessor.root, parent, bundle, expected_package_hash=predecessor.package_hash)
    verify_package(candidate.root, parent, bundle, expected_package_hash=candidate.package_hash,
                   transcript=transcript, expected_transcript_hash=expected_transcript_hash)
    return PreparedOperational(canonical(packet))


def verify_operational_packet(data: bytes, independently_prepared: PreparedOperational, *, expected_sha256: str) -> None:
    require(type(data) is bytes and len(data) <= 8 * 1024 * 1024, 'bounded immutable witness packet required')
    require(type(expected_sha256) is str and len(expected_sha256) == 64 and sha(data) == expected_sha256,
            'external witness anchor mismatch')
    require(data == independently_prepared.packet_bytes, 'witness differs from independent recomputation')
