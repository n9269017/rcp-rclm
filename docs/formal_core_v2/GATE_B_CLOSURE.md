# Formal Core v2 — Gate B finite classical/diagonal closure

## Closure decision

Gate B is complete at the declared finite classical reference scope.

```text
Gate B finite distributions and information quantities: complete
Gate B conservative extension and constructive recovery: complete
Gate B non-vacuous KL-derived strict progress: complete
Gate B concrete packet grammar and trusted checker: complete
Gate B finite worked trajectory: complete
Gate B concrete monitor instance: complete at the scoped binary meanings below
Gate B clean CI and proof-admission audit: passed
Exact Paper I main-theorem equivalence: not claimed
Paper II substantive RCLM refinement: not claimed
Gate C finite-dimensional quantum theorem: not claimed
Executable RSI: not licensed
```

The closure is deliberately narrower than the full statements of Paper I and
Paper II. It establishes a nontrivial finite information-theoretic instance of
the abstract Gate A kernel; it does not identify the instance with arbitrary
learned systems, general stochastic channels, the paper's full probability
space, semantic ambiguity, mutual information, or quantum relative entropy.

## Concrete finite information layer

`RCP.ClassicalFinite` defines a normalized nonnegative finite distribution
`Distribution n`, an explicit support relation `SupportedBy`, actual Shannon
entropy, and actual finite KL divergence:

```text
H(p)       = - Σ_i p_i log p_i
D_KL(p||q) =   Σ_i p_i log(p_i/q_i)
```

The formalized laws include:

```lean
RCP.ClassicalFinite.klDivergence_nonnegative
RCP.ClassicalFinite.klDivergence_self
RCP.ClassicalFinite.positiveKLDivergence_nonnegative
RCP.ClassicalFinite.positiveKLDivergence_self
```

KL nonnegativity is proved under the explicit support condition
`SupportedBy p q`; zero-mass and denominator-support cases are not hidden.

## Nonconstant information witness

The binary reference distributions are:

```text
uniformBinary = (1/2, 1/2)
biasedBinary  = (3/4, 1/4)
```

The project proves:

```text
D_KL(uniformBinary || biasedBinary)
  = (1/2) log(4/3)
  > 0.
```

This yields `binaryKLDivergence : LawfulDivergence
(PositiveDistribution 2)` with a proved nonconstant witness. The information
quantity is not a fixed placeholder.

## Conservative extension and recovery

The declared conservative extension is the zero-coordinate embedding:

```text
(p_0, ..., p_{n-1})
  ↦
(0, p_0, ..., p_{n-1}).
```

The recovery map removes the new head coordinate. The following are proved:

```lean
RCP.ClassicalFinite.supportedBy_extendByZero
RCP.ClassicalFinite.shannonEntropy_extendByZero
RCP.ClassicalFinite.klDivergence_extendByZero
RCP.ClassicalFinite.recover_extendByZero
RCP.ClassicalFinite.conservative_extension_recovery
```

Thus the extension preserves the support relation, Shannon entropy, and KL
exactly and admits exact constructive predecessor recovery. This theorem is for
the stated embedding; it is not a data-processing theorem for every stochastic
channel.

## Concrete kernel and packet grammar

`RCP.ClassicalFinite.BinaryState` has three states:

```text
outside
initial
target
```

The admissible trajectory uses the latter two. Updates, certificates, and
residual obligations are finite inductive types. The Boolean checker accepts
exactly two packet forms:

```text
initial -- improve / improvement certificate --> target
target  -- stay    / stability certificate   --> target
```

The exact Boolean-to-proposition correspondence is:

```lean
RCP.ClassicalFinite.binaryCheck_eq_true_iff
```

The invalid candidate claiming `initial` as the result of the improvement
update is rejected by:

```lean
RCP.ClassicalFinite.binaryCheck_rejects_invalidCandidate
```

The concrete trusted-checker refinement boundary is:

```lean
RCP.ClassicalFinite.binary_checker_refines_kernel
```

It proves that checker acceptance, together with the predecessor domain and
invariant premises, yields the complete abstract `StepObligations` bundle.

