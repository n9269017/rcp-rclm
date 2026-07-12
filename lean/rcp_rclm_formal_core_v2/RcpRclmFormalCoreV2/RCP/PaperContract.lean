import RcpRclmFormalCoreV2.RCP.InfiniteHorizon

namespace RcpRclmFormalCoreV2
namespace RCP

/--
An explicit refinement boundary between the abstract Gate A kernel and the
state-safe-set / update-admissibility predicates used by a paper-facing theorem.

A concrete Paper I instantiation must supply these predicates and prove both
logical equivalences.  Merely reusing the names `safe` or `admissible` does not
establish the refinement.
-/
structure PaperSemantics
    {State Update Certificate Protected ResidualIndex : Type*}
    (K : Kernel State Update Certificate Protected ResidualIndex) where
  stateSafe : State → Prop
  updateAdmissible : State → Candidate State Update → Certificate → Prop
  stateSafe_iff : ∀ state,
    stateSafe state ↔ K.admissible state ∧ K.protectedInvariant state
  updateAdmissible_iff : ∀ state candidate certificate,
    updateAdmissible state candidate certificate ↔
      StepObligations K state candidate certificate

/-- An accepted candidate that leaves the represented state unchanged. -/
structure AcceptedNoOp
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (state : State) where
  candidate : Candidate State Update
  certificate : Certificate
  accepted : checker.check state candidate certificate = true
  unchanged : candidate.next = state

/--
The no-op premise appearing in Paper I: every paper-safe state has an accepted
unchanged successor packet.  This is an explicit availability premise and is
not inferred from checker soundness.
-/
def NoOpFeasible
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (semantics : PaperSemantics K) : Prop :=
  ∀ state, semantics.stateSafe state → Nonempty (AcceptedNoOp checker state)

/--
The complete abstract finite-horizon preservation conclusion corresponding to
the currently mechanized Paper I surface.
-/
structure FinitePaperPreservation
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (semantics : PaperSemantics K)
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : FiniteAcceptedTrajectory checker horizon)
    (t : Nat)
    (distinction : Protected)
    (relevance : Relevance) : Prop where
  endpointStateSafe : semantics.stateSafe (trajectory.state t)
  initialNoOpAvailable : Nonempty (AcceptedNoOp checker (trajectory.state 0))
  acceptedPrefixAdmissible : ∀ j, j < t →
    semantics.updateAdmissible
      (trajectory.state j)
      (trajectory.candidate j)
      (trajectory.certificate j)
  progressMonotone :
    K.progress (trajectory.state 0) ≤ K.progress (trajectory.state t)
  strictProgressWhenWitness : ∀ j, j < t →
    K.strictWitness
        (trajectory.state j)
        (trajectory.candidate j)
        (trajectory.certificate j) →
      K.progress (trajectory.state j) < K.progress (trajectory.state (j + 1))
  protectedNonLoss :
    K.protectedValue (trajectory.state 0) distinction ≤
      K.protectedValue (trajectory.state t)
          (transportedDistinction trajectory t distinction) +
        cumulativeLossBudget trajectory t
  endpointRecovery :
    K.stateDistance
        (composedRecovery trajectory t (trajectory.state t))
        (trajectory.state 0) ≤
      cumulativeRecoveryBudget trajectory t
  lyapunovAndMotion :
    monitors.lyapunovValue (trajectory.state t) +
        cumulativeMotionCharge monitors trajectory t ≤
      monitors.lyapunovValue (trajectory.state 0) +
        cumulativeLyapunovError monitors trajectory t
  ambiguityCollapse :
    cumulativeUnsupportedCollapse monitors trajectory t ≤
      cumulativeAmbiguityError monitors trajectory t
  selfModelRelevance :
    monitors.relevanceValue (trajectory.state 0) relevance ≤
      monitors.relevanceValue (trajectory.state t)
          (transportedRelevance monitors trajectory t relevance) +
        cumulativeRelevanceError monitors trajectory t

