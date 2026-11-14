import SuccessorContext

/-
Phase 17AE fixes a conservative extension of the established interpretation.
The 260 added meanings are universal affine contracts for bounded adapter-family
programs over four integer inputs. They are neither hash labels nor success
bits. Two separating probes characterize the entire affine behavior in this
declared grammar. Reference programs establish syntax realizability only;
production search coverage and a second accepted transition remain unproved.

The actual state-indexed kernel strengthens reality containment with semantic
failure at the source. Thus declaring an already available contract cannot
manufacture capability gain. All original eleven base and twelve learned
obligations remain necessary. The root, interpretation, contract and resource
policy are fixed independently of any later candidate selection.
-/
namespace Phase17TaskInterpretation

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

abbrev Program := Phase17TaskMeaning.Program
abbrev Observation := Phase17TaskMeaning.ObservationState
abbrev State := Phase17Finite.State
abbrev Candidate := Phase17SuccessorContext.Candidate
abbrev Evidence := Phase17Finite.Evidence
abbrev Contexts := Phase17SuccessorContext.Contexts
abbrev Charges := Phase17SuccessorContext.Charges

def target (variant : Nat) (offset : Int) (xs : List Int) : List Int :=
  xs.map (fun z => Int.ofNat (variant + 1) * z + offset)

def zeroProbe : List Int := [0, 0, 0, 0]
def unitProbe : List Int := [1, 0, 0, 0]

def BoundedAdapter (p : Program) : Prop :=
  p.family = 0 ∧ p.variant < 4 ∧
    -16 ≤ p.a ∧ p.a ≤ 16 ∧ -16 ≤ p.b ∧ p.b ≤ 16

instance (p : Program) : Decidable (BoundedAdapter p) := by
  unfold BoundedAdapter
  infer_instance

def NormalForm (variant : Nat) (offset : Int) (p : Program) : Prop :=
  BoundedAdapter p ∧ p.variant = variant ∧ p.a - p.b = offset

instance (variant : Nat) (offset : Int) (p : Program) :
    Decidable (NormalForm variant offset p) := by
  unfold NormalForm
  infer_instance

/-- Universal four-input meaning, qualified by the adapter family and the
    unchanged bounded coefficient syntax. Other families are outside this
    contract even when a particular function happens to coincide. -/
def Realizes (variant : Nat) (offset : Int) (p : Program) : Prop :=
  BoundedAdapter p ∧ ∀ x0 x1 x2 x3 : Int,
    Phase17TaskMeaning.execute p [x0, x1, x2, x3] =
      target variant offset [x0, x1, x2, x3]

theorem execute_adapter (p : Program) (family : p.family = 0) (xs : List Int) :
    Phase17TaskMeaning.execute p xs = target p.variant (p.a - p.b) xs := by
  simp only [Phase17TaskMeaning.execute, family, target]
  congr 1
  funext z
  ring

private theorem probe_identifies (p : Program) (variant : Nat) (offset : Int)
    (family : p.family = 0)
    (zero : Phase17TaskMeaning.execute p zeroProbe = target variant offset zeroProbe)
    (unit : Phase17TaskMeaning.execute p unitProbe = target variant offset unitProbe) :
    p.variant = variant ∧ p.a - p.b = offset := by
  rw [execute_adapter p family] at zero unit
  have z := congrArg (fun xs : List Int => xs.getD 0 0) zero
  have u := congrArg (fun xs : List Int => xs.getD 0 0) unit
  simp [target, zeroProbe, unitProbe] at z u
  have v : p.variant = variant := by omega
  exact ⟨v, z⟩

theorem normal_form_iff_realizes (variant : Nat) (offset : Int) (p : Program) :
    NormalForm variant offset p ↔ Realizes variant offset p := by
  constructor
  · rintro ⟨bounded, v, d⟩
    refine ⟨bounded, ?_⟩
    intro x0 x1 x2 x3
    rw [execute_adapter p bounded.1, v, d]
  · rintro ⟨bounded, run⟩
    exact ⟨bounded, probe_identifies p variant offset bounded.1
      (run 0 0 0 0) (run 1 0 0 0)⟩

