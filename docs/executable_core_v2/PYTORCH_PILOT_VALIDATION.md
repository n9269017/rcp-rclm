# First PyTorch pilot validation

## Validation state

The learned admission, rejection, atomic-promotion, rollback, and independent-replay
implementation is locally complete. Authoritative cross-platform and pinned-Lean closure
remains pending until the implementation is published and one exact branch head passes
the complete Phase 0–8 plus PyTorch-pilot workflow matrix.

## Local source and test evidence

```text
source-quality findings:          0
proposal/backend tests:          10 passed
admission/rejection/replay tests: 13 passed
total focused tests:             23 passed
```

The suite covers deterministic two-process training, one genuine update, strict request
and proposal parsing, predecessor immutability, host-owned Phase 6 selection, Phase 6
realization, exact integer evaluation, rollback, Lean/checker admission, atomic
promotion, objective rejection, Lean rejection, loaded-training-module rejection,
tampered candidate/evaluation rejection, strict report round trips, source guarding,
and zero-training independent replay.

## Accepted local fixture

```text
verdict:                       promoted
active package changed:        true
manual repairs:                0
fallback rollback verified:    true
host torch loaded:             false
host proposal backend loaded:  false
replay verdict:                accept
replay training invocations:   0
```

Retained hashes:

```text
predecessor package:
d1db95be5f3036d19ff643743043056094bf597fa78e0d211c8e2e72625f6776

promoted package:
925c9759b8a60ca0ba1fcf5a39c46f8dadb74dcf975f3ef3d965a80c0d8b1c23

controller report:
82c519f14eb05506009109e031d77c34409b43d4e99feb8815e8ea09dadb2230

attempt report:
a93b0b42f984867446fce8ed39855b7bec912e66921b7f3e10bae5a6f7cc3546

candidate package tree:
28b96ff071d1ad872d5f0a3d2fbd5ce13e35f332d57bb822d566e704808e81fd

combined evaluation:
cfb9a9bfc0b86ef0b8750ad558e0c3db6f4378656b6b5206c7d64cb7f368a8bb

exact model evaluation:
ea40deb6764e3d789104a55b6186869e50fe3a91a2aa5b77eef3bd1a8751eed0

replay report:
785a0d3f1d8bd8fa2eafee1dc8dea0a3374aa0e4d3eddc44c9b07b5b39bcfe17
```

The replay stages all pass and recompute proposal evidence, selection, realization,
evaluation, certificate, Lean semantics, checker semantics, resources, rollback, and
parent linkage with no training invocation.

## Rejected local fixture

```text
verdict:                    rejected
active package changed:     false
fallback rollback verified: true
manual repairs:             0
host torch loaded:          false
host backend loaded:        false

controller report:
d674816f8e67e0c8f59d066dd8d99fdba8730d846156fc749d2c00f138224c16

attempt report:
46ca9909aaedfc96c75024c8b612205025999c8f6477dc431d24615a894c1d87
```

The rejection uses altered evaluation labels to force failure of the exact learned-model
objective. Lean and checker admission are not evaluated and the active predecessor is
preserved.

## Pending authoritative evidence

The final record will add:

```text
exact implementation and final evidence heads
Phase 0–8 and PyTorch workflow IDs
Linux, Windows, and macOS results
pinned Formal Core and differential conformance result
pinned learned promotion and rejection hashes
training-source-absent replay result
artifact names and SHA-256 digests
generated-Lean source-gate result
```

No promotion or replay claim is made from the local fixture alone.
