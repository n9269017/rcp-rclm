# Phase 4 adversarial and tamper-rejection validation

## Clean strengthened implementation validation

The hardened Phase 4 checker and deterministic adversarial suite passed their full
validation matrix at:

```text
validated implementation head:
f6a0a852b71a0f347f75797248fd24f415b3b075

workflow run:
29299291191

result:
success
```

The successful workflow established:

```text
Linux source quality and Phase 1–4 tests: success
Windows source quality and Phase 1–4 tests: success
macOS source quality and Phase 1–4 tests: success
90 Python files with zero source-quality issues
Phase 1 tests: 74 passed
Phase 2 tests: 19 passed
Phase 3 tests: 20 passed
Phase 4 tests: 10 passed
27 first-class adversarial cases: success
27/27 deterministic two-observation replays: success
27/27 nonaccepting attack results: success
pinned Formal Core v2 build: success
10 generated Lean conformance cases: success
generated-source sorry/sorryAx/admit/local-axiom scan: success
workflow closure: success
```

## Attack-suite result

```text
case count:       27
passed cases:     27
failed cases:      0
all passed:      true
```

The suite includes malformed and unknown schemas, evidence removal, parent and
certificate replay, candidate-file and checker-manifest tampering, invalid numerical
inputs, selected Gate C scope violations, forged witnesses, insufficient interval
margin, resource and provenance attacks, and five generated-Lean source attacks.

The strengthened candidate-file attack substitutes a measured file record and also
recomputes the candidate semantic-tree hash. The hardened checker still rejects it
because the measured file-record set is independently recomputed from the canonical
candidate update and successor bytes.

Quantum and numerical rejection records use the runtime's actual structured error
codes, including `NUMERIC_INVALID` and `UNSUPPORTED_SCOPE`, rather than synthetic
case labels.

Each attack record contains its declared expectation, observed verdict and reason
codes, two canonical observation hashes, deterministic replay status, and
case-specific evidence.

## Pinned Lean revalidation

The same workflow rebuilt the pinned Formal Core v2 project and reran the complete
Phase 2 generated-source conformance suite. It retained the generated packets,
certificate source, source-guard reports, compiler reports, structured verdicts, and
bridge reports.

The post-generation scan rejected the workflow if any generated Lean file contained:

```text
sorry
sorryAx
admit
project-local axiom
```

The scan and all ten conformance cases passed.

## Artifacts

```text
final workflow closure
  runtime-v2-phase-4-final-29299291191-1
  sha256:8d4c0642984cbd678804bd21e1ef2ae175da11a40562656cf44d4278bd600ecd

pinned Lean revalidation
  runtime-v2-phase-4-lean-29299291191-1
  sha256:00f1b47454eb2d42cdf7896e4bc3ed6bcf70eb4e3237e491ca2988893db6da2c

Ubuntu checker and attack evidence
  runtime-v2-phase-4-ubuntu-latest-29299291191-1
  sha256:3bfe73dd94f0048082f2d415631bf66a39cf9904d2621c46bd586da5a6bcbff4

Windows checker and attack evidence
  runtime-v2-phase-4-windows-latest-29299291191-1
  sha256:5c33c1ca8575c13aeaf1374ebbb423396ef78129679bd7714a99370ac70e1b1e

macOS checker and attack evidence
  runtime-v2-phase-4-macos-latest-29299291191-1
  sha256:63834893f94e099810a4506b05264dc3e4a564cb9f893126e7160f5ef63a7277
```

## Interpretation

This closes the implementation at the declared finite Gate B binary and selected
commuting/diagonal Gate C scope, subject to an independently green final PR head.
The validated implementation demonstrates deterministic fail-closed rejection over
the frozen Phase 4 attack matrix. It does not prove resistance to every possible
future attack or arbitrary input grammar.

A clean Phase 4 closure licenses Phase 5A deterministic bounded reference-generator
development. It does not make the generator trusted and does not authorize candidate
promotion.

The final evidence-only PR head is revalidated separately. Its exact workflow
identifier and artifact digests are recorded in the pull-request discussion rather
than embedded self-referentially in the commit that triggers those workflows.