/-- Within the declared syntax these two probes characterize the universal
    contract; no finite-test extrapolation is assumed. -/
theorem two_probe_complete (variant : Nat) (offset : Int) (p : Program) :
    (BoundedAdapter p ∧
      Phase17TaskMeaning.execute p zeroProbe = target variant offset zeroProbe ∧
      Phase17TaskMeaning.execute p unitProbe = target variant offset unitProbe) ↔
        Realizes variant offset p := by
  rw [← normal_form_iff_realizes]
  constructor
  · rintro ⟨bounded, zero, unit⟩
    exact ⟨bounded, probe_identifies p variant offset bounded.1 zero unit⟩
  · intro h
    have run := (normal_form_iff_realizes variant offset p).mp h
    exact ⟨run.1, run.2 0 0 0 0, run.2 1 0 0 0⟩

def affineMeaning (variant : Nat) (offset : Int) : Phase17TaskMeaning.Meaning where
  check := fun s => s.programs.any (fun e => decide (NormalForm variant offset e.2))
  holds := fun s => ∃ e ∈ s.programs, Realizes variant offset e.2
  sound := by
    intro s h
    simp only [List.any_eq_true, decide_eq_true_eq] at h
    rcases h with ⟨e, member, normal⟩
    exact ⟨e, member, (normal_form_iff_realizes variant offset e.2).mp normal⟩

theorem affine_check_iff (variant : Nat) (offset : Int) (s : Observation) :
    (affineMeaning variant offset).check s = true ↔
      (affineMeaning variant offset).holds s := by
  change (s.programs.any (fun e => decide (NormalForm variant offset e.2)) = true) ↔
    ∃ e ∈ s.programs, Realizes variant offset e.2
  simp only [List.any_eq_true, decide_eq_true_eq, normal_form_iff_realizes]

theorem affine_behaviors_distinct (v w : Nat) (d e : Int)
    (same : ∀ x0 x1 x2 x3 : Int,
      target v d [x0, x1, x2, x3] = target w e [x0, x1, x2, x3]) :
    v = w ∧ d = e := by
  have zero := congrArg (fun xs : List Int => xs.getD 0 0) (same 0 0 0 0)
  have unit := congrArg (fun xs : List Int => xs.getD 0 0) (same 1 0 0 0)
  simp [target] at zero unit
  exact ⟨by omega, zero⟩

def paletteVariant (n : Nat) : Nat := n / 65
def paletteOffset (n : Nat) : Int := Int.ofNat (n % 65) - 32

theorem palette_index_injective (i j : Nat)
    (same : ∀ x0 x1 x2 x3 : Int,
      target (paletteVariant i) (paletteOffset i) [x0, x1, x2, x3] =
      target (paletteVariant j) (paletteOffset j) [x0, x1, x2, x3]) : i = j := by
  have pair := affine_behaviors_distinct _ _ _ _ same
  simp only [paletteVariant, paletteOffset, Int.ofNat_eq_natCast] at pair
  omega

def referenceProgram (n : Nat) : Program :=
  let offset := paletteOffset n
  let a := if offset < -16 then -16 else if 16 < offset then 16 else offset
  { family := 0, variant := paletteVariant n, a := a, b := a - offset }

theorem reference_bounded (n : Nat) (bound : n < 260) :
    BoundedAdapter (referenceProgram n) := by
  have rem := Nat.mod_lt n (by decide : 0 < 65)
  have vr : paletteVariant n < 4 := by unfold paletteVariant; omega
  have lo : -32 ≤ paletteOffset n := by
    simp only [paletteOffset, Int.ofNat_eq_natCast]
    omega
  have hi : paletteOffset n ≤ 32 := by
    simp only [paletteOffset, Int.ofNat_eq_natCast]
    omega
  unfold BoundedAdapter referenceProgram
  dsimp only
  split_ifs <;> exact ⟨rfl, vr, by omega, by omega, by omega, by omega⟩

