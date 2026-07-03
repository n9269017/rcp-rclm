# Open-loop arbitrary-horizon generator

`generate_reference_artifact.py` is the Tier-1 artifact upgrade: it turns the static controlled JSON witness into an arbitrary finite-prefix constructor.

It is intentionally **not** the closed-loop RSI engine. It generates the canonical append-only reference trajectory for any finite horizon `N >= 2`, writes a generated artifact JSON, writes a generated run log, and leaves verification to the existing RCP/RCLM checkers.

## Examples

```powershell
python artifacts\common\generate_reference_artifact.py --mode rcp --N 5 --out artifacts\rcp\generated_artifact_N5.json --runlog artifacts\rcp\generated_runlog_N5.json
python artifacts\rcp\checker.py artifacts\rcp\generated_artifact_N5.json

python artifacts\common\generate_reference_artifact.py --mode rclm --N 5 --out artifacts\rclm\generated_artifact_N5.json --runlog artifacts\rclm\generated_runlog_N5.json
python artifacts\rclm\checker.py artifacts\rclm\generated_artifact_N5.json
```

Convenience wrappers are also provided:

```powershell
python artifacts\rcp\generator.py --N 5
python artifacts\rcp\checker.py artifacts\rcp\generated_artifact_N5.json

python artifacts\rclm\generator.py --N 5
python artifacts\rclm\checker.py artifacts\rclm\generated_artifact_N5.json
```

## Scope

- Generates arbitrary finite canonical prefixes `N -> Artifact_{0:N}^{can}`.
- Preserves exact non-loss/recovery by deterministic append-only construction.
- Generates strict ability expansion `a0 -> a0,a1 -> ... -> a0,...,aN`.
- Generates explicit residual vectors compatible with the existing checkers.
- Does not perform closed-loop candidate search or accept/reject invalid candidates.
- Does not claim broad learned-agent entry or empirical deployment validation.
