import TaskInterpretation

/- Phase 17AG: a total, truthful interface to the declared finite obligations.
   The offered transactions are explicit inputs. Exhaustion concerns that finite
   ordered pool only. Inspection fuel is a count of attempted checks, distinct
   from the inherited transaction tariff and any physical/campaign budget.
   The interface preserves the fixed interpretation. It neither authenticates
   physical input extraction nor proves producer coverage or live succession. -/
namespace Phase17TruthfulSuccessor

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3
open Phase17TaskInterpretation

deriving instance DecidableEq for Phase17Finite.Evidence

structure Offer where
  update : Phase17Finite.Update
  next : State
  evidence : Evidence
  deriving DecidableEq

def Offer.candidate (offer : Offer) : Candidate := ⟨offer.update, offer.next⟩

/-- All eight original Facts fields, followed by a checked semantic absence.
    No supplied final-result Boolean replaces these checks. The inherited
    proposal verdict list is structurally checked; physical history truth and
    independent evaluator integration remain outside this finite relation. -/
def Conditions (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (offer : Offer) : Prop :=
  let cfg := Phase17SuccessorContext.configurationAt fixed contexts charges s
  Phase17Finite.admissible cfg s ∧
  Phase17Finite.admissible cfg offer.next ∧
  offer.next = Phase17Finite.apply s offer.update ∧
  Phase17Finite.UpdateValid cfg s offer.update ∧
  Phase17Finite.trustValid cfg s offer.candidate offer.evidence ∧
  Phase17Finite.resourceValid cfg offer.candidate offer.evidence ∧
  Phase17Provenance.CandidateMatches cfg.context offer.evidence.proposal
    (Phase17Finite.candidateView offer.candidate) ∧
  (Phase17Finite.frontier cfg s ⊆ Phase17Finite.frontier cfg offer.next ∧
    (Phase17Finite.frontier cfg s).card < (Phase17Finite.frontier cfg offer.next).card) ∧
  (fixed.catalog offer.update.task).check (Phase17Finite.taskObservation s) = false

private instance admissibleDecidable (cfg : Phase17Finite.Configuration) (s : State) :
    Decidable (Phase17Finite.admissible cfg s) := by
  unfold Phase17Finite.admissible Phase17Protected.WellFormed
  infer_instance

private instance updateDecidable (cfg : Phase17Finite.Configuration) (s : State)
    (update : Phase17Finite.Update) : Decidable (Phase17Finite.UpdateValid cfg s update) := by
  unfold Phase17Finite.UpdateValid
  infer_instance

private instance trustDecidable (cfg : Phase17Finite.Configuration) (s : State)
    (candidate : Candidate) (evidence : Evidence) :
    Decidable (Phase17Finite.trustValid cfg s candidate evidence) := by
  unfold Phase17Finite.trustValid Phase17Provenance.ContextValid
  infer_instance

private instance resourceDecidable (cfg : Phase17Finite.Configuration)
    (candidate : Candidate) (evidence : Evidence) :
    Decidable (Phase17Finite.resourceValid cfg candidate evidence) := by
  unfold Phase17Finite.resourceValid Phase17Resource.Fits
  infer_instance

private instance matchDecidable (context : Phase17Provenance.Context)
    (proposal : Phase17Provenance.Proposal) (candidate : Phase17Provenance.CandidateView) :
    Decidable (Phase17Provenance.CandidateMatches context proposal candidate) := by
  unfold Phase17Provenance.CandidateMatches Phase17Provenance.Produced Phase17Provenance.ContextValid
  infer_instance

instance conditionsDecidable (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (offer : Offer) :
    Decidable (Conditions fixed contexts charges s offer) := by
  dsimp only [Conditions]
  infer_instance

def check (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (offer : Offer) : Bool :=
  decide (Conditions fixed contexts charges s offer)

def CatalogComplete (fixed : Phase17Finite.Configuration) : Prop :=
  ∀ task observation,
    (fixed.catalog task).check observation = true ↔ (fixed.catalog task).holds observation

def Accepted (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (offer : Offer) : Prop :=
  Learned.LearnedAcceptedStep (learned fixed contexts charges) s offer.candidate
    (packet fixed contexts charges s offer.evidence)

theorem conditions_iff_facts (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (offer : Offer) :
    Conditions fixed contexts charges s offer ↔
      Phase17Finite.Facts (Phase17SuccessorContext.configurationAt fixed contexts charges s)
        s offer.candidate offer.evidence ∧
      (fixed.catalog offer.update.task).check (Phase17Finite.taskObservation s) = false := by
  constructor
  · rintro ⟨before, after, typed, update, trusted, resources, matched, expansion, absent⟩
    exact ⟨⟨before, after, typed, update, trusted, resources, matched, expansion⟩, absent⟩
  · rintro ⟨facts, absent⟩
    exact ⟨facts.beforeAdmissible, facts.afterAdmissible, facts.typed,
      facts.updateValid, facts.trusted, facts.resources, facts.matched, facts.expansion, absent⟩

theorem check_iff_conditions (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (offer : Offer) :
    check fixed contexts charges s offer = true ↔ Conditions fixed contexts charges s offer := by
  simp only [check, decide_eq_true_eq]

/-- Completeness is needed to interpret a false checker result as absence of
    the fixed meaning; soundness alone would not justify semantic novelty. -/
theorem semantic_absence_iff (fixed : Phase17Finite.Configuration)
    (complete : CatalogComplete fixed) (s : State) (offer : Offer) :
    (fixed.catalog offer.update.task).check (Phase17Finite.taskObservation s) = false ↔
      SemanticFailure fixed s offer.candidate := by
  change _ ↔ ¬ (fixed.catalog offer.update.task).holds (Phase17Finite.taskObservation s)
  rw [← complete]
  exact Bool.eq_false_iff

theorem check_sound (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (complete : CatalogComplete fixed) (s : State) (offer : Offer)
    (checked : check fixed contexts charges s offer = true) :
    Accepted fixed contexts charges s offer := by
  rcases (conditions_iff_facts fixed contexts charges s offer).mp
    ((check_iff_conditions fixed contexts charges s offer).mp checked) with ⟨facts, absent⟩
  exact Phase17TaskInterpretation.accepted fixed contexts charges s offer.candidate offer.evidence
    facts ((semantic_absence_iff fixed complete s offer).mp absent)

/-- The inherited accepted type does not itself assert source admissibility.
    Keeping that domain condition explicit makes the equivalence exact. -/
theorem check_iff_accepted (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (complete : CatalogComplete fixed) (s : State)
    (source : Phase17Finite.admissible fixed s) (offer : Offer) :
    check fixed contexts charges s offer = true ↔ Accepted fixed contexts charges s offer := by
  constructor
  · exact check_sound fixed contexts charges complete s offer
  · intro accepted
    apply (check_iff_conditions fixed contexts charges s offer).mpr
    apply (conditions_iff_facts fixed contexts charges s offer).mpr
    refine ⟨?_, (semantic_absence_iff fixed complete s offer).mpr
      accepted.baseObligations.realityContained.2⟩
    exact {
      beforeAdmissible := source
      afterAdmissible := accepted.baseObligations.successorAdmissible
      typed := accepted.baseObligations.typedSuccessor
      updateValid := accepted.baseObligations.realityContained.1.2.1
      trusted := accepted.baseObligations.trustValid
      resources := accepted.baseObligations.resourceValid
      matched := accepted.baseObligations.realityContained.1.2.2.1
      expansion := accepted.learnedObligations.strictFrontierExpansion }

theorem refusal_iff (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (complete : CatalogComplete fixed) (s : State)
    (source : Phase17Finite.admissible fixed s) (offer : Offer) :
    check fixed contexts charges s offer = false ↔ ¬ Accepted fixed contexts charges s offer := by
  rw [← check_iff_accepted fixed contexts charges complete s source offer]
  exact Bool.eq_false_iff

theorem checked_semantic_gain (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (complete : CatalogComplete fixed) (s : State) (offer : Offer)
    (checked : check fixed contexts charges s offer = true) :
    ¬ (fixed.catalog offer.update.task).holds (Phase17Finite.taskObservation s) ∧
      (fixed.catalog offer.update.task).holds (Phase17Finite.taskObservation offer.next) :=
  accepted_semantic_gain fixed contexts charges s offer.candidate offer.evidence
    (check_sound fixed contexts charges complete s offer checked)

theorem checked_protected_recovery (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (offer : Offer)
    (checked : check fixed contexts charges s offer = true) :
    Phase17Finite.protectedView offer.next = Phase17Finite.protectedView s ∧
      Phase17Finite.recover offer.update offer.next = s := by
  have facts := ((conditions_iff_facts fixed contexts charges s offer).mp
    ((check_iff_conditions fixed contexts charges s offer).mp checked)).1
  rcases facts.updateValid with ⟨parent, _, _, _, freshTask, freshName, _⟩
  have typed : offer.next = Phase17Finite.apply s offer.update := facts.typed
  rw [typed]
  exact ⟨Phase17Finite.protected_view_preserved s offer.update,
    Phase17Finite.exact_recovery s offer.update parent freshTask freshName⟩

inductive Outcome (α : Type) where
  | accepted (index : Nat) (offer : α)
  | exhausted
  | budgetStop
  deriving DecidableEq

def advance {α : Type} : Outcome α → Outcome α
  | .accepted index offer => .accepted (index + 1) offer
  | .exhausted => .exhausted
  | .budgetStop => .budgetStop

/-- Empty-pool exhaustion takes precedence over a zero inspection budget. -/
def scan {α : Type} (test : α → Bool) : List α → Nat → Outcome α
  | [], _ => .exhausted
  | _ :: _, 0 => .budgetStop
  | offer :: rest, fuel + 1 =>
      if test offer then .accepted 0 offer else advance (scan test rest fuel)

def ScanSpec {α : Type} (test : α → Bool) (offers : List α) (fuel : Nat) : Outcome α → Prop
  | .accepted index offer =>
      ∃ before after, offers = before ++ offer :: after ∧ before.length = index ∧
        index < fuel ∧ (∀ prior ∈ before, test prior = false) ∧ test offer = true
  | .exhausted => offers.length ≤ fuel ∧ ∀ offer ∈ offers, test offer = false
  | .budgetStop => fuel < offers.length ∧ ∀ offer ∈ offers.take fuel, test offer = false

theorem scan_spec {α : Type} (test : α → Bool) (offers : List α) (fuel : Nat) :
    ScanSpec test offers fuel (scan test offers fuel) := by
  induction offers generalizing fuel with
  | nil => simp [scan, ScanSpec]
  | cons offer rest ih =>
    cases fuel with
    | zero => simp [scan, ScanSpec]
    | succ fuel =>
      cases tested : test offer with
      | true =>
        simp only [scan, tested, if_true, ScanSpec]
        exact ⟨[], rest, rfl, rfl, Nat.zero_lt_succ _, by simp, True.intro⟩
      | false =>
        have prior := ih fuel
        cases result : scan test rest fuel with
        | accepted index selected =>
          rw [result] at prior
          rcases prior with ⟨before, after, pool, size, bound, rejected, accepted⟩
          simp only [scan, tested, Bool.false_eq_true, if_false, result, advance, ScanSpec]
          refine ⟨offer :: before, after, ?_, by simpa using congrArg Nat.succ size,
            by omega, ?_, accepted⟩
          · simp only [List.cons_append, pool]
          · intro item member
            rcases List.mem_cons.mp member with rfl | member
            · exact tested
            · exact rejected item member
        | exhausted =>
          rw [result] at prior
          rcases prior with ⟨bound, rejected⟩
          simp only [scan, tested, Bool.false_eq_true, if_false, result, advance, ScanSpec]
          refine ⟨by simpa using Nat.succ_le_succ bound, ?_⟩
          intro item member
          rcases List.mem_cons.mp member with rfl | member
          · exact tested
          · exact rejected item member
        | budgetStop =>
          rw [result] at prior
          rcases prior with ⟨bound, rejected⟩
          simp only [scan, tested, Bool.false_eq_true, if_false, result, advance, ScanSpec]
          refine ⟨by simpa using Nat.succ_lt_succ bound, ?_⟩
          intro item member
          simp only [List.take_succ_cons, List.mem_cons] at member
          rcases member with rfl | member
          · exact tested
          · exact rejected item member

theorem scan_exhausted_iff {α : Type} (test : α → Bool) (offers : List α) (fuel : Nat) :
    scan test offers fuel = .exhausted ↔
      offers.length ≤ fuel ∧ ∀ offer ∈ offers, test offer = false := by
  constructor
  · intro result
    simpa only [result, ScanSpec] using scan_spec test offers fuel
  · rintro ⟨bound, rejected⟩
    have spec := scan_spec test offers fuel
    cases result : scan test offers fuel with
    | exhausted => rfl
    | budgetStop =>
        rw [result] at spec
        exact False.elim (Nat.not_lt_of_ge bound spec.1)
    | accepted index offer =>
        rw [result] at spec
        rcases spec with ⟨before, after, pool, _, _, _, accepted⟩
        have member : offer ∈ offers := by rw [pool]; simp
        have no := rejected offer member
        rw [no] at accepted
        cases accepted

theorem scan_budget_iff {α : Type} (test : α → Bool) (offers : List α) (fuel : Nat) :
    scan test offers fuel = .budgetStop ↔
      fuel < offers.length ∧ ∀ offer ∈ offers.take fuel, test offer = false := by
  constructor
  · intro result
    simpa only [result, ScanSpec] using scan_spec test offers fuel
  · intro stopped
    induction offers generalizing fuel with
    | nil => simp at stopped
    | cons offer rest ih =>
      cases fuel with
      | zero => rfl
      | succ fuel =>
        have tested : test offer = false := stopped.2 offer (by simp)
        have tail : fuel < rest.length ∧ ∀ item ∈ rest.take fuel, test item = false := by
          refine ⟨by simpa using stopped.1, ?_⟩
          intro item member
          exact stopped.2 item (by simpa using Or.inr member)
        simp only [scan, tested, Bool.false_eq_true, if_false, ih fuel tail, advance]

/-- Pool exhaustion is complete for that exact finite list once every entry
    may be inspected. It does not assert anything about an unoffered candidate. -/
theorem scan_exists_iff {α : Type} (test : α → Bool) (offers : List α) (fuel : Nat)
    (enough : offers.length ≤ fuel) :
    (∃ index offer, scan test offers fuel = .accepted index offer) ↔
      ∃ offer ∈ offers, test offer = true := by
  constructor
  · rintro ⟨index, offer, result⟩
    have spec := scan_spec test offers fuel
    rw [result] at spec
    rcases spec with ⟨before, after, pool, _, _, _, accepted⟩
    exact ⟨offer, by rw [pool]; simp, accepted⟩
  · rintro ⟨offer, member, accepted⟩
    have spec := scan_spec test offers fuel
    cases result : scan test offers fuel with
    | accepted index selected => exact ⟨index, selected, rfl⟩
    | exhausted =>
        rw [result] at spec
        have no := spec.2 offer member
        rw [no] at accepted
        cases accepted
    | budgetStop =>
        rw [result] at spec
        exact False.elim (Nat.not_lt_of_ge enough spec.1)

def search (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (offers : List Offer) (inspectionBudget : Nat) : Outcome Offer :=
  scan (check fixed contexts charges s) offers inspectionBudget

theorem search_accepted_sound (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (complete : CatalogComplete fixed) (s : State)
    (offers : List Offer) (fuel index : Nat) (offer : Offer)
    (result : search fixed contexts charges s offers fuel = .accepted index offer) :
    offer ∈ offers ∧ index < fuel ∧ Accepted fixed contexts charges s offer ∧
      ∃ before after, offers = before ++ offer :: after ∧ before.length = index ∧
        ∀ prior ∈ before, check fixed contexts charges s prior = false := by
  have spec := scan_spec (check fixed contexts charges s) offers fuel
  change ScanSpec _ _ _ (search fixed contexts charges s offers fuel) at spec
  rw [result] at spec
  rcases spec with ⟨before, after, pool, size, bound, rejected, checked⟩
  exact ⟨by rw [pool]; simp, bound, check_sound fixed contexts charges complete s offer checked,
    before, after, pool, size, rejected⟩

theorem search_exhausted_iff (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (complete : CatalogComplete fixed) (s : State)
    (source : Phase17Finite.admissible fixed s) (offers : List Offer) (fuel : Nat) :
    search fixed contexts charges s offers fuel = .exhausted ↔
      offers.length ≤ fuel ∧ ∀ offer ∈ offers, ¬ Accepted fixed contexts charges s offer := by
  rw [search, scan_exhausted_iff]
  simp only [refusal_iff fixed contexts charges complete s source]

theorem search_budget_iff (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (complete : CatalogComplete fixed) (s : State)
    (source : Phase17Finite.admissible fixed s) (offers : List Offer) (fuel : Nat) :
    search fixed contexts charges s offers fuel = .budgetStop ↔
      fuel < offers.length ∧
        ∀ offer ∈ offers.take fuel, ¬ Accepted fixed contexts charges s offer := by
  rw [search, scan_budget_iff]
  simp only [refusal_iff fixed contexts charges complete s source]

theorem search_exists_iff (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (complete : CatalogComplete fixed) (s : State)
    (source : Phase17Finite.admissible fixed s) (offers : List Offer) (fuel : Nat)
    (enough : offers.length ≤ fuel) :
    (∃ index offer, search fixed contexts charges s offers fuel = .accepted index offer) ↔
      ∃ offer ∈ offers, Accepted fixed contexts charges s offer := by
  rw [search, scan_exists_iff _ _ _ enough]
  simp only [check_iff_accepted fixed contexts charges complete s source]

/-- A finite semantic support is a fixed interpretation property, independent
    of any candidate or selected successor. -/
def CatalogBound (fixed : Phase17Finite.Configuration) (size : Nat) : Prop :=
  ∀ task, size ≤ task → ∀ observation, (fixed.catalog task).check observation = false

theorem frontier_card_bound (fixed : Phase17Finite.Configuration) (size : Nat)
    (bounded : CatalogBound fixed size) (s : State) :
    (Phase17Finite.frontier fixed s).card ≤ size := by
  have subset : Phase17Finite.frontier fixed s ⊆ Finset.range size := by
    intro task member
    have checked := (Finset.mem_filter.mp member).2
    apply Finset.mem_range.mpr
    by_contra outside
    have no := bounded task (Nat.le_of_not_gt outside) (Phase17Finite.taskObservation s)
    rw [no] at checked
    cases checked
  simpa using Finset.card_le_card subset

theorem extended_catalog_bound (cfg : Phase17Finite.Configuration) :
    CatalogBound (extendConfiguration cfg) 282 := by
  intro task outside observation
  change (extendedCatalog cfg.catalog task).check observation = false
  rw [catalog_outside_rejected cfg.catalog task outside]
  rfl

theorem checked_strict_growth (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (s : State) (offer : Offer)
    (checked : check fixed contexts charges s offer = true) :
    (Phase17Finite.frontier fixed s).card < (Phase17Finite.frontier fixed offer.next).card :=
  ((conditions_iff_facts fixed contexts charges s offer).mp
    ((check_iff_conditions fixed contexts charges s offer).mp checked)).1.expansion.2

/-- Every actual finite run must supply a checked offer at each linked source.
    The length bound is conditional on that run, never a construction of it. -/
theorem checked_run_length_bound (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (size : Nat) (bounded : CatalogBound fixed size)
    (states : Nat → State) (offers : Nat → Offer) (steps : Nat)
    (run : ∀ i, i < steps → (offers i).next = states (i + 1) ∧
      check fixed contexts charges (states i) (offers i) = true) :
    (Phase17Finite.frontier fixed (states 0)).card + steps ≤ size := by
  have growth : ∀ n, n ≤ steps →
      (Phase17Finite.frontier fixed (states 0)).card + n ≤
        (Phase17Finite.frontier fixed (states n)).card := by
    intro n
    induction n with
    | zero => intro _; simp
    | succ n ih =>
        intro bound
        have before := ih (by omega)
        have selected := run n (by omega)
        have strict := checked_strict_growth fixed contexts charges (states n) (offers n) selected.2
        rw [selected.1] at strict
        omega
  exact le_trans (growth steps le_rfl) (frontier_card_bound fixed size bounded (states steps))

theorem no_unbounded_checked_run (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (size : Nat) (bounded : CatalogBound fixed size)
    (states : Nat → State) (offers : Nat → Offer) :
    ¬ (∀ i, (offers i).next = states (i + 1) ∧
      check fixed contexts charges (states i) (offers i) = true) := by
  intro run
  have bound := checked_run_length_bound fixed contexts charges size bounded states offers
    (size + 1) (fun i _ => run i)
  omega

theorem saturated_frontier_refused (fixed : Phase17Finite.Configuration) (contexts : Contexts)
    (charges : Charges) (size : Nat) (bounded : CatalogBound fixed size) (s : State)
    (saturated : (Phase17Finite.frontier fixed s).card = size) (offer : Offer) :
    check fixed contexts charges s offer = false := by
  apply Bool.eq_false_iff.mpr
  intro checked
  have strict := checked_strict_growth fixed contexts charges s offer checked
  have bound := frontier_card_bound fixed size bounded offer.next
  omega

end Phase17TruthfulSuccessor
