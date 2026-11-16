import SelectedSecondStep
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

namespace Phase17SuccessorInterface
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3 Phase17TaskInterpretation Phase17SecondStep Phase17TruthfulSuccessor
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
-- Complete AG packet SHA256: 4f86b74e267c24fc9145f4ae9ce1dad5a385d9fb95e5b1219f8cadd5f62a7c82
def selectedOffer : Offer := ⟨secondUpdate, observedAfter, secondEvidence⟩
def evidenceLiteral1 : Evidence := { secondEvidence with root := "wrong-root" }
def offerLiteral1 : Offer := ⟨secondUpdate, observedAfter, evidenceLiteral1⟩
def updateLiteral1 : Phase17Finite.Update := { secondUpdate with parentPackage := "stale-parent" }
def offerLiteral2 : Offer := ⟨updateLiteral1, observedAfter, secondEvidence⟩
def evidenceLiteral2 : Evidence := { secondEvidence with contextHash := "wrong-context" }
def offerLiteral3 : Offer := ⟨secondUpdate, observedAfter, evidenceLiteral2⟩
def evidenceLiteral3 : Evidence := { secondEvidence with candidatePackage := "wrong-candidate" }
def offerLiteral4 : Offer := ⟨secondUpdate, observedAfter, evidenceLiteral3⟩
def stateLiteral2 : State := { observedAfter with semantic := { rows := [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 16383, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], selectors := [0, 1, 2, 3, 4, 5, 2, 6, 4, 0, 2, 7, 4, 8, 2, 8, 4, 9, 2, 10, 4, 1, 11, 12, 11, 13, 11, 14, 15, 11, 1, 11, 1, 2, 16, 4, 0, 2, 17, 4, 18, 2, 19, 4, 1, 2, 20, 4, 1, 21, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 23, 22, 22, 24, 25, 26, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 21, 22, 22, 22, 27, 28, 29, 22, 22, 22, 22, 21, 30, 22, 31, 22, 21, 32, 22, 22, 22, 22, 22, 22, 22, 21, 22, 22, 22, 22, 22, 0, 1, 2, 3, 4, 5, 2, 6, 4, 33, 34, 19, 20, 2, 7, 4, 8, 2, 8, 4, 9, 2, 10, 4, 1, 11, 12, 11, 1, 11, 14, 15, 11, 1, 11, 1, 2, 16, 4, 33, 34, 19, 20, 2, 17, 4, 18, 2, 19, 4, 13, 2, 20, 4, 13, 21, 22, 22, 22, 22, 22, 22, 22, 22, 0, 1, 2, 3, 4, 5, 2, 6, 4, 33, 34, 35, 19, 20, 2, 7, 4, 8, 2, 8, 4, 9, 2, 10, 4, 1, 11, 12, 11, 1, 11, 14, 15, 11, 1, 11, 1, 2, 16, 4, 36, 34, 35, 19, 20, 2, 17, 4, 18, 2, 19, 4, 13, 2, 20, 4, 13, 21, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22], goals := [[80, 111, 109, 101, 103, 97, 258], [82, 114, 102, 108, 258], [83, 122, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258], [84, 113, 258]] } }
def offerLiteral5 : Offer := ⟨secondUpdate, stateLiteral2, secondEvidence⟩
def evidenceLiteral4 : Evidence := { secondEvidence with charges := [] }
def offerLiteral6 : Offer := ⟨secondUpdate, observedAfter, evidenceLiteral4⟩
def updateLiteral2 : Phase17Finite.Update := { secondUpdate with program := { family := 0, variant := 0, a := (-5), b := 7 } }
def offerLiteral7 : Offer := ⟨updateLiteral2, observedAfter, secondEvidence⟩
def updateLiteral3 : Phase17Finite.Update := { secondUpdate with taskName := "renamed-task" }
def offerLiteral8 : Offer := ⟨updateLiteral3, observedAfter, secondEvidence⟩
def updateLiteral4 : Phase17Finite.Update := { secondUpdate with task := 259, taskName := "phase17ae.adapter.affine.3.42" }
def stateLiteral3 : State := { observedAfter with declared := ([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 259] : List Nat).toFinset, namedFrontier := (["lean.phase10.heldout.linear_gap", "lean.phase10.protected.reflexive_seven", "lean.phase11.heldout.add_zero_macro", "lean.phase12.generation1.le_refl_macro", "lean.phase12.generation2.zero_le_macro", "lean.phase12.generation3.lt_succ_planner_macro", "lean.phase12.generation4.lt_add_two_adapter_macro", "lean.phase14.generation5_zero_lt_succ", "lean.phase14.generation6_lt_add_five", "lean.phase14.generation7_succ_le_add_two", "lean.phase14.generation8_le_add_four", "lean.phase15.dynamic.multistep.4a7a415bcd169bb8", "phase16.dynamic.adapter_policy.2624594ed996371dbea9", "phase16.dynamic.architecture_policy.c3cd1f252d113cb41ebc", "phase16.dynamic.memory_policy.f9734b7e402fa0a0e992", "phase16.dynamic.optimizer_policy.10a54f6a7c3503fa7430", "phase16.dynamic.planner_policy.e8a5ef052b4885132a71", "phase16.dynamic.retrieval_policy.376f6d7a4130a978e1e6", "phase16.dynamic.tool_policy.231b912e39ff91bade12", "phase16.dynamic.verification_automation_policy.4290be408ad83beccf87", "phase17.dynamic.478d7884588779bca1483fb65d06d2a4b4d430960c47a6fdfd8036fb8a39c2ab", "phase17ae.adapter.affine.3.42", "program.phase15.dynamic.affine.beb80dc125251a70"] : List String).toFinset }
def offerLiteral9 : Offer := ⟨updateLiteral4, stateLiteral3, secondEvidence⟩
def updateLiteral5 : Phase17Finite.Update := { secondUpdate with task := 40, taskName := "phase17ae.adapter.affine.0.18" }
def stateLiteral4 : State := { observedAfter with declared := ([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 40] : List Nat).toFinset, namedFrontier := (["lean.phase10.heldout.linear_gap", "lean.phase10.protected.reflexive_seven", "lean.phase11.heldout.add_zero_macro", "lean.phase12.generation1.le_refl_macro", "lean.phase12.generation2.zero_le_macro", "lean.phase12.generation3.lt_succ_planner_macro", "lean.phase12.generation4.lt_add_two_adapter_macro", "lean.phase14.generation5_zero_lt_succ", "lean.phase14.generation6_lt_add_five", "lean.phase14.generation7_succ_le_add_two", "lean.phase14.generation8_le_add_four", "lean.phase15.dynamic.multistep.4a7a415bcd169bb8", "phase16.dynamic.adapter_policy.2624594ed996371dbea9", "phase16.dynamic.architecture_policy.c3cd1f252d113cb41ebc", "phase16.dynamic.memory_policy.f9734b7e402fa0a0e992", "phase16.dynamic.optimizer_policy.10a54f6a7c3503fa7430", "phase16.dynamic.planner_policy.e8a5ef052b4885132a71", "phase16.dynamic.retrieval_policy.376f6d7a4130a978e1e6", "phase16.dynamic.tool_policy.231b912e39ff91bade12", "phase16.dynamic.verification_automation_policy.4290be408ad83beccf87", "phase17.dynamic.478d7884588779bca1483fb65d06d2a4b4d430960c47a6fdfd8036fb8a39c2ab", "phase17ae.adapter.affine.0.18", "program.phase15.dynamic.affine.beb80dc125251a70"] : List String).toFinset }
def offerLiteral10 : Offer := ⟨updateLiteral5, stateLiteral4, secondEvidence⟩
def stateLiteral5 : State := { Phase17Finite.selectedAfter with proofs := [("lean.phase10.protected.reflexive_seven", "2923a5127ebb2dce77b93f25bfacd4ff8d23778e9c045de8ddabed164da927fb", "5392f810f0edaae2646222e27e4ba85dd09365294490637453dd5afc4086fd0a"), ("lean.phase11.heldout.add_zero_macro", "f17a5ce95e825ce7b1f160ea01b9af617754a0599dc79e598631d760d2737662", "047c1526c8be605c14dbb1ea9e7fdf798d960958c44b0c54e2c3b20b72e5e8f1"), ("lean.phase12.generation1.le_refl_macro", "29a44f8162d395296df0b6a3695ef84d4c53754badd4fc40ac572339afe81343", "64b40cfc1967d7c61ff59e88447dda1c08214b7d4f6854ab21dfce92a58ef432"), ("lean.phase12.generation2.zero_le_macro", "2ccfa1a6941344d7717e88514799bc03b443551733ef5f6611568e3b709d11ad", "810b78e6006b0587963765efe4a87f9e1cf374126d4cdbee47d22b3483200d2c"), ("lean.phase12.generation3.lt_succ_planner_macro", "ef24333062d901e017672cd228a08665df7fe26cd039bd30af051edfe0bf1f15", "0a157eea313f12a5c66a407b2ab782cb22f9e6c4a49d5c231ccb29d5854b2caf"), ("lean.phase12.generation4.lt_add_two_adapter_macro", "60e6bbca487b6807d97338b84253481f2884d25644d8f9274b716799a504d269", "32fae1c4dd17a247879289f9b8f1b4e9988f76195a101abaab29f579438c1a6e"), ("lean.phase14.generation5_zero_lt_succ", "00a2b7cac3e41ec4f7f10326f38e7876550a166956b3133ab43b60a71d167d77", "c548cc466699b3891f55e2ea9b89cb03ffa95345e797b85abd1b5ccef11fab8c"), ("lean.phase14.generation6_lt_add_five", "5f3d24df1725dd940f10edd1a1fc857d3e0a0a74aee4af2970c17e87e88e1387", "d81b0c93645b5d1fe8038d6bdc5bf36bc7ce66f65c98e5e0e437351553f5a771"), ("lean.phase14.generation7_succ_le_add_two", "e674398024eb21a38ba89194a88e47bdb9e76adc711744020733036883991f1e", "fcfda49e8ce97e014155ca5d8a1f66e5b74eadad09c53517ac8829cc3dffb910"), ("lean.phase14.generation8_le_add_four", "e213d8c64ed0c514b3be2f8e1dabde63c3b432d738e0a603140a3c948ba6ddfa", "f08827e9b291f026e450572beb47983bb520419f39f515a22f1338dfa0bece31"), ("lean.phase15.dynamic.multistep.4a7a415bcd169bb8", "a269501136730bdcde4b1ab63efdb521ebb95bf9007b4dce32025cd893b3f830", "f34f041f82c60bc693c28bcee6677254696d0988d8ab656af003131fdf93d5b8"), ("program.phase15.dynamic.affine.beb80dc125251a70", "74b00915a34bd9b2abc617337883e545052e5193f01de883549f4b61c1e9bb9e", "3020c0904123f2b84315c42fe0e13b211f9a554d81b0e2f8e730805d737f505e")] }
def stateLiteral6 : State := { observedAfter with proofs := [("lean.phase10.protected.reflexive_seven", "2923a5127ebb2dce77b93f25bfacd4ff8d23778e9c045de8ddabed164da927fb", "5392f810f0edaae2646222e27e4ba85dd09365294490637453dd5afc4086fd0a"), ("lean.phase11.heldout.add_zero_macro", "f17a5ce95e825ce7b1f160ea01b9af617754a0599dc79e598631d760d2737662", "047c1526c8be605c14dbb1ea9e7fdf798d960958c44b0c54e2c3b20b72e5e8f1"), ("lean.phase12.generation1.le_refl_macro", "29a44f8162d395296df0b6a3695ef84d4c53754badd4fc40ac572339afe81343", "64b40cfc1967d7c61ff59e88447dda1c08214b7d4f6854ab21dfce92a58ef432"), ("lean.phase12.generation2.zero_le_macro", "2ccfa1a6941344d7717e88514799bc03b443551733ef5f6611568e3b709d11ad", "810b78e6006b0587963765efe4a87f9e1cf374126d4cdbee47d22b3483200d2c"), ("lean.phase12.generation3.lt_succ_planner_macro", "ef24333062d901e017672cd228a08665df7fe26cd039bd30af051edfe0bf1f15", "0a157eea313f12a5c66a407b2ab782cb22f9e6c4a49d5c231ccb29d5854b2caf"), ("lean.phase12.generation4.lt_add_two_adapter_macro", "60e6bbca487b6807d97338b84253481f2884d25644d8f9274b716799a504d269", "32fae1c4dd17a247879289f9b8f1b4e9988f76195a101abaab29f579438c1a6e"), ("lean.phase14.generation5_zero_lt_succ", "00a2b7cac3e41ec4f7f10326f38e7876550a166956b3133ab43b60a71d167d77", "c548cc466699b3891f55e2ea9b89cb03ffa95345e797b85abd1b5ccef11fab8c"), ("lean.phase14.generation6_lt_add_five", "5f3d24df1725dd940f10edd1a1fc857d3e0a0a74aee4af2970c17e87e88e1387", "d81b0c93645b5d1fe8038d6bdc5bf36bc7ce66f65c98e5e0e437351553f5a771"), ("lean.phase14.generation7_succ_le_add_two", "e674398024eb21a38ba89194a88e47bdb9e76adc711744020733036883991f1e", "fcfda49e8ce97e014155ca5d8a1f66e5b74eadad09c53517ac8829cc3dffb910"), ("lean.phase14.generation8_le_add_four", "e213d8c64ed0c514b3be2f8e1dabde63c3b432d738e0a603140a3c948ba6ddfa", "f08827e9b291f026e450572beb47983bb520419f39f515a22f1338dfa0bece31"), ("lean.phase15.dynamic.multistep.4a7a415bcd169bb8", "a269501136730bdcde4b1ab63efdb521ebb95bf9007b4dce32025cd893b3f830", "f34f041f82c60bc693c28bcee6677254696d0988d8ab656af003131fdf93d5b8"), ("program.phase15.dynamic.affine.beb80dc125251a70", "74b00915a34bd9b2abc617337883e545052e5193f01de883549f4b61c1e9bb9e", "3020c0904123f2b84315c42fe0e13b211f9a554d81b0e2f8e730805d737f505e")] }
def offerLiteral11 : Offer := ⟨secondUpdate, stateLiteral6, secondEvidence⟩

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
theorem refused_refusal : check fixed contexts charges Phase17Finite.selectedAfter offerLiteral1 = false := by
  apply Bool.eq_false_iff.mpr
  intro passed
  have conditions := (conditions_iff_facts fixed contexts charges Phase17Finite.selectedAfter offerLiteral1).mp
    ((check_iff_conditions fixed contexts charges Phase17Finite.selectedAfter offerLiteral1).mp passed)
  have facts := conditions.1
  have denied : ¬ (offerLiteral1.evidence.root = fixed.root) := by decide +kernel
  exact denied (facts.trusted.1)
