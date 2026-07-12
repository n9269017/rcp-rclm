# RCP/RCLM Formal Core v2 — Mechanized Conditional Successor Theorem Closure

This is a separate pinned Lean project. It does not overwrite or silently
strengthen the historical canonical v1 project at
`lean/rcp_rclm_can_lean4/`.

## Current status

```text
Gate A — abstract theorem kernel: complete and clean-CI audited
Gate B — finite classical/diagonal instantiation: definitions started; not complete
Gate C — finite-dimensional quantum instantiation: not yet claimed
RCLM architecture refinement: typed interfaces and partial contract only
Exact Paper I theorem mechanization: not yet claimed
Exact Paper II architecture theorem mechanization: not yet claimed
Python checker/generator/closed loop: prohibited at this phase
External benchmark result: none
```

Abstract Gate A completion means that the theorem kernel now contains explicit
one-step checker soundness, finite and conditional infinite composition,
rollback-order endpoint recovery, named quantitative monitor composition,
standard summability-to-uniform-prefix bounds, paper-safe/update-admissibility
refinement data, and no-op feasibility. It does not identify those abstract
objects with finite KL, quantum relative entropy, trained RCLM states, or
empirical systems.

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

## Authoritative build

The repository workflow performs:

```text
paper-source and theorem-surface pin verification
pinned dependency resolution
clean Lean build
no-sorry/no-admit source scan
project-local axiom scan
#print axioms audit for the public Gate A theorem surface
artifact upload
```

The clean GitHub workflow is authoritative. Local interrupted or corrupted
mathlib caches are not evidence that a synchronized source head fails.

## Claim discipline

Abstract Gate A completion is not:

```text
a finite-KL theorem
a quantum-relative-entropy theorem
a substantive RCLM refinement
a direct RSI engine
a Python implementation
an empirical or benchmark result
```

No Python checker, generator, successor loop, or benchmark adapter is licensed
until the remaining Gate B and RCLM refinement conditions in
`docs/formal_core_v2/EXIT_CRITERIA.md` are satisfied.