/--
Paper-facing finite preservation wrapper.  All assumptions absent from the
minimal checker kernel—safe-set semantics, update-admissibility semantics,
no-op feasibility, endpoint recovery laws, and named quantitative monitors—are
visible arguments.
-/
theorem finite_paper_preservation
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (semantics : PaperSemantics K)
    (noOpFeasible : NoOpFeasible checker semantics)
    (recoveryLaws : RecoveryCompositionLaws K)
    (monitors : PreservationMonitors K (Relevance := Relevance))
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon)
    (t : Nat)
    (bound : t ≤ horizon)
    (distinction : Protected)
    (relevance : Relevance) :
    FinitePaperPreservation
      semantics monitors trajectory t distinction relevance := by
  have endpointFacts := finite_trajectory_closure checker trajectory t bound
  have endpointStateSafe : semantics.stateSafe (trajectory.state t) :=
    (semantics.stateSafe_iff (trajectory.state t)).2 endpointFacts
  have initialStateSafe : semantics.stateSafe (trajectory.state 0) :=
    (semantics.stateSafe_iff (trajectory.state 0)).2
      ⟨trajectory.initialAdmissible, trajectory.initialInvariant⟩
  refine
    { endpointStateSafe := endpointStateSafe
      initialNoOpAvailable := noOpFeasible (trajectory.state 0) initialStateSafe
      acceptedPrefixAdmissible := ?_
      progressMonotone :=
        finite_progress_monotone checker trajectory 0 t (Nat.zero_le t) bound
      strictProgressWhenWitness := ?_
      protectedNonLoss :=
        finite_composed_nonloss_bound checker trajectory t bound distinction
      endpointRecovery :=
        finite_endpoint_recovery_bound checker recoveryLaws trajectory t bound
      lyapunovAndMotion :=
        finite_lyapunov_motion_bound checker monitors trajectory t bound
      ambiguityCollapse :=
        finite_ambiguity_collapse_bound checker monitors trajectory t bound
      selfModelRelevance :=
        finite_self_model_relevance_bound
          checker monitors trajectory t bound relevance }
  · intro j jLtT
    have jLtHorizon : j < horizon := lt_of_lt_of_le jLtT bound
    exact (semantics.updateAdmissible_iff
      (trajectory.state j)
      (trajectory.candidate j)
      (trajectory.certificate j)).2
        (finite_trajectory_step_sound checker trajectory j jLtHorizon)
  · intro j jLtT strictWitness
    have jLtHorizon : j < horizon := lt_of_lt_of_le jLtT bound
    have obligations :=
      finite_trajectory_step_sound checker trajectory j jLtHorizon
    have strictAtCandidate := obligations.strictProgressWhenWitness strictWitness
    rw [trajectory.linked j jLtHorizon]
    exact strictAtCandidate

/-- Paper-facing domain and update-admissibility facts along an infinite path. -/
structure InfinitePaperTrajectoryFacts
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    (semantics : PaperSemantics K)
    (trajectory : InfiniteAcceptedTrajectory checker) : Prop where
  stateSafe : ∀ t, semantics.stateSafe (trajectory.state t)
  updateAdmissible : ∀ t,
    semantics.updateAdmissible
      (trajectory.state t)
      (trajectory.candidate t)
      (trajectory.certificate t)
  noOpAvailable : ∀ t, Nonempty (AcceptedNoOp checker (trajectory.state t))

/--
Conditional infinite Paper I domain closure.  Successor availability and no-op
feasibility are separate explicit premises; neither follows from checker
soundness.
-/
theorem conditional_infinite_paper_trajectory_exists
    {State Update Certificate Protected ResidualIndex : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (semantics : PaperSemantics K)
    (noOpFeasible : NoOpFeasible checker semantics)
    (availability : SuccessorAvailability checker)
    (initial : DomainState K) :
    ∃ trajectory : InfiniteAcceptedTrajectory checker,
      trajectory.state 0 = initial.state ∧
        InfinitePaperTrajectoryFacts semantics trajectory := by
  let trajectory := buildInfiniteAcceptedTrajectory checker availability initial
  refine ⟨trajectory, rfl, ?_⟩
  refine
    { stateSafe := ?_
      updateAdmissible := ?_
      noOpAvailable := ?_ }
  · intro t
    exact (semantics.stateSafe_iff (trajectory.state t)).2
      ⟨trajectory.admissible t, trajectory.invariant t⟩
  · intro t
    exact (semantics.updateAdmissible_iff
      (trajectory.state t)
      (trajectory.candidate t)
      (trajectory.certificate t)).2
        (accepted_step_sound checker
          (trajectory.admissible t)
          (trajectory.invariant t)
          (trajectory.accepted t))
  · intro t
    apply noOpFeasible (trajectory.state t)
    exact (semantics.stateSafe_iff (trajectory.state t)).2
      ⟨trajectory.admissible t, trajectory.invariant t⟩

end RCP
end RcpRclmFormalCoreV2
