import RcpRclmFormalCoreV3.Learned.Kernel
import Mathlib.Tactic

/- Phase 17N: declared reference-work tariffs, not physical resource totals.
   Journal persistence, extraction and actual execution are external bindings. -/
namespace Phase17Resource
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

inductive Kind where
  | candidate
  | vector
  deriving DecidableEq

abbrev Dimension := Fin 4

def tariff (k : Kind) (i : Dimension) : Nat :=
  match k, i.val with
  | .candidate, 0 => 1
  | .vector, 1 => 1
  | .vector, 2 => 4
  | .vector, 3 => 4
  | _, _ => 0

def unitCost : Kind → Nat
  | .candidate => 64
  | .vector => 24

def counter (xs : List Kind) (i : Dimension) : Nat :=
  (xs.map (fun k => tariff k i)).sum

def totalCost (xs : List Kind) : Nat := (xs.map unitCost).sum

structure Policy where
  limits : Dimension → Nat
  costLimit : Nat

def Fits (p : Policy) (xs : List Kind) : Prop :=
  totalCost xs ≤ p.costLimit ∧ ∀ i, counter xs i ≤ p.limits i

theorem cost_matches_weighted_counters (xs : List Kind) :
    totalCost xs = 64 * counter xs 0 + 16 * counter xs 1 + counter xs 2 + counter xs 3 := by
  induction xs with
  | nil => simp [totalCost, counter]
  | cons k rest ih =>
    cases k <;> simp [totalCost, counter, unitCost, tariff] at * <;> omega

theorem counter_prefix_non_decreasing (xs ys : List Kind) (i : Dimension) :
    counter xs i ≤ counter (xs ++ ys) i := by
  simp only [counter, List.map_append, List.sum_append]
  omega

theorem cost_prefix_non_decreasing (xs ys : List Kind) :
    totalCost xs ≤ totalCost (xs ++ ys) := by
  simp only [totalCost, List.map_append, List.sum_append]
  omega

theorem bounded_final_implies_bounded_prefix (p : Policy) (xs ys : List Kind)
    (h : Fits p (xs ++ ys)) : Fits p xs := by
  exact ⟨le_trans (cost_prefix_non_decreasing xs ys) h.1,
    fun i => le_trans (counter_prefix_non_decreasing xs ys i) (h.2 i)⟩

theorem over_budget_excluded (p : Policy) (xs : List Kind)
    (exceeded : p.costLimit < totalCost xs) : ¬ Fits p xs := by
  intro h
  exact (Nat.not_le_of_gt exceeded) h.1

theorem appended_charge_not_refunded (xs : List Kind) (k : Kind) :
    totalCost xs ≤ totalCost (xs ++ [k]) :=
  cost_prefix_non_decreasing xs [k]

/- Only resourceUsed/resourceBudget are supplied by this adapter. The concrete
   base, goal/information, frontier and producer obligations remain unchanged. -/
noncomputable def attach
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (charges : State → RCP.Candidate State Update → List Kind)
    (policy : State → RCP.Candidate State Update → Policy) :
    Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base :=
  { other with
    resourceUsed := fun s c => totalCost (charges s c)
    resourceBudget := fun s c => (policy s c).costLimit }

theorem unrelated_fields_unchanged
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (charges : State → RCP.Candidate State Update → List Kind)
    (policy : State → RCP.Candidate State Update → Policy) :
    (attach other charges policy).goalDrift = other.goalDrift ∧
    (attach other charges policy).informationValue = other.informationValue ∧
    (attach other charges policy).frontier = other.frontier ∧
    (attach other charges policy).proposalProducedBy = other.proposalProducedBy ∧
    (attach other charges policy).proposalBindsCandidate = other.proposalBindsCandidate :=
  ⟨rfl, rfl, rfl, rfl, rfl⟩

theorem attached_resource_bound
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (charges : State → RCP.Candidate State Update → List Kind)
    (policy : State → RCP.Candidate State Update → Policy)
    (s : State) (c : RCP.Candidate State Update)
    (h : Fits (policy s c) (charges s c)) :
    (attach other charges policy).resourceUsed s c ≤ (attach other charges policy).resourceBudget s c :=
  h.1

end Phase17Resource

namespace Phase17Resource
set_option maxRecDepth 8192
set_option maxHeartbeats 4000000
def selectedTrace : List Kind := [.vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .candidate, .vector, .vector, .vector, .vector, .vector, .vector, .vector, .vector]
def failedTrace : List Kind := [.vector]
def selectedPolicy : Policy := { limits := fun i => ([32, 328, 1312, 1312] : List Nat).getD i.val 0, costLimit := 9920 }
def expectedBinding : List String := ["b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e", "fc4cf15ec370547b14fc67ae360269cea71cbc10d773536d1a77891acbe3bf7e", "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535", "16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f"]
def observedBinding : List String := ["0000000000000000000000000000000000000000000000000000000000000000", "fc4cf15ec370547b14fc67ae360269cea71cbc10d773536d1a77891acbe3bf7e", "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535", "16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f"]

theorem selected_usage :
    counter selectedTrace 0 = 9 ∧ counter selectedTrace 1 = 144 ∧
    counter selectedTrace 2 = 576 ∧ counter selectedTrace 3 = 576 ∧
    totalCost selectedTrace = 4032 := by decide

theorem selected_budget : Fits selectedPolicy selectedTrace := by
  unfold Fits
  decide

theorem selected_bindings : observedBinding = expectedBinding := by decide

theorem selected_failed_charge : failedTrace = [Kind.vector] ∧ totalCost failedTrace = 24 := by decide
end Phase17Resource
#print axioms Phase17Resource.cost_matches_weighted_counters
#print axioms Phase17Resource.counter_prefix_non_decreasing
#print axioms Phase17Resource.cost_prefix_non_decreasing
#print axioms Phase17Resource.bounded_final_implies_bounded_prefix
#print axioms Phase17Resource.over_budget_excluded
#print axioms Phase17Resource.appended_charge_not_refunded
#print axioms Phase17Resource.unrelated_fields_unchanged
#print axioms Phase17Resource.attached_resource_bound
#print axioms Phase17Resource.selected_usage
#print axioms Phase17Resource.selected_budget
#print axioms Phase17Resource.selected_bindings
#print axioms Phase17Resource.selected_failed_charge
