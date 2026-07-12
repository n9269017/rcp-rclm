# Formal Core v2 — proof-admission and axiom audit

This audit distinguishes:

1. whether project source contains admitted proofs;
2. whether the project declares new axioms; and
3. which foundational axioms the compiled public theorems use.

A successful build alone answers none of these questions, so the workflow
performs and preserves separate source scans and `#print axioms` reports.

## Audited source scope

```text
lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2.lean
lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/**/*.lean
```

Generated dependencies under `.lake/` are excluded. The scan fails on `sorry`,
`admit`, or a project-local declaration beginning with `axiom`.

## Gate A public theorem audit

The abstract Gate A audit covers 22 public declarations, including checker
soundness, finite composition, endpoint recovery, monitor composition,
conditional infinite trajectories, summability, and the paper-facing abstract
wrappers. Its source list is fixed in:

```text
docs/formal_core_v2/audit/GateAAxiomAudit.lean
```

The complete Gate A validation record remains:

```text
Source head:          dd71e12438fd1f8e3508061981ab11b5e7fa7028
Workflow run:         29187317488
Build:                1941 jobs, success
Audit artifact:       formal-core-v2-gate-a-audit-29187317488-1
Artifact SHA-256:     1082c28af4911b4b9e8c0fcd1a8b2c288c55a44a5c8947de5b172b2633eb39d5
```

Every audited Gate A theorem reported exactly:

```lean
[propext, Classical.choice, Quot.sound]
```

The use of classical choice remains visible because the conditional infinite
trajectory selects successors from the explicit `SuccessorAvailability`
`Nonempty` premise. Availability is never derived from checker soundness.

## Gate B public theorem audit

The finite classical Gate B audit covers 22 public declarations in:

```text
docs/formal_core_v2/audit/GateBAxiomAudit.lean
```

The audited surface includes:

```lean
RCP.ClassicalFinite.klDivergence_nonnegative
RCP.ClassicalFinite.klDivergence_self
RCP.ClassicalFinite.uniformBinary_kl_biasedBinary
RCP.ClassicalFinite.uniformBinary_kl_biasedBinary_pos
RCP.ClassicalFinite.shannonEntropy_extendByZero
RCP.ClassicalFinite.klDivergence_extendByZero
RCP.ClassicalFinite.recover_extendByZero
RCP.ClassicalFinite.conservative_extension_recovery
RCP.ClassicalFinite.binaryCheck_eq_true_iff
RCP.ClassicalFinite.binaryCheck_rejects_invalidCandidate
RCP.ClassicalFinite.binaryStateDistance_triangle
RCP.ClassicalFinite.initial_improvement_obligations
RCP.ClassicalFinite.target_stability_obligations
RCP.ClassicalFinite.binary_checker_refines_kernel
RCP.ClassicalFinite.binaryLyapunov_motion_step
RCP.ClassicalFinite.binaryUnsupportedCollapse_step
RCP.ClassicalFinite.binaryRelevance_step
RCP.ClassicalFinite.binaryWorkedTrajectory_first_step_strict
RCP.ClassicalFinite.binaryWorkedTrajectory_endpoint_recovery
RCP.ClassicalFinite.binaryWorkedTrajectory_lyapunov_motion_bound
RCP.ClassicalFinite.binaryWorkedTrajectory_ambiguity_bound
RCP.ClassicalFinite.binaryWorkedTrajectory_relevance_bound
```

The authoritative Gate B validation record is:

```text
Branch source head:   c33087041a8588f11f85c0c108046701269f291f
PR merge-test SHA:    fb57537f2bb141987fcd10a8621876a034b15915
Workflow run:         29208133524
Build:                1942 jobs, success
No sorry/admit:       pass
Project-local axioms: none
No sorryAx:           pass
Audit artifact:       formal-core-v2-audit-29208133524-1
Artifact SHA-256:     dd718909eb0e683e7e92fabf76eb773f8368a1437148f2c65ccfa10d3570930c
```

For 20 of the 22 Gate B declarations, Lean reported:

```lean
[propext, Classical.choice, Quot.sound]
```

The two narrower reports are:

```text
binaryCheck_eq_true_iff:
  [propext]

binaryCheck_rejects_invalidCandidate:
  no axioms
```

Thus the audited Gate B theorem set is not globally axiom-free: it uses standard
Lean/mathlib foundational principles transitively through real analysis,
finite sums, structure extensionality, and the abstract composition theorems. It
introduces no project-local axiom and contains no admitted proof.

## Combined acceptance rule

The Formal Core audit passes only when:

```text
paper source blobs and mapped theorem surfaces match their pins
no project source contains sorry or admit
no project-local axiom declaration is present
all Gate A audit declarations elaborate
all Gate B audit declarations elaborate
no axiom report contains sorryAx
a clean pinned build succeeds
audit artifacts are uploaded even on failure
```

## Prohibited inferences

```text
clean build ⇒ exact Paper I or Paper II theorem equivalence
Gate B finite KL ⇒ arbitrary stochastic-channel data processing
Gate B finite KL ⇒ quantum relative entropy
binary monitor semantics ⇒ Paper I expectation, ambiguity, or mutual information
checker soundness ⇒ successor availability
finite accepted trajectory ⇒ executable or empirical RSI
no project-local axioms ⇒ no standard Lean/mathlib foundational dependencies
```

## Reproduction

After a successful build, run from `lean/rcp_rclm_formal_core_v2`:

```text
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateBAxiomAudit.lean
```

The GitHub workflow additionally performs the source scans and uploads all
reports.