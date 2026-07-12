# Formal Core v2 exit criteria

No Python checker, generator, closed-loop successor runtime, or external
benchmark phase begins until every item required for the claimed executable core
is satisfied.

## Global formal-core exit conditions

- [ ] The exact Paper I/Paper II theorem statements and mapped Lean declarations
  agree.
  - [x] The line-by-line comparison audit is complete.
  - [x] Every abstract Gate A mismatch has been represented or resolved.
  - [ ] Concrete Gate B/C and RCLM refinements resolve the remaining semantic
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
- [ ] Strict improvement is non-vacuous in a concrete instance and is not merely
  the introduction of a fresh index.
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
- [ ] Gate B includes a nontrivial finite classical/diagonal model with actual
  entropy/divergence, conservative extension, recovery, strict progress, and a
  concrete checker refinement.
- [x] The claimed abstract Gate A theorem source contains no `sorry` or `admit`.
- [x] No project-local `axiom` declaration or `sorryAx` occurs in the claimed
  abstract Gate A surface.
- [x] Lean and mathlib are pinned to exact immutable revisions.
- [x] `lake-manifest.json` is committed.
- [x] Clean GitHub CI builds the abstract Gate A project.
- [x] Source-admission and theorem-axiom audits are uploaded as workflow
  artifacts.
- [x] The theorem map, assumption register, and formalization manifest separate
  abstract Gate A completion from concrete paper mechanization.

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
Concrete Paper I theorem identification: DEFERRED TO GATES B/C
Paper II architecture theorem: DEFERRED TO SUBSTANTIVE RCLM REFINEMENT
```

### Gate B — concrete finite classical/diagonal instantiation

Required:

- actual finite probability distributions;
- actual Shannon entropy and KL divergence or an explicitly equivalent finite
  information quantity;
- support and zero-mass conditions;
- KL/non-loss laws;
- conservative extension and constructive recovery;
- a nonconstant worked example;
- a semantically meaningful strict-progress witness;
- concrete paper-monitor meanings where the classical instance claims them;
- concrete checker refinement for the declared finite packet grammar.

### Gate C — finite-dimensional quantum extension

Required:

- density-matrix state conditions;
- admissible channel/update conditions;
- von Neumann or quantum relative entropy;
- support/domain conditions;
- non-loss and recovery theorem;
- explicit imported matrix-analysis assumptions.

## Licensing the executable phase

The first executable checker remains unlicensed until Gate B and the concrete
checker refinement are complete and the checker input schema has a one-to-one
theorem map. The first successor generator and fail-closed loop remain
unlicensed until substantive RCLM refinement is defined. External benchmark
work resumes only after a genuine predecessor-generated successor chain exists
under that checker.
