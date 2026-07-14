# Phase 5A deterministic reference-generator validation

## Clean executable implementation head

The complete bounded-generator implementation passed its authoritative validation
matrix at:

```text
validated implementation head:
d348a23690a76ecae6924e0a95c57a0513a5a96d

Phase 0 workflow:
29309422903 — success

Phase 1 workflow:
29309422887 — success

Phase 2 workflow:
29309422909 — success

Phase 3 workflow:
29309422959 — success

Phase 4 workflow:
29309422886 — success

Phase 5A workflow:
29309422906 — success
```

All six executable-core workflows completed successfully at that exact source head.

## Cross-platform runtime validation

The Phase 5A workflow passed on Linux, Windows, and macOS. Each platform completed:

```text
Python compilation
source-quality validation
Phase 1 regression
Phase 2 bridge regression
Phase 3 checker regression
Phase 4 hardened/adversarial regression
Phase 5A generator regression
separate-process generator replay evidence
artifact publication
```

The clean Ubuntu evidence recorded:

```text
Python files scanned: 104
source-quality issues: 0
Phase 1 tests:          74 passed
Phase 2 tests:          19 passed
Phase 3 tests:          20 passed
Phase 4 tests:          10 passed
Phase 5A tests:         14 passed
```

## Separate-process generator replay

Three canonical predecessor cases were executed twice in independent temporary working
directories:

| Predecessor | Expected result | Observed result | Deterministic replay |
|---|---|---|---|
| `initial` | generated `improve` proposal | generated | true |
| `target` | generated `stabilize` proposal | generated | true |
| `outside` | fail-closed rejection | `GENERATOR_PREDECESSOR_OUTSIDE_DOMAIN` | true |

The replay-suite record is:

```text
case count:              3
generated cases:         2
rejected cases:          1
all deterministic:       true
all expected:            true
suite SHA-256:
09cf162b67b82c25cdcd6a02acf7de502eb1561e104cccb8e2f02437bdf9e1e3
```

For the accepting cases, both worker executions produced byte-identical canonical
stdout hashes and identical parsed response hashes. The worker reports no checker,
trust-anchor, previous-manifest-history, promotion-ledger, or reference-answer input,
and its audit policy denies filesystem access after startup, sockets, and subprocess
creation.

## Direct Lean grammar conformance

Before checking either realized candidate, the workflow generated a dedicated Lean
conformance file for the bounded seed grammar. The source verified:

```text
initial packet word = improve
target packet word = stabilize
word depth = 1
proof length = 1
improve witness/proposal/certificate/candidate maps
stabilize witness/proposal/certificate/candidate maps
initial and target grammar membership
rejected-word exclusion at both states
```

The generated source passed the mandatory pre-compilation source guard and compiled
under the pinned Formal Core v2 toolchain:

```text
source SHA-256:
d57a2b4e9cc4ee3c975fbe04f065a68f481f908823c49d6af64ebb88c8172164

source-guard clean: true
Lean exit code:     0
Lean timed out:     false
conformance report SHA-256:
018685759aed2d8a3170d6a756a37f7210bb9df3aaf444326b5c3deae38f5a1b
```

The same job completed the full pinned Formal Core build:

```text
2636 jobs
Build completed successfully
```

## End-to-end reference transitions

### Initial-state transition

The worker emitted the untrusted word `improve`. Outside the worker, the runtime:

```text
constructed the canonical improvement certificate
selected the exact improve update
computed the successor as target
ran the candidate source guard
obtained agreeing Lean RCP and RCLM acceptance
obtained an accepting Phase 4 hardened-checker report
```

Evidence:

```text
generator replay deterministic: true
realized successor:              target
pipeline verdict:                accept
pipeline report SHA-256:
527d5c8939fba8e369555e41483dbe95c371cb9a6ed8d106ae7094fe32c68512
```

### Target-state transition

The worker emitted the untrusted word `stabilize`. Outside the worker, the runtime:

```text
constructed the canonical stability certificate
selected the exact stay update
computed the successor as target
ran the candidate source guard
obtained agreeing Lean RCP and RCLM acceptance
obtained an accepting Phase 4 hardened-checker report
```

Evidence:

```text
generator replay deterministic: true
realized successor:              target
pipeline verdict:                accept
pipeline report SHA-256:
06e9e57cbfe9d782eb3cb55f38677582550fa79e4195320cc857a522e25f8dee
```

The aggregate pipeline record is:

```text
direct grammar conformance: true
pipeline cases:             2
accepted cases:             2
all generator replays:      deterministic
all accepted:               true
suite SHA-256:
064fc3941f29a5e518bff0d26c0186073707e36f28a6612f95e6af2c36fbe105
```

Neither generator proposal contained a certificate, selected update, successor state,
checker verdict, Lean verdict, or promotion Boolean. Those values were independently
constructed or recomputed after the untrusted process exited.

## Generated-source hygiene

The workflow scanned both the direct grammar-conformance source and the generated
candidate certificate sources before closure. It failed if any generated Lean source
contained:

```text
sorry
sorryAx
admit
project-local axiom
```

All generated sources passed. The structured source-guard records also reject invalid
UTF-8 before compilation.

## Artifacts

```text
final workflow closure
  runtime-v2-phase-5-final-29309422906-1
  sha256:8372dfb031fd941e5bb4b522bfa7474fa1cc477f0b0e70e39179dc85b454bbdb

pinned Lean grammar and candidate pipeline
  runtime-v2-phase-5-lean-29309422906-1
  sha256:35c8111812efc84d24b63066355a831583bcd241f531ae54ad7f6a23e9c11e0f

Ubuntu generator and replay evidence
  runtime-v2-phase-5-ubuntu-latest-29309422906-1
  sha256:ab2604d396d4f09336f45508c6659bca02e15cf54f3aee28c8b008f48ba94e1b

Windows generator and replay evidence
  runtime-v2-phase-5-windows-latest-29309422906-1
  sha256:cc2427428398d6fd29d479197f2dbab8bda3e95a43324de6601ab0e9dbbe3245

macOS generator and replay evidence
  runtime-v2-phase-5-macos-latest-29309422906-1
  sha256:2404273cd53e72271735fcd09a9997fbb1034b0011c24d5e00cb8e3e579cfae4
```

## Interpretation and claim boundary

This validation establishes a finite executable instance of the compiled Gate B
classical bounded seed grammar through untrusted separate-process generation,
independent certificate construction, typed selection, computed realization, pinned
Lean verification, and the Phase 4 hardened checker.

It does not establish:

```text
generator intelligence, novelty, soundness, or completeness
open-ended search, program synthesis, or LLM/scaffold correctness
learned PyTorch policy or training-update correctness
Gate C bounded-generator refinement
generator trust
candidate promotion
production filesystem realization or rollback
independent replay without invoking the reference generator
external benchmark performance
general noncommuting quantum semantics
autonomous or unbounded RSI
```

A clean Phase 5A closure licenses Phase 5B open-ended **untrusted** generator
development and Phase 6 selector/realizer/package-builder development. It does not
authorize promotion and does not make any generator trusted.

The final documentation/evidence PR head is revalidated separately. Its exact workflow
identifiers and artifact digests are recorded in the pull-request discussion rather
than embedded self-referentially in the commit that triggers those checks.
