# Paper-to-Lean theorem map — formal core v2

This map pins the theorem-facing source versions and records the strongest claim
licensed by the compiled declarations. `implemented` means the Lean declaration
exists. `clean-CI-built and audited` additionally means the pinned workflow built it,
scanned the source for admitted proofs and local axioms, and preserved its kernel
axiom report. Neither status implies exact agreement with a paper theorem.

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

## Alignment vocabulary

- **Exact**: assumptions and conclusions agree after definitional unfolding or
  harmless renaming.
- **Structural**: the inference pattern agrees, but paper-specific quantities,
  transports, laws, or certificate meanings remain abstract.
- **Deferred**: exact identification requires Gate B, Gate C, or substantive RCLM
  refinement.
- **Mismatch**: the current Lean theorem proves a genuinely different or weaker
  statement and must be strengthened or the mapped paper claim narrowed.

The line-by-line comparison and mismatch register are in
`GATE_A_PAPER_ALIGNMENT_AUDIT.md`.

## Named-claim mapping

| Paper claim surface | Formal-core v2 target | Gate | Current status |
|---|---|---:|---|
| Paper I `thm:main_rcp`, Conditional Non-Lossy Self-Update Preservation Theorem | `RCP.accepted_step_sound`, `RCP.finite_trajectory_closure`, `RCP.finite_progress_monotone`, `RCP.finite_composed_nonloss_bound`, `RCP.finite_composed_recovery_bound` | A/B/C | **Structural, not exact.** The abstract checker/domain/progress/non-loss skeleton is implemented, clean-CI-built, and audited. The paper's explicit Lyapunov expectation and squared-motion bound, ambiguity-collapse sum, self-model mutual-information bound, and summability conclusions are not yet represented. Identification of `protectedValue` with KL or quantum relative entropy is deferred to Gates B/C. |
| Paper I no-op-feasibility premise | no current declaration | A / paper wrapper | **Mismatch.** The premise is absent from the Lean-facing theorem statement. It must be represented explicitly or removed from the mapped paper theorem if it is intentionally outside the formal result. |
| Paper I state-safe-set and update-admissibility semantics | `K.admissible`, `K.protectedInvariant`, `TrustedChecker.sound` | A / refinement | **Structural.** No theorem yet identifies these abstract predicates with the full paper definitions of `K_RCP^state` and `A_RCP`. |
| Paper I direct-engine construction claim | `RCP.SuccessorAvailability` only preserves the existence boundary | later engine/refinement layer | **Not mechanized as construction.** `SuccessorAvailability` is an explicit availability hypothesis, not a generator, builder, coverage theorem, or direct-engine construction theorem. |
| robust reflective successor/domain-invariance claim | `RCP.StepObligations`, `RCP.accepted_step_sound`, finite/infinite domain closure | A plus paper-specific refinement | **Structural.** Abstract domain closure is implemented and audited; the paper's seed-library, builder, transport, uncertainty, trust, goal, and budget premises are not exposed as named Lean premises. |
| finite proof-carrying trajectory claim | `RCP.FiniteAcceptedTrajectory`, `RCP.finite_trajectory_closure`, `RCP.finite_trajectory_step_sound` | A | **Structural.** The induction and accepted-prefix shape is implemented, clean-CI-built, and audited. Paper-specific packet grammar and builder traces are deferred. |
| finite progress composition claim | `RCP.finite_progress_monotone` | A/B | **Exact for the abstract scalar functional; deferred for the paper ability-set order.** The theorem proves endpoint nondecrease for `K.progress`; it does not yet identify that functional with certified ability-set inclusion or novelty. |
| finite protected-loss composition claim | `RCP.transportedDistinction`, `RCP.finite_composed_nonloss_bound` | A/B/C | **Structural.** The additive transported-value theorem is implemented and audited. Exact finite-KL and quantum-relative-entropy readings require Gates B and C. |
| Paper I `thm:finite_horizon_constructive_recovery` | `RCP.finite_composed_recovery_bound` | A | **Mismatch.** Lean currently bounds the sum of local recovery errors by the sum of local budgets. The paper constructs a composed endpoint recovery map and proves an endpoint distance bound using metric and nonexpansiveness laws. |
| conditional infinite accepted trajectory | `RCP.SuccessorAvailability`, `RCP.conditional_infinite_trajectory_exists` | A | **Structural.** Explicit successor availability and infinite recursion are implemented and audited. This is not the full Paper I Batch-12B theorem with seed libraries, packet builders, transports, reality/tractability qualifications, and summable failure/goal-drift budgets. |
| Paper I canonical diagonal/reference checker soundness | future concrete checker instance refining `RCP.TrustedChecker` | B plus checker refinement | **Deferred.** The abstract soundness schema exists; the paper's concrete finite distributions, exact information law, packet grammar, goal/uncertainty/trust objects, and cost ledger are not instantiated. |
| Batch-13R classical/diagonal reference entry | `RCP.ClassicalFinite`, future concrete kernel/checker/trajectory | B | **Definitions started only.** Actual finite distributions, Shannon entropy, and KL expressions exist; support laws, KL laws, conservative extension, recovery, checker refinement, and a nonconstant worked trajectory remain open. |
| constructive recovery / rollback | `RCP.ConstructiveRecovery`; finite local-error aggregation | A/B | One-step update-tied recovery is implemented. Exact endpoint composition and concrete classical recovery remain open. |
| strict ability/progress expansion | `RCP.StrictProgressWhenWitness`, per-step soundness, `RCP.finite_progress_monotone` | A/B | Abstract implication implemented. A concrete, semantically meaningful strict witness and certified ability-set novelty theorem remain open. |
| Paper II typed RCLM state/update/certificate surfaces | `RCLM.State`, `RCLM.Update`, `RCLM.CertificatePacket` | RCLM | **Structural interfaces only.** Field names do not yet prove density, semantic, goal, uncertainty, trust, ability, estimator, or resource meanings. |
| Paper II substantive RCLM-to-RCP refinement | `RCLM.rclm_checker_refines_rcp` | RCLM after B | **Not implemented.** Current `RCLM.Refinement` preserves only admissibility, candidate-next compatibility, and one invariant. It does not preserve all theorem-relevant kernel fields or checker acceptance. |
| Paper II `thm:rclm-batch13r-checker-soundness` | concrete RCLM checker plus `RCLM.rclm_checker_refines_rcp` | RCLM after B | **Not implemented.** No RCLM checker is defined in Formal Core v2. |
| Paper II architecture successor/direct-engine theorem | `RCLM.rclm_architecture_successor_theorem` | RCLM after A/B | **Not implemented.** The current architecture module intentionally contains no theorem declaration. |
| finite-dimensional quantum non-loss/recovery claims | future `RCP.QuantumFinite` implementation | C | **Not implemented.** Density matrices, channels, support conditions, von Neumann/quantum relative entropy, and recovery laws remain open. |