theorem refused_stale_parent : check fixed contexts charges Phase17Finite.selectedAfter offerLiteral2 = false := by
  apply Bool.eq_false_iff.mpr
  intro passed
  have conditions := (conditions_iff_facts fixed contexts charges Phase17Finite.selectedAfter offerLiteral2).mp
    ((check_iff_conditions fixed contexts charges Phase17Finite.selectedAfter offerLiteral2).mp passed)
  have facts := conditions.1
  have denied : ¬ (offerLiteral2.update.parentPackage = Phase17Finite.selectedAfter.packageHash) := by decide +kernel
  exact denied (facts.updateValid.1)
theorem refused_wrong_context : check fixed contexts charges Phase17Finite.selectedAfter offerLiteral3 = false := by
  apply Bool.eq_false_iff.mpr
  intro passed
  have conditions := (conditions_iff_facts fixed contexts charges Phase17Finite.selectedAfter offerLiteral3).mp
    ((check_iff_conditions fixed contexts charges Phase17Finite.selectedAfter offerLiteral3).mp passed)
  have facts := conditions.1
  have denied : ¬ (offerLiteral3.evidence.contextHash = (Phase17SuccessorContext.configurationAt fixed contexts charges Phase17Finite.selectedAfter).context.contextHash) := by decide +kernel
  exact denied (facts.trusted.2.2.2.2.2.2.1)
