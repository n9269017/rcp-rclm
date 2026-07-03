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
