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
- **Deferred**: exact identification requires a later gate or refinement.
- **Mismatch**: the current Lean result is genuinely weaker or different.

The initial comparison is in `GATE_A_PAPER_ALIGNMENT_AUDIT.md`. Abstract
resolutions are in `GATE_A_ALIGNMENT_RESOLUTION_LOG.md`. The finite classical
closure boundary is in `GATE_B_CLOSURE.md`. The substantive RCLM refinement and
conditional engine boundaries are recorded in `RCLM_GATE_B_REFINEMENT_STATUS.md`
and `RCLM_DIRECT_ENGINE_STATUS.md`.

## Named-claim mapping

| Paper claim surface | Formal-core v2 target | Gate | Current status |
|---|---|---:|---|
| Paper I `thm:main_rcp`, Conditional Non-Lossy Self-Update Preservation Theorem | `RCP.finite_paper_preservation` plus the one-step, trajectory, recovery, monitor, summability, and concrete-refinement theorems | A/B/C | **Abstract wrapper implemented; one finite classical reference implemented; exact paper theorem still deferred.** The full probability, semantic ambiguity, mutual-information, and quantum-relative-entropy meanings remain open. |
| Paper I state-safe-set and update-admissibility predicates | `RCP.PaperSemantics` | A plus concrete refinement | **Explicit abstract boundary implemented.** Exact Paper I equivalence remains open. |
| Paper I no-op-feasibility premise | `RCP.AcceptedNoOp`, `RCP.NoOpFeasible` | A | **Abstract exact.** It remains a separate premise. |
| Paper I Lyapunov expectation and squared-motion conclusion | `RCP.PreservationMonitors`, `RCP.finite_lyapunov_motion_bound`, `ClassicalFinite.binaryPreservationMonitors` | A/B plus probability refinement | **Concrete reference exact for KL-to-target accounting.** Conditional expectation and squared state motion remain deferred. |
| Paper I unsupported ambiguity-collapse conclusion | `RCP.finite_ambiguity_collapse_bound`, `ClassicalFinite.binaryUnsupportedCollapse_step` | A/B plus semantic refinement | **Concrete reference exact for the declared malformed-certificate indicator.** It is not the paper semantic ambiguity quantity. |
| Paper I self-model relevance conclusion | `RCP.finite_self_model_relevance_bound`, `ClassicalFinite.binaryRelevance_step` | A/B plus semantic refinement | **Concrete reference exact for target-fit and normalization evidence.** It is not mutual information. |
| Paper I summability consequences | `RCP.SummableMonitorBudgets`, `toUniformMonitorBudgetCaps`, `infinite_monitor_bounds_of_summable`, `infinite_cumulative_motion_bounded_of_summable` | A | **Abstract exact.** Concrete error-sequence premises remain explicit. |
| Paper I `thm:finite_horizon_constructive_recovery` | `RCP.RecoveryCompositionLaws`, `RCP.composedRecovery`, `RCP.finite_endpoint_recovery_bound`, `ClassicalFinite.binaryRecoveryCompositionLaws` | A/B plus later channel refinement | **Concrete reference exact for the binary discrete metric and exact zero-extension recovery.** Trace-distance/channel recovery remains deferred. |
| Aggregate local recovery accounting | `RCP.finite_composed_recovery_bound` | A | **Implemented separately.** It is not used as a substitute for endpoint rollback. |
| Finite proof-carrying trajectory | `RCP.FiniteAcceptedTrajectory`, finite closure theorems, `ClassicalFinite.binaryWorkedTrajectory` | A/B | **Concrete reference implemented.** The path is `initial → target → target`. |
| Finite progress composition | `RCP.finite_progress_monotone`, strict-witness field in `FinitePaperPreservation`, `ClassicalFinite.binaryWorkedTrajectory_first_step_strict` | A/B | **Concrete non-vacuous witness implemented.** Progress is actual KL-distance reduction. |
| Finite protected-loss composition | `RCP.transportedDistinction`, `RCP.finite_composed_nonloss_bound`, `ClassicalFinite.klDivergence_extendByZero` | A/B/C | **Concrete finite KL preservation implemented for zero-coordinate extension.** General data processing and quantum meanings remain deferred. |
| Conditional infinite accepted trajectory | `RCP.SuccessorAvailability`, `RCP.conditional_infinite_trajectory_exists` | A | **Abstract exact.** Availability is explicit and is not inferred from checker soundness. |
| Conditional infinite paper-domain closure | `RCP.conditional_infinite_paper_trajectory_exists` | A | **Abstract exact.** Concrete Paper I semantic identification remains deferred. |
| Finite-prefix recovery/monitor preservation on infinite paths | `RCP.finitePrefixOfInfinite` and the infinite-prefix theorems | A | **Implemented abstractly.** |
| Paper I direct-engine construction shape | `RCLM.ArchitectureEngine`, `RCLM.ArchitectureEngineStep`, `RCLM.rclm_architecture_successor_theorem` | RCLM after A/B | **Structural conditional theorem implemented.** Proposal, certifier, selector, realizer, coverage, trust, resource, domain, and checker premises are explicit. Exact Paper I engine semantics are not claimed. |
| Paper I/Paper II successor-availability or generator-completeness premise | `RCLM.ArchitectureSuccessorAvailability`, `RCLM.conditional_infinite_architecture_trajectory_exists` | RCLM after A/B | **Abstract exact as a conditional existence boundary.** Availability remains an argument and is never derived from checker soundness. |
| Paper I canonical diagonal/reference checker soundness | `ClassicalFinite.binaryCheck_eq_true_iff`, `binary_checker_refines_kernel` | B | **Concrete finite reference checker implemented.** |
| Batch-13R classical/diagonal reference entry | `RCP.ClassicalFinite`, `RCP.ClassicalBinary` | B | **Gate B complete at the declared finite reference scope.** Exact identity with the complete paper object remains unclaimed. |
| Paper II typed RCLM state/update/certificate surfaces | `RCLM.State`, `RCLM.Update`, `RCLM.CertificatePacket`, `RCLM.ClassicalBinary` | RCLM after B | **Substantive finite reference types implemented.** Arbitrary learned-system semantics remain deferred. |
| Paper II substantive RCLM-to-RCP refinement | `RCLM.KernelRefinement`, `RCLM.MonitorRefinement`, `RCLM.CheckerRefinement`, generic transport theorems | RCLM after B | **Implemented and audited at the theorem-relevant Gate B scope.** General Paper II semantic identity remains deferred. |
| Paper II checker soundness theorem | `RCLM.ClassicalBinary.checker`, `RCLM.rclm_checker_refines_rcp`, `RCLM.rclm_checker_pair_refines_rcp` | RCLM after B | **Concrete Gate B RCLM checker and acceptance refinement implemented.** Architecture-wide compiler/checker equivalence remains deferred. |
| Paper II architecture successor theorem | `RCLM.rclm_architecture_successor_theorem` | RCLM after A/B | **Conditional structural theorem implemented.** It returns typed RCLM obligations, forgotten RCP obligations, recovery and monitor refinement evidence, successor-domain closure, trust/resource validity, and trust-anchor preservation. Exact pinned theorem equivalence remains open. |
| Paper II direct-engine finite reference entry | `RCLM.ClassicalBinary.architectureEngine`, `architectureSuccessorAvailability`, `improvement_direct_engine_successor` | RCLM after B | **Concrete reference implementation.** The first step is strict KL-derived improvement and later available steps are accepted stability successors. This is not indefinitely strict RSI. |
| Paper II conditional infinite architecture trajectory | `RCLM.conditional_infinite_architecture_trajectory_exists`, `RCLM.infinite_architecture_step_result`, concrete classical trajectory | RCLM after B | **Implemented under explicit architecture successor availability.** Checker soundness alone is insufficient. |
| Finite-dimensional quantum non-loss/recovery | future `RCP.QuantumFinite` implementation | C | **Not implemented.** |

## Gate verdicts

```text
Abstract Gate A theorem kernel: complete and audited
Gate B finite classical reference: complete and audited
Substantive Gate B RCLM-to-RCP refinement: implemented and audited
Conditional architecture successor theorem: implemented
Conditional architecture infinite trajectory: implemented with explicit availability
Concrete Gate B direct-engine reference: implemented
Exact Paper I theorem equivalence: false
Exact Paper II theorem equivalence: false
Gate C quantum theorem: open
Executable RSI refinement: not licensed
```

## Mapping discipline

1. A compiled structural theorem is not called an exact paper mechanization until
   every paper object, assumption, and conclusion is identified.
2. Checker soundness never implies successor availability, generator coverage, or
   useful strict improvement.
3. The concrete classical infinite engine path proves domain-preserving accepted
   continuation; after its first strict improvement it may use stability steps.
4. Aggregate local recovery accounting and endpoint rollback remain distinct.
5. The malformed-certificate indicator is not semantic ambiguity, and target-fit
   relevance is not mutual information.
6. The zero-coordinate embedding is not a theorem about every stochastic channel.
7. Historical v1 files remain canonical only for their declared finite scope.
