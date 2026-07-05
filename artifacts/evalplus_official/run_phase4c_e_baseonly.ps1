# Phase 4C-E convenience runner.
# This script builds official samples and runs canonical/base-only EvalPlus CLI.
# Full HumanEval+ official CLI can take longer; run the second block manually.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

cd $HOME\Desktop\rcp-rclm

python .\artifacts\evalplus_official\build_official_evalplus_samples.py `
  --dataset humaneval `
  --successor-source .\artifacts\evalplus_leaderboard\successor_samples_non_oracle_HumanEval_164.jsonl `
  --task-list .\artifacts\evalplus_leaderboard\tasks\humaneval\humaneval_task_ids_164.txt

python .\artifacts\evalplus_official\run_evalplus_official.py `
  --dataset humaneval `
  --samples .\artifacts\evalplus_official\samples\humaneval_164_baseline_empty.jsonl `
  --label humaneval164_baseline_baseonly `
  --base-only

python .\artifacts\evalplus_official\run_evalplus_official.py `
  --dataset humaneval `
  --samples .\artifacts\evalplus_official\samples\humaneval_164_successor.jsonl `
  --label humaneval164_successor_baseonly `
  --base-only

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

Write-Host "Phase 4C-E base-only official CLI wrapper complete."
