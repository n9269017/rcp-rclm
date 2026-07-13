# Formal Core v2 — conditional RCLM architecture engine theorem

## Status

The architecture-engine layer is implemented at two distinct levels.

```text
Generic Paper II-facing conditional theorem: implemented
Explicit generator proposal relation: implemented
Explicit certificate construction relation: implemented
Explicit candidate selector relation: implemented
Explicit successor realizer relation: implemented
Explicit witness-library/coverage premise: implemented
Explicit trust-anchor premise and preservation law: implemented
Explicit resource premise and soundness law: implemented
Explicit successor-domain closure law: implemented
Explicit successor-availability premise: implemented
Conditional infinite architecture trajectory: implemented
Concrete Gate B classical/binary engine instance: implemented
Concrete first strict-improvement step: implemented
Concrete successor availability on the declared binary domain: implemented
Clean pinned build and expanded axiom audit: passed
Exact full Paper II theorem equivalence: not claimed
Arbitrary learned-system engine completeness: not claimed
Executable Python RSI phase: not licensed
```

## Generic engine data

`RCLM.ArchitectureEngine` separates the untrusted engine stages from the trusted
checker. Its fields include:

```text
domain
witnessLibrary
proposes
constructsCertificate
selectsCandidate
realizesSuccessor
trustAnchorValid
resourcePremise
```

The structure also requires proofs that the realizer is typed, the declared
trust anchor implies the kernel trust proposition, the declared resource premise
implies the kernel resource proposition, accepted successors remain in the
architecture theorem domain, and the trust anchor remains valid at the
successor.

`RCLM.ArchitectureEngineStep` records one concrete generated, certified,
selected, realized, resource-authorized, checker-accepted packet. Generator,
certifier, selector, and realizer relations are propositions with evidence; they
are not Booleans assigned true by construction.

## One-step architecture theorem

The theorem

```lean
RCLM.rclm_architecture_successor_theorem
```

requires:

```text
an architecture-domain predecessor
kernel admissibility and protected invariant evidence
an explicit covered witness
an explicit generated proposal
an explicit constructed certificate
an explicit selected candidate
an explicit realized successor
an explicit trust anchor
an explicit resource authorization
RCLM checker acceptance
RCLM-to-RCP kernel, checker, recovery-law, and monitor refinements
```

It yields:

```text
typed RCLM successor evidence
complete RCLM StepObligations
forgotten core-checker acceptance
complete forgotten RCP StepObligations
preserved recovery-composition laws
preserved monitor-refinement evidence
successor architecture-domain membership
successor admissibility and invariant preservation
engine trust and resource validity
trust-anchor preservation
```

Checker soundness supplies the formal successor obligations only after an actual
candidate and certificate have been produced and accepted. It does not prove
that the engine can produce such a packet.

## Explicit architecture successor availability

`RCLM.ArchitectureSuccessorAvailability engine` is the separate completeness
premise:

```text
for every valid architecture predecessor,
there exists an architecture-engine step carrying all engine-stage evidence and
checker acceptance.
```

The conditional infinite theorem

```lean
RCLM.conditional_infinite_architecture_trajectory_exists
```

keeps that premise as an explicit argument. `RCLM.infinite_architecture_step_result`
then applies the one-step architecture theorem at every selected time.

The resulting architecture trajectory can be forgotten to both:

```lean
RCP.InfiniteAcceptedTrajectory rclmChecker
RCP.InfiniteAcceptedTrajectory coreChecker
```

through the already proved checker and kernel refinements.

## Concrete Gate B classical engine

`RCLM.ClassicalBinary` supplies a finite reference engine with:

```text
proposal classes: improve, stabilize, rejected
witness classes: strict improvement, stable continuation, rejected
one root trust anchor
an explicit used/limit resource record
initial-domain proposal: strict improvement
successor-domain proposal: stable continuation
canonical certificate construction
canonical candidate selection
realization by the typed RCLM update semantics
```

The concrete theorem

```lean
RCLM.ClassicalBinary.improvement_direct_engine_successor
```

proves the full generic architecture-successor result for the accepted Gate B
KL-derived improvement packet.

`RCLM.ClassicalBinary.architectureSuccessorAvailability` discharges the explicit
availability premise only for the declared binary architecture domain. The
selected infinite reference path performs the strict initial improvement and
then follows accepted stability successors. This is a theorem-level closure
witness for the finite reference engine, not evidence of indefinitely strict
capability growth.

## Validation

The architecture-engine theorem surface was included in the dedicated RCLM
axiom audit and passed the pinned Linux workflow:

```text
Branch source head:   0731abfdf0edb940312a48051a3ca527c086af5b
CI checkout commit:   90054eb9e2da0f91bd7233e882af6d8a0cdba462
Workflow run:         29215941083
Build:                1945 jobs, success
No sorry/admit:       pass
Project-local axioms: none
No sorryAx:           pass
Audited declarations: 27
Artifact:             formal-core-v2-audit-29215941083-1
Artifact SHA-256:     9d4d3d5a38e2bfefbb641950131c8a10dbec20fc90b89c165a08ef4f4b98fff4
```

The generic engine theorems report only the standard Lean/mathlib foundational
union `[propext, Classical.choice, Quot.sound]`; no project-local axiom or
admitted proof occurs.

## Claim boundary

This phase establishes a conditional architecture successor/direct-engine
closure theorem and a concrete finite reference instance. It does not establish:

```text
exact identity with every object in the pinned Paper II direct-engine theorem
arbitrary generator coverage
useful strict improvement at every recursive step
learned-model proposal or certificate generation
semantic mutual information or full ambiguity semantics
finite-dimensional quantum relative entropy
Python checker, generator, or promotion-loop refinement
empirical recursive self-improvement
external benchmark performance
```

The next formal obligation is to compare this compiled theorem line by line with
the pinned Paper II direct-engine and robust-reflective successor statements,
then either strengthen the theorem, narrow the paper claim, or register every
remaining semantic premise explicitly.
