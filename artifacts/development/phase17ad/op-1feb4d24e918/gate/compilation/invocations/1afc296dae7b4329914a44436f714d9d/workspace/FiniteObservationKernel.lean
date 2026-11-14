import ProposalProvenance
import RcpRclmFormalCoreV4
import Mathlib.Tactic
import Mathlib.Data.Finset.Card
import Mathlib.Data.Finset.Filter
import Mathlib
import RcpRclmFormalCoreV2.RCP.ClassicalFinite
import RcpRclmFormalCoreV2.RCP.QuantumDensity
import RcpRclmFormalCoreV3.Learned.Kernel

/- A typed projection of measured package components. FileRef digests are not
   a proof of physical-byte equality: the external verifier compares those bytes.
   Only a fixed pure interpretation of the frozen view is preserved. No complete
   learned or autonomous accepted step is constructed by these lemmas. -/
namespace Phase17LearnedBinding

open RcpRclmFormalCoreV2

structure FileRef where
  path : String
  size : Nat
  digest : String
  deriving DecidableEq

abbrev Image := List FileRef

abbrev RootState := RcpRclmFormalCoreV3.Learned.PackageState
  (List String) Image Image Image Image Image Image Image Image Image Image Image String

structure BoundState where
  package : RootState
  executionContext : Image
  packageHash : String

def frozenView (s : BoundState) : List Image :=
  [s.package.modelArchitecture, s.package.modelWeights, s.package.generator,
   s.package.planner, s.package.trainingPolicy, s.package.retrievalPolicy,
   s.package.memory, s.package.tokenizer, s.package.verificationPolicy,
   s.package.resourcePolicy, s.package.selfModel, s.executionContext]

def extend (s : BoundState) (key task packageHash : String) : BoundState :=
  { package := { s.package with
      base := s.package.base ++ [key]
      capabilityFrontier := insert task s.package.capabilityFrontier }
    executionContext := s.executionContext
    packageHash := packageHash }

theorem frozen_view_preserved (s : BoundState) (key task packageHash : String) :
    frozenView (extend s key task packageHash) = frozenView s := rfl

theorem fixed_interpretation_retained {Input Output : Type*}
    (interpret : List Image → Input → Output)
    (before after : BoundState) (same : frozenView after = frozenView before)
    (input : Input) :
    interpret (frozenView after) input = interpret (frozenView before) input := by
  rw [same]

theorem information_value_retained
    (information : List Image → ℝ) (before after : BoundState)
    (same : frozenView after = frozenView before) :
    information (frozenView after) = information (frozenView before) :=
  congrArg information same

/- This refers to the actual learned-root information field. The semantic
   interpretation binding is an explicit premise, NOT inferred from a hash. -/
theorem root_information_bound
    {Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel BoundState Update BaseCertificate Protected ResidualIndex}
    (learned : RcpRclmFormalCoreV3.Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base)
    (state : BoundState) (candidate : RCP.Candidate BoundState Update)
    (information : List Image → ℝ)
    (binding : ∀ s, learned.informationValue s = information (frozenView s))
    (same : frozenView candidate.next = frozenView state) :
    learned.informationValue candidate.next ≤
      learned.informationValue state + learned.informationBudget state candidate := by
  rw [binding candidate.next, binding state, same]
  exact le_add_of_nonneg_right (learned.informationBudget_nonnegative state candidate)

theorem frontier_retained (s : BoundState) (key task packageHash : String) :
    s.package.capabilityFrontier ⊆ (extend s key task packageHash).package.capabilityFrontier := by
  intro t member
  change t ∈ insert task s.package.capabilityFrontier
  exact Finset.mem_insert_of_mem member

theorem frontier_grows (s : BoundState) (key task packageHash : String)
    (fresh : task ∉ s.package.capabilityFrontier) :
    s.package.capabilityFrontier.card < (extend s key task packageHash).package.capabilityFrontier.card := by
  change s.package.capabilityFrontier.card < (insert task s.package.capabilityFrontier).card
  rw [Finset.card_insert_of_notMem fresh]
  exact Nat.lt_succ_self _

end Phase17LearnedBinding


