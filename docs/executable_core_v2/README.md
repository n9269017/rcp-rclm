# RCP/RCLM Executable Core v2

This directory is the documentation index for the frozen theorem-to-runtime contract,
Executable Core v2 Phases 0–8, and the first bounded PyTorch learned-successor pilot.
The executable project follows the completed Formal Core v2 Lean theorem stack and keeps
untrusted proposal systems outside the checker and promotion authority.

## Status

```text
Phase 0 theorem-to-runtime contract: complete and merged
Phase 1 deterministic runtime bedrock: complete and cross-platform validated
Phase 2 pinned Lean conformance bridge: complete at the selected finite scope
Phase 3 deterministic fail-closed checker: complete and cross-platform validated
Phase 4 adversarial and tamper rejection: complete and cross-platform validated
Phase 5A deterministic bounded reference generator: complete and cross-platform validated
Phase 6 selector, realizer, rollback, and package builder: complete and cross-platform validated
Phase 7 promotion and rollback controller: complete and cross-platform validated
Phase 8 independent replay: complete and cross-platform/pinned-Lean validated
First CPU-only PyTorch learned-successor pilot: complete at the declared tiny-model scope
Open-ended learned generators and external benchmarks: open and untrusted
```

Frozen formal source:

```text
Formal source commit: 012de4a55f326107f53f0e215c8aec62859d0bbf
Lean:                 leanprover/lean4:v4.31.0
mathlib:              fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
```

## Phase 0 contract

| Document | Frozen decision |
|---|---|
| `THEOREM_TO_RUNTIME_CONTRACT.md` | Overall refinement contract and phase ordering |
| `OBJECT_CORRESPONDENCE.md` | Lean declaration to schema, Python type, runtime function, evidence, and test |
| `TRUST_BOUNDARY.md` | Trusted, trusted-after-validation, and untrusted components |
| `NUMERICAL_SEMANTICS.md` | Exact rational data, certified intervals, support rules, and comparisons |
| `CANONICAL_SERIALIZATION.md` | Canonical JSON, path, content, tree, and parent hashing |
| `ACCEPTANCE_SEMANTICS.md` | Fail-closed tri-state acceptance predicate |
| `CLAIM_BOUNDARY.md` | Licensed and unlicensed claims |
| `PYTORCH_ENTRY_CRITERIA.md` | Preconditions and authority limits for learned proposal backends |

## Phase documentation

### Phases 1–4

These phases provide the immutable numerical/runtime bedrock, selected Gate B/Gate C
mathematics, the pinned Lean bridge, the pure checker, and the hardened 27-case attack
boundary. Their architecture, validation, and exit-criteria documents use the
`PHASE_1_*` through `PHASE_4_*` prefixes.

### Phase 5A — bounded reference generator

| Document | Purpose |
|---|---|
| `PHASE_5A_REFERENCE_GENERATOR.md` | Bounded Lean grammar mapping, process boundary, and end-to-end path |
| `PHASE_5A_EXIT_CRITERIA.md` | Isolation, replay, Lean, checker, and licensing criteria |
| `PHASE_5A_VALIDATION.md` | Cross-platform process and pinned-Lean evidence |
| `PHASE_5B_ENTRY_CRITERIA.md` | Preconditions for optional open-ended proposal systems |

The worker emits only an untrusted bounded proposal. Certificate construction, update
selection, logical realization, Lean verification, and checker admission remain outside
the worker.

### Phase 6 — selector, realizer, rollback, and package builder

| Document | Purpose |
|---|---|
| `PHASE_6_SELECTOR_REALIZER_PACKAGE_BUILDER.md` | Filesystem measurement, realization, rollback, packaging, and public verification |
| `PHASE_6_EXIT_CRITERIA.md` | Substantive-change, resource, rollback, package, and CI criteria |
| `PHASE_6_VALIDATION.md` | Exact workflow, package, hash, and artifact evidence |

