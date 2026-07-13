# RCP/RCLM Executable Core v2 — Phase 0

This directory freezes the theorem-to-runtime refinement contract that must be
satisfied before any v2 Python checker, generator, promotion controller, learned
proposal backend, or benchmark adapter is treated as an implementation of Formal
Core v2.

## Status

```text
Phase 0 contract: implemented in this branch
Production v2 checker: not implemented
Production v2 generator: not implemented
Production v2 promotion loop: not implemented
PyTorch successor backend: not implemented
External benchmark adapter: not licensed
```

The active formal source is the merged Formal Core v2 project at commit:

```text
012de4a55f326107f53f0e215c8aec62859d0bbf
```

The selected Gate C validation record used by this contract is:

```text
validated branch head: 6cb17a7071ba56a17d5eeffb1ad8148ddf56ee3c
workflow run:          29249052337
artifact:              formal-core-v2-audit-29249052337-1
artifact SHA-256:      18b4593e544fa926af7fac20c5623850c929004d944f509d017dba04f6f7f2e5
```

## Contract documents

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
| `PHASE_0_EXIT_CRITERIA.md` | Conditions for moving from contract work to the runtime bedrock |

## Machine-readable contract

```text
python/rcp_rclm_executable_core_v2/contract/
  runtime_contract_manifest.json
  runtime_records.schema.json
  validate_runtime_contract.py
```

`validate_runtime_contract.py` is a Phase 0 contract verifier. It is not the v2
successor checker. It verifies the contract manifest, source pins, mapped Lean
declaration surfaces, canonical contract constraints, and the anti-placeholder
source gate.

## Dependency order after Phase 0

```text
frozen contract
→ immutable runtime records and exact numerical bedrock
→ Lean conformance bridge
→ fail-closed checker
→ adversarial rejection suite
→ untrusted predecessor-driven generator
→ selector and successor realizer
→ atomic promotion and rollback controller
→ independent replay
→ optional PyTorch proposal backend
→ external benchmark adapters
```

The generator never certifies itself. Candidate assertions and candidate-reported
scores remain untrusted inputs to the checker.
