# Formal Core v2 theorem contract

## Contract status

This document freezes the implemented abstract Gate A kernel, the finite
classical Gate B reference, the substantive Gate B RCLM-to-RCP refinement, and
the conditional architecture-engine theorem. It does not claim exact identity
with every semantic object in Paper I or Paper II.

```text
abstract one-step contract: implemented
abstract finite and conditional infinite composition: implemented
endpoint recovery and quantitative monitor composition: implemented
finite classical/diagonal Gate B reference: complete
substantive Gate B RCLM-to-RCP refinement: implemented
conditional Paper II-facing architecture successor theorem: implemented
conditional architecture infinite trajectory: implemented with explicit availability
concrete Gate B direct-engine reference: implemented
finite-dimensional quantum Gate C: not complete
exact Paper I/Paper II agreement: not achieved
executable theorem-to-runtime refinement: not licensed
```

## Ordinary one-step mathematical contract

Let `M_t` be an admissible predecessor, `u_t` a typed update, `M_{t+1}`
the claimed successor, and `c_t` a certificate. For a trusted checker:

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

the project proves domain and invariant closure, complete per-step obligations,
progress composition, transported protected-value bounds, aggregate local
recovery accounting, and—under explicit recovery composition laws—a composed
endpoint rollback bound.

The endpoint theorem uses:

```lean
RCP.RecoveryCompositionLaws
RCP.composedRecovery
RCP.composedRecovery_nonexpansive
RCP.finite_endpoint_recovery_bound
```

The extra laws are visible: zero self-distance, triangle inequality, and
nonexpansiveness of every candidate-tied recovery map.

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

A concrete instance proves each one-step inequality from `StepObligations`.
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
accepted path. Every finite prefix inherits endpoint recovery and monitor
bounds. Standard `Summable` hypotheses are bridged to uniform partial-sum caps.

Checker soundness does not establish this availability premise.

## Paper-safe predicates and no-op premise

`RCP.PaperSemantics` carries paper-facing safe-state and update-admissibility
predicates with explicit equivalences to the kernel domain/invariant and
`StepObligations`. `RCP.AcceptedNoOp` and `RCP.NoOpFeasible` represent no-op
feasibility separately from successor availability.

## Gate B finite classical contract

### Information quantities

For `Distribution n` the actual quantities are:

```text
H(p)        = - Σ_i p_i log p_i
D_KL(p || q) =  Σ_i p_i log(p_i/q_i).
```

Under the explicit `SupportedBy` premise, KL is nonnegative and self-divergence
is zero. The binary distributions

```text
uniformBinary = (1/2, 1/2)
biasedBinary  = (3/4, 1/4)
```

have a proved strictly positive KL gap and therefore supply a nonconstant
`LawfulDivergence` instance.

### Conservative extension and exact recovery

The declared embedding adds one zero-mass head coordinate. The project proves
support, Shannon entropy, and KL preservation, and exact recovery by dropping
the new coordinate. This is not a theorem about every stochastic channel.

### Concrete checker and strict progress

The finite binary checker accepts exactly improvement and stability packets.
Acceptance yields the complete `StepObligations` bundle and an invalid successor
is rejected. Progress is actual reduction of KL distance to `biasedBinary`, so
the first accepted improvement is non-vacuously strict.

### Concrete monitor and trajectory scope

The binary monitor instance uses KL-to-target as Lyapunov value, KL-derived
progress increase as motion charge, a malformed-packet indicator for the scoped
collapse monitor, and finite target-fit/normalization evidence for relevance.
These meanings are not conditional expectation, semantic ambiguity, or mutual
information. The worked trajectory is:

```text
initial → target → target
```

## Substantive RCLM-to-RCP refinement contract

`RCLM.KernelRefinement` requires preservation of:

```text
state and typed update semantics
admissibility and protected invariants
protected values, transports, and budgets
state distance, recovery maps, and recovery budgets
progress and strict witnesses
computed residuals
trust, resource, and reality propositions
```

`RCLM.MonitorRefinement` preserves every named monitor quantity and transport.
`RCLM.CheckerRefinement` requires actual Boolean acceptance preservation. The
public transport theorems prove that complete RCLM obligations and recovery laws
refine to the complete RCP objects.

The concrete `RCLM.ClassicalBinary` checker additionally verifies that all
architecture fields equal the declared canonical state, update, successor, and
certificate encodings. Extra architecture data is therefore checked rather than
ignored.

