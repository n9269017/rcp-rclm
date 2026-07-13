# RCP/RCLM — Robust Reflective Successor Verification

This repository contains the two companion RCP/RCLM manuscripts, the historical
Lean v1 certificate, and the active pinned **RCP/RCLM Formal Core v2** Lean 4
project.

The active v2 project proves a conditional successor-verification theorem stack.
It does not claim that checker soundness creates a successor, that every accepted
successor is strictly useful, or that the current Lean development is an
executable recursive-self-improvement system.

## Authoritative status

| Layer | Status | Exact scope |
|---|---|---|
| Gate A — abstract theorem kernel | Complete, clean-CI built, axiom audited | Abstract conditional successor, finite composition, endpoint recovery, monitors, and conditional infinite closure |
| Gate B — finite classical/diagonal instance | Complete at the declared finite reference scope | Actual finite Shannon/KL quantities, zero-coordinate conservative extension, exact recovery, non-vacuous strict progress, concrete checker |
| Gate B RCLM-to-RCP refinement | Complete at the declared binary reference scope | Theorem-relevant state/update/certificate fields, checker acceptance, recovery laws, monitors, and architecture obligations |
| Paper II direct-engine and robust-reflective interfaces | Implemented with explicit premises | Conditional architecture theorem, explicit generator/certifier/selector/realizer boundary, verifier/envelope/goal transports |
| Bounded seed-library packet builder | Complete at the declared binary reference scope | Finite witness/packet grammars, packet construction, checker evidence, seed-domain closure, conditional infinite bounded trajectory |
| Gate C — selected finite-dimensional quantum instance | Complete and audited at the declared commuting/diagonal matrix scope | Certified complex diagonal density matrices, spectral von Neumann entropy and QRE, identity/swap channels, exact recovery, concrete checker, finite trajectory, RCLM refinement |
| General noncommuting quantum extension | Open | No arbitrary noncommuting density matrices, general CPTP maps, matrix-log QRE, data-processing theorem, or Petz recovery claim |
| Executable checker/generator/closed loop | Not licensed by the current formal result | No v2 Python refinement or benchmark claim |

The detailed status and claim boundaries are indexed in
[`docs/formal_core_v2/README.md`](docs/formal_core_v2/README.md).

## Which Lean project is authoritative?

### Active Formal Core v2

```text
lean/rcp_rclm_formal_core_v2/
```

Use this project for all current theorem work. It pins:

```text
Lean:    leanprover/lean4:v4.31.0
mathlib: fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
```

The complete dependency graph is committed in
`lean/rcp_rclm_formal_core_v2/lake-manifest.json`.

### Historical v1 certificate

```text
lean/rcp_rclm_can_lean4/
```

The v1 files are retained as historical canonical references. Formal Core v2 does
not overwrite them and does not silently reinterpret their narrower scope.

## Repository map

```text
papers/
  paper-I-rcp-math/
  paper-II-rclm-architecture/

lean/
  rcp_rclm_formal_core_v2/       active pinned project
  rcp_rclm_can_lean4/            historical v1 project

docs/formal_core_v2/
  README.md                       documentation index
  THEOREM_CONTRACT.md             frozen theorem contract
  PAPER_THEOREM_MAP.md            paper-to-Lean mapping
  ASSUMPTION_REGISTER.md          explicit premises and ownership
  EXIT_CRITERIA.md                gate and runtime licensing conditions
  AXIOM_AUDIT.md                  proof-admission and axiom policy
  GATE_B_CLOSURE.md               finite classical closure record
  RCLM_GATE_B_REFINEMENT_STATUS.md
  RCLM_DIRECT_ENGINE_STATUS.md
  PAPER_II_BOUNDED_SEED_LIBRARY_REFINEMENT.md
  GATE_C_SCOPE.md                 implemented selected quantum scope
  GATE_C_CLOSURE.md               selected Gate C closure record
  REPRODUCIBILITY.md              local and CI reproduction
  AUDIT_ARTIFACTS.md              artifact contents and interpretation
  audit/
    verify_paper_alignment_pins.sh
    GateAAxiomAudit.lean
    GateBAxiomAudit.lean
    RCLMRefinementAxiomAudit.lean
    GateCAxiomAudit.lean

.github/workflows/
  formal-core-v2.yml              authoritative pinned build and audit workflow
```

## Formal Core v2 theorem shape

For an admissible, invariant-preserving predecessor and a trusted checker,
accepted candidate/certificate evidence yields the complete one-step obligation
bundle:

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

Gate A composes these obligations along finite accepted trajectories and proves a
conditional infinite trajectory theorem under an explicit successor-availability
premise. Checker soundness alone is never used to prove generator completeness.

## Gate B finite reference

Gate B supplies a concrete finite classical reference with actual Shannon entropy
and KL divergence, exact zero-coordinate conservative extension and recovery, a
strict KL-derived improvement witness, and a Boolean checker whose acceptance
refines to the abstract obligations.

The RCLM layer preserves the theorem-relevant Gate A/B objects through an explicit
refinement map and adds separate architecture relations for generation,
certificate construction, candidate selection, realization, trust, resources,
and successor-domain closure.

## Gate C selected quantum reference

Gate C introduces a finite two-level commuting/diagonal quantum reference using:

```text
QuantumMatrix n = Matrix (Fin n) (Fin n) ℂ
```

The selected state layer proves Hermitian, positive-semidefinite, and trace-one
properties for complex diagonal density matrices. Spectral von Neumann entropy and
quantum relative entropy are implemented through the certified finite spectrum,
with support conditions explicit.

