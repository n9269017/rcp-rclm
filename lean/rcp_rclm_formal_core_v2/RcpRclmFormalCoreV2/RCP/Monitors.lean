import RcpRclmFormalCoreV2.RCP.Trajectory

namespace RcpRclmFormalCoreV2
namespace RCP

/--
Explicit abstract monitor data for the quantitative conclusions of Paper I.

The Gate A kernel does not identify these real-valued quantities with a
particular probability space, trace distance, ambiguity variable, or mutual
information expression.  A concrete refinement must make those identifications.
The intended Paper I reading is:

* `lyapunovValue state` is the relevant expected Lyapunov value;
* `motionCharge` is the charged term such as
  `κ * E[d(state⁺, state)^2]`;
* `lyapunovError` is the one-step `η` budget;
* `unsupportedCollapse` and `ambiguityError` are the `U` and `ζ` terms; and
* `relevanceValue`, `transportRelevance`, and `relevanceError` are the
  transported self-model-relevance quantity and its `ξ` budget.

Every one-step inequality is required as a theorem from the accepted step
obligations.  A generic residual index is therefore not silently reinterpreted
as one of these paper quantities.
-/
structure PreservationMonitors
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    (K : Kernel State Update Certificate Protected ResidualIndex) where
  lyapunovValue : State → ℝ
  motionCharge : State → Candidate State Update → Certificate → ℝ
  lyapunovError : State → Candidate State Update → Certificate → ℝ

  unsupportedCollapse : State → Candidate State Update → Certificate → ℝ
  ambiguityError : State → Candidate State Update → Certificate → ℝ

  relevanceValue : State → Relevance → ℝ
  transportRelevance : State → Candidate State Update → Relevance → Relevance
  relevanceError : State → Candidate State Update → Certificate → ℝ

  lyapunovValue_nonnegative : ∀ state, 0 ≤ lyapunovValue state
  motionCharge_nonnegative : ∀ state candidate certificate,
    0 ≤ motionCharge state candidate certificate
  lyapunovError_nonnegative : ∀ state candidate certificate,
    0 ≤ lyapunovError state candidate certificate
  unsupportedCollapse_nonnegative : ∀ state candidate certificate,
    0 ≤ unsupportedCollapse state candidate certificate
  ambiguityError_nonnegative : ∀ state candidate certificate,
    0 ≤ ambiguityError state candidate certificate
  relevanceError_nonnegative : ∀ state candidate certificate,
    0 ≤ relevanceError state candidate certificate

  lyapunovStep : ∀ {state candidate certificate},
    StepObligations K state candidate certificate →
      lyapunovValue candidate.next +
          motionCharge state candidate certificate ≤
        lyapunovValue state + lyapunovError state candidate certificate

  ambiguityStep : ∀ {state candidate certificate},
    StepObligations K state candidate certificate →
      unsupportedCollapse state candidate certificate ≤
        ambiguityError state candidate certificate

  relevanceStep : ∀ {state candidate certificate},
    StepObligations K state candidate certificate →
      ∀ relevance,
        relevanceValue state relevance ≤
          relevanceValue candidate.next
              (transportRelevance state candidate relevance) +
            relevanceError state candidate certificate

/-- Cumulative charged motion over the first `steps` accepted transitions. -/
def cumulativeMotionCharge
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : FiniteAcceptedTrajectory checker horizon) : Nat → ℝ
  | 0 => 0
  | t + 1 =>
      cumulativeMotionCharge monitors trajectory t +
        monitors.motionCharge
          (trajectory.state t)
          (trajectory.candidate t)
          (trajectory.certificate t)

/-- Cumulative Lyapunov error budget over the first `steps` transitions. -/
def cumulativeLyapunovError
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : FiniteAcceptedTrajectory checker horizon) : Nat → ℝ
  | 0 => 0
  | t + 1 =>
      cumulativeLyapunovError monitors trajectory t +
        monitors.lyapunovError
          (trajectory.state t)
          (trajectory.candidate t)
          (trajectory.certificate t)

/-- Cumulative unsupported ambiguity collapse over the first `steps` transitions. -/
def cumulativeUnsupportedCollapse
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : FiniteAcceptedTrajectory checker horizon) : Nat → ℝ
  | 0 => 0
  | t + 1 =>
      cumulativeUnsupportedCollapse monitors trajectory t +
        monitors.unsupportedCollapse
          (trajectory.state t)
          (trajectory.candidate t)
          (trajectory.certificate t)

