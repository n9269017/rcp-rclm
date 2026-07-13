# RCP/RCLM Formal Core v2 — Mechanized Conditional Successor Theorem Closure

This is a separate pinned Lean project. It does not overwrite or silently
strengthen the historical canonical v1 project under
`lean/rcp_rclm_can_lean4/`.

## Current status

```text
Gate A abstract theorem kernel: complete and clean-CI audited
Gate B finite classical/diagonal reference: complete at declared scope
Substantive Gate B RCLM-to-RCP refinement: complete at declared scope
Conditional RCLM architecture successor/direct-engine theorem: implemented
Paper II robust-reflective alignment interfaces: implemented
Bounded seed-library and packet-builder refinement: complete at binary scope
Conditional infinite bounded seed-library trajectory: implemented
Gate C finite-dimensional quantum instantiation: not claimed
Exact Paper I theorem mechanization: not claimed
Exact Paper II theorem mechanization: not claimed
Python checker/generator/closed loop: not licensed
External benchmark result: none
```

The exact boundaries are recorded in:

```text
docs/formal_core_v2/GATE_B_CLOSURE.md
docs/formal_core_v2/RCLM_GATE_B_REFINEMENT_STATUS.md
docs/formal_core_v2/RCLM_DIRECT_ENGINE_STATUS.md
docs/formal_core_v2/PAPER_II_BOUNDED_SEED_LIBRARY_REFINEMENT.md
```

## Exact dependency pins

```text
Lean:    leanprover/lean4:v4.31.0
mathlib: fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
```

`lake-manifest.json` pins the complete dependency graph.

## Abstract RCP contract

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

Gate A proves finite composition, endpoint recovery under explicit laws,
quantitative monitor composition, conditional infinite accepted paths under
explicit successor availability, and a summability-to-uniform-prefix bridge.
Checker soundness is not successor availability or generator completeness.

## Gate B finite classical reference

For normalized finite distributions:

```text
H(p)         = - Σ_i p_i log p_i
D_KL(p || q) =   Σ_i p_i log(p_i/q_i)
```

KL nonnegativity is proved under explicit support coverage. The uniform and
biased binary distributions provide a strictly positive, nonconstant KL witness.
The zero-head conservative extension preserves support, Shannon entropy, and KL
exactly, and dropping the added coordinate recovers the predecessor exactly.

The concrete checker accepts only:

```text
initial -- improve / improvement certificate --> target
target  -- stay    / stability certificate   --> target
```

Acceptance refines to complete obligations; an invalid successor is rejected.
Progress is actual reduction in KL distance to the target. The worked trajectory
is `initial -> target -> target` and is strict at its first transition.

## Substantive RCLM refinement

The finite RCLM reference state contains typed language, world/human reference,
definitiveness, ambiguity, memory, verifier, resource, and self-model registers.
Updates and certificates likewise carry substantive typed fields.

```text
KernelRefinement:
  preserves every theorem-relevant kernel quantity

MonitorRefinement:
  preserves Lyapunov, motion, ambiguity, and relevance quantities/transports

CheckerRefinement:
  preserves actual Boolean checker acceptance
```

The concrete RCLM checker additionally verifies that all architecture fields are
the declared canonical encodings of the core state, update, successor, and
certificate.

## Conditional architecture engine

`RCLM.ArchitectureEngine` separates:

```text
witness-library coverage
generator proposal
certificate construction
candidate selection
successor realization
trust-anchor validity and preservation
resource authorization and soundness
successor-domain closure
```

`RCLM.ArchitectureEngineStep` contains actual engine-stage data and proofs plus
RCLM checker acceptance. The theorem

```lean
RCLM.rclm_architecture_successor_theorem
```

returns typed RCLM obligations, forgotten RCP obligations, recovery/monitor
refinement evidence, successor-domain closure, and trust/resource preservation.

`ArchitectureSuccessorAvailability` is an explicit premise of the conditional
infinite architecture theorem. It is never derived from checker soundness.

## Paper II direct-engine and robust-reflective alignment

The aligned direct-engine layer distinguishes accepted continuation from strict
successor availability and separately represents non-loss, ability preservation,
strict ability expansion, viability, and projection realization.

