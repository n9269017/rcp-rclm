# Paper-to-Lean theorem map — formal core v2

This map records the strongest claim licensed by the compiled declarations.
`implemented` means a declaration exists. `clean-CI-built and audited` means the
pinned workflow built it, scanned the project for admitted proofs and local
axioms, and preserved its kernel axiom report. Neither status alone implies
exact identity with a paper theorem.

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
- **Concrete reference exact**: exact for the declared finite reference instance,
  without claiming that the reference is the complete paper semantics.
- **Structural**: the inference shape agrees but paper-specific meanings remain
  abstract.
- **Deferred**: exact identification requires a later gate or refinement.
- **Mismatch**: the current Lean result is genuinely weaker or different.

The initial comparison is in `GATE_A_PAPER_ALIGNMENT_AUDIT.md`; Gate A
resolutions are in `GATE_A_ALIGNMENT_RESOLUTION_LOG.md`; the finite classical
boundary is in `GATE_B_CLOSURE.md`; RCLM and direct-engine status is in
`RCLM_GATE_B_REFINEMENT_STATUS.md` and `RCLM_DIRECT_ENGINE_STATUS.md`; the
bounded seed-library refinement is in
`PAPER_II_BOUNDED_SEED_LIBRARY_REFINEMENT.md`.

## Named-claim mapping

| Paper claim surface | Formal-core v2 target | Current status |
|---|---|---|
| Paper I `thm:main_rcp` | `RCP.finite_paper_preservation` plus one-step, trajectory, recovery, monitor, summability, and concrete-refinement theorems | **Abstract wrapper implemented; finite classical reference implemented; exact theorem deferred.** Probability, semantic ambiguity, mutual information, and quantum meanings remain open. |
| Paper I state-safe and update-admissibility predicates | `RCP.PaperSemantics` | **Explicit abstract boundary implemented.** Exact paper equivalence remains open. |
| Paper I no-op feasibility | `RCP.AcceptedNoOp`, `RCP.NoOpFeasible` | **Abstract exact.** It remains a separate premise. |
| Paper I Lyapunov and squared-motion conclusion | `RCP.PreservationMonitors`, `finite_lyapunov_motion_bound`, binary monitors | **Concrete reference exact for KL-to-target accounting.** Conditional expectation and squared state motion remain deferred. |
| Paper I ambiguity-collapse conclusion | `RCP.finite_ambiguity_collapse_bound`, binary collapse monitor | **Concrete reference exact for the declared malformed-packet indicator.** It is not semantic ambiguity. |
| Paper I self-model relevance conclusion | `RCP.finite_self_model_relevance_bound`, binary relevance monitor | **Concrete reference exact for finite target-fit evidence.** It is not mutual information. |
| Paper I summability consequences | `RCP.SummableMonitorBudgets` and infinite-prefix theorems | **Abstract exact.** Concrete sequence premises remain explicit. |
| Paper I finite endpoint recovery | `RCP.RecoveryCompositionLaws`, `composedRecovery`, `finite_endpoint_recovery_bound`, binary recovery laws | **Concrete reference exact for the discrete metric and zero-extension recovery.** Trace-distance/channel recovery remains deferred. |
| Finite proof-carrying trajectory | `RCP.FiniteAcceptedTrajectory`, `binaryWorkedTrajectory` | **Concrete reference implemented.** The path is `initial -> target -> target`. |
| Conditional infinite accepted trajectory | `RCP.SuccessorAvailability`, `conditional_infinite_trajectory_exists` | **Abstract exact.** Availability is explicit and never inferred from checker soundness. |
| Paper I/Paper II direct-engine construction shape | `RCLM.ArchitectureEngine`, `ArchitectureEngineStep`, `rclm_architecture_successor_theorem` | **Structural conditional theorem implemented.** Proposal, certifier, selector, realizer, coverage, trust, resource, domain, and checker premises are explicit. |
| Paper I/Paper II architecture successor availability | `RCLM.ArchitectureSuccessorAvailability`, `conditional_infinite_architecture_trajectory_exists` | **Abstract exact as a conditional existence boundary.** It does not imply strict improvement at every step. |
| Paper II typed RCLM state/update/certificate surfaces | `RCLM.State`, `Update`, `CertificatePacket`, `ClassicalBinary` | **Substantive finite reference types implemented.** Arbitrary learned-system semantics remain deferred. |
| Paper II RCLM-to-RCP refinement | `RCLM.KernelRefinement`, `MonitorRefinement`, `CheckerRefinement` | **Implemented and audited at the theorem-relevant Gate B scope.** Architecture-wide semantic identity remains deferred. |
| Paper II checker soundness | concrete RCLM checker plus `rclm_checker_refines_rcp` and `rclm_checker_pair_refines_rcp` | **Concrete Gate B acceptance refinement implemented.** Arbitrary compiler/checker equivalence remains deferred. |
| Paper II architecture successor theorem | `RCLM.rclm_architecture_successor_theorem` | **Conditional structural theorem implemented.** It returns typed RCLM and forgotten RCP obligations, recovery/monitor evidence, domain closure, and trust/resource preservation. |
| Paper II strict direct-engine step | `StrictArchitectureEngineStep`, `rclm_constructive_direct_nl_rsi_engine_aligned` | **Explicit strict-successor boundary implemented.** Strict availability is not inferred from ordinary accepted availability. |
| Paper II verifier, uncertainty, goal, trust, and budget packet clauses | `PaperIISuccessorVerificationSemantics`, robust-reflective alignment theorems | **Explicit abstract interfaces implemented.** Full semantic identity remains a refinement obligation. |
| Paper II bounded witness library | `PaperIIBoundedSeedLibrary.witnesses` | **Finite generic interface implemented; concrete binary witness set implemented.** No arbitrary learned-library claim. |
| Paper II bounded update/certificate grammar | `PaperIIBoundedSeedLibrary.grammar`, `wordDepth`, `proofLength`, maximum bounds | **Concrete reference exact.** Active singleton grammars and bounds of one are proved. |
| Paper II generator coverage on the bounded class | `wordWitnessMember`, `witnessMemberCovered`, `proposalGenerated` | **Explicit theorem fields; concrete binary refinement discharged.** No unbounded generator completeness. |
| Paper II packet builder | `PaperIIBoundedSeedPacket`, `toEngineStep`, `paper_ii_bounded_seed_packet_builder_sound` | **Concrete reference exact for the bounded binary class.** The builder yields complete successor-verification obligations. |
| Paper II bounded packet to RCP refinement | `paper_ii_bounded_seed_packet_refines_architecture` | **Implemented.** Complete RCLM and forgotten RCP obligations are returned together. |
| Paper II verifier-schema identification | `PaperIISeedSemanticIdentification` verifier fields | **Explicit equality refinement; concrete binary identification proved.** |
| Paper II uncertainty-envelope identification | `PaperIISeedSemanticIdentification` envelope fields | **Explicit equality refinement; concrete binary identification proved.** |
| Paper II goal and transport identification | `PaperIISeedSemanticIdentification` goal fields | **Explicit equality refinement; concrete binary identification and zero drift proved.** |
| Paper II successor seed-domain persistence | `PaperIIBoundedSeedLibrary.successorSeedDomain` | **Explicit completeness premise; concrete binary persistence proved.** It is not derived from checker acceptance. |
| Paper II bounded infinite seed-library path | `conditional_infinite_paper_ii_bounded_seed_trajectory_exists` | **Conditional construction implemented.** It requires grammar nonemptiness and successor seed-domain closure. |
| Concrete bounded binary seed path | `ClassicalBinary.classicalInfiniteBoundedSeedTrajectory` and step theorems | **Concrete reference implemented.** One strict KL-derived improvement is followed by stable accepted continuation. |
| Finite-dimensional quantum non-loss/recovery | future `RCP.QuantumFinite` implementation | **Not implemented.** |

