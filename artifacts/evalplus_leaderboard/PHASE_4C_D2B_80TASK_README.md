# Phase 4C-D2b: HumanEval+ 80-task coverage expansion

This update moves the direct EvalPlus/HumanEval+ sidecar from the already-passed
40-task checkpoint to an 80-task checkpoint.

It adds non-oracle candidate samples for `HumanEval/40` through `HumanEval/79`
and a conservative merge script that builds:

```text
artifacts/evalplus_leaderboard/successor_samples_non_oracle_HumanEval_80.jsonl
artifacts/evalplus_leaderboard/tasks/humaneval/humaneval_task_ids_80.txt
```

The merge script refuses malformed, duplicate, missing, extra, or TODO-like entries.
It also updates the `full_164_workspace` chunk files for `040--059` and `060--079`
if that workspace exists.

## Important claim boundary

Installing this update does not by itself prove the 80-task result. The result is
claimable only after the user runs the validator and the certificate-preserving
suite harness and obtains:

```json
"task_count": 80,
"certificate_preserved": true,
"claimable_non_oracle_improvement": true
```

The ideal target is:

```json
"successor_score": 1.0,
"delta": 1.0
```

This remains a Docker-free direct EvalPlus-data sidecar, not an official EvalPlus
leaderboard result.

## Run sequence

```powershell
cd $HOME\Desktop\rcp-rclm

python .\artifacts\evalplus_leaderboard\make_humaneval_80_samples.py

python .\artifacts\evalplus_leaderboard\validate_evalplus_samples.py `
  --dataset humaneval `
  --samples .\artifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_80.jsonl `
  --task-list .\artifacts\evalplus_leaderboard\tasks\humaneval\humaneval_task_ids_80.txt

python .\artifacts\evalplus_leaderboard\certified_evalplus_suite_harness.py `
  --dataset humaneval `
  --mode rclm `
  --N 5 `
  --seed 0 `
  --task-list .\artifacts\evalplus_leaderboard\tasks\humaneval\humaneval_task_ids_80.txt `
  --successor-samples .\artifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_80.jsonl `
  --mini
```

Then inspect:

```powershell
Get-Content .\artifacts\evalplus_leaderboard\results\rclm_N5_seed0_humaneval_80tasks\leaderboard_prep_sidecar.json
```

If any task fails, print the failures:

```powershell
@'
import json
from pathlib import Path
p = Path("artifacts/evalplus_leaderboard/results/rclm_N5_seed0_humaneval_80tasks/successor_direct_eval_results.json")
data = json.loads(p.read_text(encoding="utf-8"))
for r in data["task_results"]:
    if not r["passed"]:
        print(json.dumps(r, indent=2))
'@ | python
```

Do not stage `full_164_workspace`. Stage only the permanent 80-task files and the
80-task result after it passes.