/-- Cumulative ambiguity-collapse budget over the first `steps` transitions. -/
def cumulativeAmbiguityError
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : FiniteAcceptedTrajectory checker horizon) : Nat → ℝ
  | 0 => 0
  | t + 1 =>
      cumulativeAmbiguityError monitors trajectory t +
        monitors.ambiguityError
          (trajectory.state t)
          (trajectory.candidate t)
          (trajectory.certificate t)

/-- Transport a self-model-relevance object through the first `steps` updates. -/
def transportedRelevance
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : FiniteAcceptedTrajectory checker horizon) :
    Nat → Relevance → Relevance
  | 0, relevance => relevance
  | t + 1, relevance =>
      monitors.transportRelevance
        (trajectory.state t)
        (trajectory.candidate t)
        (transportedRelevance monitors trajectory t relevance)

/-- Cumulative self-model-relevance loss budget over the first `steps` transitions. -/
def cumulativeRelevanceError
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    {checker : TrustedChecker K}
    {horizon : Nat}
    (monitors : PreservationMonitors K (Relevance := Relevance))
    (trajectory : FiniteAcceptedTrajectory checker horizon) : Nat → ℝ
  | 0 => 0
  | t + 1 =>
      cumulativeRelevanceError monitors trajectory t +
        monitors.relevanceError
          (trajectory.state t)
          (trajectory.candidate t)
          (trajectory.certificate t)

/--
Finite Lyapunov telescoping with accumulated charged motion and explicit error
budget.  A concrete instance may set the charged motion to
`κ * E[d(state⁺, state)^2]`.
-/
theorem finite_lyapunov_motion_bound
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (monitors : PreservationMonitors K (Relevance := Relevance))
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      monitors.lyapunovValue (trajectory.state t) +
          cumulativeMotionCharge monitors trajectory t ≤
        monitors.lyapunovValue (trajectory.state 0) +
          cumulativeLyapunovError monitors trajectory t := by
  intro t
  induction t with
  | zero =>
      intro _
      simp [cumulativeMotionCharge, cumulativeLyapunovError]
  | succ t inductionHypothesis =>
      intro bound
      have stepBound : t < horizon := Nat.lt_of_succ_le bound
      have previousBound : t ≤ horizon := Nat.le_of_lt stepBound
      have previous := inductionHypothesis previousBound
      have stepMonitor := monitors.lyapunovStep
        (finite_trajectory_step_sound checker trajectory t stepBound)
      have stepAtState :
          monitors.lyapunovValue (trajectory.state (t + 1)) +
              monitors.motionCharge
                (trajectory.state t)
                (trajectory.candidate t)
                (trajectory.certificate t) ≤
            monitors.lyapunovValue (trajectory.state t) +
              monitors.lyapunovError
                (trajectory.state t)
                (trajectory.candidate t)
                (trajectory.certificate t) := by
        rw [trajectory.linked t stepBound]
        exact stepMonitor
      calc
        monitors.lyapunovValue (trajectory.state (t + 1)) +
            cumulativeMotionCharge monitors trajectory (t + 1) =
          (monitors.lyapunovValue (trajectory.state (t + 1)) +
              monitors.motionCharge
                (trajectory.state t)
                (trajectory.candidate t)
                (trajectory.certificate t)) +
            cumulativeMotionCharge monitors trajectory t := by
          simp only [cumulativeMotionCharge]
          ac_rfl
        _ ≤ (monitors.lyapunovValue (trajectory.state t) +
              monitors.lyapunovError
                (trajectory.state t)
                (trajectory.candidate t)
                (trajectory.certificate t)) +
            cumulativeMotionCharge monitors trajectory t :=
          add_le_add_left stepAtState _
        _ = (monitors.lyapunovValue (trajectory.state t) +
              cumulativeMotionCharge monitors trajectory t) +
            monitors.lyapunovError
              (trajectory.state t)
              (trajectory.candidate t)
              (trajectory.certificate t) := by
          ac_rfl
        _ ≤ (monitors.lyapunovValue (trajectory.state 0) +
              cumulativeLyapunovError monitors trajectory t) +
            monitors.lyapunovError
              (trajectory.state t)
              (trajectory.candidate t)
              (trajectory.certificate t) :=
          add_le_add_left previous _
        _ = monitors.lyapunovValue (trajectory.state 0) +
            cumulativeLyapunovError monitors trajectory (t + 1) := by
          simp only [cumulativeLyapunovError]
          ac_rfl