Phase 6 constructs `realized_unverified` packages from actual bytes. It does not promote
them.

### Phase 7 — promotion and rollback controller

| Document | Purpose |
|---|---|
| `PHASE_7_PROMOTION_CONTROLLER.md` | Controller architecture, immutable store, ledger, pointer, and rollback fallback |
| `PHASE_7_EXIT_CRITERIA.md` | Closed fixed-budget and promotion criteria |
| `PHASE_7_VALIDATION.md` | Phase 0–7 workflow and finite-trajectory evidence |

The controller coordinates but does not replace the checker. It can promote only after
pinned Lean and hardened-checker acceptance, installs an immutable parent-linked package,
and changes visibility through one atomic active-pointer replacement.

### Phase 8 — independent replay

| Document | Purpose |
|---|---|
| `PHASE_8_INDEPENDENT_REPLAY.md` | Portable retained-evidence boundary and zero-generator reproducer |
| `PHASE_8_EXIT_CRITERIA.md` | Cross-platform, pinned-Lean, tamper, and claim criteria |
| `PHASE_8_VALIDATION.md` | Exact workflow, trajectory, replay, and artifact hashes |

The validated finite reference witness contains three immutable packages, two promotions,
and two correctly reproduced bounded rejections. Replay succeeds after removing the
original generator executable and records zero generator invocations.

## First PyTorch learned-successor pilot

| Document | Purpose |
|---|---|
| `PYTORCH_PILOT.md` | Frozen model/training scope, package format, trust boundary, promotion, and replay path |
| `PYTORCH_PILOT_EXIT_CRITERIA.md` | Determinism, exact evaluation, admission, rollback, replay, and claim criteria |
| `PYTORCH_PILOT_VALIDATION.md` | Cross-platform and pinned-Lean learned-pilot evidence |

Machine-readable records are:

```text
python/rcp_rclm_executable_core_v2/contract/pytorch_pilot.schema.json
python/rcp_rclm_runtime_v2/pytorch_pilot_manifest.json
python/rcp_rclm_runtime_v2/pytorch_pilot_validation.json
```

The pilot is deliberately small and CPU-only:

```text
Linear(2, 2), with bias
float64 training
canonical little-endian int64 weights
seed 1729
one thread
one SGD step
four train examples
four held-out examples
```

PyTorch is used only in the isolated proposal process. The host validates canonical raw
tensor bytes, constructs the Phase 6 selection, realizes the package, evaluates the
model with exact Python integer arithmetic, constructs the certificate, and invokes the
existing Lean/checker/promotion path. Independent replay runs after the training process
and worker source are removed and records zero training invocations.

The accepted reference improves held-out correctness from `2/4` to `4/4` while retaining
the protected class-0 result at `2/2`. A negative fixture fails the exact learned
objective, remains nonpromoting, preserves the active predecessor, and verifies rollback.

## Dependency and authority order

```text
Formal Core v2 Gates A–C
→ Phase 0 frozen refinement contract
→ Phase 1 exact deterministic runtime
→ Phase 2 pinned Lean bridge
→ Phase 3 checker
→ Phase 4 hardened rejection
→ Phase 5A bounded untrusted generator
→ Phase 6 filesystem realization and rollback
→ Phase 7 atomic promotion controller
→ Phase 8 generator-free replay
→ optional untrusted PyTorch learned proposal pilot
→ later open-ended learned/search backends and external benchmarks
```

Candidate assertions, model scores, native floating-point diagnostics, and proposed
certificate fields are never authoritative. Canonical hashing, interval/exact arithmetic,
trust validation, checker acceptance, promotion, rollback, and replay remain
framework-independent.

## Claim boundary

The executable package establishes finite reference and tiny-model pilot witnesses only.
It does not establish generator trust, learned proposal authority, arbitrary
learned-system refinement, GPU reproducibility, general noncommuting quantum semantics,
unbounded successor availability, external benchmark performance, or autonomous RSI.
