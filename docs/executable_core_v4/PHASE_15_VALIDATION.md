# Phase 15 validation

## Permanent private workflow

```text
.github/workflows/runtime-v4-phase-15.yml
```

The workflow performs:

1. exact-head source-contract validation on Ubuntu, Windows, and macOS;
2. verification and extraction of the retained certified Phase 14 bootstrap archive;
3. pinned builds of Formal Cores v2, v3, and v4;
4. authoritative post-freeze dynamic `M8 → M9` capture;
5. bundle construction and twelve-case adversarial validation;
6. pinned worker-free replay on Ubuntu, Windows, and macOS; and
7. sole final Draft 2020-12 closure aggregation.

## Deterministic entry points

```text
python/rcp_rclm_runtime_v4/tools/run_phase15_trajectory.py
python/rcp_rclm_runtime_v4/tools/build_phase15_bundle.py
python/rcp_rclm_runtime_v4/tools/replay_phase15_bundle.py
python/rcp_rclm_runtime_v4/tools/run_phase15_attacks.py
python/rcp_rclm_runtime_v4/tools/close_phase15.py
python/rcp_rclm_runtime_v4/tools/validate_phase15_schema.py
```

Repository-root mirrors are retained under `scripts/`.

## Schemas

```text
phase_15_trajectory.schema.json
phase_15_bundle.schema.json
phase_15_replay.schema.json
phase_15_attack_suite.schema.json
phase_15_closure.schema.json
```

All schemas use JSON Schema Draft 2020-12. Runtime loaders recompute canonical hashes and derived acceptance predicates after shape validation.

## Portable development result

Before publication, the selected source was exercised against the exact retained Phase 14 bundle. The portable campaign produced one rejection, one promotion, both dynamic domains, a capability frontier of 13, a recursive-productivity frontier of 11, an independently verified predecessor failure on both new tasks, an unpinned semantic replay with ten immutable packages, and twelve successful adversarial rejections.

Portable local execution is not closure authority. Final replay must invoke the pinned Lean toolchain and agree across Ubuntu, Windows, and macOS.
