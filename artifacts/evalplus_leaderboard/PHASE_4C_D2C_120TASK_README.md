# Phase 4C-D2c: HumanEval/80--119 expansion to a 120-task sidecar

This package extends the already-passed 80-task HumanEval+ direct sidecar to a
120-task candidate sidecar. It adds non-oracle successor samples for
`HumanEval/80` through `HumanEval/119`, a conservative merge script, and the
`HumanEval/0`--`HumanEval/119` task-id list.

This is still **not** an official EvalPlus leaderboard result. It is a
Docker-free direct EvalPlus/HumanEval+ public-data sidecar that preserves the
RCP/RCLM certificate bundle.

## Files

```text
artifacts/evalplus_leaderboard/
  successor_samples_non_oracle_HumanEval_80_119.jsonl
  make_humaneval_120_samples.py
  PHASE_4C_D2C_120TASK_README.md

artifacts/evalplus_leaderboard/tasks/humaneval/
  humaneval_task_ids_120.txt
```

## Run order

```powershell
python .\artifacts\evalplus_leaderboard\make_humaneval_120_samples.py

python .\artifacts\evalplus_leaderboard\validate_evalplus_samples.py `
  --dataset humaneval `
  --samples .\artifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_120.jsonl `
  --task-list .\artifacts\evalplus_leaderboard\tasks\humaneval\humaneval_task_ids_120.txt

python .\artifacts\evalplus_leaderboard\certified_evalplus_suite_harness.py `
  --dataset humaneval `
  --mode rclm `
  --N 5 `
  --seed 0 `
  --task-list .\artifacts\evalplus_leaderboard\tasks\humaneval\humaneval_task_ids_120.txt `
  --successor-samples .\artifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_120.jsonl `
  --mini
```

Inspect:

```powershell
Get-Content .\artifacts\evalplus_leaderboard\results\rclm_N5_seed0_humaneval_120tasks\leaderboard_prep_sidecar.json
```

Target fields:

```json
"task_count": 120,
"certificate_preserved": true,
"claimable_non_oracle_improvement": true
```

Ideal target:

```json
"successor_score": 1.0,
"delta": 1.0
```

If any task fails, print the failure list:

```powershell
@'
import json
from pathlib import Path

p = Path("artifacts/evalplus_leaderboard/results/rclm_N5_seed0_humaneval_120tasks/successor_direct_eval_results.json")
data = json.loads(p.read_text(encoding="utf-8"))
failed = [r for r in data["task_results"] if not r["passed"]]
for r in failed:
    print(json.dumps(r, indent=2))
'@ | python
```

Do not stage `artifacts/evalplus_leaderboard/full_164_workspace`.
