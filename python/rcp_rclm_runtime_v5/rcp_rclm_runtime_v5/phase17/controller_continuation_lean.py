"""Deterministic AC proof sources and exact named-audit/negative expectations."""
from __future__ import annotations

import json
from pathlib import Path
import re

from .controller_continuation import PreparedContinuation, require, sha, PROVENANCE, PROVENANCE_SHA

BRIDGE = 'lean/phase17_bridge/ControllerContinuation.lean'
MODULES = ('ProposalProvenance', 'ControllerContinuation')
GENERIC_NAMES = tuple('Phase17Controller.' + name for name in (
    'choose_fresh', 'choose_in_range', 'choose_available', 'fallback_complete', 'fallback_nodup',
    'advance_invariant', 'replay_invariant', 'replay_no_repeat', 'replay_result',
    'replay_append', 'deterministic_prefix_splice', 'pass_priority', 'exhaustion_priority',
    'resource_exhaustion', 'terminal_cannot_advance', 'terminal_cannot_halt',
    'halt_preserves_history', 'halted_decision', 'exhaustion_covers_grammar',
    'present_input_invariance', 'choose_context_credits_irrelevant',
    'decision_context_credits_irrelevant', 'credits_above_grammar_allowed',
    'rejection_run_progress', 'all_rejections_exhaust', 'partial_rejections_resource_exhaust',
    'rejection_run_replays', 'replay_follows', 'choose_selection_inputs', 'decision_selection_inputs',
    'decision_progress', 'decision_credit_headroom', 'decision_total', 'replay_decision_total',
))
NAMES = GENERIC_NAMES + ('Phase17ControllerExamples.selected_protocol_cases',)
NEGATIVES = ('RepeatedChoice', 'IncompleteExhaustion', 'WrongPassPriority',
             'WrongExhaustionPriority', 'ContinueAfterPass', 'RewriteTerminalCause',
             'WrongPrefixSplice', 'WrongExternalStop', 'WrongSafetyStop')
POSITIVE = 'ControllerExamples'
LABELS = (POSITIVE, *NEGATIVES)
ALLOWED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}


def _nat(value):
    require(type(value) is int and value >= 0, 'natural literal required')
    return str(value)


def _int(value):
    require(type(value) is int, 'integer literal required')
    return str(value) if value >= 0 else '(' + str(value) + ')'


def _string(value):
    require(type(value) is str and re.fullmatch('[a-zA-Z0-9_.:-]*', value), 'bounded ASCII literal required')
    return json.dumps(value)


def _observations(values):
    return '[' + ', '.join('{ index := ' + _nat(o['index']) + ', passed := ' +
                          str(o['passed']).lower() + ' }' for o in values) + ']'


def _prefix(case, *, stopped=True):
    p = case['prefix']
    stop = 'none' if not stopped or p['stop'] is None else 'some .' + p['stop']
    return '{ initialCredits := ' + _nat(p['initial_credits']) + ', observations := ' + \
           _observations(p['observations']) + ', stop := ' + stop + ' }'


def _action(case):
    names = {'await_root_verification': 'awaitRoot', 'search_exhausted': 'searchExhausted',
             'resource_exhausted': 'resourceExhausted', 'external_stop_valid_prefix': 'externalStop',
             'fail_closed_safety_halt': 'safetyHalt'}
    return '.evaluate ' + _nat(case['candidate_index']) if case['action'] == 'evaluate' else '.' + names[case['action']]


def _context(context, number):
    rows = ['{ key := ' + _string(row['key']) + ', family := ' + _nat(row['family']) +
            ', baseScore := ' + _int(row['base_score']) + ', ties := [' +
            ', '.join(_nat(i) for i in row['ties']) + '] }' for row in context['rows']]
    return ('def ctx' + str(number) + ' : Phase17Provenance.Context := { generator := "controlled-AC", '
            'parentPackage := ' + _string(context['frozen_search']['view']['active_package_hash']) +
            ', contextHash := ' + _string(context['freeze_hash']) + ', transcriptHash := "synthetic", '
            'credits := 0, offset := ' + _nat(context['offset']) + ', rows := [' + ', '.join(rows) + '] }\n')


def _preamble():
    return ('import ControllerContinuation\nnamespace Phase17ControllerExamples\n'
            'open Phase17Controller\nset_option maxRecDepth 32768\n'
            'set_option maxHeartbeats 8000000\n')


def render_positive(prepared: PreparedContinuation) -> bytes:
    packet = prepared.packet
    text = _preamble()
    for number, context in enumerate(packet['contexts']):
        text += _context(context, number)
    proofs = []
    checks = []
    for i, case in enumerate(packet['cases']):
        p = case['prefix']; c = 'ctx' + str(case['context'])
        text += 'def obs' + str(i) + ' : List Observation := ' + _observations(p['observations']) + '\n'
        text += 'def end' + str(i) + ' : Prefix := ' + _prefix(case) + '\n'
        term = ('replay ' + c + ' (initial ' + _nat(p['initial_credits']) + ') obs' + str(i))
        if p['stop'] is not None:
            term = '(' + term + ').bind (fun p => Phase17Controller.halt ' + c + ' p .' + p['stop'] + ')'
        name = 'caseCheck' + str(i)
        text += 'def ' + name + ' : Bool := decide (' + term + ' = some end' + str(i) + \
                ' ∧ decision ' + c + ' end' + str(i) + ' = some (' + _action(case) + '))\n'
        proof = 'caseProof' + str(i)
        text += 'theorem ' + proof + ' : ' + name + ' = true := by decide +kernel\n'
        proofs.append(proof); checks.append(name)
    text += 'def selectedChecks : List Bool := [' + ', '.join(checks) + ']\n'
    text += 'theorem selected_protocol_cases : selectedChecks.all id = true := by\n'
    text += '  simp only [selectedChecks, List.all_cons, List.all_nil, id_eq, ' + ', '.join(proofs) + ']\n'
    text += '  decide\nend Phase17ControllerExamples\n'
    text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    return text.encode()


