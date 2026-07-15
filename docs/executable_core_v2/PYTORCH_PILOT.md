# First PyTorch phase — deterministic learned-successor proposal pilot

## Scope

This phase introduces PyTorch only as an optional **untrusted proposal backend** after
Executable Core v2 Phases 0–8. It does not move PyTorch, floating-point reductions,
model scores, or optimizer state into the checker, canonical serializer, trust anchor,
promotion rule, or independent-replay source of truth.

The selected pilot is deliberately small:

```text
model:                 CPU-only Linear(2, 2) classifier
training dtype:        torch.float64
package weight dtype:  canonical little-endian int64
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

The one-step update starts from an immutable zero-weight predecessor. The training
worker receives the training split and a hash of held-out features, but not held-out
labels. A separate framework-independent evaluator receives the held-out labels only
after the candidate exists.

## Trust boundary

### Untrusted

```text
PyTorch runtime
training loss and gradients
optimizer implementation
float64 parameter values
quantization proposal
candidate-reported metadata
candidate-reported scores
```

### Trusted or trusted after existing validation

```text
Phase 1 canonical JSON and hash domains
raw file SHA-256
strict pilot request parser
framework-independent exact integer evaluator
Phase 6 selector record parser, realizer, rollback builder, and package verifier
Phase 7 promotion controller, when the later admission adapter is connected
Phase 8 replay boundary, when the later pilot replay adapter is connected
```

PyTorch output cannot contain an acceptance Boolean, certificate packet, or aggregate
score that is treated as evidence. Those proposal fields are fixed to `null`.

## Process isolation and failure behavior

The backend is an executable worker:

```text
python -m rcp_rclm_runtime.torch_backend.proposal_backend propose ...
```

The host starts it in a separate process with a fixed timeout, CPU-only environment,
captured canonical stdout, captured stderr, and a fresh output path. The worker writes
only to a temporary staging directory and publishes the output atomically after all
internal checks pass. A crash, timeout, nonfinite loss, nonfinite gradient, gradient
bound violation, version mismatch, visible GPU, unexpected tensor layout, byte-budget
overflow, time-budget overflow, predecessor mutation, or malformed request returns a
structured non-success result and leaves no published candidate output.

The reference runner executes two fresh proposal processes and requires byte-identical
process results and semantic output trees.

## Canonical model representation

The package source of truth is not `torch.save` and not a Python pickle. Each model
parameter is quantized to a frozen integer scale and serialized as raw little-endian
signed int64 bytes:

```text
model/weights/linear.weight.bin
model/weights/linear.bias.bin
```

The manifest records, for every tensor:

```text
name
shape
dtype
byte order
element count
size in bytes
raw-byte SHA-256
```

The model hash is the Phase 1 domain-separated canonical JSON hash of the architecture
and tensor manifest. Phase 6 receives explicit write operations with raw content hashes;
it independently rebuilds the candidate tree and does not trust the backend's model
hash declaration.

## Complete proposal artifact

The proposal contains:

```text
proposal.json
phase6_selection.json
manifest.json
files/model/architecture.json
files/model/weights_manifest.json
files/model/weights/linear.weight.bin
files/model/weights/linear.bias.bin
files/model/optimizer_manifest.json
files/model/training_data_manifest.json
files/model/rng_manifest.json
files/model/training_command.json
files/model/resource_usage.json
files/model/evaluation_request.json
files/model/rollback_binding.json
```

The Phase 6 selection contains only operations whose bytes genuinely differ or are new.
The changed weight file is classified as `model_weights`, which is already a substantive
Phase 6 component kind. Unchanged architecture and bias bytes are not falsely listed as
modified files.

## Independent evaluation

The authoritative pilot evaluator does not import PyTorch. It reads the quantized int64
candidate directly and evaluates logits with Python integer arithmetic. The frozen
held-out result is:

```text
predecessor correct: 2 / 4
candidate correct:   4 / 4
protected class-0:   2 / 2 before and after
```

The pilot evaluation conditions are therefore:

```text
held-out correct count strictly increases
protected class-0 recall does not decrease
candidate model hash differs from predecessor model hash
```

These exact empirical conditions are an admission precondition for the later promotion
adapter. They are not represented as a new Gate A/B/C theorem and are not substituted
for the existing Lean/checker obligations.

## Phase 6 alignment

The reference runner constructs an actual verified Phase 6 predecessor package, adds
the immutable predecessor model before measurement, runs the untrusted proposal twice,
parses the produced `Phase6SelectionRecord`, and invokes the existing Phase 6 package
builder. The resulting candidate package records:

```text
actual changed files
before/after hashes
commands and environment
resource usage
substantive model_weights change
canonical rollback archive
independently restored predecessor tree
candidate manifest and payload-tree hash
```

The framework-independent evaluator then reads the model bytes from the actual realized
candidate package rather than from in-memory PyTorch tensors.

## Current boundary

This first implementation round establishes:

```text
verified predecessor package
→ isolated untrusted PyTorch proposal
→ exactly one genuine weight update
→ deterministic integer weight package
→ Phase 6 candidate realization
→ exact held-out evaluation
→ protected-metric non-regression
→ verified Phase 6 rollback
```

It intentionally does not yet claim:

```text
PyTorch-specific promotion
Phase 7 learned-backend controller admission
Phase 8 generator-free replay of a promoted learned package
formal proof of the empirical model objective
arbitrary learned-system refinement
GPU determinism
LLM-scale training
open-ended generator correctness
```

The next closure work for this pilot is the narrow admission adapter that combines the
exact model evaluator with the unchanged pinned Lean and hardened-checker path, followed
by promotion/rejection and independent replay of the retained learned candidate.
