# Declared RE/METR-style AI-R&D task set v0

This folder is the first **non-smoke** external-score-ledger attachment target for
the CRSI-RE/METR bridge.

It is still **not** an official RE-Bench or METR result.  It is a declared,
repository-local RE/METR-style AI-R&D task set and score ledger used to exercise
the external bridge in real-input mode:

```text
CRSI-Core chain summary
  + declared task_manifest.json
  + declared score_ledger.json
  + scorer_artifact.json / scorer hash
  + no-leakage / no-oracle / no-manual-repair declarations
  -> certificate-preserving external bridge sidecar
```

## Why this comes after the smoke fixture

The bridge smoke fixture proved that the adapter mechanics work.  This declared
fixture is the first step beyond smoke mode because it does **not** use
`--make-smoke-fixture`.  Instead, it supplies an explicit task manifest, an
explicit external score ledger, and an explicit scorer artifact.

The result is still a declared benchmark fixture, not an official external
benchmark result.  Official RE-Bench/METR claims require official evaluator
artifacts and/or accepted benchmark run outputs.

## Files

```text
artifacts/crsi_external_bridge/declared_re_metr_v0/
  task_manifest.json                 # declared RE/METR-style task set
  scorer_artifact.json               # declared scorer/rubric artifact
  make_declared_score_ledger.py      # fills successor IDs from a CRSI chain
  run_declared_bridge.py             # one-command ledger + bridge + reproduction
  README.md
```

Generated outputs are written under:

```text
artifacts/crsi_external_bridge/results/declared_re_metr_v0_k5_seed0/
```

and remain ignored until explicitly recorded.

## Run the declared bridge attachment

From the repository root, after the bridge smoke result has been recorded/merged:

```powershell
python .\artifacts\crsi_external_bridge\declared_re_metr_v0\run_declared_bridge.py `
  --crsi-chain-summary .\artifacts\crsi_core\results\rclm_crsi_core_k5_baseN2_seed0\rclm_crsi_core_chain_summary.json `
  --outdir .\artifacts\crsi_external_bridge\results\declared_re_metr_v0_k5_seed0
```

Expected output:

```json
{
  "ok": true,
  "sidecar_ok": true,
  "reproduction_ok": true
}
```

The one-command runner creates:

```text
artifacts/crsi_external_bridge/results/declared_re_metr_v0_k5_seed0/
  declared_re_metr_score_ledger.json
  crsi_chain_reproduction_report.json
  crsi_external_bridge_sidecar.json
  crsi_external_bridge_summary.json
  crsi_external_bridge_reproduction_report.json
```

## Manual equivalent

You can also run the steps manually.

Create the declared score ledger by binding successor IDs from the recorded CRSI
chain:

```powershell
python .\artifacts\crsi_external_bridge\declared_re_metr_v0\make_declared_score_ledger.py `
  --crsi-chain-summary .\artifacts\crsi_core\results\rclm_crsi_core_k5_baseN2_seed0\rclm_crsi_core_chain_summary.json `
  --task-manifest .\artifacts\crsi_external_bridge\declared_re_metr_v0\task_manifest.json `
  --scorer-artifact .\artifacts\crsi_external_bridge\declared_re_metr_v0\scorer_artifact.json `
  --outdir .\artifacts\crsi_external_bridge\results\declared_re_metr_v0_k5_seed0
```

Then build the bridge sidecar:

```powershell
python .\artifacts\crsi_external_bridge\crsi_external_bridge_harness.py `
  --crsi-chain-summary .\artifacts\crsi_core\results\rclm_crsi_core_k5_baseN2_seed0\rclm_crsi_core_chain_summary.json `
  --task-manifest .\artifacts\crsi_external_bridge\declared_re_metr_v0\task_manifest.json `
  --score-ledger .\artifacts\crsi_external_bridge\results\declared_re_metr_v0_k5_seed0\declared_re_metr_score_ledger.json `
  --scorer-artifact .\artifacts\crsi_external_bridge\declared_re_metr_v0\scorer_artifact.json `
  --benchmark-id declared_re_metr_ai_rd_v0 `
  --benchmark-kind declared_re_metr_external_ai_rd_adapter `
  --outdir .\artifacts\crsi_external_bridge\results\declared_re_metr_v0_k5_seed0
```

Then reproduce:

```powershell
python .\artifacts\crsi_external_bridge\reproduce_external_bridge.py `
  .\artifacts\crsi_external_bridge\results\declared_re_metr_v0_k5_seed0\crsi_external_bridge_sidecar.json
```

## Task-set intent

The declared task set is intentionally small and adapter-focused.  It models the
kind of external evidence an RE/METR-style run must carry:

```text
1. reproduce a recorded CRSI chain;
2. audit certificate preservation;
3. check no-leakage / no-oracle conditions;
4. validate score-ledger consistency;
5. produce an AI-R&D-style research report/evidence package.
```

The package-level scores in the generated score ledger are monotone improving
across the recorded k5 CRSI chain.  The score entries are bound to the chain's
actual successor IDs, so the external bridge can verify successor alignment.

## Claim boundary

A passing declared-v0 bridge run can claim:

```text
A declared RE/METR-style AI-R&D score ledger was attached to a recorded CRSI-Core
chain while preserving RCP/RCLM certificates, protected non-loss invariants,
hash-chain integrity, no-oracle conditions, no-leakage flags, and monotone
external score improvement under the declared scorer artifact.
```

It cannot claim:

```text
official RE-Bench result
official METR result
external public benchmark result
frontier-scale validation
full autonomous RSI
unbounded-horizon empirical proof
```

The next phase after this declared fixture is to replace `task_manifest.json`,
`score_ledger.json`, and `scorer_artifact.json` with artifacts from an official
or independently administered RE/METR-style evaluation.
