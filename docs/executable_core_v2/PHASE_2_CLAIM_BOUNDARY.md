# Phase 2 Lean-conformance claim boundary

## Established by this phase

Phase 2 establishes a pinned hybrid verification bridge for the declared finite
reference packets only.

For each supported packet, Python:

```text
parses the canonical packet
computes the finite reference verdict
emits deterministic Lean source
hashes the source
runs the mandatory source guard
checks the pinned formal project identity and declared theorem surface
invokes the pinned Lean toolchain
captures stdout, stderr, exit code, timeout state, source/output hashes, and toolchain runtime identity
parses one packet-bound machine-readable verdict
compares the Lean and Python verdicts
```

The differential suite covers Gate B core, Gate B RCLM, Gate C core, and Gate C
RCLM improvement/stability references together with declared mutation cases.
A rejected mutation is a successful conformance result only when both interpreters
return `reject`.

## Not established

Phase 2 does not establish:

```text
that every Python runtime function refines every Lean declaration
that an arbitrary candidate package can be accepted
that candidate-provided certificates are trustworthy
that the production aggregate checker is sound
that the generator is complete or trustworthy
that a successor can be promoted
that rollback or independent replay is implemented
that a PyTorch update is theorem-refined
that a benchmark score is certified
that the noncommuting quantum case is covered
```

The generated agreement theorem is a finite reference conformance theorem. It is
not a proof of arbitrary Python program equivalence.

## Trust boundary

Untrusted inputs include:

```text
packet bytes before strict parsing
generated source before source-guard approval
candidate assertions
candidate scores
future model or generator outputs
```

Trusted only after validation:

```text
canonical parser and serializer
formal-source pin inspection
generated-source guard
pinned Lean invocation
verdict parser
bridge report construction
```

The generator never invokes itself as a certifier, cannot replace the pinned
checker surface, and cannot bypass the source guard.

## Licensing after closure

A clean Phase 2 closure licenses work on the production fail-closed checker. It
does not license promotion. The production checker must recompute all Phase 0
acceptance obligations, invoke this bridge, reject indeterminate results, and pass
an adversarial rejection suite before candidate acceptance can be claimed.