theorem reference_realizes (n : Nat) (bound : n < 260) :
    Realizes (paletteVariant n) (paletteOffset n) (referenceProgram n) := by
  apply (normal_form_iff_realizes _ _ _).mp
  refine ⟨reference_bounded n bound, rfl, ?_⟩
  simp only [referenceProgram]
  omega

theorem reference_exists (n : Nat) (bound : n < 260) :
    ∃ p : Program, BoundedAdapter p ∧
      (affineMeaning (paletteVariant n) (paletteOffset n)).holds
        { proofs := [], programs := [("semantic-reference", p)] } := by
  refine ⟨referenceProgram n, reference_bounded n bound, ?_⟩
  exact ⟨("semantic-reference", referenceProgram n), by simp, reference_realizes n bound⟩

/-- Program names play no role in new affine meanings. Renaming a registered
    implementation cannot create a missing affine behavior. -/
theorem affine_rename_invariant (v : Nat) (d : Int) (s : Observation)
    (rename : String → String) :
    (affineMeaning v d).holds
      { s with programs := s.programs.map (fun e => (rename e.1, e.2)) } ↔
        (affineMeaning v d).holds s := by
  change (∃ e ∈ s.programs.map (fun e => (rename e.1, e.2)), Realizes v d e.2) ↔
    ∃ e ∈ s.programs, Realizes v d e.2
  simp only [List.mem_map]
  constructor
  · rintro ⟨e, ⟨old, member, rfl⟩, real⟩
    exact ⟨old, member, real⟩
  · rintro ⟨e, member, real⟩
    exact ⟨(rename e.1, e.2), ⟨e, member, rfl⟩, real⟩

def extendedCatalog (legacy : Nat → Phase17TaskMeaning.Meaning) (task : Nat) :
    Phase17TaskMeaning.Meaning :=
  if task < 22 then legacy task else if task < 282 then
    affineMeaning (paletteVariant (task - 22)) (paletteOffset (task - 22))
  else Phase17TaskMeaning.rejectMeaning

def extendedName (legacy : Nat → String) (task : Nat) : String :=
  if task < 22 then legacy task else if task < 282 then
    "phase17ae.adapter.affine." ++ toString ((task - 22) / 65) ++ "." ++
      toString ((task - 22) % 65)
  else ""

def extendConfiguration (cfg : Phase17Finite.Configuration) : Phase17Finite.Configuration :=
  { cfg with catalog := extendedCatalog cfg.catalog, taskName := extendedName cfg.taskName }

theorem catalog_legacy_preserved (legacy : Nat → Phase17TaskMeaning.Meaning)
    (task : Nat) (bound : task < 22) : extendedCatalog legacy task = legacy task := by
  simp only [extendedCatalog, if_pos bound]

theorem names_legacy_preserved (legacy : Nat → String)
    (task : Nat) (bound : task < 22) : extendedName legacy task = legacy task := by
  simp only [extendedName, if_pos bound]

theorem catalog_outside_rejected (legacy : Nat → Phase17TaskMeaning.Meaning)
    (task : Nat) (bound : 282 ≤ task) :
    extendedCatalog legacy task = Phase17TaskMeaning.rejectMeaning := by
  simp only [extendedCatalog, if_neg (show ¬ task < 22 by omega), if_neg (by omega : ¬ task < 282)]

theorem frontier_legacy_preserved (cfg : Phase17Finite.Configuration) (s : State)
    (bound : s.declared ⊆ Finset.range 22) :
    Phase17Finite.frontier (extendConfiguration cfg) s = Phase17Finite.frontier cfg s := by
  apply Finset.filter_congr
  intro task member
  have small := Finset.mem_range.mp (bound member)
  rw [show (extendConfiguration cfg).catalog task = cfg.catalog task from
    catalog_legacy_preserved cfg.catalog task small]

