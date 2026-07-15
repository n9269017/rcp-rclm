# RCP/RCLM — Robust Reflective Successor Verification

This repository contains the two companion RCP/RCLM manuscripts, the historical
Lean v1 certificate, the pinned **RCP/RCLM Formal Core v2** Lean 4 project, and
Phases 0 through 6 of the **Executable Core v2** transition.

The formal project proves a conditional successor-verification theorem stack. The
executable project instantiates a finite declared reference scope with exact runtime
records, a pinned Lean bridge, a fail-closed checker, an adversarial rejection suite,
an untrusted bounded generator, and a verified filesystem candidate-package builder.
It does not claim that checker soundness creates successors, that every accepted
successor is strictly useful, or that the repository is an autonomous unbounded
recursive-self-improvement system.

## Authoritative status

| Layer | Status | Exact scope |
|---|---|---|
| Gate A — abstract theorem kernel | Complete, clean-CI built, axiom audited | Abstract conditional successor, finite composition, endpoint recovery, monitors, and conditional infinite closure |
| Gate B — finite classical instance | Complete at the declared finite reference scope | Shannon entropy, support-aware KL, zero-coordinate conservative extension, exact recovery, strict improvement, concrete checker |
| Gate B RCLM-to-RCP refinement | Complete at the declared binary scope | Theorem-relevant state/update/certificate fields, checker acceptance, recovery laws, monitors, and architecture obligations |
| Paper II engine and seed-library interfaces | Implemented with explicit premises | Generator/certifier/selector/realizer relations, trust/resource/domain premises, finite bounded packet grammar |
| Gate C — selected quantum instance | Complete and audited at the declared commuting/diagonal scope | Certified complex diagonal densities, spectral von Neumann entropy and QRE, identity/swap channels, exact recovery, checker, trajectory, and RCLM refinement |
| General noncommuting quantum extension | Open | No arbitrary noncommuting densities, general CPTP maps, matrix-log QRE, data processing, or Petz recovery claim |
| Executable Core v2 Phase 0 | Complete and merged | Frozen object map, trust boundary, numerical semantics, serialization/hashing, acceptance semantics, and claim boundary |
| Executable Core v2 Phase 1 | Complete and cross-platform validated | Immutable records, exact rationals, certified intervals, selected Gate B/Gate C mathematics, canonical hashing, source guard |
| Executable Core v2 Phase 2 | Complete at the selected finite reference scope | Pinned toolchain verification, generated Lean certificates, structured RCP/RCLM verdicts, ten-case differential conformance |
| Executable Core v2 Phase 3 | Complete and cross-platform validated | Deterministic pure checker, recomputed obligation bundle, structured reports, packet-bound Lean evidence |
| Executable Core v2 Phase 4 | Complete and cross-platform validated | Hardened package integrity, 27 deterministic adversarial cases, first-class rejection records, pinned Lean revalidation |
| Executable Core v2 Phase 5A | Complete and cross-platform validated | Separate-process bounded Gate B proposals, two-run replay, host-owned certificate/selection/logical realization, Lean and hardened-checker acceptance |
| Executable Core v2 Phase 6 | Complete and cross-platform validated at the reference package scope | Actual predecessor measurement, isolated realization, substantive policy changes, before/after hashes, rollback restoration, immutable candidate packaging, public verification |
| Phase 5B, promotion, independent replay, PyTorch, and benchmark adapters | Not yet licensed for claims | No generator trust, no candidate promotion, no autonomous RSI, and no external benchmark result |

The formal documentation is indexed in
[`docs/formal_core_v2/README.md`](docs/formal_core_v2/README.md). The executable
transition is indexed in
[`docs/executable_core_v2/README.md`](docs/executable_core_v2/README.md).

## Authoritative Lean project

The active project is:

```text
lean/rcp_rclm_formal_core_v2/
```

It pins:

```text
Lean:    leanprover/lean4:v4.31.0
mathlib: fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
```

The complete dependency graph is committed in
`lean/rcp_rclm_formal_core_v2/lake-manifest.json`.

The historical v1 project remains at:

```text
lean/rcp_rclm_can_lean4/
```

Formal Core v2 does not overwrite or silently broaden the historical certificate.

## Repository map

