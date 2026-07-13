import RcpRclmFormalCoreV2.RCLM.PaperIIDirectEngine
import RcpRclmFormalCoreV2.RCP.Summability

namespace RcpRclmFormalCoreV2
namespace RCLM

structure PaperIISuccessorVerificationSemantics
    {State Update Certificate Protected ResidualIndex Proposal Witness TrustAnchor ResourceRecord : Type*}
    {VerifierSchema UncertaintyEnvelope Goal : Type*}
    {kernel : RCP.Kernel State Update Certificate Protected ResidualIndex}
    {checker : RCP.TrustedChecker kernel}
    (engine : ArchitectureEngine
      (Proposal := Proposal)
      (Witness := Witness)
      (TrustAnchor := TrustAnchor)
      (ResourceRecord := ResourceRecord)
      kernel checker) where
  packetConstructed :
    State → RCP.Candidate State Update → Certificate → Prop
  stateVerifierSchema : State → VerifierSchema
  transportVerifierSchema :
    State → RCP.Candidate State Update → VerifierSchema → VerifierSchema
  verifierSchemaRefines : VerifierSchema → VerifierSchema → Prop
  verifierSchemaReflexive : ∀ schema, verifierSchemaRefines schema schema
  verifierSchemaTransitive :
    ∀ {first second third},
      verifierSchemaRefines first second →
      verifierSchemaRefines second third →
      verifierSchemaRefines first third
  verifierSchemaTransportMonotone :
    ∀ state candidate {first second},
      verifierSchemaRefines first second →
      verifierSchemaRefines
        (transportVerifierSchema state candidate first)
        (transportVerifierSchema state candidate second)
  uncertaintyTransportValid :
    State → RCP.Candidate State Update → Certificate → Prop
  stateGoal : State → Goal
  transportGoal : State → RCP.Candidate State Update → Goal → Goal
  goalDistance : Goal → Goal → ℝ
  goalDistance_nonnegative : ∀ first second, 0 ≤ goalDistance first second
  goalDistance_self : ∀ goal, goalDistance goal goal = 0
  goalDistance_triangle :
    ∀ first second third,
      goalDistance first third ≤
        goalDistance first second + goalDistance second third
  goalTransportNonexpansive :
    ∀ state candidate first second,
      goalDistance
          (transportGoal state candidate first)
          (transportGoal state candidate second) ≤
        goalDistance first second
  goalDriftBudget :
    State → RCP.Candidate State Update → Certificate → ℝ
  goalDriftBudget_nonnegative :
    ∀ state candidate certificate,
      0 ≤ goalDriftBudget state candidate certificate
  antiCircularTrust :
    State → RCP.Candidate State Update → Certificate → Prop
  proofBudgetValid :
    State → RCP.Candidate State Update → Certificate → Prop
  successorPersistent :
    State → RCP.Candidate State Update → Certificate → Prop
  realityCertificate :
    State → RCP.Candidate State Update → Certificate → Prop
  tractabilityCertificate :
    State → RCP.Candidate State Update → Certificate → Prop
  soundnessFailureRisk :
    State → RCP.Candidate State Update → Certificate → ℝ
  soundnessFailureRisk_nonnegative :
    ∀ state candidate certificate,
      0 ≤ soundnessFailureRisk state candidate certificate
  packetConstructed_of_engine :
    ∀ {state proposal certificate candidate},
      engine.constructsCertificate state proposal certificate →
      engine.selectsCandidate state proposal certificate candidate →
      packetConstructed state candidate certificate
  verifierSchema_step_of_obligations :
    ∀ {state candidate certificate},
      RCP.StepObligations kernel state candidate certificate →
      verifierSchemaRefines
        (transportVerifierSchema
          state candidate (stateVerifierSchema state))
        (stateVerifierSchema candidate.next)
  uncertaintyTransportValid_of_obligations :
    ∀ {state candidate certificate},
      RCP.StepObligations kernel state candidate certificate →
      uncertaintyTransportValid state candidate certificate
  goalIdentity_of_obligations :
    ∀ {state candidate certificate},
      RCP.StepObligations kernel state candidate certificate →
      goalDistance
          (stateGoal candidate.next)
          (transportGoal state candidate (stateGoal state)) ≤
        goalDriftBudget state candidate certificate
  antiCircularTrust_of_obligations :
    ∀ {state candidate certificate},
      RCP.StepObligations kernel state candidate certificate →
      antiCircularTrust state candidate certificate
  proofBudgetValid_of_obligations :
    ∀ {state candidate certificate},
      RCP.StepObligations kernel state candidate certificate →
      proofBudgetValid state candidate certificate
  successorPersistent_of_domain :
    ∀ {state candidate certificate},
      engine.domain candidate.next →
      successorPersistent state candidate certificate
  realityCertificate_of_obligations :
    ∀ {state candidate certificate},
      RCP.StepObligations kernel state candidate certificate →
      realityCertificate state candidate certificate
  tractabilityCertificate_of_resource :
    ∀ {state proposal certificate candidate resource},
      engine.resourcePremise
        state proposal certificate candidate resource →
      tractabilityCertificate state candidate certificate

