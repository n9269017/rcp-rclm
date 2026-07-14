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
Phase 5A deterministic bounded reference generator: implementation and validation in progress
Phase 5B open-ended untrusted generators: not implemented
Phase 6 realizer and package builder: not implemented
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
| `PHASE_0_EXIT_CRITERIA.md` | Phase 0 closure conditions |
| `PHASE_0_VALIDATION.md` | Clean Phase 0 CI and artifacts |

Machine-readable records remain under:

```text
python/rcp_rclm_executable_core_v2/contract/
```

## Phase 1 runtime bedrock

| Document | Purpose |
|---|---|
| `PHASE_1_RUNTIME_BEDROCK.md` | Records, exact mathematics, serialization, hashing, and source guard |
| `PHASE_1_EXIT_CRITERIA.md` | Closed implementation and licensing criteria |
| `PHASE_1_VALIDATION.md` | Linux, Windows, and macOS validation evidence |

## Phase 2 Lean conformance bridge

| Document | Purpose |
|---|---|
| `PHASE_2_LEAN_CONFORMANCE_BRIDGE.md` | Generated-source bridge, evidence, and differential claim |
| `PHASE_2_EXIT_CRITERIA.md` | Closed bridge criteria |
| `PHASE_2_VALIDATION.md` | Pinned Lean run and ten-case differential evidence |

The bridge performs:

```text
canonical reference packet
→ independent Python interpretation
→ deterministic Lean source generation
→ mandatory pre-compilation source guard
→ exact formal-source and toolchain pin verification
→ pinned Lean compilation
→ structured RCP/RCLM verdict parsing
→ differential comparison and preserved evidence
```

## Phase 3 deterministic checker

| Document | Purpose |
|---|---|
| `PHASE_3_CHECKER.md` | Pure checker architecture, recomputed obligations, and report |
| `PHASE_3_EXIT_CRITERIA.md` | Checker validation and Phase 4 entry criteria |

The checker performs:

```text
strict immutable request parsing
→ exact RCLM canonical-lift validation
→ typed successor and residual recomputation
→ entropy and KL/QRE interval recomputation
→ non-loss, recovery, invariant, containment, progress, trust, resource, and domain checks
→ RCLM-to-RCP refinement and monitor checks
→ packet binding to the Phase 2 Lean report
→ structured verdict and artifact hashes
```

## Phase 4 adversarial rejection

| Document | Purpose |
|---|---|
| `PHASE_4_ADVERSARIAL_REJECTION.md` | Hardened integrity envelope and attack matrix |
| `PHASE_4_EXIT_CRITERIA.md` | Rejection, replay, tamper, and licensing criteria |
| `PHASE_4_VALIDATION.md` | Clean implementation head, workflows, and artifact digests |

Phase 4 performs:

```text
Phase 3 checker request
→ parent, file-tree, candidate, certificate, trust, resource, policy, and manifest binding
→ deterministic malformed/tamper/replay/numeric/domain/source attacks
→ two independent observations per attack
→ first-class attack results
→ pinned Lean build and generated-source hygiene revalidation
```

## Phase 5A deterministic reference generator

| Document | Purpose |
|---|---|
| `PHASE_5A_REFERENCE_GENERATOR.md` | Bounded Lean grammar mapping, process boundary, and end-to-end path |
| `PHASE_5A_EXIT_CRITERIA.md` | Exact replay, isolation, Lean, checker, and licensing conditions |
| `PHASE_5B_ENTRY_CRITERIA.md` | Preconditions for open-ended untrusted proposal backends |

Machine-readable Phase 5A records are:

```text
python/rcp_rclm_executable_core_v2/contract/phase_5a_reference_generator.schema.json
python/rcp_rclm_runtime_v2/phase_5a_manifest.json
```

The Phase 5A path is:

```text
canonical predecessor view, public policy, objective, and budget
→ separate capability-minimized generator process
→ bounded word/witness/proposal only
→ independent proposal validation
→ host-owned certificate construction
→ deterministic single-proposal selection
→ successor derivation from the selected update
→ pinned Lean verification
→ Phase 4 hardened checker
→ structured end-to-end report
```

The worker never receives checker source, trust-anchor contents, promotion-ledger
write access, previous-manifest write access, or reference answers. It never emits a
certificate, candidate successor, or acceptance Boolean.

Phase 5A implements the formal Gate B bounded seed grammar only. Selected Gate C
remains checker-supported, but no separate bounded quantum seed grammar is claimed.

## Dependency order

```text
frozen Phase 0 contract
→ deterministic Phase 1 runtime bedrock
→ Phase 2 pinned Lean bridge and differential conformance
→ Phase 3 fail-closed checker
→ Phase 4 adversarial rejection
→ Phase 5A bounded untrusted reference generator
→ Phase 5B optional open-ended untrusted generators
→ Phase 6 selector, realizer, and package builder
→ atomic promotion and rollback controller
→ independent replay
→ optional PyTorch proposal backend
→ external benchmark adapters
```

The generator never certifies itself. Candidate assertions, model scores, native
floating-point diagnostics, and proposed certificate fields remain untrusted. The
checker owns acceptance and requires packet-bound agreement with the pinned Lean
bridge.
