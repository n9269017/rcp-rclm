# CRSI-RE/METR Bridge: Certificate-preserving external AI-R&D benchmark adapter

This folder begins the next phase after the recorded CRSI-Core witness:

```text
CRSI-External Bridge
  -> CRSI-RE/METR Bridge
  -> certificate-preserving external AI-R&D benchmark adapter
```

The bridge does **not** replace the CRSI-Core result. It consumes a recorded
CRSI-Core chain and attaches an external AI-R&D benchmark score ledger while
checking that the RCP/RCLM certificates, protected non-loss invariants, hash
chain, and no-oracle/no-leakage conditions remain intact.

## Why this phase exists

The CRSI-Core phase answers:

```text
Can the instantiated architecture execute a finite certified recursive successor
chain under its own protected internal CoreScore functional?
```

The external bridge asks the next question:

```text
Can that same certified successor chain carry an external AI-R&D task score
ledger without breaking certificates, non-loss constraints, or no-oracle/no-leakage
requirements?
```

The intended external substrate is RE-Bench / METR-style AI R&D or research
engineering evaluation. The bridge is benchmark-family compatible: it can wrap
RE-Bench-like, METR-like, MLE-style, SWE-style, or custom held-out score ledgers
as long as the required task manifest and score ledger are supplied.

## Claim boundary

A bridge run can claim only what its inputs support.

The built-in smoke fixture can claim:

```text
The CRSI external bridge adapter can bind a score ledger to a CRSI-Core chain,
verify hashes, verify no-leakage/no-oracle flags, verify certificate preservation,
and verify monotone successor scores under the bridge schema.
```

It cannot claim:

```text
official RE-Bench result
official METR result
external public benchmark result
frontier-scale validation
full autonomous RSI
unbounded-horizon empirical proof
```

A real external benchmark bridge claim requires official or declared external
benchmark artifacts: task manifest, scorer/evaluator artifact, score ledger,
run logs, and no-leakage/no-oracle declarations.

## Files

```text
artifacts/crsi_external_bridge/
  external_bridge_schema.py       # schema, hashing, score, and invariant utilities
  crsi_external_bridge_harness.py # bridge builder / adapter harness
  reproduce_external_bridge.py    # offline sidecar reproduction checker
  README.md
```

Generated outputs are written to:

```text
artifacts/crsi_external_bridge/results/
```

and are ignored by default until explicitly recorded.

## Smoke-test the adapter

After the CRSI-Core k5 result is present on `main`, run:

```powershell
python .\artifacts\crsi_external_bridge\crsi_external_bridge_harness.py `
  --crsi-chain-summary .\artifacts\crsi_core\results\rclm_crsi_core_k5_baseN2_seed0\rclm_crsi_core_chain_summary.json `
  --make-smoke-fixture `
  --benchmark-id re_metr_bridge_smoke `
  --outdir .\artifacts\crsi_external_bridge\results\smoke_k5_seed0
```

Then reproduce the sidecar offline:

```powershell
python .\artifacts\crsi_external_bridge\reproduce_external_bridge.py `
  .\artifacts\crsi_external_bridge\results\smoke_k5_seed0\crsi_external_bridge_sidecar.json
```

Expected output:

```json
{
  "ok": true,
  "errors": []
}
```

The smoke fixture is intentionally synthetic and marked as `adapter_smoke_test_only`.
It is not an external benchmark score.

## Real external benchmark mode

For a real RE/METR-style adapter run, provide three externally meaningful inputs:

```text
1. CRSI-Core chain summary
2. task manifest
3. external score ledger
```

Example shape:

```powershell
python .\artifacts\crsi_external_bridge\crsi_external_bridge_harness.py `
  --crsi-chain-summary .\artifacts\crsi_core\results\rclm_crsi_core_k5_baseN2_seed0\rclm_crsi_core_chain_summary.json `
  --task-manifest .\path\to\re_metr_task_manifest.json `
  --score-ledger .\path\to\re_metr_score_ledger.json `
  --scorer-artifact .\path\to\official_or_declared_scorer_artifact.json `
  --benchmark-id re_bench_v1_or_declared_re_metr_suite `
  --benchmark-kind re_metr_external_ai_rd_adapter `
  --public-benchmark `
  --outdir .\artifacts\crsi_external_bridge\results\re_metr_declared_run
```

Use `--official-re-bench` or `--official-metr` only when the supplied artifacts
really are official/accepted outputs from that benchmark/evaluator. Otherwise,
leave those flags off.

## Task manifest schema

Minimum shape:

```json
{
  "schema_version": "crsi-external-bridge-v1",
  "benchmark_id": "re_bench_v1_or_declared_suite",
  "benchmark_kind": "re_metr_external_ai_rd_adapter",
  "task_count": 2,
  "tasks": [
    {"task_id": "task/0", "description": "..."},
    {"task_id": "task/1", "description": "..."}
  ],
  "benchmark_answers_in_prompt": false,
  "hidden_tests_exposed": false,
  "private_solution_material_used": false,
  "diagnostic_oracle": false,
  "manual_repair_inside_chain": false,
  "human_patch_inside_chain": false
}
```

## Score ledger schema

Minimum shape:

```json
{
  "schema_version": "crsi-external-bridge-v1",
  "benchmark_id": "re_bench_v1_or_declared_suite",
  "benchmark_kind": "re_metr_external_ai_rd_adapter",
  "scores": [
    {"package_index": 0, "successor_id": "RCLM_0_...", "score": 0.10},
    {"package_index": 1, "successor_id": "RCLM_1_...", "score": 0.15},
    {"package_index": 2, "successor_id": "RCLM_2_...", "score": 0.18}
  ],
  "benchmark_answers_in_prompt": false,
  "hidden_tests_exposed": false,
  "private_solution_material_used": false,
  "diagnostic_oracle": false,
  "manual_repair_inside_chain": false,
  "human_patch_inside_chain": false
}
```

The score ledger must match the CRSI chain's successor IDs in order.

## Bridge pass/fail standard

A bridge sidecar passes only if:

```text
CRSI-Core chain is ok
CRSI-Core reproduction checker passes
RCP/RCLM certificates are preserved across the chain
protected non-loss invariants are preserved across the chain
CRSI hash chain remains valid
task manifest hash is logged
external score ledger hash is logged
scorer artifact is hash-logged or explicitly absent
no benchmark leakage flags are set
no oracle flags are set
no manual repair flags are set
score entries match CRSI successor IDs
external scores are monotone non-decreasing
external scores strictly improve, unless --allow-nonregression is used
```

## Phase relationship

```text
CRSI-Core k3/k5:
  finite executable recursive successor-improvement witness

CRSI-RE/METR Bridge:
  external AI-R&D score ledger attached to that witness without breaking certificates

Future phase:
  official RE-Bench / METR / hidden-eval run, independent reproduction, signed logs
```
