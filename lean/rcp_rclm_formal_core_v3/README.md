# RCP/RCLM Formal Core v3 — Gate D foundation

This project begins **Gate D: learned capability-frontier RCLM refinement** while
preserving the complete pinned v2 Formal Core as an unchanged local dependency.

Gate D adds:

- a typed learned package state and learned package update surface;
- a finite certified capability frontier;
- explicit active-generator, proposal, and package-hash bindings;
- exact goal-drift and resource budgets;
- a selected information non-regression inequality;
- a learned checker that must refine the existing trusted RCP/RCLM checker;
- a one-step `LearnedAcceptedStep` theorem;
- finite strict frontier growth, including `|F_N| >= |F_0| + N`;
- inherited protected-loss, recovery, Lyapunov, trust, and domain results;
- a conditional infinite frontier-expanding trajectory theorem under an explicit
  frontier-expanding successor-availability premise;
- a concrete one-step reference over the existing Gate B RCLM architecture.

The project does **not** prove the successor-availability premise, general learned
proposal authority, strict useful improvement for arbitrary models, an LLM-scale
RCLM, or autonomous/unbounded RSI.

## Validation boundary

The Gate D branch remains an implementation under test until the pinned build,
forbidden-token scan, project-local-axiom scan, and public theorem axiom audit all
complete successfully at one exact branch head.

## Build

```bash
cd lean/rcp_rclm_formal_core_v3
lake update
lake exe cache get
lake build
```

## Dependency boundary

```text
RCP/RCLM Formal Core v2
  unchanged theorem and selected reference foundation

RCP/RCLM Formal Core v3
  Gate D learned capability-frontier refinement
```