namespace Phase17TaskMeaning

structure Program where
  family : Nat
  variant : Nat
  a : Int
  b : Int
  deriving DecidableEq, Repr

def insertInt (a : Int) : List Int → List Int
  | [] => [a]
  | b :: bs => if a ≤ b then a :: b :: bs else b :: insertInt a bs

def sortInts : List Int → List Int
  | [] => []
  | a :: rest => insertInt a (sortInts rest)

/-- Independent Lean semantics of the unchanged four-integer mutation DSL. -/
def execute (p : Program) (xs : List Int) : List Int :=
  let v := p.variant + 1
  let vi : Int := Int.ofNat v
  let x := fun (i : Nat) => xs.getD i 0
  match p.family with
  | 0 => xs.map (fun z => vi * z + p.a - p.b)
  | 1 => (List.range 4).map (fun i => x ((i + v + 1) % 4) + p.a * Int.ofNat (i + 1) + p.b)
  | 2 => (List.range 4).map (fun i => x ((i + v) % 4) + if i = 0 then p.a else 0)
  | 3 => (List.range 4).map (fun i => xs.sum + p.a + Int.ofNat (v * (i + 1) * (i + 2) / 2) - p.b * Int.ofNat (i + 1))
  | 4 => [x 0 + p.a, x 1 * vi, x 2 - p.b, x 3 + x 0 * vi]
  | 5 => (List.range 4).map (fun i => x ((i * v + p.b.natAbs) % 4))
  | 6 => [x 0 + x 1 + p.a, x 1 - x 2 + p.b, x 2 * vi, x 3 + p.a - p.b]
  | 7 => sortInts (xs.map (fun z => z + p.a * vi - p.b))
  | _ => []

-- State projection is supplied by the external physical evaluator. These proofs
-- do not establish that arbitrary self-reported observations describe a model.
structure ObservationState where
  proofs : List (String × String × String)
  programs : List (String × Program)

structure Meaning where
  check : ObservationState → Bool
  holds : ObservationState → Prop
  sound : ∀ s, check s = true → holds s

def theoremMeaning (task source decode : String) (P : Prop) (proof : P) : Meaning where
  check := fun s => decide ((task, source, decode) ∈ s.proofs)
  holds := fun s => (task, source, decode) ∈ s.proofs ∧ P
  sound := by
    intro s h
    exact ⟨of_decide_eq_true h, proof⟩

structure VectorContract where
  family : Nat
  requiredProgram : Option String
  inputs : List (List Int)
  targets : List (List Int)

def vectorMeaning (t : VectorContract) : Meaning where
  check := fun s => s.programs.any (fun e => decide
    (e.2.family = t.family ∧
     (t.requiredProgram = none ∨ t.requiredProgram = some e.1) ∧
     t.inputs.map (execute e.2) = t.targets))
  holds := fun s => ∃ e ∈ s.programs,
    e.2.family = t.family ∧
    (t.requiredProgram = none ∨ t.requiredProgram = some e.1) ∧
    t.inputs.map (execute e.2) = t.targets
  sound := by
    intro s h
    simpa only [List.any_eq_true, decide_eq_true_eq] using h

def rejectMeaning : Meaning where
  check := fun _ => false
  holds := fun _ => False
  sound := by intro s h; cases h

def checkedFrontier (declared : Finset Nat) (catalog : Nat → Meaning)
    (s : ObservationState) : Finset Nat :=
  declared.filter (fun t => (catalog t).check s = true)

theorem checked_frontier_sound (declared : Finset Nat) (catalog : Nat → Meaning)
    (s : ObservationState) {task : Nat}
    (member : task ∈ checkedFrontier declared catalog s) : (catalog task).holds s := by
  exact (catalog task).sound s (Finset.mem_filter.mp member).2

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

