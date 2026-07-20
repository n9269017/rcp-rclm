# RCP/RCLM Runtime v3

This package implements the executable correspondence for Formal Core v3 Gate D and the
first canonical substrate for a real compact language model.

## Phase 9 contract

The Phase 9 layer provides immutable Python records and deterministic validation for:

- the selected compact decoder-only transformer package identity;
- the selected Lean theorem-completion task class;
- model, tokenizer, training, optimizer, generator, planner, retrieval, memory, tool,
  verification, resource, and self-model bindings;
- finite certified capability frontiers and task ledgers;
- typed substantive update operations;
- held-out task and reference-answer isolation;
- learned certificate evidence hashes;
- active-generator and proposal-protocol self-hosting bindings;
- exact frontier retention and strict expansion.

## Phase 10A substrate

`rcp_rclm_runtime_v3.phase10` adds:

```text
fixed 13.2M decoder-only transformer architecture
fixed 260-token UTF-8 byte tokenizer
canonical int16 tensor specifications and raw-file hashes
complete model package manifests
Phase 9 ModelIdentity reconstruction
rank-8 zero-output LoRA extension
exact recovery to the predecessor identity
fail-closed package and extension validation
deterministic reference-package construction
```

The trusted Runtime v3 package imports no PyTorch, NumPy, random-number backend, or
native floating-point acceptance source. Model binaries are generated in temporary
validation workspaces and are not committed.

## Build and test

Install Runtime v2 and Runtime v3:

```bash
python -m pip install --no-deps -e python/rcp_rclm_runtime_v2
python -m pip install -e "python/rcp_rclm_runtime_v3[test]"
```

Run the focused suites and reference:

```bash
python python/rcp_rclm_runtime_v3/tools/run_phase9_tests.py \
  --package-root python/rcp_rclm_runtime_v3 \
  --out artifacts/runtime_v3_phase_9/tests.log

python python/rcp_rclm_runtime_v3/tools/run_phase10_tests.py \
  --package-root python/rcp_rclm_runtime_v3 \
  --out artifacts/runtime_v3_phase_10/tests.log

python python/rcp_rclm_runtime_v3/tools/validate_phase10_schema.py \
  --schema python/rcp_rclm_executable_core_v3/contract/phase_10_substrate.schema.json \
  --out artifacts/runtime_v3_phase_10/schema.json

python python/rcp_rclm_runtime_v3/tools/run_phase10_reference.py \
  --out artifacts/runtime_v3_phase_10/reference.json

python python/rcp_rclm_runtime_v3/tools/validate_phase10_manifest.py \
  --repo-root . \
  --out artifacts/runtime_v3_phase_10/manifest.json
```

## Claim boundary

The package does not yet establish a trained compact language model, deterministic
authoritative inference, a newly certified Lean task, KL/QRE evidence, promotion,
independent replay, self-hosted recursion, or autonomous/unbounded RSI. Those remain the
open Phase 10 and later-phase obligations.
