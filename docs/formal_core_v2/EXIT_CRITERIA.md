# Formal Core v2 exit criteria

No Python checker, generator, closed-loop successor runtime, or external benchmark
phase begins until every item below is satisfied for the claimed core.

- [ ] The exact Paper I/Paper II theorem statements and mapped Lean declarations agree.
- [ ] Every theorem assumption is represented explicitly in a structure, parameter, or typeclass.
- [ ] The core divergence/non-loss quantity is nonconstant.
- [ ] Certificate residuals are computed from state/candidate/evidence, not fixed at zero.
- [ ] Reality containment is a substantive predicate with supplied evidence, not `True`.
- [ ] Architecture gates are propositions or evidence objects, not booleans assigned true by construction.
- [ ] Checker soundness proves `check = true → formal successor obligations`.
- [ ] Recovery is constructive and tied to the actual accepted update.
- [ ] Strict improvement is non-vacuous and not merely the introduction of a fresh index.
- [ ] Finite accepted-trajectory composition is proved.
- [ ] Infinite-horizon closure is proved only under an explicit successor-availability assumption.
- [ ] RCLM-to-RCP refinement is proved for substantive states, updates, and certificates.
- [ ] Gate B includes a nontrivial finite classical/diagonal model with actual entropy/divergence.
- [ ] The claimed theorem core contains no `sorry`.
- [ ] Remaining axioms, if any, are isolated, named, documented, and visible in final assumptions.
- [ ] Lean and mathlib are pinned to exact immutable revisions.
- [ ] `lake-manifest.json` is committed.
- [ ] `lake build` succeeds from a clean checkout.
- [ ] An axiom audit and a `sorry` audit are preserved as build artifacts.
- [ ] The formalization manifest and theorem map accurately state delivered versus planned scope.

## Gate-specific release conditions

### Gate A — abstract theorem kernel

- lawful divergence/non-loss interfaces;
- constructive recovery interface;
- progress and strict-witness interface;
- certificate packet and computed residual interface;
- checker soundness;
- finite composition;
- conditional infinite trajectory construction.

### Gate B — concrete finite classical/diagonal instantiation

- actual finite probability distributions;
- actual Shannon entropy and KL divergence or an explicitly equivalent finite
  information quantity;
- support/zero-mass conditions stated explicitly;
- conservative extension and recovery theorem;
- nonconstant worked example with kernel-checked proof.

### Gate C — finite-dimensional quantum extension

- density-matrix state conditions;
- admissible channel/update conditions;
- von Neumann or quantum relative entropy definition;
- support/domain conditions;
- non-loss/recovery theorem;
- explicit statement of all imported matrix-analysis assumptions.

## Licensing the executable phase

The first executable checker may begin only when Gate A and Gate B are complete
and the checker input schema has a one-to-one theorem map. The first successor
generator and fail-closed loop may begin only after the checker refinement
obligation is defined. External benchmark work resumes only after a genuine
predecessor-generated successor chain exists under that checker.