The selected transition family consists of identity and basis-swap matrix
channels. The formalization proves state/matrix action agreement, trace,
Hermitian, and positive-semidefinite preservation, exact update-indexed recovery,
and entropy/QRE preservation.

The concrete quantum checker accepts exactly an improvement transition from the
source to the target and a stable target continuation. It rejects a declared
invalid candidate, computes transition- and packet-sensitive residuals, and
refines acceptance to complete successor obligations.

The worked path is:

```text
source -> target -> target
```

It proves one strict QRE-derived progress step, endpoint recovery, finite monitor
composition, and substantive RCLM-to-RCP quantum refinement.

This closure is deliberately limited to the selected commuting/diagonal reference.
It is not a theorem about arbitrary noncommuting density operators, arbitrary CPTP
maps, general matrix logarithms, general quantum data processing, or Petz recovery.
See [`docs/formal_core_v2/GATE_C_CLOSURE.md`](docs/formal_core_v2/GATE_C_CLOSURE.md).

## Build the active v2 project

From the repository root:

```bash
cd lean/rcp_rclm_formal_core_v2
lake update
lake exe cache get
lake build
```

Run the theorem-axiom audits with:

```bash
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateBAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateCAxiomAudit.lean
```

Run the paper-source and theorem-surface pin check from the repository root:

```bash
bash docs/formal_core_v2/audit/verify_paper_alignment_pins.sh
```

The GitHub Actions workflow is authoritative because it checks out a clean tree,
installs the pinned toolchain, resolves the pinned dependency graph, obtains the
official mathlib cache, builds the project, scans for admitted proofs and local
axioms, prints all four public theorem axiom surfaces, and uploads the complete
audit bundle.

Windows cache-corruption recovery and exact reproduction instructions are in
[`docs/formal_core_v2/REPRODUCIBILITY.md`](docs/formal_core_v2/REPRODUCIBILITY.md).

## Audit artifacts

Every workflow attempt uploads:

```text
formal-core-v2-audit-<run-id>-<attempt>
```

The archive contains the build log, source-admission scans, project-local axiom
scan, paper/source pin metadata, and the Gate A, Gate B, RCLM, and Gate C theorem-
axiom reports. The artifact layout and interpretation rules are documented in
[`docs/formal_core_v2/AUDIT_ARTIFACTS.md`](docs/formal_core_v2/AUDIT_ARTIFACTS.md).

A clean build is evidence that the declared Lean project elaborates. It is not,
by itself, evidence of exact paper equivalence, arbitrary generator completeness,
strict improvement at every step, executable-system correctness, or empirical
RSI.

## Historical scripts and controlled artifacts

The repository still contains historical v1 controlled artifacts, replay
checkers, and provenance records. They remain useful as historical finite
references, but they are **not** the runtime refinement of Formal Core v2. Formal
Core v2 currently licenses no Python checker, generator, promotion loop, or
external benchmark claim.

## Primary documentation

| Document | Purpose |
|---|---|
| [`THEOREM_CONTRACT.md`](docs/formal_core_v2/THEOREM_CONTRACT.md) | Ordinary-mathematics and Lean-facing theorem contract |
| [`PAPER_THEOREM_MAP.md`](docs/formal_core_v2/PAPER_THEOREM_MAP.md) | Pinned paper claims mapped to compiled declarations |
| [`ASSUMPTION_REGISTER.md`](docs/formal_core_v2/ASSUMPTION_REGISTER.md) | Every premise, its owner, and discharge status |
| [`EXIT_CRITERIA.md`](docs/formal_core_v2/EXIT_CRITERIA.md) | Gate closure and executable-phase licensing rules |
| [`AXIOM_AUDIT.md`](docs/formal_core_v2/AXIOM_AUDIT.md) | Source-admission and foundational-axiom policy |
| [`GATE_B_CLOSURE.md`](docs/formal_core_v2/GATE_B_CLOSURE.md) | Exact finite classical scope and limitations |
| [`PAPER_II_BOUNDED_SEED_LIBRARY_REFINEMENT.md`](docs/formal_core_v2/PAPER_II_BOUNDED_SEED_LIBRARY_REFINEMENT.md) | Bounded generator/packet-builder refinement |
| [`GATE_C_SCOPE.md`](docs/formal_core_v2/GATE_C_SCOPE.md) | Implemented selected quantum scope and open extensions |
| [`GATE_C_CLOSURE.md`](docs/formal_core_v2/GATE_C_CLOSURE.md) | Selected Gate C theorem, audit, and claim boundary |

## Claim boundary

The current project establishes a clean, pinned, conditional formal theorem stack,
a nontrivial finite classical reference, and a selected finite-dimensional
diagonal quantum reference. It does **not** establish:

```text
exact full Paper I or Paper II semantic equivalence
arbitrary learned-system entry
arbitrary or unbounded generator/proof-search completeness
strict useful improvement at every recursive step
general noncommuting quantum relative entropy or channel theorems
arbitrary CPTP data processing
Petz or approximate recovery
Python checker/generator correctness
an executable recursive promotion loop
empirical recursive self-improvement
external benchmark performance
```

## Citation and licenses

Use `CITATION.cff` for the package citation and cite the two companion manuscripts
for the paper-level claims. Papers and documentation are intended for CC BY 4.0;
Lean code and software utilities are intended for MIT. See `LICENSE` and
`LICENSES/`.
