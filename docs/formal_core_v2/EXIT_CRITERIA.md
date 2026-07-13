# Formal Core v2 exit criteria

No Python checker, generator, closed-loop successor runtime, or external
benchmark phase begins until every item required for the claimed executable core
is satisfied.

## Global formal-core exit conditions

- [ ] The exact Paper I/Paper II theorem statements and mapped Lean declarations
  agree.
  - [x] The line-by-line comparison audit is complete.
  - [x] Every abstract Gate A mismatch is represented or resolved.
  - [x] Gate B resolves the declared finite classical/KL reference obligations.
  - [x] The substantive Gate B RCLM-to-RCP refinement is implemented.
  - [x] The conditional architecture successor/direct-engine theorem is
    implemented with explicit engine premises.
  - [x] The Paper II robust-reflective interfaces and remaining semantic premises
    are explicit.
  - [x] The bounded seed-library, packet grammar, packet builder, verifier-schema,
    uncertainty-envelope, and goal-transport refinements are implemented at the
    finite binary reference scope.
  - [ ] Gate C and exact Paper I/Paper II semantic refinements resolve the
    remaining mismatches.
- [x] Every assumption used by the implemented theorem surfaces is explicit in a
  structure, proposition, equality refinement, or theorem parameter.
- [x] Every Gate A kernel exhibits a nonconstant protected-value function.
- [x] Every Gate A kernel exhibits a nonconstant residual evaluator.
- [x] Reality containment is substantive and every Gate A kernel exhibits a
  packet for which it fails.
- [x] Trust, resource, and reality gates are propositions rather than booleans
  assigned true by construction.
- [x] Checker soundness proves `check = true -> formal successor obligations`.
- [x] Recovery is constructive and tied to the actual accepted update.
- [x] Composed endpoint recovery is proved under explicit self-zero, triangle,
  and nonexpansiveness laws.
- [x] Strict improvement is non-vacuous in the finite Gate B instance and is not
  merely a fresh index.
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
- [x] The conditional architecture successor theorem returns complete RCLM and
  forgotten RCP obligations plus recovery/monitor refinement evidence.
- [x] The architecture infinite theorem carries explicit successor availability.
- [x] The finite bounded seed library is represented by actual `Finset` witness
  and grammar objects.
- [x] Grammar nonemptiness on the seed domain is explicit and is not inferred
  from checker soundness.
- [x] Every active grammar word is bounded by declared update-word and proof-word
  limits.
- [x] Every active grammar word supplies proposal, certificate, selection,
  realization, resource, and checker evidence.
- [x] Successor seed-domain persistence is explicit and is not inferred from
  accepted continuation alone.
- [x] Declared verifier schemas, uncertainty envelopes, goals, transports,
  refinement relations, distances, and budgets are identified with compiled
  interfaces by equality proofs.
- [x] The generic bounded packet-builder theorem returns complete RCLM and Paper
  II successor-verification obligations.
- [x] The architecture bridge returns complete forgotten RCP obligations.
- [x] A conditional infinite bounded seed-library trajectory is constructed from
  explicit grammar nonemptiness and successor seed-domain closure.
- [x] The concrete binary grammar is `{improve}` at `initial` and `{stabilize}` at
  `target`; the rejected word is absent.
- [x] The concrete grammar and proof depth bounds are both one.
- [ ] A theorem establishes useful strict improvement at every recursive step.
  The current binary path becomes stable after its first strict step.
- [x] The audited source contains no `sorry` or `admit`.
- [x] No project-local `axiom` declaration or `sorryAx` occurs in the audited
  theorem surfaces.
- [x] Lean and mathlib are pinned to exact immutable revisions.
- [x] `lake-manifest.json` is committed.
- [x] Clean GitHub CI builds the formal project.
- [x] Source-admission and theorem-axiom audits are uploaded as workflow
  artifacts.

## Gate A — abstract theorem kernel

