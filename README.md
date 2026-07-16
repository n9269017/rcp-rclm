# RCP/RCLM — Robust Reflective Successor Verification

This repository contains the two companion RCP/RCLM manuscripts, the historical Lean v1
certificate, the pinned **RCP/RCLM Formal Core v2** Lean 4 project, **Executable Core v2
Phases 0–8**, and the first bounded **PyTorch learned-successor pilot**.

The project proves and executes a conditional successor-verification architecture. The
formal layer supplies the theorem kernel and the selected finite classical/diagonal
quantum instances. The executable layer supplies canonical records and hashing, a pinned
Lean bridge, a pure fail-closed checker, adversarial rejection, an untrusted generator,
filesystem realization and rollback, atomic promotion, and independent replay. The
PyTorch pilot adds one optional untrusted CPU-only training backend without moving
PyTorch into the checker or any other source-of-truth component.

The repository establishes a finite theorem-to-runtime refinement witness at the declared
reference scope. It does **not** prove autonomous or unbounded recursive self-improvement,
generator completeness, useful strict improvement at every step, or general
noncommuting quantum semantics.

## Authoritative status

| Layer | Status | Declared scope |
|---|---|---|
| Gate A — abstract theorem kernel | Complete, clean-CI built, axiom audited | Conditional successor soundness, finite composition, endpoint recovery, preservation monitors, and conditional infinite closure under explicit successor availability |
| Gate B — finite classical instance | Complete | Finite distributions, Shannon entropy, support-aware KL, zero-coordinate conservative extension, exact recovery, binary improvement/stability checker, and bounded seed grammar |
| Gate B RCLM-to-RCP refinement | Complete | Architecture state/update/certificate fields, checker refinement, recovery/monitor transport, and trust/resource/domain premises |
| Gate C — selected quantum instance | Complete and audited at the commuting/diagonal scope | Certified complex diagonal densities, spectral von Neumann entropy, support-aware diagonal QRE, identity/swap channels, exact selected recovery, checker, finite trajectory, and RCLM refinement |
| General noncommuting quantum extension | Open | No arbitrary noncommuting densities, general CPTP maps, matrix-log QRE, general data processing, or Petz-recovery claim |
| Executable Core v2 Phase 0 | Complete | Frozen object map, trust boundary, numerical semantics, canonical serialization/hashing, acceptance semantics, and claim boundary |
| Phase 1 | Complete and cross-platform validated | Immutable types, exact rationals, certified intervals, selected Gate B/Gate C mathematics, canonical hashes, and source hygiene |
| Phase 2 | Complete at the selected finite scope | Pinned Lean certificate generation/compilation, structured verdicts, and ten-case differential conformance |
| Phase 3 | Complete and cross-platform validated | Pure deterministic model-free checker with recomputed obligation reports |
| Phase 4 | Complete and cross-platform validated | Hardened package bindings and 27 first-class adversarial/tamper rejections |
| Phase 5A | Complete and cross-platform validated | Separate-process bounded Gate B proposal grammar, two-run replay, host-owned certificate/selection/realization, Lean and checker admission |
| Phase 6 | Complete and cross-platform validated | Isolated filesystem realization, substantive changes, before/after hashes, resource records, rollback restoration, and immutable candidate packages |
| Phase 7 | Complete and cross-platform validated | Fixed-budget retries, pinned Lean/checker admission, immutable parent-linked packages, hash-chained ledger, atomic active pointer, and rollback fallback |
| Phase 8 | Complete and cross-platform/pinned-Lean validated | Portable retained evidence, zero-generator replay, fresh realization/certificate/Lean/checker recomputation, two promotions, two bounded rejections, and a three-package chain |
| First PyTorch learned-successor pilot | Complete at the declared tiny CPU-only scope | Two deterministic proposal runs, one genuine SGD update, canonical int64 weight package, exact framework-independent evaluation, protected-metric non-regression, fail-closed admission, atomic promotion/rejection, rollback, and zero-training replay |
| Larger/open-ended learned generators and benchmarks | Open | No learned proposal authority, GPU reproducibility, LLM-scale training, architecture search, external benchmark claim, or autonomous RSI |

Formal documentation is indexed at
[`docs/formal_core_v2/README.md`](docs/formal_core_v2/README.md). Executable documentation
is indexed at [`docs/executable_core_v2/README.md`](docs/executable_core_v2/README.md).

