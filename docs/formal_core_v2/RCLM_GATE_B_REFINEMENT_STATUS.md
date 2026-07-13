# Formal Core v2 — substantive RCLM-to-RCP refinement and conditional engine closure

## Status

The substantive RCLM-to-RCP refinement is complete at the declared finite Gate B
classical/binary scope, and the next conditional architecture-engine theorem
layer is implemented.

```text
Generic theorem-relevant kernel refinement: implemented
Generic checker-acceptance refinement: implemented
Generic recovery-law transport: implemented
Generic monitor-refinement contract: implemented
Concrete Gate B classical RCLM wrapper: implemented
Concrete architecture-evidence checker: implemented
Concrete checker acceptance to RCP obligations: implemented
Explicit generator/certifier/selector/realizer engine data: implemented
Explicit witness, trust, resource, domain, and availability premises: implemented
Conditional one-step architecture successor theorem: implemented
Conditional infinite architecture trajectory: implemented
Concrete Gate B direct-engine reference: implemented
Clean pinned CI build and expanded theorem-axiom audit: required at final head
Exact full Paper II theorem equivalence: not claimed
Gate C quantum strengthening: not claimed
Executable Python RSI phase: not licensed
```

## Generic RCLM-to-RCP refinement

`RCLM.KernelRefinement` maps a substantive RCLM kernel to an RCP kernel and
requires preservation of every one-step theorem quantity used by Gate A:

```text
state and typed update semantics
admissibility and protected invariants
protected values, transports, and loss budgets
state distance, candidate-tied recovery, and recovery budgets
progress and strict witnesses
computed residuals
trust, resource, and reality-containment propositions
```

The theorem `RCLM.KernelRefinement.stepObligationsPreserved` maps a complete RCLM
`StepObligations` bundle to the complete RCP bundle. No obligation is discarded.

`RCLM.KernelRefinement.recoveryCompositionLawsPreserved` transports the recovery
laws. `RCLM.MonitorRefinement` preserves every Lyapunov, motion, ambiguity, and
relevance quantity and transport. `RCLM.CheckerRefinement` requires actual
Boolean acceptance preservation.

The public generic surface includes:

```lean
RCLM.rclm_step_obligations_refine_rcp
RCLM.rclm_checker_refines_rcp
RCLM.rclm_checker_acceptance_preserved
RCLM.rclm_checker_pair_refines_rcp
RCLM.rclm_recovery_laws_refine_rcp
RCLM.rclm_monitor_refinement_valid
```

## Concrete Gate B classical RCLM wrapper

`RCLM.ClassicalBinary` provides substantive typed records for language, world and
human references, definitiveness, ambiguity, memory, verifier, resources,
self-model, architecture updates, and certificate evidence. Canonical encodings
are defined for the outside, initial, and target states; stay and improve
updates; and improvement, stability, and malformed certificates.

The RCLM checker accepts only when:

1. the forgotten Gate B packet is accepted by the binary core checker; and
2. every architecture field equals the declared canonical encoding.

The theorem `RCLM.ClassicalBinary.accepted_architecture_successor` yields checked
architecture evidence, complete RCLM obligations, and complete forgotten RCP
obligations.

## Conditional architecture-engine layer

`RCLM.ArchitectureEngine` separates the following relations:

```text
witness-library coverage
generator proposal
certificate construction
candidate selection
successor realization
trust-anchor validity
resource authorization
```

It additionally requires typed realization, trust and resource soundness,
successor-domain closure, and trust-anchor preservation.

`RCLM.ArchitectureEngineStep` packages an actual witness, proposal, certificate,
candidate, resource record, all engine-stage evidence, and RCLM checker
acceptance.

The theorem

```lean
RCLM.rclm_architecture_successor_theorem
```

returns:

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

Checker soundness is used only after an actual candidate and certificate have
been generated, selected, realized, and accepted.

## Explicit successor availability and infinite closure

`RCLM.ArchitectureSuccessorAvailability` states that every valid architecture
predecessor has a nonempty engine step carrying all engine relations and checker
acceptance. It is an explicit premise.

Under that premise:

```lean
RCLM.conditional_infinite_architecture_trajectory_exists
RCLM.infinite_architecture_step_result
```

construct an infinite architecture trajectory and apply the one-step theorem at
every selected time. The trajectory can be forgotten to both RCLM-checker and
core-checker accepted trajectories.

Checker soundness does not imply this availability premise.

## Concrete Gate B direct-engine reference

`RCLM.ClassicalBinary.architectureEngine` instantiates:

```text
improve, stabilize, and rejected proposal classes
strict-improvement, stable-continuation, and rejected witnesses
canonical certificate construction
canonical candidate selection
typed successor realization
one root trust anchor
explicit used/limit resources
```

The theorem

```lean
RCLM.ClassicalBinary.improvement_direct_engine_successor
```

proves the complete architecture-successor result for the accepted KL-derived
improvement packet.

`RCLM.ClassicalBinary.architectureSuccessorAvailability` proves availability only
for the declared binary architecture domain. The resulting infinite reference
trajectory performs the strict initial improvement and then uses accepted
stability successors. This proves recursive domain closure, certificate
acceptance, and preservation, not indefinitely strict capability growth.

## Audit surface

The RCLM axiom audit includes the generic refinement theorems, the generic
architecture-engine theorems, the concrete checker/refinement theorems, the
concrete availability theorem, the concrete direct-engine successor theorem,
and the concrete infinite architecture step theorem.

The final synchronized workflow must pass:

```text
clean pinned Lean build
no sorry/admit scan
no project-local axiom declaration scan
Gate A axiom audit
Gate B axiom audit
RCLM refinement and architecture-engine axiom audit
```

## Claim boundary

This phase does not establish:

```text
exact identity with every pinned Paper II architecture object
arbitrary learned-system entry
arbitrary generator coverage
strict useful improvement at every recursive step
conditional-expectation, semantic ambiguity, or mutual-information identity
Gate C quantum relative entropy
Python checker or generator refinement
executable or empirical recursive self-improvement
external benchmark performance
```

The next formal task after final CI is the line-by-line Paper II engine alignment
audit: compare the generic and concrete Lean theorem assumptions and conclusions
against the pinned direct-engine and robust-reflective successor statements, then
strengthen Lean, narrow the paper, or register every remaining premise.