/-- Total unsupported ambiguity collapse is bounded by its cumulative budget. -/
theorem finite_ambiguity_collapse_bound
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (monitors : PreservationMonitors K (Relevance := Relevance))
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon) :
    ∀ t, t ≤ horizon →
      cumulativeUnsupportedCollapse monitors trajectory t ≤
        cumulativeAmbiguityError monitors trajectory t := by
  intro t
  induction t with
  | zero =>
      intro _
      simp [cumulativeUnsupportedCollapse, cumulativeAmbiguityError]
  | succ t inductionHypothesis =>
      intro bound
      have stepBound : t < horizon := Nat.lt_of_succ_le bound
      have previousBound : t ≤ horizon := Nat.le_of_lt stepBound
      have previous := inductionHypothesis previousBound
      have localBound := monitors.ambiguityStep
        (finite_trajectory_step_sound checker trajectory t stepBound)
      have combined := add_le_add previous localBound
      simpa [cumulativeUnsupportedCollapse, cumulativeAmbiguityError] using combined

/--
The initial self-model-relevance value is retained at the transported endpoint
up to the cumulative explicit relevance-loss budget.
-/
theorem finite_self_model_relevance_bound
    {State Update Certificate Protected ResidualIndex Relevance : Type*}
    {K : Kernel State Update Certificate Protected ResidualIndex}
    (checker : TrustedChecker K)
    (monitors : PreservationMonitors K (Relevance := Relevance))
    {horizon : Nat}
    (trajectory : FiniteAcceptedTrajectory checker horizon) :
    ∀ t, t ≤ horizon → ∀ relevance,
      monitors.relevanceValue (trajectory.state 0) relevance ≤
        monitors.relevanceValue (trajectory.state t)
            (transportedRelevance monitors trajectory t relevance) +
          cumulativeRelevanceError monitors trajectory t := by
  intro t
  induction t with
  | zero =>
      intro _ relevance
      simp [transportedRelevance, cumulativeRelevanceError]
  | succ t inductionHypothesis =>
      intro bound relevance
      have stepBound : t < horizon := Nat.lt_of_succ_le bound
      have previousBound : t ≤ horizon := Nat.le_of_lt stepBound
      have previous := inductionHypothesis previousBound relevance
      have obligations :=
        finite_trajectory_step_sound checker trajectory t stepBound
      have stepMonitor := monitors.relevanceStep obligations
        (transportedRelevance monitors trajectory t relevance)
      have stepAtState :
          monitors.relevanceValue (trajectory.state t)
              (transportedRelevance monitors trajectory t relevance) ≤
            monitors.relevanceValue (trajectory.state (t + 1))
                (monitors.transportRelevance
                  (trajectory.state t)
                  (trajectory.candidate t)
                  (transportedRelevance monitors trajectory t relevance)) +
              monitors.relevanceError
                (trajectory.state t)
                (trajectory.candidate t)
                (trajectory.certificate t) := by
        rw [trajectory.linked t stepBound]
        exact stepMonitor
      calc
        monitors.relevanceValue (trajectory.state 0) relevance ≤
            monitors.relevanceValue (trajectory.state t)
                (transportedRelevance monitors trajectory t relevance) +
              cumulativeRelevanceError monitors trajectory t := previous
        _ ≤ (monitors.relevanceValue (trajectory.state (t + 1))
                (monitors.transportRelevance
                  (trajectory.state t)
                  (trajectory.candidate t)
                  (transportedRelevance monitors trajectory t relevance)) +
              monitors.relevanceError
                (trajectory.state t)
                (trajectory.candidate t)
                (trajectory.certificate t)) +
            cumulativeRelevanceError monitors trajectory t :=
          add_le_add_left stepAtState _
        _ = monitors.relevanceValue (trajectory.state (t + 1))
                (transportedRelevance monitors trajectory (t + 1) relevance) +
              cumulativeRelevanceError monitors trajectory (t + 1) := by
          simp only [transportedRelevance, cumulativeRelevanceError]
          ac_rfl

end RCP
end RcpRclmFormalCoreV2
