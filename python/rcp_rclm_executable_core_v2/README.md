# RCP/RCLM Executable Core v2

This package root is reserved for the theorem-to-runtime implementation that follows
Formal Core v2.

## Current status

```text
Phase 0 contract artifacts: present
Phase 0 contract validator: present
Production immutable runtime records: not implemented
Production exact numerical engine: not implemented
Lean conformance bridge: not implemented
Production checker: not implemented
Generator: not implemented
Promotion controller: not implemented
PyTorch backend: not implemented
```

The only Python executable in this phase is:

```text
contract/validate_runtime_contract.py
```

It verifies the frozen contract and may scan generated Lean source for forbidden
proof placeholders before a later Lean invocation. It is not the successor checker.

## Validate Phase 0

From the repository root:

```bash
python3 python/rcp_rclm_executable_core_v2/contract/validate_runtime_contract.py \
  --repo-root . \
  --out artifacts/executable_core_v2_contract/validation_report.json
```

To scan a generated Lean certificate file before compilation:

```bash
python3 python/rcp_rclm_executable_core_v2/contract/validate_runtime_contract.py \
  --repo-root . \
  --scan-lean path/to/generated_certificate.lean
```

The scanner rejects:

```text
sorry
sorryAx
admit
project-local axiom declarations in generated certificate source
```

A clean scan does not replace Lean elaboration.

## Planned Phase 1 package structure

```text
rcp_rclm_runtime/
  schema/
  canonical/
  mathematics/
  refinement/
  lean_bridge/
  checker/
  generator/
  successor/
  promotion/
  provenance/
  replay/
  torch_backend/
```

Those modules are names reserved by the Phase 0 contract. They are not licensed for
production claims until their own phase exit criteria pass.
