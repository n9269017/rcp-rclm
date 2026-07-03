# Artifacts

This folder contains controlled RCP and RCLM executable reference artifacts, replay checkers, run logs, and mechanization-status manifests.

Replay the artifacts with:

```powershell
cd artifacts\rcp
python .\checker.py .\controlled_artifact.json

cd ..\rclm
python .\checker.py .\controlled_artifact.json
```

The Lean 4 certificate covers the canonical finite RCP/RCLM witness and refinement core. It does not mechanize the full math or architecture papers.

## Open-loop arbitrary-horizon generator

The repository also includes an open-loop arbitrary finite-prefix generator:

```powershell
python .\artifacts\common\generate_reference_artifact.py --mode rcp --N 5 --out .\artifacts\rcp\generated_artifact_N5.json --runlog .\artifacts\rcp\generated_runlog_N5.json
python .\artifacts\rcp\checker.py .\artifacts\rcp\generated_artifact_N5.json

python .\artifacts\common\generate_reference_artifact.py --mode rclm --N 5 --out .\artifacts\rclm\generated_artifact_N5.json --runlog .\artifacts\rclm\generated_runlog_N5.json
python .\artifacts\rclm\checker.py .\artifacts\rclm\generated_artifact_N5.json
```

This generator implements the open-loop map N -> canonical finite reference artifact. It is not yet the closed-loop certified successor generator; it does not search over multiple candidate successors, reject invalid candidates, or recursively feed accepted successors into a successor-search loop.

## Closed-loop certified successor generator (installed)

The repository now includes a finite closed-loop certified successor-generation engine:

```powershell
python .\artifacts\common\closed_loop_reference_engine.py --mode rcp --N 5 --seed 0
python .\artifacts\rcp\checker.py .\artifacts\closed_loop_runs\rcp_N5_seed0\generated_artifact.json

python .\artifacts\common\closed_loop_reference_engine.py --mode rclm --N 5 --seed 0
python .\artifacts\rclm\checker.py .\artifacts\closed_loop_runs\rclm_N5_seed0\generated_artifact.json
```

The closed-loop engine initializes a certified state, generates candidate successors, builds proof-carrying candidate packets, rejects invalid candidates, accepts a passing candidate, appends it to the certified trajectory, and writes replayable logs and hashes.

The committed example runs are:

- `artifacts/closed_loop_runs/rcp_N5_seed0/`
- `artifacts/closed_loop_runs/rclm_N5_seed0/`

Each run includes:

- `generated_artifact.json`
- `accepted_trajectory.json`
- `rejected_candidates.json`
- `closed_loop_runlog.json`
- `hashes.json`

This is a finite closed-loop certified RSI reference instance under declared conditions. It is not a claim of full autonomous RSI, broad learned-agent entry, or empirical deployment validation.
