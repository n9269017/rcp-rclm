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

## Phase 12D generator/planner self-modification

The third accepted recursive transition validates:

```text
authoritative proposal source = generator/planner inside promoted M2
typed update = generator_policy plus planner_policy
successor policy generation = 3
training steps for transition = 0
five predecessor tasks retained
one new held-out Lean task certified
selected KL/QRE non-regression accepted
strict new-task information witness accepted
Gate D / Phase 9 transition accepted
M3 atomically promoted with M2 as parent
generation-3 proposal authority installed
accepted Phase 12 promotions = 3
rejected Phase 12 attempts = 2
frontier cardinality = 6
phase12_exit_closed = false
```

The exact code proof passed at:

```text
validated branch head:
3b432d29891340de4a8eb1abcc192df507226040

PR merge-test commit:
ec1022d0b35ba3e9d922c422e9c8dac24b95899e

workflow:
29886974524
```

Portable semantic bindings:

```text
proposal:
adae651dd468da9ba3e298483f1d20bca2a6d68952b03d3f9ba6870fbd6efa5e

proposal validation:
fc292c7421f5b6867708dc2373a68bcb89895f26de8b190f89b97b176003c6f4

semantic candidate:
9233b4e759df160009946ff0553169ee0a47925327778a044dc9b78057e8852d

candidate package:
e2d5acbf01f3f9bdb1eab556d8f215ccbaf4f72cf2bd543aae71864f6f4f7bc6

candidate model:
379021b5fee92acf5d03bd89ae564193aa21aab5622d687e3bf294d18cb9249f

Phase 6 lifecycle:
8e81b267735ea98a4c1d007ac887a289b5fb41b7e0633d75a885262d70462b3f

Gate D lifecycle certificate:
0dd6257d4b8020374ccafb3909ed7ad3e31df851903aa599f9783741fa2d8c8c

Gate D transition:
c73b41ae8b864cbc2dcf54c13e62b434fb595fcafd4fe5d71ec690829b45b9ec

portable summary:
9b266b55f19c55b72e71aa8e9f3ac21c9097326e160e592e4d2ae84bda2da1c3
```

Authoritative runtime bindings:

```text
reference:
aee26163af74b4e42bf0a56c462e912985407526e8f4395ddfc5142386f108bd

verification:
5b66b8fe7300d528fca93a04a203beae3dfe0d57bf84bebf85e3e60655f3f87e

promotion:
71e3b9e027d14fb80e736aa74806f64bbc7bdc046dbce30b6e135d86274d2c37

closure:
9106d70c9a683f1724c433b21ada901390d6befabf597e46e0b09c2a5971c3d4
```

| Evidence | Artifact ID | SHA-256 digest |
|---|---:|---|
| Ubuntu | `8516901165` | `sha256:6f0da783e2ba57580b3655b28cd7b1eafea0d8b0cc232d4be145abd0deafcd8c` |
| Windows | `8516950968` | `sha256:ed3606e171ac5aba5a6fa6fa876b5635a05d4b5bd739f1f99ba8e87434df7a15` |
| macOS | `8516911574` | `sha256:9431ee3cd06aaf975bb627ace41adba79bb96ee92ca4fb0ab305ca26858643b1` |
| Pinned promotion | `8517091551` | `sha256:7a6f5bd74ee340b023fc839f682bd15dd38e0da4e838c935bab9515de03e8b0d` |
| Final closure | `8517093451` | `sha256:0f2ab95d98f38ec96491278a8a70e054016d2b018056eff20324ef396e2252c8` |

## Evidence boundary

Portable Phase 12D identities stop at deterministic proposal reports, semantic generator/planner
policies, the semantic candidate, task frontier, information report, and Gate D correspondence.
Phase 6 environment identity, pinned verification, cumulative ledger entries, content-addressed
promotion records, installed policy-byte hashes, and immutable store package hashes remain attached
to the exact authoritative run.

The active semantic model package is nested inside the Runtime v2 Phase 6/7 transport package.
The semantic package parent relation and the Phase 7 content-addressed store parent relation are
both checked, but they are not conflated into one hash namespace.

## Claim boundary

A green Phase 12D workflow proves the third accepted self-hosted transition, generator/planner
self-modification, and strict frontier prefix:

```text
F0 subsetneq F1 subsetneq F2 subsetneq F3
|F3| = 6
```

It does not prove `M3 -> M4`, the full four-promotion chain, generic successor availability, or
autonomous/unbounded RSI. Those remain explicit open criteria in `PHASE_12_EXIT_CRITERIA.md`.
