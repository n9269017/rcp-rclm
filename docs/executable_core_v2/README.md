# RCP/RCLM Executable Core v2

This directory records the frozen theorem-to-runtime contract and the staged
executable implementation following the completed Formal Core v2 Lean project.

## Status

```text
Phase 0 theorem-to-runtime contract: complete and merged
Phase 1 deterministic runtime bedrock: complete and cross-platform validated
Phase 2 initial pinned Lean conformance bridge: complete and validated
Phase 3 deterministic fail-closed checker: complete and cross-platform validated
Phase 4 adversarial and tamper rejection: complete and cross-platform validated
Phase 5A deterministic bounded reference generator: complete and cross-platform validated
Phase 5B open-ended untrusted generators: optional and not implemented
Phase 6 selector, realizer, and package builder: implementation complete; validation pending
Promotion and rollback controller: not implemented
Independent replay: not implemented
PyTorch proposal backend: not implemented
External benchmark adapter: not licensed
```

The frozen formal source is:

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
| `PYTORCH_ENTRY_CRITERIA.md` | Preconditions for a learned proposal backend |

## Phases 1–4

The first four runtime phases provide immutable exact records, selected Gate B/Gate C
mathematics, the pinned Lean conformance bridge, the pure fail-closed checker, and the
hardened 27-case adversarial rejection boundary. Their detailed architecture,
validation, and exit-criteria records remain in this directory.

## Phase 5A deterministic reference generator

| Document | Purpose |
|---|---|
| `PHASE_5A_REFERENCE_GENERATOR.md` | Bounded Lean grammar mapping, process boundary, and end-to-end path |
| `PHASE_5A_EXIT_CRITERIA.md` | Exact replay, isolation, Lean, checker, and licensing conditions |
| `PHASE_5A_VALIDATION.md` | Cross-platform process, pinned Lean, hardened-checker, and artifact evidence |
| `PHASE_5B_ENTRY_CRITERIA.md` | Preconditions for optional open-ended proposal backends |

The Phase 5A worker emits only an untrusted bounded proposal. It cannot emit a
certificate, candidate successor, checker verdict, or acceptance Boolean.

## Phase 6 selector, realizer, and package builder

| Document | Purpose |
|---|---|
| `PHASE_6_SELECTOR_REALIZER_PACKAGE_BUILDER.md` | Filesystem measurement, selection, realization, rollback, packaging, and verification |
| `PHASE_6_EXIT_CRITERIA.md` | Exact substantive-change, rollback, package, CI, and licensing conditions |

Machine-readable Phase 6 records are:

```text
python/rcp_rclm_executable_core_v2/contract/phase_6_successor_package.schema.json
python/rcp_rclm_runtime_v2/phase_6_manifest.json
```

The Phase 6 package is:

```text
python/rcp_rclm_runtime_v2/rcp_rclm_runtime/successor/
```

Its path is:

```text
actual predecessor package bytes
→ strict proposal/predecessor selection
→ isolated payload copy
→ explicit selected file operations
→ complete candidate-tree measurement
→ before/after and semantic change ledger
→ substantive-component enforcement
→ command/environment/resource evidence
→ deterministic rollback archive and fresh restoration
→ immutable candidate package
→ public package verification
→ atomic publication as realized_unverified
```

A generator never receives candidate-workspace or package write authority. Merely
changing a state index, name, version, timestamp, schema, or manifest field is not a
substantive successor.

## Dependency order

```text
frozen Phase 0 contract
→ deterministic Phase 1 runtime bedrock
→ Phase 2 pinned Lean bridge and differential conformance
→ Phase 3 fail-closed checker
→ Phase 4 adversarial rejection
→ Phase 5A bounded untrusted reference generator
→ Phase 6 selector, filesystem realizer, rollback, and package builder
→ Phase 7 atomic promotion and rollback controller
→ Phase 8 independent replay
→ optional Phase 5B/PyTorch open-ended proposal backends after containment closure
→ external benchmark adapters
```

Phase 5B proposal interfaces may be developed independently, but an arbitrary
open-ended backend must not enter the controller before the stronger Phase 6–8
sandbox, promotion, and replay boundaries exist.

The generator never certifies itself. Candidate assertions, model scores, native
floating-point diagnostics, and proposed certificate fields remain untrusted. The
checker owns acceptance and requires packet-bound agreement with the pinned Lean
bridge. Phase 6 builds candidates but never promotes them.
