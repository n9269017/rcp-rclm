# Phase 5A deterministic reference-generator validation

## Clean implementation head

The bounded Gate B reference generator, separate-process replay, pinned Lean path, and
Phase 4 hardened-checker integration passed the complete validation matrix at:

```text
validated implementation head:
ca6b7edd7df34b479be031c8cd87104db67614e9

Phase 5A workflow run:
29309437018

result:
success
```

The same implementation head also passed the Phase 0, Phase 1, Phase 2, Phase 3, and
Phase 4 authoritative workflows:

```text
Phase 0: 29309437001 — success
Phase 1: 29309436998 — success
Phase 2: 29309437021 — success
Phase 3: 29309437007 — success
Phase 4: 29309437036 — success
Phase 5A: 29309437018 — success
```

## Cross-platform runtime results

Linux, Windows, and macOS each completed:

```text
Python compilation
source-quality validation
74 Phase 1 tests
19 Phase 2 tests
20 Phase 3 tests
10 Phase 4 tests
18 Phase 5A tests
two-case separate-process generator replay
artifact upload
```

The source-quality scan covered 103 Python files and reported zero issues.

The process suite established, for both the `initial` and `target` seed states:

```text
separate worker process exit code: 0
worker standard error: empty
worker source guard: clean
first and second output bytes: identical
first and second parsed proposals: identical
first and second process reports: identical
proposal validation: pass
candidate successor fields consumed by worker: false
certificate fields consumed by worker: false
acceptance fields consumed by worker: false
```

## Bounded grammar results

The exact finite mapping exercised was:

| Seed state | Generated word | Witness | Proposal | Host-built certificate | Selected update | Host-derived successor | Resource units |
|---|---|---|---|---|---|---|---|
| `initial` | `improve` | `strict_improvement` | `improve` | `improvement` | `improve` | `target` | 1 |
| `target` | `stabilize` | `stable_continuation` | `stabilize` | `stability` | `stay` | `target` | 0 |

Both requests used word depth one, proof length one, and a maximum of one proposal.
The worker output contained no candidate, successor, certificate, checker verdict, or
acceptance Boolean.

## Pinned Lean and checker path

The pinned Linux job completed:

```text
Formal Core v2 build: 2636 jobs, success
Phase 2 differential cases: 10/10
Phase 2 accepting references: 4
Phase 2 rejecting mutations: 6
Phase 2 Python/RCP/RCLM agreement: complete
Phase 5A generated transitions: 2
Phase 5A Lean bridge acceptances: 2/2
Phase 5A hardened checker acceptances: 2/2
generated-source admission/local-axiom scan: success
workflow closure: success
```

For each Phase 5A transition the retained evidence includes:

```text
canonical generator input
first and second raw generator stdout/stderr
first and second process reports
worker source-guard evidence in the structured loop report
validated untrusted proposal
host-owned certificate-construction result
host-owned selection result
host-derived realization result
generated Lean source and source-guard report
Lean compiler stdout/stderr and structured verdict
Phase 4 hardened checker report
canonical artifact hashes
final reference-loop report
```

## Artifact digests

```text
final workflow closure
  runtime-v2-phase-5a-final-29309437018-1
  sha256:6301c4476ecf653f0eebda02c6b3c9b1cff7ee97431bf30192bbf59b7751701b

pinned Lean and end-to-end reference-loop evidence
  runtime-v2-phase-5a-lean-29309437018-1
  sha256:4dce3c45b8f5975bd9c23ab8f522929987d8b70a916c5e9030afd8663d82ae8a

Ubuntu generator evidence
  runtime-v2-phase-5a-ubuntu-latest-29309437018-1
  sha256:383b6424920102d20647799261b59a77ff577a2d237e251472ff6b669023e601

Windows generator evidence
  runtime-v2-phase-5a-windows-latest-29309437018-1
  sha256:19c865067275c289fc77826efd68f2885cc00ed290d983d0ea8af7ab8f389f5a

macOS generator evidence
  runtime-v2-phase-5a-macos-latest-29309437018-1
  sha256:7546cd2ea7677d315e06b85a07e1cfbb4edfdbe4177aad6c612ee9d3e1938975
```

## Interpretation

This closes the deterministic reference-generator implementation at the declared Gate
B bounded seed-library scope. It establishes that an immutable predecessor view can be
passed to an untrusted separate-process proposal worker, replayed deterministically,
validated, converted into a host-owned certificate and selected update, logically
realized into a successor, verified by pinned Lean, and accepted by the Phase 4
hardened checker without consuming a manually authored successor or hidden success
Boolean.

The process boundary is capability-minimized through a strict schema, a frozen AST
source guard, isolated Python mode, a fresh empty working directory, a minimized
environment, and no granted file arguments, network endpoints, or write handles. It
is not a claim of a universal operating-system sandbox for arbitrary future generator
code.

A clean Phase 5A closure licenses Phase 5B untrusted open-ended generator experiments
and Phase 6 filesystem realizer/package-builder development. It does not make a
generator trusted and does not authorize candidate promotion.
