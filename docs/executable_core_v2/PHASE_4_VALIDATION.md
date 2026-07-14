# Phase 4 adversarial and tamper-rejection validation

## First clean implementation validation

The hardened Phase 4 checker and deterministic adversarial suite passed their full
validation matrix at:

```text
validated implementation head:
4e4199e59989a829fb770556676c4e695c48ff9e

workflow run:
29298535864

result:
success
```

The successful workflow established:

```text
Linux source quality and Phase 1–4 tests: success
Windows source quality and Phase 1–4 tests: success
macOS source quality and Phase 1–4 tests: success
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
  runtime-v2-phase-4-final-29298535864-1
  sha256:b7ed3ba303311a30d3d0e66a841ff72ffe404d168f2f677c480bb7dcd85b5e23

pinned Lean revalidation
  runtime-v2-phase-4-lean-29298535864-1
  sha256:5003a7b2a9fb9f6282729d955df2ff7becdd7dddefdf4d7eb6065a144afb6c0f

Ubuntu checker and attack evidence
  runtime-v2-phase-4-ubuntu-latest-29298535864-1
  sha256:d45cb4a6e9e066585f7f73144a1cba51f9d8fe6122f60987f2e079671dd3a622

Windows checker and attack evidence
  runtime-v2-phase-4-windows-latest-29298535864-1
  sha256:248bb1b3629d10372981def0a8ecd4926c14fc549e3ae5466556e190475478f6

macOS checker and attack evidence
  runtime-v2-phase-4-macos-latest-29298535864-1
  sha256:066ac23cc9fc95c8489037f42e65728e0683c47e6111f9cf84e60798161566fe
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

The final documentation-only PR head is revalidated separately. Its exact workflow
identifier and artifact digests are recorded in the pull-request discussion rather
than embedded self-referentially in the commit that triggers those workflows.
