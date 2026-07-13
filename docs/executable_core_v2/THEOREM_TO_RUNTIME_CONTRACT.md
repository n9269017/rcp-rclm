# Theorem-to-runtime refinement contract

## Phase name

```text
RCP/RCLM Executable Core v2 — Theorem-to-Runtime Refinement and Fail-Closed Successor Promotion
```

## Purpose

This contract defines the boundary between the completed Formal Core v2 Lean
project and any later executable Python implementation. It freezes the semantic
objects, evidence requirements, trust assumptions, numeric interpretation,
serialization profile, acceptance predicate, and claim boundary before the first
production runtime checker is implemented.

No Python function is covered by a Lean theorem merely because it has a similar
name. Runtime refinement is established only when the object correspondence,
canonical encoding, conformance tests, and Lean verifier bridge named here are
implemented and pass.

## Formal source pin

```text
repository:           n9269017/rcp-rclm
formal source commit: 012de4a55f326107f53f0e215c8aec62859d0bbf
Lean:                 leanprover/lean4:v4.31.0
mathlib:              fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
formal manifest blob: a2153043eb68e912e7e700600dcd1346ce514dbb
```

The executable contract is invalid if a mapped Lean source blob changes without a
contract-version increment and renewed conformance evidence.

## Selected formal objects

### Gate A

The executable layer instantiates:

```text
RCP.Kernel
RCP.Candidate
RCP.StepObligations
RCP.TrustedChecker
RCP.RecoveryCompositionLaws
RCP.PreservationMonitors
RCP.FiniteAcceptedTrajectory
```

The runtime checker must recompute the complete one-step obligation bundle:

```text
typed successor validity
all residuals nonpositive
protected non-loss
constructive candidate-tied recovery
protected invariant preservation
progress nondecrease
strict progress when a strict witness is certified
trust validity
resource validity
reality or uncertainty containment
successor admissibility
```

### Gate B

The first executable classical reference instantiates:

```text
RCP.ClassicalFinite.Distribution
RCP.ClassicalFinite.SupportedBy
RCP.ClassicalFinite.shannonEntropy
RCP.ClassicalFinite.klDivergence
RCP.ClassicalFinite.ZeroExtension
RCP.ClassicalFinite.extendByZero
RCP.ClassicalFinite.recoverZeroExtension
RCP.ClassicalFinite.BinaryState
RCP.ClassicalFinite.BinaryUpdate
RCP.ClassicalFinite.BinaryCertificate
RCP.ClassicalFinite.binaryCheck
```

The executable reference must preserve the exact finite probability vector as the
source of truth. Entropy and KL evidence are derived from that vector, never from a
candidate-reported scalar.

### Gate C

The first executable quantum reference instantiates only the completed selected
scope:

```text
RCP.QuantumFinite.DiagonalDensityMatrix
RCP.QuantumFinite.DensityMatrixEvidence
RCP.QuantumFinite.SupportedBy
RCP.QuantumFinite.vonNeumannEntropy
RCP.QuantumFinite.quantumRelativeEntropy
RCP.QuantumFinite.FiniteDiagonalChannel
RCP.QuantumFinite.identityChannel
RCP.QuantumFinite.swapChannel
RCP.QuantumFinite.selectedChannel
RCP.QuantumFinite.selectedRecoveryChannel
RCP.QuantumFinite.QuantumState
RCP.QuantumFinite.QuantumUpdate
RCP.QuantumFinite.QuantumCertificate
RCP.QuantumFinite.quantumCheck
```

The executable quantum source of truth is the certified finite spectrum. A dense
matrix is derived from the spectrum and must be diagonal. Arbitrary noncommuting
matrices, arbitrary CPTP maps, matrix-logarithm QRE, general data processing, and
Petz recovery are outside this contract.

### RCLM

The executable architecture layer instantiates:

```text
RCLM.State
RCLM.Update
RCLM.CertificatePacket
RCLM.KernelRefinement
RCLM.MonitorRefinement
RCLM.CheckerRefinement
RCLM.ArchitectureEngine
RCLM.ArchitecturePredecessor
RCLM.ArchitectureEngineStep
RCLM.ArchitectureSuccessorAvailability
```

The runtime must preserve the complete architecture register, update register,
certificate evidence, checker acceptance, recovery laws, monitors, and the
forgotten RCP obligations. Generator proposal, certificate construction,
candidate selection, realization, trust-anchor validity, resource authorization,
and successor-domain closure are separate relations and separate evidence fields.

## Six frozen contract decisions

### 1. Object correspondence

Every mapped object has all six entries:

```text
Lean declaration
serialized schema identifier
immutable Python type name
runtime function name
certificate evidence identifier
conformance-test identifier
```

The authoritative table is `OBJECT_CORRESPONDENCE.md`; the machine-readable form
is `runtime_contract_manifest.json`.

