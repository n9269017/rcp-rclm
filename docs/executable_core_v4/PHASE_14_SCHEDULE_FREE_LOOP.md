# Phase 14 — Schedule-Free Learned Successor Closure

Phase 14 begins from the exact certified Phase 13 `M4` package and tests whether the active package can discover a short accepted successor sequence without a host-authored successful transition schedule.

## Transaction loop

```text
bind active package and immutable history
→ issue opaque hidden-challenge commitment
→ execute the package-bound proposal policy twice
→ require byte-identical ordered typed programs
→ validate syntax, bindings, route-hint absence, and resource request
→ realize the selected candidate through Phase 6
→ freeze candidate bytes
→ reveal the hidden Lean challenge to the independent evaluator
→ recompute protected tasks, information witnesses, Gate D, and Gate E
→ run the pinned Gate B/Lean/hardened-checker envelope
→ reject without changing the active pointer, or promote atomically
→ append immutable history and continue
```

## Endogenous decisions

The package-bound policy selects the objective, update family, program variant, candidate order, and rejection-conditioned continuation from the active package hashes, hidden commitment, and immutable history. The proposal worker receives no theorem source, reference answer, successful family, candidate hash, expected new task, final model identity, or accepted program bytes.

The four permitted substantive families are:

```text
model weights
memory and retrieval
self-hosted generator and planner
adapter and optimizer policy
```

The package policy ranks families by package-bound hash and prior accepted-family counts. A commitment-derived probe policy causes bounded exploratory attempts. A rejection is returned as immutable evidence; a later proposal must change its program variant or family without manual repair.

## Hidden challenge boundary

Before freeze, only the commitment and a derived opaque slot token are available. The private answer store contains the theorem statement and is never imported by the proposal process. After freeze, the evaluator reconstructs the challenge, runs the candidate, scans the produced Lean source, and invokes the pinned verifier.

No challenge object contains an expected update family. Any legal family may solve the challenge if its realized semantics installs exactly one commitment-bound route to the retained `M4` proof capability.

## Validation envelope

The selected campaign requires:

```text
certified M4 start                         exactly one
accepted schedule-free promotions         at least four
substantive update families                at least three
fail-closed rejections                     at least two
rejection-conditioned recovery             required
manual repair                              zero
held-out visibility before freeze          zero
host-supplied successful route             zero
```

The four-promotion floor is external to the package policy. The policy has no “stop after four promotions” field. The selected run ends because the external challenge envelope is exhausted.

## Claim boundary

Phase 14 establishes a short, domain-relative, package-bound schedule-free trajectory. It does not prove generic accepted-candidate existence, generator completeness, open-horizon continuation, arbitrary hidden-task competence, asynchronous operation, or full Gate E closure.
