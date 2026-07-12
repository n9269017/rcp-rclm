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
- **Abstract exact**: the inference and conclusion are proved under explicit abstract
  laws; a paper-specific refinement must still identify the abstract objects.
- **Structural**: the inference pattern agrees, but paper-specific quantities,
  transports, laws, or certificate meanings remain abstract.
- **Deferred**: exact identification requires Gate B, Gate C, or substantive RCLM
  refinement.
- **Mismatch**: the current Lean theorem proves a genuinely different or weaker
  statement and must be strengthened or the mapped paper claim narrowed.

The initial line-by-line comparison is in `GATE_A_PAPER_ALIGNMENT_AUDIT.md`.
Subsequent theorem-strengthening status is in
`GATE_A_ALIGNMENT_RESOLUTION_LOG.md`.

## Named-claim mapping

| Paper claim surface | Formal-core v2 target | Gate | Current status |
|---|---|---:|---|
| Paper I `thm:main_rcp`, Conditional Non-Lossy Self-Update Preservation Theorem | checker/domain/progress/non-loss theorems plus `RCP.PreservationMonitors` and finite monitor composition | A/B/C | **Structural, not exact.** The abstract one-step, finite trajectory, progress, protected-value, endpoint recovery, Lyapunov/motion, ambiguity, and transported relevance conclusions now exist. Exact safe-set/admissibility refinement, no-op feasibility, standard probabilistic/expectation semantics, finite-KL or quantum-relative-entropy meaning, and the final paper wrapper remain open. |
| Paper I no-op-feasibility premise | no current public declaration | A / paper wrapper | **Mismatch remains.** The premise must be represented explicitly or removed from the mapped paper theorem if formally unnecessary. |
| Paper I state-safe-set and update-admissibility semantics | `K.admissible`, `K.protectedInvariant`, `TrustedChecker.sound` | A / refinement | **Structural.** No theorem yet identifies these abstract predicates with the full paper definitions of `K_RCP^state` and `A_RCP`. |
| Paper I Lyapunov expectation and squared-motion conclusion | `RCP.PreservationMonitors`, `RCP.finite_lyapunov_motion_bound` | A plus concrete probability refinement | **Abstract exact for the telescoping inequality.** `motionCharge` may be instantiated as `κ * E[d²]`, but that probabilistic identification is not yet proved. |
| Paper I unsupported ambiguity-collapse conclusion | `RCP.finite_ambiguity_collapse_bound` | A plus semantic refinement | **Abstract exact for additive composition.** The paper-specific ambiguity variable and estimator meaning remain deferred. |
| Paper I self-model relevance conclusion | `RCP.finite_self_model_relevance_bound` with explicit `transportRelevance` | A plus B/C or RCLM semantics | **Abstract exact for transported-value composition.** Identification with the paper's mutual information is deferred. |
| Paper I finite and infinite summability consequences | finite monitor theorems, infinite prefix theorems, `RCP.UniformMonitorBudgetCaps`, `RCP.infinite_monitor_uniform_bounds`, `RCP.infinite_cumulative_motion_bounded` | A plus analytic refinement | **Partially resolved.** Uniform bounded-partial-sum conclusions are proved. A standard `Summable`-to-cap bridge for the concrete nonnegative error sequences remains open if the exact paper wording is retained. |
| Paper I direct-engine construction claim | explicit `RCP.SuccessorAvailability`; no construction theorem | later engine/refinement layer | **Not mechanized as construction.** Availability is an explicit assumption, not a generator, builder, coverage theorem, or direct-engine theorem. |
| robust reflective successor/domain-invariance claim | `RCP.StepObligations`, accepted-step soundness, finite/infinite domain closure | A plus paper-specific refinement | **Structural.** Abstract domain closure is implemented; the paper's seed-library, builder, uncertainty, trust, goal, reality, and tractability premises are not yet refined into one wrapper. |
| finite proof-carrying trajectory claim | `RCP.FiniteAcceptedTrajectory`, `RCP.finite_trajectory_closure`, `RCP.finite_trajectory_step_sound` | A | **Structural.** The induction and accepted-prefix shape is implemented and audited; paper-specific packet grammar and builder traces are deferred. |
| finite progress composition claim | `RCP.finite_progress_monotone` | A/B | **Exact for the abstract scalar functional; deferred for the paper ability-set order.** A concrete meaningful strict witness remains open. |
| finite protected-loss composition claim | `RCP.transportedDistinction`, `RCP.finite_composed_nonloss_bound` | A/B/C | **Structural.** The additive transported-value theorem is implemented. Exact finite-KL and quantum-relative-entropy readings require Gates B and C. |
| Paper I `thm:finite_horizon_constructive_recovery` | `RCP.RecoveryCompositionLaws`, `RCP.composedRecovery`, `RCP.finite_endpoint_recovery_bound` | A plus concrete metric/channel refinement | **Abstract exact and clean-CI-built.** The theorem constructs the rollback-order composition and proves the endpoint distance bound. Gate B/C must identify the abstract distance and recovery maps with the concrete classical/quantum objects. |
| aggregate local recovery accounting | `RCP.finite_composed_recovery_bound` | A | **Implemented separately.** This remains an aggregate local-error theorem and is not used as a substitute for endpoint rollback. |
| conditional infinite accepted trajectory | `RCP.SuccessorAvailability`, `RCP.conditional_infinite_trajectory_exists` | A | **Structural.** Explicit successor availability and infinite recursion are implemented; this is not the full seed-library/builder theorem. |
| finite-prefix recovery and monitor preservation on infinite paths | `RCP.finitePrefixOfInfinite`, infinite endpoint/monitor prefix theorems | A | **Implemented.** Every finite prefix inherits the finite Gate A conclusions. |
| Paper I canonical diagonal/reference checker soundness | future concrete checker instance refining `RCP.TrustedChecker` | B plus checker refinement | **Deferred.** The concrete finite distributions, packet grammar, goal/uncertainty/trust objects, and cost ledger are not instantiated. |
| Batch-13R classical/diagonal reference entry | `RCP.ClassicalFinite`, future concrete kernel/checker/trajectory | B | **Definitions started only.** Shannon and KL expressions exist; laws, conservative extension, recovery, checker refinement, and a nonconstant worked trajectory remain open. |
| strict ability/progress expansion | `RCP.StrictProgressWhenWitness`, per-step soundness, finite progress monotonicity | A/B | Abstract implication implemented. A concrete semantically meaningful novelty witness remains open. |
| Paper II typed RCLM state/update/certificate surfaces | `RCLM.State`, `RCLM.Update`, `RCLM.CertificatePacket` | RCLM | **Structural interfaces only.** Field names do not yet prove density, semantic, goal, uncertainty, trust, ability, estimator, or resource meanings. |
| Paper II substantive RCLM-to-RCP refinement | `RCLM.rclm_checker_refines_rcp` | RCLM after B | **Not implemented.** Current `RCLM.Refinement` does not preserve all theorem-relevant fields or checker acceptance. |
| Paper II `thm:rclm-batch13r-checker-soundness` | concrete RCLM checker plus `RCLM.rclm_checker_refines_rcp` | RCLM after B | **Not implemented.** No substantive RCLM checker is defined in Formal Core v2. |
| Paper II architecture successor/direct-engine theorem | `RCLM.rclm_architecture_successor_theorem` | RCLM after A/B | **Not implemented.** The architecture module intentionally contains no theorem declaration yet. |
| finite-dimensional quantum non-loss/recovery claims | future `RCP.QuantumFinite` implementation | C | **Not implemented.** Density matrices, channels, support conditions, quantum relative entropy, and recovery laws remain open. |

