# HumanEval/32 semantic evaluator fix

This patch changes the Docker-free direct EvalPlus micro/suite evaluator for `HumanEval/32` only.

Before this patch, the runner compared submitted output to the canonical solution output with exact equality:

```python
ok = (got == expected)
```

That is too strict for `HumanEval/32`, because the task asks for a root of a polynomial. Many valid solvers return a different floating approximation from the canonical Newton implementation while still satisfying the semantic task predicate.

The new evaluator checks, only for `task_id == "HumanEval/32"` and `entry_point == "find_zero"`:

```python
isfinite(x) and abs(poly(xs, x)) < 1e-4
```

All other tasks keep the previous canonical exact-output comparison.

Run the included self-test:

```powershell
python .\artifacts\evalplus_bridge\test_humaneval32_semantic_predicate.py
```

Then rerun the 40-task sidecar:

```powershell
python .\artifacts\evalplus_leaderboard\certified_evalplus_suite_harness.py `
  --dataset humaneval `
  --mode rclm `
  --N 5 `
  --seed 0 `
  --task-list .\artifacts\evalplus_leaderboard\tasks\humaneval\humaneval_task_ids_40.txt `
  --successor-samples .\artifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_40.jsonl `
  --mini
```
