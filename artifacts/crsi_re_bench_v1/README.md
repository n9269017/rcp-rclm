# CRSI-RE-Bench v1

## Certified Recursive Successor Improvement over the Official RE-Bench v1 Environments

This package begins the first **explicit RE-Bench v1** phase of the RCP/RCLM
project. It does not create an RE-Bench-like substitute and it does not accept a
manually declared score table. It pins the public `METR/RE-Bench` repository,
launches concrete agent policies in the official task families through Vivaria,
imports scorer-produced logs, computes the RE-Bench paper normalization, and
binds every score artifact to the existing CRSI certificate chain.

The target execution path is:

```text
RCLM_t core package
  -> hash-chained benchmark-ready policy extension
  -> concrete executable agent/scaffold
  -> official METR/RE-Bench task-family checkout
  -> official task scorer executes
  -> raw scorer log + trajectory + submission exported
  -> normalized RE-Bench score artifact
  -> RCP/RCLM certificate bridge and independent reproduction
```

## Official source pin

The integration manifest pins:

```text
Official repository: METR/RE-Bench
Pinned commit:       93b98062e55f6945d4a7e213a3226dd419896170
Commit message:      Stage suite (#39)
Execution platform:  Vivaria / METR Task Standard
```

The pin is not trusted merely because it appears in a JSON file. Before any run,
`pin_official_release.py` requires a clean checkout at that exact commit and
computes:

```text
suite manifest SHA-256
each task-family Git tree object
each task-family deterministic tree SHA-256
each manifest.yaml SHA-256
each scorer-file SHA-256
per-environment scorer-bundle SHA-256
```

The runner rechecks the live checkout against these hashes during preflight.

## The seven official RE-Bench v1 environments

| Index | Display label | Official task family | Pinned version | Official resources |
|---:|---|---|---:|---|
| 0 | Optimize LLM Foundry | `ai_rd_optimize_llm_foundry` | 0.2.5 | 4 H100, 52 CPU, 400 GB |
| 1 | Optimize a Kernel | `ai_rd_triton_cumsum` | 0.2.5 | 1 H100, 13 CPU, 100 GB |
| 2 | Fix Embedding | `ai_rd_fix_embedding` | 0.2.5 | 1 H100, 13 CPU, 100 GB |
| 3 | Scaling Law Experiment | `ai_rd_small_scaling_law` | 0.2.3 | 6–8 H100, 48 CPU, 400 GB |
| 4 | Restricted Architecture MLM | `ai_rd_restricted_mlm` | 0.2.5 | 2 H100, 26 CPU, 200 GB |
| 5 | Finetune GPT-2 for QA | `ai_rd_nanogpt_chat_rl` | 0.2.4 | 2 H100, 26 CPU, 200 GB |
| 6 | Scaffolding for Rust Codecontest | `ai_rd_rust_codecontests_inference` | 0.2.3 | CPU-only, 20 CPU, 100 GB |

`official_release_manifest.json` records the official starting/reference raw
scores and objective direction for each environment. The score adapter computes:

```text
normalized = max(0, (raw - starting_raw) / (reference_raw - starting_raw))
```

Therefore the starting solution maps to `0`, the official reference solution to
`1`, and stronger-than-reference results may exceed `1`.

## Pilot versus final result

### Official-environment integration pilot

The first executable target is the official CPU-only Rust Codecontests task:

```text
ai_rd_rust_codecontests_inference/main
```

The pilot uses the real official task family and scorer code but a shortened
60-minute/token-limited budget. Its allowed label is:

```text
RE-Bench v1 official-environment integration pilot
```

It is not the final seven-environment RE-Bench result.

### Full target

The final target requires:

```text
all seven official task families
8 hours per environment/package
fixed Vivaria token/action/time/cost limits across packages
at least 3 independent seeds
actual official scorer logs
all CRSI successor packages evaluated
trajectories and final submissions preserved
certificate bridge and offline reproduction
```

The full runner also refuses an operator-declared policy ladder. Full mode
requires `policy_provenance_mode=predecessor_generated` with one no-oracle policy
generation trace for every non-root successor package.

## Files