## Build and audit evidence

The first complete abstract composition audit remains recorded in
`AXIOM_AUDIT.md`. The endpoint and monitor strengthening at source head
`fb4e0d8437ca62cf89d97811eba21be395a1122e` passed:

```text
workflow run:  29186485073
artifact:      formal-core-v2-gate-a-audit-29186485073-1
artifact SHA:  sha256:f23a9fc7d7e5afda589c95d455dfcd842eb2e3cc5ea6877f86148e06af233114
```

A later successful workflow containing the expanded theorem-axiom list is the
authoritative audit evidence for the final head.

## Paper-alignment verdict

```text
Gate A abstract successor, endpoint recovery, and monitor composition kernel:
  implemented and clean-CI-built
ALIGN-06 endpoint recovery mismatch:
  resolved at abstract Gate A level
ALIGN-03/04 monitor composition:
  finite and uniform-prefix abstract schemas implemented
Exact Paper I theorem equivalence:
  false
Exact Paper II architecture theorem equivalence:
  false
Gate A paper-alignment closure:
  not yet passed
```

The next Gate A-only tasks are the Paper I safe-set/update-admissibility
refinement, the no-op-feasibility premise, and—if exact paper wording is
retained—a standard summability bridge. Gate B then supplies the first concrete
information-theoretic instantiation.

## Mapping discipline

1. A paper theorem is not marked mechanized until its mapped Lean theorem exists,
   builds under the pinned graph, contains no admitted proof, and has matching
   assumptions and conclusions.
2. Abstract exactness must not be reported as a concrete KL, quantum, semantic, or
   empirical theorem without the corresponding refinement.
3. Checker soundness never implies successor existence, generator coverage, or
   direct-engine construction.
4. `RCP.finite_composed_recovery_bound` and
   `RCP.finite_endpoint_recovery_bound` are distinct theorems and must not be
   conflated.
5. Historical v1 files remain valid only for their declared canonical finite scope
   and are not proofs of the v2 paper theorem stack.
