"""Phase 17AD sources: one kernel, projected successor context, explicit catalog bound."""
from __future__ import annotations

import json
from pathlib import Path
import re

from . import finite_kernel_lean
from .materialized import require, sha
from .successor_context import PreparedSuccessorContext

BRIDGE = 'lean/phase17_bridge/SuccessorContext.lean'
MODULES = ('ProposalProvenance', 'ControllerContinuation', 'FiniteObservationKernel',
           'SuccessorContext', 'SelectedFiniteKernel')
POSITIVE = 'SuccessorContextExamples'
NEGATIVES = ('StaleParent', 'ReusedContext', 'StaleHistory', 'StaleStateIdentity',
             'WrongNextChoice', 'PrematureRoot', 'MissingSourceCharges', 'WrongGenerator',
             'UnchangedFrontier', 'CatalogOverflow')
LABELS = (POSITIVE, *NEGATIVES)
ALLOWED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}
GENERIC_BODIES = ('LearnedStateBinding', 'TaskFrontier', 'JointEvidence',
                  'ProtectedSemantics', 'ResourceAccounting', 'FiniteObservationKernel')
PINS = {
    'ProposalProvenance': '3cae873ff4dba673c926ac4ecf214d349c2ec6a635bf0ead44547bebc76056a4',
    'ControllerContinuation': 'e585f612956d09eac8f18c08a25ca79b4b7908c0c862c8f2516b175966c7fc69',
    'LearnedStateBinding': '2184da4d22db9d9d55f5978968f7ba4e4d769b07d22f86a81cef678cb730f8ab',
    'TaskFrontier': 'fcc5cdfcbc87f3a0d5aeed901e685ecb5191aee293afc23f22d054291a99c114',
    'JointEvidence': 'fb2c7b1dc21a73ae6bcf1b2d554236d2f0569dc84568618b645a6f32cb61428d',
    'ProtectedSemantics': '2e7a34d2a61e5772c4f738f125ec93738c7f5a2a87b6c1b4783a039a1ca5ae4a',
    'ResourceAccounting': '0dedb05591770f67e8ede705930d3c850edc0ff4ada0bb6768033def975b3ca5',
    'FiniteObservationKernel': '81e6371015b8f10c83312f0733a9df7b3b4a75bbbe36348e5b187dd564a60879',
}
GENERIC_NAMES = tuple('Phase17SuccessorContext.' + name for name in (
    'base', 'learned', 'configuration_semantics_fixed', 'base_semantics_fixed',
    'learned_semantics_fixed', 'packet_uses_source_context', 'base_obligations_iff',
    'learned_obligations_iff', 'accepted_iff_local', 'accepted', 'facts_require_parent',
    'accepted_requires_parent', 'accepted_context_valid', 'accepted_source_charges',
    'stale_parent_rejected', 'facts_change_package', 'successor_context_must_change',
    'stale_successor_context_rejected', 'present_configuration_congruence',
    'present_acceptance_congruence', 'successor_controller_available', 'two_step_continuation',
))
SELECTED_NAMES = tuple('Phase17SuccessorContextExamples.' + name for name in (
    'selected_local_configuration', 'selected_first_transport', 'selected_next_context',
    'selected_next_parent', 'selected_next_valid', 'selected_context_changes',
    'selected_generator_bound', 'selected_next_decision', 'selected_projected_bindings',
    'selected_stale_context_rejected', 'selected_frontier_retention',
    'selected_catalog_rejects_above', 'selected_frontier_subset',
    'selected_frontier_card_bound', 'selected_after_saturated', 'selected_no_further_strict_step',
))
NAMES = GENERIC_NAMES + SELECTED_NAMES


def _nat(value: int) -> str:
    require(type(value) is int and value >= 0, 'natural literal required')
    return str(value)


def _int(value: int) -> str:
    require(type(value) is int, 'integer literal required')
    return str(value) if value >= 0 else '(' + str(value) + ')'


def _string(value: str) -> str:
    require(type(value) is str and re.fullmatch('[a-zA-Z0-9_.:-]*', value), 'ASCII literal required')
    return json.dumps(value)