```text
artifacts/crsi_re_bench_v1/
  README.md
  official_release_manifest.json
  official_environment_hashes.json       # unresolved template
  compute_budget_manifest.json
  agent_entrypoint_manifest.json         # unresolved template
  no_leakage_manifest.json               # unresolved template
  scorer_manifest.json                   # unresolved template
  crsi_re_bench_schema.py
  pin_official_release.py
  build_agent_entrypoint_manifest.py
  attest_no_leakage.py
  re_bench_score_adapter.py
  crsi_re_bench_runner.py
  reproduce_crsi_re_bench.py
```

Run-specific generated files belong under:

```text
artifacts/crsi_re_bench_v1/results/
```

and are ignored until an accepted result is deliberately recorded.

## Prerequisites

Use the official RE-Bench/Vivaria setup. The pinned official guide requires
Docker, Python 3.11+, and for GPU tasks NVIDIA drivers/CUDA 12.x plus NVIDIA
Container Toolkit. The official guide supports using the `viv` CLI remotely
against a configured Vivaria server. On Windows, the actual task environment is
best hosted through WSL/Linux or a remote Linux GPU server while PowerShell can
remain the orchestration shell.

Keep benchmark checkouts outside the public RCP/RCLM repository. Do not commit
secrets, unprotected official solutions, or extracted protected solution
material.

## 1. Clone and pin the official code

PowerShell example:

```powershell
$REBENCH_ROOT = "$HOME\Desktop\official-re-bench"
$AGENT_ROOT   = "$HOME\Desktop\modular-public"

git clone https://github.com/METR/RE-Bench.git $REBENCH_ROOT
git -C $REBENCH_ROOT checkout 93b98062e55f6945d4a7e213a3226dd419896170
git -C $REBENCH_ROOT status --short

git clone https://github.com/poking-agents/modular-public.git $AGENT_ROOT
git -C $AGENT_ROOT checkout a00b7cae3cf9f176fcffe790ef22f4f9da892f9a
git -C $AGENT_ROOT status --short
```

Both status commands must be empty before pinning.

Follow the official RE-Bench setup guide to install/configure Vivaria and create
`secrets.env`. Never commit that file. The Rust pilot requires the API secret
named by the official setup guide. Ensure the chosen API/service has appropriate
no-training/data-retention controls for benchmark integrity.

## 2. Pin official task and scorer hashes

```powershell
$RUN_ROOT = ".\artifacts\crsi_re_bench_v1\results\pilot_seed0"
New-Item -ItemType Directory -Force $RUN_ROOT | Out-Null

python .\artifacts\crsi_re_bench_v1\pin_official_release.py `
  --official-release-root $REBENCH_ROOT `
  --out "$RUN_ROOT\official_environment_hashes.json" `
  --scorer-out "$RUN_ROOT\pinned_scorer_manifest.json"
```

A valid result reports `environment_count: 7` and `ok: true`.

## 3. Build executable package-specific policies

For the recorded k5 seed0 CRSI chain there are six packages (`RCLM_0` through
`RCLM_5`). The builder validates that every settings pack exists in the pinned
agent's executable `manifest.json`, hashes the resolved settings, and constructs
a benchmark-ready successor-extension hash chain.

Pilot command using the included reference policy ladder:

```powershell
python .\artifacts\crsi_re_bench_v1\build_agent_entrypoint_manifest.py `
  --repo-root . `
  --crsi-chain-summary .\artifacts\crsi_core\results\rclm_crsi_core_k5_baseN2_seed0\rclm_crsi_core_chain_summary.json `
  --agent-root $AGENT_ROOT `
  --expected-agent-commit a00b7cae3cf9f176fcffe790ef22f4f9da892f9a `
  --policy-provenance operator_declared_integration_pilot `
  --out "$RUN_ROOT\agent_entrypoint_manifest.json"
```

The pilot policy ladder changes real scaffold settings between packages. It is
explicitly labeled operator-declared and therefore does **not** claim that the
core CRSI packages autonomously synthesized those policies.

For the full seven-environment target, use:

```text
--policy-provenance predecessor_generated
--generation-trace-dir <directory containing policy_generation_trace_1.json ...>
```

Each trace must identify the predecessor/successor IDs and declare no manual
repair or oracle access.

## 4. Create the no-leakage attestation

```powershell
python .\artifacts\crsi_re_bench_v1\attest_no_leakage.py `
  --operator "Nicolas.n926" `
  --confirm "NO_LEAKAGE_NO_ORACLE_NO_MANUAL_REPAIR" `
  --notes "Independent official-environment pilot; no hidden reference solution access, no manual patching, no benchmark training use." `
  --out "$RUN_ROOT\no_leakage_manifest.json"
