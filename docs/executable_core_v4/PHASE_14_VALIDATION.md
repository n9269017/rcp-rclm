# Phase 14 validation

## Permanent workflow

The permanent workflow is:

```text
.github/workflows/runtime-v4-phase-14.yml
```

It performs:

1. three-platform compilation, source-quality validation, focused tests, and schema checks;
2. exact-head authoritative capture from the retained certified Phase 13 trajectory;
3. pinned Lean evaluation of the schedule-free campaign;
4. content-addressed bundle construction;
5. the selected adversarial suite;
6. pinned worker-free replay on Ubuntu, Windows, and macOS; and
7. final Draft 2020-12 closure aggregation.

## Deterministic entry points

```text
python/rcp_rclm_runtime_v4/tools/run_phase14_trajectory.py
python/rcp_rclm_runtime_v4/tools/build_phase14_bundle.py
python/rcp_rclm_runtime_v4/tools/replay_phase14_bundle.py
python/rcp_rclm_runtime_v4/tools/run_phase14_attacks.py
python/rcp_rclm_runtime_v4/tools/close_phase14.py
python/rcp_rclm_runtime_v4/tools/validate_phase14_schema.py
```

Repository-root mirrors are retained under `scripts/`.

## Schemas

```text
phase_14_trajectory.schema.json
phase_14_bundle.schema.json
phase_14_replay.schema.json
phase_14_attack_suite.schema.json
phase_14_closure.schema.json
```

All schemas use JSON Schema Draft 2020-12. Canonical report or manifest hashes are recomputed after schema validation.

## Local portable result

The source was exercised locally against the retained certified `M4` artifact before publication. The portable result produced four promotions, two rejections, all four update families, a capability frontier of eleven, a recursive-productivity frontier of eight, a worker-free replay with nine immutable packages and sixty-two task replays, and ten successful adversarial rejections. Local development omits the pinned Lean executable; authoritative CI must replace every simulated outer-envelope result with the real pinned verifier before closure.