theorem refused_wrong_candidate : check fixed contexts charges Phase17Finite.selectedAfter offerLiteral4 = false := by
  apply Bool.eq_false_iff.mpr
  intro passed
  have conditions := (conditions_iff_facts fixed contexts charges Phase17Finite.selectedAfter offerLiteral4).mp
    ((check_iff_conditions fixed contexts charges Phase17Finite.selectedAfter offerLiteral4).mp passed)
  have facts := conditions.1
  have denied : ¬ (offerLiteral4.evidence.candidatePackage = offerLiteral4.next.packageHash) := by decide +kernel
  exact denied (facts.trusted.2.2.2.2.2.1)
theorem refused_changed_protected : check fixed contexts charges Phase17Finite.selectedAfter offerLiteral5 = false := by
  apply Bool.eq_false_iff.mpr
  intro passed
  have conditions := (conditions_iff_facts fixed contexts charges Phase17Finite.selectedAfter offerLiteral5).mp
    ((check_iff_conditions fixed contexts charges Phase17Finite.selectedAfter offerLiteral5).mp passed)
  have facts := conditions.1
  have denied : ¬ (offerLiteral5.next.semantic.goals = (Phase17Finite.apply Phase17Finite.selectedAfter offerLiteral5.update).semantic.goals) := by decide +kernel
  exact denied (congrArg (fun s : State => s.semantic.goals) facts.typed)
