# RCP/RCLM Runtime v2

This package contains the deterministic Phase 1 runtime bedrock, the validated
Phase 2 pinned Lean conformance bridge, the Phase 3 deterministic checker, the
Phase 4 hardened checker and adversarial rejection suite, the Phase 5A bounded
reference generator, the Phase 6 selector and filesystem candidate-package builder,
and the Phase 7 fixed-budget promotion and rollback controller.

## Phase 1 bedrock

Implemented and cross-platform validated:

- immutable runtime records and strict parsers;
- reduced exact rational arithmetic;
- certified outward rational logarithm intervals;
- Gate B finite distributions, Shannon entropy, support-aware KL, zero extension,
  and exact recovery;
- selected Gate C two-level diagonal density matrices, spectral entropy, diagonal
  QRE, identity/swap channels, and exact selected recovery;
- canonical JSON, semantic paths, content hashing, and semantic-tree hashing;
- RCLM-to-RCP forgetful mappings;
- generated-Lean source hygiene checks.

## Phase 2 initial Lean bridge

Implemented and validated:

- a closed immutable Gate B/Gate C reference-packet grammar;
- deterministic Python interpretation for ten accept/reject cases;
- deterministic generated Lean certificate source;
- mandatory pre-compilation rejection of admitted-proof tokens and local axioms;
- verification of the frozen formal-source Git commit and exact Lean/mathlib pins;
- pinned `lake env lean` invocation;
- canonical structured Lean verdict parsing with independent RCP and RCLM fields;
- fail-closed Python/Lean differential comparison;
- Linux, Windows, and macOS Python bridge tests;
- a clean pinned Linux Lean build and ten-case conformance run.

## Phase 3 deterministic checker

The checker core is a pure function over immutable records. It is deterministic,
model-free, network-free, generator-independent, and fail-closed. Candidate fields
that merely claim preservation, containment, improvement, trust, or acceptance are
not part of the request schema and are rejected as unknown.

## Phase 4 hardened checker and attack suite

The hardened envelope composes the Phase 3 checker with independently measured
package-integrity records. The deterministic adversarial suite records 27 first-class
schema, replay, tamper, numerical, selected-quantum, resource, trust, provenance, and
generated-source attacks.

## Phase 5A bounded reference generator

The first generator implements only the finite Gate B seed grammar declared in Lean.
It runs in a separate capability-minimized process and emits only a bounded proposal.
Trusted orchestration validates the proposal, constructs the certificate, selects the
update, derives the logical successor, invokes the pinned Lean bridge, and calls the
Phase 4 hardened checker.

Run the generator process suite:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase5a_process_suite.py \
  --out artifacts/runtime_v2_phase_5a/local/process_suite.json
```

## Phase 6 selector, realizer, and package builder

Phase 6 turns the validated proposal into an actual filesystem candidate without
promoting it. It:

```text
measures the predecessor package from bytes
→ validates proposal and predecessor bindings
→ selects explicit file operations
→ copies the payload into an isolated workspace
→ applies only selected operations
→ records exact before/after hashes
→ rejects metadata-only or state-only successors
→ builds and independently restores a rollback archive
→ writes a realized_unverified candidate package
→ publicly reverifies all package bindings
→ atomically publishes the package
```

The reference cases introduce genuine verification-policy and memory-policy changes.
The candidate remains unverified for promotion until the Phase 7 controller invokes
objective evaluation, the pinned Lean bridge, and the hardened checker.

Run the Phase 6 unit suite:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase6_tests.py \
  --package-root python/rcp_rclm_runtime_v2 \
  --out artifacts/runtime_v2_phase_6/local/phase_6_unit.log
```

Build both reference filesystem candidates:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase6_reference_suite.py \
  --outdir artifacts/runtime_v2_phase_6/local/reference_suite
```

## Phase 7 promotion and rollback controller

Phase 7 coordinates the existing components without replacing the checker:

```text
load immutable active package
→ invoke the untrusted generator twice
→ validate replay and proposal bindings
→ realize and publicly verify a Phase 6 candidate
→ derive objective evidence from the measured states
→ construct the certificate outside the generator
→ invoke the pinned Lean bridge
→ invoke the Phase 4 hardened checker
→ reverify candidate immutability
→ install an immutable parent-linked package
→ append a hash-chained ledger entry
→ atomically replace the active pointer or restore it on activation failure
```

Retry is permitted only under the original fixed attempt and resource budgets.
Rejected candidates are not repaired. Indeterminate results remain nonpromoting. The
controller does not calculate authoritative Shannon/KL or von Neumann/QRE facts; the
checker and Lean bridge retain that authority.

Run the Phase 7 unit suite:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase7_tests.py \
  --package-root python/rcp_rclm_runtime_v2 \
  --out artifacts/runtime_v2_phase_7/local/phase_7_unit.log
```

Run the deterministic platform fixture trajectory:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase7_reference_suite.py \
  --outdir artifacts/runtime_v2_phase_7/local/reference_trajectory
```

Run the pinned-Lean promotion trajectory from the repository root:

```bash
python scripts/run_promotion_loop.py \
  --repo-root . \
  --store-root artifacts/runtime_v2_phase_7/local/store \
  --out artifacts/runtime_v2_phase_7/local/summary.json \
  --trajectory \
  --timeout-seconds 180
```

The clean implementation head is recorded in
`docs/executable_core_v2/PHASE_7_VALIDATION.md` and
`phase_7_validation.json`. The final documentation/evidence PR head is revalidated
before merge.

## Boundary

The executable mathematical scope remains the declared finite Gate B binary and
selected Gate C diagonal-quantum checker semantics. Phase 7 does not add arbitrary
noncommuting matrices or channels. It also does not implement independent replay,
open-ended-generator correctness, generator trust, PyTorch learning authority,
external benchmark claims, or autonomous/unbounded RSI.
