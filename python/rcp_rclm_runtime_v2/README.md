# RCP/RCLM Runtime v2

This package contains the deterministic Phase 1 runtime bedrock, the validated
Phase 2 pinned Lean conformance bridge, and the Phase 3 deterministic checker.

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

Run the checker from the repository root:

```bash
python -m pip install --no-deps -e python/rcp_rclm_runtime_v2
python scripts/check_candidate.py request.json --out checker_report.json
```

Run the Phase 3 unit suite with:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase3_tests.py \
  --package-root python/rcp_rclm_runtime_v2 \
  --out artifacts/runtime_v2_phase_3/local/phase_3_checker.log
```

## Boundary

The checker currently validates only the declared finite Gate B binary and
selected Gate C diagonal-quantum scopes. It does not implement arbitrary
noncommuting quantum objects, a generator, candidate realization, promotion,
rollback, independent replay, PyTorch integration, or an external benchmark
claim.

Even after Phase 3 CI is green, candidate promotion remains unlicensed until
the Phase 4 adversarial and tamper-rejection suite closes the checker attack
surface.
