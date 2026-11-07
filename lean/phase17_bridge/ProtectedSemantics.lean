import Mathlib
import RcpRclmFormalCoreV2.RCP.ClassicalFinite
import RcpRclmFormalCoreV2.RCP.QuantumDensity
import RcpRclmFormalCoreV3.Learned.Kernel

/- Exact semantics of the DECLARED inherited 260-token sparse profile.
   The complete RCLM kernel and physical observation refinement are not supplied.
   Natural entries encode positive unnormalized weights minus one. -/
namespace Phase17Protected

open scoped BigOperators
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

abbrev Token := Fin 260

def weight (row : List Nat) (i : Token) : Nat := row.getD i.val 0 + 1
noncomputable def total (row : List Nat) : ℝ := ∑ i : Token, (weight row i : ℝ)

theorem total_positive (row : List Nat) : 0 < total row := by
  unfold total
  apply Finset.sum_pos
  · intro i _
    exact_mod_cast (Nat.succ_pos (row.getD i.val 0))
  · exact ⟨⟨0, by decide⟩, Finset.mem_univ _⟩

noncomputable def distribution (row : List Nat) : RCP.ClassicalFinite.PositiveDistribution 260 where
  distribution :=
    { mass := fun i => (weight row i : ℝ) / total row
      nonnegative := by
        intro i
        exact div_nonneg (Nat.cast_nonneg _) (total_positive row).le
      normalized := by
        rw [← Finset.sum_div]
        exact div_self (ne_of_gt (total_positive row)) }
  positive := by
    intro i
    apply div_pos
    · exact_mod_cast (Nat.succ_pos (row.getD i.val 0))
    · exact total_positive row

theorem mass_distribution_normalized (row : List Nat) :
    (∑ i : Token, (distribution row).distribution.mass i) = 1 :=
  (distribution row).distribution.normalized

noncomputable def density (row : List Nat) : RCP.QuantumFinite.DiagonalDensityMatrix 260 :=
  ⟨(distribution row).distribution⟩

theorem diagonal_density_sound (row : List Nat) :
    RCP.QuantumFinite.DensityMatrixEvidence (density row).matrix :=
  (density row).densityEvidence

theorem diagonal_information_is_kl (row target : List Nat) :
    RCP.QuantumFinite.quantumRelativeEntropy (density row) (density target) =
      RCP.ClassicalFinite.positiveKLDivergence (distribution row) (distribution target) ∧
    RCP.QuantumFinite.vonNeumannEntropy (density row) =
      RCP.ClassicalFinite.shannonEntropy (distribution row).distribution :=
  ⟨rfl, rfl⟩

structure Observation where
  rows : List (List Nat)
  selectors : List Nat
  goals : List (List Nat)
  deriving DecidableEq

structure Contract where
  positions : List (Nat × Nat)
  expectedGoals : List (List Nat)
  deriving DecidableEq

def rowAt (o : Observation) (current : Nat) : List Nat :=
  o.rows.getD (o.selectors.getD current 0) []

def targetRow (target : Nat) : List Nat :=
  (List.range 260).map (fun i => if i = target then 4095 else 0)

noncomputable def informationSum (o : Observation) : List (Nat × Nat) → ℝ
  | [] => 0
  | (current, target) :: rest =>
      RCP.ClassicalFinite.positiveKLDivergence
        (distribution (rowAt o current)) (distribution (targetRow target)) + informationSum o rest

noncomputable def informationValue (contract : Contract) (o : Observation) : ℝ :=
  informationSum o contract.positions

theorem information_sum_nonnegative (o : Observation) (positions : List (Nat × Nat)) :
    0 ≤ informationSum o positions := by
  induction positions with
  | nil => exact le_rfl
  | cons pair rest ih =>
    rcases pair with ⟨current, target⟩
    exact add_nonneg (RCP.ClassicalFinite.positiveKLDivergence_nonnegative _ _) ih

def goalDistance : List (List Nat) → List (List Nat) → Nat
  | [], ys => ys.length
  | _ :: xs, [] => xs.length + 1
  | x :: xs, y :: ys => (if x = y then 0 else 1) + goalDistance xs ys

theorem goal_distance_self (goals : List (List Nat)) : goalDistance goals goals = 0 := by
  induction goals with
  | nil => rfl
  | cons row rest ih => simp only [goalDistance, if_pos rfl, zero_add, ih]

/- These are explicit protected-profile fields with a zero-regression policy.
   Resource fields and all capability/provenance fields are left unchanged. -/
noncomputable def attach
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → Observation) (contract : Contract) :=
  { other with
    goalDrift := fun s c => goalDistance (observe s).goals (observe c.next).goals
    goalDriftBudget := fun _ _ => 0
    informationValue := fun s => informationValue contract (observe s)
    informationBudget := fun _ _ => 0
    informationBudget_nonnegative := fun _ _ => le_rfl }

theorem unrelated_root_fields_unchanged
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → Observation) (contract : Contract) :
    (attach other observe contract).resourceUsed = other.resourceUsed ∧
    (attach other observe contract).resourceBudget = other.resourceBudget ∧
    (attach other observe contract).frontier = other.frontier ∧
    (attach other observe contract).solves = other.solves ∧
    (attach other observe contract).activeGenerator = other.activeGenerator ∧
    (attach other observe contract).proposalProducedBy = other.proposalProducedBy ∧
    (attach other observe contract).proposalBindsCandidate = other.proposalBindsCandidate :=
  ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl⟩

theorem attached_protected_bounds
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → Observation) (contract : Contract)
    (s : State) (c : RCP.Candidate State Update)
    (retained : observe c.next = observe s) :
    (attach other observe contract).goalDrift s c ≤ (attach other observe contract).goalDriftBudget s c ∧
    (attach other observe contract).informationValue c.next ≤
      (attach other observe contract).informationValue s + (attach other observe contract).informationBudget s c := by
  change goalDistance (observe s).goals (observe c.next).goals ≤ 0 ∧
    informationValue contract (observe c.next) ≤ informationValue contract (observe s) + 0
  rw [retained, goal_distance_self, add_zero]
  exact ⟨le_rfl, le_rfl⟩

def WellFormed (o : Observation) : Prop :=
  o.selectors.length = 260 ∧ (∀ i ∈ o.selectors, i < o.rows.length) ∧
  (∀ r ∈ o.rows, r.length = 260) ∧ o.goals.length = 11

end Phase17Protected
