# Gate A paper-alignment resolution log

This log records theorem-strengthening work performed after the initial
line-by-line comparison in `GATE_A_PAPER_ALIGNMENT_AUDIT.md`. The original audit
remains a description of the mismatch state at its comparison baseline; this
file is authoritative for subsequently resolved or partially resolved
obligations.

## Current resolution status

```text
ALIGN-01 safe-set/update-admissibility boundary: represented by explicit equivalence structure
ALIGN-02 no-op feasibility: represented by explicit accepted unchanged-successor premise
ALIGN-03 Lyapunov/motion and summability composition: implemented abstractly
ALIGN-04 ambiguity and self-model relevance composition: implemented abstractly
ALIGN-06 typed endpoint recovery composition: resolved at abstract Gate A level
Abstract Gate A theorem kernel: complete, subject to final clean-CI audit of the synchronized head
Exact Paper I theorem equivalence: still false pending concrete semantic/information refinements
Exact Paper II architecture theorem equivalence: still false
Full formal-core release closure: not yet passed
```

## ALIGN-06 — typed endpoint recovery composition

Implemented declarations:

```lean
RCP.RecoveryCompositionLaws
RCP.composedRecovery
RCP.composedRecovery_nonexpansive
RCP.finite_endpoint_recovery_bound
RCP.infinite_endpoint_recovery_prefix_bound
```

`RecoveryCompositionLaws` exposes exactly the additional assumptions used by the
endpoint proof:

```text
zero self-distance
triangle inequality
nonexpansiveness of every candidate-tied recovery map
```

For a finite accepted trajectory, `composedRecovery` is the rollback-order
composition

```text
R₀ ∘ R₁ ∘ ... ∘ Rₜ₋₁.
```

`finite_endpoint_recovery_bound` proves that applying this composition to the
state at time `t` returns within the cumulative declared recovery budget of the
initial state. The older `finite_composed_recovery_bound` remains a separate
aggregate local-error theorem.

The abstract theorem assumes only the laws used by the proof. Gate B or Gate C
must identify `stateDistance` and `recover` with concrete classical or quantum
objects before a trace-distance/channel statement is claimed.

## ALIGN-03 and ALIGN-04 — explicit paper monitor schema

`RCP.PreservationMonitors` gives separate theorem-facing data for:

```text
Lyapunov value
charged squared-motion term
Lyapunov error budget
unsupported ambiguity collapse
ambiguity-collapse budget
self-model relevance object and value
cross-time self-model relevance transport
self-model relevance loss budget
```

Every one-step monitor inequality is an explicit theorem from
`RCP.StepObligations`; generic residual nonpositivity is not silently
reinterpreted as one of these quantitative statements.

Finite composition:

```lean
RCP.finite_lyapunov_motion_bound
RCP.finite_ambiguity_collapse_bound
RCP.finite_self_model_relevance_bound
```

Infinite-path finite-prefix composition:

```lean
RCP.infinite_lyapunov_motion_prefix_bound
RCP.infinite_ambiguity_collapse_prefix_bound
RCP.infinite_self_model_relevance_prefix_bound
RCP.infinite_monitor_uniform_bounds
RCP.infinite_cumulative_motion_bounded
```

The standard analytic bridge is now explicit:

```lean
RCP.SummableMonitorBudgets
RCP.SummableMonitorBudgets.toUniformMonitorBudgetCaps
RCP.infinite_monitor_bounds_of_summable
RCP.infinite_cumulative_motion_bounded_of_summable
```

Summability is assumed for the three concrete nonnegative error sequences; the
bridge proves that every finite partial budget is bounded by the corresponding
`tsum`, then applies the uniform-prefix theorems. Concrete probability,
ambiguity, and mutual-information semantics remain separate refinement
obligations.

## ALIGN-01 and ALIGN-02 — paper-facing predicates and no-op premise

`RCP.PaperSemantics` carries the paper-facing state-safe and update-admissibility
predicates together with explicit equivalences to:

```text
K.admissible state ∧ K.protectedInvariant state
StepObligations K state candidate certificate
```

The equivalences are theorem assumptions to be discharged by a concrete Paper I
refinement; they are not established by naming fields.

`RCP.AcceptedNoOp` and `RCP.NoOpFeasible` represent the paper's no-op premise as
an accepted unchanged-successor packet at every paper-safe state. No-op
feasibility remains distinct from general successor availability.

The paper-facing wrappers are:

```lean
RCP.finite_paper_preservation
RCP.conditional_infinite_paper_trajectory_exists
```

The finite wrapper combines safe-set closure, update-admissibility of every
accepted prefix step, no-op availability, monotone/strict progress, protected
non-loss, endpoint recovery, Lyapunov/motion, ambiguity, and transported
self-model relevance. The conditional infinite wrapper retains both
`SuccessorAvailability` and `NoOpFeasible` as visible premises.

## Build evidence to date

Endpoint recovery passed clean CI at source head
`15684a69977e667117faa6c223cbe8d723fb0b95`, workflow `29186121381`, artifact:

```text
formal-core-v2-gate-a-audit-29186121381-1
sha256:67441f83872020eb629f70cd34f0681d938b2b672c4d76bc5de342097f8de37d
```

The monitor, infinite-prefix, paper-contract, and summability code through source
head `cb579049b045213a95d505e39ca3e5d548ea82c1` passed workflow
`29186841285`, including clean build, source-admission scan, local-axiom scan,
and theorem-axiom audit. A final synchronized-head run with the expanded audit
list supersedes this evidence once complete.

## Remaining work after abstract Gate A

No abstract Gate A inference listed in the theorem contract remains merely an
untyped comment or an implicit inference. Remaining closure work belongs to the
cross-gate paper instantiation:

1. Gate B: finite classical/diagonal KL laws, conservative extension, concrete
   recovery, nonconstant witness, and checker refinement;
2. Gate C: finite-dimensional quantum state/channel, relative-entropy, support,
   and recovery laws;
3. Paper I concrete refinements identifying the abstract safe set, monitors,
   transports, and protected values with the pinned paper objects;
4. Paper II full RCLM field-preserving refinement, checker theorem, and
   architecture successor theorem;
5. final exact paper-facing wrapper after those refinements.

No Python checker, successor generator, closed-loop runtime, or external
benchmark phase is licensed by abstract Gate A completion alone.
