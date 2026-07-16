# First PyTorch phase — deterministic learned-successor pilot

## Scope

This phase introduces PyTorch only as an optional **untrusted proposal backend** after
Executable Core v2 Phases 0–8. PyTorch, floating-point reductions, model scores,
optimizer state, and candidate declarations remain outside canonical serialization,
certificate arithmetic, KL/QRE bounds, trust validation, checker acceptance,
promotion, and replay.

The frozen pilot is deliberately small:

```text
model:                 CPU-only Linear(2, 2) classifier
training dtype:        torch.float64
package weight dtype:  canonical little-endian signed int64
quantization scale:    1,000,000
seed:                  1729
threads:               1
optimizer:             SGD, momentum 0, weight decay 0
optimizer steps:       exactly 1
learning rate:         exact policy value 1/4
training examples:     4
held-out examples:     4
GPU:                   forbidden
network:               forbidden
```

The training worker receives the frozen training split and a hash of held-out features,
but never receives held-out labels. A separate framework-independent evaluator receives
the held-out labels only after the candidate package exists.

## Trust separation

### Untrusted proposal process

```text
PyTorch runtime
training loss and gradients
optimizer implementation
float64 parameter values
quantization proposal
candidate-reported selection
candidate-reported acceptance
candidate-reported certificate
candidate-reported aggregate score
```

### Framework-independent host path

```text
strict request and proposal parsing
Phase 1 canonical JSON and hashing
raw tensor-byte SHA-256
host-constructed Phase 6 selection
Phase 6 isolated realization and rollback
exact integer held-out evaluation
host-constructed stability certificate
pinned Lean bridge
Phase 4 hardened checker
Phase 7 immutable promotion store
model-free independent replay
```

The host does not import PyTorch, `proposal_backend.py`, or the process launcher while
performing validation, evaluation, Lean/checker admission, promotion, or replay. The
launcher is imported ephemerally only to start the untrusted process, then removed from
the host module table and package attributes.

## Process isolation and failure behavior

The backend runs as a separate executable worker:

```text
python -I -B proposal_backend.py propose ...
```

The host supplies a canonical request, immutable predecessor payload, fresh output path,
CPU-only environment, fixed timeout, and captured stdout/stderr. The worker stages its
output and publishes atomically only after internal consistency checks pass.

A crash, timeout, PyTorch version mismatch, visible GPU, nonfinite loss, nonfinite or
missing gradient, gradient-bound overflow, unexpected tensor layout, predecessor
mutation, malformed request, output overwrite, or byte/time budget overflow is
nonaccepting.

Every candidate is generated twice in fresh processes. The host requires equal raw
stdout/stderr, equal source-guard evidence, equal proposal hash, and equal semantic output
tree before selection.

## Canonical model representation

The package source of truth is neither `torch.save` nor pickle. Parameters are quantized
to the frozen integer scale and serialized as raw little-endian signed int64 files:

```text
model/weights/linear.weight.bin
model/weights/linear.bias.bin
```

Each tensor record binds:

```text
name
shape
dtype
byte order
element count
byte length
raw-byte SHA-256
```

The model identity is a Phase 1 domain-separated canonical JSON hash of the architecture
and tensor manifest. PyTorch proposes float64 values, but cannot choose the canonical
bytes or hashes accepted by the host.

## Phase 6 realization and rollback

The host validates the proposal and independently constructs a strict
`Phase6SelectionRecord`. Candidate-reported selection fields are retained only as
untrusted evidence and are not consumed.

The genuine substantive operation is a changed file under:

```text
model/weights/
component kind: model_weights
```

Phase 6 then copies the predecessor into an isolated workspace, applies only the
host-selected writes, remeasures the candidate, records all before/after hashes, creates
the rollback archive, restores that archive independently, publicly verifies the
candidate package, and publishes it as `realized_unverified`.

## Exact model evaluation

The model evaluator imports no PyTorch. It reads signed int64 tensor bytes and computes
logits and predictions using Python integer arithmetic.

The frozen held-out result is:

```text
predecessor correct:       2 / 4
candidate correct:         4 / 4
protected class-0 correct: 2 / 2 before and after
```

The learned-candidate gate requires:

```text
candidate model hash differs from predecessor model hash
held-out correct count strictly increases
protected class-0 metric does not decrease
```

These are exact empirical package conditions. They are not represented as a new Gate
A/B/C theorem and do not replace the existing Lean/checker obligations.

## Lean and checker admission

After exact model evaluation passes, the host constructs the ordinary Gate B stability
certificate outside PyTorch. The candidate preserves the logical `target` state while
changing model weights. The pinned Lean bridge and hardened checker therefore verify the
existing formal stability obligations; they do **not** prove the empirical model score.

Promotion requires both independent gates:

```text
exact model objective/protected-metric gate
and
existing Lean plus hardened-checker stability gate
```

A failure in either gate is nonpromoting. The controller does not manually repair the
candidate and the active predecessor remains unchanged.

## Atomic promotion and independent replay

An accepted candidate is installed through the existing Phase 7 content-addressed
store, parent binding, append-only ledger, and atomic active-pointer replacement.

The learned replay path then recomputes, without rerunning training:

```text
retained two-process generator evidence
proposal validation
host selection
fresh Phase 6 realization
exact integer evaluation
host certificate
Lean source and source guard
Lean semantic verdict
hardened-checker semantic verdict
resource evidence
rollback restoration
promotion-parent linkage
```

Replay rejects if `torch`, the process launcher, or the proposal backend is loaded. The
pinned workflow physically removes `proposal_backend.py` and `process.py` before replay
and requires zero training/generator invocations.

## Local deterministic evidence

The completed local suite records:

```text
proposal/backend tests:          10 passed
admission/rejection/replay tests: 13 passed
source-quality findings:          0
accepted fixture:                 promoted
rejected objective fixture:       active package preserved
independent replay:               accept
training invocations in replay:   0
manual repair count:              0
```

Authoritative completion still requires one published exact head to pass Linux,
Windows, macOS, pinned Lean, all Phase 0–8 regressions, learned promotion/rejection,
training-source removal, independent replay, generated-Lean hygiene, and closure.

## Claim boundary

Even after closure, this pilot establishes only one deterministic CPU-only learned
successor example behind the existing trust boundary. It does not establish generator
trust, learned proposal authority, arbitrary learned-system refinement, open-ended
generator correctness, GPU reproducibility, LLM-scale training, strict useful
improvement at every recursive step, unbounded successor availability, general
noncommuting quantum semantics, external benchmark performance, or autonomous/unbounded
RSI.
