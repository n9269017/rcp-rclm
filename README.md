# RCP/RCLM — Robust Reflective Successor Verification

This repository contains the two companion RCP/RCLM manuscripts, the historical
Lean v1 certificate, the completed pinned **RCP/RCLM Formal Core v2** Lean 4
reference scopes, and Phases 0 through 5A of the **Executable Core v2** transition.

The formal project proves a conditional successor-verification theorem stack. The
Executable Core contract, deterministic bedrock, finite-reference Lean bridge,
fail-closed checker, adversarial rejection suite, and bounded reference generator do
not claim that checker soundness creates a successor, that every accepted successor is
strictly useful, or that the current repository is an autonomous
recursive-self-improvement system.

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
| Executable Core v2 Phase 2 | Complete at the selected finite reference scope | Pinned formal-source/toolchain verification, generated Lean certificates, structured RCP/RCLM verdicts, and ten-case Python/Lean differential conformance |
| Executable Core v2 Phase 3 | Complete and cross-platform validated at the selected scope | Deterministic pure checker, recomputed obligation bundle, structured reports, and packet-bound Lean evidence |
| Executable Core v2 Phase 4 | Complete and cross-platform validated at the declared attack scope | Hardened package integrity, 27 deterministic replayed attacks, first-class rejection records, and pinned Lean/source-guard revalidation |
| Executable Core v2 Phase 5A | Complete and cross-platform/pinned-Lean validated | Separate-process bounded Gate B generator, deterministic replay, direct Lean grammar conformance, certificate construction, typed selection, computed realization, and hardened checking |
| Phase 5B, production realization, promotion, replay, PyTorch, and benchmark adapters | Not licensed | No generator trust, candidate promotion, autonomous recursive improvement, or external benchmark claim |

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
  contract/                       frozen schemas for Phases 0, 3, 4, and 5A

python/rcp_rclm_runtime_v2/
  rcp_rclm_runtime/
    checker/                      Phase 3 checker and Phase 4 hardened envelope
    adversarial/                  Phase 4 attack records and deterministic runner
    generator/                    Phase 5A bounded worker and pipeline
    lean_bridge/                  Phase 2 pinned Lean bridge
    mathematics/                  exact Gate B and selected Gate C mathematics
  tests/                          Phase 1 deterministic tests and frozen vectors
  tests_phase2/                   Phase 2 bridge tests
  tests_phase3/                   Phase 3 checker tests
  tests_phase4/                   Phase 4 hardened and adversarial tests
  tests_phase5/                   Phase 5A generator and pipeline tests
  tools/                          validation, test, conformance, and report runners

scripts/
  check_candidate.py
  check_hardened_candidate.py
  generate_candidate.py

.github/workflows/
  formal-core-v2.yml
  executable-core-v2-contract.yml
  runtime-v2-phase-1.yml
  runtime-v2-phase-2.yml
  runtime-v2-phase-3.yml
  runtime-v2-phase-4.yml
  runtime-v2-phase-5.yml
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

The bedrock does not accept or promote candidates.

### Phase 2 — pinned Lean conformance bridge

Phase 2 adds the initial hybrid reference bridge:

```text
strict finite Gate B/Gate C reference packets
independent deterministic Python interpretation
deterministic generated Lean certificate source
pre-compilation source guard
formal-source Git and toolchain pin verification
pinned Lean compilation
structured RCP and RCLM verdict parsing
fail-closed differential comparison
raw source, stdout, stderr, compiler, pin, and toolchain evidence
```

The clean reference suite contains four accepted improvement/stability cases and six
rejected wrong-successor, wrong-certificate, or malformed-certificate mutations. It
establishes agreement only for those ten selected cases; it is not the production
successor checker and does not authorize promotion.

### Phase 3 — deterministic checker

Phase 3 is the first core executable decision engine. It is deterministic, pure over
immutable input records, model-free, network-free, generator-independent, and
fail-closed. It independently recomputes:

```text
typed successor and residuals
state-derived exact distributions or diagonal spectra
Shannon/von Neumann entropy and KL/QRE certified intervals
protected non-loss and constructive recovery
invariant, containment, progress, strict-witness, trust, resource, and domain checks
RCLM-to-RCP refinement and preservation monitors
exact packet binding to an accepting Phase 2 Lean report
canonical artifact hashes
```

The final Boolean is derived from the structured tri-state report. Candidate fields
that merely assert success are not accepted as evidence.

### Phase 4 — adversarial and tamper rejection

Phase 4 composes the checker with a package-integrity envelope and attacks the
resulting boundary before a generator exists. The hardened layer recomputes:

```text
predecessor and candidate semantic-tree hashes
parent package and parent-manifest links
candidate and certificate hashes
trust, resource, checker-policy, Lean-policy, and claim-boundary hashes
pinned checker-manifest hash
transition binding over predecessor, candidate, certificate, evaluation, and Lean evidence
```

The deterministic suite records malformed, replay, tamper, numerical, resource,
trust, provenance, selected-quantum-scope, forged-witness, and generated-Lean-source
attacks as first-class results. Every attack is executed twice, must reproduce the
same structured observation hash, and must remain nonaccepting.

### Phase 5A — deterministic bounded reference generator

Phase 5A implements the compiled classical bounded seed grammar:

```text
initial → improve
target  → stabilize
maximum update-word depth = 1
maximum proof-word length = 1
```

The generator runs in a separate isolated Python process. Its canonical request
contains only the predecessor package, public generator policy, declared objective,
and resource budget. Lazy package startup prevents checker imports; after startup, a
Python audit hook denies all filesystem opens, filesystem mutations, sockets, and
subprocess creation.

Every proposal is generated twice in fresh temporary directories and must reproduce
an identical canonical response hash. Outside the generator, the runtime constructs
the certificate, selects the typed update, computes the successor, directly compiles
Lean assertions for the bounded grammar, runs the generated-candidate Lean bridge, and
submits the result to the Phase 4 hardened checker.

The clean validation passed on Linux, Windows, and macOS, directly compiled the bounded
Lean grammar, and accepted both the initial-improvement and target-stability pipelines.
The selected Gate C mathematics remains available to the checker, but Phase 5A does
not claim a Gate C generator because the formal bounded seed-library implementation is
currently classical binary.

Phase 5A closure licenses development of open-ended **untrusted** proposal backends
and the production selector/realizer/package-builder boundary. It does not make a
generator trusted and does not authorize promotion.

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

## Install and validate Runtime v2

```bash
cd python/rcp_rclm_runtime_v2
python -m pip install --no-deps -e .
python -m compileall -q rcp_rclm_runtime tests tests_phase2 tests_phase3 tests_phase4 tests_phase5 tools
python tools/validate_source_quality.py --package-root . --out source_quality.json
python tools/validate_phase1_release.py phase_1_validation.json
python tools/validate_phase2_release.py phase_2_validation.json
python -m unittest discover -s tests -v
python -m unittest discover -s tests_phase2 -v
python -m unittest discover -s tests_phase3 -v
python -m unittest discover -s tests_phase4 -v
python -m unittest discover -s tests_phase5 -v
python tools/run_phase4_adversarial.py --out phase_4_adversarial.json
python tools/run_phase5_reference_replay.py --outdir phase_5_reference_replay
```

Run the pinned bridge from the repository root with:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase2_conformance.py \
  --repo-root . \
  --outdir artifacts/runtime_v2_phase_2/local
```

Run the hardened checker with:

```bash
python scripts/check_hardened_candidate.py request.json \
  --out hardened_checker_report.json
```

Run the bounded generator proposal worker with:

```bash
python scripts/generate_candidate.py generator_input.json \
  --out generator_replay.json
```

Run the complete Phase 5A pinned pipeline with:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase5_reference_pipeline.py \
  --repo-root . \
  --outdir artifacts/runtime_v2_phase_5/local
```

The authoritative workflows are:

```text
.github/workflows/runtime-v2-phase-1.yml
.github/workflows/runtime-v2-phase-2.yml
.github/workflows/runtime-v2-phase-3.yml
.github/workflows/runtime-v2-phase-4.yml
.github/workflows/runtime-v2-phase-5.yml
```

## Claim boundary

The repository establishes a clean, pinned formal theorem stack, deterministic
runtime mathematics, a finite-reference Python/Lean conformance bridge, a selected-
scope executable checker, a deterministic adversarial rejection implementation, and
a finite classical bounded reference-generator implementation. It does **not**
establish:

```text
exact full Paper I or Paper II semantic equivalence
arbitrary learned-system entry
arbitrary or unbounded generator/proof-search completeness
generator trust or open-ended generator correctness
strict useful improvement at every recursive step
Gate C bounded generator refinement
general noncommuting quantum relative entropy or channel theorems
arbitrary CPTP data processing
Petz or approximate recovery
general Python-to-Lean refinement beyond the selected reference packets
candidate promotion authorization
an executable recursive promotion loop
independent replay without the original generator
empirical recursive self-improvement
external benchmark performance
```

## Citation and licenses

Use `CITATION.cff` for the package citation and cite the two companion manuscripts
for paper-level claims. Papers and documentation are intended for CC BY 4.0; Lean
code and software utilities are intended for MIT. See `LICENSE` and `LICENSES/`.
