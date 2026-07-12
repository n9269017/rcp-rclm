# Formal Core v2 theorem contract

## Contract status

This document freezes the **complete abstract Gate A successor and preservation
kernel**. It is not, by itself, the exact concrete statement of Paper I's
`thm:main_rcp` or any Paper II architecture theorem. The initial comparison is
in `GATE_A_PAPER_ALIGNMENT_AUDIT.md`; later resolutions are recorded in
`GATE_A_ALIGNMENT_RESOLUTION_LOG.md`.

```text
abstract one-step contract: implemented
abstract finite trajectory composition: implemented
abstract endpoint recovery composition: implemented
abstract quantitative monitor composition: implemented
standard Summable-to-uniform-prefix bridge: implemented
paper-safe/update-admissibility refinement boundary: implemented
no-op-feasibility premise: implemented
conditional infinite trajectory construction: implemented
paper-facing finite and infinite abstract wrappers: implemented
abstract Gate A theorem kernel: complete
exact Paper I/Paper II agreement: not yet achieved
```

## Ordinary one-step mathematical contract

Let `M_t` be an admissible predecessor state, `u_t` a proposed typed update,
`M_{t+1}` the claimed successor, and `c_t` a certificate packet. The kernel
supplies typed update semantics, protected distinctions and transports,
quantitative loss and recovery budgets, a candidate-tied recovery map, progress
and strict-witness predicates, computed residuals, trust/resource/reality
predicates, and an admissible successor domain.

For a trusted checker:

```text
Admissible(M_t)
∧ ProtectedInvariant(M_t)
∧ Check(M_t,u_t,M_{t+1},c_t) = true

⇒

M_{t+1} = Apply(M_t,u_t)
∧ every computed residual is nonpositive
∧ every protected distinction is preserved within its loss budget
∧ recovery returns within the one-step recovery budget
∧ ProtectedInvariant(M_{t+1})
∧ Progress(M_t) ≤ Progress(M_{t+1})
∧ (StrictWitness(...) ⇒ Progress(M_t) < Progress(M_{t+1}))
∧ TrustValid(...)
∧ ResourceValid(...)
∧ RealityContained(...)
∧ Admissible(M_{t+1}).
```

This is checker soundness, not successor existence or generator completeness.

## Finite composition contract

For an accepted finite path

```text
M_0 --(u_0,c_0)--> M_1 -- ... --> M_N
```

the project proves:

1. every in-horizon state remains admissible and invariant-preserving;
2. every transition satisfies the complete one-step obligations;
3. progress is monotone and each strict witness yields strict progress;
4. transported protected values satisfy an additive loss-budget bound;
5. actual local recovery errors satisfy the aggregate local-budget bound; and
6. under explicit recovery composition laws, the rollback-order composed map
   recovers the initial state from the endpoint within the cumulative budget.

The endpoint theorem uses:

```lean
RCP.RecoveryCompositionLaws
RCP.composedRecovery
RCP.composedRecovery_nonexpansive
RCP.finite_endpoint_recovery_bound
```

The extra laws are visible: zero self-distance, triangle inequality, and
nonexpansiveness of each candidate-tied recovery map.

## Quantitative Paper I monitor contract

`RCP.PreservationMonitors` explicitly names:

```text
Lyapunov value
charged motion term
Lyapunov error budget
unsupported ambiguity collapse
ambiguity error budget
self-model relevance value
cross-time relevance transport
relevance error budget
```

A concrete instance may set the motion charge to
`κ * E[d(M_{t+1},M_t)^2]`, but this interpretation must be proved. A generic
residual is never silently treated as a named monitor.

Finite composition is provided by:

```lean
RCP.finite_lyapunov_motion_bound
RCP.finite_ambiguity_collapse_bound
RCP.finite_self_model_relevance_bound
```

## Infinite trajectory and summability contract

`RCP.SuccessorAvailability` remains an explicit premise: every admissible,
invariant-preserving state has a nonempty accepted successor packet. Under this
premise, `RCP.conditional_infinite_trajectory_exists` constructs an infinite
accepted path.

Every finite prefix inherits endpoint recovery and the monitor bounds through
`RCP.finitePrefixOfInfinite` and the infinite-prefix theorems.

The analytic summability surface is:

```lean
RCP.SummableMonitorBudgets
RCP.SummableMonitorBudgets.toUniformMonitorBudgetCaps
RCP.infinite_monitor_bounds_of_summable
RCP.infinite_cumulative_motion_bounded_of_summable
```

The three concrete nonnegative error sequences are assumed `Summable`. Their
finite partial sums are bounded by their `tsum`s, supplying the uniform caps
used by the infinite-prefix preservation theorems.

## Paper-safe predicates and no-op premise

`RCP.PaperSemantics` carries paper-facing predicates

```text
StateSafe(M)
UpdateAdmissible(M,u,M',c)
```

together with explicit equivalences to

```text
K.admissible M ∧ K.protectedInvariant M
StepObligations K M candidate c.
```

The equivalences are concrete refinement obligations, not consequences of the
names.

`RCP.AcceptedNoOp` and `RCP.NoOpFeasible` represent the no-op premise as an
accepted unchanged-successor packet for every paper-safe state. No-op
feasibility is separate from general successor availability.

## Paper-facing abstract wrappers

`RCP.finite_paper_preservation` combines, with all assumptions visible:

```text
paper-safe endpoint membership
accepted-prefix update admissibility
initial no-op availability
monotone and strict-witness progress
transported protected non-loss
composed endpoint recovery
Lyapunov/motion bound
ambiguity-collapse bound
transported self-model-relevance bound
```

`RCP.conditional_infinite_paper_trajectory_exists` constructs an infinite
accepted path with paper-safe states, paper-update-admissible steps, and no-op
availability, under both explicit `SuccessorAvailability` and `NoOpFeasible`.

## Concrete obligations still open

Exact Paper I mechanization still requires:

1. concrete refinement of `PaperSemantics` to the pinned `K_RCP^state` and
   `A_RCP` definitions;
2. conditional-expectation semantics for the Lyapunov monitor and identification
   of the motion charge;
3. concrete ambiguity and mutual-information definitions and transports;
4. finite KL and quantum-relative-entropy interpretations with support laws; and
5. a final paper-facing wrapper after those identifications.

Exact Paper II mechanization still requires substantive RCLM state, update,
certificate, checker, monitor, and recovery semantics and a proof that forgetting
an accepted RCLM packet preserves every theorem-relevant RCP object.

## Implemented public Gate A declarations

```lean
RCP.accepted_step_sound
RCP.finite_trajectory_closure
RCP.finite_trajectory_step_sound
RCP.finite_progress_monotone
RCP.finite_composed_nonloss_bound
RCP.finite_composed_recovery_bound
RCP.composedRecovery_nonexpansive
RCP.finite_endpoint_recovery_bound
RCP.finite_lyapunov_motion_bound
RCP.finite_ambiguity_collapse_bound
RCP.finite_self_model_relevance_bound
RCP.conditional_infinite_trajectory_exists
RCP.infinite_endpoint_recovery_prefix_bound
RCP.infinite_monitor_uniform_bounds
RCP.infinite_cumulative_motion_bounded
RCP.infinite_monitor_bounds_of_summable
RCP.infinite_cumulative_motion_bounded_of_summable
RCP.finite_paper_preservation
RCP.conditional_infinite_paper_trajectory_exists
```

Reserved for later gates:

```lean
RCLM.rclm_checker_refines_rcp
RCLM.rclm_architecture_successor_theorem
MainTheorem.mechanized_conditional_successor_closure
```
