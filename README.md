# RCP/RCLM — Robust Reflective Successor Verification

This repository contains the two companion RCP/RCLM manuscripts, the historical
Lean v1 certificate, the completed pinned **RCP/RCLM Formal Core v2** Lean 4
reference scopes, and the first two phases of the **Executable Core v2** transition.

The formal project proves a conditional successor-verification theorem stack. The
Executable Core contract and deterministic bedrock do not claim that checker
soundness creates a successor, that every accepted successor is strictly useful, or
that the current repository is an autonomous recursive-self-improvement system.

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
| Executable Core v2 Phase 0 | Complete and merged | Frozen theorem-to-runtime object map, trust boundary, numerical semantics, serialization/hashing, acceptance semantics, and claim boundary |
| Executable Core v2 Phase 1 | Complete and cross-platform validated | Immutable records, strict parsing, exact rationals, certified intervals, selected Gate B/Gate C mathematics, canonical hashing, RCLM mappings, source guard |
| Pinned Lean compiler/verifier bridge | Next phase; not implemented | Restricted generated certificate source, pinned Lean invocation, structured verifier reports, differential conformance |
| Production checker/generator/promotion loop | Not licensed | No candidate acceptance or promotion claim |

The formal documentation is indexed in
[`docs/formal_core_v2/README.md`](docs/formal_core_v2/README.md). The executable
transition is indexed in
[`docs/executable_core_v2/README.md`](docs/executable_core_v2/README.md).

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
  rcp_rclm_formal_core_v2/       active pinned formal project
  rcp_rclm_can_lean4/            historical v1 project

docs/formal_core_v2/             theorem, gate, audit, and reproduction records
docs/executable_core_v2/         theorem-to-runtime and runtime-phase records

python/rcp_rclm_executable_core_v2/
  contract/                       frozen Phase 0 machine-readable contract

python/rcp_rclm_runtime_v2/
  rcp_rclm_runtime/               deterministic Phase 1 bedrock
  tests/                          74 deterministic tests and frozen vectors
  tools/                          source-quality, report, and release validators

.github/workflows/
  formal-core-v2.yml
  executable-core-v2-contract.yml
  runtime-v2-phase-1.yml
```

## Formal Core v2 theorem shape

For an admissible, invariant-preserving predecessor and a trusted checker, accepted
candidate/certificate evidence yields the complete one-step obligation bundle:

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
premise. Checker soundness is never used to prove generator completeness.

## Gate B finite reference

Gate B supplies a concrete finite classical reference with actual Shannon entropy
and KL divergence, exact zero-coordinate conservative extension and recovery, a
strict KL-derived improvement witness, and a Boolean checker whose acceptance
refines to the abstract obligations.

The RCLM layer preserves theorem-relevant Gate A/B objects through an explicit
refinement map and adds separate architecture relations for generation, certificate
construction, candidate selection, realization, trust, resources, and
successor-domain closure.

## Gate C selected quantum reference

Gate C uses certified finite spectra embedded as complex diagonal matrices. It
proves Hermitian, positive-semidefinite, and trace-one properties, spectral von
Neumann entropy, support-aware diagonal QRE, identity/swap channel behavior, exact
selected recovery, a concrete quantum checker, finite trajectory properties, and
substantive RCLM refinement.

The closure is limited to the finite commuting/diagonal reference. It does not
establish arbitrary noncommuting density operators, arbitrary CPTP maps, general
matrix logarithms, general quantum data processing, or Petz recovery.

## Executable Core v2 transition

### Phase 0 — frozen contract

Phase 0 pins the Formal Core source and freezes:

```text
Lean declaration to schema/Python/runtime/evidence/test correspondence
trusted, trusted-after-validation, and untrusted components
exact rational and certified interval semantics
canonical JSON, path, content-hash, and tree-hash rules
fail-closed tri-state acceptance semantics
runtime and PyTorch claim boundaries
```

### Phase 1 — deterministic bedrock

Phase 1 implements and validates:

```text
immutable strict runtime records
exact reduced rational arithmetic
certified outward rational logarithm intervals
Gate B distributions, entropy, KL, extension, and recovery
selected Gate C diagonal densities, entropy, QRE, channels, and recovery
canonical JSON and semantic paths
content and semantic-tree hashing
RCLM-to-RCP forgetful mapping evidence
generated-Lean anti-placeholder/local-axiom source guard
Linux, Windows, and macOS conformance fixtures
```

The bedrock does not accept or promote candidates. The next licensed phase is the
pinned Lean compiler/verifier bridge and Python/Lean differential conformance.

## Build and validate Formal Core v2

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

## Install and validate the Phase 1 runtime

```bash
cd python/rcp_rclm_runtime_v2
python -m pip install --no-deps -e .
python -m compileall -q rcp_rclm_runtime tests tools
python tools/validate_source_quality.py .
python tools/validate_phase1_release.py phase_1_validation.json
python -m unittest discover -s tests -v
```

The authoritative CI workflow is:

```text
.github/workflows/runtime-v2-phase-1.yml
```

## Claim boundary

The repository establishes a clean, pinned formal theorem stack and a deterministic
runtime bedrock for selected finite references. It does **not** establish:

```text
exact full Paper I or Paper II semantic equivalence
arbitrary learned-system entry
arbitrary or unbounded generator/proof-search completeness
strict useful improvement at every recursive step
general noncommuting quantum relative entropy or channel theorems
arbitrary CPTP data processing
Petz or approximate recovery
Python-to-Lean differential refinement
production successor-checker soundness
an executable recursive promotion loop
empirical recursive self-improvement
external benchmark performance
```

## Citation and licenses

Use `CITATION.cff` for the package citation and cite the two companion manuscripts
for paper-level claims. Papers and documentation are intended for CC BY 4.0; Lean
code and software utilities are intended for MIT. See `LICENSE` and `LICENSES/`.
