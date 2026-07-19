import Mathlib.Tactic.NormNum
import RcpRclmFormalCoreV2.RCLM.ClassicalBinary
import RcpRclmFormalCoreV3.Learned.Infinite

namespace RcpRclmFormalCoreV3
namespace Learned
namespace Reference

open RcpRclmFormalCoreV2
open RcpRclmFormalCoreV2.RCP
open RcpRclmFormalCoreV2.RCLM
open RcpRclmFormalCoreV2.RCLM.ClassicalBinary

inductive Task where
  | baseline
  | frontierOne
  deriving DecidableEq

inductive Generator where
  | boundedReference
  deriving DecidableEq

inductive Proposal where
  | improve
  deriving DecidableEq

inductive PackageHash where
  | root
  deriving DecidableEq

def frontier : ClassicalState → Finset Task
  | state =>
      match state.core with
      | .outside => ∅
      | .initial => { .baseline }
      | .target => { .baseline, .frontierOne }

def solves (state : ClassicalState) (task : Task) : Prop :=
  task ∈ frontier state

def generatorBound (_state : ClassicalState) (generator : Generator) : Prop :=
  generator = .boundedReference

def proposalProducedBy
    (generator : Generator)
    (state : ClassicalState)
    (proposal : Proposal) : Prop :=
  generator = .boundedReference ∧
    state = initialState ∧
    proposal = .improve

def proposalBindsCandidate
    (state : ClassicalState)
    (proposal : Proposal)
    (candidate : Candidate ClassicalState ClassicalUpdate) : Prop :=
  state = initialState ∧
    proposal = .improve ∧
    candidate.update = improvementUpdate ∧
    candidate.next = targetState

def packageHashBound
    (_state : ClassicalState)
    (_generator : Generator)
    (hash : PackageHash) : Prop :=
  hash = .root

noncomputable def informationValue (state : ClassicalState) : ℝ :=
  binaryGap - binaryProgress state.core

noncomputable def learnedKernel : FrontierKernel
    (Task := Task)
    (Generator := Generator)
    (Proposal := Proposal)
    (PackageHash := PackageHash)
    kernel where
  frontier := frontier
  solves := solves
  frontierSound := by
    intro state task member
    exact member
  activeGenerator := fun _ => .boundedReference
  activePackageHash := fun _ => .root
  generatorBound := generatorBound
  proposalProducedBy := proposalProducedBy
  proposalBindsCandidate := proposalBindsCandidate
  packageHashBound := packageHashBound
  goalDrift := fun _ _ => 0
  goalDriftBudget := fun _ _ => 0
  resourceUsed := fun _ _ => 1
  resourceBudget := fun _ _ => 1
  informationValue := informationValue
  informationBudget := fun _ _ => 0
  informationBudget_nonnegative := by
    intro state candidate
    exact le_rfl

def improvementPacket :
    CertificatePacket ClassicalCertificate Task Generator Proposal PackageHash where
  base := improvementCertificate
  protectedFrontier := { .baseline }
  generator := .boundedReference
  proposal := .improve
  generatorPackageHash := .root

def ReferencePacket
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate :
      CertificatePacket ClassicalCertificate Task Generator Proposal PackageHash) : Prop :=
  state = initialState ∧
    candidate.update = improvementUpdate ∧
    candidate.next = targetState ∧
    certificate.base = improvementCertificate ∧
    certificate.protectedFrontier = { .baseline } ∧
    certificate.generator = .boundedReference ∧
    certificate.proposal = .improve ∧
    certificate.generatorPackageHash = .root

def check
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate :
      CertificatePacket ClassicalCertificate Task Generator Proposal PackageHash) : Bool :=
  decide (ReferencePacket state candidate certificate)

theorem check_eq_true_iff
    (state : ClassicalState)
    (candidate : Candidate ClassicalState ClassicalUpdate)
    (certificate :
      CertificatePacket ClassicalCertificate Task Generator Proposal PackageHash) :
    check state candidate certificate = true ↔
      ReferencePacket state candidate certificate := by
  simp [check]