private theorem names_image_preserved (cfg : Phase17Finite.Configuration) (s : State)
    (bound : s.declared ⊆ Finset.range 22) :
    s.declared.image (extendConfiguration cfg).taskName = s.declared.image cfg.taskName := by
  apply Finset.image_congr
  intro task member
  exact names_legacy_preserved cfg.taskName task (Finset.mem_range.mp (bound member))

theorem admissible_legacy_iff (cfg : Phase17Finite.Configuration) (s : State)
    (bound : s.declared ⊆ Finset.range 22) :
    Phase17Finite.admissible (extendConfiguration cfg) s ↔ Phase17Finite.admissible cfg s := by
  unfold Phase17Finite.admissible
  rw [frontier_legacy_preserved cfg s bound, names_image_preserved cfg s bound]
  rfl

private theorem update_legacy_iff (cfg : Phase17Finite.Configuration) (s : State)
    (u : Phase17Finite.Update) (bound : u.task < 22) :
    Phase17Finite.UpdateValid (extendConfiguration cfg) s u ↔
      Phase17Finite.UpdateValid cfg s u := by
  unfold Phase17Finite.UpdateValid
  rw [show (extendConfiguration cfg).taskName u.task = cfg.taskName u.task from
    names_legacy_preserved cfg.taskName u.task bound]
  rfl

/-- Original finite facts transport without weakening, when all declarations
    remain in the preserved legacy range. -/
theorem facts_legacy_iff (cfg : Phase17Finite.Configuration) (s : State) (c : Candidate)
    (e : Evidence) (before : s.declared ⊆ Finset.range 22)
    (after : c.next.declared ⊆ Finset.range 22) (task : c.update.task < 22) :
    Phase17Finite.Facts (extendConfiguration cfg) s c e ↔ Phase17Finite.Facts cfg s c e := by
  constructor
  · intro h
    exact {
      beforeAdmissible := (admissible_legacy_iff cfg s before).mp h.beforeAdmissible
      afterAdmissible := (admissible_legacy_iff cfg c.next after).mp h.afterAdmissible
      typed := h.typed
      updateValid := (update_legacy_iff cfg s c.update task).mp h.updateValid
      trusted := h.trusted
      resources := h.resources
      matched := h.matched
      expansion := by simpa only [frontier_legacy_preserved cfg s before,
        frontier_legacy_preserved cfg c.next after] using h.expansion }
  · intro h
    exact {
      beforeAdmissible := (admissible_legacy_iff cfg s before).mpr h.beforeAdmissible
      afterAdmissible := (admissible_legacy_iff cfg c.next after).mpr h.afterAdmissible
      typed := h.typed
      updateValid := (update_legacy_iff cfg s c.update task).mpr h.updateValid
      trusted := h.trusted
      resources := h.resources
      matched := h.matched
      expansion := by simpa only [frontier_legacy_preserved cfg s before,
        frontier_legacy_preserved cfg c.next after] using h.expansion }

theorem theorem_meaning_complete (task source decode : String) (P : Prop) (proof : P)
    (s : Observation) :
    (Phase17TaskMeaning.theoremMeaning task source decode P proof).check s = true ↔
      (Phase17TaskMeaning.theoremMeaning task source decode P proof).holds s := by
  simp only [Phase17TaskMeaning.theoremMeaning, decide_eq_true_eq]
  exact ⟨fun h => ⟨h, proof⟩, And.left⟩

theorem vector_meaning_complete (contract : Phase17TaskMeaning.VectorContract) (s : Observation) :
    (Phase17TaskMeaning.vectorMeaning contract).check s = true ↔
      (Phase17TaskMeaning.vectorMeaning contract).holds s := by
  simp only [Phase17TaskMeaning.vectorMeaning, List.any_eq_true, decide_eq_true_eq]

theorem catalog_complete (legacy : Nat → Phase17TaskMeaning.Meaning)
    (complete : ∀ task, task < 22 → ∀ s,
      (legacy task).check s = true ↔ (legacy task).holds s)
    (task : Nat) (s : Observation) :
    (extendedCatalog legacy task).check s = true ↔ (extendedCatalog legacy task).holds s := by
  unfold extendedCatalog
  split_ifs with old tail
  · exact complete task old s
  · exact affine_check_iff _ _ s
  · simp [Phase17TaskMeaning.rejectMeaning]