def _read(root: Path, name: str) -> bytes:
    path = root / 'lean/phase17_bridge' / (name + '.lean')
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'missing/linked successor-context template: ' + name)
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    if name in PINS:
        require(sha(raw) == PINS[name], 'inherited successor-context template changed: ' + name)
    return raw


def _split_imports(raw: bytes) -> tuple[list[str], str]:
    imports, lines = [], []
    started = False
    for line in raw.decode('utf-8').splitlines(keepends=True):
        if line.startswith('import '):
            require(not started, 'embedded template import')
            imports.append(line.rstrip('\n'))
        else:
            if line.strip():
                started = True
            lines.append(line)
    return imports, ''.join(lines)


def generic_finite_module(root: Path) -> bytes:
    imports, bodies = ['import ProposalProvenance'], []
    for name in GENERIC_BODIES:
        head, body = _split_imports(_read(root, name))
        for line in head:
            if line not in imports:
                imports.append(line)
        bodies.append(body)
    return ('\n'.join(imports) + '\n' + '\n'.join(bodies)).encode('utf-8')


def selected_finite_module(prepared: PreparedSuccessorContext, root: Path) -> bytes:
    original = finite_kernel_lean.render(prepared.finite(), source_root=root)
    suffix = ('\n'.join('#print axioms ' + name for name in finite_kernel_lean.NAMES) + '\n').encode()
    require(original.endswith(suffix), 'Q audit suffix differs')
    _, selected = _split_imports(original[:-len(suffix)])
    for name in (*GENERIC_BODIES, 'ProposalProvenance'):
        _, body = _split_imports(_read(root, name))
        require(selected.count(body) == 1, 'Q generic body occurrence differs: ' + name)
        selected = selected.replace(body, '', 1)
    require(not re.search(r'^\s*(import |#print)', selected, re.M), 'unexpected Q residual command')
    return ('import FiniteObservationKernel\n' + selected).encode('utf-8')


def _common(prepared: PreparedSuccessorContext) -> str:
    p = prepared.packet
    context = p['next_context']['provenance_context']
    rows = ['{ key := ' + _string(row['key']) + ', family := ' + _nat(row['family']) +
            ', baseScore := ' + _int(row['base_score']) + ', ties := [' +
            ', '.join(_nat(x) for x in row['ties']) + '] }' for row in context['rows']]
    text = ('import SelectedFiniteKernel\nimport SuccessorContext\n'
            'namespace Phase17SuccessorContextExamples\n'
            'open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3 Phase17SuccessorContext\n'
            'set_option maxRecDepth 32768\nset_option maxHeartbeats 16000000\n'
            '-- Prospective input projection; no new challenge or accepted successor is asserted.\n')
    text += 'def nextContext : Phase17Provenance.Context := {\n'
    for target, source in (('generator', 'generator'), ('parentPackage', 'parent_package'),
                           ('contextHash', 'context_hash'), ('transcriptHash', 'transcript_hash')):
        text += '  ' + target + ' := ' + _string(context[source]) + '\n'
    text += '  credits := ' + _nat(context['credits']) + '\n  offset := ' + _nat(context['offset'])
    text += '\n  rows := [' + ', '.join(rows) + '] }\n'
    text += '''
def selectedContexts (s : State) : Phase17Provenance.Context :=
  if s.packageHash = Phase17Finite.selectedBefore.packageHash then
    Phase17Finite.selectedConfiguration.context else nextContext

def selectedCharges (laterCharges : Charges) (s : State) : List Phase17Resource.Kind :=
  if s.packageHash = Phase17Finite.selectedBefore.packageHash then
    Phase17Finite.selectedConfiguration.expectedCharges else laterCharges s
'''
    for name, value in (
        ('prospectiveStateHash', p['prospective_state_hash']),
        ('prospectiveHistoryHash', p['prospective_history_hash']),
        ('priorStateHash', p['transition']['parent_state_hash']),
        ('viewStateHash', p['next_context']['view']['predecessor_state_hash']),
        ('viewPackageHash', p['next_context']['view']['active_package_hash']),
        ('viewRootHash', p['next_context']['view']['fixed_verifier_hash']),
        ('transitionParentHash', p['transition']['parent_physical_package_hash']),
        ('transitionCandidateHash', p['transition']['candidate_physical_package_hash']),
        ('projectedGenerator', p['next_context']['context_binding']['generator_id']),
        ('initialCandidateHash', p['next_context']['initial_candidate_hash']),
    ):
        text += 'def ' + name + ' : String := ' + _string(value) + '\n'
    text += 'def nextTurn : Nat := ' + _nat(p['transition']['next_turn_index']) + '\n'
    text += 'def priorTurn : Nat := ' + _nat(p['transition']['prior_turn_index']) + '\n'
    return text


