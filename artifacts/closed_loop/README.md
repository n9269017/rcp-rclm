# Closed-loop certified successor synthesis reference engine

This folder documents the Tier-2/3/4 executable-artifact upgrade for the RCP/RCLM package.

The shared implementation is:

```text
artifacts/common/closed_loop_reference_engine.py
```

Convenience wrappers are:

```text
artifacts/rcp/closed_loop.py
artifacts/rclm/closed_loop.py
```

A run does the following finite certified loop:

```text
initialize certified state rho_0
for t = 0..N-1:
  generate candidate successor set C_t
  build proof-carrying packets for each candidate
  verify residuals, recovery, non-loss, ability expansion, goal drift, trust, cost, and reality containment
  reject invalid candidates with logged reasons
  accept a passing candidate
  append accepted successor to the trajectory
  set rho_{t+1} as current state
write generated_artifact.json, accepted_trajectory.json, rejected_candidates.json, closed_loop_runlog.json, hashes.json
```

Example:

```powershell
python .\artifacts\common\closed_loop_reference_engine.py --mode rcp --N 5 --seed 0
python .\artifacts\rcp\checker.py .\artifacts\closed_loop_runs\rcp_N5_seed0\generated_artifact.json

python .\artifacts\common\closed_loop_reference_engine.py --mode rclm --N 5 --seed 0
python .\artifacts\rclm\checker.py .\artifacts\closed_loop_runs\rclm_N5_seed0\generated_artifact.json
```

This is a finite closed-loop certified reference instance under declared conditions. It is not full autonomous RSI, broad learned-agent entry, or empirical deployment validation.
