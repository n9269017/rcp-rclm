# RCP/RCLM Runtime v2

This package contains the completed deterministic Phase 1 runtime bedrock and the
Phase 2 initial pinned Lean conformance bridge.

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

Implemented in this branch:

- a closed immutable Gate B/Gate C reference-packet grammar;
- deterministic Python interpretation for ten accept/reject cases;
- deterministic generated Lean certificate source;
- mandatory pre-compilation rejection of admitted-proof tokens and local axioms;
- verification of the frozen formal-source Git commit and the exact Lean/mathlib pins;
- pinned `lake env lean` invocation;
- raw stdout, stderr, exit-code, timeout, source, and toolchain evidence;
- canonical structured Lean verdict parsing with independent RCP and RCLM fields;
- fail-closed Python/Lean differential comparison;
- preservation of generated source and every per-case report.

Run the Phase 2 reference suite from the repository root with:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase2_conformance.py \
  --repo-root . \
  --outdir artifacts/runtime_v2_phase_2/local
```

The Formal Core project must already have its pinned dependency graph resolved.
The authoritative validation is the GitHub Actions workflow
`.github/workflows/runtime-v2-phase-2.yml`.

## Boundary

The bridge validates only the declared finite Gate B binary and selected Gate C
diagonal-quantum reference and mutation cases. It is not the production successor
checker and does not authorize candidate promotion.

Not implemented or licensed here:

- a mature Lean executable that parses canonical packets directly;
- the production aggregate checker;
- an untrusted generator;
- successor selection or realization;
- promotion, rollback, or independent replay;
- a PyTorch proposal backend;
- external benchmark adapters;
- arbitrary noncommuting quantum semantics.