## Pinned formal project

The active Lean project is:

```text
lean/rcp_rclm_formal_core_v2/
```

It pins:

```text
Lean:    leanprover/lean4:v4.31.0
mathlib: fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
```

The frozen formal source commit used by Runtime v2 is:

```text
012de4a55f326107f53f0e215c8aec62859d0bbf
```

The historical v1 project remains under `lean/rcp_rclm_can_lean4/`; v2 does not overwrite
or silently broaden that certificate.

## Repository map

```text
papers/
  paper-I-rcp-math/
  paper-II-rclm-architecture/

lean/
  rcp_rclm_formal_core_v2/       active pinned Formal Core v2
  rcp_rclm_can_lean4/            historical v1 certificate

docs/formal_core_v2/             theorem, gate, audit, and reproduction records
docs/executable_core_v2/         Phase 0–8 and PyTorch-pilot architecture/validation

python/rcp_rclm_executable_core_v2/
  contract/                       strict executable schemas

python/rcp_rclm_runtime_v2/
  rcp_rclm_runtime/
    canonical/                    canonical JSON, paths, content/tree hashes
    mathematics/                  exact Gate B and selected Gate C mathematics
    refinement/                   RCLM-to-RCP executable mappings
    lean_bridge/                  generated-source guard and pinned Lean verifier
    checker/                      Phase 3 checker and Phase 4 hardened envelope
    adversarial/                  deterministic Phase 4 attack suite
    generator/                    Phase 5A bounded untrusted worker/process
    successor/                    Phase 6 selector, realizer, package, rollback
    promotion/                    Phase 7 immutable store, ledger, pointer, controller
    replay/                       Phase 8 bundle and generator-free reproducer
    torch_backend/                optional untrusted CPU PyTorch pilot and model-free replay
  tests*/                         Phase-specific regression suites
  tests_pytorch_pilot/            learned proposal/admission/replay tests
  tools/                          conformance and artifact runners

scripts/
  check_candidate.py
  check_hardened_candidate.py
  run_phase5a_reference_loop.py
  build_candidate_package.py
  run_promotion_loop.py
  build_replay_bundle.py
  reproduce_run.py
  run_pytorch_pilot.py
  run_pytorch_pilot_controller.py
  replay_pytorch_pilot.py
```

## Formal theorem shape

For an admissible invariant-preserving predecessor and a trusted checker, accepted
candidate/certificate evidence yields a one-step obligation bundle:

```text
typed successor validity
computed residual nonpositivity
protected-distinction non-loss
constructive candidate-tied recovery
protected-invariant preservation
progress nondecrease
strict progress when a strict witness is certified
trust/verifier validity
resource validity
reality/uncertainty containment
successor-domain admissibility
```

Gate A composes the obligations over finite accepted trajectories and proves conditional
infinite closure only under an explicit successor-availability premise. Checker soundness
is not generator completeness.

Gate B instantiates the theorem with exact finite classical objects. Gate C instantiates
the selected two-level commuting/diagonal quantum reference. The latter does not imply a
general noncommuting theorem.

## Executable theorem-to-runtime path

```text
Phase 0  freeze refinement contract and trust boundary
Phase 1  implement exact deterministic runtime bedrock
Phase 2  bind selected packets to the pinned Lean project
Phase 3  recompute all checker obligations
Phase 4  reject schema, tamper, numeric, trust, and proof-token attacks
Phase 5A run the bounded untrusted reference proposal process
Phase 6  realize actual filesystem candidates and verified rollback snapshots
Phase 7  promote or reject through Lean/checker-controlled atomic transactions
Phase 8  replay retained transitions without invoking the original generator
```

The validated finite reference trajectory is:

```text
RCLM_0 — immutable initial root
→ RCLM_1 — target plus a substantive verification-policy change
→ RCLM_2 — target plus a substantive memory-policy change
→ bounded rejection
→ bounded rejection
→ active package remains RCLM_2
```

Phase 8 re-realizes candidate packages, reconstructs certificates, regenerates and scans
Lean source, reruns Lean and the hardened checker, verifies rollback and parent links, and
records zero original-generator invocations.

## First PyTorch learned-successor pilot

PyTorch remains an optional **untrusted proposal backend**. It is not used as the source
of truth for canonical serialization, hashing, certificate arithmetic, KL/QRE bounds,
trust, checker acceptance, promotion, rollback, or replay.

