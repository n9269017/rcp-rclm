# RCP/RCLM Executable Core v2

This directory records the frozen theorem-to-runtime contract and the staged
executable implementation that follows the completed Formal Core v2 Lean project.

## Status

```text
Phase 0 theorem-to-runtime contract: complete and merged
Phase 1 deterministic runtime bedrock: complete and cross-platform validated
Phase 2 initial pinned Lean conformance bridge: implemented; clean CI pending
Mature canonical-packet Lean executable: not implemented
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

## Phase 1 runtime bedrock

| Document | Purpose |
|---|---|
| `PHASE_1_RUNTIME_BEDROCK.md` | Records, exact mathematics, selected Gate B/C scope, serialization, hashing, and source guard |
| `PHASE_1_EXIT_CRITERIA.md` | Closed implementation, validation, and licensing criteria |
| `PHASE_1_VALIDATION.md` | Synchronized Linux, Windows, and macOS workflow and artifact record |

## Phase 2 Lean conformance bridge

| Document | Purpose |
|---|---|
| `PHASE_2_LEAN_CONFORMANCE_BRIDGE.md` | Initial generated-source bridge, trust boundary, evidence, and differential claim |
| `PHASE_2_EXIT_CRITERIA.md` | Conditions required before Phase 2 can close |

The bridge package is:

```text
python/rcp_rclm_runtime_v2/rcp_rclm_runtime/lean_bridge/
```

The initial bridge performs:

```text
canonical reference packet
→ independent Python interpretation
→ deterministic Lean source generation
→ mandatory source guard
→ exact pin verification
→ pinned Lean compilation
→ structured RCP/RCLM verdict parsing
→ differential comparison
→ preserved evidence
```

The checker, generator, successor controller, replay layer, and PyTorch backend remain
absent rather than represented by empty modules.

## Dependency order

```text
frozen Phase 0 contract
→ deterministic Phase 1 runtime bedrock
→ Phase 2 pinned Lean bridge and differential conformance
→ fail-closed production checker
→ adversarial rejection suite
→ untrusted predecessor-driven generator
→ selector and successor realizer
→ atomic promotion and rollback controller
→ independent replay
→ optional PyTorch proposal backend
→ external benchmark adapters
```

The generator never certifies itself. Candidate assertions, model scores, native
floating-point diagnostics, and proposed certificate fields remain untrusted until
recomputed by the future checker and matched against the pinned Lean bridge.
