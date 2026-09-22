# Phase 15 exit criteria

Phase 15 closes only when one exact source head satisfies every item below.

## Exact predecessor boundary

- The bootstrap archive has SHA-256 `2331d850f809f27d1ee1c99f9d0b2bf7b0c5a7767d215cfc1b7b4369647651d8`.
- The reopened Phase 14 bundle manifest hash is `401568424e0b9cae8e7b6c0806c201ec484eb66d718d4894f1e51fbf66f4f5dc`.
- The reopened Phase 14 trajectory report hash is `04f3e842cd89283a07bc93dc5f34978731b18541fce2d29ef48f3b3a6160b02c`.
- The initial active store package is the certified Phase 14 `M8` store.
- The initial semantic package hash is `8b47fc42da83fc75abfd74f755c3f2b609b023bae229f5f947ab499267d34310`.

## Dynamic challenge and training isolation

- Both candidates are completely trained, built, and frozen before private challenge generation.
- The training worker receives no held-out task ID, prompt, answer, or private challenge material.
- Two isolated executions of each selected training request produce byte-identical canonical output trees.
- Hidden tasks occupy a frozen novelty partition disjoint from the public curriculum.
- The predecessor is independently executed and fails every new dynamic task.

## Accepted transition

- Exactly one fail-closed candidate rejection is retained.
- The rejection preserves the active store pointer and requires no manual repair.
- Exactly one `M8 → M9` promotion is accepted and parent-linked.
- The accepted candidate solves both dynamic domains.
- All eleven predecessor capability tasks are independently recertified.
- The capability frontier grows from 11 to 13 tasks.
- The recursive-productivity frontier retains all eight predecessor abilities and adds three selected abilities.
- Base compact-transformer tensors and inherited adapters remain byte-identical.
- Phase 6 realization, rollback, Gate D, Gate E, pinned Lean, Gate B, hardened checker, and Phase 7 atomic promotion all accept.

## Worker-free replay

Ubuntu, Windows, and macOS each independently replay the retained bundle with:

```text
training invocations          0
candidate-builder invocations 0
proposal-worker invocations   0
generator invocations         0
planner invocations           0
manual repairs                0
```

Each platform reopens at least ten immutable packages, recertifies 22 protected-task executions, replays four dynamic-task executions, recomputes one Gate D transition, one Gate E report, and one pinned outer envelope, and agrees on all source, trajectory, bundle, store, and semantic-package identities.

## Adversarial closure

The attack suite must reject all twelve selected attacks, including route hints, pre-freeze challenge generation, private-answer substitution, hidden-material training, post-freeze decoder mutation, inherited-context substitution, protected-frontier regression, candidate-freeze substitution, unpinned replay, and private challenge imports in the worker.

## Sole closing authority

Trajectory, attack, and replay reports retain:

```text
phase15_exit_closed = false
gate_e_closed = false
next_phase = 15
```

Only the final three-platform aggregator may emit:

```json
{
  "accepted": true,
  "phase15_exit_closed": true,
  "gate_e_closed": false,
  "next_phase": 16
}
```