def render_positive(prepared: PreparedSuccessorContext) -> bytes:
    text = _common(prepared)
    index = _nat(prepared.packet['next_context']['initial_candidate_index'])
    text += '''
theorem selected_local_configuration (laterCharges : Charges) :
    configurationAt Phase17Finite.selectedConfiguration selectedContexts
      (selectedCharges laterCharges) Phase17Finite.selectedBefore =
        Phase17Finite.selectedConfiguration := by
  simp [configurationAt, selectedContexts, selectedCharges]

theorem selected_first_transport (laterCharges : Charges) :
    Learned.LearnedAcceptedStep
      (learned Phase17Finite.selectedConfiguration selectedContexts (selectedCharges laterCharges))
      Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
      (packet Phase17Finite.selectedConfiguration selectedContexts (selectedCharges laterCharges)
        Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) := by
  apply accepted
  rw [selected_local_configuration]
  exact Phase17Finite.selected_facts

theorem selected_next_context : selectedContexts Phase17Finite.selectedAfter = nextContext := by
  have changed : Phase17Finite.selectedAfter.packageHash ≠ Phase17Finite.selectedBefore.packageHash := by
    decide +kernel
  simp only [selectedContexts, if_neg changed]

theorem selected_next_parent : nextContext.parentPackage = Phase17Finite.selectedAfter.packageHash := by
  decide +kernel

theorem selected_next_valid : Phase17Provenance.ContextValid nextContext := by
  unfold Phase17Provenance.ContextValid
  decide +kernel

theorem selected_context_changes : nextContext ≠ Phase17Finite.selectedConfiguration.context := by
  intro same
  have different : nextContext.parentPackage ≠
      Phase17Finite.selectedConfiguration.context.parentPackage := by decide +kernel
  exact different (congrArg Phase17Provenance.Context.parentPackage same)

theorem selected_generator_bound (laterCharges : Charges) :
    (learned Phase17Finite.selectedConfiguration selectedContexts (selectedCharges laterCharges)).generatorBound
      Phase17Finite.selectedAfter nextContext.generator := by
  change nextContext.generator = (selectedContexts Phase17Finite.selectedAfter).generator ∧
    (selectedContexts Phase17Finite.selectedAfter).parentPackage = Phase17Finite.selectedAfter.packageHash ∧
    Phase17Provenance.ContextValid (selectedContexts Phase17Finite.selectedAfter)
  rw [selected_next_context]
  exact ⟨rfl, selected_next_parent, selected_next_valid⟩
'''
    text += '''
theorem selected_next_decision :
    Phase17Controller.decision nextContext (Phase17Controller.initial nextContext.credits) =
      some (.evaluate ''' + index + ''') ∧
    (Phase17Provenance.rowAt nextContext ''' + index + ''').key = initialCandidateHash := by
  decide +kernel
'''
    text += '''
theorem selected_projected_bindings :
    transitionParentHash = Phase17Finite.selectedBefore.packageHash ∧
    transitionCandidateHash = Phase17Finite.selectedAfter.packageHash ∧
    viewPackageHash = Phase17Finite.selectedAfter.packageHash ∧
    viewRootHash = Phase17Finite.fixedRoot ∧
    viewStateHash = prospectiveStateHash ∧ prospectiveStateHash ≠ priorStateHash ∧
    nextContext.transcriptHash = prospectiveHistoryHash ∧
    nextContext.generator = projectedGenerator ∧ nextTurn = priorTurn + 1 := by decide +kernel

theorem selected_stale_context_rejected (laterCharges : Charges) (c : Candidate) (e : Evidence) :
    ¬ Learned.LearnedAcceptedStep
      (learned Phase17Finite.selectedConfiguration
        (fun _ => Phase17Finite.selectedConfiguration.context) (selectedCharges laterCharges))
      Phase17Finite.selectedAfter c
      (packet Phase17Finite.selectedConfiguration
        (fun _ => Phase17Finite.selectedConfiguration.context) (selectedCharges laterCharges)
        Phase17Finite.selectedAfter e) := by
  apply stale_parent_rejected
  decide +kernel

theorem selected_frontier_retention (contexts : Contexts) (charges : Charges) :
    ((learned Phase17Finite.selectedConfiguration contexts charges).frontier Phase17Finite.selectedBefore).card = 21 ∧
    ((learned Phase17Finite.selectedConfiguration contexts charges).frontier Phase17Finite.selectedAfter).card = 22 ∧
    (learned Phase17Finite.selectedConfiguration contexts charges).frontier Phase17Finite.selectedBefore ⊆
      (learned Phase17Finite.selectedConfiguration contexts charges).frontier Phase17Finite.selectedAfter := by
  refine ⟨?_, ?_, Phase17Finite.selected_facts.expansion.1⟩
  · change (Phase17Finite.frontier Phase17Finite.selectedConfiguration Phase17Finite.selectedBefore).card = 21
    decide +kernel
  · change (Phase17Finite.frontier Phase17Finite.selectedConfiguration Phase17Finite.selectedAfter).card = 22
    decide +kernel

-- Q's preserved catalog is exhausted at the selected successor. The generic
-- two-step theorem does not supply a second strict step for this finite catalog.
theorem selected_catalog_rejects_above (n : Nat) (bound : 22 ≤ n) :
    Phase17TaskMeaning.catalog n = Phase17TaskMeaning.rejectMeaning := by
  obtain ⟨k, equal⟩ := Nat.exists_eq_add_of_le bound
  rw [equal, Nat.add_comm 22 k]
  rfl

theorem selected_frontier_subset (contexts : Contexts) (charges : Charges) (s : State) :
    (learned Phase17Finite.selectedConfiguration contexts charges).frontier s ⊆ Finset.range 22 := by
  intro t member
  by_contra missing
  have outside : ¬ t < 22 := by simpa only [Finset.mem_range] using missing
  have solved := (learned Phase17Finite.selectedConfiguration contexts charges).frontierSound member
  change (Phase17TaskMeaning.catalog t).holds (Phase17Finite.taskObservation s) at solved
  rw [selected_catalog_rejects_above t (Nat.le_of_not_gt outside)] at solved
  exact solved

theorem selected_frontier_card_bound (contexts : Contexts) (charges : Charges) (s : State) :
    ((learned Phase17Finite.selectedConfiguration contexts charges).frontier s).card ≤ 22 := by
  have bounded := Finset.card_le_card (selected_frontier_subset contexts charges s)
  simpa only [Finset.card_range] using bounded

theorem selected_after_saturated (contexts : Contexts) (charges : Charges) :
    ((learned Phase17Finite.selectedConfiguration contexts charges).frontier Phase17Finite.selectedAfter).card = 22 :=
  (selected_frontier_retention contexts charges).2.1

theorem selected_no_further_strict_step (contexts : Contexts) (charges : Charges)
    (c : Candidate) (e : Evidence) :
    ¬ Learned.LearnedAcceptedStep (learned Phase17Finite.selectedConfiguration contexts charges)
      Phase17Finite.selectedAfter c
      (packet Phase17Finite.selectedConfiguration contexts charges Phase17Finite.selectedAfter e) := by
  intro claimed
  have growth := claimed.learnedObligations.strictFrontierExpansion.2
  have bounded := selected_frontier_card_bound contexts charges c.next
  have saturated := selected_after_saturated contexts charges
  omega

end Phase17SuccessorContextExamples
'''
    text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    return text.encode('utf-8')


