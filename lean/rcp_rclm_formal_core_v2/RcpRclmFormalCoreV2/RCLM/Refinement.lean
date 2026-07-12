import RcpRclmFormalCoreV2.RCP.Checker
import RcpRclmFormalCoreV2.RCP.Monitors
import RcpRclmFormalCoreV2.RCP.Recovery

namespace RcpRclmFormalCoreV2
namespace RCLM

structure KernelRefinement
    {CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex : Type*}
    {RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex : Type*}
    (rclmKernel :
      RCP.Kernel
        RclmState
        RclmUpdate
        RclmCertificate
        RclmProtected
        RclmResidualIndex)
    (coreKernel :
      RCP.Kernel
        CoreState
        CoreUpdate
        CoreCertificate
        CoreProtected
        CoreResidualIndex) where
  forgetState : RclmState → CoreState
  liftState : CoreState → RclmState
  forgetLiftState : ∀ state, forgetState (liftState state) = state

  forgetUpdate : RclmUpdate → CoreUpdate
  liftUpdate : CoreUpdate → RclmUpdate
  forgetLiftUpdate : ∀ update, forgetUpdate (liftUpdate update) = update

  forgetCertificate : RclmCertificate → CoreCertificate
  liftCertificate : CoreCertificate → RclmCertificate
  forgetLiftCertificate : ∀ certificate,
    forgetCertificate (liftCertificate certificate) = certificate

  forgetProtected : RclmProtected → CoreProtected
  liftProtected : CoreProtected → RclmProtected
  forgetLiftProtected : ∀ distinction,
    forgetProtected (liftProtected distinction) = distinction

  forgetResidualIndex : RclmResidualIndex → CoreResidualIndex
  liftResidualIndex : CoreResidualIndex → RclmResidualIndex
  forgetLiftResidualIndex : ∀ index,
    forgetResidualIndex (liftResidualIndex index) = index

  applyPreserved : ∀ state update,
    forgetState (rclmKernel.apply state update) =
      coreKernel.apply (forgetState state) (forgetUpdate update)

  admissiblePreserved : ∀ state,
    rclmKernel.admissible state →
      coreKernel.admissible (forgetState state)

  invariantPreserved : ∀ state,
    rclmKernel.protectedInvariant state →
      coreKernel.protectedInvariant (forgetState state)

  protectedValuePreserved : ∀ state distinction,
    rclmKernel.protectedValue state distinction =
      coreKernel.protectedValue
        (forgetState state)
        (forgetProtected distinction)

  transportProtectedPreserved : ∀ state candidate distinction,
    forgetProtected
        (rclmKernel.transportProtected state candidate distinction) =
      coreKernel.transportProtected
        (forgetState state)
        { update := forgetUpdate candidate.update
          next := forgetState candidate.next }
        (forgetProtected distinction)

  lossBudgetPreserved : ∀ state candidate,
    rclmKernel.lossBudget state candidate =
      coreKernel.lossBudget
        (forgetState state)
        { update := forgetUpdate candidate.update
          next := forgetState candidate.next }

  stateDistancePreserved : ∀ x y,
    rclmKernel.stateDistance x y =
      coreKernel.stateDistance (forgetState x) (forgetState y)

  recoverPreserved : ∀ state candidate endpoint,
    forgetState (rclmKernel.recover state candidate endpoint) =
      coreKernel.recover
        (forgetState state)
        { update := forgetUpdate candidate.update
          next := forgetState candidate.next }
        (forgetState endpoint)

  recoveryBudgetPreserved : ∀ state candidate,
    rclmKernel.recoveryBudget state candidate =
      coreKernel.recoveryBudget
        (forgetState state)
        { update := forgetUpdate candidate.update
          next := forgetState candidate.next }

  progressPreserved : ∀ state,
    rclmKernel.progress state = coreKernel.progress (forgetState state)

  strictWitnessPreserved : ∀ state candidate certificate,
    rclmKernel.strictWitness state candidate certificate ↔
      coreKernel.strictWitness
        (forgetState state)
        { update := forgetUpdate candidate.update
          next := forgetState candidate.next }
        (forgetCertificate certificate)

  residualPreserved : ∀ state candidate certificate index,
    rclmKernel.residual state candidate certificate index =
      coreKernel.residual
        (forgetState state)
        { update := forgetUpdate candidate.update
          next := forgetState candidate.next }
        (forgetCertificate certificate)
        (forgetResidualIndex index)

  trustValidPreserved : ∀ state candidate certificate,
    rclmKernel.trustValid state candidate certificate ↔
      coreKernel.trustValid
        (forgetState state)
        { update := forgetUpdate candidate.update
          next := forgetState candidate.next }
        (forgetCertificate certificate)

  resourceValidPreserved : ∀ state candidate certificate,
    rclmKernel.resourceValid state candidate certificate ↔
      coreKernel.resourceValid
        (forgetState state)
        { update := forgetUpdate candidate.update
          next := forgetState candidate.next }
        (forgetCertificate certificate)

  realityContainedPreserved : ∀ state candidate certificate,
    rclmKernel.realityContained state candidate certificate ↔
      coreKernel.realityContained
        (forgetState state)
        { update := forgetUpdate candidate.update
          next := forgetState candidate.next }
        (forgetCertificate certificate)

