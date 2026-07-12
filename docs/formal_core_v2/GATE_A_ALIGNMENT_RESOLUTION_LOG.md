# Gate A paper-alignment resolution log

This log records theorem-strengthening work performed after the initial
line-by-line comparison in `GATE_A_PAPER_ALIGNMENT_AUDIT.md`. The original audit
remains an immutable description of the mismatch state at its comparison
baseline; this file is the authoritative status update for subsequently resolved
or partially resolved obligations.

## Current resolution status

```text
ALIGN-06 typed endpoint recovery composition: resolved at abstract Gate A level
ALIGN-03 Lyapunov/motion monitor composition: finite and uniform-prefix schema implemented
ALIGN-04 ambiguity and self-model relevance composition: finite and uniform-prefix schema implemented
Exact Paper I theorem equivalence: still false
Exact Paper II architecture theorem equivalence: still false
Gate A paper-alignment closure: not yet passed
```

## ALIGN-06 — typed endpoint recovery composition

The following declarations are now implemented:

```lean
RCP.RecoveryCompositionLaws
RCP.composedRecovery
RCP.composedRecovery_nonexpansive
RCP.finite_endpoint_recovery_bound
RCP.infinite_endpoint_recovery_prefix_bound
```

`RecoveryCompositionLaws` exposes exactly the additional abstract assumptions
used by the endpoint proof:

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
initial state. This is the endpoint theorem that the earlier
`finite_composed_recovery_bound` deliberately did not claim.

The abstract theorem is more general than the trace-distance/channel instance:
it assumes only the laws used by the proof. Gate B or Gate C must still identify
`stateDistance` and `recover` with the concrete classical or quantum objects used
by a paper-facing instantiation.

## ALIGN-03 and ALIGN-04 — explicit paper monitor schema

The new `RCP.PreservationMonitors` structure gives separate theorem-facing data
for:

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

It also requires explicit one-step soundness theorems from
`RCP.StepObligations`; generic residual nonpositivity is not silently treated as
one of these quantitative statements.

The finite composition theorems are:

```lean
RCP.finite_lyapunov_motion_bound
RCP.finite_ambiguity_collapse_bound
RCP.finite_self_model_relevance_bound
```

For an infinite accepted path, every finite prefix inherits these bounds through:

```lean
RCP.infinite_lyapunov_motion_prefix_bound
RCP.infinite_ambiguity_collapse_prefix_bound
RCP.infinite_self_model_relevance_prefix_bound
```

`RCP.UniformMonitorBudgetCaps` states explicit uniform caps on all finite partial
error budgets. Under those caps:

```lean
RCP.infinite_monitor_uniform_bounds
RCP.infinite_cumulative_motion_bounded
```

prove the corresponding uniform finite-prefix conclusions. This is the
bounded-partial-sum form needed by the abstract kernel. A later paper-facing
refinement must still prove that the concrete nonnegative error sequences are
summable in the standard analytic sense and that their partial sums satisfy
these caps.

## Clean build evidence

The endpoint and monitor implementation at source head
`fb4e0d8437ca62cf89d97811eba21be395a1122e` passed the pinned workflow:

```text
GitHub Actions run: 29186485073
artifact: formal-core-v2-gate-a-audit-29186485073-1
artifact digest: sha256:f23a9fc7d7e5afda589c95d455dfcd842eb2e3cc5ea6877f86148e06af233114
```

The run completed the clean Lean build, no-admission scan, project-local axiom
scan, theorem axiom audit, and artifact upload successfully.

A subsequent audit-source update adds the new endpoint, monitor, and
infinite-prefix theorem names to `GateAAxiomAudit.lean`; its latest successful
workflow evidence supersedes the run above for the final audit list.

## Remaining Gate A paper-alignment work

The principal Gate A-only obligations now remaining are:

1. represent the exact Paper I state-safe-set and update-admissibility refinement;
2. represent the paper's no-op-feasibility premise or formally narrow that premise;
3. add a standard analytic `Summable`-to-uniform-cap bridge for the concrete
   nonnegative budget sequences, if the exact paper wording is retained;
4. introduce the final Paper I wrapper only after concrete KL/quantum and
   paper-semantic refinements are available.

Gate B must still supply the first nontrivial finite classical/diagonal
information-theoretic instance. Paper II still requires full RCLM field
preservation, checker refinement, and the architecture successor theorem.

No Python checker, successor generator, closed-loop runtime, or external
benchmark phase is licensed by these additions alone.