-- Supplies the ACTUAL frontier/solves/frontierSound fields of the immutable root.
-- All other kernel fields and their adequacy remain obligations of the caller.
def attachTaskSemantics
    {State Update BaseCertificate Protected ResidualIndex Generator Proposal PackageHash : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → ObservationState) (declared : State → Finset Nat)
    (catalog : Nat → Meaning) :
    Learned.FrontierKernel (Task := Nat) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base :=
  { other with
    frontier := fun s => checkedFrontier (declared s) catalog (observe s)
    solves := fun s task => (catalog task).holds (observe s)
    frontierSound := by
      intro s task member
      exact checked_frontier_sound (declared s) catalog (observe s) member }

theorem attached_root_frontier_sound
    {State Update BaseCertificate Protected ResidualIndex Generator Proposal PackageHash : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → ObservationState) (declared : State → Finset Nat)
    (catalog : Nat → Meaning) {s : State} {task : Nat}
    (member : task ∈ (attachTaskSemantics other observe declared catalog).frontier s) :
    (attachTaskSemantics other observe declared catalog).solves s task :=
  (attachTaskSemantics other observe declared catalog).frontierSound member

end Phase17TaskMeaning

/- This template is appended after the pinned, regenerated typed/task/provenance
   source bodies. It does not import a historical successful result as evidence.
   All remaining base, goal, resource and information premises stay explicit. -/
namespace Phase17Joint

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

/-- One kernel receives both adapters, rather than two unrelated kernels. -/
def compose
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView) :=
  Phase17Provenance.attachProvenance
    (Phase17TaskMeaning.attachTaskSemantics other observeTasks declared catalog)
    context candidateView

theorem composed_frontier_sound
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView)
    {s : State} {task : Nat}
    (member : task ∈ (compose other observeTasks declared catalog context candidateView).frontier s) :
    (catalog task).holds (observeTasks s) :=
  (compose other observeTasks declared catalog context candidateView).frontierSound member

theorem composed_provenance_bound
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView)
    (s : State) (p : Phase17Provenance.Proposal)
    (valid : Phase17Provenance.ContextValid (context s))
    (produced : Phase17Provenance.Produced (context s) p) :
    (compose other observeTasks declared catalog context candidateView).generatorBound s (context s).generator ∧
    (compose other observeTasks declared catalog context candidateView).proposalProducedBy
      (context s).generator s p :=
  ⟨⟨rfl, valid⟩, ⟨rfl, produced⟩⟩

/-- Composition does not replace open semantic/resource fields with constants. -/
theorem remaining_semantics_unchanged
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView) :
    (compose other observeTasks declared catalog context candidateView).goalDrift = other.goalDrift ∧
    (compose other observeTasks declared catalog context candidateView).goalDriftBudget = other.goalDriftBudget ∧
    (compose other observeTasks declared catalog context candidateView).resourceUsed = other.resourceUsed ∧
    (compose other observeTasks declared catalog context candidateView).resourceBudget = other.resourceBudget ∧
    (compose other observeTasks declared catalog context candidateView).informationValue = other.informationValue ∧
    (compose other observeTasks declared catalog context candidateView).informationBudget = other.informationBudget :=
  ⟨rfl, rfl, rfl, rfl, rfl, rfl⟩

def certificate
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView)
    (s : State) (p : Phase17Provenance.Proposal) (baseCertificate : BaseCertificate) :
    Learned.CertificatePacket BaseCertificate Nat String Phase17Provenance.Proposal String :=
  { base := baseCertificate
    protectedFrontier := (compose other observeTasks declared catalog context candidateView).frontier s
    generator := (context s).generator
    proposal := p
    generatorPackageHash := (context s).parentPackage }

/-- Actual LearnedAcceptedStep constructor, CONDITIONAL on all remaining premises.
    It is not instantiated for a physical transition by this development gate. -/
