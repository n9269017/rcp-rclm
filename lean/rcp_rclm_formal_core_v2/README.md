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
| Gate B finite classical/diagonal instance | Complete and audited | Actual finite Shannon/KL quantities, conservative extension, exact recovery, concrete checker and trajectory |
| Substantive RCLM-to-RCP refinement | Complete at the Gate B reference scope | State/update/certificate fields, checker acceptance, recovery laws, monitors |
| Conditional architecture successor theorem | Implemented and audited | Explicit generator, certifier, selector, realizer, trust, resource, and domain premises |
| Paper II direct-engine and robust-reflective interfaces | Implemented with explicit semantic premises | Verifier-schema, uncertainty-envelope, goal-transport, trust, budget, and persistence boundaries |
| Bounded seed-library and packet-builder refinement | Complete and audited at the binary reference scope | Finite grammars, packet construction, checker evidence, seed-domain closure |
| Gate C selected finite-dimensional quantum instance | Complete and audited at the commuting/diagonal matrix scope | Complex diagonal density matrices, spectral entropy/QRE, identity/swap channels, exact recovery, checker, trajectory, RCLM refinement |
| General noncommuting quantum extension | Open | Arbitrary density operators, CPTP maps, matrix-log QRE, data processing, Petz/approximate recovery |
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

The paper sources are pinned by Git blob in the manifest and checked by the
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
lake env lean ../../docs/formal_core_v2/audit/GateCAxiomAudit.lean
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
    QuantumDensity.lean
    QuantumKernel.lean
    QuantumChannels.lean
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
    QuantumBinary.lean

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

The package proves exact support, Shannon-entropy, and KL preservation. Dropping
the new coordinate recovers the predecessor exactly. This theorem is limited to
the declared zero-extension and is not a general stochastic-channel result.

## Concrete checker and trajectory

The binary checker accepts exactly:

```text
initial -- improve / improvement certificate --> target
target  -- stay    / stability certificate   --> target
```

Acceptance refines to the complete abstract `StepObligations`; a deliberately
invalid successor is rejected. Progress is reduction of actual KL distance to the
target, so the first transition is non-vacuously strict.

The worked finite path is:

```text
initial -> target -> target
```

# Substantive RCLM-to-RCP refinement

The concrete RCLM reference state carries typed registers for language, world and
human reference, definitiveness, ambiguity, memory, verifier, resources, and self
model. Updates and certificates carry corresponding theorem-relevant evidence.

The generic refinement structures preserve:

```text
state/update/certificate/protected/residual maps
typed update semantics
admissibility and invariant preservation
protected values, transports, and budgets
state distance, recovery, and recovery budgets
progress and strict witnesses
computed residuals
trust, resources, and reality containment
complete StepObligations
recovery-composition laws
Lyapunov, ambiguity, and relevance monitors
actual Boolean checker acceptance
```

The concrete RCLM checker verifies that the extra architecture fields equal the
declared canonical encodings. The fields are checked rather than ignored.

# Conditional architecture engine

`RCLM.ArchitectureEngine` separates:

