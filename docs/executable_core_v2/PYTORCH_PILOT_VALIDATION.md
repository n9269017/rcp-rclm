# First PyTorch pilot validation

## Current state

The deterministic CPU-only proposal backend and framework-independent exact evaluator
are implemented on a dedicated branch. The reference path locally demonstrates:

```text
two fresh PyTorch proposal processes
one genuine SGD update per process
identical canonical proposal output
Phase 6 selection parsing
actual Phase 6 candidate package construction
exact held-out improvement
protected-metric non-regression
verified rollback restoration
```

The pilot is not yet closed. Cross-platform workflow evidence, the formal
Lean/hardened-checker admission adapter, learned-candidate promotion/rejection, and
independent replay remain pending.

## Local focused tests

```text
10 focused unit tests passed
```

The tests cover:

```text
one genuine weight update
exact held-out evaluation
protected-metric non-regression
strict Phase 6 selection parsing
substantive model_weights classification
predecessor immutability
held-out-label schema rejection
null self-certification fields
RNG reset and deterministic nonstochastic update
backend import without importing torch
existing-output protection
predecessor tensor tamper rejection
two-fresh-process deterministic output
```

## Local reference path

The local reference runner produced:

```text
predecessor correct count: 2 / 4
candidate correct count:   4 / 4
protected class-0 count:   2 / 2 before and after
proposal processes:        2
Phase 6 package built:     true
Phase 6 rollback verified: true
promotion attempted:       false
```

Exact CI heads, workflow IDs, artifact hashes, and final closure fields will be populated
only after the implementation is published and the authoritative workflow runs.