theorem assemble_learned_step
    {State Update BaseCertificate Protected ResidualIndex : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) base)
    (observeTasks : State → Phase17TaskMeaning.ObservationState)
    (declared : State → Finset Nat) (catalog : Nat → Phase17TaskMeaning.Meaning)
    (context : State → Phase17Provenance.Context)
    (candidateView : RCP.Candidate State Update → Phase17Provenance.CandidateView)
    (s : State) (candidate : RCP.Candidate State Update)
    (p : Phase17Provenance.Proposal) (baseCertificate : BaseCertificate)
    (valid : Phase17Provenance.ContextValid (context s))
    (produced : Phase17Provenance.Produced (context s) p)
    (matched : Phase17Provenance.CandidateMatches (context s) p (candidateView candidate))
    (expansion : Learned.StrictFrontierExpansion
      (compose other observeTasks declared catalog context candidateView) s candidate)
    (baseProof : RCP.StepObligations base s candidate baseCertificate)
    (goal : other.goalDrift s candidate ≤ other.goalDriftBudget s candidate)
    (resources : other.resourceUsed s candidate ≤ other.resourceBudget s candidate)
    (information : other.informationValue candidate.next ≤
      other.informationValue s + other.informationBudget s candidate) :
    Learned.LearnedAcceptedStep
      (compose other observeTasks declared catalog context candidateView) s candidate
      (certificate other observeTasks declared catalog context candidateView s p baseCertificate) := by
  exact {
    baseObligations := baseProof
    learnedObligations := {
      protectedFrontierCertified := by intro task h; exact h
      protectedFrontierRetained := expansion.1
      strictFrontierExpansion := expansion
      generatorIsActive := rfl
      generatorBound := ⟨rfl, valid⟩
      proposalProduced := ⟨rfl, produced⟩
      proposalBindsCandidate := matched
      packageHashIsActive := rfl
      packageHashBound := ⟨rfl, rfl, valid⟩
      goalDriftWithinBudget := goal
      resourceWithinBudget := resources
      informationNonRegression := information } }

structure Binding where
  historicalState : String
  predecessor : String
  candidate : String
  transcript : String
  program : String
  objective : String
  challenge : String
  deriving DecidableEq

end Phase17Joint


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
  | cons row rest ih => simp [goalDistance, ih]

/- These are explicit protected-profile fields with a zero-regression policy.
   Resource fields and all capability/provenance fields are left unchanged. -/
noncomputable def attach
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal PackageHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → Observation) (contract : Contract) :
    Learned.FrontierKernel (Task := Task) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base :=
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

/- Phase 17Q: a concrete kernel for the finite observations reconstructed from one
   inactive append-only package transition.  This template is appended after the
   unchanged typed/task/provenance/protected/resource templates.

   Its state is an explicit finite observation, not an arbitrary neural machine.
   The Python/physical-to-observation refinement is an external trust boundary.
   The fixed context describes one transaction and supplies no next-turn oracle.
   The declared reference-work tariff is not total physical resource accounting.
   No autonomous accepted step or active promotion is constructed here. -/
namespace Phase17Finite

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

abbrev Program := Phase17TaskMeaning.Program
abbrev Image := Phase17LearnedBinding.Image
abbrev ProofObservation := String × String × String

/-- Complete finite projection used by this kernel.  The twelve frozen images
    retain the typed component separation; program contents and task meanings
    remain explicit data rather than a package hash or asserted success bit. -/
structure State where
  frozen : List Image
  keys : List String
  proofs : List ProofObservation
  programs : List (String × Program)
  declared : Finset Nat
  namedFrontier : Finset String
  semantic : Phase17Protected.Observation
  packageHash : String
  root : String
  deriving DecidableEq

/-- Fieldwise equality avoids reducing a proof transport inside a derived
    equality decision when independently represented finite sets are compared. -/
theorem state_ext (s t : State)
    (frozen : s.frozen = t.frozen) (keys : s.keys = t.keys)
    (proofs : s.proofs = t.proofs) (programs : s.programs = t.programs)
    (declared : s.declared = t.declared) (namedFrontier : s.namedFrontier = t.namedFrontier)
    (semantic : s.semantic = t.semantic) (packageHash : s.packageHash = t.packageHash)
    (root : s.root = t.root) : s = t := by
  cases s
  cases t
  simp only [State.mk.injEq]
  exact ⟨frozen, keys, proofs, programs, declared, namedFrontier, semantic, packageHash, root⟩