## Gate A build and proof-admission evidence

The first complete abstract composition-and-audit result is recorded in
`AXIOM_AUDIT.md`:

```text
source commit: 2b68a0048482ad481dfe6b05ce3c5a3262c7a08a
workflow run:  29184258470
artifact:      formal-core-v2-gate-a-audit-29184258470-1
artifact SHA:  sha256:3a4654e730c6ee5d1c87c723fc66a2b79d74e9642e380e9eb8dce95ac7053470
```

The reports show a clean 1938-job build, no `sorry` or `admit`, no project-local
`axiom` declarations, no `sorryAx`, and the exact foundational axiom set
`[propext, Classical.choice, Quot.sound]` for each audited public Gate A theorem.

## Paper-alignment verdict

The comparison pass is complete in `GATE_A_PAPER_ALIGNMENT_AUDIT.md`. Its result is:

```text
Gate A abstract composition kernel: implemented, clean-CI-built, audited
Exact Paper I theorem equivalence: false
Exact Paper II architecture theorem equivalence: false
Mismatch resolution: open
Gate A paper-alignment closure: not passed
```

The next abstract proof obligation is endpoint recovery composition. The next
paper-monitor obligation is an explicit abstract schema for the Lyapunov,
ambiguity-collapse, self-model-relevance, and cumulative/summable conclusions of
Paper I. Gate B then supplies the first concrete information-theoretic instance.

## Mapping discipline

1. A paper theorem is not marked mechanized until the mapped Lean theorem exists,
   builds under the pinned toolchain, contains no admitted proof, and its assumptions
   and conclusions match the paper statement.
2. A structural correspondence must not be reported as exact mechanization.
3. If Lean is narrower than the paper, the paper claim must be narrowed or Lean must
   be strengthened; the mismatch remains visible until one of those actions occurs.
4. Gate B and Gate C may instantiate Gate A, but may not silently change the Gate A
   contract.
5. Checker soundness never implies successor existence, generator coverage, or
   direct-engine construction.
6. `RCP.finite_composed_recovery_bound` is an aggregate local-error theorem. It is
   not the paper's endpoint rollback theorem.
7. Historical v1 files remain valid only for their declared canonical finite scope
   and are not proofs of the v2 paper theorem stack.
