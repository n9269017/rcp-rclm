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
  - [ ] Gate C and substantive RCLM refinements resolve the remaining semantic
    mismatches.
- [x] Every assumption used by the abstract Gate A theorem surface is explicit in
  a structure, proposition, or theorem parameter.
- [x] Every Gate A kernel must exhibit a nonconstant protected-value function.
- [x] Every Gate A kernel must exhibit a nonconstant residual evaluator; a
  globally zero residual function is excluded.
- [x] Reality containment is a substantive proposition and every Gate A kernel
  must exhibit at least one packet for which it fails; an identically `True`
  gate is excluded.
- [x] Trust, resource, and reality gates are propositions rather than booleans
  assigned true by construction.
- [x] Checker soundness proves `check = true → formal successor obligations`.
- [x] Recovery is constructive and tied to the actual accepted update.
- [x] The composed endpoint recovery theorem is proved under explicit
  zero-distance, triangle, and nonexpansiveness laws.
- [x] Strict improvement is non-vacuous in a concrete instance and is not merely
  the introduction of a fresh index. The Gate B witness strictly reduces actual
  KL distance to the target distribution.
- [x] Abstract finite accepted-trajectory composition is proved.
- [x] Abstract infinite-horizon closure is proved only under explicit successor
  availability.
- [x] Paper-facing safe-set/update-admissibility equivalences and no-op
  feasibility are explicit Gate A premises.
- [x] Finite Lyapunov/motion, ambiguity-collapse, and transported
  self-model-relevance composition is proved abstractly.
- [x] Standard summability assumptions on nonnegative monitor budgets are bridged
  to uniform finite-prefix bounds.
- [ ] RCLM-to-RCP refinement is proved for substantive states, updates,
  certificates, monitor/recovery laws, and checker acceptance.
- [x] Gate B includes a nontrivial finite classical/diagonal model with actual
  entropy/divergence, conservative extension, recovery, strict progress, and a
  concrete checker refinement.
- [x] The claimed Gate A and Gate B theorem source contains no `sorry` or `admit`.
- [x] No project-local `axiom` declaration or `sorryAx` occurs in the audited Gate
  A or Gate B surface.
- [x] Lean and mathlib are pinned to exact immutable revisions.
- [x] `lake-manifest.json` is committed.
- [x] Clean GitHub CI builds the Gate A and Gate B project.
- [x] Source-admission and theorem-axiom audits are uploaded as workflow
  artifacts.
- [x] The theorem map, assumption register, closure records, and formalization
  manifest separate abstract Gate A, finite Gate B, and remaining paper/RCLM
  obligations.

## Gate-specific release conditions

### Gate A — abstract theorem kernel

Implemented:

- lawful and non-vacuous protected-value interface;
- candidate/state/certificate-dependent nonconstant residual interface;
- substantive reality-containment proposition;
- constructive one-step recovery;
- explicit recovery composition laws and endpoint rollback theorem;
- progress and strict-witness interface;
- certificate packet and trusted checker soundness;
- finite domain/invariant, progress, protected-value, recovery, and strict-witness
  composition;
- explicit Lyapunov/motion, ambiguity, and self-model-relevance monitor schema;
- finite monitor composition;
- conditional infinite accepted trajectory under `SuccessorAvailability`;
- finite-prefix endpoint and monitor preservation on infinite paths;
- `Summable`-to-uniform-budget-cap bridge;
- explicit paper state-safe/update-admissibility refinement boundary;
- explicit accepted no-op premise;
- finite and conditional infinite paper-facing abstract wrapper theorems.

```text
Abstract Gate A theorem kernel: COMPLETE
Concrete Paper I theorem identification: PARTIALLY DISCHARGED BY GATE B
Paper II architecture theorem: DEFERRED TO SUBSTANTIVE RCLM REFINEMENT
```

### Gate B — concrete finite classical/diagonal instantiation

Delivered:

- [x] actual finite probability distributions;
- [x] actual Shannon entropy and finite KL divergence;
- [x] explicit support and zero-mass conditions;
- [x] support-aware KL nonnegativity and self-divergence zero;
- [x] a proved nonconstant positive binary KL witness;
- [x] zero-coordinate conservative extension;
- [x] exact preservation of support, Shannon entropy, and KL for that extension;
- [x] exact constructive recovery of the predecessor distribution;
- [x] a substantive finite state/update/certificate/residual model;
- [x] a semantically meaningful strict-progress witness based on KL reduction;
- [x] concrete finite monitor meanings for the claims made by the binary instance;
- [x] explicit documentation that those monitor meanings are not Paper I
  expectation, semantic ambiguity, or mutual information;
- [x] a concrete Boolean packet grammar;
- [x] a proof that Boolean acceptance refines to complete `StepObligations`;
- [x] explicit invalid-candidate rejection;
- [x] discrete recovery composition laws and an endpoint theorem instance;
- [x] a nontrivial accepted finite trajectory `initial → target → target`;
- [x] dedicated Gate B theorem-axiom audit.

```text
Gate B finite classical reference scope: COMPLETE
Exact Paper I main theorem: NOT YET COMPLETE
Substantive RCLM refinement: NEXT
```

The closure boundary and non-claims are fixed in
`docs/formal_core_v2/GATE_B_CLOSURE.md`.

### Gate C — finite-dimensional quantum extension

Required:

- density-matrix state conditions;
- admissible channel/update conditions;
- von Neumann or quantum relative entropy;
- support/domain conditions;
- non-loss and recovery theorem;
- explicit imported matrix-analysis assumptions.

### Substantive RCLM refinement

Required after Gate B and strengthened after Gate C:

- every theorem-relevant RCLM state field has a substantive type and invariant;
- RCLM updates refine the selected RCP update semantics;
- RCLM certificates refine the RCP packet grammar and monitor evidence;
- recovery, protected transport, progress, trust, resource, and reality fields are
  preserved by forgetting;
- RCLM checker acceptance implies the concrete RCP checker obligations;
- the architecture successor theorem keeps generator/certifier/selector/realizer
  premises explicit.

## Licensing the executable phase

Gate B completion alone does not license Python execution. The first executable
checker remains unlicensed until the substantive RCLM checker refinement is
proved and its input schema has a one-to-one theorem map. The first successor
generator and fail-closed loop remain unlicensed until the architecture-level
refinement and generation premises are formalized. External benchmark work
resumes only after a genuine predecessor-generated successor chain exists under
that checker.

```text
Python checker licensed: false
Python generator licensed: false
Closed-loop runtime licensed: false
External benchmark phase licensed: false
```