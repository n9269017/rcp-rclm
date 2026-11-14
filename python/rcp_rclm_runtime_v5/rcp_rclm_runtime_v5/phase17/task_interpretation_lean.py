"""Phase 17AE sources: fixed meanings, conservative extension, guarded acceptance.

Only the original finite transition is reconstructed. Arbitrary later source
contexts remain parameters; this renderer performs no follow-up selection.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from . import successor_context_lean as inherited
from .materialized import require, sha
from .task_interpretation import PreparedTaskInterpretation

BRIDGE = 'lean/phase17_bridge/TaskInterpretation.lean'
MODULES = ('ProposalProvenance', 'ControllerContinuation', 'FiniteObservationKernel',
           'SuccessorContext', 'TaskInterpretation', 'SelectedFiniteKernel')
POSITIVE = 'TaskInterpretationExamples'
NEGATIVES = ('LegacyMeaningChanged', 'LegacyNameChanged', 'WrongSlope', 'WrongOffset',
             'OutOfBoundsProgram', 'WrongFamily', 'MissingRegistryWitness',
             'AlreadySolvedCredit', 'RenamedProgramCredit', 'OutsidePalette')
LABELS = (POSITIVE, *NEGATIVES)
ALLOWED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}
GENERIC_BODIES = inherited.GENERIC_BODIES
PINS = {**inherited.PINS,
        'SuccessorContext': '741df11aed775b6c09c59364dd45364403aebe68baaea08e1f79b271812093fe'}
GENERIC_NAMES = tuple('Phase17TaskInterpretation.' + name for name in (
    'execute_adapter', 'normal_form_iff_realizes', 'two_probe_complete', 'affine_check_iff',
    'affine_behaviors_distinct', 'palette_index_injective', 'reference_bounded',
    'reference_realizes', 'reference_exists', 'affine_rename_invariant',
    'catalog_legacy_preserved', 'names_legacy_preserved', 'catalog_outside_rejected',
    'frontier_legacy_preserved', 'admissible_legacy_iff', 'facts_legacy_iff',
    'catalog_complete', 'base', 'learned', 'base_obligations_iff', 'learned_obligations_iff',
    'accepted_iff', 'accepted', 'already_solved_rejected', 'accepted_semantic_gain',
    'guarded_two_step',
))
SELECTED_NAMES = tuple('Phase17TaskInterpretationExamples.' + name for name in (
    'selected_legacy_complete', 'selected_catalog_complete', 'selected_names_distinct',
    'selected_old_frontiers', 'selected_rich_facts', 'selected_local_configuration',
    'selected_first_accepted', 'selected_before_availability', 'selected_after_availability',
    'selected_missing_contracts', 'selected_already_solved_undeclared',
    'selected_existing_behavior_rejected', 'selected_unavailable_witness', 'selected_fixed_catalog',
))
NAMES = GENERIC_NAMES + SELECTED_NAMES


def _read(root: Path, name: str) -> bytes:
    raw = inherited._read(root, name)
    if name in PINS:
        require(sha(raw) == PINS[name], 'inherited task-interpretation template changed: ' + name)
    return raw


_split_imports = inherited._split_imports
generic_finite_module = inherited.generic_finite_module
selected_finite_module = inherited.selected_finite_module


def _string(value: str) -> str:
    require(type(value) is str and re.fullmatch('[a-zA-Z0-9_.:-]*', value), 'ASCII literal required')
    return json.dumps(value)


def _common(prepared: PreparedTaskInterpretation) -> str:
    text = '''import SelectedFiniteKernel
import TaskInterpretation
namespace Phase17TaskInterpretationExamples
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3 Phase17TaskInterpretation
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000

def selectedFixed : Phase17Finite.Configuration :=
  extendConfiguration Phase17Finite.selectedConfiguration

-- Later providers are mathematical parameters. No later candidate is selected.
def selectedContexts (laterContexts : Contexts) (s : State) : Phase17Provenance.Context :=
  if s.packageHash = Phase17Finite.selectedBefore.packageHash then
    Phase17Finite.selectedConfiguration.context else laterContexts s

def selectedCharges (laterCharges : Charges) (s : State) : List Phase17Resource.Kind :=
  if s.packageHash = Phase17Finite.selectedBefore.packageHash then
    Phase17Finite.selectedConfiguration.expectedCharges else laterCharges s

def available (s : State) : Finset Nat :=
  (Finset.range 282).filter (fun t => 22 ≤ t ∧
    (selectedFixed.catalog t).check (Phase17Finite.taskObservation s) = true)

def missing : Finset Nat := (Finset.range 282).filter (fun t => 22 ≤ t ∧ t ≠ 259)
'''
    for target, source in (('catalogDigest', 'catalog_sha256'),
                           ('descriptorDigest', 'descriptor_sha256'),
                           ('paletteDigest', 'tail_sha256')):
        text += 'def ' + target + ' : String := ' + _string(prepared.packet['catalog'][source]) + '\n'
    return text


def render_positive(prepared: PreparedTaskInterpretation) -> bytes:
    text = _common(prepared)
    text += '''
theorem selected_legacy_complete (task : Nat) (bound : task < 22) (s : Observation) :
    (Phase17TaskMeaning.catalog task).check s = true ↔
      (Phase17TaskMeaning.catalog task).holds s := by
  interval_cases task <;>
    simp only [Phase17TaskMeaning.catalog, theorem_meaning_complete, vector_meaning_complete]

theorem selected_catalog_complete (task : Nat) (s : Observation) :
    (selectedFixed.catalog task).check s = true ↔ (selectedFixed.catalog task).holds s :=
  catalog_complete Phase17TaskMeaning.catalog selected_legacy_complete task s

private def nameIndex (s : String) : Nat :=
  match s.toList with
  | 'p' :: 'h' :: 'a' :: 's' :: 'e' :: '1' :: '7' :: 'a' :: 'e' :: '.' ::
      'a' :: 'd' :: 'a' :: 'p' :: 't' :: 'e' :: 'r' :: '.' ::
      'a' :: 'f' :: 'f' :: 'i' :: 'n' :: 'e' :: '.' :: v :: '.' :: digits =>
      22 + 65 * (v.toNat - 48) + digits.foldl (fun n c => 10 * n + (c.toNat - 48)) 0
  | _ => Phase17TaskMeaning.taskIds.idxOf s

private theorem selected_name_roundtrip :
    (List.range 282).map (fun n => nameIndex (selectedFixed.taskName n)) = List.range 282 := by
  decide +kernel

theorem selected_names_distinct :
    ((List.range 282).map selectedFixed.taskName).Nodup := by
  apply List.Nodup.of_map nameIndex
  rw [List.map_map]
  change ((List.range 282).map (fun n => nameIndex (selectedFixed.taskName n))).Nodup
  rw [selected_name_roundtrip]
  exact List.nodup_range

theorem selected_old_frontiers :
    Phase17Finite.frontier selectedFixed Phase17Finite.selectedBefore = Finset.range 21 ∧
    Phase17Finite.frontier selectedFixed Phase17Finite.selectedAfter = Finset.range 22 := by
  constructor <;> decide +kernel

theorem selected_rich_facts :
    Phase17Finite.Facts selectedFixed Phase17Finite.selectedBefore
      Phase17Finite.selectedCandidate Phase17Finite.selectedEvidence := by
  apply (facts_legacy_iff Phase17Finite.selectedConfiguration
    Phase17Finite.selectedBefore Phase17Finite.selectedCandidate Phase17Finite.selectedEvidence
    (by decide +kernel) (by decide +kernel) (by decide +kernel)).mpr
  exact Phase17Finite.selected_facts

theorem selected_local_configuration (laterContexts : Contexts) (laterCharges : Charges) :
    Phase17SuccessorContext.configurationAt selectedFixed
      (selectedContexts laterContexts) (selectedCharges laterCharges) Phase17Finite.selectedBefore =
        selectedFixed := by
  simp [Phase17SuccessorContext.configurationAt, selectedContexts, selectedCharges,
    selectedFixed, extendConfiguration]

theorem selected_first_accepted (laterContexts : Contexts) (laterCharges : Charges) :
    Learned.LearnedAcceptedStep
      (learned selectedFixed (selectedContexts laterContexts) (selectedCharges laterCharges))
      Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
      (packet selectedFixed (selectedContexts laterContexts) (selectedCharges laterCharges)
        Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) := by
  apply accepted
  · rw [selected_local_configuration]
    exact selected_rich_facts
  · change ¬ (selectedFixed.catalog 21).holds
      (Phase17Finite.taskObservation Phase17Finite.selectedBefore)
    intro solved
    have checked := (selected_catalog_complete 21 _).mpr solved
    have rejected : (selectedFixed.catalog 21).check
        (Phase17Finite.taskObservation Phase17Finite.selectedBefore) = false := by decide +kernel
    rw [rejected] at checked
    cases checked

theorem selected_before_availability : available Phase17Finite.selectedBefore = {259} := by
  decide +kernel

theorem selected_after_availability : available Phase17Finite.selectedAfter = {259} := by
  decide +kernel

private theorem missing_at (s : State) (exactAvailable : available s = {259})
    (task : Nat) (member : task ∈ missing) :
    ¬ (selectedFixed.catalog task).holds (Phase17Finite.taskObservation s) := by
  intro solved
  have checked := (selected_catalog_complete task _).mpr solved
  have facts := Finset.mem_filter.mp member
  have found : task ∈ available s := Finset.mem_filter.mpr
    ⟨facts.1, facts.2.1, checked⟩
  rw [exactAvailable] at found
  exact facts.2.2 (Finset.mem_singleton.mp found)

theorem selected_missing_contracts : missing.card = 259 ∧
    ∀ task ∈ missing,
      ¬ (selectedFixed.catalog task).holds
        (Phase17Finite.taskObservation Phase17Finite.selectedBefore) ∧
      ¬ (selectedFixed.catalog task).holds
        (Phase17Finite.taskObservation Phase17Finite.selectedAfter) := by
  refine ⟨by decide +kernel, ?_⟩
  intro task member
  exact ⟨missing_at _ selected_before_availability task member,
    missing_at _ selected_after_availability task member⟩

theorem selected_already_solved_undeclared :
    (selectedFixed.catalog 259).holds
      (Phase17Finite.taskObservation Phase17Finite.selectedBefore) ∧
    (selectedFixed.catalog 259).holds
      (Phase17Finite.taskObservation Phase17Finite.selectedAfter) ∧
    259 ∉ Phase17Finite.selectedBefore.declared ∧
    259 ∉ Phase17Finite.selectedAfter.declared := by
  exact ⟨(selected_catalog_complete 259 _).mp (by decide +kernel),
    (selected_catalog_complete 259 _).mp (by decide +kernel),
    by decide +kernel, by decide +kernel⟩

theorem selected_existing_behavior_rejected (contexts : Contexts) (charges : Charges)
    (c : Candidate) (e : Evidence) (task : c.update.task = 259) :
    ¬ Learned.LearnedAcceptedStep (learned selectedFixed contexts charges)
      Phase17Finite.selectedAfter c
      (packet selectedFixed contexts charges Phase17Finite.selectedAfter e) := by
  intro h
  have meaning : selectedFixed.catalog c.update.task = affineMeaning 3 10 := by
    rw [task]
    rfl
  have novel := accepted_affine_program selectedFixed contexts charges
    Phase17Finite.selectedAfter c e 3 10 meaning h
  have old := selected_already_solved_undeclared.2.1
  change ∃ entry ∈ Phase17Finite.selectedAfter.programs, Realizes 3 10 entry.2 at old
  rcases old with ⟨entry, member, real⟩
  exact novel.2 entry member real

theorem selected_unavailable_witness :
    ∃ p : Program, BoundedAdapter p ∧
      (selectedFixed.catalog 22).holds
        { proofs := [], programs := [("semantic-reference", p)] } ∧
      ¬ (selectedFixed.catalog 22).holds
        (Phase17Finite.taskObservation Phase17Finite.selectedAfter) := by
  rcases reference_exists 0 (by decide) with ⟨p, bounded, real⟩
  exact ⟨p, bounded, real,
    (selected_missing_contracts.2 22 (by decide +kernel)).2⟩

theorem selected_fixed_catalog (contexts : Contexts) (charges : Charges) (s : State) :
    (Phase17SuccessorContext.configurationAt selectedFixed contexts charges s).root =
      selectedFixed.root ∧
    (Phase17SuccessorContext.configurationAt selectedFixed contexts charges s).catalog =
      selectedFixed.catalog ∧
    (Phase17SuccessorContext.configurationAt selectedFixed contexts charges s).taskName =
      selectedFixed.taskName ∧
    (Phase17SuccessorContext.configurationAt selectedFixed contexts charges s).contract =
      selectedFixed.contract ∧
    (Phase17SuccessorContext.configurationAt selectedFixed contexts charges s).policy =
      selectedFixed.policy :=
  Phase17SuccessorContext.configuration_semantics_fixed selectedFixed contexts charges s

end Phase17TaskInterpretationExamples
'''
    text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    return text.encode('utf-8')


def render_negative(prepared: PreparedTaskInterpretation, label: str) -> bytes:
    require(label in NEGATIVES, 'unknown task-interpretation negative')
    before = '(Phase17Finite.taskObservation Phase17Finite.selectedBefore)'
    after = '(Phase17Finite.taskObservation Phase17Finite.selectedAfter)'
    assertions = {
        'LegacyMeaningChanged': '(selectedFixed.catalog 21).check ' + before,
        'LegacyNameChanged': 'decide (selectedFixed.taskName 0 = "phase17ae.adapter.affine.0.0")',
        'WrongSlope': '(affineMeaning 0 10).check ' + after,
        'WrongOffset': '(affineMeaning 3 11).check ' + after,
        'OutOfBoundsProgram': '(affineMeaning 3 10).check { proofs := [], programs := [("out-of-bounds", ⟨0, 3, 17, 7⟩)] }',
        'WrongFamily': '(affineMeaning 0 10).check { proofs := [], programs := [("coincident-function", ⟨1, 2, 0, 10⟩)] }',
        'MissingRegistryWitness': '(affineMeaning 3 10).check { proofs := [], programs := [] }',
        'AlreadySolvedCredit': '!((selectedFixed.catalog 259).check ' + after + ')',
        'RenamedProgramCredit': '!((affineMeaning 3 10).check { proofs := [], programs := Phase17Finite.selectedAfter.programs.map (fun e => ("renamed", e.2)) })',
        'OutsidePalette': '(selectedFixed.catalog 282).check ' + after,
    }
    text = _common(prepared) + 'def wrongClaim : Bool := ' + assertions[label] + '\n'
    text += 'theorem actual_rejection : wrongClaim = false := by decide +kernel\n'
    text += 'example : wrongClaim = true := by\n  simp only [actual_rejection, Bool.false_eq_true]\n  decide\n'
    text += 'end Phase17TaskInterpretationExamples\n'
    return text.encode('utf-8')


def sources(prepared: PreparedTaskInterpretation, root: Path) -> dict[str, bytes]:
    require(type(prepared) is PreparedTaskInterpretation, 'exact task-interpretation input required')
    result = {
        MODULES[0]: _read(root, MODULES[0]),
        MODULES[1]: _read(root, MODULES[1]),
        MODULES[2]: generic_finite_module(root),
        MODULES[3]: _read(root, MODULES[3]),
        MODULES[4]: _read(root, MODULES[4]),
        MODULES[5]: selected_finite_module(prepared, root),
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
        require(match is not None, 'missing or reordered task-interpretation audit: ' + name)
        axioms = [] if match[1] is None else [x.strip() for x in match[1].split(',') if x.strip()]
        require(len(axioms) == len(set(axioms)) and set(axioms) <= ALLOWED_AXIOMS,
                'unapproved task-interpretation axiom')
        audits[name] = axioms
        cursor = match.end()
    require(cursor == len(stdout), 'unexpected task-interpretation audit output')
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
