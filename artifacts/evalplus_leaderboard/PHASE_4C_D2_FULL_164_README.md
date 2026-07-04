# Phase 4C-D2: Full 164-task HumanEval+ coverage preparation

This phase prepares the move from the already-passed 20-task HumanEval+ direct sidecar to full 164-task HumanEval+ coverage.

It does **not** by itself claim a full HumanEval+ pass.  It creates the workspace, chunk files, validator, merger, and full-sidecar runner needed to complete all 164 non-oracle successor samples without accidentally treating TODO placeholders as benchmark evidence.

## Added files

```text
artifacts/evalplus_leaderboard/
  make_humaneval_full_workspace.py
  merge_humaneval_full_samples.py
  validate_humaneval_full_completion.py
  run_humaneval_full_sidecar.py
  show_humaneval_task.py
  PHASE_4C_D2_FULL_164_README.md

artifacts/evalplus_leaderboard/tasks/humaneval/
  humaneval_task_ids_full.txt
```

## Step 1: make sure public task export exists

```powershell
python .\artifacts\evalplus_leaderboard\export_evalplus_tasks.py --dataset humaneval
```

## Step 2: create the full workspace

```powershell
python .\artifacts\evalplus_leaderboard\make_humaneval_full_workspace.py --overwrite
```

This creates:

```text
artifacts/evalplus_leaderboard/full_164_workspace/
  chunks/
  task_lists/
  successor_samples_non_oracle_HumanEval_full.DRAFT_TODO.jsonl
  full_workspace_manifest.json
  chunk_status.csv
```

The first chunk should reuse the already-passed 20-task sample where available. The remaining chunks intentionally contain TODO placeholders.

## Step 3: edit chunk files, not the full draft

Edit files under:

```text
artifacts/evalplus_leaderboard/full_164_workspace/chunks/
```

Each TODO solution must be replaced with a complete non-oracle solution for the corresponding public prompt. Use:

```powershell
python .\artifacts\evalplus_leaderboard\show_humaneval_task.py HumanEval/37
```

to inspect public prompt material for a task.

## Step 4: merge only after TODOs are gone

```powershell
python .\artifacts\evalplus_leaderboard\merge_humaneval_full_samples.py
```

This writes:

```text
artifacts/evalplus_leaderboard/successor_samples_non_oracle_HumanEval_full.jsonl
```

The merge script refuses to create the final claimable sample file if TODO placeholders remain.

## Step 5: validate the final full sample file

```powershell
python .\artifacts\evalplus_leaderboard\validate_humaneval_full_completion.py `
  --samples .\artifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_full.jsonl
```

Required result:

```json
"ok": true,
"expected_tasks": 164,
"provided_tasks": 164,
"todo_count": 0,
"claimable_candidate": true
```

## Step 6: run full HumanEval+ direct sidecar

Start with mini mode:

```powershell
python .\artifacts\evalplus_leaderboard\run_humaneval_full_sidecar.py
```

This validates the full sample file and runs:

```text
certified_evalplus_suite_harness.py --dataset humaneval --full --mini
```

The result will be written under:

```text
artifacts/evalplus_leaderboard/results/rclm_N5_seed0_humaneval_full/
```

## Step 7: heavier direct full-plus-test sidecar

Only after the mini full run passes:

```powershell
python .\artifacts\evalplus_leaderboard\run_humaneval_full_sidecar.py --full-plus-tests
```

This is still a direct local sidecar, not an official EvalPlus leaderboard score.

## Claim boundary

A successful Phase 4C-D2 direct full sidecar can support:

```text
Claimable non-oracle full HumanEval+ direct sidecar improvement with RCP/RCLM certificate preservation.
```

It does **not** by itself support:

```text
official EvalPlus leaderboard result,
SWE-bench result,
Terminal-Bench result,
RE-Bench / MLE-Bench / WebArena result,
full autonomous RSI,
arbitrary trained-system entry.
```

Official EvalPlus leaderboard-style status requires official EvalPlus evaluation artifacts and the wrapper in `wrap_official_evalplus_results.py`.
