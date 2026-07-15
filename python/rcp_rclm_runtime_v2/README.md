# RCP/RCLM Runtime v2

This package contains the deterministic Phase 1 runtime bedrock, the validated
Phase 2 pinned Lean conformance bridge, the Phase 3 deterministic checker, the
Phase 4 hardened checker and adversarial rejection suite, the Phase 5A bounded
reference generator, and the cross-platform validated Phase 6 selector, filesystem
realizer, rollback builder, and candidate-package verifier.

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
The candidate package remains unverified for promotion; Phase 7 must run objective
evaluation, the checker, and the Lean bridge before any active-package replacement.
The exact clean implementation and artifact record is
`docs/executable_core_v2/PHASE_6_VALIDATION.md`.

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

## Boundary

The executable mathematical scope remains the declared finite Gate B binary and
selected Gate C diagonal-quantum checker semantics. Phase 6 does not add arbitrary
noncommuting matrices or channels. It also does not implement promotion, active-package
replacement, promotion-ledger mutation, independent replay, open-ended-generator
correctness, PyTorch learning, or external benchmark claims.