The robust-reflective layer represents verifier-schema transport, uncertainty
envelopes, goal transport and drift, anti-circular trust, proof/checking budgets,
successor persistence, optional reality/tractability certificates, summable
failure risk, and a separately supplied Borel-Cantelli consequence.

These interfaces are proposition-valued theorem inputs. They are not inferred
from names or from checker acceptance.

## Bounded seed-library and packet builder

The generic finite interface is:

```lean
RCLM.PaperIIBoundedSeedLibrary
```

It carries:

```text
seed domain
finite witness library
finite packet grammar
word-depth and proof-length bounds
witness/proposal/certificate/candidate/resource decoders
grammar nonemptiness on the seed domain
witness coverage
proposal-generation evidence
certificate-construction evidence
candidate-selection evidence
successor-realization evidence
resource authorization
checker acceptance
successor seed-domain closure
```

A concrete grammar word and its membership proof form:

```lean
RCLM.PaperIIBoundedSeedPacket
```

and are converted to the compiled engine step by:

```lean
RCLM.PaperIIBoundedSeedPacket.toEngineStep
```

The packet-builder theorem

```lean
RCLM.paper_ii_bounded_seed_packet_builder_sound
```

returns complete RCLM obligations, complete Paper II successor-verification
obligations, successor seed-domain membership, verifier-schema persistence,
uncertainty-envelope persistence, and the declared goal-drift bound.

The architecture bridge

```lean
RCLM.paper_ii_bounded_seed_packet_refines_architecture
```

also returns complete forgotten RCP obligations and recovery/monitor refinement
evidence.

## Semantic identification

`RCLM.PaperIISeedSemanticIdentification` requires equality proofs identifying:

```text
declared verifier schema, transport, and refinement relation
declared uncertainty envelope, transport, and refinement relation
declared goal, goal transport, goal distance, and drift budget
```

Field names alone are never treated as semantic equality.

## Bounded seed-library recursion

The recursive bounded-seed construction selects only grammar-certified packets,
constructs the next architecture predecessor, and preserves explicit seed-domain
membership. Its public theorems include:

```lean
RCLM.conditional_infinite_paper_ii_bounded_seed_trajectory_exists
RCLM.infinite_paper_ii_bounded_seed_step_result
RCLM.infinite_paper_ii_bounded_seed_step_refines_architecture
```

The theorem depends on declared grammar nonemptiness and successor seed-domain
closure. It does not infer either property from checker soundness.

## Concrete bounded binary reference

```text
active grammar at initial: {improve}
active grammar at target:  {stabilize}
maximum update-word depth: 1
maximum proof-word length: 1
rejected word: absent from every active grammar
```

The declared verifier schema is `trustedBinaryChecker`, the uncertainty envelope
is `contained`, and the goal is `biasedTarget`; all three transports are the
declared identity transports at this finite reference scope.

The concrete bounded trajectory performs one strict KL-derived improvement and
then accepted stability continuations. It proves finite-class seed-library
closure, not indefinitely strict capability growth.

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
    PaperIIDirectEngine.lean
    PaperIIRobustReflective.lean
    PaperIIAlignmentPremises.lean
    PaperIIBoundedSeedLibrary.lean
    PaperIIBoundedSeedTrajectory.lean
    ClassicalBinary.lean
    ClassicalBinaryEngine.lean
    ClassicalBinaryPaperII.lean
    ClassicalBinarySeedLibrary.lean
    ClassicalBinarySeedTrajectory.lean
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
Gate A theorem-axiom audit
Gate B theorem-axiom audit
RCLM/refinement/engine/bounded-seed theorem-axiom audit
combined artifact upload
```

The clean GitHub workflow is authoritative. Interrupted local dependency caches
are not evidence that a synchronized source head fails.

## Claim discipline

The current project does not establish:

```text
exact Paper I main-theorem equivalence
exact full Paper II semantic equivalence
unbounded grammar or proof-search completeness
arbitrary learned-system seed-domain entry
arbitrary learned generator coverage
strict useful improvement at every recursive step
finite-dimensional quantum relative entropy
Python checker or generator correctness
an executable promotion loop
empirical recursive self-improvement
external benchmark performance
```

No Python checker, generator, successor loop, or benchmark adapter is licensed
until the remaining theorem-to-runtime and semantic conditions in
`docs/formal_core_v2/EXIT_CRITERIA.md` are satisfied.
