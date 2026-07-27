# Gate E scope — constructive endogenous successor availability

## Purpose

Gate E addresses the remaining liveness boundary after the completed Gate D and
`M0 -> M4` Phase 13 closure.

The repository already contains a genuine self-hosted finite trajectory with model-weight,
memory/retrieval, generator/planner, and adapter/architecture/optimizer transitions. Gate E
does not replace or relabel that result. It removes the remaining host-specified successful
route.

The central question is:

```text
Can the active RCLM discover the next accepted successor without receiving
which objective, update family, exact program, candidate hash, new capability,
or final model identity must succeed?
```

## Formal move

Gate D assumes frontier-expanding successor availability:

```text
for every admissible invariant-preserving state,
an accepted learned successor exists.
```

Gate E introduces a deterministic bounded search over an active-package-generated finite
candidate enumeration. Search returns exactly one of:

```text
an accepted candidate selected in deterministic enumeration order; or
a proof-carrying exhaustion record classifying every enumerated candidate as nonaccepted.
```

Relative completeness is proved:

```text
if an accepted candidate occurs in the declared finite enumeration,
the bounded search returns an accepted candidate.
```

This is stronger than supplying a preselected accepted successor, but narrower than proving
universal successor availability.

## Immutable authorities

The following remain outside the learned package throughout Gate E and Phase 14:

```text
Lean kernel and pinned formal projects
root trust anchor
Gate D and Gate E trusted checkers
canonical serialization and hashing
held-out challenge and answer store
candidate realizer
rollback authority
promotion authority
immutable ledger
```

## Endogenous choices

The active package is permitted to choose:

```text
objective
candidate hypothesis
update classes
training, retrieval, or memory intervention
architecture or adapter mutation
resource request
experiment order
candidate ranking
response to rejection
whether to continue search or emit exhaustion
```

## Forbidden route answers

The package input must not contain:

```text
next successful transition index
required successful component set
accepted mutation-program bytes
expected candidate hash
expected new capability
expected final model identity
host-selected objective
```

## Recursive productivity

Gate E adds a second finite frontier:

```text
R(M) = independently certified recursive-improvement abilities of package M
```

Every accepted Gate E successor must retain the complete predecessor recursive-productivity
frontier. A named strict witness must be absent from the predecessor frontier and present in
the successor frontier.

## Current foundation claim

The initial Formal Core v4 slice proves:

```text
Gate E checker soundness
bounded-search soundness
sound search exhaustion
relative bounded-search completeness
nonstagnation or certified exhaustion
recursive-productivity retention
strict recursive-productivity witness validity
finite capability-frontier growth
finite autonomous search-resource bounds
constructive availability from accepted-candidate existence in the declared enumeration
conditional infinite autonomous trajectory existence
```

## Explicit nonclaims

This foundation does not yet establish:

```text
a schedule-free Phase 14 learned trajectory
generic accepted-candidate existence
generic successor availability
open-ended generator completeness
broad external usefulness
an empirically unbounded run
a mutable trusted checker
noncommuting quantum semantics
asynchronous daemon execution
```