def SemanticFailure (fixed : Phase17Finite.Configuration) (s : State) (c : Candidate) : Prop :=
  ¬ (fixed.catalog c.update.task).holds (Phase17Finite.taskObservation s)

/-- Semantic novelty is an actual base-kernel condition. The preexisting
    non-universality witness still refutes the stronger predicate. -/
noncomputable def base (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) :
    RCP.Kernel State Phase17Finite.Update Evidence Phase17Finite.Protected Phase17Finite.ResidualIndex :=
  { Phase17SuccessorContext.base fixed contexts charges with
    realityContained := fun s c e =>
      (Phase17SuccessorContext.base fixed contexts charges).realityContained s c e ∧
        SemanticFailure fixed s c
    realityContained_not_universal := by
      rcases (Phase17SuccessorContext.base fixed contexts charges).realityContained_not_universal with
        ⟨s, c, e, rejected⟩
      exact ⟨s, c, e, fun h => rejected h.1⟩ }

noncomputable def learned (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) :
    Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String)
      (base fixed contexts charges) where
  frontier := (Phase17SuccessorContext.learned fixed contexts charges).frontier
  solves := (Phase17SuccessorContext.learned fixed contexts charges).solves
  frontierSound := (Phase17SuccessorContext.learned fixed contexts charges).frontierSound
  activeGenerator := (Phase17SuccessorContext.learned fixed contexts charges).activeGenerator
  activePackageHash := (Phase17SuccessorContext.learned fixed contexts charges).activePackageHash
  generatorBound := (Phase17SuccessorContext.learned fixed contexts charges).generatorBound
  proposalProducedBy := (Phase17SuccessorContext.learned fixed contexts charges).proposalProducedBy
  proposalBindsCandidate := (Phase17SuccessorContext.learned fixed contexts charges).proposalBindsCandidate
  packageHashBound := (Phase17SuccessorContext.learned fixed contexts charges).packageHashBound
  goalDrift := (Phase17SuccessorContext.learned fixed contexts charges).goalDrift
  goalDriftBudget := (Phase17SuccessorContext.learned fixed contexts charges).goalDriftBudget
  resourceUsed := (Phase17SuccessorContext.learned fixed contexts charges).resourceUsed
  resourceBudget := (Phase17SuccessorContext.learned fixed contexts charges).resourceBudget
  informationValue := (Phase17SuccessorContext.learned fixed contexts charges).informationValue
  informationBudget := (Phase17SuccessorContext.learned fixed contexts charges).informationBudget
  informationBudget_nonnegative :=
    (Phase17SuccessorContext.learned fixed contexts charges).informationBudget_nonnegative

abbrev packet := Phase17SuccessorContext.packet

/-- All eleven preexisting base obligations are retained, plus semantic failure. -/
theorem base_obligations_iff (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence) :
    RCP.StepObligations (base fixed contexts charges) s c e ↔
      RCP.StepObligations (Phase17SuccessorContext.base fixed contexts charges) s c e ∧
        SemanticFailure fixed s c := by
  constructor
  · intro h
    exact ⟨{
      typedSuccessor := h.typedSuccessor
      residualsNonpositive := h.residualsNonpositive
      protectedNonLoss := h.protectedNonLoss
      constructiveRecovery := h.constructiveRecovery
      invariantPreserved := h.invariantPreserved
      progressNondecreasing := h.progressNondecreasing
      strictProgressWhenWitness := h.strictProgressWhenWitness
      trustValid := h.trustValid
      resourceValid := h.resourceValid
      realityContained := h.realityContained.1
      successorAdmissible := h.successorAdmissible }, h.realityContained.2⟩
  · rintro ⟨h, failure⟩
    exact {
      typedSuccessor := h.typedSuccessor
      residualsNonpositive := h.residualsNonpositive
      protectedNonLoss := h.protectedNonLoss
      constructiveRecovery := h.constructiveRecovery
      invariantPreserved := h.invariantPreserved
      progressNondecreasing := h.progressNondecreasing
      strictProgressWhenWitness := h.strictProgressWhenWitness
      trustValid := h.trustValid
      resourceValid := h.resourceValid
      realityContained := ⟨h.realityContained, failure⟩
      successorAdmissible := h.successorAdmissible }

