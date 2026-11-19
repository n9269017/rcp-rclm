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