def ofObservations (root : String) (bound : Phase17LearnedBinding.BoundState)
    (tasks : Phase17TaskMeaning.ObservationState) (declared : Finset Nat)
    (semantic : Phase17Protected.Observation) : State :=
  { frozen := Phase17LearnedBinding.frozenView bound
    keys := bound.package.base
    proofs := tasks.proofs
    programs := tasks.programs
    declared := declared
    namedFrontier := bound.package.capabilityFrontier
    semantic := semantic
    packageHash := bound.packageHash
    root := root }

structure Update where
  key : String
  program : Program
  task : Nat
  taskName : String
  parentPackage : String
  candidatePackage : String
  contextHash : String
  charges : List Phase17Resource.Kind
  deriving DecidableEq

/-- Immutable interpretation, context, and work envelope for ONE transaction.
    In particular, candidate data cannot choose a new task catalog, goal target,
    producer history, root identity, or tariff to make its own checks pass. -/
structure Configuration where
  root : String
  catalog : Nat → Phase17TaskMeaning.Meaning
  taskName : Nat → String
  contract : Phase17Protected.Contract
  context : Phase17Provenance.Context
  policy : Phase17Resource.Policy
  expectedCharges : List Phase17Resource.Kind

structure Evidence where
  root : String
  parentPackage : String
  candidatePackage : String
  contextHash : String
  transcriptHash : String
  proposal : Phase17Provenance.Proposal
  charges : List Phase17Resource.Kind

def taskObservation (s : State) : Phase17TaskMeaning.ObservationState :=
  { proofs := s.proofs, programs := s.programs }

def frontier (cfg : Configuration) (s : State) : Finset Nat :=
  Phase17TaskMeaning.checkedFrontier s.declared cfg.catalog (taskObservation s)

def apply (s : State) (u : Update) : State :=
  { s with
    keys := s.keys ++ [u.key]
    programs := s.programs ++ [(u.key, u.program)]
    declared := insert u.task s.declared
    namedFrontier := insert u.taskName s.namedFrontier
    packageHash := u.candidatePackage }

/-- Candidate-tied inverse of the finite append operation.  It uses the actual
    observed successor and update metadata, not a constant predecessor oracle. -/
def recover (u : Update) (observed : State) : State :=
  { observed with
    keys := observed.keys.dropLast
    programs := observed.programs.dropLast
    declared := observed.declared.erase u.task
    namedFrontier := observed.namedFrontier.erase u.taskName
    packageHash := u.parentPackage }

abbrev Protected := List Image × List ProofObservation × Phase17Protected.Observation

def protectedView (s : State) : Protected := (s.frozen, s.proofs, s.semantic)

noncomputable def protectedValue (s : State) (p : Protected) : ℝ :=
  if protectedView s = p then 1 else 0

noncomputable def distance (s t : State) : ℝ := if s = t then 0 else 1

def admissible (cfg : Configuration) (s : State) : Prop :=
  s.root = cfg.root ∧ s.root ≠ "" ∧ s.packageHash ≠ "" ∧
  s.frozen.length = 12 ∧ s.keys = s.programs.map Prod.fst ∧ s.keys.Nodup ∧
  s.namedFrontier = s.declared.image cfg.taskName ∧ frontier cfg s = s.declared ∧
  Phase17Protected.WellFormed s.semantic ∧ s.semantic.goals = cfg.contract.expectedGoals

def UpdateValid (cfg : Configuration) (s : State) (u : Update) : Prop :=
  u.parentPackage = s.packageHash ∧ u.contextHash = cfg.context.contextHash ∧
  u.key ≠ "" ∧ u.key ∉ s.keys ∧ u.task ∉ s.declared ∧
  u.taskName ∉ s.namedFrontier ∧ u.taskName = cfg.taskName u.task ∧ u.taskName ≠ "" ∧
  u.candidatePackage ≠ s.packageHash ∧ u.candidatePackage ≠ "" ∧
  u.program.family < 8 ∧ u.program.variant < 4

def candidateView (c : RCP.Candidate State Update) : Phase17Provenance.CandidateView :=
  { parentPackage := c.update.parentPackage
    contextHash := c.update.contextHash
    program := c.update.key
    package := c.next.packageHash }