```

The attestation is evidence, not magical proof. Preserve service settings,
Vivaria logs, task hashes, and trajectories so the declaration can be audited.

## 5. Preflight

```powershell
python .\artifacts\crsi_re_bench_v1\crsi_re_bench_runner.py `
  --phase preflight `
  --official-release-root $REBENCH_ROOT `
  --crsi-chain-summary .\artifacts\crsi_core\results\rclm_crsi_core_k5_baseN2_seed0\rclm_crsi_core_chain_summary.json `
  --official-environment-hashes "$RUN_ROOT\official_environment_hashes.json" `
  --pinned-scorer-manifest "$RUN_ROOT\pinned_scorer_manifest.json" `
  --agent-entrypoint-manifest "$RUN_ROOT\agent_entrypoint_manifest.json" `
  --no-leakage-manifest "$RUN_ROOT\no_leakage_manifest.json" `
  --run-mode pilot `
  --outdir $RUN_ROOT
```

Preflight fails on any dirty/mismatched official checkout, altered scorer,
altered agent checkout/settings pack, invalid CRSI chain, missing attestation, or
unacceptable policy provenance.

## 6. Build the concrete Vivaria run plan

```powershell
python .\artifacts\crsi_re_bench_v1\crsi_re_bench_runner.py `
  --phase plan `
  --official-release-root $REBENCH_ROOT `
  --crsi-chain-summary .\artifacts\crsi_core\results\rclm_crsi_core_k5_baseN2_seed0\rclm_crsi_core_chain_summary.json `
  --official-environment-hashes "$RUN_ROOT\official_environment_hashes.json" `
  --pinned-scorer-manifest "$RUN_ROOT\pinned_scorer_manifest.json" `
  --agent-entrypoint-manifest "$RUN_ROOT\agent_entrypoint_manifest.json" `
  --no-leakage-manifest "$RUN_ROOT\no_leakage_manifest.json" `
  --run-mode pilot `
  --seed 0 `
  --secrets-env "$REBENCH_ROOT\secrets.env" `
  --outdir $RUN_ROOT
```

The plan contains six real `viv run` commands with fixed `--max-tokens`,
`--max-actions`, `--max-total-seconds`, and `--max-cost` limits.

## 7. Execute only after export plumbing is configured

Execution is deliberately gated:

```text
--confirm-execute OFFICIAL_RE_BENCH_V1
```

For every run, configure three operator-specific export command templates:

```text
score exporter      -> writes raw_score_log.json
trajectory exporter -> writes agent_trajectory.json
submission exporter -> copies the final submission tree into final_submission/
usage exporter       -> writes usage.json with actual run usage and resource fields
```

Vivaria's HTTP/CLI interfaces are deployment-specific and unstable, so the
integration accepts explicit command templates rather than pretending one
hard-coded database query is universally correct.

Template placeholders:

```text
{run_id} {out} {package_index} {family}
```

Example shape:

```powershell
python .\artifacts\crsi_re_bench_v1\crsi_re_bench_runner.py `
  --phase execute `
  --crsi-chain-summary .\artifacts\crsi_core\results\rclm_crsi_core_k5_baseN2_seed0\rclm_crsi_core_chain_summary.json `
  --agent-entrypoint-manifest "$RUN_ROOT\agent_entrypoint_manifest.json" `
  --no-leakage-manifest "$RUN_ROOT\no_leakage_manifest.json" `
  --outdir $RUN_ROOT `
  --plan "$RUN_ROOT\run_plan.json" `
  --confirm-execute OFFICIAL_RE_BENCH_V1 `
  --score-export-command-template '<YOUR_EXPORTER> score --run-id {run_id} --out "{out}"' `
  --trajectory-export-command-template '<YOUR_EXPORTER> trajectory --run-id {run_id} --out "{out}"' `
  --submission-export-command-template '<YOUR_EXPORTER> submission --run-id {run_id} --out "{out}"' `
  --usage-export-command-template '<YOUR_EXPORTER> usage --run-id {run_id} --out "{out}"'
```

