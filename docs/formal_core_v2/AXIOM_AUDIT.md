# Formal Core v2 — Gate A proof-admission and axiom audit

This audit distinguishes three different questions that must not be conflated:

1. **Does the source contain admitted proof placeholders?**
2. **Does the project declare any new axioms?**
3. **Which foundational axioms does each compiled public theorem actually use?**

A successful `lake build` answers none of those questions by itself. The Formal
Core v2 workflow therefore runs and preserves a separate audit after building.

## Audited source scope

The no-admission and user-axiom scans cover the v2 Lean source tree:

```text
lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2.lean
lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/**/*.lean
```

Generated dependencies under `.lake/` are excluded. The scan fails on the proof
placeholder tokens `sorry` or `admit`, and on project-local declarations beginning
with `axiom`.

## Audited public Gate A theorems

The kernel-generated `#print axioms` report covers:

```lean
RCP.accepted_step_sound
RCP.finite_trajectory_closure
RCP.finite_trajectory_step_sound
RCP.finite_progress_monotone
RCP.finite_composed_nonloss_bound
RCP.finite_composed_recovery_bound
RCP.conditional_infinite_trajectory_exists
```

The exact output is preserved by GitHub Actions as the
`formal-core-v2-gate-a-audit-*` workflow artifact.

## Acceptance rule

Gate A audit passes only when:

```text
no project source contains sorry or admit
no project-local axiom declaration is present
all audit declarations elaborate under the pinned Lean/mathlib graph
no #print axioms report contains sorryAx
all audit reports are uploaded even when a later audit check fails
```

## Interpretation of foundational dependencies

The conditional infinite trajectory is constructed from the explicit
`SuccessorAvailability` hypothesis, whose result is a `Nonempty` accepted
successor. Selecting a concrete successor from that proposition is deliberately
`noncomputable` and may expose `Classical.choice` in the axiom report. That is not
hidden generator completeness: the availability hypothesis remains visible in
the theorem statement.

Any other reported foundational dependency must be read from the generated
artifact and reviewed before Gate A is called closed. In particular:

```text
sorryAx is prohibited
project-local undeclared axioms are prohibited
checker soundness may not imply successor availability
abstract Gate A may not be relabeled as a concrete KL or quantum theorem
```

## Reproduction

After `lake build` succeeds, run from
`lean/rcp_rclm_formal_core_v2`:

```text
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
```

The CI workflow additionally performs the source scans and uploads the reports.