def trustValid (cfg : Configuration) (s : State) (c : RCP.Candidate State Update)
    (e : Evidence) : Prop :=
  e.root = cfg.root ∧ s.root = cfg.root ∧ c.next.root = cfg.root ∧ cfg.root ≠ "" ∧
  e.parentPackage = s.packageHash ∧ e.candidatePackage = c.next.packageHash ∧
  e.contextHash = cfg.context.contextHash ∧ e.transcriptHash = cfg.context.transcriptHash ∧
  cfg.context.parentPackage = s.packageHash ∧ cfg.context.generator ≠ "" ∧
  cfg.context.contextHash ≠ "" ∧ cfg.context.transcriptHash ≠ "" ∧
  Phase17Provenance.ContextValid cfg.context

def resourceValid (cfg : Configuration) (c : RCP.Candidate State Update) (e : Evidence) : Prop :=
  e.charges = c.update.charges ∧ e.charges = cfg.expectedCharges ∧
    Phase17Resource.Fits cfg.policy e.charges

def realityContained (cfg : Configuration) (s : State) (c : RCP.Candidate State Update)
    (e : Evidence) : Prop :=
  c.next = apply s c.update ∧ UpdateValid cfg s c.update ∧
  Phase17Provenance.CandidateMatches cfg.context e.proposal (candidateView c) ∧
  e.charges = cfg.expectedCharges

inductive ResidualIndex where
  | total
  | dimension (index : Phase17Resource.Dimension)

noncomputable def residual (cfg : Configuration) (e : Evidence) : ResidualIndex → ℝ
  | .total => (Phase17Resource.totalCost e.charges : ℝ) - (cfg.policy.costLimit : ℝ)
  | .dimension i => (Phase17Resource.counter e.charges i : ℝ) - (cfg.policy.limits i : ℝ)

private def emptyState : State :=
  ⟨[], [], [], [], ∅, ∅, ⟨[], [], []⟩, "", ""⟩

private def emptyUpdate : Update := ⟨"", ⟨0, 0, 0, 0⟩, 0, "", "", "", "", []⟩

private def emptyEvidence : Evidence :=
  ⟨"", "", "", "", "", ⟨"", "", "", "", [], [], "", ""⟩, []⟩

/-- This is an actual RCP kernel.  The protected observation indicator,
    per-dimension work residuals, and rejectable structural transition relation
    satisfy the immutable root's three anti-vacuity requirements. -/
noncomputable def base (cfg : Configuration) :
    RCP.Kernel State Update Evidence Protected ResidualIndex where
  apply := apply
  admissible := admissible cfg
  protectedInvariant := admissible cfg
  protectedValue := protectedValue
  protectedValue_nonconstant := by
    let changed : State := { emptyState with semantic := ⟨[], [], [[1]]⟩ }
    refine ⟨emptyState, protectedView emptyState, changed, protectedView emptyState, ?_⟩
    norm_num [protectedValue, protectedView, emptyState, changed]
  transportProtected := fun _ _ p => p
  lossBudget := fun _ _ => 0
  lossBudget_nonnegative := by intros; exact le_rfl
  stateDistance := distance
  stateDistance_nonnegative := by intros; unfold distance; split <;> norm_num
  recover := fun _ c observed => recover c.update observed
  recoveryBudget := fun _ _ => 0
  recoveryBudget_nonnegative := by intros; exact le_rfl
  progress := fun s => ((frontier cfg s).card : ℝ)
  strictWitness := fun s c _ => c.update.task ∉ frontier cfg s ∧ c.update.task ∈ frontier cfg c.next
  residual := fun _ _ e i => residual cfg e i
  residual_nonconstant := by
    let c : RCP.Candidate State Update := ⟨emptyUpdate, emptyState⟩
    refine ⟨emptyState, c, emptyEvidence, emptyState, c,
      { emptyEvidence with charges := [.candidate] }, .total, ?_⟩
    norm_num [residual, emptyEvidence, Phase17Resource.totalCost,
      Phase17Resource.unitCost]
    linarith
  trustValid := trustValid cfg
  resourceValid := fun _ c e => resourceValid cfg c e
  realityContained := realityContained cfg
  realityContained_not_universal := by
    refine ⟨emptyState, ⟨emptyUpdate, emptyState⟩, emptyEvidence, ?_⟩
    intro h
    have invalid := h.2.1.2.2.1
    exact invalid rfl