theorem refused_omitted_charge : check fixed contexts charges Phase17Finite.selectedAfter offerLiteral6 = false := by
  apply Bool.eq_false_iff.mpr
  intro passed
  have conditions := (conditions_iff_facts fixed contexts charges Phase17Finite.selectedAfter offerLiteral6).mp
    ((check_iff_conditions fixed contexts charges Phase17Finite.selectedAfter offerLiteral6).mp passed)
  have facts := conditions.1
  have denied : ¬ (offerLiteral6.evidence.charges = offerLiteral6.update.charges) := by decide +kernel
  exact denied (facts.resources.1)
theorem refused_wrong_program : check fixed contexts charges Phase17Finite.selectedAfter offerLiteral7 = false := by
  apply Bool.eq_false_iff.mpr
  intro passed
  have conditions := (conditions_iff_facts fixed contexts charges Phase17Finite.selectedAfter offerLiteral7).mp
    ((check_iff_conditions fixed contexts charges Phase17Finite.selectedAfter offerLiteral7).mp passed)
  have facts := conditions.1
  have denied : ¬ (offerLiteral7.next.programs = (Phase17Finite.apply Phase17Finite.selectedAfter offerLiteral7.update).programs) := by decide +kernel
  exact denied (congrArg Phase17Finite.State.programs facts.typed)
