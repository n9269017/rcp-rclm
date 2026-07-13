# Trust boundary

## Principle

No component becomes trusted because it produced a plausible result. Trust is
assigned only by this contract and, where stated, only after deterministic
conformance, tamper, and replay validation.

## Root-of-trust inputs

The following are immutable trust anchors for the first executable reference:

```text
formal source commit:
  012de4a55f326107f53f0e215c8aec62859d0bbf

Lean toolchain:
  leanprover/lean4:v4.31.0

mathlib commit:
  fabf563a7c95a166b8d7b6efca11c8b4dc9d911f

formal manifest blob:
  a2153043eb68e912e7e700600dcd1346ce514dbb

selected Gate C audit artifact SHA-256:
  18b4593e544fa926af7fac20c5623850c929004d944f509d017dba04f6f7f2e5
```

Changing a root requires a new contract version and renewed conformance evidence.

## Trusted immediately

Only immutable identifiers and cryptographic primitives are trusted immediately:

```text
pinned formal-source identifiers
pinned theorem and source blob identifiers
SHA-256 as the declared content-hash primitive
this versioned contract after clean contract validation
```

This category does not include candidate-produced data.

## Trusted only after validation

The following components enter the trusted computing base only after their Phase 1
or later exit criteria pass:

```text
canonical serializer and parser
canonical path normalizer
semantic tree hasher
exact-rational implementation
certified interval implementation
Lean verifier bridge
runtime checker
promotion rule
atomic manifest writer
rollback controller
independent replay implementation
```

Required validation includes:

```text
positive fixtures
mutation and tamper fixtures
unknown-field rejection
round-trip canonicalization
cross-platform byte equality
Python-to-Lean differential tests
failure-injection tests
independent replay
```

Until those tests pass, the component is implementation-under-test and its output
cannot authorize promotion.

## Always untrusted

The following remain outside the trusted computing base:

```text
generator
LLM or other planning model
PyTorch model and model weights
optimizer and training loop
proposal ranking policy
retrieval or memory policy
candidate code and candidate files
candidate-provided certificate assertions
candidate-reported scores
candidate-reported hashes
candidate-reported resource usage
generated Lean source before scanning and elaboration
external benchmark output before independent ingestion
human-authored manual repair during a run
```

Untrusted components may propose data. They may not determine acceptance.

## Generator separation

The generator runs as a separate process with:

```text
read-only predecessor package
read-only public objective
fixed resource budget
empty candidate workspace
```

It must not have write access to:

```text
checker implementation
Lean verifier implementation
trust-anchor files
accepted package manifests
promotion ledger
replay ledger
reference answers
held-out evaluation data
```

The generator may emit a certificate proposal, but every authoritative fact is
recomputed by the checker.

## No self-certification

Fields such as the following are assertions, not evidence:

```text
accepted
certificate_preserved
strict_improvement
reality_contained
resource_valid
trust_valid
non_loss_preserved
recovery_exact
score_improved
```

The checker ignores these fields for acceptance or rejects them if they appear in a
schema that does not declare them.

## Lean bridge boundary

The initial Lean bridge trusts only:

```text
canonical packet bytes
pinned source template
anti-placeholder scan result
pinned Lean executable and dependency graph
Lean process exit status
machine-readable verifier output whose hash is recorded
```

Generated source is untrusted until all of the following hold:

```text
no forbidden proof token
no project-local axiom declaration
source hash recorded
pinned Lean elaboration succeeds
expected theorem entry point is invoked
verifier report parses canonically
```

## Human operator boundary

An operator may start, stop, or reproduce a run. An operator may not alter a
candidate, certificate, score, or manifest between generation and checking.

Any manual change requires a new run identifier and invalidates the previous
transition. There is no override-to-accept mechanism.

## Promotion authority

Only the promotion controller may mark a candidate active, and only when it
receives:

```text
runtime verdict = accept
Lean bridge verdict = accept
all package hashes valid
parent linkage valid
no manual-repair marker
resource record valid
atomic write and rollback snapshot complete
```

The checker computes acceptance. The controller only enforces the already computed
result.
