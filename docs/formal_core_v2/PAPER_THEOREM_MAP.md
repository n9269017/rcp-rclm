# Paper-to-Lean theorem map — formal core v2

This map pins the theorem-facing source versions and records the strongest claim
licensed by the compiled declarations. `implemented` means the declaration
exists. `clean-CI-built and audited` additionally means the pinned workflow built
it, scanned the source for admitted proofs and project-local axioms, and
preserved its kernel axiom report. Neither status by itself implies exact
agreement with a paper theorem.

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
- **Abstract exact**: the inference is proved under explicit abstract laws; a
  later refinement must identify the abstract objects with the paper objects.
- **Concrete reference exact**: the theorem is exact for the declared finite
  reference instance, without claiming that the instance is the complete paper
  semantics.
- **Structural**: the inference shape agrees, but important paper-specific
  quantities or certificate meanings remain abstract.
- **Deferred**: exact identification requires Gate C or substantive RCLM
  refinement.
- **Mismatch**: the current Lean result is genuinely weaker or different.

The initial comparison is in `GATE_A_PAPER_ALIGNMENT_AUDIT.md`. Abstract
resolutions are in `GATE_A_ALIGNMENT_RESOLUTION_LOG.md`. The finite classical
closure boundary is in `GATE_B_CLOSURE.md`.

## Named-claim mapping

| Paper claim surface | Formal-core v2 target | Gate | Current status |
|---|---|---:|---|
| Paper I `thm:main_rcp`, Conditional Non-Lossy Self-Update Preservation Theorem | `RCP.finite_paper_preservation` plus the one-step, trajectory, recovery, monitor, summability, and concrete-refinement theorems | A/B/C | **Abstract wrapper implemented; one finite classical reference implemented; exact paper theorem still deferred.** Gate B now supplies actual finite KL, exact zero-extension recovery, a KL-derived strict witness, a concrete checker, and scoped classical monitors. Paper I's full probability, semantic ambiguity, mutual-information, and quantum-relative-entropy meanings remain open. |
| Paper I state-safe-set and update-admissibility predicates | `RCP.PaperSemantics` | A plus concrete refinement | **Explicit abstract boundary implemented.** The Gate B binary domain and checker are concrete, but no theorem identifies them with the complete pinned Paper I safe-set and update-admissibility definitions. |
| Paper I no-op-feasibility premise | `RCP.AcceptedNoOp`, `RCP.NoOpFeasible` | A | **Abstract exact.** This remains a separate explicit premise. The Gate B binary checker intentionally demonstrates improvement and stability packets; it is not claimed to discharge Paper I no-op feasibility on every mapped safe state. |
| Paper I Lyapunov expectation and squared-motion conclusion | `RCP.PreservationMonitors`, `RCP.finite_lyapunov_motion_bound`, `ClassicalFinite.binaryPreservationMonitors` | A/B plus probability refinement | **Concrete reference exact for KL-to-target Lyapunov accounting.** Gate B uses finite KL as the Lyapunov value and KL-derived progress increase as the motion charge with zero error. Identification with conditional expectation and squared state motion remains deferred. |
| Paper I unsupported ambiguity-collapse conclusion | `RCP.finite_ambiguity_collapse_bound`, `ClassicalFinite.binaryUnsupportedCollapse_step` | A/B plus semantic refinement | **Concrete reference exact for the declared malformed-certificate indicator.** It is not identified with the paper's semantic ambiguity quantity. |
| Paper I self-model relevance conclusion | `RCP.finite_self_model_relevance_bound`, `ClassicalFinite.binaryRelevance_step` | A/B plus RCLM refinement | **Concrete reference exact for target-fit and normalization evidence.** It is not identified with mutual information. |
| Paper I summability consequences | `RCP.SummableMonitorBudgets`, `toUniformMonitorBudgetCaps`, `infinite_monitor_bounds_of_summable`, `infinite_cumulative_motion_bounded_of_summable` | A plus concrete sequence refinement | **Abstract exact.** Gate B's finite worked trajectory has zero declared monitor errors; no infinite empirical or probabilistic conclusion is inferred. |
| Paper I `thm:finite_horizon_constructive_recovery` | `RCP.RecoveryCompositionLaws`, `RCP.composedRecovery`, `RCP.finite_endpoint_recovery_bound`, `ClassicalFinite.binaryRecoveryCompositionLaws` | A/B plus later channel refinement | **Concrete reference exact for the binary discrete metric and exact zero-extension recovery.** Trace distance and quantum-channel recovery remain deferred. |
| Aggregate local recovery accounting | `RCP.finite_composed_recovery_bound` | A | **Implemented separately.** This theorem is not used as a substitute for endpoint rollback. |
| Finite proof-carrying trajectory | `RCP.FiniteAcceptedTrajectory`, finite closure and step-soundness theorems, `ClassicalFinite.binaryWorkedTrajectory` | A/B | **Concrete reference implemented.** The trajectory `initial → target → target` is accepted by the declared finite packet grammar. |
| Finite progress composition | `RCP.finite_progress_monotone`, strict-witness field in `FinitePaperPreservation`, `ClassicalFinite.binaryWorkedTrajectory_first_step_strict` | A/B | **Concrete non-vacuous witness implemented.** Progress is reduction of actual KL distance to the target, not introduction of a fresh index. |
| Finite protected-loss composition | `RCP.transportedDistinction`, `RCP.finite_composed_nonloss_bound`, `ClassicalFinite.klDivergence_extendByZero` | A/B/C | **Concrete finite KL preservation implemented for zero-coordinate extension.** General pushforward/data-processing and quantum-relative-entropy meanings remain deferred. |
| Conditional infinite accepted trajectory | `RCP.SuccessorAvailability`, `RCP.conditional_infinite_trajectory_exists` | A | **Abstract exact.** Successor availability is explicit and is never inferred from checker soundness or the finite Gate B example. |
| Conditional infinite paper-domain closure | `RCP.conditional_infinite_paper_trajectory_exists` | A | **Abstract exact.** Concrete Paper I semantic identification remains deferred. |
| Finite-prefix recovery/monitor preservation on infinite paths | `RCP.finitePrefixOfInfinite` and the infinite-prefix theorems | A | **Implemented abstractly.** Gate B is a finite reference instance and does not itself supply generator completeness. |
| Direct-engine construction claim | no construction theorem; only `SuccessorAvailability` | later engine/refinement layer | **Not mechanized as construction.** Generator, coverage, certifier, selector, and realizer claims require their own assumptions and proofs. |
| Paper I canonical diagonal/reference checker soundness | `ClassicalFinite.binaryCheck_eq_true_iff`, `binary_checker_refines_kernel` | B | **Concrete finite reference checker implemented.** Acceptance refines to the complete `StepObligations` bundle. This is not yet identified with every field of the paper's full canonical checker. |
| Batch-13R classical/diagonal reference entry | `RCP.ClassicalFinite`, `RCP.ClassicalBinary` | B | **Gate B complete at the declared finite reference scope.** Actual distributions, Shannon/KL, support laws, conservative extension, exact recovery, KL-derived strict progress, concrete residuals/checker, recovery laws, monitors, and a worked trajectory are implemented. Exact identity with the entire Batch-13R paper object remains unclaimed. |
| Paper II typed RCLM state/update/certificate surfaces | `RCLM.State`, `RCLM.Update`, `RCLM.CertificatePacket` | RCLM | **Structural interfaces only.** Field names do not establish semantic realization. |
| Paper II substantive RCLM-to-RCP refinement | `RCLM.rclm_checker_refines_rcp` | RCLM after B | **Next selected formal obligation; not implemented.** Every theorem-relevant field, classical monitor meaning, recovery law, and checker acceptance must be preserved. |
| Paper II checker soundness theorem | concrete RCLM checker plus `rclm_checker_refines_rcp` | RCLM after B | **Not implemented.** |
| Paper II architecture successor/direct-engine theorem | `RCLM.rclm_architecture_successor_theorem` | RCLM after A/B | **Not implemented.** |
| Finite-dimensional quantum non-loss/recovery | future `RCP.QuantumFinite` implementation | C | **Not implemented.** |