namespace KernelRefinement

variable
    {CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex : Type*}
    {RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex : Type*}
    {rclmKernel :
      RCP.Kernel
        RclmState
        RclmUpdate
        RclmCertificate
        RclmProtected
        RclmResidualIndex}
    {coreKernel :
      RCP.Kernel
        CoreState
        CoreUpdate
        CoreCertificate
        CoreProtected
        CoreResidualIndex}


def forgetCandidate
    (refinement : KernelRefinement rclmKernel coreKernel)
    (candidate : RCP.Candidate RclmState RclmUpdate) :
    RCP.Candidate CoreState CoreUpdate where
  update := refinement.forgetUpdate candidate.update
  next := refinement.forgetState candidate.next


def liftCandidate
    (refinement : KernelRefinement rclmKernel coreKernel)
    (candidate : RCP.Candidate CoreState CoreUpdate) :
    RCP.Candidate RclmState RclmUpdate where
  update := refinement.liftUpdate candidate.update
  next := refinement.liftState candidate.next


theorem forgetLiftCandidate
    (refinement : KernelRefinement rclmKernel coreKernel)
    (candidate : RCP.Candidate CoreState CoreUpdate) :
    refinement.forgetCandidate (refinement.liftCandidate candidate) = candidate := by
  cases candidate with
  | mk update next =>
      simp [forgetCandidate, liftCandidate,
        refinement.forgetLiftUpdate, refinement.forgetLiftState]


