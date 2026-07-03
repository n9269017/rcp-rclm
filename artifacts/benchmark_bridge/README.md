# B9-Bridge Phase 3: Certificate-Preserving Benchmark Sidecar

This folder implements the first certificate-preserving benchmark bridge for the
RCP/RCLM artifact package.

It wraps a controlled local benchmark run with:

- before/after task scores;
- score deltas;
- learned-entry `LECert` status;
- closed-loop accepted/rejected successor trajectory evidence;
- checker pass/fail status;
- certificate-preservation booleans;
- hashes and reproducible run logs.

The executable shape is:

```text
BenchmarkRun_B(M_0,...,M_N) ⇓ (Score_{B,0},...,Score_{B,N})
∀ t<N, Check_RCP(PCS_t)=1
Score_B(M_N)-Score_B(M_0)=Δ_B
```

When `Δ_B > 0` and `certificate_preserved = true`, the result is a controlled
certificate-preserving local benchmark improvement for that finite run.

## What this is

This is a **local controlled mini benchmark sidecar**, beginning with:

```text
local-mini-terminal-v0
```

The mini benchmark is deterministic and auditable.  It scores a baseline system
`M_0` with ability `a0` against a successor `M_N` whose final ability set is read
from the generated closed-loop artifact.  Tasks are solved when the required
ability is present.

## What this is not

This is not:

- SWE-bench;
- RE-Bench;
- MLE-bench;
- Terminal-Bench;
- WebArena;
- frontier-scale validation;
- arbitrary trained-system entry;
- full autonomous RSI.

It is the controlled bridge needed before public benchmark sidecars.

## Files

```text
artifacts/benchmark_bridge/
  certified_benchmark_harness.py
  benchmark_sidecar_schema.py
  local_mini_tasks.py
  score_delta.py
  README.md
```

## Run a smoke test

From the repository root:

```powershell
python .\artifacts\benchmark_bridge\certified_benchmark_harness.py --modes rclm --N 5 --seeds 0
```

Expected: output contains `"ok": true`.

## Run RCP and RCLM examples

```powershell
python .\artifacts\benchmark_bridge\certified_benchmark_harness.py --modes rcp rclm --N 5 --seeds 0
```

Outputs are written to:

```text
artifacts/benchmark_bridge/results/
  certificate_preserving_benchmark_summary.json
  certificate_preserving_benchmark_detailed.json
  certificate_preserving_benchmark_results.csv
  rcp_N5_seed0_local-mini-terminal-v0/
  rclm_N5_seed0_local-mini-terminal-v0/
```

Each case folder contains:

```text
benchmark_sidecar.json
benchmark_scores.json
local_task_results.json
certificate_bundle.json
benchmark_runlog.json
hashes.json
```

## Example sidecar fields

```json
{
  "benchmark": "local-mini-terminal-v0",
  "benchmark_version": "0.1.0",
  "baseline_score": 0.2857142857142857,
  "successor_score": 0.6428571428571429,
  "delta": 0.3571428571428572,
  "certificate_preserved": true,
  "accepted_updates": 5,
  "all_pcs_checked": true,
  "runlog_hash": "...",
  "certificate_hash": "..."
}
```

## Claim boundary

A successful Phase-3 sidecar means:

```text
A controlled local benchmark score improved while the learned-entry certificate,
closed-loop replay, and checker evidence were preserved for the declared finite run.
```

It does **not** mean:

```text
public benchmark SOTA,
arbitrary trained-system entry,
frontier-scale validation,
or full autonomous RSI.
```
