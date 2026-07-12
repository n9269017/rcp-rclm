# Formal Core v2 — substantive RCLM-to-RCP refinement at Gate B scope

## Status

The first substantive RCLM-to-RCP refinement tranche is complete at the declared
finite classical binary reference scope.

```text
Generic theorem-relevant kernel refinement: implemented
Generic checker-acceptance refinement: implemented
Generic recovery-law transport: implemented
Generic monitor-refinement contract: implemented
Concrete Gate B classical RCLM state/update/certificate wrapper: implemented
Concrete architecture-evidence checker: implemented
Concrete checker acceptance to RCP StepObligations: implemented
Clean pinned CI build and theorem-axiom audit: passed
Full Paper II architecture theorem: not claimed
Generator/certifier/selector/realizer construction theorem: not claimed
Gate C quantum strengthening: not claimed
Executable Python RSI phase: not licensed
```

## Generic refinement contract

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

The state, update, certificate, protected-distinction, and residual-index maps
have explicit right-inverse witnesses for the core objects used by theorem
transport.

The theorem

```lean
RCLM.KernelRefinement.stepObligationsPreserved
```

proves that a complete RCLM `StepObligations` bundle maps to the complete RCP
`StepObligations` bundle. No field is replaced by a Boolean asserted true by
construction.

## Recovery and monitor refinement

`RCLM.KernelRefinement.recoveryCompositionLawsPreserved` transports zero
self-distance, triangle, and candidate-recovery nonexpansiveness from the RCLM
kernel to the RCP kernel.

`RCLM.MonitorRefinement` explicitly preserves:

```text
Lyapunov values
motion charges
Lyapunov error budgets
unsupported-collapse quantities
ambiguity budgets
relevance values and transports
relevance error budgets
```

These are theorem-relevant equalities, not name-based identifications.

## Checker refinement

`RCLM.CheckerRefinement` requires actual Boolean acceptance preservation:

```text
RCLM checker accepts
  implies
RCP checker accepts the forgotten packet.
```

The public generic theorems include:

```lean
RCLM.rclm_step_obligations_refine_rcp
RCLM.rclm_checker_refines_rcp
RCLM.rclm_checker_acceptance_preserved
RCLM.rclm_checker_pair_refines_rcp
RCLM.rclm_recovery_laws_refine_rcp
RCLM.rclm_monitor_refinement_valid
```

Checker soundness remains distinct from successor availability and generator
completeness.

## Concrete Gate B classical RCLM wrapper

`RCLM.ClassicalBinary` instantiates the generic contracts with substantive RCLM
records whose fields include:

```text
language register
world and human reference registers
definitiveness and ambiguity registers
memory and verifier registers
resource ledger
self-model register
core, parameter, architecture, memory, verifier, semantic, tool, and resource updates
semantic, typing, ledger, goal-transport, trust, resource, reality, recovery,
and progress evidence
```

The core projection is the completed Gate B binary KL kernel. Canonical RCLM
encodings are defined for the outside, initial, and target states; stay and
improve updates; and improvement, stability, and malformed certificates.

The RCLM checker accepts only when both conditions hold:

1. the forgotten Gate B packet is accepted by the concrete binary checker; and
2. every architecture field equals the declared canonical encoding of its core
   state, update, successor, or certificate.

Thus the extra architecture evidence is checked rather than ignored.

The concrete public surface includes:

```lean
RCLM.ClassicalBinary.check_eq_true_iff
RCLM.ClassicalBinary.architectureEvidence_of_check
RCLM.ClassicalBinary.accepted_architecture_successor
RCLM.ClassicalBinary.improvement_refines_gate_b
RCLM.ClassicalBinary.improvement_architecture_evidence
```

`accepted_architecture_successor` yields, from one accepted packet:

```text
validated architecture evidence
complete RCLM StepObligations
complete forgotten RCP StepObligations
```

## Validation

The synchronized source head passed the pinned Linux workflow:

```text
Source head:        8483cdc3ae53843c6d3294b8b73ef3397393a958
Workflow run:       29212558655
Build:              success
No sorry/admit:     pass
Project-local axiom scan: pass
Gate A axiom audit: pass
Gate B axiom audit: pass
RCLM refinement axiom audit: pass
Artifact:           formal-core-v2-audit-29212558655-1
Artifact SHA-256:   4a2dfe1e3ef30112f7b1c30ee111255654b890de7a42774b11006b9d1536a914
```

The RCLM audit covers nineteen generic and concrete public declarations. No
reported theorem depends on `sorryAx`, and the whole source tree contains no
`sorry`, `admit`, or project-local `axiom` declaration.

## Claim boundary

This tranche does not establish:

```text
exact Paper II architecture-theorem equivalence
architecture generator/certifier/selector/realizer completeness
successor availability
arbitrary learned-system entry
Gate C quantum relative entropy
Python checker or generator refinement
executable or empirical recursive self-improvement
external benchmark performance
```

The next refinement obligation is to formulate the Paper II architecture-level
successor theorem with all generator, certifier, selector, realizer, trust,
resource, and availability premises explicit, then prove its Gate B classical
instance without weakening the present checker and field-preservation boundary.