## Non-vacuous strict progress

The progress functional is tied to actual KL distance from the declared target:

```text
Progress(state)
  = D_KL(uniformBinary || biasedBinary)
      - D_KL(distribution(state) || biasedBinary).
```

The accepted improvement step satisfies:

```text
Progress(initial) < Progress(target)
```

because the first KL is strictly positive and the target self-divergence is
zero. This is not strict progress by adding an index or incrementing a counter.

## Recovery composition laws

The binary kernel uses the discrete state distance. The project proves zero
self-distance and the triangle inequality and supplies candidate-tied recovery
nonexpansiveness through:

```lean
RCP.ClassicalFinite.binaryStateDistance_triangle
RCP.ClassicalFinite.binaryRecoveryCompositionLaws
```

The worked trajectory therefore instantiates the Gate A endpoint theorem in:

```lean
RCP.ClassicalFinite.binaryWorkedTrajectory_endpoint_recovery
```

## Concrete monitor meanings

`binaryPreservationMonitors` supplies a concrete finite monitor instance:

```text
Lyapunov value:
  KL distance from the state's binary distribution to biasedBinary

Motion charge:
  the nonnegative accepted-step increase in KL-derived progress

Lyapunov error:
  zero in this exact finite reference instance

Unsupported-collapse indicator:
  one exactly for a malformed certificate, zero otherwise

Ambiguity error:
  zero because accepted step obligations exclude malformed certificates

Relevance values:
  targetFit      = KL-derived progress
  normalization  = constant normalization witness 1

Relevance transport:
  identity on the two finite relevance labels

Relevance error:
  zero in this exact finite reference instance
```

The corresponding one-step and worked-trajectory theorems are:

```lean
RCP.ClassicalFinite.binaryLyapunov_motion_step
RCP.ClassicalFinite.binaryUnsupportedCollapse_step
RCP.ClassicalFinite.binaryRelevance_step
RCP.ClassicalFinite.binaryWorkedTrajectory_lyapunov_motion_bound
RCP.ClassicalFinite.binaryWorkedTrajectory_ambiguity_bound
RCP.ClassicalFinite.binaryWorkedTrajectory_relevance_bound
```

These are concrete classical meanings, but they are not asserted to be Paper
I's conditional expectation, semantic ambiguity, or self-model mutual
information. Those identifications remain separate cross-gate obligations.

## Worked accepted trajectory

The finite trajectory is:

```text
initial → target → target
```

It is accepted by the concrete checker at both transitions, linked to the
actual update semantics, and strictly improves at the first step. It also
instantiates the endpoint-recovery and monitor-composition theorems.

## Authoritative validation

The synchronized finite-reference theorem source at branch head
`c33087041a8588f11f85c0c108046701269f291f` passed the pinned Linux workflow:

```text
Workflow run:       29208133524
PR merge-test SHA:  fb57537f2bb141987fcd10a8621876a034b15915
Build:              1942 jobs, success
No sorry/admit:     pass
Project-local axiom scan: pass
Gate A axiom audit: pass
Gate B axiom audit: pass
Artifact:           formal-core-v2-audit-29208133524-1
Artifact SHA-256:   dd718909eb0e683e7e92fabf76eb773f8368a1437148f2c65ccfa10d3570930c
```

The Gate B audit covers 22 public declarations. No declaration reports
`sorryAx`. The axiom union reported by Lean is:

```lean
[propext, Classical.choice, Quot.sound]
```

`binaryCheck_eq_true_iff` reports only `[propext]`, and
`binaryCheck_rejects_invalidCandidate` reports no axioms.

## Proof and claim boundary

Gate B closure does not imply:

```text
exact Paper I main-theorem equivalence
arbitrary-channel KL data processing
quantum relative entropy or density-matrix recovery
full RCLM-to-RCP refinement
RCLM checker or architecture theorem
successor availability or generator completeness
Python checker/generator correctness
executable or empirical recursive self-improvement
external benchmark performance
```

The next formal phase is the substantive RCLM-to-RCP refinement at the Gate B
classical scope, followed by the finite-dimensional quantum strengthening in
Gate C.