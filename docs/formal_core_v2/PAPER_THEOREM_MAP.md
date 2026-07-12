# Paper-to-Lean theorem map — formal core v2

This map pins the theorem-facing source versions before implementation and records
which declarations have actually been implemented. A declaration is marked
`implemented` only when its Lean source exists; it is marked `clean-CI-built`
only after the pinned Formal Core v2 workflow succeeds for the containing commit.

## Source pins

```text
Paper I:
  papers/paper-I-rcp-math/main.tex
  Git blob: 084eae21d252d205d2012b62744c1506644e3e58

Paper II:
  papers/paper-II-rclm-architecture/main.tex
  Git blob: 9b51be8294ad79fd4f63522b01e0f617f0bf2ffd

Historical Lean v1 RCP:
  lean/rcp_rclm_can_lean4/RcpRclmMech/RCP.lean
  Git blob: 56e0da83578bfffd4ec4cc56f3a48280c3098730

Historical Lean v1 RCLM:
  lean/rcp_rclm_can_lean4/RcpRclmMech/RCLM.lean
  Git blob: 151b5d6216c8abefc16528f2a9ed6c0b6319060f
```

## Named-claim mapping

| Paper claim surface | Formal-core v2 target | Gate | Current status |
|---|---|---:|---|
| Conditional Non-Lossy Self-Update Preservation Theorem | `RCP.accepted_step_sound`, `RCP.finite_composed_nonloss_bound`, `RCP.finite_composed_recovery_bound` | A | one-step theorem clean-CI-built; finite composition declarations implemented and CI/audit enforced |
| direct-engine construction claim | explicit `RCP.SuccessorAvailability`; no existence claim from checker soundness | A | assumption boundary implemented and remains explicit in the public infinite theorem |
| robust reflective successor/domain-invariance claim | accepted-step obligations plus `successorAdmissible` | A | implemented in `RCP.StepObligations`, `RCP.accepted_step_sound`, and finite/infinite closure constructions; clean-CI-built |
| finite proof-carrying trajectory claim | `RCP.finite_trajectory_closure`, `RCP.finite_trajectory_step_sound` | A | implemented and clean-CI-built |
| finite progress composition claim | `RCP.finite_progress_monotone` | A | implemented; CI/audit enforced |
| finite protected-loss composition claim | transported distinctions plus `RCP.finite_composed_nonloss_bound` | A | implemented; bounds the initial protected value by the transported endpoint value plus the sum of declared per-step loss budgets |
| finite recovery composition claim | local recovery errors plus `RCP.finite_composed_recovery_bound` | A | implemented; aggregate local-error bound only, not an undeclared endpoint rollback theorem |
| infinite seed-library closure claim | `RCP.conditional_infinite_trajectory_exists` with explicit availability hypothesis | A | implemented and clean-CI-built; successor availability is not inferred from checker soundness |
| Batch-13R classical/diagonal reference entry | actual finite distributions and nonconstant Shannon/KL divergence | B | definitions started; required laws, conservative extension, recovery theorem, and worked example not yet implemented |
| constructive recovery / rollback | `RCP.ConstructiveRecovery` tied to the actual candidate update | A/B | one-step interface and finite aggregate local-error theorem implemented; concrete Gate B recovery remains pending |
| strict ability/progress expansion | `RCP.StrictProgressWhenWitness` and per-step soundness, with `RCP.finite_progress_monotone` for nondecrease | A/B | abstract implication implemented; a concrete non-vacuous Gate B witness remains pending |
| RCLM-to-RCP refinement | `RCLM.rclm_checker_refines_rcp` for substantive states, updates, and certificates | RCLM after A/B | contract only |
| architecture-level successor theorem | `RCLM.rclm_architecture_successor_theorem` | RCLM after A/B | contract only |
| finite-dimensional quantum non-loss claim | density matrices, admissible channels, von Neumann/quantum relative entropy, recovery theorem | C | not yet implemented |

## Gate A audit boundary

The CI workflow must preserve both:

```text
no-sorry / no-admit source audit
#print axioms output for every public Gate A theorem
```

The audit is described in `AXIOM_AUDIT.md`. A successful build alone does not
license a claim that Gate A is assumption-free: the generated axiom report is the
source of truth for foundational dependencies, and the theorem statements retain
all model-specific assumptions through their explicit kernel/checker arguments.

## Mapping discipline

1. A paper theorem is not marked mechanized until the mapped Lean theorem exists,
   builds under the pinned toolchain, contains no `sorry`, and its assumptions
   match the paper statement.
2. If the Lean theorem is narrower than the paper theorem, the paper mapping must
   record the narrowing explicitly.
3. Gate B and Gate C may instantiate Gate A, but may not silently change the Gate
   A theorem contract.
4. The direct-engine/generator claim is not discharged by checker soundness. Any
   existence or completeness result must expose its own assumptions.
5. Historical v1 files remain valid only for their declared canonical finite
   scope and are not treated as proofs of the v2 theorem.
6. `RCP.finite_composed_recovery_bound` is deliberately an aggregate theorem over
   certified local recovery errors. A stronger endpoint rollback theorem requires
   additional composition structure and may not be inferred from this result.
