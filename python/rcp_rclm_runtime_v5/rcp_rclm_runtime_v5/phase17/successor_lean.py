"""Compile freshly measured finite successor facts; NEVER a complete root verdict.

The immutable Gate E root is imported, not rewritten. A conditional theorem
connects three finite frontier-inclusion facts to the root's actual fields. Its
kernel/mapping/operational premises are explicit and remain undischargeable by a
mere serialized success flag.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import tempfile

from rcp_rclm_runtime_v5.phase17.materialized import require, sha
from rcp_rclm_runtime_v5.phase17.successor_evidence import PreparedSuccessor, SCHEMA, FALSE_CLAIMS
from rcp_rclm_runtime_v5.phase17 import lean_frontier_gate as gate

BRIDGE_PATH = 'lean/phase17_bridge/SuccessorEvidence.lean'
BRIDGE_SHA256 = 'a947147a280df0de68186549752fb1d180d73a587d790eee364b347ce3fe44e7'
NAMES = ('Phase17Evidence.selected_facts', 'Phase17Evidence.protected_interpretation',
         'Phase17Evidence.root_recursive_frontier_fields', 'Phase17Evidence.selected_dsl_regression')
FAMILY_CODES = {'adapter_policy': 0, 'architecture_policy': 1, 'memory_policy': 2,
                'optimizer_policy': 3, 'planner_policy': 4, 'retrieval_policy': 5,
                'tool_policy': 6, 'verification_automation_policy': 7}


def string(value: str) -> str:
    require(type(value) is str and len(value) <= 512 and value.isascii() and
            all(32 <= ord(c) < 127 for c in value), 'nonliteral Lean string')
    return json.dumps(value, ensure_ascii=False)


def integer(value: int) -> str:
    require(type(value) is int and abs(value) < 2**63, 'bounded exact integer required')
    return '(' + str(value) + ')' if value < 0 else str(value)


def array(values, encode) -> str:
    require(type(values) is list and len(values) <= 256, 'finite literal list required')
    return '[' + ', '.join(encode(v) for v in values) + ']'


def program(p: dict) -> str:
    from rcp_rclm_runtime_v5.phase17.bootstrap import _validate_program
    _validate_program(p)
    return ('{ family := ' + str(FAMILY_CODES[p['family']]) + ', variant := ' + integer(p['variant']) +
            ', a := ' + integer(p['parameter_a']) + ', b := ' + integer(p['parameter_b']) + ' }')


def _file(row: dict) -> str:
    require(type(row) is dict and set(row) == {'path', 'sha256', 'size'}, 'file identity shape')
    require(re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None and type(row['size']) is int and row['size'] >= 0,
            'file identity values')
    return '(' + string(row['path']) + ', ' + string(row['sha256']) + ', ' + integer(row['size']) + ')'


def render(prepared: PreparedSuccessor, bridge_bytes: bytes, *, negative_control: bool = False) -> bytes:
    require(type(prepared) is PreparedSuccessor and type(bridge_bytes) is bytes, 'immutable prepared inputs required')
    normalized = bridge_bytes.replace(b'\r\n', b'\n')
    require(sha(normalized) == BRIDGE_SHA256, 'transition bridge template changed')
    packet = prepared.packet
    require(packet.get('schema_id') == SCHEMA and packet['claims'] == {k: False for k in FALSE_CLAIMS}
            and all(packet['claims'][k] is False for k in FALSE_CLAIMS), 'packet schema/claim escalation')
    checks = packet['candidate_evaluation']['probe_checks']
    vectors = [r['input'] for r in checks]
    targets = [list(r['expected']) for r in checks]
    require(len(vectors) == len(targets) == 8 and all(len(x) == 4 for x in vectors + targets), 'fixed probe shape')
    if negative_control:
        targets[0][0] += 1  # Deliberately false *certificate*, not a changed accepted task.
    vec = lambda x: array(x, integer)
    fields = [
        ('protectedBefore', array(packet['projection']['protected_before'], _file)),
        ('protectedAfter', array(packet['projection']['protected_after'], _file)),
        ('programsBefore', array(packet['programs_before'], string)),
        ('programsAfter', array(packet['programs_after'], string)),
        ('newProgram', string(packet['bindings']['program_hash'])),
        ('capabilitiesBefore', array(packet['capabilities_before'], string)),
        ('capabilitiesAfter', array(packet['capabilities_after'], string)),
        ('newCapability', string(packet['new_capability'])),
        ('recursiveBefore', array(packet['recursive_before'], string)),
        ('recursiveAfter', array(packet['recursive_after'], string)),
        ('searchUsed', integer(packet['search_used'])), ('searchBudget', integer(packet['search_budget'])),
        ('program', program(packet['candidate_program'])),
        ('inheritedFamilyPrograms', array(packet['inherited_family_programs'], program)),
        ('inputs', array(vectors, vec)), ('targets', array(targets, vec)),
    ]
    from rcp_rclm_runtime_v5.phase17.materialized import execute_matrix
    grammar = packet['current_grammar']
    require(len(grammar) == 32, 'full grammar differential surface required')
    probes = [[-3, 0, 5, 11], [0, 0, 0, 0], [-64, -1, 0, 64], [64, 63, -63, -64]]
    examples = [(p, x, execute_matrix(p, x)) for p in grammar for x in probes]
    differential = '[' + ',\n'.join('(' + program(p) + ', ' + vec(x) + ', ' + vec(y) + ')'
                                     for p, x, y in examples) + ']'
    tail = ('\nnamespace Phase17Evidence\nset_option maxRecDepth 16384\n'
            'set_option maxHeartbeats 4000000\n'
            '-- Input packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
            'def selectedPacket : Packet := {\n' + ''.join('  ' + k + ' := ' + v + '\n' for k, v in fields) + '}\n'
            'theorem selected_facts : FiniteFacts selectedPacket := by\n  constructor <;> decide\n'
            'def selectedCases : List (Program × List Int × List Int) := ' + differential + '\n'
            'theorem selected_dsl_regression : selectedCases.all (fun c => decide (execute c.1 c.2.1 = c.2.2)) = true := by decide\n'
            'end Phase17Evidence\n' + ''.join('#print axioms ' + n + '\n' for n in NAMES))
    source = normalized + tail.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', source),
            'forbidden generated source token')
    return source


def parse_audits(stdout: str) -> dict[str, list[str]]:
    require(type(stdout) is str, 'audit output must be text')
    # Accept whitespace wrapping inside a genuine axiom list, not extra messages.
    cursor = 0
    result = {}
    for name in NAMES:
        pattern = (r"'" + re.escape(name) +
                   r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*")
        match = re.compile(pattern, re.S).match(stdout, cursor)
        require(match is not None, 'exact named theorem audits required')
        result[name] = gate._axioms(match.group(0), name)
        cursor = match.end()
    require(cursor == len(stdout), 'unexpected additional audit output')
    return result


def _check_finite_successor(prepared: PreparedSuccessor, *, source_root: Path,
                           lean_workspace: Path, toolchain_root: Path | None = None) -> dict:
    """Real compiler path or explicit blocked/rejected result. No test success mode."""
    result = {'schema_id': 'runtime.v5.phase17.finite-successor-lean.v1', 'status': 'blocked',
              'packet_sha256': sha(prepared.packet_bytes), 'commands': [], 'theorem_axioms': {},
              'measurement_binding_is_callers_obligation': True, 'dsl_regression_cases': 128,
              'finite_successor_facts_verified': False, 'conditional_root_binding_checked': False,
              'negative_certificate_rejected': False,
              'claims': {k: False for k in FALSE_CLAIMS}}
    try:
        bridge = (source_root / BRIDGE_PATH).read_bytes()
        positive = render(prepared, bridge)
        negative = render(prepared, bridge, negative_control=True)
        before = gate.root_source_fingerprint(lean_workspace)
        dependencies = gate._dependency_state(lean_workspace)
        tool = gate.resolve_toolchain(toolchain_root)
        env, git = gate._lean_environment(tool)
        suffix = '.exe' if os.name == 'nt' else ''
        lean, lake = tool / 'bin' / ('lean' + suffix), tool / 'bin' / ('lake' + suffix)
        executables = {str(p): sha(gate._read_regular(p)) for p in (lean, lake, git)}
        version = gate._process([str(lean), '--version'], lean_workspace / gate.ROOT_PROJECT, env, timeout=30)
        result['commands'].append(version)
        require(version['returncode'] == 0 and not version['stderr'] and
                re.match(r'^Lean \(version 4\.31\.0(?:,|\))', version['stdout']), 'Lean version mismatch')
        result['status'] = 'rejected'
        with tempfile.TemporaryDirectory(prefix='r17f-') as temporary:
            directory = Path(temporary).resolve(strict=True)
            bad, good = directory / 'Negative.lean', directory / 'Certificate.lean'
            bad.write_bytes(negative); good.write_bytes(positive)
            argv = [str(lake), '--keep-toolchain', '--no-cache', 'env', str(lean)]
            rejected = gate._process([*argv, str(bad)], lean_workspace / gate.ROOT_PROJECT, env)
            result['commands'].append(rejected)
            diagnostic = rejected['stdout'] + rejected['stderr']
            require(rejected['returncode'] == 1 and 'error:' in diagnostic and
                    ('decide' in diagnostic or 'false' in diagnostic.lower()),
                    'compiler did not reject the deliberately false finite certificate')
            require(bad.read_bytes() == negative, 'negative control source changed')
            result['negative_certificate_rejected'] = True
            accepted = gate._process([*argv, str(good)], lean_workspace / gate.ROOT_PROJECT, env)
            result['commands'].append(accepted)
            require(accepted['returncode'] == 0 and not accepted['stderr'], 'finite certificate or root-binding lemma rejected')
            axioms = parse_audits(accepted['stdout'])
            require(good.read_bytes() == positive, 'positive source changed')
        require(gate.root_source_fingerprint(lean_workspace) == before and
                gate._dependency_state(lean_workspace) == dependencies, 'pinned environment changed')
        require({str(p): sha(gate._read_regular(p)) for p in (lean, lake, git)} == executables,
                'verification executable changed')
        require((source_root / BRIDGE_PATH).read_bytes() == bridge, 'bridge source changed')
        result.update(status='passed', finite_successor_facts_verified=True,
                      conditional_root_binding_checked=True, theorem_axioms=axioms,
                      positive_source_sha256=sha(positive), negative_source_sha256=sha(negative),
                      executable_sha256=executables, trusted_import_cache_assumption=True)
    except (ValueError, OSError, __import__('subprocess').SubprocessError) as exc:
        result['failure'] = {'type': type(exc).__name__, 'reason': str(exc)}
    return result
