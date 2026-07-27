# Gate E executable contract

## Purpose

The Runtime v4 contract mirrors the Formal Core v4 deterministic bounded-search foundation.
It freezes the records required before the active `M4` package is permitted to run a
schedule-free Phase 14 search.

## Canonical report

`AutonomousSearchReport` binds:

```text
active source package hash
immutable history hash
post-freeze challenge commitment
false-valued forbidden-route-hint record
predecessor capability frontier
predecessor recursive-productivity frontier
ordered package-generated attempts
canonical enumeration hash
immutable total search budget
manual repair count
held-out visibility flag
promotion or exhaustion result
first accepted attempt index, when promoted
complete exhaustion certificate, when exhausted
```

Every report retains:

```text
gate_e_closed = false
phase14_exit_closed = false
```

## Attempt record

Each attempt binds:

```text
contiguous attempt index
package-selected objective
package-selected update kinds
program hash
realized candidate hash
Gate D certificate hash
active-package generation flag
independent evaluator verdict
complete rejection reason set
capability frontier after evaluation
recursive-productivity frontier after evaluation
search cost
canonical attempt hash
```

Candidate self-report is not an acceptance authority.

## Promotion validation

A promoted result is accepted only when:

```text
attempt indices are contiguous from zero
attempt hashes are unique
search cost is within budget
manual repairs = 0
held-out material visible before freeze = false
selected attempt is exactly the first accepted attempt
complete predecessor capability frontier is retained
capability frontier strictly expands
complete predecessor recursive-productivity frontier is retained
no exhaustion certificate is present
```

## Exhaustion validation

An exhausted result is accepted only when:

```text
no enumerated attempt is accepted
no selected attempt index is present
complete coverage is asserted for the declared bounded grammar
all attempts have rejection classifications
exhaustion enumeration hash equals the report enumeration hash
ordered exhaustion attempt hashes equal the ordered report attempt hashes
```

The certificate proves exhaustion only for the declared bounded grammar. It does not prove
that no acceptable successor exists outside that grammar.

## Deterministic references

The foundation contains two references:

```text
promotion reference:
  attempt 0 rejects for protected-capability regression
  attempt 1 accepts
  capability frontier strictly expands
  recursive-productivity frontier strictly expands

exhaustion reference:
  two package-generated attempts reject
  complete ordered exhaustion packet accepts
```

Both package-tool and repository-root entry points must emit byte-identical report and
validation JSON on Ubuntu, Windows, and macOS.
