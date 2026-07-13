# RCP/RCLM Formal Core v2 — Mechanized Conditional Successor Theorem Closure

This is a separate pinned Lean project. It does not overwrite or silently
strengthen the historical canonical v1 project at
`lean/rcp_rclm_can_lean4/`.

## Current status

```text
Gate A — abstract theorem kernel: complete and clean-CI audited
Gate B — finite classical/diagonal reference: complete at declared scope
Substantive Gate B RCLM-to-RCP refinement: implemented and audited
Conditional RCLM architecture successor/direct-engine theorem: implemented
Concrete Gate B direct-engine reference: implemented
Conditional infinite architecture trajectory: implemented with explicit availability
Gate C — finite-dimensional quantum instantiation: not claimed
Exact Paper I theorem mechanization: not claimed
Exact Paper II theorem mechanization: not claimed
Python checker/generator/closed loop: not licensed
External benchmark result: none
```

Gate A supplies the conditional successor kernel. Gate B supplies actual
Shannon/KL quantities, conservative extension, exact recovery, KL-derived strict
progress, a concrete checker, scoped monitors, and a worked trajectory. The RCLM
layers now preserve the theorem-relevant Gate A/B objects and provide a
conditional architecture-engine theorem with explicit generator, certifier,
selector, realizer, witness, trust, resource, domain, and availability premises.

The exact boundaries are recorded in:

```text
docs/formal_core_v2/GATE_B_CLOSURE.md
docs/formal_core_v2/RCLM_GATE_B_REFINEMENT_STATUS.md
docs/formal_core_v2/RCLM_DIRECT_ENGINE_STATUS.md
```

## Exact dependency pins

```text
Lean:    leanprover/lean4:v4.31.0
mathlib: fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
```

`lake-manifest.json` pins the complete dependency graph.

## One-step RCP contract

For an admissible invariant-preserving predecessor, trusted-checker acceptance
implies:

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

The kernel excludes globally constant protected values, globally constant
residual evaluators, and universally true reality containment.

## Gate A composition

```text
finite accepted-trajectory domain/invariant closure
finite progress composition
transported protected-value loss-budget composition
aggregate local recovery accounting
composed endpoint rollback under explicit laws
finite Lyapunov/motion composition
finite ambiguity-collapse composition
finite transported relevance composition
conditional infinite accepted path under explicit SuccessorAvailability
finite-prefix endpoint and monitor preservation
Summable-to-uniform-budget bridge
explicit PaperSemantics equivalences
explicit NoOpFeasible premise
finite and conditional infinite paper-facing wrappers
```

Checker soundness is not successor availability or generator completeness.

## Gate B finite classical reference

### Information quantities

```text
Distribution n:
  nonnegative masses with total mass one

H(p):
  - Σ_i p_i log p_i

D_KL(p||q):
  Σ_i p_i log(p_i/q_i)
```

KL nonnegativity is proved under explicit support coverage. The uniform and
biased binary distributions give a strictly positive, nonconstant KL witness.

### Conservative extension

```text
(p_0, ..., p_{n-1})
  ↦
(0, p_0, ..., p_{n-1})
```

Support, Shannon entropy, and KL are preserved exactly, and dropping the new
coordinate recovers the predecessor exactly.

### Concrete checker and progress

The finite checker accepts only:

```text
initial -- improve / improvement certificate --> target
target  -- stay    / stability certificate   --> target
```

Acceptance refines to complete `StepObligations`; an invalid claimed successor is
rejected. Progress is reduction in actual KL distance to the target, so the
first accepted step is strictly improving for an information-theoretic reason.

### Worked trajectory

```text
initial → target → target
```

The trajectory is checker accepted, update linked, strictly improves at its first
step, and instantiates endpoint recovery and all finite monitor bounds.

## Substantive RCLM refinement

The RCLM reference state contains typed language, world/human reference,
definitiveness, ambiguity, memory, verifier, resource, and self-model registers.
Updates and certificate packets likewise contain substantive typed fields.

`RCLM.KernelRefinement` preserves every theorem-relevant kernel quantity.
`RCLM.MonitorRefinement` preserves the named monitor quantities and transports.
`RCLM.CheckerRefinement` preserves actual Boolean checker acceptance.

The concrete RCLM checker additionally verifies that all architecture fields are
the declared canonical encodings of the core state, update, successor, and
certificate. Architecture fields are checked rather than ignored.

## Conditional architecture engine

`RCLM.ArchitectureEngine` separates:

```text
witness-library coverage
generator proposal
certificate construction
candidate selection
successor realization
trust-anchor validity
resource authorization
successor-domain closure
```

`RCLM.ArchitectureEngineStep` carries an actual witness, proposal, certificate,
candidate, resource record, all engine-stage evidence, and RCLM checker
acceptance.

The theorem

```lean
RCLM.rclm_architecture_successor_theorem
```

returns typed RCLM successor evidence, complete RCLM obligations, forgotten core
checker acceptance, complete RCP obligations, recovery and monitor refinement
evidence, successor-domain closure, and trust/resource preservation.

It is conditional on actual engine-stage evidence. Checker soundness does not
produce a proposal, certificate, candidate, or realizer witness.

## Architecture successor availability

`RCLM.ArchitectureSuccessorAvailability` states that every valid architecture
predecessor has a nonempty generated, certified, selected, realized,
resource-authorized, checker-accepted engine step.

Under that explicit premise:

```lean
RCLM.conditional_infinite_architecture_trajectory_exists
RCLM.infinite_architecture_step_result
```

construct and certify an infinite architecture trajectory. It can be forgotten
to both RCLM-checker and core-checker accepted trajectories.

## Concrete Gate B direct-engine reference

The concrete engine has improve/stabilize/rejected proposals,
strict-improvement/stable-continuation/rejected witnesses, canonical certificate
and candidate relations, one root trust anchor, and explicit used/limit
resources.

```lean
RCLM.ClassicalBinary.improvement_direct_engine_successor
```

proves the full architecture-successor result for the accepted KL-derived
improvement packet.

```lean
RCLM.ClassicalBinary.architectureSuccessorAvailability
```

proves availability only on the declared binary domain. The selected infinite
reference path performs one strict improvement and then accepted stability
continuations. It proves formal recursive closure, not indefinitely strict
capability growth.

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
    ArchitectureEngine.lean
    ClassicalBinary.lean
    ClassicalBinaryEngine.lean
  RCP.lean
  RCLM.lean
  MainTheorem.lean
```

## Authoritative build and audit

The workflow performs:

```text
paper-source and theorem-surface pin verification
pinned dependency resolution
clean Lean build
no-sorry/no-admit source scan
project-local axiom scan
Gate A theorem-axiom audit
Gate B theorem-axiom audit
RCLM refinement and architecture-engine theorem-axiom audit
combined artifact upload
```

The clean GitHub workflow is authoritative. Interrupted or corrupted local
mathlib caches are not evidence that a synchronized source head fails.

## Claim discipline

The current project is not:

```text
exact Paper I main-theorem equivalence
exact Paper II direct-engine equivalence
finite-dimensional quantum-relative-entropy closure
an arbitrary learned-system generator
proof of strict improvement at every recursive step
a Python implementation
an empirical or benchmark result
```

No Python checker, generator, successor loop, or benchmark adapter is licensed
until the remaining theorem-to-runtime conditions in
`docs/formal_core_v2/EXIT_CRITERIA.md` are satisfied.