The execution report is not `ok` unless all agent runs succeed and all three
artifact classes are present for every package.

## 8. Ingest official scorer logs

`raw_score_log.json` must be JSON or JSONL containing numeric official scorer
entries. Minimum entry:

```json
{"score": 0.08}
```

Recommended entry:

```json
{
  "timestamp": "2026-07-11T00:00:00+00:00",
  "score": 0.08,
  "compute_used": {"wall_clock_seconds": 1760},
  "usage_limits": {"tokens": 100000, "actions": 1000, "total_seconds": 1800, "cost": 100.0}
}
```

Then:

```powershell
python .\artifacts\crsi_re_bench_v1\crsi_re_bench_runner.py `
  --phase ingest `
  --crsi-chain-summary .\artifacts\crsi_core\results\rclm_crsi_core_k5_baseN2_seed0\rclm_crsi_core_chain_summary.json `
  --official-environment-hashes "$RUN_ROOT\official_environment_hashes.json" `
  --pinned-scorer-manifest "$RUN_ROOT\pinned_scorer_manifest.json" `
  --agent-entrypoint-manifest "$RUN_ROOT\agent_entrypoint_manifest.json" `
  --no-leakage-manifest "$RUN_ROOT\no_leakage_manifest.json" `
  --run-mode pilot `
  --seed 0 `
  --outdir $RUN_ROOT
```

No score is invented by the adapter. Missing scorer exports fail ingestion.

## 9. Reproduce the result

```powershell
python .\artifacts\crsi_re_bench_v1\reproduce_crsi_re_bench.py `
  --result-dir $RUN_ROOT `
  --crsi-chain-summary .\artifacts\crsi_core\results\rclm_crsi_core_k5_baseN2_seed0\rclm_crsi_core_chain_summary.json `
  --official-environment-hashes "$RUN_ROOT\official_environment_hashes.json" `
  --pinned-scorer-manifest "$RUN_ROOT\pinned_scorer_manifest.json" `
  --agent-entrypoint-manifest "$RUN_ROOT\agent_entrypoint_manifest.json" `
  --no-leakage-manifest "$RUN_ROOT\no_leakage_manifest.json"
```

The reproduction checker recomputes input hashes, scorer hashes, package and
environment aggregates, progression rules, raw log hashes, result self-hashes,
and the certificate bridge.

## Formal acceptance rule

For package `RCLM_t` and environment `e`, the score artifact records:

```text
raw_score[t,e]
normalized_score[t,e]
best_score[t,e]
time_to_best_seconds[t,e]
compute_used[t,e]
usage_limits[t,e]
submission_hash[t,e]
scorer_hash[e]
policy_hash[t]
benchmark_successor_id[t]
```

A bridge result passes only if:

```text
RCP/RCLM certificates remain preserved
official environment/scorer hashes remain pinned
fixed usage limits are equal across packages within each environment
no hidden reference solution access, leakage, oracle, or manual patching
score entries are attached to the correct core and benchmark-ready successor IDs
aggregate normalized score never regresses
at least one strict aggregate improvement occurs
no environment regresses by more than epsilon
all raw logs, trajectories, submissions, run logs, and hash manifests reproduce
```

## Claim boundary

### Pilot claim after a real passing pilot

```text
CRSI-RCLM was evaluated in an independent integration pilot on the official
RE-Bench v1 Rust Codecontests environment, using pinned official task/scorer code
and hash-logged executable package-specific agent policies.
```

This is not a full RE-Bench result and not METR validation.

### Full independent run claim

Only after all seven environments, fixed 8-hour budgets, required seeds, actual
official scorers, predecessor-generated policy traces, and reproduction pass:

```text
CRSI-RCLM was evaluated in an independent run on all seven official RE-Bench v1
environments with certificate-preserving recursive successor packages.
```

### Never claim without third-party validation

```text
Official METR-validated result
```

Using METR's public environment code does not mean METR administered, accepted,
or reproduced the run.
