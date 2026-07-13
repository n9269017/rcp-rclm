# RCP/RCLM Formal Core v2

## Mechanized Conditional Successor Theorem Closure

This directory is the active, pinned Lean 4 formalization package for the
RCP/RCLM conditional successor-verification program.

It is separate from the historical v1 project at
`lean/rcp_rclm_can_lean4/`. The v1 sources remain historical canonical
references; this project does not overwrite them or silently strengthen their
claims.

## Status summary

| Component | Status | Scope |
|---|---|---|
| Gate A abstract theorem kernel | Complete and audited | Abstract successor obligations, finite composition, endpoint recovery, monitors, conditional infinite closure |
| Gate B finite classical/diagonal instance | Complete and audited | Actual finite Shannon/KL quantities and a concrete binary reference |
| Substantive RCLM-to-RCP refinement | Complete at the Gate B reference scope | State/update/certificate fields, checker acceptance, recovery laws, monitors |
| Conditional architecture successor theorem | Implemented and audited | Explicit generator, certifier, selector, realizer, trust, resource, and domain premises |
| Paper II direct-engine and robust-reflective interfaces | Implemented with explicit semantic premises | Verifier-schema, uncertainty-envelope, goal-transport, trust, budget, and persistence boundaries |
| Bounded seed-library and packet-builder refinement | Complete and audited at the binary reference scope | Finite grammars, packet construction, checker evidence, seed-domain closure |
| Gate C finite-dimensional quantum instance | **Planning placeholder only** | No density-matrix, channel, von Neumann entropy, or quantum-relative-entropy theorem is yet claimed |
| Executable runtime refinement | Not licensed | No v2 Python checker, generator, promotion loop, or benchmark result |

The documentation index is
[`../../docs/formal_core_v2/README.md`](../../docs/formal_core_v2/README.md).

## Exact pins

```text
Lean:    leanprover/lean4:v4.31.0
mathlib: fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
```

Pinning is distributed across:

```text
lean-toolchain       exact Lean toolchain
lakefile.toml        exact mathlib revision
lake-manifest.json   complete resolved dependency graph
formalization_manifest.json
                     theorem/package status and validation metadata
```

The paper sources are also pinned by Git blob in the manifest and checked by the
paper-alignment audit script.

## Quick start

From the repository root:

```bash
cd lean/rcp_rclm_formal_core_v2
lake update
lake exe cache get
lake build
```

Run the public theorem-axiom audits:

```bash
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateBAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
```

Run the paper/source pin check from the repository root:

```bash
bash docs/formal_core_v2/audit/verify_paper_alignment_pins.sh
```

The clean GitHub workflow is authoritative. Detailed reproduction and Windows
cache-recovery instructions are in
[`../../docs/formal_core_v2/REPRODUCIBILITY.md`](../../docs/formal_core_v2/REPRODUCIBILITY.md).

## Package layout

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

RcpRclmFormalCoreV2.lean
formalization_manifest.json
lakefile.toml
lake-manifest.json
lean-toolchain
```

`RCP.lean` and `RCLM.lean` are public facade modules. The implementation remains
split into theorem-focused internal modules so that assumptions and proof failures
stay localized.

# Gate A — abstract theorem kernel

## One-step contract

For an admissible, invariant-preserving predecessor, trusted-checker acceptance
implies:

```text
typed successor validity
computed residual nonpositivity
quantitative protected-distinction non-loss
constructive recovery tied to the actual candidate update
protected-invariant preservation
progress nondecrease
strict progress when a strict witness is certified
trust/verifier validity
resource validity
reality/uncertainty containment
successor-domain admissibility
```

The abstract `Kernel` prevents three vacuous degeneracies:

```text
protected values may not be globally constant
residual evaluation must exhibit fixed-index input sensitivity
reality containment may not be universally true
```

## Finite composition

The finite accepted-trajectory layer proves:

```lean
RCP.finite_trajectory_closure
RCP.finite_progress_monotone
RCP.finite_composed_nonloss_bound
RCP.finite_composed_recovery_bound
RCP.finite_endpoint_recovery_bound
RCP.finite_lyapunov_motion_bound
RCP.finite_ambiguity_collapse_bound
RCP.finite_self_model_relevance_bound
```

Aggregate local recovery accounting and endpoint rollback are separate results.
The endpoint theorem requires explicit self-zero, triangle, and recovery-map
nonexpansiveness laws.

## Conditional infinite closure

```lean
RCP.SuccessorAvailability
RCP.conditional_infinite_trajectory_exists
```

`SuccessorAvailability` is an explicit premise. Checker soundness cannot prove
that a useful accepted successor exists.

Finite prefixes of an infinite accepted path inherit the finite recovery and
monitor theorems. Standard summability assumptions are bridged to uniform prefix
bounds by the summability layer.

## Paper-facing abstract boundary

`RCP.PaperSemantics` carries explicit equivalences between paper-facing safe-state
and update-admissibility predicates and the kernel objects. These equivalences are
refinement obligations, not consequences of terminology.

`RCP.AcceptedNoOp` and `RCP.NoOpFeasible` represent no-op feasibility separately
from general successor availability.

# Gate B — finite classical/diagonal instance

## Actual finite information quantities

For normalized finite distributions:

```text
H(p)         = - Σ_i p_i log p_i
D_KL(p || q) =   Σ_i p_i log(p_i/q_i)
```

KL nonnegativity is proved under explicit support coverage, and self-divergence is
zero. The uniform and biased binary distributions give a strictly positive KL
witness, so the concrete protected quantity is not constant.

## Conservative extension and exact recovery

The concrete embedding adds one zero-mass head coordinate:

```text
(p₀, …, pₙ₋₁) ↦ (0, p₀, …, pₙ₋₁)
```

The package proves exact preservation of:

```text
support coverage
Shannon entropy
KL divergence
```

Dropping the new coordinate recovers the predecessor exactly. This is a theorem
for the declared finite zero-extension, not for every stochastic channel.

## Concrete state, certificate, checker, and strict progress

The binary checker accepts exactly:

```text
initial -- improve / improvement certificate --> target
target  -- stay    / stability certificate   --> target
```

Acceptance refines to the complete abstract `StepObligations`; a deliberately
invalid successor is rejected. Progress is reduction of actual KL distance to the
target, so the improvement transition is non-vacuously strict.

The worked finite path is:

```text
initial → target → target
```

It instantiates progress, protected-value, recovery, Lyapunov/motion,
ambiguity-indicator, and relevance-label composition at the declared finite
scope.

# Substantive RCLM-to-RCP refinement

The concrete RCLM reference state carries typed registers for:

```text
language
world reference
human reference
definitiveness
ambiguity
memory
verifier
resources
self model
```

Updates and certificates carry corresponding theorem-relevant evidence.

The generic refinement structures are:

```text
KernelRefinement
  state/update/certificate/protected/residual maps
  typed update semantics
  admissibility and invariant preservation
  protected values, transports, and budgets
  state distance, recovery, and recovery budgets
  progress and strict witnesses
  residuals
  trust, resources, and reality containment
  complete StepObligations
  recovery-composition laws

