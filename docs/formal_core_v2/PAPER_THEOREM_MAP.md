# Paper-to-Lean theorem map — formal core v2

This map pins the theorem-facing source versions before implementation.

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

| Paper claim surface | Formal-core v2 target | Gate | Initial status |
|---|---|---:|---|
| Conditional Non-Lossy Self-Update Preservation Theorem | `RCP.accepted_step_sound`, finite non-loss/recovery composition | A | contract frozen |
| direct-engine construction claim | explicit `SuccessorAvailability` / generator-completeness interface; no existence claim from checker soundness | A | assumption boundary frozen |
| robust reflective successor/domain-invariance claim | accepted-step obligations plus `successorAdmissible` | A | contract frozen |
| finite proof-carrying trajectory claim | `RCP.finite_trajectory_closure` | A | not yet proved |
| infinite seed-library closure claim | `RCP.conditional_infinite_trajectory_exists` with explicit availability hypothesis | A | not yet proved |
| Batch-13R classical/diagonal reference entry | actual finite distributions and nonconstant Shannon/KL divergence | B | not yet implemented |
| constructive recovery / rollback | `RCP.ConstructiveRecovery` tied to the actual candidate update | A/B | interface started |
| strict ability/progress expansion | non-vacuous `StrictWitness` implying strict increase of a declared progress functional | A/B | interface started |
| RCLM-to-RCP refinement | `RCLM.rclm_checker_refines_rcp` for substantive states, updates, and certificates | RCLM after A/B | contract only |
| architecture-level successor theorem | `RCLM.rclm_architecture_successor_theorem` | RCLM after A/B | contract only |
| finite-dimensional quantum non-loss claim | density matrices, admissible channels, von Neumann/quantum relative entropy, recovery theorem | C | not yet implemented |

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