def render_negative(prepared: PreparedContinuation, label: str) -> bytes:
    require(label in NEGATIVES, 'unknown controller negative')
    packet = prepared.packet
    cases = {case['name']: case for case in packet['cases']}
    chosen = {
        'RepeatedChoice': cases['pass_last_credit_01'],
        'IncompleteExhaustion': cases['credit_boundary_31'],
        'WrongPassPriority': cases['pass_last_credit_01'],
        'WrongExhaustionPriority': cases['credit_boundary_32'],
        'ContinueAfterPass': cases['pass_last_credit_01'],
        'RewriteTerminalCause': cases['pass_last_credit_01'],
        'WrongPrefixSplice': cases['pass_last_credit_04'],
        'WrongExternalStop': cases['external_at_4'],
        'WrongSafetyStop': cases['safety_at_4'],
    }[label]
    c = chosen['context']; text = _preamble() + _context(packet['contexts'][c], c)
    text += 'def endPrefix : Prefix := ' + _prefix(chosen) + '\n'
    ctx = 'ctx' + str(c)
    first = chosen['prefix']['observations'][0]['index'] if chosen['prefix']['observations'] else 0
    if label == 'RepeatedChoice':
        obs = [{'index': first, 'passed': False}, {'index': first, 'passed': False}]
        assertion = '(replay ' + ctx + ' (initial 40) ' + _observations(obs) + ').isSome'
    elif label == 'IncompleteExhaustion':
        assertion = 'decide (decision ' + ctx + ' endPrefix = some .searchExhausted)'
    elif label == 'WrongPassPriority':
        assertion = 'decide (decision ' + ctx + ' endPrefix = some .resourceExhausted)'
    elif label == 'WrongExhaustionPriority':
        assertion = 'decide (decision ' + ctx + ' endPrefix = some .resourceExhausted)'
    elif label == 'ContinueAfterPass':
        assertion = '(advance ' + ctx + ' endPrefix { index := 0, passed := false }).isSome'
    elif label == 'RewriteTerminalCause':
        assertion = '(Phase17Controller.halt ' + ctx + ' endPrefix .external).isSome'
    elif label == 'WrongPrefixSplice':
        obs = list(reversed(chosen['prefix']['observations']))
        assertion = '(replay ' + ctx + ' (initial 4) ' + _observations(obs) + ').isSome'
    elif label == 'WrongExternalStop':
        assertion = 'decide (decision ' + ctx + ' endPrefix = some .safetyHalt)'
    else:
        assertion = 'decide (decision ' + ctx + ' endPrefix = some .externalStop)'
    text += 'def wrongClaim : Bool := ' + assertion + '\n'
    # The first fact must compile; only the deliberately impossible final claim
    # is an acceptable rejection location. Import failures cannot satisfy this.
    text += 'theorem actual_rejection : wrongClaim = false := by decide +kernel\n'
    text += 'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
    text += 'end Phase17ControllerExamples\n'
    return text.encode()


def sources(prepared: PreparedContinuation, root: Path) -> dict[str, bytes]:
    provenance = (root / PROVENANCE).read_bytes().replace(b'\r\n', b'\n')
    require(sha(provenance) == PROVENANCE_SHA, 'original provenance source changed')
    bridge = (root / BRIDGE).read_bytes().replace(b'\r\n', b'\n')
    result = {MODULES[0]: provenance, MODULES[1]: bridge, POSITIVE: render_positive(prepared)}
    result.update({label: render_negative(prepared, label) for label in NEGATIVES})
    for label, raw in result.items():
        require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', raw),
                'forbidden proof source token: ' + label)
    return result


def parse_audits(stdout: str) -> dict:
    cursor = 0; audits = {}
    for name in NAMES:
        pattern = re.compile("'" + re.escape(name) +
            r"' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*", re.S)
        match = pattern.match(stdout, cursor)
        require(match is not None, 'missing or reordered controller theorem audit: ' + name)
        axioms = [] if match[1] is None else [x.strip() for x in match[1].split(',') if x.strip()]
        require(len(set(axioms)) == len(axioms) and set(axioms) <= ALLOWED_AXIOMS, 'unapproved controller axiom')
        audits[name] = axioms; cursor = match.end()
    require(cursor == len(stdout), 'unexpected controller audit output')
    return audits


def negative_location(raw: bytes) -> tuple[int, int]:
    lines = raw.decode().splitlines()
    require(lines.count('example : wrongClaim = true := by') == 1, 'negative assertion identity')
    index = lines.index('example : wrongClaim = true := by')
    require(lines[index + 1:index + 3] ==
            ['  simp only [actual_rejection, Bool.false_eq_true]', '  decide'],
            'negative assertion tactic identity')
    return index + 3, 2


def validate_negative(label: str, raw: bytes, stdout: str, stderr: str, returncode: int) -> None:
    require(label in NEGATIVES and type(returncode) is int and returncode == 1 and not stderr,
            'negative control did not return its intended compiler rejection')
    line, col = negative_location(raw)
    expected = re.compile(r'(?:[^\r\n]*[/\\])?' + re.escape(label) + r'\.lean:' + str(line) + ':' + str(col) +
                          r': error: Tactic `decide` proved that the proposition\s+False\s+is false\s*')
    require(expected.fullmatch(stdout) is not None, 'negative diagnostic is not the exact intended False assertion')