def render_negative(prepared: PreparedSuccessorContext, label: str) -> bytes:
    require(label in NEGATIVES, 'unknown successor-context negative')
    index = prepared.packet['next_context']['initial_candidate_index']
    assertions = {
        'StaleParent': 'decide (({ nextContext with parentPackage := Phase17Finite.selectedBefore.packageHash } : Phase17Provenance.Context).parentPackage = Phase17Finite.selectedAfter.packageHash)',
        'ReusedContext': 'decide (nextContext.contextHash = Phase17Finite.selectedConfiguration.context.contextHash)',
        'StaleHistory': 'decide (nextContext.transcriptHash = Phase17Finite.selectedConfiguration.context.transcriptHash)',
        'StaleStateIdentity': 'decide (viewStateHash = priorStateHash)',
        'WrongNextChoice': 'decide (Phase17Controller.decision nextContext (Phase17Controller.initial nextContext.credits) = some (.evaluate ' + _nat((index + 1) % 32) + '))',
        'PrematureRoot': 'decide (Phase17Controller.decision nextContext (Phase17Controller.initial nextContext.credits) = some .awaitRoot)',
        'MissingSourceCharges': '@decide (Phase17Finite.resourceValid (configurationAt Phase17Finite.selectedConfiguration selectedContexts (fun _ => []) Phase17Finite.selectedBefore) Phase17Finite.selectedCandidate Phase17Finite.selectedEvidence) (by unfold Phase17Finite.resourceValid Phase17Resource.Fits; infer_instance)',
        'WrongGenerator': 'decide (nextContext.generator = Phase17Finite.selectedConfiguration.context.generator)',
        'UnchangedFrontier': 'decide (Phase17Finite.frontier Phase17Finite.selectedConfiguration Phase17Finite.selectedBefore = Phase17Finite.frontier Phase17Finite.selectedConfiguration Phase17Finite.selectedAfter)',
        'CatalogOverflow': '(Phase17TaskMeaning.catalog 22).check (Phase17Finite.taskObservation Phase17Finite.selectedAfter)',
    }
    text = _common(prepared) + 'def wrongClaim : Bool := ' + assertions[label] + '\n'
    text += 'theorem actual_rejection : wrongClaim = false := by decide +kernel\n'
    text += 'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
    text += 'end Phase17SuccessorContextExamples\n'
    return text.encode('utf-8')


