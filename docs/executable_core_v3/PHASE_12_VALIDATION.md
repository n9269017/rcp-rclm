# Phase 12 validation

## Phase 12A selected scope

The first Phase 12 validation surface checks one recursive invocation of the generation-2
successor installed by Phase 11. The portable reference must establish:

```text
retained Phase 11 closure manifest accepted
promoted beta package identity bound
promoted beta model identity bound
successor generator identity bound
successor planner identity bound
active proposal-protocol binding accepted
model-generated typed program emitted
deterministic replay byte-identical
stale generation request rejected
active package tree unchanged
held-out material consumed = false
manual repairs = 0
accepted Phase 12 promotions = 0
phase12_exit_closed = false
```

## Cross-platform workflow

`.github/workflows/runtime-v3-phase-12-recursion.yml` runs the Phase 12A reference on Linux,
Windows, and macOS. Each platform:

1. compiles the complete Runtime v3 source;
2. applies the deterministic source-quality gate;
3. validates the retained Phase 11 closure dependency without reclassifying runtime-bound
   Phase 11 evidence as portable;
4. runs the focused Phase 12 test suite;
5. recomputes the Phase 12A reference;
6. validates the Draft 2020-12 evidence schema and canonical summary hash;
7. executes the repository-root Phase 12 entry point;
8. requires byte-identical output from the tool and repository entry points;
9. uploads the complete portable evidence directory.

The terminal closure job emits:

```text
phase12a_recursive_start_closed=true
phase12_exit_closed=false
```

## Evidence boundary

The Phase 12A summary exposes only identities needed to bind the active semantic package and its
recursive proposal. It does not claim that environment-bound Phase 11 realization, ledger, or
promotion hashes are cross-platform identities. Those remain retained by the exact Phase 11 code
proof.

The first rejected Phase 12 program is not a candidate and therefore has no Phase 6, Lean,
checker, or promotion evidence. The absence of such evidence is part of the correct rejection
boundary rather than an omitted acceptance step.

## Non-circular exact-head binding

The source tree freezes the Phase 12A contract, implementation, schema, tests, and workflow. The
exact validated branch head, PR merge-test commit, workflow run, and artifact digests are recorded
in the pull-request description after one complete exact-head run. Those run identifiers are not
written back into the source and therefore do not trigger an evidence-binding loop.

## Claim boundary

A green Phase 12A workflow proves only the recursive-start slice. It does not prove the first
accepted Phase 12 successor or the four-promotion trajectory. Those remain explicit open exit
criteria in `PHASE_12_EXIT_CRITERIA.md`.