theorem stepObligationsPreserved
    (refinement : KernelRefinement rclmKernel coreKernel)
    {state : RclmState}
    {candidate : RCP.Candidate RclmState RclmUpdate}
    {certificate : RclmCertificate}
    (obligations :
      RCP.StepObligations rclmKernel state candidate certificate) :
    RCP.StepObligations
      coreKernel
      (refinement.forgetState state)
      (refinement.forgetCandidate candidate)
      (refinement.forgetCertificate certificate) := by
  refine
    { typedSuccessor := ?_
      residualsNonpositive := ?_
      protectedNonLoss := ?_
      constructiveRecovery := ?_
      invariantPreserved := ?_
      progressNondecreasing := ?_
      strictProgressWhenWitness := ?_
      trustValid := ?_
      resourceValid := ?_
      realityContained := ?_
      successorAdmissible := ?_ }
  · unfold RCP.TypedSuccessor at obligations ⊢
    have mappedEquality :
        refinement.forgetState candidate.next =
          refinement.forgetState
            (rclmKernel.apply state candidate.update) :=
      congrArg refinement.forgetState obligations.typedSuccessor
    calc
      refinement.forgetState candidate.next =
          refinement.forgetState
            (rclmKernel.apply state candidate.update) := mappedEquality
      _ = coreKernel.apply
            (refinement.forgetState state)
            (refinement.forgetUpdate candidate.update) :=
        refinement.applyPreserved state candidate.update
  · intro index
    have localBound :=
      obligations.residualsNonpositive
        (refinement.liftResidualIndex index)
    rw [refinement.residualPreserved,
      refinement.forgetLiftResidualIndex] at localBound
    exact localBound
  · unfold RCP.ProtectedNonLoss at obligations ⊢
    intro distinction
    have localBound :=
      obligations.protectedNonLoss
        (refinement.liftProtected distinction)
    rw [refinement.protectedValuePreserved,
      refinement.protectedValuePreserved,
      refinement.transportProtectedPreserved,
      refinement.lossBudgetPreserved,
      refinement.forgetLiftProtected] at localBound
    exact localBound
  · unfold RCP.ConstructiveRecovery at obligations ⊢
    have localBound := obligations.constructiveRecovery
    rw [refinement.stateDistancePreserved,
      refinement.recoverPreserved,
      refinement.recoveryBudgetPreserved] at localBound
    exact localBound
  · exact refinement.invariantPreserved candidate.next
      obligations.invariantPreserved
  · unfold RCP.ProgressNondecreasing at obligations ⊢
    have localBound := obligations.progressNondecreasing
    rw [refinement.progressPreserved,
      refinement.progressPreserved] at localBound
    exact localBound
  · unfold RCP.StrictProgressWhenWitness at obligations ⊢
    intro coreWitness
    have rclmWitness :
        rclmKernel.strictWitness state candidate certificate :=
      (refinement.strictWitnessPreserved state candidate certificate).2
        coreWitness
    have localStrict :=
      obligations.strictProgressWhenWitness rclmWitness
    rw [refinement.progressPreserved,
      refinement.progressPreserved] at localStrict
    exact localStrict
  · exact
      (refinement.trustValidPreserved state candidate certificate).1
        obligations.trustValid
  · exact
      (refinement.resourceValidPreserved state candidate certificate).1
        obligations.resourceValid
  · exact
      (refinement.realityContainedPreserved state candidate certificate).1
        obligations.realityContained
  · exact refinement.admissiblePreserved candidate.next
      obligations.successorAdmissible


theorem recoveryCompositionLawsPreserved
    (refinement : KernelRefinement rclmKernel coreKernel)
    (laws : RCP.RecoveryCompositionLaws rclmKernel) :
    RCP.RecoveryCompositionLaws coreKernel := by
  refine
    { selfDistanceZero := ?_
      triangle := ?_
      recoverNonexpansive := ?_ }
  · intro state
    have localZero := laws.selfDistanceZero (refinement.liftState state)
    rw [refinement.stateDistancePreserved,
      refinement.forgetLiftState] at localZero
    exact localZero
  · intro x y z
    have localTriangle := laws.triangle
      (refinement.liftState x)
      (refinement.liftState y)
      (refinement.liftState z)
    rw [refinement.stateDistancePreserved,
      refinement.stateDistancePreserved,
      refinement.stateDistancePreserved,
      refinement.forgetLiftState] at localTriangle
    exact localTriangle
  · intro state candidate x y
    have localNonexpansive := laws.recoverNonexpansive
      (refinement.liftState state)
      (refinement.liftCandidate candidate)
      (refinement.liftState x)
      (refinement.liftState y)
    rw [refinement.stateDistancePreserved,
      refinement.recoverPreserved,
      refinement.recoverPreserved,
      refinement.stateDistancePreserved,
      refinement.forgetLiftState,
      refinement.forgetLiftUpdate] at localNonexpansive
    exact localNonexpansive

end KernelRefinement