The frozen pilot uses:

```text
model:                 Linear(2, 2), with bias
device:                CPU only
training dtype:        float64
canonical weight type: little-endian int64
seed:                  1729
threads:               1
optimizer:             SGD
optimizer steps:       exactly 1
train examples:        4
held-out examples:     4
GPU/network:           forbidden
```

The training worker receives no held-out labels. It emits an untrusted proposal and raw
canonical tensor files. A framework-independent exact integer evaluator recomputes the
held-out and protected metrics from the realized package. The accepted reference changes
the model hash, improves held-out correctness from `2/4` to `4/4`, and preserves the
protected class-0 result at `2/2`.

The learned candidate then follows the existing trusted-after-validation path:

```text
predecessor model package
→ two isolated PyTorch proposal runs
→ host-constructed Phase 6 selection
→ actual candidate package and rollback snapshot
→ exact model-free evaluation
→ host-owned certificate
→ generated-Lean source guard and pinned Lean verifier
→ Phase 4 hardened checker
→ Phase 7 atomic promotion or fail-closed rejection
→ independent replay after removing the training worker
```

The negative fixture fails the exact learned objective, does not promote, preserves the
active predecessor, and verifies rollback. The independent reproducer records zero
training invocations and no loaded training-backend module.

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

Install Runtime v2 and the optional pinned pilot dependency:

```bash
cd python/rcp_rclm_runtime_v2
python -m pip install --no-deps -e .
python -m pip install '.[torch-pilot]'
```

Run all Python suites:

```bash
python -m compileall -q rcp_rclm_runtime tests tests_phase2 tests_phase3 tests_phase4 tests_phase5 tests_phase6 tests_phase7 tests_phase8 tests_pytorch_pilot tools
python tools/validate_source_quality.py --package-root . --out source_quality.json
python -m unittest discover -s tests -v
python -m unittest discover -s tests_phase2 -v
python -m unittest discover -s tests_phase3 -v
python -m unittest discover -s tests_phase4 -v
python -m unittest discover -s tests_phase5 -v
python -m unittest discover -s tests_phase6 -v
python -m unittest discover -s tests_phase7 -v
python -m unittest discover -s tests_phase8 -v
python -m unittest discover -s tests_pytorch_pilot -v
```

Principal repository-root entry points include:

```bash
python scripts/run_promotion_loop.py --repo-root . --store-root artifacts/phase7/store --out artifacts/phase7/summary.json --trajectory
python scripts/build_replay_bundle.py --source-store artifacts/phase7/store --output artifacts/phase8/bundle
python scripts/reproduce_run.py --repo-root . --bundle artifacts/phase8/bundle --outdir artifacts/phase8/reproduced
python scripts/run_pytorch_pilot.py --outdir artifacts/pytorch/proposal
python scripts/run_pytorch_pilot_controller.py --repo-root . --store-root artifacts/pytorch/store --out artifacts/pytorch/controller.json --expect promoted
python scripts/replay_pytorch_pilot.py --repo-root . --store-root artifacts/pytorch/store --outdir artifacts/pytorch/replay --summary artifacts/pytorch/replay.json --require-training-source-absent
```

## Next research boundary

Later optional work may introduce learned experiment selection, proposal ranking, planners,
adapters/LoRA, optimizer-policy changes, or architecture changes. Every such component
must remain inside the successor package hash boundary and outside checker authority.
Large external benchmarks should follow—not precede—the corresponding deterministic
containment, rollback, promotion, and replay evidence.

## Claim boundary

The repository does **not** establish:

```text
exact full Paper I or Paper II semantic equivalence
arbitrary learned-system entry or learned proposal authority
arbitrary or unbounded generator/proof-search completeness
strict useful improvement at every recursive step
general noncommuting QRE or arbitrary CPTP data processing
Petz or approximate recovery
general Python-to-Lean refinement beyond the declared packets
independent replay beyond the declared finite reference and tiny-model pilot scopes
GPU reproducibility or LLM-scale learned refinement
external benchmark performance
autonomous or unbounded RSI
```

## Citation and licenses

Use `CITATION.cff` for the package citation and cite the companion manuscripts for
paper-level claims. Papers and documentation are intended for CC BY 4.0; Lean code and
software utilities are intended for MIT. See `LICENSE` and `LICENSES/`.
