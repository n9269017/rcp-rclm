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
Phase 11 closure manifest. The promoted generation-2 package emits:

```text
V1;O=F;U=WLCGP;D=A;A=N;R=1,0,1,96,1,1;E=WLCGP;B=X;G=2;P=2
```

This is a genuine recursive invocation: the proposal is generated from the model and policy
bytes inside the promoted generation-2 successor, not from the Phase 11 predecessor generator.
The program requests generator and planner updates while declaring successor generation 2 for
both. Generation 2 is already active, so the immutable validator rejects it with exactly:

```text
PHASE12_GENERATION_NOT_ADVANCED
```

The rejection occurs before candidate realization. The package tree remains byte-for-byte
unchanged. It consumes one generator invocation, one rejected attempt, and no realization,
evaluation, promotion, frontier expansion, or manual repair.

## Phase 12B — first accepted recursive successor

The second slice resumes from the same unchanged generation-2 package. The fresh invocation is
bound to the Phase 12A draft, its fail-closed validation report, the unchanged active state, the
first transition in the frozen component schedule, and the original total budget.

The installed planner projects the rejected draft onto transition zero and emits:

```text
V1;O=F;U=W;D=A;A=N;R=1,0,1,96,1,1;E=W;B=X;G=2;P=2
```

The proposal changes only `model_weights`; the generation-2 generator and planner remain
unchanged. The new held-out task is:

```lean
import Mathlib

macro "q" : tactic => `(tactic| omega)

example (n : Nat) : n <= n := by
  q
```

with task ID:

```text
lean.phase12.generation1.le_refl_macro
```

`M1` retains all three tasks in `F0`, adds the new task, satisfies selected KL/QRE obligations,
passes Gate D / Phase 9, pinned Lean, and the hardened checker, and is atomically promoted. Thus:

```text
F1 = F0 union {lean.phase12.generation1.le_refl_macro}
F0 subsetneq F1
|F0| = 3
|F1| = 4
```

The Phase 7 ledger contains the Phase 12A rejection followed by the `M1` promotion. The active
pointer remains unchanged for the rejection and advances only after the accepted transaction.

## Phase 12C — memory and retrieval successor

The third slice uses the generator and planner inside promoted `M1` as the authoritative source
for both of its proposals. No fixed external proposal model replaces the active package.

### Second fail-closed rejection

The package-bound generation-2 planner first emits:

```text
V1;O=F;U=R;D=A;A=N;R=1,0,0,96,1,1;E=R;B=X;G=2;P=2
```

This program requests a retrieval update but omits the required memory-state update for
transition one of the frozen component schedule. The immutable validator rejects it with exactly:

```text
PHASE12C_COMPONENT_SCHEDULE_INCOMPLETE
```

The rejection occurs before realization and leaves `M1` unchanged. This is the second and final
rejected attempt permitted by the precommitted trajectory budget.

### Fresh memory and retrieval proposal

A fresh invocation consumes the retained rejection report and emits:

```text
V1;O=F;U=MR;D=A;A=N;R=1,0,0,96,1,1;E=MR;B=X;G=2;P=2
```

The proposal changes exactly:

```text
memory_state
retrieval_policy
```

It requests zero training steps. The compact model weights, tokenizer, architecture, adapter,
optimizer, generator, and planner remain unchanged.

### Selected retrieval-backed capability

`M2` installs one package-bound memory entry representing a previously certified order-tactic
route and one deterministic exact-marker retrieval rule. For the new query marker `U`, the
retriever returns that memory entry and routes decoding to the already certified `T -> q -> EOS`
model path. The held-out task is:

```lean
import Mathlib

macro "q" : tactic => `(tactic| omega)

example (n : Nat) : 0 <= n := by
  q
```

with task ID:

```text
lean.phase12.generation2.zero_le_macro
```

The predecessor `M1` has no retrieval rule for marker `U` and fails the selected task. The
candidate `M2` recomputes the package-bound retrieval hit, decodes `q`, and passes pinned Lean.
The memory and retrieval payloads contain no held-out task ID, prompt, source, or reference answer.
They bind only a route derived from the already certified `M1` frontier.

