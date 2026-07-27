# Gate E executable validation

## Exact-source policy

Every Ubuntu, Windows, and macOS job checks out the exact branch head and records:

```text
source head
source tree
runner identity
Python version
```

The job rejects if the checked-out commit differs from the declared source head at either the
beginning or end of validation.

## Cross-platform validation surface

Each operating system performs:

```text
Runtime v2 canonical-foundation installation
Runtime v4 editable installation
Python compilation
source-quality validation
17 focused Gate E contract/adversarial tests
promotion reference through package entry point
promotion reference through repository entry point
exhaustion reference through package entry point
exhaustion reference through repository entry point
byte-identical entry-point comparison
promotion Draft 2020-12 schema and hash validation
exhaustion Draft 2020-12 schema and hash validation
exact source binding
```

## Promotion reference

The deterministic promotion reference contains two package-generated attempts:

```text
attempt 0:
  rejected for protected-capability regression

attempt 1:
  independently accepted
  selected as the first accepted attempt
  capability frontier strictly expands
  recursive-productivity frontier retains the predecessor and adds one witness
```

The validation record retains:

```text
manual repairs = 0
held-out material visible before freeze = false
route hints absent = true
gate_e_closed = false
phase14_exit_closed = false
```

## Exhaustion reference

The deterministic exhaustion reference contains two rejected package-generated attempts.
The exhaustion packet binds:

```text
canonical enumeration hash
ordered canonical attempt hashes
complete bounded-grammar coverage declaration
complete reason classification
absence of any accepted attempt
```

The result proves exhaustion only for the declared bounded enumeration.

## Adversarial tests

The focused suite rejects at least:

```text
forbidden host route hints
noncontiguous attempt indices
search-budget overflow
manual repair
held-out visibility before freeze
selection of an attempt other than the first accepted attempt
capability-frontier regression
absence of strict capability expansion
recursive-productivity regression
exhaustion containing an accepted attempt
exhaustion attempt-hash order mismatch
rejected attempt without a reason
candidate self-report substituted for package generation
```

## Canonical-hash validation

The schema validator independently recomputes:

```text
every attempt hash
enumeration hash
complete report hash
```

The manifest excludes itself from no hash relation: report hashes are computed from the
complete report object with only the `report_hash` field removed.

## Evidence identity

Exact final source head, workflow, three artifact IDs and digests, promotion/exhaustion report
hashes, and validation hashes are recorded in the pull-request evidence after the final
exact-head workflow is green.