## Conditional architecture-engine contract

### Explicit engine data

`RCLM.ArchitectureEngine` has separate relations for:

```text
witness-library coverage
generator proposal
certificate construction
candidate selection
successor realization
trust-anchor validity
resource authorization
```

It also requires proofs that realization agrees with typed update semantics,
trust and resource premises imply the corresponding kernel propositions,
accepted successors remain in the architecture theorem domain, and the trust
anchor remains valid at the successor.

`RCLM.ArchitectureEngineStep` packages an actual witness, proposal, certificate,
candidate, resource record, all relation evidence, and RCLM checker acceptance.

### One-step Paper II-facing inference

For an `ArchitecturePredecessor`, an `ArchitectureEngineStep`, the substantive
RCLM-to-RCP refinements, recovery laws, and monitor refinement:

```text
valid architecture predecessor
∧ witness covered
∧ proposal generated
∧ certificate constructed
∧ candidate selected
∧ successor realized
∧ trust anchor valid
∧ resource premise satisfied
∧ RCLM checker accepts

⇒

typed RCLM successor
∧ complete RCLM StepObligations
∧ forgotten core checker accepts
∧ complete forgotten RCP StepObligations
∧ preserved recovery-composition laws
∧ preserved monitor refinement
∧ successor remains in the architecture theorem domain
∧ successor remains admissible and invariant-preserving
∧ engine trust and resource validity
∧ trust-anchor preservation.
```

The corresponding theorem is:

```lean
RCLM.rclm_architecture_successor_theorem
```

This theorem is conditional on actual engine-stage evidence. It does not
construct a proposal from checker soundness.

### Conditional architecture recursion

`RCLM.ArchitectureSuccessorAvailability engine` states that every valid
architecture predecessor has a nonempty checker-accepted engine step carrying
all proposal/certificate/selection/realization/resource evidence.

Under that explicit premise:

```lean
RCLM.conditional_infinite_architecture_trajectory_exists
```

constructs an infinite architecture trajectory, and
`RCLM.infinite_architecture_step_result` supplies the one-step architecture
result at every time. The trajectory can be forgotten to both RCLM-checker and
core-checker accepted trajectories.

Availability is never derived from checker soundness.

## Concrete Gate B direct-engine reference

`RCLM.ClassicalBinary.architectureEngine` instantiates:

```text
strict-improvement and stable-continuation witnesses
improve and stabilize proposals
canonical certificates and candidates
one root trust anchor
explicit used/limit resources
realization by the typed RCLM update function
```

The concrete theorem

```lean
RCLM.ClassicalBinary.improvement_direct_engine_successor
```

proves the full architecture-successor result for the accepted KL-derived
improvement packet.

`RCLM.ClassicalBinary.architectureSuccessorAvailability` proves availability
only on the declared binary architecture domain. The resulting formal infinite
path performs one strict improvement and thereafter may use accepted stability
steps. It proves recursive domain closure and accepted continuation, not
indefinitely strict capability growth.

## Remaining exact-paper obligations

Exact Paper I/Paper II mechanization still requires:

1. exact refinement of paper safe-state and update-admissibility semantics;
2. probability/conditional-expectation and squared-motion identification;
3. semantic ambiguity and mutual-information definitions;
4. finite-dimensional quantum relative entropy and channel recovery;
5. line-by-line identification of Paper II generator, certifier, selector,
   realizer, witness-library, trust, resource, and viability objects;
6. any stronger useful-successor or strict-improvement completeness premise;
7. the final combined paper-facing wrapper.

## Public theorem surfaces

Gate A, Gate B, and RCLM declarations are audited separately. The RCLM surface
now includes:

```lean
RCLM.rclm_step_obligations_refine_rcp
RCLM.rclm_checker_refines_rcp
RCLM.rclm_checker_acceptance_preserved
RCLM.rclm_recovery_laws_refine_rcp
RCLM.rclm_monitor_refinement_valid
RCLM.rclm_architecture_successor_theorem
RCLM.conditional_infinite_architecture_trajectory_exists
RCLM.infinite_architecture_step_result
RCLM.ClassicalBinary.architectureSuccessorAvailability
RCLM.ClassicalBinary.improvement_direct_engine_successor
RCLM.ClassicalBinary.classical_infinite_architecture_trajectory_exists
RCLM.ClassicalBinary.classical_infinite_architecture_step_result
```

Reserved for later closure:

```lean
MainTheorem.mechanized_conditional_successor_closure
```
