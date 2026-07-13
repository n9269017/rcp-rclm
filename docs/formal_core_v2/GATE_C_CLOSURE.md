# Gate C closure — selected finite-dimensional diagonal quantum reference

## Verdict

Gate C is complete at the declared finite-dimensional commuting/diagonal reference scope.

The completed scope is a two-level complex matrix representation whose certified states are diagonal density matrices. The selected channels are the identity channel and a basis-swap channel. The information quantities are spectral von Neumann entropy and spectral quantum relative entropy, definitionally reduced to Shannon entropy and finite KL divergence on the diagonal spectrum.

This closure does not claim arbitrary noncommuting density matrices, arbitrary completely positive trace-preserving maps, a general matrix logarithm, a general data-processing inequality, Petz recovery, infinite-dimensional operator algebras, or exact identity with every quantum statement in Paper I or Paper II.

## Immutable environment

```text
Lean:    leanprover/lean4:v4.31.0
mathlib: fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
Paper I blob:  084eae21d252d205d2012b62744c1506644e3e58
Paper II blob: 9b51be8294ad79fd4f63522b01e0f617f0bf2ffd
```

## Implemented modules

```text
RCP/QuantumDensity.lean
RCP/QuantumKernel.lean
RCP/QuantumChannels.lean
RCP/QuantumFinite.lean
RCLM/QuantumBinary.lean
```

The public facades import the selected quantum modules through `RCP.lean`, `RCLM.lean`, and `MainTheorem.lean`.

## Density-matrix reference

`DiagonalDensityMatrix n` contains a normalized nonnegative finite distribution and exposes the complex matrix

```text
Matrix.diagonal (fun i => distribution.mass i : Matrix (Fin n) (Fin n) ℂ).
```

For every selected density the formalization proves:

```text
Hermitian matrix
positive semidefinite matrix
trace equal to one
finite dimension
```

The proof objects are collected by `DensityMatrixEvidence`.

`PositiveDiagonalDensityMatrix n` additionally carries strict positivity of every spectral mass. This discharges the support premise used by the selected quantum-relative-entropy nonnegativity theorem.

## Entropy and divergence

The selected definitions are:

```text
vonNeumannEntropy ρ
  = -∑ᵢ pᵢ log pᵢ

quantumRelativeEntropy ρ σ
  = ∑ᵢ pᵢ log (pᵢ / qᵢ)
```

where `p` and `q` are the diagonal spectra of `ρ` and `σ`.

The compiled theorem surface includes:

```text
quantumRelativeEntropy_nonnegative
quantumRelativeEntropy_self
positiveQuantumRelativeEntropy_nonnegative
positiveQuantumRelativeEntropy_self
source_target_quantumRelativeEntropy
source_target_quantumRelativeEntropy_pos
source_target_vonNeumannEntropy_equal
```

Nonnegativity for arbitrary diagonal densities retains the explicit support hypothesis. Strictly positive spectral states provide that support constructively.

The source and target reference states have spectra `(1/4, 3/4)` and `(3/4, 1/4)`. Their quantum relative entropy is proved equal to `(1/2) * log 3`, hence strictly positive. The protected/progress quantity is therefore nonconstant.

## Selected channels and constructive recovery

`FiniteDiagonalChannel n` packages:

```text
a state transformer on diagonal density matrices
a complex-linear matrix map
matrix-action agreement
trace preservation
Hermitian preservation
positive-semidefinite preservation
```

The concrete channel family contains:

```text
identityChannel
swapChannel
selectedChannel
selectedRecoveryChannel
```

For the selected update family the formalization proves:

```text
selectedChannel_state_action
selectedChannel_densityEvidence
selectedChannel_recovery_exact
selectedChannel_vonNeumannEntropy_preserving
selectedChannel_quantumRelativeEntropy_preserving
```

The recovery channel is tied to the actual update. `stay` recovers by identity and `swap` recovers by applying the involutive basis swap again.

This is exact recovery for the selected reversible channel family. It is not a general approximate-recovery theorem.

## Concrete checker and successor obligations

The quantum kernel has substantive state, update, certificate, residual, trust, resource, and reality-containment objects.

The accepted packet grammar is exactly:

```text
source + swap + target + improvement certificate
target + stay + target + stability certificate
```

The compiled checker surface includes:

```text
quantumCheck_eq_true_iff
quantumCheck_rejects_invalidCandidate
source_improvement_obligations
target_stability_obligations
quantum_checker_refines_kernel
```

