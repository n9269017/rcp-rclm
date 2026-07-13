# Formal Core v2 exit criteria

No Python checker, generator, closed-loop successor runtime, or external
benchmark phase begins until every item required for the claimed executable core
is satisfied.

## Global formal-core exit conditions

- [ ] The exact Paper I/Paper II theorem statements and mapped Lean declarations
  agree.
  - [x] The line-by-line comparison audit is complete.
  - [x] Every abstract Gate A mismatch has been represented or resolved.
  - [x] Gate B resolves the declared finite classical/KL reference obligations.
  - [x] The substantive Gate B RCLM-to-RCP refinement is implemented.
  - [x] A conditional Paper II-facing architecture successor/direct-engine theorem
    with explicit engine premises is implemented.
  - [ ] Gate C and exact Paper I/Paper II semantic refinements resolve the remaining
    mismatches.
- [x] Every assumption used by the abstract theorem surfaces is explicit in a
  structure, proposition, or theorem parameter.
- [x] Every Gate A kernel exhibits a nonconstant protected-value function.
- [x] Every Gate A kernel exhibits a nonconstant residual evaluator.
- [x] Reality containment is substantive and every Gate A kernel exhibits a
  packet for which it fails.
- [x] Trust, resource, and reality gates are propositions rather than booleans
  assigned true by construction.
- [x] Checker soundness proves `check = true → formal successor obligations`.
- [x] Recovery is constructive and tied to the actual accepted update.
- [x] Composed endpoint recovery is proved under explicit self-zero, triangle,
  and nonexpansiveness laws.
- [x] Strict improvement is non-vacuous in a concrete instance and is not merely
  a fresh index. The Gate B witness strictly reduces actual KL distance.
- [x] Abstract finite accepted-trajectory composition is proved.
- [x] Abstract infinite-horizon closure is proved only under explicit successor
  availability.
- [x] Paper-facing safe-state/update-admissibility equivalences and no-op
  feasibility are explicit premises.
- [x] Finite Lyapunov/motion, ambiguity-collapse, and transported relevance
  composition is proved abstractly.
- [x] Standard summability assumptions are bridged to uniform finite-prefix
  bounds.
- [x] RCLM-to-RCP refinement is proved for substantive Gate B states, updates,
  certificates, monitor/recovery laws, and checker acceptance.
- [x] Generator proposal, certificate construction, candidate selection,
  successor realization, witness coverage, trust anchor, resource premise, and
  successor-domain closure are explicit architecture-engine objects.
- [x] The conditional architecture successor theorem yields typed RCLM
  obligations, forgotten RCP obligations, recovery/monitor refinement evidence,
  and successor-domain closure.
- [x] The conditional infinite architecture theorem carries an explicit
  architecture successor-availability premise.
- [x] The concrete Gate B architecture engine discharges availability only on its
  declared binary domain.
- [ ] A theorem establishes useful strict improvement at every recursive
  architecture step. The current binary infinite reference path becomes stable
  after its first strict step.
- [x] Gate B includes a nontrivial finite classical/diagonal model with actual
  entropy/divergence, conservative extension, recovery, strict progress, and a
  concrete checker refinement.
- [x] The audited source contains no `sorry` or `admit`.
- [x] No project-local `axiom` declaration or `sorryAx` occurs in the audited
  theorem surfaces.
- [x] Lean and mathlib are pinned to exact immutable revisions.
- [x] `lake-manifest.json` is committed.
- [x] Clean GitHub CI builds the formal project.
- [x] Source-admission and theorem-axiom audits are uploaded as workflow
  artifacts.
- [x] The theorem map, assumption register, closure records, and formalization
  manifest separate implemented structural theorems from exact paper claims.

## Gate-specific release conditions

### Gate A — abstract theorem kernel

```text
Abstract Gate A theorem kernel: COMPLETE
Concrete Paper I theorem identification: PARTIALLY DISCHARGED BY GATE B
```

### Gate B — concrete finite classical/diagonal instantiation

Delivered:

- [x] normalized finite distributions;
- [x] actual Shannon entropy and finite KL divergence;
- [x] support-aware KL nonnegativity and self-zero;
- [x] a positive nonconstant binary KL witness;
- [x] zero-coordinate conservative extension;
- [x] exact support, Shannon, and KL preservation for that extension;
- [x] exact constructive recovery;
- [x] substantive finite state/update/certificate/residual types;
- [x] KL-derived strict progress;
- [x] concrete monitor meanings with explicit semantic limits;
- [x] concrete Boolean checker and complete obligation refinement;
- [x] invalid-candidate rejection;
- [x] binary recovery composition laws;
- [x] a nontrivial trajectory `initial → target → target`;
- [x] dedicated theorem-axiom audit.

```text
Gate B finite classical reference scope: COMPLETE
Exact Paper I main theorem: NOT COMPLETE
```

### Substantive RCLM refinement

Delivered at the Gate B classical scope:

- [x] substantive typed architecture state fields and invariants;
- [x] substantive typed update fields;
- [x] typed certificate-evidence fields;
- [x] state/update/certificate/protected/residual forget-lift maps;
- [x] typed update semantics preservation;
- [x] admissibility and protected-invariant preservation;
- [x] protected values, transports, and budgets preservation;
- [x] state-distance, recovery, and recovery-budget preservation;
- [x] progress and strict-witness preservation;
- [x] computed residual preservation;
- [x] trust, resource, and reality proposition preservation;
- [x] complete `StepObligations` transport;
- [x] recovery-composition law transport;
- [x] Lyapunov/motion/ambiguity/relevance monitor refinement;
- [x] Boolean checker-acceptance preservation;
- [x] checked canonical architecture evidence;
- [x] dedicated RCLM theorem-axiom audit.

### Conditional architecture successor/direct-engine theorem

Delivered:

- [x] explicit architecture theorem domain;
- [x] explicit witness-library/coverage proposition;
- [x] explicit generator proposal relation;
- [x] explicit certificate construction relation;
- [x] explicit candidate selector relation;
- [x] explicit successor realizer relation;
- [x] realizer-to-typed-update proof obligation;
- [x] explicit trust-anchor premise, soundness, and preservation;
- [x] explicit resource premise and soundness;
- [x] explicit successor-domain closure law;
- [x] one-step conditional architecture successor theorem;
- [x] complete RCLM and forgotten RCP obligations in the theorem result;
- [x] recovery-law and monitor-refinement evidence in the theorem result;
- [x] explicit architecture successor-availability premise;
- [x] conditional infinite architecture trajectory theorem;
- [x] conversion to RCLM-checker and core-checker accepted trajectories;
- [x] concrete Gate B engine with one strict improvement and stable continuation;
- [x] concrete availability proof on the declared binary architecture domain;
- [ ] exact identity with every pinned Paper II direct-engine object and semantic
  assumption;
- [ ] arbitrary learned-system generator/certifier/selector/realizer refinement;
- [ ] indefinitely strict useful-successor completeness.

```text
Conditional structural Paper II-facing architecture theorem: IMPLEMENTED
Concrete Gate B direct-engine reference: IMPLEMENTED
Exact full Paper II theorem equivalence: NOT COMPLETE
```

### Gate C — finite-dimensional quantum extension

Required:

- density-matrix state conditions;
- admissible channel/update conditions;
- von Neumann or quantum relative entropy;
- support/domain conditions;
- non-loss and recovery theorem;
- explicit imported matrix-analysis assumptions.

## Licensing the executable phase

The present formal work still does not license the Python phase. The generic
architecture engine is relational and the concrete engine is a finite binary
reference. Before a runtime checker or generator is claimed as a theorem
refinement, the executable schemas and functions must map one-to-one to the Lean
objects and the untrusted generator must produce candidates rather than replay a
predeclared finite relation.

External benchmark work resumes only after a genuine predecessor-generated
successor package chain exists under that executable checker.

```text
Python checker licensed: false
Python generator licensed: false
Closed-loop runtime licensed: false
External benchmark phase licensed: false
```
