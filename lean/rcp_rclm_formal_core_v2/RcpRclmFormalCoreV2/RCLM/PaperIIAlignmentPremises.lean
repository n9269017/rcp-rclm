import RcpRclmFormalCoreV2.RCLM.PaperIIRobustReflective

namespace RcpRclmFormalCoreV2
namespace RCLM

structure PaperIIUncertaintyEnvelopeSemantics
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {VerifierSchema UncertaintyEnvelope Goal : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (successorSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine) where
  stateEnvelope : State → UncertaintyEnvelope
  transportEnvelope :
    State → RCP.Candidate State Update → UncertaintyEnvelope → UncertaintyEnvelope
  envelopeRefines : UncertaintyEnvelope → UncertaintyEnvelope → Prop
  envelopeReflexive : ∀ envelope, envelopeRefines envelope envelope
  envelopeTransitive :
    ∀ {first second third},
      envelopeRefines first second →
      envelopeRefines second third →
      envelopeRefines first third
  transportMonotone :
    ∀ state candidate {first second},
      envelopeRefines first second →
      envelopeRefines
        (transportEnvelope state candidate first)
        (transportEnvelope state candidate second)
  oneStepPersistence :
    ∀ {state candidate certificate},
      RCP.StepObligations kernel state candidate certificate →
      envelopeRefines
        (transportEnvelope state candidate (stateEnvelope state))
        (stateEnvelope candidate.next)

structure PaperIIDomainSemantics
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker) where
  directEngineDomain : State → Prop
  seedLibraryDomain : State → Prop
  successorVerificationDomain : State → Prop
  directEngineDomain_to_architectureDomain :
    ∀ {state}, directEngineDomain state → engine.domain state
  seedLibraryDomain_to_directEngineDomain :
    ∀ {state}, seedLibraryDomain state → directEngineDomain state
  seedLibraryDomain_to_successorVerificationDomain :
    ∀ {state}, seedLibraryDomain state → successorVerificationDomain state
  architectureDomain_to_successorVerificationDomain :
    ∀ {state}, engine.domain state → successorVerificationDomain state

structure PaperIIClaimScope where
  realWorldReliabilityClaimed : Prop
  computationalTractabilityClaimed : Prop

