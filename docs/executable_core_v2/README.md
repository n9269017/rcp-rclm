# RCP/RCLM Executable Core v2

This directory records the theorem-to-runtime contract and the staged executable
implementation that follows the completed Formal Core v2 Lean project.

## Status

```text
Phase 0 theorem-to-runtime contract: complete and merged
Phase 1 deterministic runtime bedrock: complete and cross-platform validated
Pinned Lean compiler/verifier bridge: not implemented; licensed to begin
Production fail-closed successor checker: not implemented
Untrusted generator: not implemented
Promotion and rollback controller: not implemented
PyTorch proposal backend: not implemented
External benchmark adapter: not licensed
```

The frozen formal source is:

```text
Formal source commit: 012de4a55f326107f53f0e215c8aec62859d0bbf
Lean:                 leanprover/lean4:v4.31.0
mathlib:              fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
```

## Phase 0 contract documents

| Document | Frozen decision |
|---|---|
| `THEOREM_TO_RUNTIME_CONTRACT.md` | Overall refinement contract and phase ordering |
| `OBJECT_CORRESPONDENCE.md` | Lean declaration to schema, Python type, runtime function, evidence, and conformance test |
| `TRUST_BOUNDARY.md` | Trusted, trusted-after-validation, and untrusted components |
| `NUMERICAL_SEMANTICS.md` | Exact rational data, certified intervals, support rules, and comparison semantics |
| `CANONICAL_SERIALIZATION.md` | Canonical JSON profile, path rules, content hashes, tree hashes, and parent linkage |
| `ACCEPTANCE_SEMANTICS.md` | Fail-closed promotion predicate and reason-code requirements |
| `CLAIM_BOUNDARY.md` | What the first executable reference may and may not claim |
| `PYTORCH_ENTRY_CRITERIA.md` | Preconditions for adding a learned proposal backend |
| `PHASE_0_EXIT_CRITERIA.md` | Conditions for moving from contract work to runtime implementation |
| `PHASE_0_VALIDATION.md` | Clean Phase 0 CI and artifact record |

Machine-readable Phase 0 records remain at:

```text
python/rcp_rclm_executable_core_v2/contract/
```

The Phase 0 validator verifies the contract and formal pins. It is not the
production successor checker.

## Phase 1 runtime bedrock

| Document | Purpose |
|---|---|
| `PHASE_1_RUNTIME_BEDROCK.md` | Implemented records, exact mathematics, selected Gate B/C scope, serialization, hashing, and source guard |
| `PHASE_1_EXIT_CRITERIA.md` | Closed implementation, validation, and licensing criteria |
| `PHASE_1_VALIDATION.md` | Clean synchronized Linux, Windows, and macOS workflow and artifact record |

The package is:

```text
python/rcp_rclm_runtime_v2/
```

Phase 1 contains only:

```text
immutable records and strict parsers
exact rational arithmetic
certified rational logarithm intervals
Gate B finite classical mathematics
selected Gate C diagonal quantum mathematics
canonical JSON and path handling
content and tree hashing
RCLM-to-RCP forgetful mappings
generated-Lean source guard
```

The checker, compiler bridge, generator, successor controller, replay layer, and
PyTorch backend are intentionally absent rather than represented by empty files.

## Dependency order

```text
frozen Phase 0 contract
-> deterministic Phase 1 runtime bedrock
-> pinned Lean compiler/verifier bridge and differential conformance
-> fail-closed production checker
-> adversarial rejection suite
-> untrusted predecessor-driven generator
-> selector and successor realizer
-> atomic promotion and rollback controller
-> independent replay
-> optional PyTorch proposal backend
-> external benchmark adapters
```

The generator never certifies itself. Candidate assertions, model scores, native
floating-point diagnostics, and proposed certificate fields remain untrusted until
recomputed by the future checker and matched against the pinned Lean bridge.
