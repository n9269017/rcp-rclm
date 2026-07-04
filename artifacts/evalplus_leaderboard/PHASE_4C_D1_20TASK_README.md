# Phase 4C-D1: EvalPlus/HumanEval+ 20-task coverage expansion

This update adds the 20-task HumanEval+ leaderboard-prep sample file and task-list for the next coverage expansion step.

Files:

```text
artifacts/evalplus_leaderboard/tasks/humaneval/humaneval_task_ids_20.txt
artifacts/evalplus_leaderboard/successor_samples_non_oracle_HumanEval_20.jsonl
artifacts/evalplus_leaderboard/make_humaneval_20_samples.py
```

Scope and claim boundary:

- This is a Docker-free direct EvalPlus/HumanEval+ suite-prep sidecar input, not an official EvalPlus leaderboard result.
- If the 20-task sidecar passes, the claim is a certificate-preserving non-oracle HumanEval+ 20-task direct sidecar improvement.
- It is not SWE-bench, Terminal-Bench, RE-Bench, MLE-bench, WebArena, full HumanEval+, or full autonomous RSI.

Run from the repository root:

```powershell
python .rtifacts\evalplus_leaderboardalidate_evalplus_samples.py `
  --dataset humaneval `
  --samples .rtifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_20.jsonl `
  --task-list .rtifacts\evalplus_leaderboard	asks\humaneval\humaneval_task_ids_20.txt

python .rtifacts\evalplus_leaderboard\certified_evalplus_suite_harness.py `
  --dataset humaneval `
  --mode rclm `
  --N 5 `
  --seed 0 `
  --task-list .rtifacts\evalplus_leaderboard	asks\humaneval\humaneval_task_ids_20.txt `
  --successor-samples .rtifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_20.jsonl `
  --mini
```

Expected success markers:

```json
"task_count": 20,
"certificate_preserved": true,
"claimable_non_oracle_improvement": true
```

If any task fails, inspect:

```powershell
Get-Content .rtifacts\evalplus_leaderboardesultsclm_N5_seed0_humaneval_20tasks\successor_direct_eval_results.json
Get-Content .rtifacts\evalplus_leaderboardesultsclm_N5_seed0_humaneval_20tasks\leaderboard_prep_sidecar.json
```