```text
architecture theorem domain
witness-library coverage
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

```lean
RCLM.rclm_architecture_successor_theorem
```

returns typed RCLM successor evidence, complete RCLM and forgotten RCP obligations,
transported recovery and monitor evidence, domain closure, and trust/resource
validity.

The infinite architecture theorem keeps
`RCLM.ArchitectureSuccessorAvailability` explicit. It does not turn checker
soundness into generator completeness.

# Paper II bounded seed-library and packet builder

`RCLM.PaperIIBoundedSeedLibrary` contains finite `Finset` witness and grammar
objects, explicit depth/proof bounds, proposal/certificate/candidate/resource
decoders, grammar nonemptiness, coverage, realization, checker acceptance, and
successor seed-domain closure.

A selected grammar word forms `RCLM.PaperIIBoundedSeedPacket` and converts to an
architecture step. Packet-builder soundness returns complete successor-verification
obligations; the architecture refinement additionally returns complete forgotten
RCP obligations plus recovery and monitor evidence.

The concrete binary grammar is:

```text
active grammar at initial: {improve}
active grammar at target:  {stabilize}
maximum update-word depth: 1
maximum proof-word length: 1
rejected word: absent from every active grammar
```

The path improves strictly once and then uses accepted stability continuation. It
does not prove indefinitely strict capability growth.

# Gate C — selected finite-dimensional quantum instance

## Density representation

The selected matrix type is:

```text
QuantumMatrix n = Matrix (Fin n) (Fin n) ℂ
```

`RCP.QuantumFinite.DiagonalDensityMatrix n` carries a normalized nonnegative
spectrum and exposes its complex diagonal matrix. For every selected density the
formalization proves:

```text
matrix.IsHermitian
matrix.PosSemidef
Matrix.trace matrix = 1
```

`PositiveDiagonalDensityMatrix n` carries strict positivity of every spectral
mass and therefore supplies the support hypothesis required by the selected QRE
nonnegativity theorem.

## Entropy and quantum relative entropy

At the commuting/diagonal scope:

```text
S(ρ)      = - Σ_i p_i log p_i
D(ρ || σ) =   Σ_i p_i log (p_i/q_i)
```

The source and target spectra are `(1/4, 3/4)` and `(3/4, 1/4)`. Their QRE is proved
equal to `(1/2) * log 3`, hence strictly positive. The concrete protected/progress
quantity is therefore nonconstant.

This is a spectral commuting reference, not a general matrix-logarithm theorem.

## Selected matrix channels and recovery

`FiniteDiagonalChannel n` packages:

```text
action on diagonal density matrices
complex-linear matrix map
state/matrix action agreement
trace preservation
Hermitian preservation
positive-semidefinite preservation
```

The concrete channel family is:

```text
stay -> identityChannel
swap -> swapChannel
```

The selected recovery channel is indexed by the actual update. Identity recovers
identity; swap recovers by applying the involutive basis swap again. The package
proves exact recovery and entropy/QRE preservation for this selected family.

## Quantum kernel and checker

The quantum kernel has substantive state, update, certificate, residual, trust,
resource, and reality-containment objects. It accepts exactly:

```text
source + swap + target + improvement certificate
target + stay + target + stability certificate
```

Residuals test the actual typed transition and actual packet acceptance. The
reality gate excludes an explicit outside-state packet and is not definitionally
true.

The checker theorem retains the required form:

```text
check = true -> complete StepObligations
```

and a declared invalid candidate is rejected.

## Quantum monitors and finite trajectory

The progress functional is derived from the positive source-to-target QRE gap.
The worked path is:

```text
source -> target -> target
```

The first step is strict; the second is stable. The package proves endpoint
recovery, Lyapunov/motion composition, and relevance transport.

## Quantum RCLM refinement

`RCLM/QuantumBinary.lean` supplies substantive architecture states, updates,
certificates, a concrete checker, recovery laws, and monitors, and identifies:

```text
architecture state -> selected density
architecture update -> selected forward channel
architecture update -> selected recovery channel
architecture state -> selected entropy
architecture state pair -> selected QRE
```

```lean
RCLM.QuantumBinary.accepted_quantum_architecture_successor
```

returns complete RCLM obligations, complete forgotten RCP obligations, density
evidence, forward-channel realization, exact selected recovery, entropy
preservation, and QRE preservation.

## Gate C limitation

The selected closure does not claim:

```text
arbitrary noncommuting density matrices
arbitrary CPTP channels
general matrix-logarithm QRE
general quantum data processing
trace-distance, Petz, or approximate recovery
strict useful improvement at every recursive step
exact full Paper I or Paper II quantum identity
```

See:

```text
../../docs/formal_core_v2/GATE_C_SCOPE.md
../../docs/formal_core_v2/GATE_C_CLOSURE.md
```

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
source scan for sorry/sorryAx/admit
project-local axiom declaration scan
Gate A theorem-axiom audit
Gate B theorem-axiom audit
RCLM/refinement/engine/bounded-seed theorem-axiom audit
Gate C theorem-axiom audit
audit artifact upload even on failure
```

## Audit scripts

```text
docs/formal_core_v2/audit/verify_paper_alignment_pins.sh
docs/formal_core_v2/audit/GateAAxiomAudit.lean
docs/formal_core_v2/audit/GateBAxiomAudit.lean
docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
docs/formal_core_v2/audit/GateCAxiomAudit.lean
```

## Artifact name

```text
formal-core-v2-audit-<workflow-run-id>-<attempt>
```

The artifact contains the full build log, metadata, source-admission scans, local
axiom scan, and all four theorem-axiom reports. See
[`../../docs/formal_core_v2/AUDIT_ARTIFACTS.md`](../../docs/formal_core_v2/AUDIT_ARTIFACTS.md).

The audited foundational union at the completed selected Gate C scope is:

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

The project currently proves a pinned conditional theorem stack, a nontrivial
finite classical reference, and a selected finite-dimensional diagonal quantum
reference. It does not prove:

```text
exact full Paper I semantic equivalence
exact full Paper II semantic equivalence
arbitrary learned-system theorem entry
arbitrary learned generator coverage
unbounded grammar or proof-search completeness
strict useful improvement at every recursive step
general noncommuting quantum closure
arbitrary CPTP data processing
Petz or approximate recovery
Python checker or generator correctness
an executable recursive promotion loop
empirical recursive self-improvement
external benchmark performance
```

No executable phase begins until the relevant conditions in
[`../../docs/formal_core_v2/EXIT_CRITERIA.md`](../../docs/formal_core_v2/EXIT_CRITERIA.md)
are explicitly satisfied.