Thus Boolean acceptance implies the complete `StepObligations` record. Residuals depend on the candidate transition and packet acceptance; they are not fixed at zero. Reality containment excludes an explicit outside-state packet and is not definitionally `True`.

## Progress, monitors, and trajectory

The progress functional is the positive source-to-target quantum-relative-entropy gap minus the current quantum relative entropy to the target.

The formalization proves:

```text
quantumProgress_source
quantumProgress_target
quantumProgress_source_lt_target
quantumLyapunov_motion_step
quantumUnsupportedCollapse_step
quantumRelevance_step
```

The finite accepted trajectory is:

```text
source --swap/improvement--> target --stay/stability--> target
```

Its compiled consequences include:

```text
quantumWorkedTrajectory_first_step_strict
quantumWorkedTrajectory_endpoint_recovery
quantumWorkedTrajectory_lyapunov_motion_bound
quantumWorkedTrajectory_relevance_bound
```

Finite composition is therefore instantiated concretely. Conditional infinite closure continues to use the abstract Gate A theorem with explicit `SuccessorAvailability`; checker soundness alone is not used to infer successor existence or indefinitely strict progress.

## RCLM-to-RCP quantum refinement

`RCLM/QuantumBinary.lean` supplies substantive architecture states, updates, certificate packets, canonical forget/lift maps, a concrete RCLM checker, recovery laws, monitors, and explicit density/channel identifications.

The refinement preserves:

```text
typed successor semantics
admissibility and protected invariants
protected values and transports
state distance and candidate-tied recovery
progress and strict witnesses
computed residuals
trust, resource, and reality propositions
complete StepObligations
checker acceptance
recovery-composition laws
Lyapunov, ambiguity, and relevance monitors
density-matrix evidence
forward-channel realization
exact selected recovery
entropy preservation
quantum-relative-entropy preservation
```

The principal architecture theorem is:

```text
RCLM.QuantumBinary.accepted_quantum_architecture_successor
```

with concrete improvement and stability corollaries.

## Dedicated theorem-axiom audit

The selected Gate C theorem surface is audited by:

```text
docs/formal_core_v2/audit/GateCAxiomAudit.lean
```

The pinned workflow verifies the audit independently from the Gate A, Gate B, and earlier RCLM audits.

First complete Gate C audit record:

```text
branch source head: 9250d1fa40179738ca161dbd9b1d9310f9c901ce
pull-request checkout commit: de60b043147906a411a8b827ce41120a0e2f4e1c
workflow run: 29246781311
artifact: formal-core-v2-audit-29246781311-1
artifact SHA-256: 38d2776534e94a6ebb6281924e30133ff9c35d4edbbe34393b4f1d1c48c03072
audited Gate C declarations: 32
```

The audit reports no admitted-proof token, no project-local axiom declaration, and no `sorryAx`. The union of reported foundational dependencies is:

```text
propext
Classical.choice
Quot.sound
```

`quantumCheck_rejects_invalidCandidate` is reported axiom-free. The other declarations use only the documented Lean/mathlib foundational principles above.

## Closure checklist

```text
[x] exact Lean and mathlib revisions pinned
[x] actual complex matrix-valued density representation
[x] Hermitian, positive-semidefinite, and trace-one evidence
[x] actual spectral von Neumann entropy
[x] actual support-aware quantum relative entropy
[x] nonconstant positive quantum-relative-entropy witness
[x] selected matrix-valued channels
[x] exact candidate-tied recovery
[x] substantive residual, trust, resource, and reality gates
[x] concrete Boolean checker soundness
[x] invalid candidate rejection
[x] non-vacuous strict progress
[x] finite accepted trajectory
[x] endpoint recovery and monitor composition
[x] substantive RCLM-to-RCP quantum refinement
[x] source scan contains no admitted proof token
[x] no project-local axiom declaration
[x] dedicated Gate C theorem-axiom audit
[x] clean pinned GitHub CI
```

## Explicit non-implications

This closure does not establish:

```text
diagonal quantum relative entropy = general noncommuting matrix QRE
selected swap/identity channels = arbitrary CPTP channels
exact reversible recovery = Petz or approximate recovery
one strict finite step = indefinitely strict recursive improvement
conditional infinite closure = checker-derived successor availability
formal progress = external benchmark improvement
finite formal closure = empirical or autonomous RSI
selected quantum refinement = exact full Paper I/Paper II identity
```
