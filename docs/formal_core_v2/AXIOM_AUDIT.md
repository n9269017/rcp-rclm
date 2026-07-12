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

The exact output is preserved by GitHub Actions as a
`formal-core-v2-gate-a-audit-*` workflow artifact.

## Recorded successful audit

The first complete Gate A composition-and-audit run passed with the following
immutable evidence:

```text
Formal Core source commit:
  2b68a0048482ad481dfe6b05ce3c5a3262c7a08a

GitHub Actions run:
  29184258470

PR merge-test commit used by the runner:
  05ed9721db8abc0adb1f5d30ceea13ab2b57a914

Toolchain:
  leanprover/lean4:v4.31.0

Resolved lake-manifest SHA-256:
  c17842b8da89c8c84beed4e8b33892616ef75c15475133a07aca97c16d853b0a

Audit artifact:
  formal-core-v2-gate-a-audit-29184258470-1

Artifact digest:
  sha256:3a4654e730c6ee5d1c87c723fc66a2b79d74e9642e380e9eb8dce95ac7053470
```

The preserved reports establish:

```text
PASS: clean build completed successfully (1938 jobs)
PASS: no sorry or admit token occurs in the Formal Core v2 Lean source
PASS: no project-local axiom declaration occurs in the Formal Core v2 Lean source
PASS: every audited theorem elaborates
PASS: no audited theorem reports sorryAx
```

For every audited public Gate A theorem, Lean reported exactly:

```lean
[propext, Classical.choice, Quot.sound]
```

Thus the current abstract Gate A theorem set is **not axiom-free**; it uses the
listed standard Lean/mathlib foundational principles. It introduces no
project-local axiom and contains no admitted proof. This precise statement
replaces any looser claim that a clean build alone made the theorem set
assumption-free.

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
`noncomputable` and uses classical choice. The availability hypothesis remains
visible in the theorem statement and is not inferred from checker soundness.

The `#print axioms` command reports transitive theorem dependencies; it does not
by itself attribute each foundational axiom to a single source expression. The
recorded result is therefore stated extensionally: all seven public Gate A
theorems depend on `propext`, `Classical.choice`, and `Quot.sound`, and none
depends on `sorryAx`.

The following inferences remain prohibited:

```text
checker soundness ⇒ successor availability
abstract Gate A ⇒ concrete KL theorem
abstract Gate A ⇒ finite-dimensional quantum theorem
aggregate local recovery bound ⇒ undeclared endpoint rollback map
clean build ⇒ empirical RSI
```

## Reproduction

After `lake build` succeeds, run from
`lean/rcp_rclm_formal_core_v2`:

```text
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
```

The CI workflow additionally performs the source scans and uploads all reports.
