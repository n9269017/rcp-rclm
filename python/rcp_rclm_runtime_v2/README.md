# RCP/RCLM Runtime v2

This package contains the deterministic Phase 1 runtime bedrock, the validated
Phase 2 pinned Lean conformance bridge, the Phase 3 deterministic checker, the
Phase 4 hardened checker and adversarial rejection suite, and the validated Phase 5A
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
insufficient interval margins, resource/provenance violations, and forbidden generated
Lean source.

## Phase 5A deterministic reference generator

The generator implements the finite classical bounded seed grammar proved in Lean:

```text
initial → improve
target  → stabilize
maximum word depth = 1
maximum proof length = 1
```

The worker receives only the predecessor package, public generator policy, declared
objective, and resource budget. It executes in a separate isolated Python process.
Lazy package initialization prevents checker imports. After startup, its audit hook
denies all filesystem opens, filesystem mutations, sockets, and subprocess creation.
It has no request fields for checker source, trust anchors, previous-manifest history,
the promotion ledger, reference answers, certificates, successors, or verdicts.

Every invocation is executed twice in fresh temporary directories. The untrusted
proposal binds to the predecessor, policy, objective, budget, and full input hashes.
Outside the worker, the runtime independently:

```text
constructs the canonical certificate
selects the typed update
computes the successor from predecessor plus update
compiles direct Lean assertions for the bounded grammar
builds the generated candidate Lean packet
runs both source guards and pinned Lean compilations
runs the Phase 4 hardened checker
```

The clean validation passed on Linux, Windows, and macOS. It recorded 104 Python files
with zero source-quality issues, 14 Phase 5A tests, three deterministic process-replay
cases, direct pinned-Lean grammar conformance, and two accepting end-to-end reference
transitions.

Run only the separate generator worker through:

```bash
python -m pip install --no-deps -e python/rcp_rclm_runtime_v2
python scripts/generate_candidate.py generator_input.json \
  --out generator_replay.json
```

Run the complete pinned reference pipeline through:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase5_reference_pipeline.py \
  --repo-root . \
  --outdir artifacts/runtime_v2_phase_5/local
```

Run the Phase 5A unit suite with:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase5_tests.py \
  --package-root python/rcp_rclm_runtime_v2 \
  --out artifacts/runtime_v2_phase_5/local/phase_5_generator.log
```

## Boundary

The selected Gate C mathematics and checker remain implemented, but Phase 5A does not
claim a Gate C bounded generator because the formal bounded seed-library instance is
currently classical binary. Phase 5A also does not implement open-ended search,
program synthesis, LLM/scaffold generation, learned PyTorch policies, training-driven
updates, production filesystem realization, promotion, rollback, independent replay,
or external benchmark claims.

The generator remains untrusted. Phase 5A closure licenses Phase 5B open-ended
untrusted-generator development and Phase 6 selector/realizer/package-builder work;
it does not authorize candidate promotion.
