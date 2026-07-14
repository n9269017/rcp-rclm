# RCP/RCLM Executable Core v2

This directory records the frozen theorem-to-runtime contract and the staged
executable implementation that follows the completed Formal Core v2 Lean project.

## Status

```text
Phase 0 theorem-to-runtime contract: complete and merged
Phase 1 deterministic runtime bedrock: complete and cross-platform validated
Phase 2 initial pinned Lean conformance bridge: complete and validated
Phase 3 deterministic fail-closed checker: implementation complete; CI and Phase 4 closure pending
Mature canonical-packet Lean executable: not implemented
Adversarial checker closure: next phase
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
| `PHASE_2_EXIT_CRITERIA.md` | Closed Phase 2 implementation and licensing criteria |
| `PHASE_2_VALIDATION.md` | Pinned Lean run, ten-case differential suite, and artifact digests |

Machine-readable Phase 2 records are:

```text
python/rcp_rclm_runtime_v2/phase_2_manifest.json
python/rcp_rclm_runtime_v2/phase_2_validation.json
```

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
→ exact formal-source and toolchain pin verification
→ pinned Lean compilation
→ structured RCP/RCLM verdict parsing
→ differential comparison
→ preserved evidence
```

The clean implementation validation covered ten cases: four accepted
improvement/stability packets and six rejected wrong-successor,
wrong-certificate, or malformed-certificate mutations across Gate B and the
selected Gate C scope.

## Phase 3 deterministic checker

| Document | Purpose |
|---|---|
| `PHASE_3_CHECKER.md` | Pure checker architecture, recomputed obligations, structured report, and claim boundary |
| `PHASE_3_EXIT_CRITERIA.md` | Exact CI and licensing conditions for Phase 4 entry |

Machine-readable Phase 3 records are:

```text
python/rcp_rclm_executable_core_v2/contract/phase_3_checker.schema.json
python/rcp_rclm_runtime_v2/phase_3_manifest.json
```

The checker package is:

```text
python/rcp_rclm_runtime_v2/rcp_rclm_runtime/checker/
```

The checker performs:

```text
strict immutable request parsing
→ exact RCLM canonical-lift validation
→ typed-successor and residual recomputation
→ entropy and KL/QRE interval recomputation
→ non-loss, recovery, invariant, containment, progress, trust, resource, and domain checks
→ RCLM-to-RCP refinement and monitor checks
→ exact packet binding to the Phase 2 Lean report
→ structured verdict and computed artifact hashes
```

The generator, selector, realizer, promotion controller, replay layer, and
PyTorch backend remain absent rather than represented by empty modules.

## Dependency order

```text
frozen Phase 0 contract
→ deterministic Phase 1 runtime bedrock
→ completed Phase 2 pinned Lean bridge and differential conformance
→ Phase 3 fail-closed deterministic checker
→ Phase 4 adversarial rejection suite
→ untrusted predecessor-driven generator
→ selector and successor realizer
→ atomic promotion and rollback controller
→ independent replay
→ optional PyTorch proposal backend
→ external benchmark adapters
```

The generator never certifies itself. Candidate assertions, model scores, native
floating-point diagnostics, and proposed certificate fields remain untrusted.
The checker recomputes authoritative facts and requires packet-bound agreement
with the pinned Lean bridge.