```text
papers/
  paper-I-rcp-math/
  paper-II-rclm-architecture/

lean/
  rcp_rclm_formal_core_v2/       active pinned formal project
  rcp_rclm_can_lean4/            historical v1 project

docs/formal_core_v2/             theorem, gate, audit, and reproduction records
docs/executable_core_v2/         theorem-to-runtime and executable-phase records

python/rcp_rclm_executable_core_v2/
  contract/                       frozen schemas for Phases 0, 3, 4, 5A, and 6

python/rcp_rclm_runtime_v2/
  rcp_rclm_runtime/
    mathematics/                  exact Gate B and selected Gate C mathematics
    lean_bridge/                  Phase 2 pinned Lean bridge
    checker/                      Phase 3 checker and Phase 4 hardened envelope
    adversarial/                  Phase 4 attack records and deterministic runner
    generator/                    Phase 5A bounded worker, protocol, process, and loop
    successor/                    Phase 6 selector, realizer, rollback, package verifier
  tests/                          Phase 1 deterministic tests and frozen vectors
  tests_phase2/                   Phase 2 bridge tests
  tests_phase3/                   Phase 3 checker tests
  tests_phase4/                   Phase 4 hardened and adversarial tests
  tests_phase5/                   Phase 5A generator and reference-loop tests
  tests_phase6/                   Phase 6 successor-package tests
  tools/                          validation, conformance, and artifact runners

scripts/
  check_candidate.py
  check_hardened_candidate.py
  generate_reference_candidate.py
  run_phase5a_reference_loop.py
  build_candidate_package.py

.github/workflows/
  formal-core-v2.yml
  executable-core-v2-contract.yml
  runtime-v2-phase-1.yml
  runtime-v2-phase-2.yml
  runtime-v2-phase-3.yml
  runtime-v2-phase-4.yml
  runtime-v2-phase-5a.yml
  runtime-v2-phase-6.yml
```

## Formal theorem shape

For an admissible invariant-preserving predecessor and a trusted checker, accepted
candidate/certificate evidence yields the one-step obligation bundle:

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

Gate B supplies a concrete finite classical reference with actual Shannon entropy and
KL divergence, exact zero-coordinate extension and recovery, a KL-derived strict
improvement witness, a binary checker, and a bounded improve/stabilize seed grammar.

Gate C uses certified finite spectra embedded as complex diagonal matrices. It proves
Hermitian, positive-semidefinite, and trace-one properties; spectral von Neumann
entropy; support-aware diagonal QRE; identity/swap behavior; exact selected recovery;
and finite checker/trajectory/RCLM properties. The claim remains limited to the
commuting/diagonal reference.

## Executable Core v2 phases

### Phase 0 — frozen theorem-to-runtime contract

Phase 0 freezes the Lean-to-schema/Python/runtime/evidence/test correspondence, trust
boundary, exact/interval numerical semantics, canonical JSON and tree hashing,
fail-closed tri-state acceptance, and claim limits.

### Phase 1 — deterministic runtime bedrock

Phase 1 implements immutable strict records, exact rational arithmetic, certified
outward log intervals, selected Gate B/Gate C mathematics, canonical paths and hashes,
RCLM-to-RCP mappings, and the generated-Lean anti-placeholder/local-axiom source gate.

### Phase 2 — pinned Lean conformance bridge

Phase 2 performs:

```text
canonical reference packet
→ independent Python interpretation
→ deterministic Lean source generation
→ pre-compilation source guard
→ exact formal-source and toolchain pin verification
→ pinned Lean compilation
→ structured RCP/RCLM verdict parsing
→ differential comparison and retained evidence
```

The declared suite contains four accepted references and six rejected mutations.

### Phase 3 — deterministic checker

The checker is deterministic, pure over immutable inputs, model-free, network-free,
generator-independent, and fail-closed. It recomputes typed successor and residuals,
state-derived distributions/spectra, entropy and KL/QRE intervals, protected non-loss,
recovery, invariants, containment, progress, strict witness, trust, resources, domain,
RCLM-to-RCP consistency, monitors, Lean-packet binding, and artifact hashes.

Candidate fields that merely assert success are not evidence.

### Phase 4 — adversarial and tamper rejection

Phase 4 adds parent/tree/candidate/certificate/trust/resource/policy/claim bindings and
records 27 deterministic schema, replay, tamper, numeric, scope, witness, resource,
trust, provenance, and generated-source attacks. Every required attack remains
nonaccepting.

### Phase 5A — deterministic bounded reference generator