theorem protected_view_preserved (s : State) (u : Update) :
    protectedView (apply s u) = protectedView s := rfl

theorem exact_recovery (s : State) (u : Update)
    (parent : u.parentPackage = s.packageHash)
    (freshTask : u.task ∉ s.declared) (freshName : u.taskName ∉ s.namedFrontier) :
    recover u (apply s u) = s := by
  simp [recover, apply, freshTask, freshName, parent]

theorem residuals_nonpositive (cfg : Configuration) (e : Evidence)
    (fits : Phase17Resource.Fits cfg.policy e.charges) :
    ∀ i, residual cfg e i ≤ 0 := by
  intro i
  cases i with
  | total => exact sub_nonpos.mpr (by exact_mod_cast fits.1)
  | dimension i => exact sub_nonpos.mpr (by exact_mod_cast fits.2 i)

/-- Every learned field is supplied here; no unspecified compatible kernel is
    an argument.  Proposal authority is restricted to the fixed current parent.
    A new transaction requires a newly authenticated context, not reuse of this
    context as an implicit successor-produced history. -/
noncomputable def learned (cfg : Configuration) :
    Learned.FrontierKernel (Task := Nat) (Generator := String)
      (Proposal := Phase17Provenance.Proposal) (PackageHash := String) (base cfg) where
  frontier := frontier cfg
  solves := fun s t => (cfg.catalog t).holds (taskObservation s)
  frontierSound := by
    intro s t h
    exact Phase17TaskMeaning.checked_frontier_sound s.declared cfg.catalog (taskObservation s) h
  activeGenerator := fun _ => cfg.context.generator
  activePackageHash := fun s => s.packageHash
  generatorBound := fun s g => g = cfg.context.generator ∧
    cfg.context.parentPackage = s.packageHash ∧ Phase17Provenance.ContextValid cfg.context
  proposalProducedBy := fun g s p => g = cfg.context.generator ∧
    cfg.context.parentPackage = s.packageHash ∧ Phase17Provenance.Produced cfg.context p
  proposalBindsCandidate := fun s p c => cfg.context.parentPackage = s.packageHash ∧
    Phase17Provenance.CandidateMatches cfg.context p (candidateView c)
  packageHashBound := fun s g hash => g = cfg.context.generator ∧ hash = s.packageHash ∧
    cfg.context.parentPackage = s.packageHash ∧ Phase17Provenance.ContextValid cfg.context
  goalDrift := fun s c => Phase17Protected.goalDistance s.semantic.goals c.next.semantic.goals
  goalDriftBudget := fun _ _ => 0
  resourceUsed := fun _ c => Phase17Resource.totalCost c.update.charges
  resourceBudget := fun _ _ => cfg.policy.costLimit
  informationValue := fun s => Phase17Protected.informationValue cfg.contract s.semantic
  informationBudget := fun _ _ => 0
  informationBudget_nonnegative := by intros; exact le_rfl

/-- Finite, independently checkable conditions for one observation transition.
    These are propositions over the supplied literals, not a caller acceptance
    flag, physical-execution assertion, or a remaining abstract base kernel. -/
structure Facts (cfg : Configuration) (s : State) (c : RCP.Candidate State Update)
    (e : Evidence) : Prop where
  beforeAdmissible : admissible cfg s
  afterAdmissible : admissible cfg c.next
  typed : c.next = apply s c.update
  updateValid : UpdateValid cfg s c.update
  trusted : trustValid cfg s c e
  resources : resourceValid cfg c e
  matched : Phase17Provenance.CandidateMatches cfg.context e.proposal (candidateView c)
  expansion : frontier cfg s ⊆ frontier cfg c.next ∧
    (frontier cfg s).card < (frontier cfg c.next).card

