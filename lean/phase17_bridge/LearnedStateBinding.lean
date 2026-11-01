import RcpRclmFormalCoreV4
import Mathlib.Tactic

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
  rw [Finset.card_insert_of_not_mem fresh]
  exact Nat.lt_succ_self _

end Phase17LearnedBinding
