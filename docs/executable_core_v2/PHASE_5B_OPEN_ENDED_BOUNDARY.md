# Phase 5B open-ended generator boundary

## Status

Phase 5B is not implemented in Phase 5A. This document freezes the boundary that any
future open-ended generator must satisfy.

## Candidate generator classes

Only after the deterministic reference generator is fully replayable may the proposal
interface be supplemented by:

```text
bounded or heuristic search
program synthesis
LLM or scaffold proposals
learned PyTorch policies
training-driven weight updates
```

These components remain untrusted regardless of proposal quality.

## Unchanged checker boundary

An open-ended generator may propose:

```text
update intent
candidate source edits or model-package edits
training or synthesis commands
resource request
untrusted diagnostic scores
```

It may not provide authoritative values for:

```text
accepted
certificate preserved
reality contained
strict improvement
recovery valid
trust valid
resource valid
parent linkage valid
Lean verified
```

The same framework-independent checker, pinned Lean bridge, package-integrity rules,
and fail-closed interval semantics remain authoritative.

## Required isolation

The Phase 5A Python audit hook is not sufficient containment for arbitrary model code,
native extensions, compilers, or training frameworks. Before Phase 5B can execute, the
controller boundary must provide operating-system isolation with at least:

```text
read-only predecessor mount
read-only public policy and declared task
fixed writable candidate workspace only
no checker-source mount
no trust-anchor mount
no promotion-ledger mount
no previous-manifest-history mount beyond the declared predecessor
no reference-answer mount
network disabled unless a future contract explicitly permits and records it
fixed CPU, memory, process, time, and storage budgets
complete command and environment recording
```

## Replay boundary

A Phase 5B proposal may be nondeterministic internally, but the raw proposal and all
inputs must be preserved. Later independent replay does not rerun the original
generator; it recomputes realization, evaluation, certificate construction, checking,
and Lean verification from the preserved proposal package.

## PyTorch boundary

PyTorch may be used only as an untrusted proposal backend after the deterministic
reference path is closed. It must not become the source of truth for canonical JSON,
hashing, KL/QRE bounds, trust validation, promotion, or replay. Native floating-point
model diagnostics cannot directly satisfy a mathematical certificate.

## Claim boundary

Adding an open-ended generator does not establish:

```text
generator soundness or completeness
arbitrary learned-system refinement
strict useful novelty
candidate promotion authorization
autonomous recursive self-improvement
unbounded RSI
```