theorem refused_wrong_task_name : check fixed contexts charges Phase17Finite.selectedAfter offerLiteral8 = false := by
  apply Bool.eq_false_iff.mpr
  intro passed
  have conditions := (conditions_iff_facts fixed contexts charges Phase17Finite.selectedAfter offerLiteral8).mp
    ((check_iff_conditions fixed contexts charges Phase17Finite.selectedAfter offerLiteral8).mp passed)
  have facts := conditions.1
  have denied : ¬ (offerLiteral8.update.taskName = fixed.taskName offerLiteral8.update.task) := by decide +kernel
  exact denied (facts.updateValid.2.2.2.2.2.2.1)
theorem refused_already_solved : check fixed contexts charges Phase17Finite.selectedAfter offerLiteral9 = false := by
  apply Bool.eq_false_iff.mpr
  intro passed
  have conditions := (conditions_iff_facts fixed contexts charges Phase17Finite.selectedAfter offerLiteral9).mp
    ((check_iff_conditions fixed contexts charges Phase17Finite.selectedAfter offerLiteral9).mp passed)
  have facts := conditions.1
  have available : (fixed.catalog offerLiteral9.update.task).check
      (Phase17Finite.taskObservation Phase17Finite.selectedAfter) = true := by decide +kernel
  rw [available] at conditions
  exact Bool.noConfusion conditions.2
