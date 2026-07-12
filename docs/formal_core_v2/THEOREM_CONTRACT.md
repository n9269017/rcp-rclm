# Formal Core v2 theorem contract

## Contract status

This document freezes the complete abstract Gate A successor/preservation kernel
and the declared finite classical Gate B reference instance. It is not, by
itself, the exact concrete statement of Paper I's `thm:main_rcp` or any Paper II
architecture theorem.

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
finite classical/diagonal Gate B reference: complete
substantive RCLM refinement: not yet complete
finite-dimensional quantum Gate C: not yet complete
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

## Quantitative monitor contract

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

A concrete instance must prove every one-step inequality from
`StepObligations`; a generic residual is never silently reinterpreted as a named
monitor. Finite composition is provided by:

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
`RCP.finitePrefixOfInfinite` and the infinite-prefix theorems. Standard
`Summable` hypotheses are bridged to uniform partial-sum caps by:

```lean
RCP.SummableMonitorBudgets
RCP.SummableMonitorBudgets.toUniformMonitorBudgetCaps
RCP.infinite_monitor_bounds_of_summable
RCP.infinite_cumulative_motion_bounded_of_summable
```

## Paper-safe predicates and no-op premise

`RCP.PaperSemantics` carries paper-facing `StateSafe` and `UpdateAdmissible`
predicates with explicit equivalences to the kernel domain/invariant and
`StepObligations`. The equivalences are concrete refinement obligations, not
consequences of the names.

`RCP.AcceptedNoOp` and `RCP.NoOpFeasible` represent the no-op premise as an
accepted unchanged-successor packet for every paper-safe state. No-op feasibility
is separate from general successor availability.

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

## Gate B finite classical contract

### Distributions and information quantities

For `Distribution n`:

```text
mass_i ≥ 0
Σ_i mass_i = 1
```

The actual finite quantities are:

```text
H(p)       = - Σ_i p_i log p_i
D_KL(p||q) =   Σ_i p_i log(p_i/q_i).
```

`SupportedBy p q` requires every positive numerator mass to have a positive
denominator mass. Under that premise:

```lean
RCP.ClassicalFinite.klDivergence_nonnegative
```

proves `0 ≤ D_KL(p||q)`, and `klDivergence_self` proves self-divergence zero.

### Nonconstant binary witness

The concrete distributions

```text
uniformBinary = (1/2, 1/2)
biasedBinary  = (3/4, 1/4)
```

satisfy:

```text
D_KL(uniformBinary || biasedBinary)
  = (1/2) log(4/3)
  > 0.
```

They therefore define a nonconstant `LawfulDivergence` instance.

### Conservative extension and exact recovery

The declared embedding adds one zero-mass head coordinate. The project proves:

```text
support is preserved
Shannon entropy is preserved exactly
KL divergence is preserved exactly
dropping the new coordinate recovers the predecessor exactly
```

through:

```lean
RCP.ClassicalFinite.shannonEntropy_extendByZero
RCP.ClassicalFinite.klDivergence_extendByZero
RCP.ClassicalFinite.recover_extendByZero
RCP.ClassicalFinite.conservative_extension_recovery
```

No claim is made here about every stochastic channel.

### Concrete binary kernel and checker

The finite state, update, certificate, and residual types define a concrete
`RCP.Kernel`. The checker accepts exactly the improvement and stability packet
grammar. Its refinement theorem is:

```lean
RCP.ClassicalFinite.binary_checker_refines_kernel
```

so accepted concrete packets yield the complete abstract `StepObligations`.
The invalid claimed successor is explicitly rejected.

### KL-derived strict progress

The progress functional is:

```text
Progress(state)
  = D_KL(uniformBinary || biasedBinary)
      - D_KL(distribution(state) || biasedBinary).
```

The accepted improvement step strictly raises this functional because the
initial KL gap is positive and target self-divergence is zero. Strict progress
is therefore not index growth.

### Concrete recovery and monitor refinement

The binary state distance is the discrete metric. `binaryRecoveryCompositionLaws`
proves the exact laws needed by `finite_endpoint_recovery_bound`.

`binaryPreservationMonitors` uses:

```text
KL-to-target as Lyapunov value
accepted KL-derived progress increase as motion charge
zero Lyapunov error
malformed-certificate indicator as unsupported collapse
zero ambiguity error on valid packets
target-fit progress and normalization evidence as relevance labels
identity relevance transport
zero relevance error
```

These meanings are exact for the finite binary reference. They are not claimed
to be conditional expectation, semantic ambiguity, or mutual information.

### Worked trajectory

`binaryWorkedTrajectory` is the accepted finite path:

```text
initial → target → target
```

Its first transition has strict KL-derived progress and it instantiates endpoint
recovery plus all three finite monitor bounds.

## Concrete obligations still open

Exact Paper I mechanization still requires:

1. concrete refinement of `PaperSemantics` to the pinned state-safe and
   update-admissibility definitions;
2. conditional-expectation and squared-motion semantics beyond the finite KL
   reference;
3. semantic ambiguity and mutual-information definitions and transports;
4. finite-dimensional quantum relative entropy and channel recovery; and
5. a final paper-facing wrapper after those identifications.

Exact Paper II mechanization still requires substantive RCLM state, update,
certificate, checker, monitor, and recovery semantics and a proof that forgetting
an accepted RCLM packet preserves every theorem-relevant RCP object.

## Implemented public declarations

Gate A public declarations are audited in `GateAAxiomAudit.lean`. Gate B public
declarations are audited in `GateBAxiomAudit.lean`, including:

```lean
RCP.ClassicalFinite.klDivergence_nonnegative
RCP.ClassicalFinite.shannonEntropy_extendByZero
RCP.ClassicalFinite.klDivergence_extendByZero
RCP.ClassicalFinite.conservative_extension_recovery
RCP.ClassicalFinite.binaryCheck_eq_true_iff
RCP.ClassicalFinite.binary_checker_refines_kernel
RCP.ClassicalFinite.binaryLyapunov_motion_step
RCP.ClassicalFinite.binaryUnsupportedCollapse_step
RCP.ClassicalFinite.binaryRelevance_step
RCP.ClassicalFinite.binaryWorkedTrajectory_first_step_strict
RCP.ClassicalFinite.binaryWorkedTrajectory_endpoint_recovery
RCP.ClassicalFinite.binaryWorkedTrajectory_lyapunov_motion_bound
RCP.ClassicalFinite.binaryWorkedTrajectory_ambiguity_bound
RCP.ClassicalFinite.binaryWorkedTrajectory_relevance_bound
```

Reserved for later gates:

```lean
RCLM.rclm_checker_refines_rcp
RCLM.rclm_architecture_successor_theorem
MainTheorem.mechanized_conditional_successor_closure
```