## Gate A verdict

```text
abstract one-step and composition kernel: complete
endpoint recovery composition: complete
explicit quantitative monitor composition: complete
conditional infinite accepted path: complete under explicit availability
paper-safe/update-admissibility boundary and no-op premise: explicit
abstract Gate A theorem kernel: complete and audited
```

## Gate B verdict

```text
finite normalized distributions: implemented
actual Shannon entropy and finite KL: implemented
support-aware KL nonnegativity and self-zero: implemented
nonconstant binary KL LawfulDivergence: implemented
zero-coordinate conservative extension: implemented
support, Shannon, and KL preservation: implemented
exact constructive recovery: implemented
KL-derived strict progress witness: implemented
computed residuals and substantive gates: implemented
concrete Boolean checker and soundness refinement: implemented
binary recovery composition laws: implemented
scoped classical monitor refinement: implemented
nontrivial finite accepted trajectory: implemented
Gate B finite reference scope: complete, subject to synchronized clean-CI audit
exact Paper I theorem equivalence: false
exact Paper II architecture theorem equivalence: false
```

## Mapping discipline

1. Gate B completion is a finite classical reference result, not full Paper I or
   Paper II mechanization.
2. A paper theorem is called exactly mechanized only after concrete assumptions
   and conclusions match the pinned statement.
3. Checker soundness never implies successor availability or direct-engine
   construction.
4. Aggregate local recovery accounting and endpoint rollback remain distinct.
5. The malformed-certificate indicator is not semantic ambiguity, and the
   target-fit relevance score is not mutual information.
6. The zero-coordinate embedding is not a theorem about every stochastic
   channel.
7. Historical v1 files remain canonical only for their declared finite scope.