/-- All twelve learned obligations are unchanged. -/
theorem learned_obligations_iff (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence) :
    Learned.SpecificObligations (learned fixed contexts charges) s c
      (packet fixed contexts charges s e) ↔
      Learned.SpecificObligations (Phase17SuccessorContext.learned fixed contexts charges) s c
        (packet fixed contexts charges s e) := by
  constructor <;> intro h <;> exact {
    protectedFrontierCertified := h.protectedFrontierCertified
    protectedFrontierRetained := h.protectedFrontierRetained
    strictFrontierExpansion := h.strictFrontierExpansion
    generatorIsActive := h.generatorIsActive
    generatorBound := h.generatorBound
    proposalProduced := h.proposalProduced
    proposalBindsCandidate := h.proposalBindsCandidate
    packageHashIsActive := h.packageHashIsActive
    packageHashBound := h.packageHashBound
    goalDriftWithinBudget := h.goalDriftWithinBudget
    resourceWithinBudget := h.resourceWithinBudget
    informationNonRegression := h.informationNonRegression }

theorem accepted_iff (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence) :
    Learned.LearnedAcceptedStep (learned fixed contexts charges) s c
      (packet fixed contexts charges s e) ↔
      Learned.LearnedAcceptedStep (Phase17SuccessorContext.learned fixed contexts charges) s c
        (packet fixed contexts charges s e) ∧ SemanticFailure fixed s c := by
  constructor
  · intro h
    have b := (base_obligations_iff fixed contexts charges s c e).mp h.baseObligations
    exact ⟨⟨b.1, (learned_obligations_iff fixed contexts charges s c e).mp h.learnedObligations⟩, b.2⟩
  · rintro ⟨h, failure⟩
    exact ⟨(base_obligations_iff fixed contexts charges s c e).mpr ⟨h.baseObligations, failure⟩,
      (learned_obligations_iff fixed contexts charges s c e).mpr h.learnedObligations⟩

theorem accepted (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence)
    (facts : Phase17Finite.Facts
      (Phase17SuccessorContext.configurationAt fixed contexts charges s) s c e)
    (failure : SemanticFailure fixed s c) :
    Learned.LearnedAcceptedStep (learned fixed contexts charges) s c
      (packet fixed contexts charges s e) :=
  (accepted_iff fixed contexts charges s c e).mpr
    ⟨Phase17SuccessorContext.accepted fixed contexts charges s c e facts, failure⟩

theorem already_solved_rejected (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence)
    (solved : (fixed.catalog c.update.task).holds (Phase17Finite.taskObservation s)) :
    ¬ Learned.LearnedAcceptedStep (learned fixed contexts charges) s c
      (packet fixed contexts charges s e) := by
  intro h
  exact h.baseObligations.realityContained.2 solved

/-- A guarded accepted step proves actual semantic failure then success for
    the fixed meaning. Frontier declaration alone does not imply this result. -/
theorem accepted_semantic_gain (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence)
    (h : Learned.LearnedAcceptedStep (learned fixed contexts charges) s c
      (packet fixed contexts charges s e)) :
    ¬ (fixed.catalog c.update.task).holds (Phase17Finite.taskObservation s) ∧
      (fixed.catalog c.update.task).holds (Phase17Finite.taskObservation c.next) := by
  refine ⟨h.baseObligations.realityContained.2, ?_⟩
  have typed : c.next = Phase17Finite.apply s c.update := h.baseObligations.typedSuccessor
  have adm : Phase17Finite.admissible fixed c.next := h.baseObligations.successorAdmissible
  have exactFrontier : Phase17Finite.frontier fixed c.next = c.next.declared :=
    adm.2.2.2.2.2.2.2.1
  apply Phase17TaskMeaning.checked_frontier_sound c.next.declared fixed.catalog
    (Phase17Finite.taskObservation c.next)
  change c.update.task ∈ Phase17Finite.frontier fixed c.next
  rw [exactFrontier, typed]
  exact Finset.mem_insert_self _ _

