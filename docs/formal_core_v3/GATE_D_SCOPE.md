# Gate D scope — learned capability-frontier RCLM refinement

## Purpose

Gate D replaces the informal phrase "strict useful improvement" with an explicit
finite capability-frontier obligation while preserving every accepted-step theorem
from Formal Core v2.

The central object is a finite set of independently certified tasks associated with
a learned package state. An accepted learned successor must retain the predecessor
frontier and strictly increase its cardinality.

## Formal base

Gate D imports the unchanged v2 theorem surface:

```text
RCP.Kernel
RCP.Candidate
RCP.StepObligations
RCP.TrustedChecker
RCP.RecoveryCompositionLaws
RCP.PreservationMonitors
RCP.FiniteAcceptedTrajectory
RCLM classical reference state, update, certificate, checker, and refinement
```

Gate D does not replace these objects. It adds learned-package and
capability-frontier obligations around them.

## Learned package surface

`Learned.PackageState` provides typed positions for:

```text
base theorem state
model architecture
model weights
generator
planner
training policy
retrieval policy
memory
tokenizer
verification-facing policy
resource policy
self model
finite capability frontier
```

The trusted checker and trust anchor are deliberately not fields of the learned
package. They remain external authority.

`Learned.PackageUpdate` provides typed positions for:

```text
base update
weight update
architecture update
generator update
planner update
training-policy update
retrieval update
memory update
tokenizer update
self-model update
```

## Capability frontier

For state `M`, Gate D supplies:

```text
frontier M : Finset Task
solves M q : Prop
```

and requires frontier soundness:

```text
q ∈ frontier M → solves M q
```

For predecessor `M` and candidate successor `M'`, strict expansion is:

```text
frontier M ⊆ frontier M'
card (frontier M) < card (frontier M')
```

The finite theorem derives:

```text
card (frontier M_0) + N ≤ card (frontier M_N)
```

for every accepted Gate D trajectory of length `N`.

## Generator and package binding

An accepted Gate D certificate binds:

```text
active generator
proposal produced by that generator
proposal to the actual candidate
active predecessor package hash
generator to that package hash
```

The formal relation does not trust a generator merely because the certificate names
it. The learned checker must prove every binding.

## Bounded obligations

Gate D adds:

```text
goalDrift M candidate ≤ goalDriftBudget M candidate
resourceUsed M candidate ≤ resourceBudget M candidate
informationValue candidate.next ≤
  informationValue M + informationBudget M candidate
```

The information orientation treats smaller values as better. A concrete learned
language-model refinement may later instantiate it with a selected KL/QRE distance
to a target distribution, using the exact or interval runtime semantics already
established by v2.

## Inherited obligations

Every accepted Gate D step still proves the complete base `RCP.StepObligations`:

```text
typed successor
residual nonpositivity
protected non-loss
constructive recovery
invariant preservation
progress nondecrease
strict progress when witnessed
trust validity
resource validity
reality containment
successor admissibility
```

Finite Gate D trajectories therefore inherit the existing protected-loss,
endpoint-recovery, Lyapunov/motion, ambiguity, relevance, trust, and domain results.

## Current concrete reference

The initial reference is a one-step refinement of the existing Gate B RCLM
improvement transition.

```text
initial frontier: {baseline}
target frontier:  {baseline, frontierOne}
active generator: boundedReference
proposal:         improve
package hash:     root
resource use:     1
resource budget:  1
goal drift:       0
information budget: 0
```

The reference proves one accepted learned step and one unit of frontier-cardinality
growth. It is a non-vacuity witness for the new theorem shape; it is not a learned
language model.

## Explicitly outside this Gate D foundation

The current foundation does not establish:

```text
an LLM-scale model package
an open-ended experiment planner
arbitrary task-verifier correctness
learned proposal authority
generator self-modification
a multi-generation self-hosted chain
frontier-expanding successor availability for every state
strict usefulness outside the declared certified-task semantics
full Paper I or Paper II semantic equivalence
general noncommuting quantum semantics
autonomous or unbounded RSI
```
