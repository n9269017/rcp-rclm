# Phase 11A — active-model typed experiment proposal

## Status

Phase 11A installs the first bounded model-facing generator and planner surface over the
promoted Phase 10 compact model.  It demonstrates that the active predecessor model can
emit a typed mutation program, receive an immutable host rejection, and emit a fresh
program under the same precommitted budget.

The host-created bootstrap is recorded separately and is **not** counted as autonomous
improvement.  Full Phase 11 remains open until model-generated candidates are realized,
one candidate is rejected, a later candidate is accepted and promoted, and changed
generator/planner bytes are installed in that promoted successor.

## Dependency

Phase 11A starts from merged Phase 10 head:

```text
52acaa820d75380b8766a2d7f4f78226645acc1f
```

The Phase 10 model, tokenizer, architecture, protected tasks, selected information
semantics, Phase 6 boundary, Phase 7 store, hardened checker, canonical serializer, and
root trust anchor remain unchanged.

## Bootstrap separation

The Phase 10 package still described its generator and planner as external reference
policies.  Phase 11 therefore requires one explicit bootstrap step before an active model
can hold proposal authority.

The host installs a function-preserving active-generator package by:

1. copying the promoted Phase 10 learned package;
2. retaining the existing `rfl` and `omega` transition columns exactly;
3. writing two bounded proposal programs into previously unused transition columns;
4. replacing the generator and planner policy artifacts with active model-facing policies;
5. binding the proposal protocol into the Phase 9 self-hosting identity;
6. retaining the exact model package, tensor, support-artifact, and policy hashes.

This changes the package and model identities, but the closure record explicitly states:

```text
host_installed_active_generator_bootstrap = true
bootstrap_counted_as_autonomous_improvement = false
```

The bootstrap is a starting-state construction, not an accepted learned successor.

## Selected generator profile

The selected profile is:

```text
position_addressed_typed_mutation_v1
```

It is implemented inside the existing exact integer sparse execution surface.  Each
proposal position addresses one reserved model state token.  The canonical transition
scores produce one output byte with a strict positive margin.  `<eos>` terminates the
program.

This selected profile demonstrates model-owned proposal bytes.  It does not claim general
native-float transformer generation or unconstrained natural-language planning.

## Typed mutation grammar

The model emits canonical ASCII only:

```text
V1;O=<objective>;U=<updates>;D=<data>;A=<architecture>;
R=<wall,accelerators,steps,bytes,candidates,evaluations>;
E=<components>;B=<rollback>;G=<generator-generation>;P=<planner-generation>
```

The parsed object contains:

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

Whitespace, reordered fields, duplicate update codes, unknown codes, missing rollback,
noncanonical serialization, or binding mismatches fail closed.

## Fixed invocation budget

Both invocations use the same immutable budget:

```text
wall-clock seconds:  1
accelerator count:   0
training steps:      1
output bytes:        96
candidate count:     2
evaluation calls:    2
manual repairs:      0
```

The model may not write directly into a candidate package.

## Frozen authorities

The typed language cannot address:

```text
active ledger history
canonical serializer
hardened checker
held-out answer store
package hashing
pinned Lean project
promotion authority
root trust anchor
```

Tokenizer and verification-policy updates are also forbidden in the selected Phase 11A
surface.

## First model-generated proposal: rejected

The active model emits:

```text
V1;O=F;U=V;D=A;A=N;R=1,0,2,96,1,1;E=V;B=X;G=1;P=1
```

The immutable host rejects it for two independent reasons:

```text
PHASE11_BUDGET_EXCEEDED
PHASE11_FORBIDDEN_UPDATE_CLASS
```

The proposal requests two training steps against a one-step ceiling and attempts to
change the verification policy.  No active package mutation occurs.

## Fresh model-generated proposal: validated

The second invocation receives an observation hash containing the first validation report
hash.  The active model then emits a different program:

```text
V1;O=F;U=WGP;D=A;A=N;R=1,0,1,96,1,1;E=WGP;B=X;G=2;P=2
```

It requests:

```text
model-weight update
generator-policy update
planner-policy update
exact predecessor rollback
successor generator generation 2
successor planner generation 2
```

The host validates the program under the original budget.  No held-out task identifier,
prompt, source, or reference answer is visible to either invocation.

## Stable reference

The cross-platform reference binds:

```text
active package:
724fcda02a1124eeeb2f2c0207052d16705d6fdb95afc6b87a7f5e6b658e47c4

active model:
94a07482cf243964d54e6f9079103f7d1ca85745d351a0a28a9030cbb11ef023

active generator:
166966f0e0724c65f1137529fb774882cdeb88c2c1262ff243ad0709f8a12b8b

active planner:
6d3b7dff5117791ba50c7b0b89eddb07d8acaf1afb0deb56e32d06fcff55dff2

proposal protocol:
5fbf5cb884187dc37e492ce9cd0057f746d60138e9a542fa1723072a3914b7d8

Phase 11A summary:
fe32f0d879f26929505170fbf695657af02be623090cfc41b383aabc32e8312e
```

Ubuntu, Windows, and macOS produced byte-identical reference JSON.

## Claim boundary

Phase 11A establishes:

```text
active predecessor model generated proposal bytes      yes
proposal generated without held-out material            yes
one model-generated proposal rejected                   yes
fresh later typed program validated                     yes
same fixed budget retained                              yes
manual repair count                                     0
```

It does not yet establish:

```text
model-generated candidate realization
model-generated candidate rejection after realization
accepted and promoted model-generated candidate
changed generator/planner bytes in a promoted successor
recursive use of the modified successor generator
Phase 11 completion
```