structure MonitorRefinement
    {CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex : Type*}
    {RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex : Type*}
    {CoreRelevance RclmRelevance : Type*}
    {rclmKernel :
      RCP.Kernel
        RclmState
        RclmUpdate
        RclmCertificate
        RclmProtected
        RclmResidualIndex}
    {coreKernel :
      RCP.Kernel
        CoreState
        CoreUpdate
        CoreCertificate
        CoreProtected
        CoreResidualIndex}
    (refinement : KernelRefinement rclmKernel coreKernel)
    (rclmMonitors :
      RCP.PreservationMonitors rclmKernel (Relevance := RclmRelevance))
    (coreMonitors :
      RCP.PreservationMonitors coreKernel (Relevance := CoreRelevance)) where
  forgetRelevance : RclmRelevance → CoreRelevance
  liftRelevance : CoreRelevance → RclmRelevance
  forgetLiftRelevance : ∀ relevance,
    forgetRelevance (liftRelevance relevance) = relevance

  lyapunovValuePreserved : ∀ state,
    rclmMonitors.lyapunovValue state =
      coreMonitors.lyapunovValue (refinement.forgetState state)

  motionChargePreserved : ∀ state candidate certificate,
    rclmMonitors.motionCharge state candidate certificate =
      coreMonitors.motionCharge
        (refinement.forgetState state)
        (refinement.forgetCandidate candidate)
        (refinement.forgetCertificate certificate)

  lyapunovErrorPreserved : ∀ state candidate certificate,
    rclmMonitors.lyapunovError state candidate certificate =
      coreMonitors.lyapunovError
        (refinement.forgetState state)
        (refinement.forgetCandidate candidate)
        (refinement.forgetCertificate certificate)

  unsupportedCollapsePreserved : ∀ state candidate certificate,
    rclmMonitors.unsupportedCollapse state candidate certificate =
      coreMonitors.unsupportedCollapse
        (refinement.forgetState state)
        (refinement.forgetCandidate candidate)
        (refinement.forgetCertificate certificate)

  ambiguityErrorPreserved : ∀ state candidate certificate,
    rclmMonitors.ambiguityError state candidate certificate =
      coreMonitors.ambiguityError
        (refinement.forgetState state)
        (refinement.forgetCandidate candidate)
        (refinement.forgetCertificate certificate)

  relevanceValuePreserved : ∀ state relevance,
    rclmMonitors.relevanceValue state relevance =
      coreMonitors.relevanceValue
        (refinement.forgetState state)
        (forgetRelevance relevance)

  transportRelevancePreserved : ∀ state candidate relevance,
    forgetRelevance
        (rclmMonitors.transportRelevance state candidate relevance) =
      coreMonitors.transportRelevance
        (refinement.forgetState state)
        (refinement.forgetCandidate candidate)
        (forgetRelevance relevance)

  relevanceErrorPreserved : ∀ state candidate certificate,
    rclmMonitors.relevanceError state candidate certificate =
      coreMonitors.relevanceError
        (refinement.forgetState state)
        (refinement.forgetCandidate candidate)
        (refinement.forgetCertificate certificate)

structure CheckerRefinement
    {CoreState CoreUpdate CoreCertificate CoreProtected CoreResidualIndex : Type*}
    {RclmState RclmUpdate RclmCertificate RclmProtected RclmResidualIndex : Type*}
    {rclmKernel :
      RCP.Kernel
        RclmState
        RclmUpdate
        RclmCertificate
        RclmProtected
        RclmResidualIndex}
    {coreKernel :
      RCP.Kernel
        CoreState
        CoreUpdate
        CoreCertificate
        CoreProtected
        CoreResidualIndex}
    (kernelRefinement : KernelRefinement rclmKernel coreKernel)
    (rclmChecker : RCP.TrustedChecker rclmKernel)
    (coreChecker : RCP.TrustedChecker coreKernel) where
  acceptancePreserved : ∀ state candidate certificate,
    rclmChecker.check state candidate certificate = true →
      coreChecker.check
        (kernelRefinement.forgetState state)
        (kernelRefinement.forgetCandidate candidate)
        (kernelRefinement.forgetCertificate certificate) = true

end RCLM
end RcpRclmFormalCoreV2