structure PaperIISuccessorVerificationObligations
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
    (semantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (state : State)
    (candidate : RCP.Candidate State Update)
    (certificate : Certificate) : Prop where
  packetConstructed : semantics.packetConstructed state candidate certificate
  explicitResidualsNonpositive :
    ∀ index, kernel.residual state candidate certificate index ≤ 0
  verifierSchemaPreserved :
    semantics.verifierSchemaRefines
      (semantics.transportVerifierSchema
        state candidate (semantics.stateVerifierSchema state))
      (semantics.stateVerifierSchema candidate.next)
  uncertaintyTransportValid :
    semantics.uncertaintyTransportValid state candidate certificate
  goalIdentityBound :
    semantics.goalDistance
        (semantics.stateGoal candidate.next)
        (semantics.transportGoal
          state candidate (semantics.stateGoal state)) ≤
      semantics.goalDriftBudget state candidate certificate
  antiCircularTrust : semantics.antiCircularTrust state candidate certificate
  proofBudgetValid : semantics.proofBudgetValid state candidate certificate
  successorPersistent : semantics.successorPersistent state candidate certificate
  realityCertificate : semantics.realityCertificate state candidate certificate
  tractabilityCertificate :
    semantics.tractabilityCertificate state candidate certificate

theorem paper_ii_successor_verification_obligations
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
    (semantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    {state : State}
    (step : ArchitectureEngineStep engine state)
    (obligations :
      RCP.StepObligations kernel state step.candidate step.certificate)
    (successorDomain : engine.domain step.candidate.next) :
    PaperIISuccessorVerificationObligations
      semantics state step.candidate step.certificate := by
  have packetConstructed :
      semantics.packetConstructed
        state step.candidate step.certificate :=
    semantics.packetConstructed_of_engine
      step.certificateConstructed step.candidateSelected
  have verifierSchemaPreserved :
      semantics.verifierSchemaRefines
        (semantics.transportVerifierSchema
          state step.candidate (semantics.stateVerifierSchema state))
        (semantics.stateVerifierSchema step.candidate.next) :=
    semantics.verifierSchema_step_of_obligations obligations
  have uncertaintyTransportValid :
      semantics.uncertaintyTransportValid
        state step.candidate step.certificate :=
    semantics.uncertaintyTransportValid_of_obligations obligations
  have goalIdentityBound :
      semantics.goalDistance
          (semantics.stateGoal step.candidate.next)
          (semantics.transportGoal
            state step.candidate (semantics.stateGoal state)) ≤
        semantics.goalDriftBudget
          state step.candidate step.certificate :=
    semantics.goalIdentity_of_obligations obligations
  have antiCircularTrust :
      semantics.antiCircularTrust state step.candidate step.certificate :=
    semantics.antiCircularTrust_of_obligations obligations
  have proofBudgetValid :
      semantics.proofBudgetValid state step.candidate step.certificate :=
    semantics.proofBudgetValid_of_obligations obligations
  have successorPersistent :
      semantics.successorPersistent state step.candidate step.certificate :=
    semantics.successorPersistent_of_domain successorDomain
  have realityCertificate :
      semantics.realityCertificate state step.candidate step.certificate :=
    semantics.realityCertificate_of_obligations obligations
  have tractabilityCertificate :
      semantics.tractabilityCertificate
        state step.candidate step.certificate :=
    semantics.tractabilityCertificate_of_resource step.resourceAuthorized
  exact
    { packetConstructed := packetConstructed
      explicitResidualsNonpositive := obligations.residualsNonpositive
      verifierSchemaPreserved := verifierSchemaPreserved
      uncertaintyTransportValid := uncertaintyTransportValid
      goalIdentityBound := goalIdentityBound
      antiCircularTrust := antiCircularTrust
      proofBudgetValid := proofBudgetValid
      successorPersistent := successorPersistent
      realityCertificate := realityCertificate
      tractabilityCertificate := tractabilityCertificate }

def transportedPaperIIVerifierSchema
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
    (semantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (trajectory : RCP.FiniteAcceptedTrajectory checker horizon) :
    Nat → VerifierSchema → VerifierSchema
  | 0, schema => schema
  | t + 1, schema =>
      semantics.transportVerifierSchema
        (trajectory.state t)
        (trajectory.candidate t)
        (transportedPaperIIVerifierSchema semantics trajectory t schema)

def transportedPaperIIGoal
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
    (semantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (trajectory : RCP.FiniteAcceptedTrajectory checker horizon) :
    Nat → Goal → Goal
  | 0, goal => goal
  | t + 1, goal =>
      semantics.transportGoal
        (trajectory.state t)
        (trajectory.candidate t)
        (transportedPaperIIGoal semantics trajectory t goal)

def cumulativePaperIIGoalDriftBudget
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
    (semantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (trajectory : RCP.FiniteAcceptedTrajectory checker horizon) : Nat → ℝ
  | 0 => 0
  | t + 1 =>
      semantics.goalDriftBudget
          (trajectory.state t)
          (trajectory.candidate t)
          (trajectory.certificate t) +
        cumulativePaperIIGoalDriftBudget semantics trajectory t

def cumulativePaperIISoundnessFailureRisk
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
    (semantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (trajectory : RCP.FiniteAcceptedTrajectory checker horizon) : Nat → ℝ
  | 0 => 0
  | t + 1 =>
      semantics.soundnessFailureRisk
          (trajectory.state t)
          (trajectory.candidate t)
          (trajectory.certificate t) +
        cumulativePaperIISoundnessFailureRisk semantics trajectory t

theorem transportedPaperIIVerifierSchema_monotone
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
    (semantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (trajectory : RCP.FiniteAcceptedTrajectory checker horizon) :
    ∀ t {first second},
      semantics.verifierSchemaRefines first second →
      semantics.verifierSchemaRefines
        (transportedPaperIIVerifierSchema semantics trajectory t first)
        (transportedPaperIIVerifierSchema semantics trajectory t second) := by
  intro t
  induction t with
  | zero =>
      intro first second refinement
      exact refinement
  | succ t inductionHypothesis =>
      intro first second refinement
      have transportedRefinement :
          semantics.verifierSchemaRefines
            (transportedPaperIIVerifierSchema semantics trajectory t first)
            (transportedPaperIIVerifierSchema semantics trajectory t second) :=
        inductionHypothesis refinement
      exact semantics.verifierSchemaTransportMonotone
        (trajectory.state t)
        (trajectory.candidate t)
        transportedRefinement

theorem transportedPaperIIGoal_nonexpansive
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
    (semantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (trajectory : RCP.FiniteAcceptedTrajectory checker horizon) :
    ∀ t first second,
      semantics.goalDistance
          (transportedPaperIIGoal semantics trajectory t first)
          (transportedPaperIIGoal semantics trajectory t second) ≤
        semantics.goalDistance first second := by
  intro t
  induction t with
  | zero =>
      intro first second
      exact le_rfl
  | succ t inductionHypothesis =>
      intro first second
      have previousBound :
          semantics.goalDistance
              (transportedPaperIIGoal semantics trajectory t first)
              (transportedPaperIIGoal semantics trajectory t second) ≤
            semantics.goalDistance first second :=
        inductionHypothesis first second
      have stepBound :
          semantics.goalDistance
              (semantics.transportGoal
                (trajectory.state t)
                (trajectory.candidate t)
                (transportedPaperIIGoal semantics trajectory t first))
              (semantics.transportGoal
                (trajectory.state t)
                (trajectory.candidate t)
                (transportedPaperIIGoal semantics trajectory t second)) ≤
            semantics.goalDistance
              (transportedPaperIIGoal semantics trajectory t first)
              (transportedPaperIIGoal semantics trajectory t second) :=
        semantics.goalTransportNonexpansive
          (trajectory.state t)
          (trajectory.candidate t)
          (transportedPaperIIGoal semantics trajectory t first)
          (transportedPaperIIGoal semantics trajectory t second)
      exact le_trans stepBound previousBound

theorem finite_paper_ii_verifier_schema_persistence
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
    (semantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (trajectory : RCP.FiniteAcceptedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      semantics.verifierSchemaRefines
        (transportedPaperIIVerifierSchema
          semantics trajectory t
          (semantics.stateVerifierSchema (trajectory.state 0)))
        (semantics.stateVerifierSchema (trajectory.state t)) := by
  intro t
  induction t with
  | zero =>
      intro _
      exact semantics.verifierSchemaReflexive _
  | succ t inductionHypothesis =>
      intro bound
      have stepIndexBound : t < horizon := Nat.lt_of_succ_le bound
      have previousBound : t ≤ horizon := Nat.le_trans (Nat.le_succ t) bound
      have previousPersistence := inductionHypothesis previousBound
      have transportedPrevious :
          semantics.verifierSchemaRefines
            (semantics.transportVerifierSchema
              (trajectory.state t)
              (trajectory.candidate t)
              (transportedPaperIIVerifierSchema
                semantics trajectory t
                (semantics.stateVerifierSchema (trajectory.state 0))))
            (semantics.transportVerifierSchema
              (trajectory.state t)
              (trajectory.candidate t)
              (semantics.stateVerifierSchema (trajectory.state t))) :=
        semantics.verifierSchemaTransportMonotone
          (trajectory.state t)
          (trajectory.candidate t)
          previousPersistence
      have obligations :=
        RCP.finite_trajectory_step_sound checker trajectory t stepIndexBound
      have currentStep :
          semantics.verifierSchemaRefines
            (semantics.transportVerifierSchema
              (trajectory.state t)
              (trajectory.candidate t)
              (semantics.stateVerifierSchema (trajectory.state t)))
            (semantics.stateVerifierSchema (trajectory.state (t + 1))) := by
        have localStep :=
          semantics.verifierSchema_step_of_obligations obligations
        rw [← trajectory.linked t stepIndexBound] at localStep
        exact localStep
      exact semantics.verifierSchemaTransitive
        transportedPrevious currentStep

theorem finite_paper_ii_goal_identity_bound
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
    (semantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (trajectory : RCP.FiniteAcceptedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      semantics.goalDistance
          (semantics.stateGoal (trajectory.state t))
          (transportedPaperIIGoal
            semantics trajectory t
            (semantics.stateGoal (trajectory.state 0))) ≤
        cumulativePaperIIGoalDriftBudget semantics trajectory t := by
  intro t
  induction t with
  | zero =>
      intro _
      have selfZero := semantics.goalDistance_self
        (semantics.stateGoal (trajectory.state 0))
      simpa [transportedPaperIIGoal, cumulativePaperIIGoalDriftBudget] using
        (le_of_eq selfZero)
  | succ t inductionHypothesis =>
      intro bound
      have stepIndexBound : t < horizon := Nat.lt_of_succ_le bound
      have previousBound : t ≤ horizon := Nat.le_trans (Nat.le_succ t) bound
      have previousGoalBound := inductionHypothesis previousBound
      have obligations :=
        RCP.finite_trajectory_step_sound checker trajectory t stepIndexBound
      have currentStep :
          semantics.goalDistance
              (semantics.stateGoal (trajectory.state (t + 1)))
              (semantics.transportGoal
                (trajectory.state t)
                (trajectory.candidate t)
                (semantics.stateGoal (trajectory.state t))) ≤
            semantics.goalDriftBudget
              (trajectory.state t)
              (trajectory.candidate t)
              (trajectory.certificate t) := by
        have localStep := semantics.goalIdentity_of_obligations obligations
        rw [← trajectory.linked t stepIndexBound] at localStep
        exact localStep
      have transportedPrevious :
          semantics.goalDistance
              (semantics.transportGoal
                (trajectory.state t)
                (trajectory.candidate t)
                (semantics.stateGoal (trajectory.state t)))
              (semantics.transportGoal
                (trajectory.state t)
                (trajectory.candidate t)
                (transportedPaperIIGoal
                  semantics trajectory t
                  (semantics.stateGoal (trajectory.state 0)))) ≤
            cumulativePaperIIGoalDriftBudget semantics trajectory t := by
        have nonexpansive := semantics.goalTransportNonexpansive
          (trajectory.state t)
          (trajectory.candidate t)
          (semantics.stateGoal (trajectory.state t))
          (transportedPaperIIGoal
            semantics trajectory t
            (semantics.stateGoal (trajectory.state 0)))
        exact le_trans nonexpansive previousGoalBound
      have triangle := semantics.goalDistance_triangle
        (semantics.stateGoal (trajectory.state (t + 1)))
        (semantics.transportGoal
          (trajectory.state t)
          (trajectory.candidate t)
          (semantics.stateGoal (trajectory.state t)))
        (semantics.transportGoal
          (trajectory.state t)
          (trajectory.candidate t)
          (transportedPaperIIGoal
            semantics trajectory t
            (semantics.stateGoal (trajectory.state 0))))
      calc
        semantics.goalDistance
            (semantics.stateGoal (trajectory.state (t + 1)))
            (transportedPaperIIGoal
              semantics trajectory (t + 1)
              (semantics.stateGoal (trajectory.state 0))) ≤
          semantics.goalDistance
              (semantics.stateGoal (trajectory.state (t + 1)))
              (semantics.transportGoal
                (trajectory.state t)
                (trajectory.candidate t)
                (semantics.stateGoal (trajectory.state t))) +
            semantics.goalDistance
              (semantics.transportGoal
                (trajectory.state t)
                (trajectory.candidate t)
                (semantics.stateGoal (trajectory.state t)))
              (semantics.transportGoal
                (trajectory.state t)
                (trajectory.candidate t)
                (transportedPaperIIGoal
                  semantics trajectory t
                  (semantics.stateGoal (trajectory.state 0)))) := triangle
        _ ≤ semantics.goalDriftBudget
              (trajectory.state t)
              (trajectory.candidate t)
              (trajectory.certificate t) +
            cumulativePaperIIGoalDriftBudget semantics trajectory t :=
          add_le_add currentStep transportedPrevious
        _ = cumulativePaperIIGoalDriftBudget
              semantics trajectory (t + 1) := by rfl

structure PaperIIInfiniteBudgetAssumptions
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
    (semantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (trajectory : InfiniteArchitectureTrajectory engine) : Prop where
  goalDrift : Summable fun t =>
    semantics.goalDriftBudget
      (trajectory.predecessor t).state
      (trajectory.step t).candidate
      (trajectory.step t).certificate
  soundnessFailure : Summable fun t =>
    semantics.soundnessFailureRisk
      (trajectory.predecessor t).state
      (trajectory.step t).candidate
      (trajectory.step t).certificate

structure PaperIIInfiniteRobustReflectiveResult
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
    (svSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (trajectory : InfiniteArchitectureTrajectory engine) : Prop where
  successorVerification : ∀ t,
    PaperIISuccessorVerificationObligations
      svSemantics
      (trajectory.predecessor t).state
      (trajectory.step t).candidate
      (trajectory.step t).certificate
  candidateNonLossy : ∀ t,
    directSemantics.nonLossyCandidate
      (trajectory.predecessor t).state
      (trajectory.step t).candidate
  algebraicGate : ∀ t,
    directSemantics.algebraicGate
      (trajectory.predecessor t).state
      (trajectory.step t).candidate
      (trajectory.step t).certificate
  fullGate : ∀ t,
    directSemantics.fullGate
      (trajectory.predecessor t).state
      (trajectory.step t).candidate
      (trajectory.step t).certificate
  predecessorAbilitiesPreserved : ∀ t,
    directSemantics.predecessorAbilitiesPreserved
      (trajectory.predecessor t).state
      (trajectory.step t).candidate
      (trajectory.step t).certificate
  strictAbilityExpansionWhenWitness : ∀ t,
    kernel.strictWitness
      (trajectory.predecessor t).state
      (trajectory.step t).candidate
      (trajectory.step t).certificate →
    directSemantics.strictAbilityExpansion
      (trajectory.predecessor t).state
      (trajectory.step t).candidate
      (trajectory.step t).certificate
  successorViable : ∀ t,
    directSemantics.viabilityKernel (trajectory.step t).candidate.next
  projectionRealized : ∀ t,
    directSemantics.projectionRealized
      (trajectory.predecessor t).state
      (trajectory.step t).candidate
      (trajectory.step t).certificate
  verifierSchemaPersistence : ∀ horizon,
    svSemantics.verifierSchemaRefines
      (transportedPaperIIVerifierSchema
        svSemantics
        (RCP.finitePrefixOfInfinite
          (InfiniteArchitectureTrajectory.toAcceptedTrajectory trajectory)
          horizon)
        horizon
        (svSemantics.stateVerifierSchema (trajectory.predecessor 0).state))
      (svSemantics.stateVerifierSchema (trajectory.predecessor horizon).state)
  goalIdentityBound : ∀ horizon,
    svSemantics.goalDistance
        (svSemantics.stateGoal (trajectory.predecessor horizon).state)
        (transportedPaperIIGoal
          svSemantics
          (RCP.finitePrefixOfInfinite
            (InfiniteArchitectureTrajectory.toAcceptedTrajectory trajectory)
            horizon)
          horizon
          (svSemantics.stateGoal (trajectory.predecessor 0).state)) ≤
      cumulativePaperIIGoalDriftBudget
        svSemantics
        (RCP.finitePrefixOfInfinite
          (InfiniteArchitectureTrajectory.toAcceptedTrajectory trajectory)
          horizon)
        horizon
  goalDriftSummable : Summable fun t =>
    svSemantics.goalDriftBudget
      (trajectory.predecessor t).state
      (trajectory.step t).candidate
      (trajectory.step t).certificate
  soundnessFailureSummable : Summable fun t =>
    svSemantics.soundnessFailureRisk
      (trajectory.predecessor t).state
      (trajectory.step t).candidate
      (trajectory.step t).certificate

theorem paper_ii_infinite_robust_reflective_result
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
    (svSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (trajectory : InfiniteArchitectureTrajectory engine)
    (budgets : PaperIIInfiniteBudgetAssumptions svSemantics trajectory) :
    PaperIIInfiniteRobustReflectiveResult
      directSemantics svSemantics trajectory := by
  refine
    { successorVerification := ?_
      candidateNonLossy := ?_
      algebraicGate := ?_
      fullGate := ?_
      predecessorAbilitiesPreserved := ?_
      strictAbilityExpansionWhenWitness := ?_
      successorViable := ?_
      projectionRealized := ?_
      verifierSchemaPersistence := ?_
      goalIdentityBound := ?_
      goalDriftSummable := budgets.goalDrift
      soundnessFailureSummable := budgets.soundnessFailure }
  · intro t
    have obligations := checker.sound
      (trajectory.predecessor t).admissible
      (trajectory.predecessor t).invariant
      (trajectory.step t).checkerAccepted
    have successorDomain : engine.domain (trajectory.step t).candidate.next := by
      rw [← trajectory.linked t]
      exact (trajectory.predecessor (t + 1)).domainValid
    exact paper_ii_successor_verification_obligations
      svSemantics (trajectory.step t) obligations successorDomain
  · intro t
    have obligations := checker.sound
      (trajectory.predecessor t).admissible
      (trajectory.predecessor t).invariant
      (trajectory.step t).checkerAccepted
    exact directSemantics.nonLossyCandidate_of_obligations obligations
  · intro t
    have obligations := checker.sound
      (trajectory.predecessor t).admissible
      (trajectory.predecessor t).invariant
      (trajectory.step t).checkerAccepted
    exact directSemantics.algebraicGate_of_obligations obligations
  · intro t
    have obligations := checker.sound
      (trajectory.predecessor t).admissible
      (trajectory.predecessor t).invariant
      (trajectory.step t).checkerAccepted
    exact directSemantics.fullGate_of_obligations obligations
  · intro t
    have obligations := checker.sound
      (trajectory.predecessor t).admissible
      (trajectory.predecessor t).invariant
      (trajectory.step t).checkerAccepted
    exact directSemantics.predecessorAbilitiesPreserved_of_obligations obligations
  · intro t strictWitness
    have obligations := checker.sound
      (trajectory.predecessor t).admissible
      (trajectory.predecessor t).invariant
      (trajectory.step t).checkerAccepted
    exact directSemantics.strictAbilityExpansion_of_witness
      strictWitness obligations
  · intro t
    have successorDomain : engine.domain (trajectory.step t).candidate.next := by
      rw [← trajectory.linked t]
      exact (trajectory.predecessor (t + 1)).domainValid
    exact directSemantics.viabilityKernel_of_domain successorDomain
  · intro t
    have obligations := checker.sound
      (trajectory.predecessor t).admissible
      (trajectory.predecessor t).invariant
      (trajectory.step t).checkerAccepted
    exact directSemantics.projectionRealized_of_typedSuccessor
      obligations.typedSuccessor
  · intro horizon
    have bound : horizon ≤ horizon := Nat.le_refl horizon
    exact finite_paper_ii_verifier_schema_persistence
      svSemantics
      (RCP.finitePrefixOfInfinite
        (InfiniteArchitectureTrajectory.toAcceptedTrajectory trajectory)
        horizon)
      horizon
      bound
  · intro horizon
    have bound : horizon ≤ horizon := Nat.le_refl horizon
    exact finite_paper_ii_goal_identity_bound
      svSemantics
      (RCP.finitePrefixOfInfinite
        (InfiniteArchitectureTrajectory.toAcceptedTrajectory trajectory)
        horizon)
      horizon
      bound

theorem conditional_infinite_paper_ii_robust_reflective_trajectory_exists
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
    (svSemantics : PaperIISuccessorVerificationSemantics
      (VerifierSchema := VerifierSchema)
      (UncertaintyEnvelope := UncertaintyEnvelope)
      (Goal := Goal)
      engine)
    (availability : ArchitectureSuccessorAvailability engine)
    (initial : ArchitecturePredecessor engine)
    (budgets : PaperIIInfiniteBudgetAssumptions
      svSemantics
      (buildInfiniteArchitectureTrajectory engine availability initial)) :
    ∃ trajectory : InfiniteArchitectureTrajectory engine,
      trajectory.predecessor 0 = initial ∧
      PaperIIInfiniteRobustReflectiveResult
        directSemantics svSemantics trajectory := by
  let trajectory :=
    buildInfiniteArchitectureTrajectory engine availability initial
  have initialEquality : trajectory.predecessor 0 = initial := rfl
  have result :
      PaperIIInfiniteRobustReflectiveResult
        directSemantics svSemantics trajectory :=
    paper_ii_infinite_robust_reflective_result
      directSemantics svSemantics trajectory budgets
  exact ⟨trajectory, initialEquality, result⟩

end RCLM
end RcpRclmFormalCoreV2