structure PaperIIOptionalClaimCertificates
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {VerifierSchema UncertaintyEnvelope Goal : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    {successorSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine}
    (scope : PaperIIClaimScope)
    (state : State)
    (candidate : RCP.Candidate State Update)
    (certificate : Certificate) : Prop where
  realityWhenClaimed :
    scope.realWorldReliabilityClaimed →
      successorSemantics.realityCertificate state candidate certificate
  tractabilityWhenClaimed :
    scope.computationalTractabilityClaimed →
      successorSemantics.tractabilityCertificate state candidate certificate

structure PaperIIBorelCantelliPremise
    (failureRisk : Nat → ℝ) where
  World : Type*
  Failure : Nat → World → Prop
  AlmostEverywhere : (World → Prop) → Prop
  firstBorelCantelli :
    Summable failureRisk →
      AlmostEverywhere fun world =>
        ∃ cutoff, ∀ t, cutoff ≤ t → ¬ Failure t world

def transportedPaperIIUncertaintyEnvelope
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {VerifierSchema UncertaintyEnvelope Goal : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    {horizon : Nat}
    {successorSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine}
    (uncertaintySemantics :
      PaperIIUncertaintyEnvelopeSemantics successorSemantics)
    (trajectory : RCP.FiniteAcceptedTrajectory checker horizon) :
    Nat → UncertaintyEnvelope → UncertaintyEnvelope
  | 0, envelope => envelope
  | t + 1, envelope =>
      uncertaintySemantics.transportEnvelope
        (trajectory.state t)
        (trajectory.candidate t)
        (transportedPaperIIUncertaintyEnvelope
          uncertaintySemantics trajectory t envelope)

theorem transportedPaperIIUncertaintyEnvelope_monotone
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {VerifierSchema UncertaintyEnvelope Goal : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    {horizon : Nat}
    {successorSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine}
    (uncertaintySemantics :
      PaperIIUncertaintyEnvelopeSemantics successorSemantics)
    (trajectory : RCP.FiniteAcceptedTrajectory checker horizon) :
    ∀ t {first second},
      uncertaintySemantics.envelopeRefines first second →
      uncertaintySemantics.envelopeRefines
        (transportedPaperIIUncertaintyEnvelope
          uncertaintySemantics trajectory t first)
        (transportedPaperIIUncertaintyEnvelope
          uncertaintySemantics trajectory t second) := by
  intro t
  induction t with
  | zero =>
      intro first second refinement
      exact refinement
  | succ t inductionHypothesis =>
      intro first second refinement
      have previousRefinement :
          uncertaintySemantics.envelopeRefines
            (transportedPaperIIUncertaintyEnvelope
              uncertaintySemantics trajectory t first)
            (transportedPaperIIUncertaintyEnvelope
              uncertaintySemantics trajectory t second) :=
        inductionHypothesis refinement
      exact uncertaintySemantics.transportMonotone
        (trajectory.state t)
        (trajectory.candidate t)
        previousRefinement

theorem finite_paper_ii_uncertainty_envelope_persistence
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {VerifierSchema UncertaintyEnvelope Goal : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    {horizon : Nat}
    {successorSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine}
    (uncertaintySemantics :
      PaperIIUncertaintyEnvelopeSemantics successorSemantics)
    (trajectory : RCP.FiniteAcceptedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      uncertaintySemantics.envelopeRefines
        (transportedPaperIIUncertaintyEnvelope
          uncertaintySemantics trajectory t
          (uncertaintySemantics.stateEnvelope (trajectory.state 0)))
        (uncertaintySemantics.stateEnvelope (trajectory.state t)) := by
  intro t
  induction t with
  | zero =>
      intro _
      exact uncertaintySemantics.envelopeReflexive _
  | succ t inductionHypothesis =>
      intro bound
      have stepIndexBound : t < horizon := Nat.lt_of_succ_le bound
      have previousBound : t ≤ horizon :=
        Nat.le_trans (Nat.le_succ t) bound
      have previousPersistence := inductionHypothesis previousBound
      have transportedPrevious :
          uncertaintySemantics.envelopeRefines
            (uncertaintySemantics.transportEnvelope
              (trajectory.state t)
              (trajectory.candidate t)
              (transportedPaperIIUncertaintyEnvelope
                uncertaintySemantics trajectory t
                (uncertaintySemantics.stateEnvelope (trajectory.state 0))))
            (uncertaintySemantics.transportEnvelope
              (trajectory.state t)
              (trajectory.candidate t)
              (uncertaintySemantics.stateEnvelope (trajectory.state t))) :=
        uncertaintySemantics.transportMonotone
          (trajectory.state t)
          (trajectory.candidate t)
          previousPersistence
      have obligations :=
        RCP.finite_trajectory_step_sound checker trajectory t stepIndexBound
      have currentStep :
          uncertaintySemantics.envelopeRefines
            (uncertaintySemantics.transportEnvelope
              (trajectory.state t)
              (trajectory.candidate t)
              (uncertaintySemantics.stateEnvelope (trajectory.state t)))
            (uncertaintySemantics.stateEnvelope (trajectory.state (t + 1))) := by
        have localStep := uncertaintySemantics.oneStepPersistence obligations
        rw [← trajectory.linked t stepIndexBound] at localStep
        exact localStep
      exact uncertaintySemantics.envelopeTransitive
        transportedPrevious currentStep

theorem paper_ii_optional_claim_certificates
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {VerifierSchema UncertaintyEnvelope Goal : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    {successorSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine}
    (scope : PaperIIClaimScope)
    {state : State}
    {candidate : RCP.Candidate State Update}
    {certificate : Certificate}
    (obligations : PaperIISuccessorVerificationObligations
      successorSemantics state candidate certificate) :
    PaperIIOptionalClaimCertificates
      scope state candidate certificate := by
  exact
    { realityWhenClaimed := fun _ => obligations.realityCertificate
      tractabilityWhenClaimed := fun _ => obligations.tractabilityCertificate }

theorem paper_ii_almost_sure_finitely_many_failures
    {failureRisk : Nat → ℝ}
    (premise : PaperIIBorelCantelliPremise failureRisk)
    (summableRisk : Summable failureRisk) :
    premise.AlmostEverywhere fun world =>
      ∃ cutoff, ∀ t, cutoff ≤ t → ¬ premise.Failure t world :=
  premise.firstBorelCantelli summableRisk

structure PaperIIAlignedInfiniteResult
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {VerifierSchema UncertaintyEnvelope Goal : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (directSemantics : PaperIIDirectEngineSemantics engine)
    (successorSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (uncertaintySemantics :
      PaperIIUncertaintyEnvelopeSemantics successorSemantics)
    (domainSemantics : PaperIIDomainSemantics engine)
    (trajectory : InfiniteArchitectureTrajectory engine) : Prop where
  robustReflective :
    PaperIIInfiniteRobustReflectiveResult
      directSemantics successorSemantics trajectory
  successorVerificationDomain : ∀ t,
    domainSemantics.successorVerificationDomain
      (trajectory.predecessor t).state
  uncertaintyEnvelopePersistence : ∀ horizon,
    uncertaintySemantics.envelopeRefines
      (transportedPaperIIUncertaintyEnvelope
        uncertaintySemantics
        (RCP.finitePrefixOfInfinite
          (InfiniteArchitectureTrajectory.toAcceptedTrajectory trajectory)
          horizon)
        horizon
        (uncertaintySemantics.stateEnvelope
          (trajectory.predecessor 0).state))
      (uncertaintySemantics.stateEnvelope
        (trajectory.predecessor horizon).state)

theorem paper_ii_aligned_infinite_result
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {VerifierSchema UncertaintyEnvelope Goal : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    {engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker}
    (directSemantics : PaperIIDirectEngineSemantics engine)
    (successorSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (uncertaintySemantics :
      PaperIIUncertaintyEnvelopeSemantics successorSemantics)
    (domainSemantics : PaperIIDomainSemantics engine)
    (trajectory : InfiniteArchitectureTrajectory engine)
    (budgets : PaperIIInfiniteBudgetAssumptions
      successorSemantics trajectory) :
    PaperIIAlignedInfiniteResult
      directSemantics successorSemantics uncertaintySemantics
      domainSemantics trajectory := by
  have robustReflective :
      PaperIIInfiniteRobustReflectiveResult
        directSemantics successorSemantics trajectory :=
    paper_ii_infinite_robust_reflective_result
      directSemantics successorSemantics trajectory budgets
  refine
    { robustReflective := robustReflective
      successorVerificationDomain := ?_
      uncertaintyEnvelopePersistence := ?_ }
  · intro t
    exact domainSemantics.architectureDomain_to_successorVerificationDomain
      (trajectory.predecessor t).domainValid
  · intro horizon
    have bound : horizon ≤ horizon := Nat.le_refl horizon
    exact finite_paper_ii_uncertainty_envelope_persistence
      uncertaintySemantics
      (RCP.finitePrefixOfInfinite
        (InfiniteArchitectureTrajectory.toAcceptedTrajectory trajectory)
        horizon)
      horizon
      bound

theorem conditional_infinite_paper_ii_aligned_trajectory_exists
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {VerifierSchema UncertaintyEnvelope Goal : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker)
    (directSemantics : PaperIIDirectEngineSemantics engine)
    (successorSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (uncertaintySemantics :
      PaperIIUncertaintyEnvelopeSemantics successorSemantics)
    (domainSemantics : PaperIIDomainSemantics engine)
    (availability : ArchitectureSuccessorAvailability engine)
    (initial : ArchitecturePredecessor engine)
    (initialSeedLibraryDomain :
      domainSemantics.seedLibraryDomain initial.state)
    (budgets : PaperIIInfiniteBudgetAssumptions
      successorSemantics
      (buildInfiniteArchitectureTrajectory engine availability initial)) :
    ∃ trajectory : InfiniteArchitectureTrajectory engine,
      trajectory.predecessor 0 = initial ∧
      domainSemantics.seedLibraryDomain
        (trajectory.predecessor 0).state ∧
      PaperIIAlignedInfiniteResult
        directSemantics successorSemantics uncertaintySemantics
        domainSemantics trajectory := by
  let trajectory :=
    buildInfiniteArchitectureTrajectory engine availability initial
  have initialEquality : trajectory.predecessor 0 = initial := rfl
  have initialSeed :
      domainSemantics.seedLibraryDomain
        (trajectory.predecessor 0).state := by
    rw [initialEquality]
    exact initialSeedLibraryDomain
  have alignedResult :
      PaperIIAlignedInfiniteResult
        directSemantics successorSemantics uncertaintySemantics
        domainSemantics trajectory :=
    paper_ii_aligned_infinite_result
      directSemantics successorSemantics uncertaintySemantics
      domainSemantics trajectory budgets
  exact ⟨trajectory, initialEquality, initialSeed, alignedResult⟩

end RCLM
end RcpRclmFormalCoreV2
