# Phase 14 trust boundary — schedule-free learned successor closure

## Starting state

Phase 14 begins from the independently closed Phase 13 `M4` package. The exact Phase 13
trajectory is historical evidence; it is not the successful route supplied to Phase 14.

## Immutable external authorities

```text
Formal Core v2, v3, and v4 Lean projects
Lean kernel and pinned dependency graph
root trust anchor
canonical serializer and hashing rules
Gate D hardened checker
Gate E autonomous checker
hidden challenge and answer store
candidate realizer
rollback service
promotion controller
immutable content-addressed store
hash-chained ledger
```

These components may reject an active-package proposal. They may not tell the package which
proposal will succeed.

## Active package authority

The active package may emit:

```text
objective declaration
search hypothesis
ordered typed mutation programs
update-family choices
training, retrieval, memory, planner, generator, adapter, architecture, tokenizer,
tool, resource-policy, or self-model operations allowed by the frozen grammar
resource request
candidate ranking
rejection-conditioned follow-up
search continuation or exhaustion request
```

## Host responsibilities

The host may:

```text
provide immutable active-package and history hashes
provide hidden challenge commitments
validate syntax and budget
realize candidates in isolated directories
freeze candidate bytes
invoke independent evaluators
verify and classify rejection
restore rollback snapshots
atomically promote accepted successors
advance one transaction at a time
```

The host may not:

```text
select the objective
select the successful update family
rewrite a model-generated program
repair a candidate
supply expected accepted bytes
skip earlier accepted attempts
change challenge answers after commitment
promote on candidate self-report
```

## Transaction order

```text
bind active state and immutable history
issue hidden challenge commitment
invoke active package
parse ordered candidate enumeration
validate route-hint absence
realize next legal attempt
freeze candidate
open hidden evaluation
run Gate D and Gate E verification
reject and append evidence, or atomically promote
repeat from the resulting active state
```

## Claim boundary

An external turn-based harness is retained. Phase 14 targets autonomous decision and route
selection, not asynchronous daemon execution.