/-- For an affine task, typed append and the semantic guard force the newly
    appended program to supply the universal behavior. Every earlier registered
    program fails the same bounded adapter contract, independently of its key. -/
theorem accepted_affine_program (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (c : Candidate) (e : Evidence)
    (variant : Nat) (offset : Int)
    (meaning : fixed.catalog c.update.task = affineMeaning variant offset)
    (h : Learned.LearnedAcceptedStep (learned fixed contexts charges) s c
      (packet fixed contexts charges s e)) :
    Realizes variant offset c.update.program ∧
      ∀ entry ∈ s.programs, ¬ Realizes variant offset entry.2 := by
  have gain := accepted_semantic_gain fixed contexts charges s c e h
  rw [meaning] at gain
  have old : ∀ entry ∈ s.programs, ¬ Realizes variant offset entry.2 := by
    intro entry member real
    exact gain.1 ⟨entry, member, real⟩
  refine ⟨?_, old⟩
  rcases gain.2 with ⟨entry, member, real⟩
  change entry ∈ c.next.programs at member
  have typed : c.next = Phase17Finite.apply s c.update := h.baseObligations.typedSuccessor
  rw [typed] at member
  change entry ∈ s.programs ++ [(c.update.key, c.update.program)] at member
  rcases List.mem_append.mp member with prior | fresh
  · exact False.elim (old entry prior real)
  · have equal := List.mem_singleton.mp fresh
    simpa only [equal] using real

/-- Conditional composition in one fixed guarded kernel. Both independent
    transactions and both semantic failures must be supplied; this theorem
    does not assert a second candidate, search result, or physical execution. -/
theorem guarded_two_step (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (first second : Candidate) (e1 e2 : Evidence)
    (firstFacts : Phase17Finite.Facts
      (Phase17SuccessorContext.configurationAt fixed contexts charges s) s first e1)
    (firstFailure : SemanticFailure fixed s first)
    (secondFacts : Phase17Finite.Facts
      (Phase17SuccessorContext.configurationAt fixed contexts charges first.next) first.next second e2)
    (secondFailure : SemanticFailure fixed first.next second) :
    Learned.LearnedAcceptedStep (learned fixed contexts charges) s first
      (packet fixed contexts charges s e1) ∧
    Learned.LearnedAcceptedStep (learned fixed contexts charges) first.next second
      (packet fixed contexts charges first.next e2) ∧
    Phase17Finite.frontier fixed s ⊆ Phase17Finite.frontier fixed second.next ∧
    (Phase17Finite.frontier fixed s).card + 2 ≤ (Phase17Finite.frontier fixed second.next).card ∧
    Phase17Finite.protectedView second.next = Phase17Finite.protectedView s := by
  refine ⟨accepted fixed contexts charges s first e1 firstFacts firstFailure,
    accepted fixed contexts charges first.next second e2 secondFacts secondFailure,
    Finset.Subset.trans firstFacts.expansion.1 secondFacts.expansion.1, ?_, ?_⟩
  · have a := firstFacts.expansion.2
    have b := secondFacts.expansion.2
    change (Phase17Finite.frontier fixed s).card < (Phase17Finite.frontier fixed first.next).card at a
    change (Phase17Finite.frontier fixed first.next).card <
      (Phase17Finite.frontier fixed second.next).card at b
    omega
  · rw [secondFacts.typed, Phase17Finite.protected_view_preserved,
      firstFacts.typed, Phase17Finite.protected_view_preserved]

end Phase17TaskInterpretation
