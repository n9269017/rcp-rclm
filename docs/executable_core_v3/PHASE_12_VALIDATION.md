# Phase 12 validation

## Phase 12A selected scope

The first Phase 12 validation surface checks one recursive invocation of the generation-2
successor installed by Phase 11. The portable reference establishes:

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

`.github/workflows/runtime-v3-phase-12-recursion.yml` validates that slice on Linux, Windows, and
macOS and emits `phase12a_recursive_start_closed=true` while retaining
`phase12_exit_closed=false`.

## Phase 12B selected scope

The second validation surface checks the complete first accepted recursive successor prefix:

```text
Phase 12A rejection retained
fresh rejection-conditioned proposal produced
proposal source bound to active generation-2 generator and planner
proposal replay byte-identical
selected update class = model_weights
held-out material consumed = false
manual repair count = 0
isolated duplicate training agrees with host-exact tensor bytes
Phase 6 realization succeeds
rollback restores M0 exactly
all three F0 tasks retained
one new held-out Lean task certified
selected KL/QRE non-regression accepted
strict new-task information witness accepted
Gate D / Phase 9 transition accepted
Phase 12A rejection written to immutable ledger
active pointer unchanged after rejection
M1 atomically promoted with unchanged M0 store package as parent
reopened immutable package contains the expected M1 semantic package
accepted Phase 12 promotions = 1
frontier cardinality = 4
phase12_exit_closed = false
```

The portable evidence summary binds the active generation-2 package, its fresh weight-only
proposal, the deterministic semantic candidate, the four-task frontier, the selected information
report, and the Gate D transition. Environment-bound Phase 6, pinned verification, ledger, and
promotion hashes remain attached to the authoritative run.

## Phase 12B workflow and code proof

`.github/workflows/runtime-v3-phase-12-first-promotion.yml` contains six independently visible
jobs:

```text
Ubuntu portable lifecycle
Windows portable lifecycle
macOS portable lifecycle
isolated untrusted training
pinned Lean, Gate D, hardened checking, rejection ledger, and atomic promotion
terminal Phase 12B closure
```

The final Phase 12B exact-head run passed at source head
`c23ab1d076087addbb9755f2845ef3c82bbd360e`, PR merge-test commit
`52c4c5c2b389e02af8aacb55bb7466fea410706f`, and workflow `29848641953`.
Its terminal record emitted:

```text
phase12b_first_promotion_closed=true
accepted_phase12_promotions=1
rejected_phase12_attempts=1
frontier_cardinality=4
manual_repairs=0
heldout_material_consumed=false
phase12_exit_closed=false
```

## Phase 12C selected scope

The third validation surface checks the complete memory/retrieval successor prefix:

```text
M1 generator and planner are the authoritative proposal source
retrieval-only proposal emitted and deterministically replayed
retrieval-only proposal rejected for incomplete component coverage
M1 package tree unchanged after the second rejection
fresh rejection-conditioned memory/retrieval proposal emitted
accepted program requests zero training steps
selected semantic changes = memory_state plus retrieval_policy
model identity unchanged
generator and planner unchanged
Phase 6 realization succeeds
wrapper memory and retrieval projections equal the embedded package manifests
rollback restores M1 exactly
all four F1 tasks retained
one new retrieval-backed held-out Lean task certified
selected KL/QRE non-regression accepted
strict new-task information witness accepted
Gate D / Phase 9 changed_components = {memory_state, retrieval_policy}
second rejection appended without moving the active pointer
M2 atomically promoted with unchanged M1 store package as parent
reopened immutable package contains the expected memory/retrieval bytes
accepted Phase 12 promotions = 2
rejected Phase 12 attempts = 2
frontier cardinality = 5
manual repairs = 0
phase12_exit_closed = false
```

The selected new task is:

```lean
import Mathlib

macro "q" : tactic => `(tactic| omega)

example (n : Nat) : 0 <= n := by
  q
```

The predecessor has no retrieval entry for query marker `U`. The candidate installs one
package-bound memory entry and one exact-marker retrieval rule that routes `U` to the already
certified `T -> q -> EOS` model path. The evaluator recomputes the retrieval hit, effective prompt,
model decode, Lean source, and verifier result after candidate freeze.

## Phase 12C workflow

`.github/workflows/runtime-v3-phase-12-memory-retrieval.yml` exposes five independently visible
jobs:

```text
Ubuntu portable lifecycle
Windows portable lifecycle
macOS portable lifecycle
pinned Lean, Gate D, hardened checking, second rejection, and M2 promotion
terminal Phase 12C closure
```

Every portable operating-system leg:

1. compiles the complete Runtime v3 and Phase 12 source;
2. applies the deterministic source-quality gate;
3. validates the retained Phase 11 closure dependency;
4. runs the complete focused Phase 12 test suite;
5. recomputes the Phase 12C reference;
6. validates the Draft 2020-12 schema and canonical summary hash;
7. executes the repository-root Phase 12C entry point;
8. requires byte-identical tool and repository-entry output;
9. verifies the cumulative budget and frontier boundary;
10. uploads the portable evidence directory.

The pinned closure job independently builds Formal Core v2 and v3, rejects admitted proofs and
project-local axioms, audits the inherited selected-information theorem surface, runs all five
Lean tasks, recomputes retrieval and information evidence, executes Gate D and the hardened
checker, reconstructs the Phase 12B store prefix, appends the second rejection at ledger sequence
three, and atomically promotes `M2` at sequence four.

The terminal record must emit:

```text
phase12c_memory_retrieval_promotion_closed=true
accepted_phase12_promotions=2
rejected_phase12_attempts=2
frontier_cardinality=5
manual_repairs=0
phase12_exit_closed=false
```

Exact source, merge-test, workflow, report, and artifact identities are recorded in the pull-request
description only after one complete exact-head run, avoiding an evidence-binding loop.

## Evidence boundary

Portable Phase 12C identities stop at deterministic proposal reports, semantic memory/retrieval
manifests, the semantic candidate, task frontier, information report, and Gate D correspondence.
Phase 6 environment identity, pinned verification, cumulative ledger entries, content-addressed
promotion records, and immutable store package hashes remain attached to the exact authoritative
run.

The active semantic model package is nested inside the Runtime v2 Phase 6/7 transport package.
The semantic package parent relation and the Phase 7 content-addressed store parent relation are
both checked, but they are not conflated into one hash namespace.

## Claim boundary

A green Phase 12C workflow proves the second accepted self-hosted transition and strict frontier
prefix:

```text
F0 subsetneq F1 subsetneq F2
|F2| = 5
```

It does not prove `M2 -> M3`, `M3 -> M4`, the full four-promotion chain, generic successor
availability, or autonomous/unbounded RSI. Those remain explicit open criteria in
`PHASE_12_EXIT_CRITERIA.md`.
