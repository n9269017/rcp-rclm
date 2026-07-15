# Phase 7 promotion-controller validation

## Validation state

The promotion-controller implementation is locally complete and has the authoritative
Phase 7 workflow, strict record schema, local deterministic evidence, generated-Lean
source scan, and closure job attached. Cross-platform and pinned-Lean closure remains
pending until one exact published head passes the full Phase 0–7 matrix.

The implementation under validation is based on:

```text
164e4138be8af4effc36e88a9d30b26d740e101f
```

Subsequent commits in PR #22 add only the missing validation, schema, workflow, and
status records unless a CI failure requires an executable repair.

## Local deterministic evidence

The exact branch source currently reports:

```text
Python files scanned: 161
source-quality issues: 0

Phase 1 tests:  74
Phase 2 tests:  19
Phase 3 tests:  20
Phase 4 tests:  10
Phase 5A tests: 18
Phase 6 tests:  22
Phase 7 tests:  17
```

The Phase 7 reference trajectory completed with fixture Lean evidence:

```text
root initial package
→ target plus a substantive verification-policy promotion
→ target plus a substantive memory-policy promotion
→ two rejected attempts after the finite grammar is exhausted
```

Its deterministic local bindings are:

```text
trajectory hash:
bb5440c2fc8abfa077ff500c19047305b417777accdd32c447185974755a092a

bootstrap package:
0a80ac68151d9c64915472b0611d983f01622988cc32187ce9ff822c343c1211

first promoted package:
29a6684c57a5f7dbe6919b942fe5f45ea305ba148411d550c781b5a844dcef10

second promoted package:
14ed1b50445e9d0f6444ebf7b1aa1a61acfe1e3a3c585ae8103f60bfb66c07d4

final active package after exhausted rejection:
14ed1b50445e9d0f6444ebf7b1aa1a61acfe1e3a3c585ae8103f60bfb66c07d4
```

The controller preserves raw generator input/output, process reports, proposal,
selection, Phase 6 realization evidence, objective evaluation, host-constructed
certificate, generated Lean source and source-guard report, Lean report, hardened
checker report, attempt report, package hashes, pointer state, ledger entries, resource
records, and rollback evidence.

## Exact-head workflow requirements

The authoritative Phase 7 workflow must pass all of the following at one head:

```text
Linux, Windows, and macOS compilation and Phase 1–7 regression
Phase 7 deterministic reference trajectory on all three platforms
complete pinned Formal Core build
all ten Phase 2 differential cases
both Phase 5A reference loops
both Phase 6 filesystem packages
real pinned-Lean Phase 7 promotion trajectory
generated Lean source admission/local-axiom scan
Phase 7 closure artifact
```

The final validation record must preserve the exact head, workflow IDs, test counts,
trajectory and package hashes, and platform/pinned/final artifact digests. Those fields
are populated only after the corresponding workflow completes; they are not asserted
self-referentially by the commit that triggers the run.

## Claim boundary

Before exact-head closure, this is an implementation candidate and does not license
Phase 8. After clean closure it supports only:

> A deterministic fixed-budget promotion and rollback controller for the declared
> finite Gate B reference path, with checker-owned acceptance, pinned Lean evidence,
> immutable parent-linked packages, append-only hash evidence, and fail-closed
> rejection behavior.

It does not establish independent replay, generator trust, open-ended-generator
correctness, learned PyTorch authority, external benchmark performance, general
noncommuting quantum semantics, or autonomous/unbounded RSI.
