# Gate C scope — finite-dimensional quantum extension

## Status

```text
Planning placeholder: present
Lean implementation: not begun
Density-matrix theorem: not claimed
Quantum relative entropy theorem: not claimed
Channel recovery theorem: not claimed
Gate C closure: false
```

This document records the boundary that must be frozen before Gate C code is
written. It does not add a quantum theorem and does not strengthen Gate A or Gate
B.

The current Lean module:

```text
lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/QuantumFinite.lean
```

is intentionally empty apart from a scope declaration.

## Purpose

Gate C will instantiate the existing conditional RCP kernel with a nontrivial
finite-dimensional quantum reference. It must use actual matrix-valued states,
actual entropy or divergence quantities, an update tied to an admissible quantum
transition, constructive recovery, a non-vacuous strict-progress witness, and a
concrete checker refinement.

The quantum instance must refine the existing Gate A theorem interfaces rather
than bypass them with a separate theorem vocabulary.

## Decisions required before implementation

### State representation

Freeze one exact finite-dimensional representation, including universe and index
choices. The likely boundary is a complex square matrix on a finite index type,
but the implementation must name the exact mathlib type and imports.

Required state evidence:

```text
Hermitian
positive semidefinite
trace one
finite dimension
support/domain data needed by logarithms and relative entropy
```

The representation must distinguish raw matrices from certified density
operators.

### Admissible transitions

Freeze the update/channel representation and prove the exact laws needed by the
kernel:

```text
linearity
complete positivity or the selected finite equivalent
trace preservation
state-domain preservation
candidate next state agrees with applying the update
```

If a weaker transition class is selected for the first concrete instance, that
narrower scope must be explicit in the theorem map and claim boundary.

### Entropy and divergence

Freeze exact definitions for:

```text
von Neumann entropy
quantum relative entropy
support convention
zero/equality cases
nonnegativity or the exact imported theorem boundary
```

The core protected quantity may not be a constant. Any imported matrix logarithm,
functional calculus, spectral, trace, or positivity theorem must be listed by
exact module and reflected in the axiom audit.

### Protected distinctions and transport

Define theorem-relevant protected distinctions and their cross-time transport.
The instance must prove that the transport is tied to the selected update rather
than assigned independently.

The first Gate C reference may use a narrow commuting/diagonal class only if the
scope is stated as such and does not duplicate Gate B under a quantum label.

### Recovery

Define a candidate-indexed constructive recovery map tied to the actual quantum
transition. Freeze the intended theorem:

```text
local recovery bound
recovery composition laws
finite endpoint rollback bound
```

Any use of a Petz-style recovery map, explicit inverse channel, partial trace,
embedding, or restricted exact recovery must identify the domain and support
conditions precisely.

### Progress and strict witness

Define a progress functional that is not index growth and prove at least one
strict witness for an accepted quantum candidate:

```text
progress predecessor < progress successor
```

The witness must follow from the selected quantum information quantity or another
explicit theorem-relevant objective.

### Certificates, residuals, and checker

The concrete packet must include evidence for:

```text
typed transition
protected non-loss
constructive recovery
residual nonpositivity
trust validity
resource validity
reality/uncertainty containment
successor admissibility
strict witness when claimed
```

Residuals must be computed from actual state/candidate/certificate evidence and
must satisfy the existing input-sensitivity requirement.

Checker soundness must retain the form:

```text
check = true -> complete StepObligations
```

### RCLM refinement

Gate C must strengthen the RCLM-to-RCP refinement over the selected quantum
objects. It must identify the architecture state, update, certificate, monitor,
recovery, verifier, uncertainty, goal, resource, and checker objects that are
actually preserved.

The bounded seed-library interfaces may be reused only after the quantum packet
grammar and semantic identifications are explicit.

## Intended theorem boundary

The first defensible Gate C theorem should have the following conditional shape:

```text
given a certified finite-dimensional quantum predecessor,
an admissible candidate channel/update,
a quantum certificate packet,
protected distinctions and cross-time transports,
a constructive recovery map,
progress and strict-witness evidence,
trust/resource/reality evidence,
and a sound trusted checker,

checker acceptance implies the complete RCP successor obligations.
```

It must then instantiate the existing finite composition and conditional infinite
trajectory theorems. Infinite closure must continue to carry explicit successor
availability.

## Minimum concrete reference

A Gate C closure claim requires at least one nontrivial concrete finite reference
with:

```text
actual density matrices
actual matrix-valued update or channel
actual nonconstant quantum information quantity
explicit support/domain proof
constructive recovery tied to the update
non-vacuous strict progress
concrete Boolean checker
invalid candidate rejection
finite accepted trajectory
RCLM refinement
source and axiom audits
```

A type alias around the classical Gate B distributions is insufficient unless the
result is explicitly described as a commuting diagonal bridge rather than Gate C
closure.

## Planned module organization

The existing public placeholder is:

```text
RCP/QuantumFinite.lean
```

Before implementation begins, decide whether the concrete development remains in
that file or is split into focused internal modules such as:

```text
RCP/QuantumFinite/Types.lean
RCP/QuantumFinite/Density.lean
RCP/QuantumFinite/Entropy.lean
RCP/QuantumFinite/Channels.lean
RCP/QuantumFinite/Recovery.lean
RCP/QuantumFinite/Checker.lean
RCP/QuantumFinite/Trajectory.lean
RCLM/QuantumFinite.lean
```

No split is mandated by this placeholder. The exact imported API and theorem
contract should determine the file boundary.

## Gate C exit conditions

Gate C is complete only when all applicable items hold:

```text
exact representation and theorem statement frozen
exact mathlib imports pinned
all assumptions explicit
actual nonconstant quantum divergence or entropy quantity
actual computed residuals
reality containment is substantive
constructive recovery tied to the accepted update
non-vacuous strict witness
concrete checker soundness
invalid packet rejection
finite trajectory composition instantiated
conditional infinite closure retains successor availability
RCLM refinement proved over the quantum objects
no sorry/admit
no project-local axiom declaration
public theorem axiom audit extended
paper theorem map and assumption register synchronized
clean pinned GitHub CI succeeds
closure record and manifest updated
```

## Non-goals of the placeholder

This document does not claim:

```text
a completed Gate C theorem
quantum advantage
arbitrary quantum channels
infinite-dimensional operator algebras
full Paper I or Paper II equivalence
strict useful improvement at every recursive step
an executable checker or generator
empirical RSI
```

No later document should cite this planning record as evidence that any quantum
result has been mechanized.