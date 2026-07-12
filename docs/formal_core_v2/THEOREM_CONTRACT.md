# Formal Core v2 theorem contract

## Contract status

This document freezes the **abstract Gate A successor and preservation kernel**.
It is not, by itself, the exact statement of Paper I's `thm:main_rcp` or any
Paper II architecture theorem. The initial comparison is in
`GATE_A_PAPER_ALIGNMENT_AUDIT.md`; later resolutions are recorded in
`GATE_A_ALIGNMENT_RESOLUTION_LOG.md`.

Current status:

```text
abstract one-step contract: implemented
abstract finite trajectory composition: implemented
abstract endpoint recovery composition: implemented
abstract finite paper-monitor composition: implemented
abstract conditional infinite trajectory construction: implemented
uniform finite-prefix monitor bounds under explicit budget caps: implemented
clean build and proof-admission audit: passed
exact Paper I/Paper II agreement: not yet achieved
```

## Ordinary abstract mathematical statement

Let `M_t` be an admissible predecessor system state at recursive time `t`. Let
`u_t` be a proposed typed update, let `M_{t+1}` be the candidate's claimed
successor state, and let `c_t` be a certificate packet. Let the formal kernel
supply:

- typed successor semantics `Apply(M_t,u_t)`;
- protected distinctions and explicit cross-time transport;
- a nonconstant divergence/information interface;
- declared quantitative loss budgets;
- a constructive recovery map tied to the candidate update;
- a state distance and one-step recovery budget;
- a protected-invariant predicate;
- a progress functional and strict-witness predicate;
- computed certificate residuals;
- trust/verifier, resource, and reality/uncertainty predicates; and
- an admissible successor domain.

For a trusted checker `Check`, the abstract one-step target is:

```text
Admissible(M_t)
∧ ProtectedInvariant(M_t)
∧ Check(M_t,u_t,M_{t+1},c_t) = true

⇒

M_{t+1} = Apply(M_t,u_t)
∧ every computed residual is nonpositive
∧ every declared protected distinction is preserved within the loss budget
∧ Recover(M_t,u_t,M_{t+1}) returns within the recovery budget of M_t
∧ ProtectedInvariant(M_{t+1})
∧ Progress(M_t) ≤ Progress(M_{t+1})
∧ (StrictWitness(M_t,u_t,M_{t+1},c_t)
    ⇒ Progress(M_t) < Progress(M_{t+1}))
∧ TrustValid(M_t,u_t,M_{t+1},c_t)
∧ ResourceValid(M_t,u_t,M_{t+1},c_t)
∧ RealityContained(M_t,u_t,M_{t+1},c_t)
∧ Admissible(M_{t+1}).
```

The checker theorem is a soundness theorem. It is not, by itself, a theorem that
an improving candidate exists, that a generator covers a witness, or that a
paper-specific packet can be constructed.

## Abstract finite composition contract

For a finite sequence

```text
M_0 --(u_0,c_0)--> M_1 -- ... --> M_N
```

whose initial state is admissible and invariant-preserving and whose transitions
are accepted, the project proves:

1. every in-horizon state remains admissible and invariant-preserving;
2. every transition satisfies the complete one-step obligations;
3. progress is monotone;
4. transported protected values satisfy the additive loss-budget bound;
5. actual local recovery errors satisfy the aggregate local-budget bound;
6. strict progress follows at each step carrying a strict witness; and
7. under explicit recovery-composition laws, the rollback-order composed map
   recovers the initial state from the endpoint within the cumulative budget.

The endpoint theorem uses:

```lean
RCP.RecoveryCompositionLaws
RCP.composedRecovery
RCP.composedRecovery_nonexpansive
RCP.finite_endpoint_recovery_bound
```

The required laws are exactly zero self-distance, the triangle inequality, and
nonexpansiveness of every candidate-tied recovery map. They are not inferred
from checker soundness.

## Explicit Paper I monitor contract

`RCP.PreservationMonitors` supplies named data and laws for the quantitative
Paper I conclusions:

