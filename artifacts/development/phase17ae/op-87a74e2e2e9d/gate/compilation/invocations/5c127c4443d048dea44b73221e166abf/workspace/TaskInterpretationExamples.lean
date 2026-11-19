import SelectedFiniteKernel
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
def catalogDigest : String := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
def descriptorDigest : String := "25c0498782cadd5338a470c31a9247e3176ae4a74bd7ac35ac9b71fcb1c681de"
def paletteDigest : String := "6a2d373bc339c83966c0d5a7302729190d14fc0ce62c4922af04eabb56929656"

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
#print axioms Phase17TaskInterpretation.execute_adapter
#print axioms Phase17TaskInterpretation.normal_form_iff_realizes
#print axioms Phase17TaskInterpretation.two_probe_complete
#print axioms Phase17TaskInterpretation.affine_check_iff
#print axioms Phase17TaskInterpretation.affine_behaviors_distinct
#print axioms Phase17TaskInterpretation.palette_index_injective
#print axioms Phase17TaskInterpretation.reference_bounded
#print axioms Phase17TaskInterpretation.reference_realizes
#print axioms Phase17TaskInterpretation.reference_exists
#print axioms Phase17TaskInterpretation.affine_rename_invariant
#print axioms Phase17TaskInterpretation.catalog_legacy_preserved
#print axioms Phase17TaskInterpretation.names_legacy_preserved
#print axioms Phase17TaskInterpretation.catalog_outside_rejected
#print axioms Phase17TaskInterpretation.frontier_legacy_preserved
#print axioms Phase17TaskInterpretation.admissible_legacy_iff
#print axioms Phase17TaskInterpretation.facts_legacy_iff
#print axioms Phase17TaskInterpretation.catalog_complete
#print axioms Phase17TaskInterpretation.base
#print axioms Phase17TaskInterpretation.learned
#print axioms Phase17TaskInterpretation.base_obligations_iff
#print axioms Phase17TaskInterpretation.learned_obligations_iff
#print axioms Phase17TaskInterpretation.accepted_iff
#print axioms Phase17TaskInterpretation.accepted
#print axioms Phase17TaskInterpretation.already_solved_rejected
#print axioms Phase17TaskInterpretation.accepted_semantic_gain
#print axioms Phase17TaskInterpretation.guarded_two_step
#print axioms Phase17TaskInterpretationExamples.selected_legacy_complete
#print axioms Phase17TaskInterpretationExamples.selected_catalog_complete
#print axioms Phase17TaskInterpretationExamples.selected_names_distinct
#print axioms Phase17TaskInterpretationExamples.selected_old_frontiers
#print axioms Phase17TaskInterpretationExamples.selected_rich_facts
#print axioms Phase17TaskInterpretationExamples.selected_local_configuration
#print axioms Phase17TaskInterpretationExamples.selected_first_accepted
#print axioms Phase17TaskInterpretationExamples.selected_before_availability
#print axioms Phase17TaskInterpretationExamples.selected_after_availability
#print axioms Phase17TaskInterpretationExamples.selected_missing_contracts
#print axioms Phase17TaskInterpretationExamples.selected_already_solved_undeclared
#print axioms Phase17TaskInterpretationExamples.selected_existing_behavior_rejected
#print axioms Phase17TaskInterpretationExamples.selected_unavailable_witness
#print axioms Phase17TaskInterpretationExamples.selected_fixed_catalog
