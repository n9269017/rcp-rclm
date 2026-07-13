# PyTorch entry criteria

## Position in the phase order

PyTorch is not part of the trusted numerical checker foundation. It enters only as
an optional untrusted proposal backend after the deterministic reference loop is
complete.

Required order:

```text
Phase 0 contract
→ runtime records and exact numeric bedrock
→ Lean conformance bridge
→ fail-closed checker
→ adversarial rejection suite
→ deterministic predecessor-driven reference generator
→ successor realizer and package builder
→ promotion and rollback controller
→ independent replay
→ PyTorch learned-successor pilot
```

## Preconditions

A PyTorch phase may begin only when all of the following are true:

```text
runtime checker has clean CI and differential Lean conformance
all acceptance reason codes are implemented
canonical serialization is cross-platform stable
adversarial rejection suite passes
reference generator is outside the checker trust boundary
promotion is atomic and has tested rollback
independent replay recomputes every accepted transition without the generator
resource accounting is independently measured
```

## Initial role

The first PyTorch component is an untrusted proposal backend that produces a real
changed model package. It does not decide acceptance.

The model package must record:

```text
architecture identifier
framework and version
device class
tensor names
tensor shapes
tensor dtypes
canonical tensor hashes
optimizer type and hyperparameters
optimizer-state hash
training-data manifest hash
train/validation split hash
random seeds
RNG states
number of steps
resource budget
actual resource usage
predecessor weight hash
candidate weight hash
rollback snapshot hash
```

## Deterministic pilot

The first learned-system pilot is limited to a small CPU-only model with:

```text
fixed architecture
fixed dataset and held-out split
fixed seed
fixed optimizer
fixed step count
fixed thread count
fixed resource budget
one genuine weight update
protected-metric nonregression requirement
held-out objective improvement requirement
exact package rollback
multiple independent reproductions
```

GPU execution and nondeterministic kernels are deferred until deterministic CPU
reproduction is established.

## Numeric authority

PyTorch tensors and reductions are not authoritative evidence for Gate B or Gate C
mathematical acceptance.

The checker independently converts required candidate evidence into:

```text
exact rational records
certified interval records
canonical hashes
```

A `torch.float32` score may guide proposal generation, but it cannot establish a
strict witness or non-loss inequality.

## Model package boundary

Every changed component that contributes to the successor must be inside the
semantic package hash boundary, including:

```text
weights
architecture configuration
training policy
optimizer policy
planning policy
retrieval policy
memory policy
verification policy
code-generation policy
```

An invocation of the same unchanged external model under a new successor ID is not
a substantive successor.

## Evaluation boundary

Training data and held-out evaluation data must be separated by committed content
hashes. The generator must not read held-out labels or reference answers.

The checker ingests raw evaluation output from an independent evaluator and rejects
candidate-reported aggregate scores without underlying evidence.

## Promotion rule

A PyTorch candidate is promoted only when the ordinary runtime acceptance predicate
passes. There is no PyTorch-specific bypass.

At minimum:

```text
candidate package hash changed
predecessor linkage valid
resource budget valid
held-out objective nondecreasing
strict objective improvement when claimed
protected metrics within non-loss bounds
RCLM-to-RCP package refinement consistent
Lean bridge passes for the formal reference evidence
rollback snapshot complete
```

## Deferred roles

The following are later phases:

```text
learned proposal ranking
learned experiment selection
learned planner
LoRA or adapter successor generation
optimizer-policy modification
architecture search
model-generated checker changes
model-generated promotion-rule changes
```

Changes to the checker or promotion rule require a new trust-boundary and contract
review before they can become active.
