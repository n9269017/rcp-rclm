# Paper-to-Lean theorem map — formal core v2

This map pins the theorem-facing source versions and records the strongest claim
licensed by the compiled declarations. `implemented` means the declaration
exists. `clean-CI-built and audited` additionally means the pinned workflow built
it, scanned the source for admitted proofs and project-local axioms, and
preserved its kernel axiom report. Neither status by itself implies concrete
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
- **Structural**: the inference shape agrees, but important paper-specific
  quantities or certificate meanings remain abstract.
- **Deferred**: exact identification requires Gate B, Gate C, or substantive RCLM
  refinement.
- **Mismatch**: the current Lean result is genuinely weaker or different.

The initial comparison is in `GATE_A_PAPER_ALIGNMENT_AUDIT.md`. Subsequent
resolutions are in `GATE_A_ALIGNMENT_RESOLUTION_LOG.md`.

## Named-claim mapping

| Paper claim surface | Formal-core v2 target | Gate | Current status |
|---|---|---:|---|
| Paper I `thm:main_rcp`, Conditional Non-Lossy Self-Update Preservation Theorem | `RCP.finite_paper_preservation` plus the one-step, trajectory, recovery, monitor, and summability theorems | A/B/C | **Abstract Gate A wrapper implemented; concrete theorem still deferred.** The wrapper exposes paper-safe/update-admissibility equivalences, no-op feasibility, accepted-prefix admissibility, progress, protected non-loss, endpoint recovery, Lyapunov/motion, ambiguity, and transported relevance. Exact expectation, KL/quantum-relative-entropy, ambiguity, mutual-information, and safe-set meanings require concrete refinements. |
| Paper I state-safe-set and update-admissibility predicates | `RCP.PaperSemantics` | A plus concrete refinement | **Explicit boundary implemented.** The paper predicates and their equivalences to kernel domain/invariant and `StepObligations` are visible assumptions, not implicit name matching. Concrete equivalence remains deferred. |
| Paper I no-op-feasibility premise | `RCP.AcceptedNoOp`, `RCP.NoOpFeasible` | A | **Abstract exact.** Every paper-safe state must have an accepted unchanged-successor packet. This premise is distinct from general successor availability. |
| Paper I Lyapunov expectation and squared-motion conclusion | `RCP.PreservationMonitors`, `RCP.finite_lyapunov_motion_bound` | A plus probability refinement | **Abstract exact for telescoping.** `motionCharge` can be instantiated as `κ·E[d²]`; that interpretation remains deferred. |
| Paper I unsupported ambiguity-collapse conclusion | `RCP.finite_ambiguity_collapse_bound` | A plus semantic refinement | **Abstract exact for additive composition.** Concrete ambiguity semantics remain deferred. |
| Paper I self-model relevance conclusion | `RCP.finite_self_model_relevance_bound` | A plus B/C or RCLM refinement | **Abstract exact for transported-value composition.** Identification with mutual information remains deferred. |
| Paper I summability consequences | `RCP.SummableMonitorBudgets`, `toUniformMonitorBudgetCaps`, `infinite_monitor_bounds_of_summable`, `infinite_cumulative_motion_bounded_of_summable` | A plus concrete monitor refinement | **Abstract exact.** Standard `Summable` assumptions on the three nonnegative error sequences yield `tsum` caps and uniform finite-prefix bounds. |
| Paper I `thm:finite_horizon_constructive_recovery` | `RCP.RecoveryCompositionLaws`, `RCP.composedRecovery`, `RCP.finite_endpoint_recovery_bound` | A plus concrete metric/channel refinement | **Abstract exact.** The rollback-order map is constructed and the endpoint distance is bounded by the cumulative budget. Concrete trace-distance/channel identification is deferred. |
| Aggregate local recovery accounting | `RCP.finite_composed_recovery_bound` | A | **Implemented separately.** This theorem is not used as a substitute for endpoint rollback. |
| Finite proof-carrying trajectory | `RCP.FiniteAcceptedTrajectory`, finite closure and step-soundness theorems | A | **Structural/abstract exact.** Accepted-prefix induction is implemented; paper-specific packet grammar and compiler traces require Gate B/refinement. |
| Finite progress composition | `RCP.finite_progress_monotone`, strict-witness field in `FinitePaperPreservation` | A/B | **Abstract exact.** Concrete ability-set meaning and a non-vacuous witness are Gate B/RCLM obligations. |
| Finite protected-loss composition | `RCP.transportedDistinction`, `RCP.finite_composed_nonloss_bound` | A/B/C | **Abstract exact.** Finite KL and quantum-relative-entropy meanings are deferred. |
| Conditional infinite accepted trajectory | `RCP.SuccessorAvailability`, `RCP.conditional_infinite_trajectory_exists` | A | **Abstract exact.** Successor availability is explicit and is never inferred from checker soundness. |
| Conditional infinite paper-domain closure | `RCP.conditional_infinite_paper_trajectory_exists` | A | **Abstract exact.** Paper-safe state closure, update admissibility, and no-op availability are carried along the selected infinite accepted path. |
| Finite-prefix recovery/monitor preservation on infinite paths | `RCP.finitePrefixOfInfinite` and the infinite-prefix theorems | A | **Implemented.** Every finite prefix inherits endpoint recovery and the quantitative monitor bounds. |
| Direct-engine construction claim | no Gate A construction theorem; only `SuccessorAvailability` | later engine/refinement layer | **Not mechanized as construction.** Generator, coverage, certifier, selector, and realizer claims require their own assumptions and proofs. |
| Paper I canonical diagonal/reference checker soundness | future concrete `TrustedChecker` instance | B plus checker refinement | **Deferred.** Concrete distributions, packet grammar, trust/goal/uncertainty objects, and cost ledger are not instantiated. |
| Batch-13R classical/diagonal reference entry | `RCP.ClassicalFinite` plus future concrete kernel/checker/trajectory | B | **Definitions started only.** KL laws, conservative extension, concrete recovery, checker refinement, and nonconstant worked trajectory remain open. |
| Paper II typed RCLM state/update/certificate surfaces | `RCLM.State`, `RCLM.Update`, `RCLM.CertificatePacket` | RCLM | **Structural interfaces only.** Field names do not establish semantic realization. |
| Paper II substantive RCLM-to-RCP refinement | `RCLM.rclm_checker_refines_rcp` | RCLM after B | **Not implemented.** All theorem-relevant fields, monitor laws, and checker acceptance must be preserved. |
| Paper II checker soundness theorem | concrete RCLM checker plus `rclm_checker_refines_rcp` | RCLM after B | **Not implemented.** |
| Paper II architecture successor/direct-engine theorem | `RCLM.rclm_architecture_successor_theorem` | RCLM after A/B | **Not implemented.** |
| Finite-dimensional quantum non-loss/recovery | future `RCP.QuantumFinite` implementation | C | **Not implemented.** |

## Abstract Gate A verdict

```text
one-step checker kernel: implemented
finite domain/invariant/progress/non-loss composition: implemented
endpoint recovery composition: implemented
explicit Lyapunov/ambiguity/relevance composition: implemented
standard Summable-to-uniform-cap bridge: implemented
paper-safe/update-admissibility boundary: implemented as explicit refinement data
no-op premise: implemented
conditional infinite accepted path: implemented under explicit availability
paper-facing finite and infinite abstract wrappers: implemented
abstract Gate A theorem kernel: complete
exact Paper I theorem equivalence: false pending concrete refinements
exact Paper II architecture theorem equivalence: false
```

The final synchronized clean-CI run and artifact are recorded in
`AXIOM_AUDIT.md` and the formalization manifest.

## Mapping discipline

1. Abstract Gate A completion is not a finite-KL, quantum, RCLM, or empirical
   result.
2. A paper theorem is called exactly mechanized only after concrete assumptions
   and conclusions match the pinned statement.
3. Checker soundness never implies successor availability or direct-engine
   construction.
4. Aggregate local recovery accounting and endpoint rollback remain distinct.
5. Historical v1 files remain canonical only for their declared finite scope.
