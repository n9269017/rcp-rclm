"""Phase 17AF: concrete second acceptance in AE's fixed semantic kernel.

The renderer authenticates immutable prepared input through ``PreparedSecondStep``.
It retains the six inherited module bytes and adds a concrete second transition.
The selected two-step theorem has no assumed future Facts, context or charge
provider. Physical extraction and bounded reference accounting retain their
explicit external scope.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from . import task_interpretation_lean as inherited
from .materialized import require, sha
from .second_step import PreparedSecondStep
from .successor_lean import program, string

MODULES = (*inherited.MODULES, 'SelectedSecondStep')
POSITIVE = 'SecondStepExamples'
NEGATIVES = ('StaleParent', 'WrongContext', 'MixedCandidate', 'WrongRoot',
             'SkippedProposal', 'WrongProgram', 'WrongTaskName', 'UnchangedFrontier',
             'ChangedProtected', 'OmittedCharge', 'OverBudget', 'AlreadySolvedCredit')
LABELS = (POSITIVE, *NEGATIVES)
ALLOWED_AXIOMS = inherited.ALLOWED_AXIOMS
GENERIC_BODIES = inherited.GENERIC_BODIES
PINS = {**inherited.PINS,
        'TaskInterpretation': 'ffa8ba516458b81ebb2909b19ad377c01073d61254b8daee967cbcf53a8d43b9'}
_split_imports = inherited._split_imports
generic_finite_module = inherited.generic_finite_module
selected_finite_module = inherited.selected_finite_module

SELECTED_NAMES = tuple('Phase17SecondStep.' + name for name in (
    'selected_legacy_complete', 'selected_catalog_complete', 'fixed_interpretation',
    'second_before_matches', 'second_meaning', 'second_context_parent',
    'second_context_valid', 'second_context_changes', 'second_initial_choice',
    'second_program_reachable', 'second_verdict_truthful', 'first_configuration',
    'second_configuration', 'first_facts', 'first_semantic_failure',
    'second_facts', 'second_semantic_failure', 'first_accepted', 'second_accepted',
    'second_base_obligations', 'second_learned_obligations', 'selected_two_step',
    'selected_frontiers', 'selected_registry_counts', 'second_semantic_gain',
    'second_universal_program', 'second_protected_preservation', 'second_exact_recovery',
    'selected_two_step_recovery', 'second_resource_totals', 'second_source_resources',
    'selected_affine_availability',
))
NAMES = ('Phase17TaskInterpretation.accepted_affine_program',
         'Phase17TaskInterpretation.guarded_two_step', *SELECTED_NAMES)


def _read(root: Path, name: str) -> bytes:
    raw = inherited._read(root, name)
    if name in PINS:
        require(sha(raw) == PINS[name], 'inherited second-step template changed: ' + name)
    return raw


def _nat(value: int) -> str:
    require(type(value) is int and value >= 0, 'natural literal required')
    return str(value)


def _int(value: int) -> str:
    require(type(value) is int, 'integer literal required')
    return str(value) if value >= 0 else '(' + str(value) + ')'


def _list(values, emit) -> str:
    require(type(values) is list, 'literal list required')
    return '[' + ', '.join(emit(v) for v in values) + ']'


def _kinds(values: list[str]) -> str:
    require(type(values) is list and all(v in ('candidate', 'vector') for v in values),
            'reference charge kinds differ')
    return '[' + ', '.join('.' + v for v in values) + ']'


def _state(name: str, value: dict) -> str:
    images = _list(value['frozen'], lambda rows: _list(rows, lambda row:
        '⟨' + string(row['path']) + ', ' + _nat(row['size']) + ', ' + string(row['sha256']) + '⟩'))
    proofs = _list(value['proofs'], lambda row:
                   '(' + ', '.join(string(item) for item in row) + ')')
    require(len(value['programs']) == len(value['keys']), 'projected program/key inventory differs')
    programs = '[' + ', '.join('(' + string(key) + ', ' + program(p) + ')'
        for key, p in zip(value['keys'], value['programs'], strict=True)) + ']'
    semantic = value['semantic']
    vectors = lambda rows: _list(rows, lambda row: _list(row, _nat))
    return ('def ' + name + ' : State := {\n'
            '  frozen := ' + images + '\n'
            '  keys := ' + _list(value['keys'], string) + '\n'
            '  proofs := ' + proofs + '\n'
            '  programs := ' + programs + '\n'
            '  declared := (' + _list(value['declared'], _nat) + ' : List Nat).toFinset\n'
            '  namedFrontier := (' + _list(value['named_frontier'], string) + ' : List String).toFinset\n'
            '  semantic := { rows := ' + vectors(semantic['mass_minus_one_dictionary']) +
            ', selectors := ' + _list(semantic['row_selectors'], _nat) +
            ', goals := ' + vectors(semantic['goals']) + ' }\n'
            '  packageHash := ' + string(value['package_hash']) + '\n'
            '  root := ' + string(value['root']) + ' }\n')


def _context(value: dict) -> str:
    rows = _list(value['rows'], lambda row:
        '{ key := ' + string(row['key']) + ', family := ' + _nat(row['family']) +
        ', baseScore := ' + _int(row['base_score']) +
        ', ties := ' + _list(row['ties'], _nat) + ' }')
    fields = [('generator', value['generator']), ('parentPackage', value['parent_package']),
              ('contextHash', value['context_hash']), ('transcriptHash', value['transcript_hash'])]
    return ('def secondContext : Phase17Provenance.Context := {\n' +
            ''.join('  ' + name + ' := ' + string(item) + '\n' for name, item in fields) +
            '  credits := ' + _nat(value['credits']) + '\n' +
            '  offset := ' + _nat(value['offset']) + '\n  rows := ' + rows + ' }\n')


def render_selected(prepared: PreparedSecondStep) -> bytes:
    require(type(prepared) is PreparedSecondStep, 'exact prepared second-step input required')
    p = prepared.packet
    update = p['update']
    proposal = p['proposal']
    context = p['second_context']
    source = prepared.successor_context().packet['next_context']
    text = '''import SelectedFiniteKernel
import TaskInterpretation
namespace Phase17SecondStep
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3 Phase17TaskInterpretation
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000

def fixed : Phase17Finite.Configuration :=
  extendConfiguration Phase17Finite.selectedConfiguration
'''
    text += '-- Complete AF input packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    text += ('-- The canonical AF transcript digest is checked by Python. The inherited\n'
             '-- AD context transcript field remains its prospective history anchor.\n')
    text += 'def referenceTranscriptDigest : String := ' + string(p['reference_transcript_sha256']) + '\n'
    text += _state('observedBefore', p['finite_projection']['before'])
    text += _state('observedAfter', p['finite_projection']['after'])
    text += _context(context)
    text += 'def secondIndex : Nat := ' + _nat(source['initial_candidate_index']) + '\n'
    text += 'def secondPrograms : List Program := ' + _list(source['programs'], program) + '\n'
    text += 'def secondCharges : List Phase17Resource.Kind := ' + _kinds(p['resource']['charge_sequence']) + '\n'
    text += 'def secondUpdate : Phase17Finite.Update := {\n'
    text += '  key := ' + string(update['key']) + '\n  program := ' + program(update['program']) + '\n'
    text += '  task := ' + _nat(update['task']) + '\n  taskName := ' + string(update['task_name']) + '\n'
    for target, key in (('parentPackage', 'parent_package'), ('candidatePackage', 'candidate_package'),
                        ('contextHash', 'context_hash')):
        text += '  ' + target + ' := ' + string(update[key]) + '\n'
    text += '  charges := ' + _kinds(update['charges']) + ' }\n'
    text += 'def secondCandidate : Candidate := ⟨secondUpdate, observedAfter⟩\n'
    text += 'def secondProposal : Phase17Provenance.Proposal := {\n'
    for target, key in (('generator', 'generator'), ('parentPackage', 'parent_package'),
                        ('contextHash', 'context_hash'), ('transcriptHash', 'transcript_hash'),
                        ('program', 'program'), ('candidatePackage', 'candidate_package')):
        text += '  ' + target + ' := ' + string(proposal[key]) + '\n'
    text += '  choices := ' + _list(proposal['choices'], _nat) + '\n'
    require(all(type(v) is bool for v in proposal['verdicts']), 'literal verdict booleans required')
    text += '  verdicts := [' + ', '.join('true' if v else 'false' for v in proposal['verdicts']) + '] }\n'
    text += 'def secondEvidence : Evidence := {\n'
    for target, value in (('root', p['finite_projection']['before']['root']),
                           ('parentPackage', update['parent_package']),
                           ('candidatePackage', update['candidate_package']),
                           ('contextHash', context['context_hash']),
                           ('transcriptHash', context['transcript_hash'])):
        text += '  ' + target + ' := ' + string(value) + '\n'
    text += '  proposal := secondProposal\n  charges := secondCharges }\n'
    text += '''
-- The two source contexts and charge lists are explicit data. They carry no
-- authentication or accepted transition for any later package.
def contexts (s : State) : Phase17Provenance.Context :=
  if s.packageHash = Phase17Finite.selectedBefore.packageHash then
    Phase17Finite.selectedConfiguration.context else secondContext

def charges (s : State) : List Phase17Resource.Kind :=
  if s.packageHash = Phase17Finite.selectedBefore.packageHash then
    Phase17Finite.selectedConfiguration.expectedCharges else secondCharges

def secondConfiguration : Phase17Finite.Configuration :=
  { fixed with context := secondContext, expectedCharges := secondCharges }

def semanticVerdict (index : Nat) : Bool :=
  (fixed.catalog secondUpdate.task).check
    { proofs := Phase17Finite.selectedAfter.proofs
      programs := Phase17Finite.selectedAfter.programs ++
        [((Phase17Provenance.rowAt secondContext index).key,
          secondPrograms.getD index ⟨8, 0, 0, 0⟩)] }

def available (s : State) : Finset Nat :=
  (Finset.range 282).filter (fun task => 22 ≤ task ∧
    (fixed.catalog task).check (Phase17Finite.taskObservation s) = true)

theorem selected_legacy_complete (task : Nat) (bound : task < 22) (s : Observation) :
    (Phase17TaskMeaning.catalog task).check s = true ↔
      (Phase17TaskMeaning.catalog task).holds s := by
  interval_cases task <;>
    simp only [Phase17TaskMeaning.catalog, theorem_meaning_complete, vector_meaning_complete]

theorem selected_catalog_complete (task : Nat) (s : Observation) :
    (fixed.catalog task).check s = true ↔ (fixed.catalog task).holds s :=
  catalog_complete Phase17TaskMeaning.catalog selected_legacy_complete task s

theorem fixed_interpretation (s : State) :
    (Phase17SuccessorContext.configurationAt fixed contexts charges s).catalog =
      extendedCatalog Phase17TaskMeaning.catalog ∧
    (Phase17SuccessorContext.configurationAt fixed contexts charges s).taskName =
      extendedName Phase17Finite.selectedConfiguration.taskName ∧
    (Phase17SuccessorContext.configurationAt fixed contexts charges s).root =
      Phase17Finite.selectedConfiguration.root ∧
    (Phase17SuccessorContext.configurationAt fixed contexts charges s).contract =
      Phase17Finite.selectedConfiguration.contract ∧
    (Phase17SuccessorContext.configurationAt fixed contexts charges s).policy =
      Phase17Finite.selectedConfiguration.policy := ⟨rfl, rfl, rfl, rfl, rfl⟩

theorem second_before_matches : observedBefore = Phase17Finite.selectedAfter := by
  apply Phase17Finite.state_ext <;> decide +kernel

theorem second_meaning : secondUpdate.task = 41 ∧
    fixed.catalog secondUpdate.task = affineMeaning 0 (-13) ∧
    secondUpdate.taskName = fixed.taskName secondUpdate.task := by
  exact ⟨rfl, rfl, by decide +kernel⟩

theorem second_context_parent :
    secondContext.parentPackage = Phase17Finite.selectedAfter.packageHash := by decide +kernel

theorem second_context_valid : Phase17Provenance.ContextValid secondContext := by
  unfold Phase17Provenance.ContextValid
  decide +kernel

theorem second_context_changes : secondContext ≠ Phase17Finite.selectedConfiguration.context := by
  intro same
  have different : secondContext.parentPackage ≠
      Phase17Finite.selectedConfiguration.context.parentPackage := by decide +kernel
  exact different (congrArg Phase17Provenance.Context.parentPackage same)

theorem second_initial_choice :
    Phase17Controller.decision secondContext (Phase17Controller.initial secondContext.credits) =
      some (.evaluate secondIndex) ∧ secondIndex = 30 := by decide +kernel

theorem second_program_reachable :
    (Phase17Provenance.rowAt secondContext secondIndex).key = secondUpdate.key ∧
    secondPrograms.getD secondIndex ⟨8, 0, 0, 0⟩ = secondUpdate.program ∧
    secondProposal.choices = [secondIndex] ∧
    secondProposal.program = secondUpdate.key := by decide +kernel

theorem second_verdict_truthful :
    secondProposal.verdicts = secondProposal.choices.map semanticVerdict ∧
    secondProposal.verdicts = [true] := by decide +kernel

theorem first_configuration :
    Phase17SuccessorContext.configurationAt fixed contexts charges Phase17Finite.selectedBefore =
      fixed := by simp [Phase17SuccessorContext.configurationAt, contexts, charges, fixed, extendConfiguration]

theorem second_configuration :
    Phase17SuccessorContext.configurationAt fixed contexts charges Phase17Finite.selectedAfter =
      secondConfiguration := by
  have different : Phase17Finite.selectedAfter.packageHash ≠
      Phase17Finite.selectedBefore.packageHash := by decide +kernel
  simp only [Phase17SuccessorContext.configurationAt, contexts, charges, if_neg different,
    secondConfiguration]

theorem first_facts :
    Phase17Finite.Facts
      (Phase17SuccessorContext.configurationAt fixed contexts charges Phase17Finite.selectedBefore)
      Phase17Finite.selectedBefore Phase17Finite.selectedCandidate Phase17Finite.selectedEvidence := by
  rw [first_configuration]
  apply (facts_legacy_iff Phase17Finite.selectedConfiguration
    Phase17Finite.selectedBefore Phase17Finite.selectedCandidate Phase17Finite.selectedEvidence
    (by decide +kernel) (by decide +kernel) (by decide +kernel)).mpr
  exact Phase17Finite.selected_facts

theorem first_semantic_failure :
    SemanticFailure fixed Phase17Finite.selectedBefore Phase17Finite.selectedCandidate := by
  change ¬ (fixed.catalog 21).holds (Phase17Finite.taskObservation Phase17Finite.selectedBefore)
  intro solved
  have checked := (selected_catalog_complete 21 _).mpr solved
  have rejected : (fixed.catalog 21).check
      (Phase17Finite.taskObservation Phase17Finite.selectedBefore) = false := by decide +kernel
  rw [rejected] at checked
  cases checked

theorem second_facts :
    Phase17Finite.Facts
      (Phase17SuccessorContext.configurationAt fixed contexts charges Phase17Finite.selectedAfter)
      Phase17Finite.selectedAfter secondCandidate secondEvidence := by
  rw [second_configuration]
  constructor
  · unfold Phase17Finite.admissible Phase17Protected.WellFormed
    decide +kernel
  · unfold Phase17Finite.admissible Phase17Protected.WellFormed
    decide +kernel
  · apply Phase17Finite.state_ext <;> decide +kernel
  · unfold Phase17Finite.UpdateValid
    decide +kernel
  · unfold Phase17Finite.trustValid Phase17Provenance.ContextValid
    decide +kernel
  · unfold Phase17Finite.resourceValid Phase17Resource.Fits
    decide +kernel
  · unfold Phase17Provenance.CandidateMatches Phase17Provenance.Produced
      Phase17Provenance.ContextValid
    decide +kernel
  · decide +kernel

theorem second_semantic_failure : SemanticFailure fixed Phase17Finite.selectedAfter secondCandidate := by
  change ¬ (fixed.catalog 41).holds (Phase17Finite.taskObservation Phase17Finite.selectedAfter)
  intro solved
  have checked := (selected_catalog_complete 41 _).mpr solved
  have rejected : (fixed.catalog 41).check
      (Phase17Finite.taskObservation Phase17Finite.selectedAfter) = false := by decide +kernel
  rw [rejected] at checked
  cases checked

theorem first_accepted :
    Learned.LearnedAcceptedStep (learned fixed contexts charges) Phase17Finite.selectedBefore
      Phase17Finite.selectedCandidate
      (packet fixed contexts charges Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) :=
  accepted fixed contexts charges Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
    Phase17Finite.selectedEvidence first_facts first_semantic_failure

theorem second_accepted :
    Learned.LearnedAcceptedStep (learned fixed contexts charges) Phase17Finite.selectedAfter
      secondCandidate (packet fixed contexts charges Phase17Finite.selectedAfter secondEvidence) :=
  accepted fixed contexts charges Phase17Finite.selectedAfter secondCandidate secondEvidence
    second_facts second_semantic_failure

theorem second_base_obligations :
    RCP.StepObligations (base fixed contexts charges) Phase17Finite.selectedAfter
      secondCandidate secondEvidence := second_accepted.baseObligations

theorem second_learned_obligations :
    Learned.SpecificObligations (learned fixed contexts charges) Phase17Finite.selectedAfter
      secondCandidate (packet fixed contexts charges Phase17Finite.selectedAfter secondEvidence) :=
  second_accepted.learnedObligations

theorem selected_two_step :
    Learned.LearnedAcceptedStep (learned fixed contexts charges) Phase17Finite.selectedBefore
      Phase17Finite.selectedCandidate
      (packet fixed contexts charges Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) ∧
    Learned.LearnedAcceptedStep (learned fixed contexts charges) Phase17Finite.selectedAfter
      secondCandidate (packet fixed contexts charges Phase17Finite.selectedAfter secondEvidence) ∧
    Phase17Finite.frontier fixed Phase17Finite.selectedBefore ⊆
      Phase17Finite.frontier fixed observedAfter ∧
    (Phase17Finite.frontier fixed Phase17Finite.selectedBefore).card + 2 ≤
      (Phase17Finite.frontier fixed observedAfter).card ∧
    Phase17Finite.protectedView observedAfter =
      Phase17Finite.protectedView Phase17Finite.selectedBefore :=
  guarded_two_step fixed contexts charges Phase17Finite.selectedBefore
    Phase17Finite.selectedCandidate secondCandidate Phase17Finite.selectedEvidence secondEvidence
    first_facts first_semantic_failure second_facts second_semantic_failure

theorem selected_frontiers :
    Phase17Finite.frontier fixed Phase17Finite.selectedBefore = Finset.range 21 ∧
    Phase17Finite.frontier fixed Phase17Finite.selectedAfter = Finset.range 22 ∧
    Phase17Finite.frontier fixed observedAfter = insert 41 (Finset.range 22) ∧
    (Phase17Finite.frontier fixed observedAfter).card = 23 := by
  exact ⟨by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel⟩

theorem selected_registry_counts :
    Phase17Finite.selectedBefore.programs.length = 8 ∧
    Phase17Finite.selectedAfter.programs.length = 9 ∧
    observedAfter.programs.length = 10 := by decide +kernel

theorem second_semantic_gain :
    ¬ (fixed.catalog 41).holds (Phase17Finite.taskObservation Phase17Finite.selectedAfter) ∧
    (fixed.catalog 41).holds (Phase17Finite.taskObservation observedAfter) :=
  accepted_semantic_gain fixed contexts charges Phase17Finite.selectedAfter secondCandidate
    secondEvidence second_accepted

theorem second_universal_program :
    Realizes 0 (-13) secondUpdate.program ∧
    ∀ entry ∈ Phase17Finite.selectedAfter.programs, ¬ Realizes 0 (-13) entry.2 :=
  accepted_affine_program fixed contexts charges Phase17Finite.selectedAfter secondCandidate
    secondEvidence 0 (-13) second_meaning.2.1 second_accepted

theorem second_protected_preservation :
    Phase17Finite.protectedView observedAfter =
      Phase17Finite.protectedView Phase17Finite.selectedAfter := by
  have typed := second_facts.typed
  change observedAfter = Phase17Finite.apply Phase17Finite.selectedAfter secondUpdate at typed
  rw [typed, Phase17Finite.protected_view_preserved]

theorem second_exact_recovery :
    Phase17Finite.recover secondUpdate observedAfter = Phase17Finite.selectedAfter := by
  have typed := second_facts.typed
  change observedAfter = Phase17Finite.apply Phase17Finite.selectedAfter secondUpdate at typed
  rw [typed]
  apply Phase17Finite.exact_recovery <;> decide +kernel

theorem selected_two_step_recovery :
    Phase17Finite.recover Phase17Finite.selectedUpdate
      (Phase17Finite.recover secondUpdate observedAfter) = Phase17Finite.selectedBefore := by
  rw [second_exact_recovery]
  exact Phase17Finite.selected_exact_recovery

theorem second_resource_totals :
    secondCharges.length = 39 ∧ Phase17Resource.counter secondCharges 0 = 1 ∧
    Phase17Resource.counter secondCharges 1 = 38 ∧
    Phase17Resource.counter secondCharges 2 = 152 ∧
    Phase17Resource.counter secondCharges 3 = 152 ∧
    Phase17Resource.totalCost secondCharges = 976 := by decide +kernel

theorem second_source_resources :
    secondEvidence.charges = secondCandidate.update.charges ∧
    secondEvidence.charges = charges Phase17Finite.selectedAfter ∧
    Phase17Resource.Fits fixed.policy secondEvidence.charges :=
  second_accepted.baseObligations.resourceValid

theorem selected_affine_availability :
    available Phase17Finite.selectedAfter = {259} ∧ available observedAfter = {41, 259} := by
  constructor <;> decide +kernel

end Phase17SecondStep
'''
    return text.encode('utf-8')


def render_positive(prepared: PreparedSecondStep) -> bytes:
    require(type(prepared) is PreparedSecondStep, 'exact prepared second-step input required')
    return ('import SelectedSecondStep\n' + '\n'.join('#print axioms ' + name for name in NAMES) + '\n').encode()


def render_negative(prepared: PreparedSecondStep, label: str) -> bytes:
    require(type(prepared) is PreparedSecondStep and label in NEGATIVES, 'exact second-step negative input required')
    prefix = '''import SelectedSecondStep
namespace Phase17SecondStepControl
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3 Phase17TaskInterpretation Phase17SecondStep
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
'''
    zero = '"' + '0' * 64 + '"'
    def checked(proposition: str, definitions: str) -> str:
        # These predicates intentionally have no global Decidable instances.
        # Supply the transparent finite instance without a classical decision.
        return '(@decide (' + proposition + ') (by unfold ' + definitions + '; infer_instance))'
    mutations = {
        'StaleParent': ('def wrongUpdate := { secondUpdate with parentPackage := ' + zero + ' }\n',
            checked('Phase17Finite.UpdateValid secondConfiguration Phase17Finite.selectedAfter wrongUpdate',
                    'Phase17Finite.UpdateValid')),
        'WrongContext': ('def wrongEvidence := { secondEvidence with contextHash := ' + zero + ' }\n',
            checked('Phase17Finite.trustValid secondConfiguration Phase17Finite.selectedAfter secondCandidate wrongEvidence',
                    'Phase17Finite.trustValid Phase17Provenance.ContextValid')),
        'MixedCandidate': ('def wrongEvidence := { secondEvidence with candidatePackage := ' + zero + ' }\n',
            checked('Phase17Finite.trustValid secondConfiguration Phase17Finite.selectedAfter secondCandidate wrongEvidence',
                    'Phase17Finite.trustValid Phase17Provenance.ContextValid')),
        'WrongRoot': ('def wrongEvidence := { secondEvidence with root := ' + zero + ' }\n',
            checked('Phase17Finite.trustValid secondConfiguration Phase17Finite.selectedAfter secondCandidate wrongEvidence',
                    'Phase17Finite.trustValid Phase17Provenance.ContextValid')),
        'SkippedProposal': ('def wrongProposal := { secondProposal with choices := [] }\n',
            checked('Phase17Provenance.CandidateMatches secondContext wrongProposal (Phase17Finite.candidateView secondCandidate)',
                    'Phase17Provenance.CandidateMatches Phase17Provenance.Produced Phase17Provenance.ContextValid')),
        'WrongProgram': ('def wrongProgram : Program := { secondUpdate.program with a := 0 }\n',
            '(fixed.catalog secondUpdate.task).check { proofs := Phase17Finite.selectedAfter.proofs, programs := Phase17Finite.selectedAfter.programs ++ [(secondUpdate.key, wrongProgram)] }'),
        'WrongTaskName': ('def wrongUpdate := { secondUpdate with taskName := "phase17ae.adapter.affine.0.20" }\n',
            checked('Phase17Finite.UpdateValid secondConfiguration Phase17Finite.selectedAfter wrongUpdate',
                    'Phase17Finite.UpdateValid')),
        'UnchangedFrontier': ('def wrongAfter := { observedAfter with declared := Phase17Finite.selectedAfter.declared, namedFrontier := Phase17Finite.selectedAfter.namedFrontier }\n',
            'decide ((Phase17Finite.frontier fixed Phase17Finite.selectedAfter).card < (Phase17Finite.frontier fixed wrongAfter).card)'),
        'ChangedProtected': ('def wrongAfter := { observedAfter with semantic := { observedAfter.semantic with goals := [] } }\n',
            'decide (wrongAfter.semantic = Phase17Finite.selectedAfter.semantic)'),
        'OmittedCharge': ('def wrongEvidence := { secondEvidence with charges := secondCharges.tail }\n',
            checked('Phase17Finite.resourceValid secondConfiguration secondCandidate wrongEvidence',
                    'Phase17Finite.resourceValid Phase17Resource.Fits')),
        'OverBudget': ('def excessCharges : List Phase17Resource.Kind := List.replicate (fixed.policy.costLimit / 64 + 1) .candidate\n',
            checked('Phase17Resource.Fits fixed.policy excessCharges', 'Phase17Resource.Fits')),
        'AlreadySolvedCredit': ('',
            '!((fixed.catalog 259).check (Phase17Finite.taskObservation Phase17Finite.selectedAfter))'),
    }
    definitions, assertion = mutations[label]
    text = prefix + definitions + 'def wrongClaim : Bool := ' + assertion + '\n'
    text += 'theorem actual_rejection : wrongClaim = false := by decide +kernel\n'
    text += 'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
    text += 'end Phase17SecondStepControl\n'
    return text.encode('utf-8')


def sources(prepared: PreparedSecondStep, root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedSecondStep, 'exact prepared second-step input required')
    result = {
        MODULES[0]: _read(root, MODULES[0]),
        MODULES[1]: _read(root, MODULES[1]),
        MODULES[2]: generic_finite_module(root),
        MODULES[3]: _read(root, MODULES[3]),
        MODULES[4]: _read(root, MODULES[4]),
        MODULES[5]: selected_finite_module(prepared, root),
        MODULES[6]: render_selected(prepared),
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
        require(match is not None, 'missing or reordered second-step audit: ' + name)
        axioms = [] if match[1] is None else [x.strip() for x in match[1].split(',') if x.strip()]
        require(len(axioms) == len(set(axioms)) and set(axioms) <= ALLOWED_AXIOMS,
                'unapproved second-step axiom')
        audits[name] = axioms
        cursor = match.end()
    require(cursor == len(stdout), 'unexpected second-step audit output')
    return audits


def negative_location(raw: bytes) -> tuple[int, int]:
    return inherited.negative_location(raw)


def validate_negative(label: str, raw: bytes, stdout: str, stderr: str, returncode: int) -> None:
    require(label in NEGATIVES and type(returncode) is int and returncode == 1 and not stderr,
            'negative control did not return intended compiler rejection')
    line, col = negative_location(raw)
    expected = re.compile(r'(?:[^\r\n]*[/\\])?' + re.escape(label) + r'\.lean:' + str(line) + ':' + str(col) +
        r': error: Tactic `decide` proved that the proposition\s+False\s+is false\s*')
    require(expected.fullmatch(stdout) is not None,
            'negative diagnostic is not exact intended False assertion')