The untrusted worker receives only an immutable predecessor view, public policy,
declared objective, and bounded resources. It emits only a bounded word, witness,
proposal name, and binding/resource fields. It cannot emit a certificate, successor,
checker result, or acceptance Boolean.

The host executes each request twice, validates replay, constructs the certificate,
selects the typed update, derives the logical successor, invokes the pinned Lean bridge,
and calls the hardened checker. The clean reference path covers:

```text
initial → improve → target
target  → stabilize → target
```

### Phase 6 — selector, realizer, rollback, and candidate package

Phase 6 converts a validated proposal into an actual filesystem candidate:

```text
measure actual predecessor bytes
→ validate proposal and parent bindings
→ select explicit file operations
→ copy payload into a fresh isolated workspace
→ apply only selected operations
→ remeasure the complete candidate tree
→ record before/after file and semantic hashes
→ require a genuine substantive component change
→ record commands, environment, and resource use
→ build and independently restore a deterministic rollback archive
→ write an immutable realized_unverified candidate package
→ publicly reverify all package bindings
→ atomically publish without overwriting an existing output
```

The `initial` reference changes the state and verification policy. The `target`
reference preserves the target state while changing the memory policy. Metadata-only,
state-only, name-, version-, timestamp-, schema-, index-, and manifest-only changes are
not substantive successors.

Phase 6 builds and verifies candidate packages but never promotes them. The exact clean
record is [`PHASE_6_VALIDATION.md`](docs/executable_core_v2/PHASE_6_VALIDATION.md).

## Build and validate

Build Formal Core v2:

```bash
cd lean/rcp_rclm_formal_core_v2
lake update
lake exe cache get
lake build
```

Run the theorem-axiom audits:

```bash
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateBAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateCAxiomAudit.lean
```

Install and test Runtime v2:

```bash
cd python/rcp_rclm_runtime_v2
python -m pip install --no-deps -e .
python -m compileall -q rcp_rclm_runtime tests tests_phase2 tests_phase3 tests_phase4 tests_phase5 tests_phase6 tools
python tools/validate_source_quality.py --package-root . --out source_quality.json
python -m unittest discover -s tests -v
python -m unittest discover -s tests_phase2 -v
python -m unittest discover -s tests_phase3 -v
python -m unittest discover -s tests_phase4 -v
python -m unittest discover -s tests_phase5 -v
python -m unittest discover -s tests_phase6 -v
```

Run the principal executable paths from the repository root:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase2_conformance.py \
  --repo-root . \
  --outdir artifacts/runtime_v2_phase_2/local

python scripts/run_phase5a_reference_loop.py \
  --repo-root . \
  --outdir artifacts/runtime_v2_phase_5a/local/reference_loop

python python/rcp_rclm_runtime_v2/tools/run_phase6_reference_suite.py \
  --outdir artifacts/runtime_v2_phase_6/local/reference_suite
```

## Next boundary

A clean Phase 6 closure licenses development of the Phase 7 promotion controller. That
controller must still perform objective evaluation, invoke the checker and Lean bridge,
atomically promote only a fully accepted package, hash-log all evidence, and roll back
on rejection. Phase 6 itself does not authorize active-package replacement.

Phase 5B open-ended proposal backends remain untrusted. A learned or open-ended backend
must not enter the controller before the stronger Phase 6–8 containment, promotion,
and independent-replay boundaries are closed. PyTorch and native floating-point model
outputs may propose or rank candidates later, but never determine canonical hashes,
KL/QRE certification, strict margins, trust validity, checker acceptance, promotion, or
replay.

## Claim boundary

The repository does **not** establish:

```text
exact full Paper I or Paper II semantic equivalence
arbitrary learned-system entry
arbitrary or unbounded generator/proof-search completeness
generator trust or open-ended generator correctness
strict useful improvement at every recursive step
general noncommuting QRE or arbitrary CPTP data processing
Petz or approximate recovery
general Python-to-Lean refinement beyond the declared reference packets
candidate promotion authorization
an executable recursive promotion loop
independent replay
empirical autonomous or unbounded RSI
external benchmark performance
```

## Citation and licenses

Use `CITATION.cff` for the package citation and cite the companion manuscripts for
paper-level claims. Papers and documentation are intended for CC BY 4.0; Lean code and
software utilities are intended for MIT. See `LICENSE` and `LICENSES/`.