```text
lyapunov value
charged motion term
lyapunov error budget
unsupported ambiguity collapse
ambiguity error budget
self-model relevance value
cross-time relevance transport
relevance error budget
```

The intended concrete interpretation may set the motion charge to
`κ * E[d(M_{t+1},M_t)^2]`, but Gate A treats it as an explicit nonnegative
quantity whose one-step inequality must be proved from `StepObligations`.

The finite theorems are:

```lean
RCP.finite_lyapunov_motion_bound
RCP.finite_ambiguity_collapse_bound
RCP.finite_self_model_relevance_bound
```

A generic residual index is not silently identified with any of these monitors.
Concrete probability, ambiguity, and mutual-information meanings require later
refinement theorems.

## Abstract conditional infinite-horizon contract

The availability assumption remains explicit:

```text
SuccessorAvailability:
  for every admissible invariant-preserving state M,
  there exists a candidate and certificate accepted by the trusted checker.
```

Under this assumption and an initial domain state,
`RCP.conditional_infinite_trajectory_exists` constructs an infinite accepted
trajectory. Checker soundness does not imply this availability hypothesis.

Every finite prefix can be converted to `RCP.FiniteAcceptedTrajectory` by
`RCP.finitePrefixOfInfinite`, so it inherits endpoint recovery and all monitor
bounds. The public prefix and uniform-bound declarations include:

```lean
RCP.infinite_endpoint_recovery_prefix_bound
RCP.infinite_lyapunov_motion_prefix_bound
RCP.infinite_ambiguity_collapse_prefix_bound
RCP.infinite_self_model_relevance_prefix_bound
RCP.UniformMonitorBudgetCaps
RCP.infinite_monitor_uniform_bounds
RCP.infinite_cumulative_motion_bounded
```

`UniformMonitorBudgetCaps` is the explicit bounded-partial-sum premise. A
paper-facing theorem that retains standard analytic `Summable` wording must
prove that the concrete nonnegative error series supplies these caps.

## Exact Paper I wrapper obligations still open

An exact wrapper for Paper I `thm:main_rcp` must still provide:

1. a refinement between `Admissible ∧ ProtectedInvariant` and the paper's
   `K_RCP^state`;
2. a refinement between accepted `StepObligations` and the paper's
   `A_RCP(t,rho,Phi)` relation;
3. the no-op-feasibility premise, or a documented paper narrowing;
4. concrete conditional-expectation semantics for the Lyapunov monitor and
   concrete identification of the motion charge;
5. concrete ambiguity and self-model mutual-information semantics with valid
   transports;
6. a standard `Summable`-to-partial-sum-cap bridge if exact summability wording
   is retained;
7. finite KL and quantum-relative-entropy interpretations with support/domain
   laws; and
8. the final paper-facing theorem declaration with every assumption visible.

The endpoint recovery inference itself is no longer an open Gate A mismatch.
Concrete trace-distance/channel instances remain Gate B/C obligations.

## Exact Paper II refinement obligations

The RCLM architecture layer must define substantive state, update, certificate,
and checker semantics and prove that forgetting an accepted RCLM packet to RCP
preserves every theorem-relevant object:

```text
update application and typed successor
protected values and transports
loss and recovery budgets
state distance, recovery map, and recovery composition laws
progress and strict witnesses
paper monitor data and laws
residual evaluator
trust, resource, and reality predicates
predecessor/successor admissibility and invariants
checker result and checker soundness
```

Only after this refinement exists may the project introduce:

```lean
RCLM.rclm_checker_refines_rcp
RCLM.rclm_architecture_successor_theorem
```

## Lean-facing declarations

Implemented Gate A declarations include:

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
```

Reserved but not yet delivered:

```lean
RCLM.rclm_checker_refines_rcp
RCLM.rclm_architecture_successor_theorem
MainTheorem.mechanized_conditional_successor_closure
```

Implementation, build/audit status, paper alignment, and any narrowing are
recorded in the formalization manifest and theorem map.