theorem reference_specific_obligations :
    SpecificObligations learnedKernel
      initialState improvementCandidate improvementPacket := by
  refine
    { protectedFrontierCertified := ?_
      protectedFrontierRetained := ?_
      strictFrontierExpansion := ?_
      generatorIsActive := ?_
      generatorBound := ?_
      proposalProduced := ?_
      proposalBindsCandidate := ?_
      packageHashIsActive := ?_
      packageHashBound := ?_
      goalDriftWithinBudget := ?_
      resourceWithinBudget := ?_
      informationNonRegression := ?_ }
  · simp [improvementPacket, learnedKernel, frontier, initialState, canonicalState]
  · simp [improvementPacket, learnedKernel, frontier, improvementCandidate,
      targetState, canonicalState]
  · constructor
    · simp [learnedKernel, frontier, initialState, targetState,
        improvementCandidate, canonicalState]
    · norm_num [learnedKernel, frontier, initialState, targetState,
        improvementCandidate, canonicalState]
  · rfl
  · rfl
  · exact ⟨rfl, rfl, rfl⟩
  · exact ⟨rfl, rfl, rfl, rfl⟩
  · rfl
  · rfl
  · exact le_rfl
  · exact le_rfl
  · change informationValue targetState ≤ informationValue initialState + 0
    rw [informationValue, informationValue]
    change binaryGap - binaryProgress .target ≤
      binaryGap - binaryProgress .initial + 0
    rw [binaryProgress_target, binaryProgress_initial]
    simpa using binaryGap_pos.le

noncomputable def checker : TrustedLearnedChecker learnedKernel ClassicalBinary.checker where
  check := check
  refinesBase := by
    intro state candidate certificate accepted
    have packet := (check_eq_true_iff state candidate certificate).1 accepted
    rcases packet with
      ⟨stateEq, updateEq, nextEq, baseEq, frontierEq, generatorEq,
        proposalEq, hashEq⟩
    subst state
    cases candidate with
    | mk update next =>
        dsimp at updateEq nextEq
        subst update
        subst next
        rw [baseEq]
        exact improvement_check_accepts
  learnedSound := by
    intro state candidate certificate stateAdmissible stateInvariant accepted
    have packet := (check_eq_true_iff state candidate certificate).1 accepted
    rcases packet with
      ⟨stateEq, updateEq, nextEq, baseEq, frontierEq, generatorEq,
        proposalEq, hashEq⟩
    subst state
    cases candidate with
    | mk update next =>
        dsimp at updateEq nextEq
        subst update
        subst next
        cases certificate with
        | mk baseCertificate protectedFrontier generator proposal packageHash =>
            dsimp at baseEq frontierEq generatorEq proposalEq hashEq
            subst baseCertificate
            subst protectedFrontier
            subst generator
            subst proposal
            subst packageHash
            exact reference_specific_obligations

theorem improvement_check_accepts_learned :
    checker.check initialState improvementCandidate improvementPacket = true := by
  rfl

theorem improvement_learned_accepted_step :
    LearnedAcceptedStep learnedKernel
      initialState improvementCandidate improvementPacket := by
  have initialAdmissible : kernel.admissible initialState := by
    constructor
    · decide
    · rfl
  have initialInvariant : kernel.protectedInvariant initialState := by
    constructor
    · decide
    · rfl
  exact learned_accepted_step_sound checker
    initialAdmissible initialInvariant improvement_check_accepts_learned

noncomputable def referenceTrajectory : FiniteLearnedTrajectory checker 1 where
  state
    | 0 => initialState
    | _ + 1 => targetState
  candidate := fun _ => improvementCandidate
  certificate := fun _ => improvementPacket
  initialAdmissible := by
    constructor
    · decide
    · rfl
  initialInvariant := by
    constructor
    · decide
    · rfl
  accepted := by
    intro t bound
    have tZero : t = 0 :=
      Nat.eq_zero_of_le_zero (Nat.le_of_lt_succ bound)
    subst t
    rfl
  linked := by
    intro t bound
    have tZero : t = 0 :=
      Nat.eq_zero_of_le_zero (Nat.le_of_lt_succ bound)
    subst t
    rfl

theorem reference_frontier_card_growth :
    (learnedKernel.frontier (referenceTrajectory.state 0)).card + 1 ≤
      (learnedKernel.frontier (referenceTrajectory.state 1)).card :=
  finite_learned_final_frontier_growth checker referenceTrajectory

end Reference
end Learned
end RcpRclmFormalCoreV3
