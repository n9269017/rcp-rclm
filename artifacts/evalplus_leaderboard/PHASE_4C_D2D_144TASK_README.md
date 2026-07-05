# Phase 4C-D2d — HumanEval/120–143 expansion to a 144-task sidecar

This update extends the certificate-preserving HumanEval+ direct sidecar from
the already-passed 120-task checkpoint to a 144-task checkpoint.

It adds non-oracle sample entries for:

```text
HumanEval/120
...
HumanEval/143
```

and a merge script that builds:

```text
artifacts/evalplus_leaderboard/successor_samples_non_oracle_HumanEval_144.jsonl
```

from:

```text
successor_samples_non_oracle_HumanEval_120.jsonl
+
successor_samples_non_oracle_HumanEval_120_143.jsonl
```

## Claim boundary

Before running the harness:

```text
144-task expansion files: added.
144-task result: not yet.
```

After a successful run, the correct claim is:

```text
Claimable non-oracle HumanEval+ 144-task direct sidecar improvement with
RCP/RCLM certificates preserved.
```

Only if the sidecar reports `successor_score = 1.0` is it a 144/144 direct
sidecar full pass.

This is still not an official EvalPlus leaderboard result, not a SWE-bench
result, and not a full autonomous RSI result.

## Commands

```powershell
python .\artifacts\evalplus_leaderboard\make_humaneval_144_samples.py

python .\artifacts\evalplus_leaderboard\validate_evalplus_samples.py `
  --dataset humaneval `
  --samples .\artifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_144.jsonl `
  --task-list .\artifacts\evalplus_leaderboard\tasks\humaneval\humaneval_task_ids_144.txt

python .\artifacts\evalplus_leaderboard\certified_evalplus_suite_harness.py `
  --dataset humaneval `
  --mode rclm `
  --N 5 `
  --seed 0 `
  --task-list .\artifacts\evalplus_leaderboard\tasks\humaneval\humaneval_task_ids_144.txt `
  --successor-samples .\artifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_144.jsonl `
  --mini
```

If failures remain:

```powershell
@'
import json
from pathlib import Path

p = Path("artifacts/evalplus_leaderboard/results/rclm_N5_seed0_humaneval_144tasks/successor_direct_eval_results.json")
data = json.loads(p.read_text(encoding="utf-8"))

failed = [r for r in data["task_results"] if not r["passed"]]
for r in failed:
    print(json.dumps(r, indent=2))
'@ | python
```
