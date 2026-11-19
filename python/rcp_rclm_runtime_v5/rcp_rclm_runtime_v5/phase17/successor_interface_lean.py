"""Phase 17AG total finite successor interface and exact controlled examples.

The generic checker decides the original eight finite facts and semantic
absence. The complete fixed catalog turns its verdict into an exact guarded
acceptance statement inside the explicit source-admissibility domain. Offered
pool exhaustion is distinct from an inspection-budget stop and global search.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from . import second_step_lean as inherited
from .materialized import require, sha
from .successor_interface import PreparedSuccessorInterface, CASE_NAMES, case_requests
from .successor_lean import program, string

MODULES = (*inherited.MODULES, 'TruthfulSuccessorInterface')
POSITIVE = 'SuccessorInterfaceExamples'
NEGATIVES = ('FalseRootAcceptance', 'FalseParentAcceptance', 'FalseContextAcceptance',
             'FalseResourceAcceptance', 'FalseTypedAcceptance', 'FalseProtectedAcceptance',
             'FalseTaskNameAcceptance', 'AlreadySolvedAcceptance', 'FalseSuccessorAcceptance',
             'FalseSourceDomainAcceptance', 'EmptyPoolAcceptance', 'BudgetCalledExhaustion',
             'UncheckedSuffixCalledExhaustion', 'SkippedFirstPassingOffer')
LABELS = (POSITIVE, *NEGATIVES)
ALLOWED_AXIOMS = inherited.ALLOWED_AXIOMS
GENERIC_BODIES = inherited.GENERIC_BODIES
PINS = dict(inherited.PINS)
_read = inherited._read
_split_imports = inherited._split_imports
generic_finite_module = inherited.generic_finite_module
selected_finite_module = inherited.selected_finite_module
negative_location = inherited.negative_location

GENERIC_NAMES = tuple('Phase17TruthfulSuccessor.' + name for name in (
    'conditions_iff_facts', 'semantic_absence_iff', 'check_sound', 'check_iff_accepted',
    'refusal_iff', 'checked_semantic_gain', 'checked_protected_recovery', 'scan_spec',
    'scan_exhausted_iff', 'scan_budget_iff', 'scan_exists_iff', 'search_accepted_sound',
    'search_exhausted_iff', 'search_budget_iff', 'search_exists_iff', 'frontier_card_bound',
    'extended_catalog_bound', 'checked_strict_growth', 'checked_run_length_bound',
    'no_unbounded_checked_run', 'saturated_frontier_refused'))
SELECTED_NAMES = tuple('Phase17SuccessorInterface.' + name for name in (
    'fixed_catalog_unchanged', 'selected_check', 'selected_interface_accepted',
    'selected_semantic_gain', 'selected_exact_recovery', 'selected_source_capacity',
    'selected_successor_capacity', *('case_' + name for name in CASE_NAMES),
    'budget_can_hide_accepted', 'pool_exhaustion_is_local'))
NAMES = (*GENERIC_NAMES, *SELECTED_NAMES)


def _nat(value):
    require(type(value) is int and value >= 0, 'natural literal required')
    return str(value)


def _list(values, emit):
    require(type(values) is list, 'literal list required')
    return '[' + ', '.join(emit(value) for value in values) + ']'


def _canon(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'))


def _expected(result):
    codes = {'accepted': 0, 'exhausted': 1, 'budget_stop': 2}
    selected = 'none' if result['selected_index'] is None else '(some ' + _nat(result['selected_index']) + ')'
    return '(' + _nat(codes[result['status']]) + ', ' + selected + ', ' + _nat(result['examined']) + ')'


class _Literals:
    """Emit exact record differences from source-bound imported AF literals."""
    def __init__(self, selected):
        self.selected = selected
        self.lines = []
        self.states = {_canon(selected['source']): 'Phase17Finite.selectedAfter',
                       _canon(selected['offers'][0]['next']): 'observedAfter'}
        self.updates = {_canon(selected['offers'][0]['update']): 'secondUpdate'}
        self.evidence = {_canon(selected['offers'][0]['evidence']): 'secondEvidence'}
        self.offers = {_canon(selected['offers'][0]): 'selectedOffer'}

    def state(self, value):
        key = _canon(value)
        if key in self.states:
            return self.states[key]
        base = self.selected['source']
        # Choosing the nearer base changes only compact source spelling.
        other = self.selected['offers'][0]['next']
        if sum(value[k] != other[k] for k in value) <= sum(value[k] != base[k] for k in value):
            base, reference = other, 'observedAfter'
        else:
            reference = 'Phase17Finite.selectedAfter'
        name = 'stateLiteral' + str(len(self.states))
        changed = []
        for field in value:
            if value[field] == base[field] or field == 'program_keys':
                continue
            item = value[field]
            if field == 'frozen':
                term = _list(item, lambda rows: _list(rows, lambda row:
                    '⟨' + string(row['path']) + ', ' + _nat(row['size']) + ', ' + string(row['sha256']) + '⟩'))
            elif field == 'keys':
                term = _list(item, string)
            elif field == 'proofs':
                term = _list(item, lambda row: '(' + ', '.join(string(x) for x in row) + ')')
            elif field == 'programs':
                term = '[' + ', '.join('(' + string(k) + ', ' + program(p) + ')'
                    for k, p in zip(value['program_keys'], item, strict=True)) + ']'
            elif field in ('declared', 'named_frontier'):
                term = ('(' + _list(item, _nat if field == 'declared' else string) +
                    (' : List Nat)' if field == 'declared' else ' : List String)') + '.toFinset')
            elif field == 'semantic':
                vectors = lambda rows: _list(rows, lambda row: _list(row, _nat))
                term = ('{ rows := ' + vectors(item['mass_minus_one_dictionary']) + ', selectors := ' +
                    _list(item['row_selectors'], _nat) + ', goals := ' + vectors(item['goals']) + ' }')
            else:
                require(field in ('package_hash', 'root'), 'unsupported state field')
                term = string(item)
            target = {'named_frontier': 'namedFrontier', 'package_hash': 'packageHash'}.get(field, field)
            changed.append(target + ' := ' + term)
        if value['program_keys'] != base['program_keys'] and value['programs'] == base['programs']:
            changed.append('programs := [' + ', '.join('(' + string(k) + ', ' + program(p) + ')'
                for k, p in zip(value['program_keys'], value['programs'], strict=True)) + ']')
        self.lines.append('def ' + name + ' : State := { ' + reference + ' with ' + ', '.join(changed) + ' }\n')
        self.states[key] = name
        return name

    def update(self, value):
        key = _canon(value)
        if key in self.updates:
            return self.updates[key]
        names = {'task_name': 'taskName', 'parent_package': 'parentPackage',
                 'candidate_package': 'candidatePackage', 'context_hash': 'contextHash'}
        changed = []
        for field, item in value.items():
            if item == self.selected['offers'][0]['update'][field]:
                continue
            emit = program if field == 'program' else _nat if field == 'task' else inherited._kinds if field == 'charges' else string
            changed.append(names.get(field, field) + ' := ' + emit(item))
        name = 'updateLiteral' + str(len(self.updates))
        self.lines.append('def ' + name + ' : Phase17Finite.Update := { secondUpdate with ' + ', '.join(changed) + ' }\n')
        self.updates[key] = name
        return name

    def proof(self, value):
        key = _canon(value)
        if key in self.evidence:
            return self.evidence[key]
        names = {'parent_package': 'parentPackage', 'candidate_package': 'candidatePackage',
                 'context_hash': 'contextHash', 'transcript_hash': 'transcriptHash'}
        changed = []
        for field, item in value.items():
            if item == self.selected['offers'][0]['evidence'][field]:
                continue
            require(field != 'proposal', 'unimplemented controlled proposal difference')
            emit = inherited._kinds if field == 'charges' else string
            changed.append(names.get(field, field) + ' := ' + emit(item))
        name = 'evidenceLiteral' + str(len(self.evidence))
        self.lines.append('def ' + name + ' : Evidence := { secondEvidence with ' + ', '.join(changed) + ' }\n')
        self.evidence[key] = name
        return name

    def offer(self, value):
        key = _canon(value)
        if key in self.offers:
            return self.offers[key]
        update, after, proof = self.update(value['update']), self.state(value['next']), self.proof(value['evidence'])
        name = 'offerLiteral' + str(len(self.offers))
        self.lines.append('def ' + name + ' : Offer := ⟨' + update + ', ' + after + ', ' + proof + '⟩\n')
        self.offers[key] = name
        return name


def _rejection_proof(case, source, offer):
    expression = 'check fixed contexts charges ' + source + ' ' + offer
    text = 'theorem refused_' + case + ' : ' + expression + ' = false := by\n'
    text += '  apply Bool.eq_false_iff.mpr\n  intro passed\n'
    text += ('  have conditions := (conditions_iff_facts fixed contexts charges ' + source + ' ' + offer + ').mp\n'
             '    ((check_iff_conditions fixed contexts charges ' + source + ' ' + offer + ').mp passed)\n'
             '  have facts := conditions.1\n')
    if case == 'already_solved':
        text += ('  have available : (fixed.catalog ' + offer + '.update.task).check\n'
                 '      (Phase17Finite.taskObservation ' + source + ') = true := by decide +kernel\n'
                 '  rw [available] at conditions\n  exact Bool.noConfusion conditions.2\n')
    elif case in ('false_successor', 'source_inadmissible'):
        state = offer + '.next' if case == 'false_successor' else source
        facts = 'facts.afterAdmissible' if case == 'false_successor' else 'facts.beforeAdmissible'
        task = '40' if case == 'false_successor' else '0'
        text += ('  have frontierExact := ' + facts + '.2.2.2.2.2.2.2.1\n'
                 '  have declared : ' + task + ' ∈ ' + state + '.declared := by decide +kernel\n'
                 '  have member : ' + task + ' ∈ Phase17Finite.frontier\n'
                 '      (Phase17SuccessorContext.configurationAt fixed contexts charges ' + source + ') ' + state + ' :=\n'
                 '    frontierExact.symm ▸ declared\n'
                 '  have checked := (Finset.mem_filter.mp member).2\n'
                 '  have rejected : (fixed.catalog ' + task + ').check (Phase17Finite.taskObservation ' + state + ') = false := by decide +kernel\n'
                 '  change (fixed.catalog ' + task + ').check (Phase17Finite.taskObservation ' + state + ') = true at checked\n'
                 '  rw [rejected] at checked\n  cases checked\n')
    else:
        cfg = '(Phase17SuccessorContext.configurationAt fixed contexts charges ' + source + ')'
        atomic = {
            'refusal': (offer + '.evidence.root = fixed.root', 'facts.trusted.1'),
            'stale_parent': (offer + '.update.parentPackage = ' + source + '.packageHash', 'facts.updateValid.1'),
            'wrong_context': (offer + '.evidence.contextHash = ' + cfg + '.context.contextHash', 'facts.trusted.2.2.2.2.2.2.1'),
            'wrong_candidate': (offer + '.evidence.candidatePackage = ' + offer + '.next.packageHash', 'facts.trusted.2.2.2.2.2.1'),
            'omitted_charge': (offer + '.evidence.charges = ' + offer + '.update.charges', 'facts.resources.1'),
            'wrong_task_name': (offer + '.update.taskName = fixed.taskName ' + offer + '.update.task', 'facts.updateValid.2.2.2.2.2.2.1'),
            'wrong_program': (offer + '.next.programs = (Phase17Finite.apply ' + source + ' ' + offer + '.update).programs',
                              'congrArg Phase17Finite.State.programs facts.typed'),
            'changed_protected': (offer + '.next.semantic.goals = (Phase17Finite.apply ' + source + ' ' + offer + '.update).semantic.goals',
                                  'congrArg (fun s : State => s.semantic.goals) facts.typed'),
        }
        proposition, proof = atomic[case]
        text += '  have denied : ¬ (' + proposition + ') := by decide +kernel\n'
        text += '  exact denied (' + proof + ')\n'
    return text


def render_selected(prepared: PreparedSuccessorInterface, root: Path) -> bytes:
    require(type(prepared) is PreparedSuccessorInterface, 'exact prepared successor interface required')
    packet = prepared.packet
    requests = case_requests(prepared.second_step())
    require(tuple(requests) == CASE_NAMES and tuple(x['name'] for x in packet['cases']) == CASE_NAMES,
            'controlled interface inventory differs')
    selected = packet['selected_request']
    require(selected == requests['selected'], 'selected request changed')
    imports, generic = _split_imports(_read(root, 'TruthfulSuccessor'))
    text = 'import SelectedSecondStep\n' + '\n'.join(imports) + '\n' + generic
    text += '\nnamespace Phase17SuccessorInterface\n'
    text += 'open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3 Phase17TaskInterpretation Phase17SecondStep Phase17TruthfulSuccessor\n'
    text += 'set_option maxRecDepth 32768\nset_option maxHeartbeats 16000000\n'
    text += '-- Complete AG packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    text += 'def selectedOffer : Offer := ⟨secondUpdate, observedAfter, secondEvidence⟩\n'
    literals = _Literals(selected)
    case_terms = {}
    for name, request in requests.items():
        require(request['context'] == selected['context'] and request['expected_charges'] == selected['expected_charges'],
                'controlled context or charge provider differs')
        source = literals.state(request['source'])
        offers = [literals.offer(offer) for offer in request['offers']]
        case_terms[name] = (source, offers, request['inspection_budget'])
    text += ''.join(literals.lines)
    text += '''
theorem fixed_catalog_unchanged : CatalogComplete fixed ∧ CatalogBound fixed 282 ∧
    fixed.catalog = extendedCatalog Phase17TaskMeaning.catalog :=
  ⟨selected_catalog_complete, extended_catalog_bound Phase17Finite.selectedConfiguration, rfl⟩

theorem selected_check : check fixed contexts charges Phase17Finite.selectedAfter selectedOffer = true :=
  (check_iff_accepted fixed contexts charges selected_catalog_complete Phase17Finite.selectedAfter
    second_facts.beforeAdmissible selectedOffer).mpr second_accepted

theorem selected_interface_accepted :
    Accepted fixed contexts charges Phase17Finite.selectedAfter selectedOffer :=
  check_sound fixed contexts charges selected_catalog_complete _ _ selected_check

theorem selected_semantic_gain :
    ¬ (fixed.catalog selectedOffer.update.task).holds
      (Phase17Finite.taskObservation Phase17Finite.selectedAfter) ∧
    (fixed.catalog selectedOffer.update.task).holds (Phase17Finite.taskObservation selectedOffer.next) :=
  checked_semantic_gain fixed contexts charges selected_catalog_complete _ _ selected_check

theorem selected_exact_recovery :
    Phase17Finite.protectedView selectedOffer.next = Phase17Finite.protectedView Phase17Finite.selectedAfter ∧
    Phase17Finite.recover selectedOffer.update selectedOffer.next = Phase17Finite.selectedAfter :=
  checked_protected_recovery fixed contexts charges _ _ selected_check

def resultSummary (poolSize fuel : Nat) : Outcome Offer → Nat × Option Nat × Nat
  | .accepted index _ => (0, some index, index + 1)
  | .exhausted => (1, none, poolSize)
  | .budgetStop => (2, none, fuel)
'''
    rejected = {}
    for name in CASE_NAMES:
        source, offers, _ = case_terms[name]
        for offer in offers:
            if offer == 'selectedOffer' and source == 'Phase17Finite.selectedAfter':
                continue
            key = (source, offer)
            if key in rejected:
                continue
            text += _rejection_proof(name, source, offer)
            rejected[key] = 'refused_' + name
    case_names = []
    for row in packet['cases']:
        name, result = row['name'], row['result']
        source, offers, fuel = case_terms[name]
        expr = 'search fixed contexts charges ' + source + ' [' + ', '.join(offers) + '] ' + _nat(fuel)
        text += 'def result_' + name + ' : Outcome Offer := ' + expr + '\n'
        text += ('theorem case_' + name + ' : resultSummary ' + _nat(len(offers)) + ' ' + _nat(fuel) +
                ' result_' + name + ' = ' + _expected(result) + ' := by\n')
        if result['examined'] == 0:
            text += '  rfl\n'
        else:
            simp = ['result_' + name, 'search', 'scan']
            visited = offers[:result['examined']]
            passing = any((source, offer) not in rejected for offer in visited)
            failing = any((source, offer) in rejected for offer in visited)
            simp.extend(dict.fromkeys(rejected.get((source, offer), 'selected_check') for offer in visited))
            if failing:
                simp += ['Bool.false_eq_true', 'if_false', 'advance']
            if passing:
                simp += ['if_true']
            simp += ['resultSummary']
            text += '  simp only [' + ', '.join(simp) + ']\n'
        case_names.append('case_' + name)
    text += '''
theorem selected_source_capacity (providers : Contexts) (work : Charges)
    (states : Nat → State) (offers : Nat → Offer) (steps : Nat)
    (initial : states 0 = Phase17Finite.selectedAfter)
    (run : ∀ i, i < steps → (offers i).next = states (i + 1) ∧
      check fixed providers work (states i) (offers i) = true) : steps ≤ 260 := by
  have bound := checked_run_length_bound fixed providers work 282
    (extended_catalog_bound Phase17Finite.selectedConfiguration) states offers steps run
  have size : (Phase17Finite.frontier fixed Phase17Finite.selectedAfter).card = 22 := by
    rw [Phase17SecondStep.selected_frontiers.2.1]
    exact Finset.card_range 22
  rw [initial, size] at bound
  omega

theorem selected_successor_capacity (providers : Contexts) (work : Charges)
    (states : Nat → State) (offers : Nat → Offer) (steps : Nat)
    (initial : states 0 = observedAfter)
    (run : ∀ i, i < steps → (offers i).next = states (i + 1) ∧
      check fixed providers work (states i) (offers i) = true) : steps ≤ 259 := by
  have bound := checked_run_length_bound fixed providers work 282
    (extended_catalog_bound Phase17Finite.selectedConfiguration) states offers steps run
  have size : (Phase17Finite.frontier fixed observedAfter).card = 23 :=
    Phase17SecondStep.selected_frontiers.2.2.2
  rw [initial, size] at bound
  omega

theorem budget_can_hide_accepted :
    search fixed contexts charges Phase17Finite.selectedAfter [selectedOffer] 0 = .budgetStop ∧
    Accepted fixed contexts charges Phase17Finite.selectedAfter selectedOffer :=
  ⟨rfl, selected_interface_accepted⟩

theorem pool_exhaustion_is_local :
    search fixed contexts charges Phase17Finite.selectedAfter [] 0 = .exhausted ∧
    Accepted fixed contexts charges Phase17Finite.selectedAfter selectedOffer :=
  ⟨rfl, selected_interface_accepted⟩

end Phase17SuccessorInterface
'''
    return text.encode('utf-8')


def render_positive(prepared):
    require(type(prepared) is PreparedSuccessorInterface, 'exact prepared successor interface required')
    return ('import TruthfulSuccessorInterface\n' + '\n'.join('#print axioms ' + n for n in NAMES) + '\n').encode()


def render_negative(prepared, label):
    require(type(prepared) is PreparedSuccessorInterface and label in NEGATIVES, 'exact interface negative required')
    mapping = {
        'FalseRootAcceptance': 'refusal', 'FalseParentAcceptance': 'stale_parent',
        'FalseContextAcceptance': 'wrong_context', 'FalseResourceAcceptance': 'omitted_charge',
        'FalseTypedAcceptance': 'wrong_program', 'FalseProtectedAcceptance': 'changed_protected',
        'FalseTaskNameAcceptance': 'wrong_task_name', 'AlreadySolvedAcceptance': 'already_solved',
        'FalseSuccessorAcceptance': 'false_successor', 'FalseSourceDomainAcceptance': 'source_inadmissible',
        'EmptyPoolAcceptance': 'empty', 'BudgetCalledExhaustion': 'zero_budget',
        'UncheckedSuffixCalledExhaustion': 'budget_before_selected',
    }
    prefix = '''import TruthfulSuccessorInterface
namespace Phase17SuccessorInterfaceControl
open Phase17SuccessorInterface Phase17TruthfulSuccessor Phase17SecondStep
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
'''
    if label == 'SkippedFirstPassingOffer':
        assertion = 'decide (resultSummary 2 2 (search fixed contexts charges Phase17Finite.selectedAfter [selectedOffer, selectedOffer] 2) = (0, some 1, 2))'
        proof = 'by simp [wrongClaim, search, scan, selected_check, resultSummary]'
    else:
        name = mapping[label]
        case = next(row for row in prepared.packet['cases'] if row['name'] == name)
        result = case['result']
        wrong = '(1, none, ' + _nat(result['examined']) + ')' if label in (
            'BudgetCalledExhaustion', 'UncheckedSuffixCalledExhaustion') else '(0, some 0, 1)'
        assertion = ('decide (resultSummary ' + _nat(result['pool_size']) + ' ' + _nat(result['inspection_budget']) +
            ' result_' + name + ' = ' + wrong + ')')
        proof = 'by simp only [wrongClaim, case_' + name + ']; decide +kernel'
    text = prefix + 'def wrongClaim : Bool := ' + assertion + '\n'
    text += 'theorem actual_rejection : wrongClaim = false := ' + proof + '\n'
    text += 'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
    text += 'end Phase17SuccessorInterfaceControl\n'
    return text.encode()


def sources(prepared, root):
    require(type(prepared) is PreparedSuccessorInterface, 'exact prepared successor interface required')
    inherited_sources = inherited.sources(prepared.second_step(), root)
    result = {name: inherited_sources[name] for name in inherited.MODULES}
    result[MODULES[-1]] = render_selected(prepared, root)
    result[POSITIVE] = render_positive(prepared)
    result.update({name: render_negative(prepared, name) for name in NEGATIVES})
    for name, raw in result.items():
        require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', raw),
                'forbidden proof source token: ' + name)
    return result


def parse_audits(stdout):
    cursor, audits = 0, {}
    for name in NAMES:
        match = re.compile("'" + re.escape(name) +
            r"' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*", re.S).match(stdout, cursor)
        require(match is not None, 'missing or reordered successor interface audit: ' + name)
        axioms = [] if match[1] is None else [x.strip() for x in match[1].split(',') if x.strip()]
        require(len(axioms) == len(set(axioms)) and set(axioms) <= ALLOWED_AXIOMS,
                'unapproved successor interface axiom')
        audits[name] = axioms
        cursor = match.end()
    require(cursor == len(stdout), 'unexpected successor interface audit output')
    return audits


def validate_negative(label, raw, stdout, stderr, returncode):
    require(label in NEGATIVES and type(returncode) is int and returncode == 1 and not stderr,
            'negative control did not return intended compiler rejection')
    line, col = negative_location(raw)
    expected = re.compile(r'(?:[^\r\n]*[/\\])?' + re.escape(label) + r'\.lean:' + str(line) + ':' + str(col) +
        r': error: Tactic `decide` proved that the proposition\s+False\s+is false\s*')
    require(expected.fullmatch(stdout) is not None, 'negative diagnostic is not exact intended False assertion')
