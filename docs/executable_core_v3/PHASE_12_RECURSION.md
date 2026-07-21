# Phase 12 — self-hosted multi-generation recursion

## Purpose

Phase 12 begins at merged Phase 11 commit
`5af6f68bc43c32ae5477d303c443b7159698eeed`. Phase 11 installed changed generation-2
generator and planner policies inside the promoted successor but deliberately did not claim that
those policies had produced another proposal.

The complete Phase 12 target is the finite self-hosted chain:

```text
M0 -> M1 -> M2 -> M3 -> M4
```

with four consecutive accepted learned promotions. For every accepted transition, the active
package's own generator and planner must produce the proposal used to construct the next
candidate. Every successor must retain the complete predecessor frontier and add exactly one
new independently certified Lean task.

## Precommitted trajectory contract

The selected total budget is frozen before the recursive run:

```text
wall-clock seconds:       24
accelerators:              0
training steps:            4
model-generator calls:     6
output bytes:            576
candidate realizations:    4
candidate evaluations:     4
accepted promotions:       4
permitted rejections:      2
manual repairs:            0
```

The initial certified frontier has cardinality three. The target frontier has cardinality seven:

```text
|F0| = 3
|F4| >= 7
```

The selected component schedule is:

```text
M0 -> M1  genuine model-weight update
M1 -> M2  memory and retrieval-policy update
M2 -> M3  generator and planner self-modification
M3 -> M4  typed architecture or adapter and optimizer modification
```

The schedule is a selected executable contract, not a theorem that every admissible package has
such a successor.

## Phase 12A — recursive successor-generator start

The first slice reconstructs the Phase 11 beta semantic package and binds it to the retained
Phase 11 closure manifest. The binding covers:

```text
Phase 11 exit closure
Phase 11 atomic promotion claim
beta package identity
beta model identity
successor generator-policy identity
successor planner-policy identity
```

The active generation-2 package is then opened read-only. The runtime verifies that its installed
generator policy:

```text
has generation 2
has next-proposal authority
is bound to the inherited Phase 11 typed-program protocol
cannot write a candidate directly
cannot see held-out material
```

The installed planner is likewise required to be generation 2 and bounded within the run.

The successor model deterministically emits:

```text
V1;O=F;U=WLCGP;D=A;A=N;R=1,0,1,96,1,1;E=WLCGP;B=X;G=2;P=2
```

This is a genuine recursive invocation: the proposal is generated from the model and policy
bytes inside the promoted generation-2 successor, not from the Phase 11 predecessor generator.
The exact decode is independently replayed.

## Fail-closed first rejection

The emitted program requests generator and planner updates while declaring successor generation
2 for both. The active package is already generation 2. The immutable Phase 12 validator
therefore rejects the proposal with exactly:

```text
PHASE12_GENERATION_NOT_ADVANCED
```

The rejection occurs before candidate realization. The package tree is hashed before and after
the invocation and must be byte-for-byte unchanged. It consumes:

```text
generator invocations:   1
rejected attempts:       1
candidate realizations:  0
candidate evaluations:   0
accepted promotions:     0
frontier expansions:     0
manual repairs:          0
```

This rejection is part of the Phase 12 trajectory budget. It is not counted as improvement.

## Trust boundary

The active package controls proposal bytes through its bound generator and planner policies. It
does not control:

```text
canonical serialization
package hashing
the Phase 6 realizer
pinned Lean verification
the hardened checker
promotion authority
the root trust anchor
the held-out answer store
the immutable ledger
```

Candidate self-report remains non-authoritative.

## Claim boundary

Phase 12A establishes:

```text
Phase 12 has begun
the promoted generation-2 successor is bound to retained Phase 11 evidence
the changed successor generator has been used recursively
its first proposal is model-generated and deterministically replayed
the stale generation request is rejected fail-closed
the active package remains unchanged
held-out material consumed = false
manual repairs = 0
```

It does not yet establish:

```text
an accepted Phase 12 promotion
a Phase 12 frontier expansion
the four-promotion M0 -> M4 chain
generic frontier-expanding successor availability
an autonomous or unbounded RSI trajectory
```

The next slice must produce a fresh rejection-conditioned proposal from the same active
successor under the original total budget and carry the first accepted Phase 12 successor through
realization, verification, and promotion.