### Realization, verification, and second promotion

The host realizes `M2` through Phase 6 using explicit `memory_policy` and `retrieval_policy`
operations. The wrapper projections and the embedded learned-package manifests must agree, and
the rollback archive must restore `M1` exactly.

The verifier independently checks:

```text
all four F1 tasks retained
new retrieval-backed Lean task solved
model identity unchanged
memory state changed
retrieval policy changed
generator and planner unchanged
protected KL/QRE non-regression
strict positive new-task information witness
Gate D / Phase 9 changed_components = {memory_state, retrieval_policy}
pinned Gate B Lean bridge accepted
hardened checker accepted
candidate unchanged during verification
```

The second rejection is appended to the existing Phase 7 chain at ledger sequence three without
moving the active pointer. The accepted `M2` candidate is then promoted at sequence four with the
unchanged `M1` store package as parent. The reopened immutable package must contain the expected
memory and retrieval bytes and the unchanged generation-2 generator and planner.

The resulting frontier is:

```text
F2 = F1 union {lean.phase12.generation2.zero_le_macro}
F1 subsetneq F2
|F1| = 4
|F2| = 5
```

The cumulative trajectory prefix records:

```text
generator invocations:   4
rejected attempts:       2
candidate realizations:  2
candidate evaluations:   2
accepted promotions:     2
frontier expansions:     2
manual repairs:          0
```

## Phase 12D — generation-3 generator/planner successor

The third accepted transition begins from promoted `M2`. Its unchanged generation-2 generator and
planner produce the authoritative typed program:

```text
V1;O=F;U=GP;D=A;A=N;R=1,0,0,96,1,1;E=GP;B=X;G=3;P=3
```

The rejection budget is already exhausted, so this invocation must be accepted without a new
rejected attempt. The program changes exactly the generator and planner policy components, requests
generation 3 for both, uses zero training steps, and preserves the model, memory, retrieval,
architecture, adapter, tokenizer, and optimizer identities.

The selected new held-out task is:

```lean
import Mathlib

macro "q" : tactic => `(tactic| omega)

example (n : Nat) : n < n + 1 := by
  q
```

The generation-3 planner installs a deterministic route from marker `V` to the already certified
`U -> T -> q -> EOS` memory/retrieval/model path. The new generator and planner bytes are installed
inside the promoted `M3` package and are assigned next-proposal authority for `M3 -> M4`.

The resulting frontier relation is:

```text
F3 = F2 union {lean.phase12.generation3.lt_succ_planner_macro}
F2 subsetneq F3
|F2| = 5
|F3| = 6
```

The cumulative bounded trajectory prefix is:

```text
generator invocations:   5
rejected attempts:       2
candidate realizations:  3
candidate evaluations:   3
accepted promotions:     3
frontier expansions:     3
manual repairs:0
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

Candidate self-report remains non-authoritative. Memory and retrieval are candidate-controlled
semantic components, but the verifier recomputes their hashes, exact lookup behavior, decoded
output, task execution, and relationship to the predecessor frontier.

## Current claim boundary

The completed Phase 12 prefix now establishes:

```text
the promoted generation-2 successor has been used recursively
M0 -> M1 is a genuine model-weight successor
M1 -> M2 is a substantive memory/retrieval successor
M2 -> M3 is a substantive generator/planner self-modification
two package-generated attempts were rejected fail-closed
three later package-generated proposals were accepted
F0 subsetneq F1 subsetneq F2 subsetneq F3
|F3| = 6
M1, M2, and M3 are atomically promoted
generation-3 generator/planner proposal authority is installed in M3
held-out material consumed = false
manual repairs = 0
```

It does not yet establish:

```text
M3 -> M4 architecture/optimizer promotion
the complete four-promotion M0 -> M4 chain
|F4| >= 7
generic frontier-expanding successor availability
an autonomous or unbounded RSI trajectory
```

The final slice must use the newly installed generation-3 generator and planner inside promoted
`M3` to produce the authoritative architecture/adapter and optimizer proposal for `M3 -> M4`.
