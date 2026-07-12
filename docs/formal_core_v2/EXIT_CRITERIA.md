# Formal Core v2 exit criteria

No Python checker, generator, closed-loop successor runtime, or external benchmark
phase begins until every item below is satisfied for the claimed core.

- [ ] The exact Paper I/Paper II theorem statements and mapped Lean declarations agree.
  - [x] The line-by-line comparison audit is complete.
  - [ ] Every recorded mismatch has been resolved by theorem strengthening, paper
    narrowing, or an explicit named assumption.
- [ ] Every theorem assumption is represented explicitly in a structure, parameter,
  or typeclass.
- [ ] The core divergence/non-loss quantity is nonconstant.
- [ ] Certificate residuals are computed from state/candidate/evidence, not fixed at
  zero.
- [ ] Reality containment is a substantive predicate with supplied evidence, not
  `True`.
- [ ] Architecture gates are propositions or evidence objects, not booleans assigned
  true by construction.
- [x] Checker soundness proves `check = true → formal successor obligations` for the
  current abstract Gate A checker.
- [x] Recovery is constructive and tied to the actual accepted update at one step.
- [ ] The paper-facing composed endpoint recovery theorem is proved with explicit
  metric, typing, and nonexpansiveness assumptions.
- [ ] Strict improvement is non-vacuous and not merely the introduction of a fresh
  index in a concrete instance.
- [x] Abstract finite accepted-trajectory composition is proved.
- [x] Abstract infinite-horizon closure is proved only under an explicit
  successor-availability assumption.
- [ ] RCLM-to-RCP refinement is proved for substantive states, updates, certificates,
  and checker acceptance.
- [ ] Gate B includes a nontrivial finite classical/diagonal model with actual
  entropy/divergence.
- [x] The currently claimed abstract Gate A theorem source contains no `sorry`.
- [x] Current foundational dependencies are isolated and preserved in the axiom
  audit; no project-local axiom declaration or `sorryAx` occurs.
- [x] Lean and mathlib are pinned to exact immutable revisions.
- [x] `lake-manifest.json` is committed.
- [x] `lake build` succeeds from a clean checkout for the current abstract kernel.
- [x] An axiom audit and a `sorry` audit are preserved as build artifacts.
- [x] The formalization manifest and theorem map accurately state the current
  abstract delivered scope and the paper-alignment gaps.

The authoritative comparison and obligation ledger are in
`GATE_A_PAPER_ALIGNMENT_AUDIT.md`. A checked item above is local to the stated
abstract scope and must not be read as completion of the full paper theorem stack.

## Gate-specific release conditions

### Gate A — abstract theorem kernel

Delivered and clean-CI-audited:

- lawful divergence/non-loss interfaces;
- constructive one-step recovery interface;
- progress and strict-witness interface;
- certificate packet and computed residual interface;
- checker soundness;
- finite domain/invariant, progress, protected-value, and aggregate local-recovery
  composition;
- conditional infinite accepted-trajectory construction.

Required before paper-aligned Gate A closure:

- explicit safe-set/update-admissibility refinement for Paper I;
- no-op-feasibility wrapper or documented paper narrowing;
- paper-monitor schema for Lyapunov drift, squared motion, ambiguity collapse,
  self-model relevance, and summability;
- typed endpoint recovery-map composition;
- resolved mapping of each remaining Paper I/Paper II mismatch.

### Gate B — concrete finite classical/diagonal instantiation

- actual finite probability distributions;
- actual Shannon entropy and KL divergence or an explicitly equivalent finite
  information quantity;
- support/zero-mass conditions stated explicitly;
- conservative extension and recovery theorem;
- nonconstant worked example with kernel-checked proof;
- concrete checker refinement for the declared finite packet grammar.

### Gate C — finite-dimensional quantum extension

- density-matrix state conditions;
- admissible channel/update conditions;
- von Neumann or quantum relative entropy definition;
- support/domain conditions;
- non-loss/recovery theorem;
- explicit statement of all imported matrix-analysis assumptions.

## Licensing the executable phase

The first executable checker may begin only when Gate A and Gate B are complete and
the checker input schema has a one-to-one theorem map. The first successor generator
and fail-closed loop may begin only after the checker refinement obligation is defined.
External benchmark work resumes only after a genuine predecessor-generated successor
chain exists under that checker.
