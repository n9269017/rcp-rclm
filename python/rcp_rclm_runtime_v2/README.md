# RCP/RCLM Runtime v2

This package contains the deterministic Phase 1 runtime bedrock, the validated
Phase 2 pinned Lean conformance bridge, the Phase 3 deterministic checker, the
Phase 4 hardened checker and adversarial rejection suite, and the Phase 5A
bounded reference generator.

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
model-free, network-free, generator-independent, and fail-closed.

It recomputes:

- exact RCLM canonical state/update/certificate lifts;
- the typed successor;
- typed and packet residuals;
- Shannon/von Neumann entropy and KL/QRE interval evidence;
- zero-budget protected non-loss;
- selected constructive recovery;
- protected invariants and reality containment;
- progress and the derived strict witness;
- trust-root, resource, provenance, and domain obligations;
- RCLM-to-RCP refinement and preservation monitors;
- exact packet binding to an accepting Phase 2 Lean report;
- canonical hashes of all authoritative inputs and derived bindings.

Candidate fields that merely claim preservation, containment, improvement, trust,
or acceptance are not part of the request schema and are rejected as unknown.

## Phase 4 hardened checker and attack suite

The hardened envelope composes the Phase 3 checker with independently measured
package-integrity records. It recomputes:

- predecessor and candidate semantic-tree hashes;
- candidate parent package and parent manifest links;
- candidate and certificate hashes;
- trust-anchor, resource-record, checker-policy, Lean-policy, and claim hashes;
- the pinned Phase 3 checker-manifest hash;
- a transition-binding hash over the predecessor, candidate, certificate,
  evaluation evidence, and Lean bridge report.

The deterministic adversarial suite records 27 first-class cases covering schema
attacks, evidence removal, parent/certificate replay, file and manifest tampering,
invalid numerical data, selected Gate C scope violations, forged witnesses,
insufficient interval margins, resource/provenance violations, and forbidden
generated Lean source.

## Phase 5A bounded reference generator

The first generator implements only the finite Gate B seed grammar declared in Lean.
It runs in a separate process and receives a canonical read-only view containing the
predecessor state and package hashes, public policy, objective, and resource bounds.
It receives no checker source, trust anchor, promotion ledger, previous-manifest write
handle, or reference answer.

The worker emits only a bounded word, witness, proposal name, depth/proof bounds,
resource use, and binding hashes. It does not emit a certificate, successor,
candidate, or acceptance Boolean. Trusted orchestration independently validates the
proposal, constructs the canonical certificate, selects the single permitted update,
derives the successor, invokes the pinned Lean bridge, and calls the Phase 4 hardened
checker.

Run the separate-process generator suite:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase5a_process_suite.py \
  --out artifacts/runtime_v2_phase_5a/local/process_suite.json
```

Run the complete pinned reference loop from the repository root:

```bash
python scripts/run_phase5a_reference_loop.py \
  --repo-root . \
  --outdir artifacts/runtime_v2_phase_5a/local/reference_loop
```

## Boundary

The executable scope remains the declared finite Gate B binary and selected Gate C
diagonal-quantum checker semantics. Phase 5A adds only the Gate B bounded generator
grammar. It does not implement a real filesystem realizer, promotion, rollback,
independent replay, open-ended search, program synthesis, LLM/scaffold generation,
PyTorch learning, external benchmarks, or arbitrary noncommuting quantum semantics.

The generator remains untrusted. A clean Phase 5A closure licenses Phase 5B
open-ended-generator experiments and Phase 6 realizer/package-builder development,
but does not license candidate promotion.
