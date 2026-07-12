# Formal Core v2 — Gate A proof-admission and axiom audit

This audit distinguishes:

1. whether source contains admitted proofs;
2. whether the project declares new axioms; and
3. which foundational axioms the compiled public theorems use.

A successful build alone answers none of these questions, so the workflow
performs and preserves separate scans and `#print axioms` reports.

## Audited source scope

```text
lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2.lean
lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/**/*.lean
```

Generated dependencies under `.lake/` are excluded. The scan fails on `sorry`,
`admit`, or a project-local declaration beginning with `axiom`.

## Audited public abstract Gate A theorems

```lean
RCP.accepted_step_sound
RCP.finite_trajectory_closure
RCP.finite_trajectory_step_sound
RCP.finite_progress_monotone
RCP.finite_composed_nonloss_bound
RCP.finite_composed_recovery_bound
RCP.composedRecovery_nonexpansive
RCP.finite_endpoint_recovery_bound
RCP.finite_lyapunov_motion_bound
RCP.finite_ambiguity_collapse_bound
RCP.finite_self_model_relevance_bound
RCP.conditional_infinite_trajectory_exists
RCP.infinite_endpoint_recovery_prefix_bound
RCP.infinite_lyapunov_motion_prefix_bound
RCP.infinite_ambiguity_collapse_prefix_bound
RCP.infinite_self_model_relevance_prefix_bound
RCP.infinite_monitor_uniform_bounds
RCP.infinite_cumulative_motion_bounded
RCP.infinite_monitor_bounds_of_summable
RCP.infinite_cumulative_motion_bounded_of_summable
RCP.finite_paper_preservation
RCP.conditional_infinite_paper_trajectory_exists
```

The exact output is preserved as a `formal-core-v2-gate-a-audit-*` workflow
artifact.

## Complete abstract Gate A audit evidence

```text
Source head:
  dd71e12438fd1f8e3508061981ab11b5e7fa7028

GitHub Actions run:
  29187317488

PR merge-test commit used by the runner:
  80811f1fa4102841688a97ead6591fd0f41301aa

Toolchain:
  leanprover/lean4:v4.31.0

Resolved lake-manifest SHA-256:
  c17842b8da89c8c84beed4e8b33892616ef75c15475133a07aca97c16d853b0a

Paper I blob:
  084eae21d252d205d2012b62744c1506644e3e58

Paper II blob:
  9b51be8294ad79fd4f63522b01e0f617f0bf2ffd

Audit artifact:
  formal-core-v2-gate-a-audit-29187317488-1

Artifact digest:
  sha256:1082c28af4911b4b9e8c0fcd1a8b2c288c55a44a5c8947de5b172b2633eb39d5
```

The preserved reports establish:

```text
PASS: paper blobs and mapped theorem surfaces are pinned
PASS: clean build completed successfully (1941 jobs)
PASS: no sorry or admit token occurs in project source
PASS: no project-local axiom declaration occurs in project source
PASS: every audited theorem elaborates
PASS: no audited theorem reports sorryAx
```

For every theorem in the expanded public Gate A list, Lean reported exactly:

```lean
[propext, Classical.choice, Quot.sound]
```

Thus the abstract Gate A theorem set is not axiom-free: it uses these standard
Lean/mathlib foundational principles. It introduces no project-local axiom and
contains no admitted proof.

## Why classical choice remains visible

The conditional infinite trajectory is selected from the explicit
`SuccessorAvailability` premise, which returns `Nonempty` accepted successors.
Selecting a concrete path is deliberately noncomputable and uses classical
choice. The availability premise remains visible and is never derived from
checker soundness.

The summability theorems also use mathlib's infinite-sum infrastructure. The
axiom report is transitive and is therefore stated extensionally rather than
assigning each foundational axiom to one source line.

## Acceptance rule

The abstract Gate A audit passes only when:

```text
no source contains sorry or admit
no project-local axiom declaration is present
all audited declarations elaborate under the pinned graph
no axiom report contains sorryAx
audit artifacts are uploaded even on failure
```

## Prohibited inferences

```text
checker soundness ⇒ successor availability
abstract Gate A ⇒ concrete finite KL
abstract Gate A ⇒ finite-dimensional quantum relative entropy
abstract PaperSemantics ⇒ concrete Paper I semantics without a refinement proof
abstract endpoint recovery ⇒ trace-distance/channel recovery without an instance
clean build ⇒ executable RSI or empirical evidence
```

## Reproduction

After a successful build, run from `lean/rcp_rclm_formal_core_v2`:

```text
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
```

The workflow additionally performs the source scans and uploads all reports.
