# Phase 11 — autonomous untrusted experiment planner and generator

## Status

Phase 11 closes the first bounded active-model experiment cycle. One active predecessor
package emits typed mutation programs, the immutable host rejects both an invalid proposal
and a realized regressing candidate, and a later fresh model-generated candidate is accepted
and atomically promoted. The promoted successor contains changed generation-2 generator and
planner policies.

The host-created active-generator bootstrap remains a separately declared starting-state
construction and is **not** counted as autonomous improvement. The first use of the changed
successor generator is intentionally reserved for Phase 12.

## Dependency and immutable authorities

Phase 11 starts from merged Phase 10 head:

```text
52acaa820d75380b8766a2d7f4f78226645acc1f
```

The Runtime v2 checker, pinned Lean projects, root trust anchor, canonical serializer,
package hashing, promotion authority, held-out answer store, and active ledger history remain
outside the learned package. A model may emit a typed mutation program, but it cannot write
directly into a candidate or alter those authorities.

## Active-generator bootstrap

The promoted Phase 10 package still described generator and planner policies as external
reference components. Phase 11 therefore installs one explicit bounded active package before
model proposal authority is granted.

The bootstrap:

1. retains the Phase 10 `rfl` and `omega` capabilities;
2. installs position-addressed proposal behavior in unused exact-integer transition columns;
3. installs active generator and planner policy artifacts;
4. binds package, model, state, generator, planner, objective, and proposal-protocol hashes;
5. leaves candidate construction and promotion entirely host-controlled.

The retained boundary is:

```text
host_installed_active_generator_bootstrap = true
bootstrap_counted_as_autonomous_improvement = false
```

## Typed mutation language

The selected model emits canonical ASCII:

```text
V1;O=<objective>;U=<updates>;D=<data>;A=<architecture>;
R=<wall,accelerators,steps,bytes,candidates,evaluations>;
E=<components>;B=<rollback>;G=<generator-generation>;P=<planner-generation>
```

The parsed object records:

```text
proposal objective
selected update classes
training policy
data selection
architecture mutation
resource request
expected affected components
rollback declaration
successor generator generation
successor planner generation
```

Whitespace, field reordering, duplicate or unknown codes, unsupported mutation classes,
noncanonical serialization, absent exact rollback, budget overruns, or active-package and
policy binding mismatches fail closed.

## Precommitted total budget

The selected Phase 11 trajectory uses one immutable ledger:

```text
wall-clock seconds per invocation:  1
accelerators:                       0
training steps per candidate:       1
output bytes per program:           96
model generator invocations:        3
candidate realizations:             2
candidate evaluations:              2
manual repairs:                      0
```

The invalid first proposal does not consume a candidate-realization slot. The alpha and beta
candidates consume the two declared realization and evaluation slots.

## Invocation 0 — invalid program rejected

The active model first emits:

```text
V1;O=F;U=V;D=A;A=N;R=1,0,2,96,1,1;E=V;B=X;G=1;P=1
```

The immutable host rejects it for:

```text
PHASE11_BUDGET_EXCEEDED
PHASE11_FORBIDDEN_UPDATE_CLASS
```

It requests two training steps against a one-step ceiling and attempts to mutate the
verification policy. No candidate is realized and the active package is unchanged.

## Invocation 1 — alpha candidate realized and rejected

After the first rejection, a fresh model invocation emits:

```text
V1;O=F;U=WLGP;D=A;A=N;R=1,0,1,96,1,1;E=WLGP;B=X;G=2;P=2
```

The host validates the typed program and realizes alpha through the inherited Phase 6
boundary. Exact rollback succeeds. Alpha solves the selected new Phase 11 task and retains
the Phase 10 `omega` task, but it changes the protected `R` transition so deterministic
tie-breaking no longer emits `rfl`.

The lifecycle verdict is therefore:

```text
candidate realized = true
rollback exact = true
new task solved = true
protected capability retained = false
verdict = reject
reason = protected_capability_regression
```

The rejection is written to the immutable Phase 7 ledger. The active package hash before
and after that rejection is identical.

## Invocation 2 — beta candidate accepted and promoted

A third fresh invocation is bound to alpha's rejection report and emits:

```text
V1;O=F;U=WLCGP;D=A;A=N;R=1,0,1,96,1,1;E=WLCGP;B=X;G=2;P=2
```

The added curriculum update removes alpha's protected-marker conflict while retaining the
new training signal. Beta is realized through Phase 6 and independently satisfies:

```text
exact rollback
protected rfl retention
Phase 10 omega retention
new Phase 11 Lean task certification
selected entropy/KL/diagonal-QRE non-regression
strict selected information witness
complete Gate D / Phase 9 transition acceptance
pinned Gate B Lean bridge acceptance
hardened checker acceptance
```

Phase 7 then atomically promotes beta. Its immutable promoted package has the unchanged
active predecessor as parent and ledger sequence number 2: one rejection followed by one
promotion.

## New selected Lean task

The new held-out task is:

```text
task ID: lean.phase11.heldout.add_zero_macro
model marker: S
model completion: z
```

The pinned Lean source is:

```lean
import Mathlib

macro "z" : tactic => `(tactic| simp)

example (n : Nat) : n + 0 = n := by
  z
```

The completion is generated by the candidate model and accepted only after independent Lean
execution. Candidate self-report is not authoritative.

## Installed successor policies

The accepted candidate changes and binds:

```text
model weights
adapter manifest
data curriculum
generator policy
planner policy
```

The promoted generator and planner policy bytes differ from the active predecessor's. Both
policies declare generation 2 and are verified inside the immutable promoted package.

This establishes self-hosting readiness, not recursive use. The next proposal must be emitted
by those installed generation-2 policies to satisfy the central Phase 12 condition.

## Held-out and trust boundary

No generator or training input contains the Phase 11 held-out task identifier, model prompt,
Lean source, expected completion, or reference answer. Candidate generation and training use
only the permitted training partition. Held-out evaluation begins only after candidate freeze.

The selected implementation remains bounded to the exact compact sparse language-model
profile and Lean theorem-completion class. It does not claim arbitrary native-float model
generation, generic successor availability, autonomous unbounded RSI, or an infinite learned
trajectory.
