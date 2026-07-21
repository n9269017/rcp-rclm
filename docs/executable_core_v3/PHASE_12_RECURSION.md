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

### Fail-closed first rejection

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

## Phase 12B — first accepted recursive successor

The second slice resumes from the same unchanged generation-2 package. The fresh invocation is
bound to the Phase 12A draft invocation, its fail-closed validation report, the unchanged active
state, the first transition in the frozen component schedule, and the original total budget.

The installed planner has an explicit `fresh_proposal_after_rejection` capability. It projects the
active package's rejected draft onto transition zero of the precommitted schedule and emits the
canonical typed mutation program:

```text
V1;O=F;U=W;D=A;A=N;R=1,0,1,96,1,1;E=W;B=X;G=2;P=2
```

The authoritative proposal relation is therefore package-bound to both installed generation-2
components:

```text
proposal source = active generation-2 generator plus active generation-2 planner
selected update = model_weights only
successor generator generation = 2, unchanged
successor planner generation = 2, unchanged
manual repair = 0
held-out material visible = false
```

The proposal is recomputed twice and must be byte-identical. The active package tree is unchanged
by proposal generation.

### Selected M0 to M1 capability

The first accepted successor adds one sparse model-weight chain for a new held-out Lean task:

```lean
import Mathlib

macro "q" : tactic => `(tactic| omega)

example (n : Nat) : n <= n := by
  q
```

The held-out task ID is:

```text
lean.phase12.generation1.le_refl_macro
```

Training input exposes only a generic prompt hash, the marker token `T`, the completion token `q`,
and the selected transition pairs. The held-out task ID, prompt, Lean source, and reference answer
remain outside generator, planner, and training-worker access. Two isolated untrusted worker runs
must agree with host-exact tensor recomputation.

### Realization, verification, and frontier growth

The host builds `M1` through the inherited Phase 6 boundary. The realized candidate:

```text
changes only model_weights
retains the Phase 10 protected rfl task
retains the Phase 10 omega task
retains the Phase 11 z task
solves the new Phase 12 q task
preserves the generation-2 generator policy
preserves the generation-2 planner policy
has exact rollback to M0
```

The resulting frontier relation is:

```text
F0 = {
  lean.phase10.heldout.linear_gap,
  lean.phase10.protected.reflexive_seven,
  lean.phase11.heldout.add_zero_macro
}

F1 = F0 union {lean.phase12.generation1.le_refl_macro}

F0 subsetneq F1
|F0| = 3
|F1| = 4
```

The checker independently recomputes exact deterministic decoding, invokes pinned Lean after
candidate freeze, verifies all predecessor task certifications, certifies the new task, recomputes
selected token-density evidence, and requires:

```text
protected KL/QRE non-regression
strict positive new-task information witness
complete Gate D / Phase 9 transition acceptance
inherited Gate B Lean-bridge acceptance
hardened-checker acceptance
candidate immutability during verification
```

### Rejection ledger and first atomic promotion

The authoritative Phase 7 run first records the Phase 12A stale-generation proposal as a
non-promotion ledger entry. The active pointer remains on `M0`. The later accepted attempt then
promotes the realized `M1` package atomically with that unchanged active store package as parent.
The reopened immutable package must contain the expected semantic `M1` package and the unchanged
generation-2 generator and planner bytes.

The completed trajectory prefix records:

```text
generator invocations:   2
rejected attempts:       1
candidate realizations:  1
candidate evaluations:   1
accepted promotions:     1
frontier expansions:     1
manual repairs:          0
```

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

## Current claim boundary

The completed Phase 12 prefix now establishes:

```text
the promoted generation-2 successor has been used recursively
one package-generated recursive proposal was rejected fail-closed
one later fresh package-generated proposal was accepted
M0 -> M1 is a genuine model-weight successor
M1 retains all of F0 and adds one certified Lean capability
F0 subsetneq F1 and |F1| = 4
M1 is atomically promoted
held-out material consumed = false
manual repairs = 0
```

It does not yet establish:

```text
M1 -> M2 memory/retrieval promotion
M2 -> M3 generator/planner self-modification
M3 -> M4 architecture/optimizer promotion
the complete four-promotion M0 -> M4 chain
|F4| >= 7
generic frontier-expanding successor availability
an autonomous or unbounded RSI trajectory
```

The next slice must use the generator and planner inside promoted `M1` to produce the authoritative
memory/retrieval proposal for `M1 -> M2` under the remaining precommitted budget.
