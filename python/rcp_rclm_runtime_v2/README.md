# RCP/RCLM Runtime v2 — Phase 1 bedrock

This package implements the deterministic runtime bedrock licensed by the frozen
Executable Core v2 Phase 0 theorem-to-runtime contract.

Implemented in this phase:

- immutable runtime records and strict parsers;
- reduced exact rational arithmetic;
- closed rational intervals and certified logarithm enclosures;
- Gate B finite-distribution, Shannon-entropy, support-aware KL, zero-extension,
  and exact-recovery operations;
- selected Gate C two-level diagonal-density, spectral entropy, diagonal QRE,
  identity/swap channel, and exact selected-recovery operations;
- canonical JSON, semantic path validation, content hashing, and tree hashing;
- RCLM-to-RCP forgetful record mappings;
- generated-Lean source guarding before any compiler invocation.

Not implemented or licensed here:

- the production aggregate checker;
- a Lean compiler/verifier bridge;
- a generator;
- successor promotion or rollback control;
- a PyTorch proposal backend;
- external benchmark adapters.

The selected quantum implementation is intentionally limited to the completed
commuting/diagonal two-level reference. A probability spectrum is the source of
truth. Arbitrary noncommuting matrices, general CPTP channels, matrix-log QRE,
data-processing claims, and Petz recovery remain outside scope.