MonitorRefinement
  Lyapunov value and motion charge
  ambiguity quantity and transport
  relevance quantity and transport

CheckerRefinement
  actual Boolean acceptance preservation
```

The concrete RCLM checker also verifies that all extra architecture fields equal
the declared canonical encodings. The fields are checked rather than ignored.

# Conditional architecture engine

`RCLM.ArchitectureEngine` separates the following relations and premises:

```text
architecture theorem domain
finite or abstract witness-library coverage
generator proposal relation
certificate construction relation
candidate selection relation
successor realization relation
trust-anchor validity and preservation
resource authorization and soundness
successor-domain closure
```

`RCLM.ArchitectureEngineStep` packages actual witness, proposal, certificate,
candidate, resource, realization, and checker-acceptance evidence.

The theorem:

```lean
RCLM.rclm_architecture_successor_theorem
```

returns:

```text
typed RCLM successor evidence
complete RCLM StepObligations
forgotten core checker acceptance
complete forgotten RCP StepObligations
transported recovery-composition laws
transported monitor-refinement evidence
successor architecture-domain membership
successor admissibility and invariant preservation
engine trust/resource validity
trust-anchor preservation
```

The infinite architecture theorem keeps
`RCLM.ArchitectureSuccessorAvailability` explicit. It does not turn checker
soundness into generator completeness.

# Paper II alignment interfaces

## Direct-engine semantics

The direct-engine layer separately represents:

```text
non-lossy candidate status
algebraic gate
full gate
predecessor-ability preservation
strict ability expansion
viability-kernel membership
projection realization
```

Accepted continuation is not identified with strict improvement.

## Robust-reflective successor semantics

The robust-reflective layer separately represents:

```text
verifier schema and cross-time transport
uncertainty envelope and transport
goal and goal transport
goal distance and drift budget
anti-circular trust
proof/checking budget validity
successor persistence
reality and tractability certificates
soundness-failure risk
summability and separately supplied almost-sure consequences
```

These objects are proposition-valued theorem data. Similar names do not establish
semantic identity.

# Bounded seed-library and packet builder

## Generic interface

```lean
RCLM.PaperIIBoundedSeedLibrary
```

contains actual finite `Finset` objects and explicit laws for:

```text
seed domain
finite witness library
finite packet-word grammar
word-depth and proof-length bounds
witness/proposal/certificate/candidate/resource decoders
grammar nonemptiness on the seed domain
word-to-witness membership
witness coverage
proposal generation
certificate construction
candidate selection
successor realization
resource authorization
checker acceptance
successor seed-domain closure
```

A selected grammar word plus its proofs forms:

```lean
RCLM.PaperIIBoundedSeedPacket
```

and converts to the compiled architecture step through:

```lean
RCLM.PaperIIBoundedSeedPacket.toEngineStep
```

## Packet-builder and architecture refinement

```lean
RCLM.paper_ii_bounded_seed_packet_builder_sound
```

returns complete RCLM obligations, Paper II successor-verification obligations,
seed-domain closure, verifier-schema persistence, uncertainty-envelope
persistence, and the declared goal-drift bound.

```lean
RCLM.paper_ii_bounded_seed_packet_refines_architecture
```

adds the complete forgotten RCP obligations plus recovery and monitor refinement.

`RCLM.PaperIISeedSemanticIdentification` requires pointwise equality proofs for
the declared verifier schema, uncertainty envelope, goal, transports, refinement
relations, distance, and budget.

## Recursive bounded trajectory

```lean
RCLM.conditional_infinite_paper_ii_bounded_seed_trajectory_exists
RCLM.infinite_paper_ii_bounded_seed_step_result
RCLM.infinite_paper_ii_bounded_seed_step_refines_architecture
```

The construction selects from an explicitly nonempty finite grammar and preserves
an independently supplied successor seed-domain law. Classical choice selects an
available packet; checker soundness does not supply the packet.

## Concrete binary grammar

```text
active grammar at initial: {improve}
active grammar at target:  {stabilize}
maximum update-word depth: 1
maximum proof-word length: 1
rejected word: absent from every active grammar
```

The declared verifier schema is `trustedBinaryChecker`, the uncertainty envelope
is `contained`, and the goal is `biasedTarget`; the finite reference uses identity
transports and zero goal drift.

The path improves strictly once and then uses accepted stability continuation. It
does not prove indefinitely strict capability growth.

# Gate C planning placeholder

Gate C has **not** begun in this branch. `RCP/QuantumFinite.lean` is intentionally
empty apart from a scope declaration.

The planned Gate C contract must be frozen before implementation and must include:

```text
finite-dimensional complex matrix representation
density matrices with Hermitian, positive-semidefinite, and trace-one evidence
support/domain conditions for matrix logarithms
admissible completely positive trace-preserving transitions
von Neumann entropy or an explicitly chosen equivalent finite definition
quantum relative entropy with explicit support convention
non-loss theorem for declared protected distinctions
constructive recovery tied to the actual transition
nonconstant concrete quantum witness
non-vacuous strict progress witness
concrete checker refinement
finite trajectory composition
conditional infinite closure with explicit successor availability
strengthened RCLM-to-RCP refinement over the quantum objects
exact import and axiom audit
```

See
[`../../docs/formal_core_v2/GATE_C_SCOPE.md`](../../docs/formal_core_v2/GATE_C_SCOPE.md).
No density-matrix, channel, or quantum-relative-entropy result should be inferred
from the current placeholder.

# Build, audit, and artifacts

## Authoritative workflow

```text
.github/workflows/formal-core-v2.yml
```

The workflow performs:

```text
paper-source blob and theorem-surface pin verification
pinned Lean installation
pinned dependency resolution
official mathlib cache retrieval
clean project build
source scan for sorry/admit
project-local axiom declaration scan
Gate A theorem-axiom audit
Gate B theorem-axiom audit
RCLM/refinement/engine/bounded-seed theorem-axiom audit
audit artifact upload even on failure
```

## Audit scripts

```text
docs/formal_core_v2/audit/verify_paper_alignment_pins.sh
docs/formal_core_v2/audit/GateAAxiomAudit.lean
docs/formal_core_v2/audit/GateBAxiomAudit.lean
docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
```

## Artifact name

```text
formal-core-v2-audit-<workflow-run-id>-<attempt>
```

The artifact contains the full build log, metadata, source-admission scans, local
axiom scan, and the three theorem-axiom reports. See
[`../../docs/formal_core_v2/AUDIT_ARTIFACTS.md`](../../docs/formal_core_v2/AUDIT_ARTIFACTS.md).

The audited foundational union at the completed Gate B/bounded-seed scope is:

```lean
[propext, Classical.choice, Quot.sound]
```

No audited declaration reports `sorryAx`, and no project-local axiom declaration
occurs in the audited source. Some concrete declarations are axiom-free.

# Change discipline

A formal change is not considered complete until all applicable steps pass:

```text
1. Freeze or update the ordinary-mathematics contract.
2. Represent every new premise explicitly.
3. Add or strengthen Lean declarations without admitted proofs.
4. Update the paper theorem map and assumption register.
5. Extend the appropriate axiom-audit file.
6. Update the formalization manifest and closure/status record.
7. Pass the clean pinned GitHub workflow.
8. Record the exact claim boundary and remaining mismatches.
```

Documentation-only changes must not silently upgrade theorem status.

# Exact claim boundary

The project currently proves a pinned conditional theorem stack and a nontrivial
finite classical reference. It does not prove:

```text
exact full Paper I semantic equivalence
exact full Paper II semantic equivalence
arbitrary learned-system theorem entry
arbitrary learned generator coverage
unbounded grammar or proof-search completeness
strict useful improvement at every recursive step
finite-dimensional quantum relative entropy or channel recovery
Python checker or generator correctness
an executable recursive promotion loop
empirical recursive self-improvement
external benchmark performance
```

No executable phase begins until the relevant conditions in
[`../../docs/formal_core_v2/EXIT_CRITERIA.md`](../../docs/formal_core_v2/EXIT_CRITERIA.md)
are explicitly satisfied.