theorem refused_false_successor : check fixed contexts charges Phase17Finite.selectedAfter offerLiteral10 = false := by
  apply Bool.eq_false_iff.mpr
  intro passed
  have conditions := (conditions_iff_facts fixed contexts charges Phase17Finite.selectedAfter offerLiteral10).mp
    ((check_iff_conditions fixed contexts charges Phase17Finite.selectedAfter offerLiteral10).mp passed)
  have facts := conditions.1
  have frontierExact := facts.afterAdmissible.2.2.2.2.2.2.2.1
  have declared : 40 ∈ offerLiteral10.next.declared := by decide +kernel
  have member : 40 ∈ Phase17Finite.frontier
      (Phase17SuccessorContext.configurationAt fixed contexts charges Phase17Finite.selectedAfter) offerLiteral10.next :=
    frontierExact.symm ▸ declared
  have checked := (Finset.mem_filter.mp member).2
  have rejected : (fixed.catalog 40).check (Phase17Finite.taskObservation offerLiteral10.next) = false := by decide +kernel
  change (fixed.catalog 40).check (Phase17Finite.taskObservation offerLiteral10.next) = true at checked
  rw [rejected] at checked
  cases checked
theorem refused_source_inadmissible : check fixed contexts charges stateLiteral5 offerLiteral11 = false := by
  apply Bool.eq_false_iff.mpr
  intro passed
  have conditions := (conditions_iff_facts fixed contexts charges stateLiteral5 offerLiteral11).mp
    ((check_iff_conditions fixed contexts charges stateLiteral5 offerLiteral11).mp passed)
  have facts := conditions.1
  have frontierExact := facts.beforeAdmissible.2.2.2.2.2.2.2.1
  have declared : 0 ∈ stateLiteral5.declared := by decide +kernel
  have member : 0 ∈ Phase17Finite.frontier
      (Phase17SuccessorContext.configurationAt fixed contexts charges stateLiteral5) stateLiteral5 :=
    frontierExact.symm ▸ declared
  have checked := (Finset.mem_filter.mp member).2
  have rejected : (fixed.catalog 0).check (Phase17Finite.taskObservation stateLiteral5) = false := by decide +kernel
  change (fixed.catalog 0).check (Phase17Finite.taskObservation stateLiteral5) = true at checked
  rw [rejected] at checked
  cases checked
def result_selected : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [selectedOffer] 1
theorem case_selected : resultSummary 1 1 result_selected = (0, (some 0), 1) := by
  simp only [result_selected, search, scan, selected_check, if_true, resultSummary]
def result_empty : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [] 0
theorem case_empty : resultSummary 0 0 result_empty = (1, none, 0) := by
  rfl
def result_zero_budget : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [selectedOffer] 0
theorem case_zero_budget : resultSummary 1 0 result_zero_budget = (2, none, 0) := by
  rfl
