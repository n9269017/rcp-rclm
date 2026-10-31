# Runtime v5 development — Phase 17A controller foundation

This is public implementation work, not the archived `v5-trajectory` roadmap
release and not a completed Phase 17 result. The first slice implements a
present-only, resumable finite-search controller and its Phase 16 grammar/ranker
adapter. It does not yet implement the complete autonomous successor loop.

## Run the tests

From the repository root, with Python 3.11 or later:

```sh
python scripts/run_phase17_tests.py
```

No GitHub CLI, network access, pretrained download, or package installation is
needed for these focused tests when the complete repository is checked out.
`--core-only` runs only the control-plane tests and is not integration evidence.

## API and trust boundary

`bind_phase16_search` snapshots a supplied Phase 16 `ModelState`, reuses its
unchanged 32-program grammar and inherited ranking function, and returns the
exact candidate-to-program mapping plus a frozen `SearchPrefix`.

`decide(prefix)` has no future horizon, successful stopping time, next-family
schedule, terminal package, or evaluation seed argument. The first four
attempts preserve Phase 16 rejection-conditioned ranking; the remaining
attempts enumerate the frozen grammar without repetition. An evaluator call
consumes one candidate credit. These credits do not measure CPU time, energy,
or total end-to-end verification cost.

`record_evaluation` binds a receipt to the current decision, predecessor, and
challenge commitment. A candidate-pass receipt yields
`await_root_verification`, **never promotion**. This module does not authenticate
an evaluator merely because it supplies a hash. The immutable verifier and
atomic promotion service must independently check the actual evidence.

A full rejected grammar yields a scoped enumeration record. A partial search
with no remaining credits yields `resource_exhausted`, not search exhaustion.
External stop and fail-closed safety halt are distinct. No terminal action
claims successful completion of the research phase.

Checkpoints use the existing Runtime v2 canonical JSON/hash implementation,
strict field sets, bounded histories, replay of every selection, and an
externally retained expected prefix hash. A hash supplied by an adversary along
with its own rewritten checkpoint is not an independent trust anchor.

## Remaining integration

Authenticated Phase 16 terminal bootstrap; objective selection; post-freeze
challenge-service isolation; actual independent evaluation and full-frontier
recertification; atomic promotion/rollback; durable cross-turn ledger;
resource-accounted continuation; pinned Lean bridge; multi-seed reference
campaigns; schema and adversarial closure remain outstanding.

```text
phase17_exit_closed = false
gate_e_closed = false
next_phase = 17
egc0_baseline_completed = false
```

The existing v4.6 code and historical v4.5/v5 releases are not rewritten by this
slice. EGC-0 follows Phase 17 development as requested, but must evaluate the
frozen Phase 16 lineage rather than select a better Phase 17 package afterward.