theorem base_step (cfg : Configuration) (s : State) (c : RCP.Candidate State Update)
    (e : Evidence) (facts : Facts cfg s c e) :
    RCP.StepObligations (base cfg) s c e := by
  rcases facts.updateValid with ⟨parent, _, _, _, freshTask, freshName, _⟩
  constructor
  · exact facts.typed
  · exact residuals_nonpositive cfg e facts.resources.2.2
  · intro p
    change protectedValue s p ≤ protectedValue c.next p + 0
    rw [facts.typed]
    change protectedValue s p ≤ protectedValue s p + 0
    simpa only [add_zero] using (le_refl (protectedValue s p))
  · change distance (recover c.update c.next) s ≤ 0
    rw [facts.typed, exact_recovery s c.update parent freshTask freshName]
    simp [distance]
  · exact facts.afterAdmissible
  · change ((frontier cfg s).card : ℝ) ≤ ((frontier cfg c.next).card : ℝ)
    exact_mod_cast facts.expansion.2.le
  · intro _
    change ((frontier cfg s).card : ℝ) < ((frontier cfg c.next).card : ℝ)
    exact_mod_cast facts.expansion.2
  · exact facts.trusted
  · exact facts.resources
  · exact ⟨facts.typed, facts.updateValid, facts.matched, facts.resources.2.1⟩
  · exact facts.afterAdmissible

def packet (cfg : Configuration) (s : State) (e : Evidence) :
    Learned.CertificatePacket Evidence Nat String Phase17Provenance.Proposal String :=
  { base := e
    protectedFrontier := frontier cfg s
    generator := cfg.context.generator
    proposal := e.proposal
    generatorPackageHash := s.packageHash }

/-- Fully instantiated base and learned obligations for the stated finite model.
    Applying this theorem to measured literals still does not prove their physical
    refinement, arbitrary neural semantics, autonomous continuation, or promotion. -/
theorem accepted (cfg : Configuration) (s : State) (c : RCP.Candidate State Update)
    (e : Evidence) (facts : Facts cfg s c e) :
    Learned.LearnedAcceptedStep (learned cfg) s c (packet cfg s e) := by
  rcases facts.trusted with ⟨_, _, _, _, _, _, _, _, parent, _, _, _, contextValid⟩
  have produced : Phase17Provenance.Produced cfg.context e.proposal := facts.matched.1
  refine { baseObligations := base_step cfg s c e facts, learnedObligations := ?_ }
  constructor
  · intro t h; exact h
  · exact facts.expansion.1
  · exact facts.expansion
  · rfl
  · exact ⟨rfl, parent, contextValid⟩
  · exact ⟨rfl, parent, produced⟩
  · exact ⟨parent, facts.matched⟩
  · rfl
  · exact ⟨rfl, rfl, parent, contextValid⟩
  · change Phase17Protected.goalDistance s.semantic.goals c.next.semantic.goals ≤ 0
    rw [facts.typed]
    exact (Phase17Protected.goal_distance_self s.semantic.goals).le
  · change Phase17Resource.totalCost c.update.charges ≤ cfg.policy.costLimit
    rw [← facts.resources.1]
    exact facts.resources.2.2.1
  · change Phase17Protected.informationValue cfg.contract c.next.semantic ≤
      Phase17Protected.informationValue cfg.contract s.semantic + 0
    rw [facts.typed]
    exact le_of_eq (add_zero _).symm

theorem accepted_protected_frontier (cfg : Configuration) (s : State)
    (c : RCP.Candidate State Update) (e : Evidence) (facts : Facts cfg s c e) :
    (packet cfg s e).protectedFrontier = (learned cfg).frontier s ∧
    (learned cfg).frontier s ⊆ (learned cfg).frontier c.next ∧
    ((learned cfg).frontier s).card < ((learned cfg).frontier c.next).card :=
  ⟨rfl, facts.expansion⟩

theorem accepted_all_resource_dimensions (cfg : Configuration) (s : State)
    (c : RCP.Candidate State Update) (e : Evidence) (facts : Facts cfg s c e) :
    e.charges = c.update.charges ∧ e.charges = cfg.expectedCharges ∧
      Phase17Resource.Fits cfg.policy e.charges :=
  facts.resources

end Phase17Finite