## Gate verdicts

```text
Abstract Gate A theorem kernel: complete and audited
Gate B finite classical reference: complete and audited
Substantive Gate B RCLM-to-RCP refinement: complete at declared scope
Conditional architecture successor/direct-engine theorem: implemented
Paper II robust-reflective interfaces: implemented
Bounded seed-library and packet-builder refinement: complete at binary scope
Conditional bounded seed-library trajectory: implemented
Exact Paper I theorem equivalence: false
Exact Paper II theorem equivalence: false
Gate C quantum theorem: open
Executable RSI refinement: not licensed
```

## Mapping discipline

1. Checker soundness never implies successor existence, grammar nonemptiness,
   generator coverage, or successor seed-domain persistence.
2. Finite grammar completeness never implies unbounded proof-search completeness.
3. Bounded seed-library closure never implies arbitrary learned-system entry.
4. Accepted architecture continuation never implies strict improvement at every
   step.
5. The concrete binary path proves one strict improvement and stable recursive
   continuation, not unbounded empirical RSI.
6. Aggregate local recovery accounting and endpoint rollback remain distinct.
7. The finite collapse and relevance monitors are not semantic ambiguity or
   mutual information.
8. The zero-coordinate embedding is not a theorem about every stochastic or
   quantum channel.
9. Historical v1 files remain canonical only for their declared finite scope.