A future implementation may add internal helper types, but it may not change a
mapped field, enum, or semantic function without incrementing the contract version.

### 2. Trust boundary

The trust boundary is defined in `TRUST_BOUNDARY.md`.

The generator, candidate code, candidate-provided certificates, candidate-reported
scores, PyTorch model, optimizer, and planning scaffold are untrusted. They may
supply evidence inputs, but they may not decide acceptance.

The canonical serializer, content hasher, runtime checker, Lean bridge, and
promotion rule become trusted only after their own deterministic tests,
differential conformance tests, and tamper tests pass.

### 3. Numerical semantics

The numeric profile is defined in `NUMERICAL_SEMANTICS.md`.

Core rules:

```text
probability masses use reduced exact rational values
mathematical integers are encoded as decimal strings
logs and log-derived quantities use outward-rounded certified intervals
NaN and infinity are rejected before evaluation
normalization is exact for rational inputs
support is a structural predicate, not a tolerance comparison
strict progress passes only when the computed lower bound is greater than zero
non-loss passes only when the computed upper bound is no greater than the budget
an interval overlapping a decision boundary produces indeterminate, never accept
```

### 4. Canonical serialization and hashing

The serialization profile is defined in `CANONICAL_SERIALIZATION.md`.

Core rules:

```text
UTF-8 only
Unicode NFC normalization
lexicographically ordered object keys
no insignificant whitespace
no floating-point JSON numbers
mathematical integers and rationals encoded as canonical decimal strings
POSIX relative paths only
no absolute paths, dot segments, backslashes, or symlinks
semantic hashes exclude timestamps, owners, and host-specific metadata
SHA-256 with explicit domain separation
parent package hash and certificate hash are mandatory linkage fields
```

### 5. Acceptance semantics

The fail-closed predicate is defined in `ACCEPTANCE_SEMANTICS.md`.

The checker returns exactly one of:

```text
accept
reject
indeterminate
```

Only `accept` is promotable. Any missing evidence, schema drift, unsupported scope,
numeric overlap, Lean bridge failure, hash mismatch, timeout, or internal error is
`reject` or `indeterminate`, never implicit acceptance.

### 6. Claim boundary

The claim boundary is defined in `CLAIM_BOUNDARY.md`.

The first executable result may claim a finite, replayable theorem-to-runtime
reference witness for the selected Gate B and Gate C scopes after all runtime exit
criteria pass. It may not claim arbitrary learned-system entry, indefinitely strict
improvement, unbounded generator completeness, general quantum closure, autonomous
RSI, or external benchmark performance.

## Required runtime architecture after Phase 0

```text
contract records and schemas
→ exact rational and interval mathematics
→ canonical serializer and tree hasher
→ generated-source anti-placeholder gate
→ Lean conformance bridge
→ fail-closed checker
→ adversarial rejection suite
→ deterministic reference generator
→ successor realizer and package builder
→ promotion and rollback controller
→ independent replay
→ optional learned/PyTorch proposal backend
```

## Lean bridge requirement

At least one independent Lean-backed verifier path is mandatory before the Python
checker is called a refinement. The initial permitted bridge is:

```text
canonical runtime packet
→ generated restricted Lean certificate source
→ anti-placeholder and local-axiom scan
→ pinned Lean invocation
→ structured verifier report
```

A later pinned Lean executable may replace per-packet source generation after
conformance is established.

The pre-compilation source gate must reject occurrences of:

```text
sorry
sorryAx
admit
```

Generated certificate source must also reject project-local `axiom` declarations.
The scan is a hygiene gate; successful scanning does not substitute for Lean
elaboration.

## Generator independence

The generator runs outside the checker trust boundary. It receives only declared
predecessor inputs and a fixed resource budget. It has no write access to:

```text
checker source
Lean verifier source
trust anchor
previous accepted manifests
promotion ledger
reference answers
```

The generator may construct a proposed certificate packet, but the checker must
recompute every authoritative fact. No candidate field named `accepted`,
`certificate_preserved`, `strict_improvement`, or similar is trusted as evidence.

## Contract versioning

The initial version is:

```text
rcp-rclm-runtime-contract-v2.0.0
```

A major version change is required for:

```text
field removal or semantic reinterpretation
change of canonical byte representation
change of hash domain separation
change of acceptance logic
change of numeric decision rules
expansion beyond the selected Gate B or Gate C scope
```

A minor version may add optional evidence that cannot affect acceptance. A patch
version may correct documentation without changing machine-readable semantics.

## Phase transition rule

Phase 1 may begin only when every item in `PHASE_0_EXIT_CRITERIA.md` is satisfied by
a clean CI run. Phase 0 does not license a generator, promotion loop, PyTorch model,
or external benchmark adapter.
