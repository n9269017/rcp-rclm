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
