# Phase 4C-E: Official EvalPlus Artifact Wrapper

This phase converts the project from a **direct Docker-free EvalPlus/HumanEval sidecar** to a wrapper for **official EvalPlus CLI evaluation artifacts**.

It does not fake a leaderboard result.

The intended status ladder is:

1. Direct sidecar full pass: already achieved in Phase 4C-D2e.
2. Official EvalPlus CLI artifact: produced by running `evalplus.evaluate`.
3. Certificate sidecar over the official artifact: produced by `wrap_official_evalplus_results.py`.
4. Leaderboard-style claim: only when the official full-suite EvalPlus artifact is available and the sidecar marks the result as full-suite/non-mini/official-CLI.
5. Actual public leaderboard listing: only if submitted/recognized externally; this repository wrapper alone does not create an external leaderboard listing.

## Files

```text
artifacts/evalplus_official/
  build_official_evalplus_samples.py
  run_evalplus_official.py
  wrap_official_evalplus_results.py
  official_evalplus_sidecar_schema.py
  parse_evalplus_outputs.py
  PHASE_4C_E_OFFICIAL_EVALPLUS_README.md
  samples/
  results/
  manifests/
```

## Step 1 — Build official EvalPlus sample files

From repo root:

```powershell
python .\artifacts\evalplus_official\build_official_evalplus_samples.py `
  --dataset humaneval `
  --successor-source .\artifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_164.jsonl `
  --task-list .\artifacts\evalplus_leaderboard\tasks\humaneval\humaneval_task_ids_164.txt
```

This writes:

```text
artifacts/evalplus_official/samples/humaneval_164_baseline_empty.jsonl
artifacts/evalplus_official/samples/humaneval_164_successor.jsonl
```

## Step 2 — Run official EvalPlus CLI, canonical/base HumanEval

EvalPlus official CLI supports `--base-only` for original HumanEval base tests.

```powershell
python .\artifacts\evalplus_official\run_evalplus_official.py `
  --dataset humaneval `
  --samples .\artifacts\evalplus_official\samples\humaneval_164_baseline_empty.jsonl `
  --label humaneval164_baseline_baseonly `
  --base-only
```

```powershell
python .\artifacts\evalplus_official\run_evalplus_official.py `
  --dataset humaneval `
  --samples .\artifacts\evalplus_official\samples\humaneval_164_successor.jsonl `
  --label humaneval164_successor_baseonly `
  --base-only
```

Then wrap the base-only result:

```powershell
python .\artifacts\evalplus_official\wrap_official_evalplus_results.py `
  --dataset humaneval `
  --mode rclm `
  --N 5 `
  --seed 0 `
  --label humaneval164_official_baseonly `
  --score-kind base `
  --baseline-run .\artifacts\evalplus_official\results\humaneval164_baseline_baseonly\official_evalplus_runlog.json `
  --successor-run .\artifacts\evalplus_official\results\humaneval164_successor_baseonly\official_evalplus_runlog.json `
  --direct-sidecar .\artifacts\evalplus_leaderboard\results\rclm_N5_seed0_humaneval_164tasks_baseonly\leaderboard_prep_sidecar.json
```

## Step 3 — Run official EvalPlus CLI, HumanEval+ full suite

For a leaderboard-style local artifact, use the official CLI without `--mini`.

```powershell
python .\artifacts\evalplus_official\run_evalplus_official.py `
  --dataset humaneval `
  --samples .\artifacts\evalplus_official\samples\humaneval_164_baseline_empty.jsonl `
  --label humaneval164_baseline_evalplus_full
```

```powershell
python .\artifacts\evalplus_official\run_evalplus_official.py `
  --dataset humaneval `
  --samples .\artifacts\evalplus_official\samples\humaneval_164_successor.jsonl `
  --label humaneval164_successor_evalplus_full
```

Wrap the full EvalPlus result:

```powershell
python .\artifacts\evalplus_official\wrap_official_evalplus_results.py `
  --dataset humaneval `
  --mode rclm `
  --N 5 `
  --seed 0 `
  --label humaneval164_official_evalplus_full `
  --score-kind plus `
  --baseline-run .\artifacts\evalplus_official\results\humaneval164_baseline_evalplus_full\official_evalplus_runlog.json `
  --successor-run .\artifacts\evalplus_official\results\humaneval164_successor_evalplus_full\official_evalplus_runlog.json `
  --direct-sidecar .\artifacts\evalplus_leaderboard\results\rclm_N5_seed0_humaneval_164tasks\leaderboard_prep_sidecar.json `
  --full-suite `
  --leaderboard-eligible-candidate
```

## If EvalPlus output parsing fails

The wrapper is deliberately strict. If the official CLI output changes and pass@1 cannot be parsed, pass explicit scores after manually inspecting the official EvalPlus stdout/cache artifact:

```powershell
python .\artifacts\evalplus_official\wrap_official_evalplus_results.py `
  --dataset humaneval `
  --mode rclm `
  --N 5 `
  --seed 0 `
  --label humaneval164_official_evalplus_full `
  --score-kind plus `
  --baseline-score 0.0 `
  --successor-score 1.0 `
  --baseline-run .\artifacts\evalplus_official\results\humaneval164_baseline_evalplus_full\official_evalplus_runlog.json `
  --successor-run .\artifacts\evalplus_official\results\humaneval164_successor_evalplus_full\official_evalplus_runlog.json `
  --direct-sidecar .\artifacts\evalplus_leaderboard\results\rclm_N5_seed0_humaneval_164tasks\leaderboard_prep_sidecar.json `
  --full-suite `
  --leaderboard-eligible-candidate
```

Only use explicit scores when they exactly match the official EvalPlus output/cache.

## Claim boundary

A successful Phase 4C-E official CLI wrapper can support:

```text
Official EvalPlus CLI artifact wrapped with RCP/RCLM certificate sidecar.
```

It does not by itself support:

```text
External EvalPlus public leaderboard listing.
SWE-bench result.
Terminal-Bench / RE-Bench / MLE-Bench / WebArena result.
Full autonomous RSI.
```