def sources(prepared: PreparedSuccessorContext, root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedSuccessorContext, 'exact successor-context input required')
    result = {
        MODULES[0]: _read(root, MODULES[0]),
        MODULES[1]: _read(root, MODULES[1]),
        MODULES[2]: generic_finite_module(root),
        MODULES[3]: _read(root, MODULES[3]),
        MODULES[4]: selected_finite_module(prepared, root),
        POSITIVE: render_positive(prepared),
    }
    result.update({label: render_negative(prepared, label) for label in NEGATIVES})
    for label, raw in result.items():
        require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', raw),
                'forbidden proof source token: ' + label)
    return result


def parse_audits(stdout: str) -> dict:
    cursor, audits = 0, {}
    for name in NAMES:
        match = re.compile("'" + re.escape(name) +
            r"' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])\s*", re.S).match(stdout, cursor)
        require(match is not None, 'missing or reordered successor-context audit: ' + name)
        axioms = [] if match[1] is None else [x.strip() for x in match[1].split(',') if x.strip()]
        require(len(axioms) == len(set(axioms)) and set(axioms) <= ALLOWED_AXIOMS, 'unapproved successor-context axiom')
        audits[name] = axioms
        cursor = match.end()
    require(cursor == len(stdout), 'unexpected successor-context audit output')
    return audits


def negative_location(raw: bytes) -> tuple[int, int]:
    lines = raw.decode('utf-8').splitlines()
    require(lines.count('example : wrongClaim = true := by') == 1, 'negative assertion identity')
    index = lines.index('example : wrongClaim = true := by')
    require(lines[index + 1:index + 3] ==
            ['  simp only [actual_rejection, Bool.false_eq_true]', '  decide'],
            'negative assertion tactic identity')
    return index + 3, 2


def validate_negative(label: str, raw: bytes, stdout: str, stderr: str, returncode: int) -> None:
    require(label in NEGATIVES and type(returncode) is int and returncode == 1 and not stderr,
            'negative control did not return intended compiler rejection')
    line, col = negative_location(raw)
    expected = re.compile(r'(?:[^\r\n]*[/\\])?' + re.escape(label) + r'\.lean:' + str(line) + ':' + str(col) +
        r': error: Tactic `decide` proved that the proposition\s+False\s+is false\s*')
    require(expected.fullmatch(stdout) is not None, 'negative diagnostic is not exact intended False assertion')
