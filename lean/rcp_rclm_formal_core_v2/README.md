# RCP/RCLM Formal Core v2 — Mechanized Conditional Successor Theorem Closure

This is a separate pinned Lean project. It does not overwrite or silently
strengthen the historical canonical v1 project at
`lean/rcp_rclm_can_lean4/`.

## Current status

```text
Gate A — abstract theorem kernel: complete and clean-CI audited
Gate B — finite classical/diagonal reference: complete at declared scope
Gate C — finite-dimensional quantum instantiation: not yet claimed
RCLM architecture refinement: typed interfaces and partial contract only
Exact Paper I theorem mechanization: not yet claimed
Exact Paper II architecture theorem mechanization: not yet claimed
Python checker/generator/closed loop: prohibited at this phase
External benchmark result: none
```

Gate A supplies the conditional successor theorem kernel. Gate B now supplies a
nontrivial finite classical instance with actual Shannon/KL quantities,
support-aware KL laws, conservative extension and exact recovery, KL-derived
strict progress, a concrete checker refining the kernel, scoped classical
monitors, and a worked accepted trajectory.

Gate B completion is not full Paper I/Paper II equivalence. The exact closure
boundary is recorded in `docs/formal_core_v2/GATE_B_CLOSURE.md`.

## Exact dependency pins

```text
Lean:    leanprover/lean4:v4.31.0
mathlib: fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
```

`lake-manifest.json` is committed and pins the complete dependency graph.

## The central one-step contract

For an admissible predecessor state, candidate successor, and certificate packet,
trusted-checker acceptance implies:

```text
typed successor validity
computed residual nonpositivity
quantitative protected-distinction non-loss
constructive candidate-tied recovery
protected-invariant preservation
progress nondecrease
strict progress when a strict witness is certified
trust/verifier validity
resource validity
reality/uncertainty containment
successor-domain admissibility
```

The kernel itself excludes globally constant protected values, globally constant
residual evaluators, and an identically true reality-containment gate.

## Gate A composition delivered

```text
finite accepted-trajectory domain/invariant closure
finite progress composition
transported protected-value loss-budget composition
aggregate local recovery accounting
composed endpoint rollback under explicit metric/nonexpansive laws
finite Lyapunov/motion composition
finite ambiguity-collapse composition
finite transported self-model-relevance composition
conditional infinite accepted path under explicit SuccessorAvailability
finite-prefix endpoint and monitor preservation on infinite paths
standard Summable-to-tsum-cap bridge
explicit PaperSemantics equivalences
explicit accepted NoOpFeasible premise
finite_paper_preservation wrapper
conditional_infinite_paper_trajectory_exists wrapper
```

Checker soundness is not a successor-existence or direct-engine theorem.

## Gate B finite classical reference

### Information quantities

```text
Distribution n:
  nonnegative finite masses with total mass one

H(p):
  - Σ_i p_i log p_i

D_KL(p||q):
  Σ_i p_i log(p_i/q_i)
```

KL nonnegativity is proved under explicit denominator-support coverage. The
uniform and biased binary distributions produce a strictly positive, nonconstant
KL witness.

### Conservative extension

```text
(p_0, ..., p_{n-1})
  ↦
(0, p_0, ..., p_{n-1})
```

The extension preserves support, Shannon entropy, and KL exactly, and dropping
the new coordinate recovers the predecessor exactly.

### Concrete checker and strict progress

The finite checker accepts only:

```text
initial -- improve / improvement certificate --> target
target  -- stay    / stability certificate   --> target
```

Acceptance refines to the complete `StepObligations` bundle. An invalid claimed
successor is rejected. Progress is reduction in actual KL distance to the target,
so the first accepted step is strictly improving for an information-theoretic
reason rather than because an index was added.

### Concrete monitors

The binary monitor instance uses KL-to-target as its Lyapunov value, accepted
KL-derived progress increase as its motion charge, a malformed-certificate
indicator as its finite unsupported-collapse quantity, and target-fit plus
normalization evidence as its finite relevance labels. These are scoped finite
meanings, not claims of conditional expectation, semantic ambiguity, or mutual
information.

### Worked trajectory

```text
initial → target → target
```

The trajectory is checker accepted, update linked, strictly improves at its first
step, and instantiates endpoint recovery and all three finite monitor bounds.

## Module layout

```text
RcpRclmFormalCoreV2/
  RCP/
    Types.lean
    ProtectedDistinctions.lean
    RelativeEntropy.lean
    Recovery.lean
    Progress.lean
    Certificates.lean
    Checker.lean
    Trajectory.lean
    Monitors.lean
    InfiniteHorizon.lean
    Summability.lean
    PaperContract.lean
    ClassicalFinite.lean
    ClassicalBinary.lean
    QuantumFinite.lean
  RCLM/
    State.lean
    Update.lean
    CertificatePacket.lean
    Refinement.lean
    ArchitectureTheorem.lean
  RCP.lean
  RCLM.lean
  MainTheorem.lean
```

## Authoritative build and audit

The repository workflow performs:

```text
paper-source and theorem-surface pin verification
pinned dependency resolution
clean Lean build
no-sorry/no-admit source scan
project-local axiom scan
#print axioms audit for the public Gate A theorem surface
#print axioms audit for the public Gate B theorem surface
combined artifact upload
```

The clean GitHub workflow is authoritative. Local interrupted or corrupted
mathlib caches are not evidence that a synchronized source head fails.

## Claim discipline

Gate A plus Gate B completion is not:

```text
exact Paper I main-theorem equivalence
a finite-dimensional quantum-relative-entropy theorem
a substantive RCLM refinement
a direct RSI engine
a Python implementation
an empirical or benchmark result
```

No Python checker, generator, successor loop, or benchmark adapter is licensed
until the substantive RCLM refinement and remaining conditions in
`docs/formal_core_v2/EXIT_CRITERIA.md` are satisfied.