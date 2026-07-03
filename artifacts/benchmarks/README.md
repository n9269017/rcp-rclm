# B9-Bridge Phase 1: Internal Closed-Loop RSI Benchmark Suite

This folder contains the first internal benchmark harness for the executable
RCP/RCLM instantiation package.

## Purpose

The B9-Bridge is the bridge from closed-loop certified successor generation to
benchmarkable learned-system evaluation. Phase 1 does **not** run public external
AI-agent benchmarks. It runs the existing finite closed-loop certified successor
generator across multiple horizons, seeds, and modes, then verifies every
generated artifact with the existing `checker.py` scripts.

The protocol shape this begins to instantiate is:

```text
LearnedEntryAudit_{0:N}(M_theta, D, L, C) => LECert_{0:N}
BenchmarkRun_B(M_0, ..., M_N) => (Score_{B,0}, ..., Score_{B,N})
forall t<N, Check_RCP(PCS_t)=1
```

Phase 1 covers the internal closed-loop certification benchmark portion. It does
not yet implement full learned-entry audit or external benchmark scoring.

## Files

```text
artifacts/benchmarks/
  rsi_benchmark_harness.py
  benchmark_schema.py
  score_utils.py
  README.md
```

The harness writes results to:

```text
artifacts/benchmarks/results/
  internal_closed_loop_benchmark_summary.json
  internal_closed_loop_benchmark_detailed.json
  internal_closed_loop_benchmark_results.csv
  runs/
    rcp_N2_seed0/
    rcp_N2_seed1/
    ...
    rclm_N10_seed2/
```

Each run folder contains the normal closed-loop outputs:

```text
generated_artifact.json
accepted_trajectory.json
rejected_candidates.json
closed_loop_runlog.json
hashes.json
```

## Run the default internal suite

From the repository root:

```powershell
python .\artifacts\benchmarks\rsi_benchmark_harness.py
```

Default grid:

```text
modes: rcp, rclm
N: 2, 3, 5, 10
seeds: 0, 1, 2
```

That produces 24 benchmark cases.

## Run a smaller smoke test

```powershell
python .\artifacts\benchmarks\rsi_benchmark_harness.py --modes rcp rclm --N 2 --seeds 0
```

## Run a custom grid

```powershell
python .\artifacts\benchmarks\rsi_benchmark_harness.py --modes rclm --N 5 10 --seeds 0 1 2 3
```

## What a pass means

A case passes only if:

- the closed-loop engine exits successfully;
- the existing mode-specific `checker.py` accepts the generated artifact;
- every accepted step is checked;
- residuals are nonpositive;
- strict ability expansion holds at each step;
- non-loss/recovery preservation holds at each step;
- goal-identity drift is zero;
- singleton reality containment holds;
- the run includes rejection evidence for invalid candidates;
- generated/accepted/rejected counts match the current candidate grammar.

## What this does not claim

This benchmark suite is **not**:

- a SWE-bench, RE-Bench, MLE-bench, Terminal-Bench, WebArena, or METR result;
- a B9 learned-entry FullPass;
- a public external benchmark pass;
- empirical deployment validation;
- full autonomous RSI.

It is the first internal RSI benchmark suite over the closed-loop certified
reference engine. The next phases are a learned-entry audit harness and a
certificate-preserving external benchmark sidecar.