def result_refusal : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [offerLiteral1] 1
theorem case_refusal : resultSummary 1 1 result_refusal = (1, none, 1) := by
  simp only [result_refusal, search, scan, refused_refusal, Bool.false_eq_true, if_false, advance, resultSummary]
def result_refusal_then_selected : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [offerLiteral1, selectedOffer] 2
theorem case_refusal_then_selected : resultSummary 2 2 result_refusal_then_selected = (0, (some 1), 2) := by
  simp only [result_refusal_then_selected, search, scan, refused_refusal, selected_check, Bool.false_eq_true, if_false, advance, if_true, resultSummary]
def result_budget_before_selected : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [offerLiteral1, selectedOffer] 1
theorem case_budget_before_selected : resultSummary 2 1 result_budget_before_selected = (2, none, 1) := by
  simp only [result_budget_before_selected, search, scan, refused_refusal, Bool.false_eq_true, if_false, advance, resultSummary]
def result_stale_parent : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [offerLiteral2] 1
theorem case_stale_parent : resultSummary 1 1 result_stale_parent = (1, none, 1) := by
  simp only [result_stale_parent, search, scan, refused_stale_parent, Bool.false_eq_true, if_false, advance, resultSummary]
def result_wrong_context : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [offerLiteral3] 1
theorem case_wrong_context : resultSummary 1 1 result_wrong_context = (1, none, 1) := by
  simp only [result_wrong_context, search, scan, refused_wrong_context, Bool.false_eq_true, if_false, advance, resultSummary]
def result_wrong_candidate : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [offerLiteral4] 1
theorem case_wrong_candidate : resultSummary 1 1 result_wrong_candidate = (1, none, 1) := by
  simp only [result_wrong_candidate, search, scan, refused_wrong_candidate, Bool.false_eq_true, if_false, advance, resultSummary]
def result_changed_protected : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [offerLiteral5] 1
theorem case_changed_protected : resultSummary 1 1 result_changed_protected = (1, none, 1) := by
  simp only [result_changed_protected, search, scan, refused_changed_protected, Bool.false_eq_true, if_false, advance, resultSummary]
def result_omitted_charge : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [offerLiteral6] 1
theorem case_omitted_charge : resultSummary 1 1 result_omitted_charge = (1, none, 1) := by
  simp only [result_omitted_charge, search, scan, refused_omitted_charge, Bool.false_eq_true, if_false, advance, resultSummary]
def result_wrong_program : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [offerLiteral7] 1
theorem case_wrong_program : resultSummary 1 1 result_wrong_program = (1, none, 1) := by
  simp only [result_wrong_program, search, scan, refused_wrong_program, Bool.false_eq_true, if_false, advance, resultSummary]
def result_wrong_task_name : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [offerLiteral8] 1
theorem case_wrong_task_name : resultSummary 1 1 result_wrong_task_name = (1, none, 1) := by
  simp only [result_wrong_task_name, search, scan, refused_wrong_task_name, Bool.false_eq_true, if_false, advance, resultSummary]
def result_already_solved : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [offerLiteral9] 1
theorem case_already_solved : resultSummary 1 1 result_already_solved = (1, none, 1) := by
  simp only [result_already_solved, search, scan, refused_already_solved, Bool.false_eq_true, if_false, advance, resultSummary]
def result_false_successor : Outcome Offer := search fixed contexts charges Phase17Finite.selectedAfter [offerLiteral10] 1
theorem case_false_successor : resultSummary 1 1 result_false_successor = (1, none, 1) := by
  simp only [result_false_successor, search, scan, refused_false_successor, Bool.false_eq_true, if_false, advance, resultSummary]
def result_source_inadmissible : Outcome Offer := search fixed contexts charges stateLiteral5 [offerLiteral11] 1
theorem case_source_inadmissible : resultSummary 1 1 result_source_inadmissible = (1, none, 1) := by
  simp only [result_source_inadmissible, search, scan, refused_source_inadmissible, Bool.false_eq_true, if_false, advance, resultSummary]

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
