# Phase 16 validation

## Permanent private workflow

```text
.github/workflows/runtime-v4-phase-16.yml
```

The workflow performs:

1. exact-head contract validation on Ubuntu, Windows, and macOS;
2. exact verification of the retained Phase 15 closure and full accepted bundle;
3. Python compilation, deterministic source-quality checks, and the focused Phase 16 test suite;
4. Draft 2020-12 validation of all Phase 16 schemas;
5. one authoritative multi-seed `8 → 16 → 32 → 64` capture, with the optional 100-promotion stretch campaign enabled;
6. twelve selected adversarial rejection cases;
7. complete worker-free replay on Ubuntu, Windows, and macOS; and
8. sole final Phase 16 closure aggregation.

## Deterministic entry points

```text
python/rcp_rclm_runtime_v4/tools/verify_phase16_bootstrap.py
python/rcp_rclm_runtime_v4/tools/run_phase16_campaign.py
python/rcp_rclm_runtime_v4/tools/run_phase16_foundation.py
python/rcp_rclm_runtime_v4/tools/run_phase16_capture.py
python/rcp_rclm_runtime_v4/tools/run_phase16_reference.py
python/rcp_rclm_runtime_v4/tools/replay_phase16_capture.py
python/rcp_rclm_runtime_v4/tools/run_phase16_attacks.py
python/rcp_rclm_runtime_v4/tools/close_phase16.py
python/rcp_rclm_runtime_v4/tools/validate_phase16_schema.py
```

Repository-root mirrors are retained under `scripts/`.

## Schemas

```text
phase_16_archive.schema.json
phase_16_attack_suite.schema.json
phase_16_bootstrap.schema.json
phase_16_campaign.schema.json
phase_16_capture.schema.json
phase_16_closure.schema.json
phase_16_fairness.schema.json
phase_16_foundation.schema.json
phase_16_replay.schema.json
```

Runtime validation goes beyond shape. It reconstructs legal grammars, inherited ranking traces, fair orders, hidden commitments, candidate executions, archive chains, successor states, frontiers, exhaustion certificates, and complete campaign/capture hashes.

## Development versus closure authority

Portable local success establishes that the deterministic implementation and reference campaigns are coherent. It is not the final closure authority. The authoritative source head must pass the permanent workflow, produce the retained capture, survive all selected attacks, and agree across the three independent replay platforms before the final aggregator may set `phase16_exit_closed=true`.
