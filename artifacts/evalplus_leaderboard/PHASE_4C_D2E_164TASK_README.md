# Phase 4C-D2e — Final HumanEval/144--163 expansion to 164 tasks

This phase builds the final `successor_samples_non_oracle_HumanEval_164.jsonl`
from the already-passed 144-task file plus the final HumanEval/144--163 block.

## Canonical status

The repository's `--dataset humaneval` path uses canonical HumanEval task IDs:
`HumanEval/0` through `HumanEval/163`.

Two different evaluation modes should be kept separate:

1. **Canonical/base HumanEval direct sidecar**: run with `--base-only`.
   This checks the base HumanEval input set in the Docker-free direct sidecar.

2. **EvalPlus/HumanEval+ direct sidecar**: run with `--mini`.
   This keeps the same HumanEval task IDs but includes bounded plus-input testing
   in the local sidecar. It is stricter than base-only but is still not an
   official EvalPlus leaderboard result.

## Official wrapper status

This phase is not the official EvalPlus CLI / leaderboard wrapper.
It produces a certificate-preserving direct sidecar. Official EvalPlus artifacts
can be wrapped later with `wrap_official_evalplus_results.py` after running the
official EvalPlus evaluator.

## Build

```powershell
python .\artifacts\evalplus_leaderboard\make_humaneval_164_samples.py
```

## Validate

```powershell
python .\artifacts\evalplus_leaderboard\validate_evalplus_samples.py `
  --dataset humaneval `
  --samples .\artifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_164.jsonl `
  --task-list .\artifacts\evalplus_leaderboard\tasks\humaneval\humaneval_task_ids_164.txt
```

## Canonical/base-only 164-task sidecar

```powershell
python .\artifacts\evalplus_leaderboard\certified_evalplus_suite_harness.py `
  --dataset humaneval `
  --mode rclm `
  --N 5 `
  --seed 0 `
  --task-list .\artifacts\evalplus_leaderboard\tasks\humaneval\humaneval_task_ids_164.txt `
  --successor-samples .\artifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_164.jsonl `
  --base-only `
  --mini
```

Immediately copy the result folder if you want to preserve this base-only
artifact before running the plus-mini sidecar:

```powershell
Copy-Item `
  .\artifacts\evalplus_leaderboard\results\rclm_N5_seed0_humaneval_164tasks `
  .\artifacts\evalplus_leaderboard\results\rclm_N5_seed0_humaneval_164tasks_baseonly `
  -Recurse -Force
```

## EvalPlus/HumanEval+ direct mini sidecar

```powershell
python .\artifacts\evalplus_leaderboard\certified_evalplus_suite_harness.py `
  --dataset humaneval `
  --mode rclm `
  --N 5 `
  --seed 0 `
  --task-list .\artifacts\evalplus_leaderboard\tasks\humaneval\humaneval_task_ids_164.txt `
  --successor-samples .\artifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_164.jsonl `
  --mini
```

## Failure inspection

```powershell
@'
import json
from pathlib import Path

p = Path("artifacts/evalplus_leaderboard/results/rclm_N5_seed0_humaneval_164tasks/successor_direct_eval_results.json")
data = json.loads(p.read_text(encoding="utf-8"))

failed = [r for r in data["task_results"] if not r["passed"]]
for r in failed:
    print(json.dumps(r, indent=2))
'@ | python
```

## Claim boundary

A successful direct sidecar can claim:

`Claimable non-oracle HumanEval 164-task direct sidecar improvement with
RCP/RCLM certificates preserved.`

It cannot claim:

- official EvalPlus leaderboard result,
- SWE-bench result,
- Terminal-Bench / RE-Bench / MLE-Bench / WebArena result,
- full autonomous RSI.