```text
Abstract Gate A theorem kernel: COMPLETE
Concrete Paper I theorem identification: PARTIALLY DISCHARGED BY GATE B
```

## Gate B — finite classical/diagonal instantiation

Delivered:

- [x] normalized finite distributions;
- [x] actual Shannon entropy and finite KL divergence;
- [x] support-aware KL nonnegativity and self-zero;
- [x] positive nonconstant binary KL witness;
- [x] zero-coordinate conservative extension;
- [x] exact support, Shannon, and KL preservation;
- [x] exact constructive recovery;
- [x] substantive finite state/update/certificate/residual types;
- [x] KL-derived strict progress;
- [x] concrete monitor meanings with explicit semantic limits;
- [x] concrete Boolean checker and complete obligation refinement;
- [x] invalid-candidate rejection;
- [x] binary recovery composition laws;
- [x] nontrivial trajectory `initial -> target -> target`;
- [x] dedicated theorem-axiom audit.

```text
Gate B finite classical reference scope: COMPLETE
Exact Paper I main theorem: NOT COMPLETE
```

## Substantive RCLM refinement

Delivered at the Gate B classical scope:

- [x] substantive typed architecture state, update, and certificate fields;
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

## Conditional architecture successor/direct-engine theorem

Delivered:

- [x] explicit architecture theorem domain;
- [x] explicit witness coverage, generator, certifier, selector, and realizer;
- [x] realizer-to-typed-update proof obligation;
- [x] explicit trust-anchor and resource soundness;
- [x] explicit successor-domain closure;
- [x] complete RCLM and forgotten RCP obligations;
- [x] recovery-law and monitor-refinement evidence;
- [x] explicit architecture successor availability;
- [x] conditional infinite architecture trajectory;
- [x] concrete Gate B direct-engine reference;
- [ ] arbitrary learned-system engine refinement;
- [ ] indefinitely strict useful-successor completeness.

## Bounded seed-library and packet-builder refinement

Delivered:

- [x] generic finite witness library;
- [x] generic finite certificate-word grammar;
- [x] explicit maximum update-word and proof-word lengths;
- [x] seed-domain to architecture-domain refinement;
- [x] grammar nonemptiness premise;
- [x] word-to-witness membership and witness coverage;
- [x] proposal, certificate, candidate, realization, resource, and checker
  relations for every active word;
- [x] successor seed-domain closure;
- [x] packet-to-architecture-step construction;
- [x] packet-builder soundness theorem;
- [x] RCLM-to-RCP architecture refinement theorem for bounded packets;
- [x] verifier-schema semantic identification;
- [x] uncertainty-envelope semantic identification;
- [x] goal and goal-transport semantic identification;
- [x] conditional infinite bounded seed-library trajectory;
- [x] concrete binary singleton grammars;
- [x] concrete rejected-word exclusion;
- [x] concrete initial strict packet and target stability packet;
- [x] concrete infinite seed-domain preservation;
- [ ] unbounded grammar or proof-search completeness;
- [ ] arbitrary learned-system seed-domain entry;
- [ ] arbitrary learned generator coverage.

```text
Bounded seed-library reference refinement: COMPLETE AT DECLARED BINARY SCOPE
Exact full Paper II seed-library theorem identity: NOT COMPLETE
```

## Gate C — finite-dimensional quantum extension

Required:

- density-matrix state conditions;
- admissible channel/update conditions;
- von Neumann or quantum relative entropy;
- support/domain conditions;
- non-loss and recovery theorem;
- explicit imported matrix-analysis assumptions.

## Licensing the executable phase

The current Lean work does not license the Python phase. The finite grammar and
packet builder are theorem objects, not an external generator implementation.
Before a runtime checker or generator is claimed as a refinement, executable
schemas and functions must map one-to-one to the Lean objects and an untrusted
predecessor-driven generator must produce candidates rather than replay a
predeclared finite relation.

```text
Python checker licensed: false
Python generator licensed: false
Closed-loop runtime licensed: false
External benchmark phase licensed: false
```
