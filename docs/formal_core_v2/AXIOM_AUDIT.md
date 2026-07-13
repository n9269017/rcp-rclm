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

## Gate A audit

The abstract Gate A audit covers 22 public declarations in:

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

Every audited Gate A theorem reported:

```lean
[propext, Classical.choice, Quot.sound]
```

Classical choice remains visible because an infinite trajectory selects
successors from an explicit `Nonempty` availability premise.

## Gate B audit

The finite classical Gate B audit covers 22 declarations in:

```text
docs/formal_core_v2/audit/GateBAxiomAudit.lean
```

The authoritative Gate B validation record is:

```text
Source head:          c33087041a8588f11f85c0c108046701269f291f
Workflow run:         29208133524
Build:                1942 jobs, success
No sorry/admit:       pass
Project-local axioms: none
No sorryAx:           pass
Audit artifact:       formal-core-v2-audit-29208133524-1
Artifact SHA-256:     dd718909eb0e683e7e92fabf76eb773f8368a1437148f2c65ccfa10d3570930c
```

Most Gate B declarations report the standard union:

```lean
[propext, Classical.choice, Quot.sound]
```

Narrower computational theorems use only `propext` or no axioms.

## RCLM refinement and architecture-engine audit

The RCLM audit file is:

```text
docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
```

It covers 27 generic and concrete declarations, including:

```lean
RCLM.KernelRefinement.stepObligationsPreserved
RCLM.KernelRefinement.recoveryCompositionLawsPreserved
RCLM.rclm_checker_refines_rcp
RCLM.rclm_checker_acceptance_preserved
RCLM.rclm_monitor_refinement_valid
RCLM.rclm_architecture_successor_theorem
RCLM.conditional_infinite_architecture_trajectory_exists
RCLM.infinite_architecture_step_result
RCLM.ClassicalBinary.accepted_architecture_successor
RCLM.ClassicalBinary.engine_relations_accept
RCLM.ClassicalBinary.architectureSuccessorAvailability
RCLM.ClassicalBinary.improvement_direct_engine_successor
RCLM.ClassicalBinary.classical_infinite_architecture_trajectory_exists
RCLM.ClassicalBinary.classical_infinite_architecture_step_result
```

The validated architecture-engine audit record is:

```text
Branch source head:   0731abfdf0edb940312a48051a3ca527c086af5b
Workflow run:         29215941083
Build:                1945 jobs, success
No sorry/admit:       pass
Project-local axioms: none
No sorryAx:           pass
Audited declarations: 27
Audit artifact:       formal-core-v2-audit-29215941083-1
Artifact SHA-256:     9d4d3d5a38e2bfefbb641950131c8a10dbec20fc90b89c165a08ef4f4b98fff4
```

The generic refinement and architecture theorems report:

```lean
[propext, Classical.choice, Quot.sound]
```

The concrete canonical projection theorems are axiom-free; several concrete
Boolean/equality theorems report only `propext`. No audited declaration reports
`sorryAx`.

The classical-choice dependency in the architecture infinite theorem is
expected and explicit: `ArchitectureSuccessorAvailability` supplies a `Nonempty`
engine step for every valid predecessor, and the construction selects one. The
availability proposition is not inferred from checker soundness.

## Combined acceptance rule

The Formal Core audit passes only when:

```text
paper source blobs and mapped theorem surfaces match their pins
no project source contains sorry or admit
no project-local axiom declaration is present
all Gate A audit declarations elaborate
all Gate B audit declarations elaborate
all RCLM refinement and architecture-engine declarations elaborate
no axiom report contains sorryAx
a clean pinned build succeeds
audit artifacts are uploaded even on failure
```

## Prohibited inferences

```text
clean build ⇒ exact Paper I or Paper II theorem equivalence
no project-local axioms ⇒ no standard Lean/mathlib foundational dependencies
checker soundness ⇒ successor availability
architecture availability ⇒ strict useful improvement at every step
concrete binary infinite path ⇒ unbounded empirical RSI
Gate B finite KL ⇒ quantum relative entropy
binary monitor semantics ⇒ Paper I expectation, ambiguity, or mutual information
conditional architecture theorem ⇒ executable generator correctness
```

## Reproduction

After a successful build, run from `lean/rcp_rclm_formal_core_v2`:

```text
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateBAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
```

The GitHub workflow additionally performs the source scans and uploads all
reports.
