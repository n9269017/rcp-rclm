# Formal Core v2 assumption register

This register separates theorem assumptions from conclusions and prevents
checker soundness, successor existence, empirical validity, computational
tractability, and paper-specific semantics from being conflated.

An entry marked **open** is a tracked concrete formalization obligation. It is
not an axiom that may silently be used by a public theorem.

## Abstract Gate A assumptions

| ID | Assumption | Required by | Represented or discharged where | Status |
|---|---|---|---|---|
| A1 | predecessor is in the declared admissible domain | one-step theorem | caller / prior trajectory step | represented |
| A2 | predecessor satisfies the protected invariant | one-step theorem | caller / prior trajectory step | represented |
| A3 | divergence/protected-value laws used by an instantiation are lawful | concrete non-loss interpretation | `RCP.LawfulDivergence`; Gate B/C instance | **finite Gate B and selected diagonal Gate C discharged**; arbitrary quantum instance open |
| A4 | cross-time protected-distinction transport is correctly tied to the update | non-loss theorem | `Kernel.transportProtected`; instantiation/refinement proof | **finite Gate B and selected Gate C identity transport discharged**; general paper transport open |
| A5 | recovery map is tied to the actual candidate update | recovery theorem | candidate-indexed `Kernel.recover` and `ConstructiveRecovery` | represented; concrete binary, zero-extension, and selected identity/swap recoveries supplied |
| A6 | residual evaluator is the declared evaluator for the certificate packet | checker theorem | candidate/certificate-indexed `Kernel.residual`; concrete checker refinement | **finite Gate B and selected Gate C discharged** by computed typed/packet residuals |
| A7 | trusted checker is sound | accepted-step theorem | proof field of `RCP.TrustedChecker` | abstractly represented; concrete RCP and RCLM classical/quantum checkers proved sound |
| A8 | trust/verifier evidence is valid | accepted-step theorem | `Kernel.trustValid` proposition and checker proof | represented; finite classical and selected quantum instances discharged |
| A9 | resource evidence is valid | accepted-step theorem | `Kernel.resourceValid` proposition and checker proof | represented; finite classical and selected quantum instances discharged |
| A10 | reality/uncertainty containment evidence is valid | accepted-step theorem | `Kernel.realityContained` proposition and checker proof | represented; finite classical and selected quantum instances discharged and non-universality witnessed |
| A11 | strict witness is meaningful for the declared progress functional | strict-progress theorem | `Kernel.strictWitness` and `StrictProgressWhenWitness` | **Gate B discharged by KL progress; selected Gate C discharged by positive spectral QRE progress** |
| A12 | every admissible invariant-preserving state has an accepted successor | RCP infinite-horizon theorem | explicit `RCP.SuccessorAvailability` | represented and intentionally assumed |
| A13 | finite resource bounds permit checker/generator execution | executable phase | later cost theorem/implementation evidence | deferred |
| A14 | learned or empirical systems satisfy the abstraction boundary | learned-entry/benchmark phase | later refinement and audit evidence | deferred |

## Paper-alignment and RCLM refinement assumptions

| ID | Assumption or refinement obligation | Required by | Represented or discharged where | Status |
|---|---|---|---|---|
| A15 | paper state-safe membership is equivalent to kernel admissibility plus invariant preservation | Paper I state-safe mapping | `RCP.PaperSemantics.stateSafe_iff` | abstract boundary represented; exact Paper I equivalence open |
| A16 | paper update admissibility is equivalent to accepted formal step obligations | Paper I update-admissibility mapping | `RCP.PaperSemantics.updateAdmissible_iff` | abstract boundary represented; exact Paper I equivalence open |
| A17 | no-op is feasible on the mapped theorem domain | Paper I main-theorem premise | `RCP.AcceptedNoOp`, `RCP.NoOpFeasible` | represented as explicit premise |
| A18 | a named Lyapunov monitor satisfies one-step drift with charged motion and error | Paper I Lyapunov conclusion | `PreservationMonitors.lyapunovStep`; classical and selected quantum monitors | **finite references discharged for KL/QRE-to-target accounting**; conditional-expectation/squared-motion identity open |
| A19 | unsupported ambiguity collapse has a nonnegative monitor and one-step budget | Paper I ambiguity conclusion | `PreservationMonitors.ambiguityStep`; classical and selected quantum malformed-packet indicators | **finite references discharged only for the declared packet indicators** |
| A20 | self-model relevance has a transported monitor and one-step loss budget | Paper I relevance conclusion | `PreservationMonitors.relevanceStep`; classical and selected quantum finite labels | **finite references discharged only for declared labels**; mutual-information identity open |
| A21 | nonnegative error sequences satisfy standard summability hypotheses | Paper I infinite analytic conclusions | `RCP.SummableMonitorBudgets` | standard bridge implemented; concrete sequence premise remains explicit |
| A22 | state distance has self-zero and triangle laws and each recovery map is nonexpansive | endpoint recovery theorem | `RCP.RecoveryCompositionLaws`; classical and selected quantum laws | **discharged for the finite discrete metrics and selected exact recovery**; trace-distance/general channel instance open |
| A23 | protected value/transport are finite KL or quantum relative entropy and pair pushforward, with support laws | exact information-theoretic reading | `ClassicalFinite`, `QuantumFinite` | **finite KL and selected commuting-diagonal QRE components discharged**; general noncommuting data processing open |
| A24 | every theorem-relevant RCP field, monitor law, and recovery law is preserved by RCLM refinement | Paper II refinement theorem | `RCLM.KernelRefinement`, `MonitorRefinement`, recovery-law transport | **discharged at substantive Gate B and selected Gate C scopes**; architecture-wide semantic identity open |
| A25 | a substantive RCLM checker exists and Boolean acceptance refines to core checker acceptance and obligations | Paper II checker/architecture theorem | `RCLM.CheckerRefinement`, concrete classical and quantum checkers | **discharged at Gate B and selected Gate C scopes**; arbitrary compiler/checker refinement open |
| A26 | generator proposal, certificate construction, candidate selection, successor realization, and witness coverage are explicitly supplied | Paper II direct-engine theorem | `RCLM.ArchitectureEngine`, `ArchitectureEngineStep` | represented as explicit relational evidence; concrete binary instance discharged |
| A27 | the architecture trust anchor is valid for the predecessor and preserved by an accepted successor | Paper II trust boundary | `ArchitectureEngine.trustAnchorValid`, `trustAnchorSound`, `trustAnchorPreserved` | represented; concrete root-anchor instance discharged |
| A28 | the engine resource authorization implies the kernel resource proposition | Paper II resource boundary | `ArchitectureEngine.resourcePremise`, `resourcePremiseSound` | represented; concrete used/limit instance discharged |
| A29 | accepted generated successors remain in the declared architecture theorem domain | architecture recursion | `ArchitectureEngine.successorDomain` | represented; concrete binary domain discharged |
| A30 | every valid architecture predecessor has a generated, certified, selected, realized, resource-authorized, checker-accepted step | conditional infinite architecture theorem | explicit `RCLM.ArchitectureSuccessorAvailability` | intentionally assumed generically; discharged only for declared finite reference engines |
| A31 | every recursive architecture step is strictly beneficial rather than merely accepted and non-lossy | indefinitely strict RSI claim | no current generic theorem | **open and not inferred**; concrete paths become stable after the first strict step |
| A32 | engine relations and RCLM fields have the exact pinned Paper II semantics | exact Paper II theorem equivalence | line-by-line semantic identification and selected refinements | partially discharged by explicit interfaces; full identity open |
| A33 | the bounded Paper II seed domain refines to the compiled architecture theorem domain | bounded seed-library entry | `PaperIIBoundedSeedLibrary.seedDomain_to_engineDomain` | explicit generic field; concrete binary instance discharged |
| A34 | the declared witness library and certificate-word grammar are finite and the grammar is nonempty on every seed-domain state | bounded packet construction | `witnesses`, `grammar`, `grammarNonempty` | explicit generic fields; concrete singleton grammars discharged |
| A35 | every active grammar word maps to a covered witness and satisfies declared update-word and proof-word bounds | bounded coverage/tractability boundary | `wordWitnessMember`, `witnessMemberCovered`, `wordDepthBound`, `proofLengthBound` | explicit generic fields; concrete bounds equal one |
| A36 | every active grammar word actually supplies proposal, certificate, candidate, realization, resource, and checker evidence | bounded packet-builder soundness | relational fields of `PaperIIBoundedSeedLibrary`; `PaperIIBoundedSeedPacket.toEngineStep` | explicit generic fields; concrete binary instance discharged |
| A37 | the selected bounded-library successor remains in the next bounded seed domain | finite or infinite seed-library recursion | `PaperIIBoundedSeedLibrary.successorSeedDomain` | explicit completeness premise; concrete binary instance discharged |
| A38 | the declared verifier schemas, uncertainty envelopes, goals, transports, refinement relations, distances, and drift budgets equal the compiled Paper II interfaces | exact bounded-class semantic bridge | `PaperIISeedSemanticIdentification` | explicit equality refinement; concrete binary identification discharged |
| A39 | the finite grammar is complete only for the declared bounded witness class | claim discipline | bounded library interface and phase record | explicit limitation; arbitrary proof-search and learned-generator completeness remain open |
| A40 | an infinite bounded seed-library trajectory requires grammar nonemptiness and successor seed-domain closure at every selected state | conditional infinite seed-library theorem | `conditional_infinite_paper_ii_bounded_seed_trajectory_exists` | represented constructively; not derived from checker soundness |

## Gate B finite-reference premises

| ID | Premise | Represented or discharged where | Status |
|---|---|---|---|
| B1 | finite masses are nonnegative and normalized | `ClassicalFinite.Distribution` | represented by proof fields |
| B2 | KL denominator support covers every positive numerator mass | `ClassicalFinite.SupportedBy` | explicit theorem hypothesis; automatic for `PositiveDistribution` |
| B3 | binary information witness has strictly positive KL gap | `uniformBinary_kl_biasedBinary_pos` | proved |
| B4 | conservative extension adds exactly one zero-mass head coordinate | `ZeroExtension`, `extendByZero` | represented and normalized |
| B5 | recovery drops the declared head coordinate | `recoverZeroExtension`, `recover_extendByZero` | exact recovery proved |
| B6 | finite packet grammar consists exactly of improvement and stability packets | `binaryCheck_eq_true_iff` | proved |
| B7 | strict progress means strict reduction in KL distance to `biasedBinary` | `binaryProgress`, `binaryProgress_initial_lt_target` | proved |
| B8 | binary monitor semantics are the scoped meanings in `GATE_B_CLOSURE.md` | `binaryPreservationMonitors` | proved; no expectation/MI identity claimed |
| B9 | concrete RCLM architecture states and packets are canonical lifts of the Gate B core | `RCLM.ClassicalBinary.ArchitectureEvidenceValid` | checked by the RCLM checker |
| B10 | concrete engine coverage contains an improvement witness at `initial` and a stability witness at `target` | `ClassicalBinary.architectureSuccessorAvailability` | proved for declared binary domain |
| B11 | active bounded packet grammar is exactly `{improve}` at `initial` and `{stabilize}` at `target` | `ClassicalBinary.boundedPacketGrammar`, `boundedPacketGrammar_cases` | proved by exhaustive cases |
| B12 | every active bounded word and proof trace has depth at most one | `boundedWordDepth`, `boundedProofLength`, `boundedSeedLibrary` | proved |
| B13 | rejected word is absent from every active grammar | `boundedPacketGrammar_cases` | proved |
| B14 | bounded packet decoders reproduce the concrete engine proposal, certificate, candidate, resource, and successor relations | `ClassicalBinary.boundedSeedLibrary` | proved |
| B15 | declared verifier, uncertainty, and goal objects are definitionally identified with compiled Paper II reference interfaces | `boundedSeedSemanticIdentification` | proved |
| B16 | bounded seed-library path performs strict improvement once and then remains on accepted stable target continuation | concrete seed packets and trajectory | proved at reference scope; not indefinitely strict RSI |

## Gate C selected quantum-reference premises

| ID | Premise | Represented or discharged where | Status |
|---|---|---|---|
| C1 | quantum states are finite complex diagonal matrices indexed by `Fin n` | `QuantumFinite.QuantumMatrix`, `DiagonalDensityMatrix` | frozen and represented |
| C2 | every selected matrix is Hermitian, positive semidefinite, and trace one | `matrix_isHermitian`, `matrix_posSemidef`, `matrix_trace_one`, `DensityMatrixEvidence` | proved |
| C3 | selected von Neumann entropy is the entropy of the diagonal spectrum | `vonNeumannEntropy` | definitional at commuting-diagonal scope |
| C4 | selected quantum relative entropy is finite KL on the diagonal spectra | `quantumRelativeEntropy` | definitional at commuting-diagonal scope |
| C5 | numerator support is contained in denominator support | `QuantumFinite.SupportedBy` | explicit theorem premise; discharged by positive spectral states |
| C6 | selected source-to-target QRE gap is strictly positive | `source_target_quantumRelativeEntropy`, `source_target_quantumRelativeEntropy_pos` | proved |
| C7 | admissible channels preserve the selected matrix-state conditions | `FiniteDiagonalChannel` fields; identity/swap instances | proved for selected family |
| C8 | selected update action equals the declared channel action | `selectedChannel_state_action` | proved exhaustively |
| C9 | recovery is indexed by the actual selected update and is exact | `selectedRecoveryChannel`, `selectedChannel_recovery_exact` | proved for identity/swap family |
| C10 | selected channel preserves entropy and QRE | selected channel preservation theorems | proved for identity/swap family |
| C11 | RCLM state/update/certificate/checker/monitor data refine the selected quantum kernel | `RCLM.QuantumBinary` kernel, checker, recovery, and monitor refinements | proved |
| C12 | checker acceptance yields complete RCLM/RCP obligations and selected density/channel/recovery evidence | `accepted_quantum_architecture_successor` | proved |
| C13 | infinite quantum continuation requires an accepted successor at every admissible state | abstract `SuccessorAvailability` | explicit premise; not derived from checker soundness |
| C14 | general noncommuting density operators, arbitrary CPTP maps, matrix-log QRE, data processing, and Petz recovery are outside the selected reference | claim boundary | explicit open extension, not silently assumed |

## Current verdict

Every assumption used by the abstract Gate A, finite Gate B, substantive RCLM
refinement, conditional architecture engine, bounded seed-library packet builder,
and selected Gate C theorem surfaces is represented as a structure field,
proposition, theorem parameter, equality refinement, or explicit
availability/completeness premise.

The selected Gate C implementation closes a finite commuting-diagonal matrix
reference with actual density-matrix evidence, spectral entropy/QRE, selected
matrix channels, exact candidate-tied recovery, a concrete checker, finite
trajectory, monitors, and RCLM refinement. It does not close the general
noncommuting quantum or exact full-paper semantic obligations.

## Foundational proof dependencies

The preserved `#print axioms` audits report standard Lean/mathlib foundational
principles and no `sorryAx`. Gate A, Gate B, RCLM, and Gate C theorem surfaces
have separate audit files under `docs/formal_core_v2/audit/`.

For the selected Gate C audit, the reported axiom union is:

```text
propext
Classical.choice
Quot.sound
```

## Prohibited implicit inferences

```text
checker soundness ⇒ successor existence
checker soundness ⇒ grammar nonemptiness
checker soundness ⇒ generator coverage or direct-engine construction
checker soundness ⇒ successor seed-domain persistence
finite grammar completeness ⇒ unbounded proof-search completeness
bounded seed-library closure ⇒ arbitrary learned-system seed-domain entry
architecture successor availability ⇒ strict improvement at every step
accepted stability continuation ⇒ recursive capability growth
finite or infinite formal trajectory ⇒ unbounded empirical RSI
internal progress ⇒ external benchmark improvement
certificate fields marked true ⇒ certificate propositions
finite Gate B KL ⇒ arbitrary stochastic-channel data processing
selected diagonal QRE ⇒ arbitrary noncommuting matrix QRE
identity/swap preservation ⇒ general CPTP data processing
exact involutive recovery ⇒ Petz or approximate recovery
binary malformed-packet indicator ⇒ Paper I semantic ambiguity
binary target-fit relevance ⇒ mutual information
typed RCLM field names ⇒ exact Paper II semantics
conditional engine theorem ⇒ arbitrary learned-system engine completeness
```

Any new axiom or undischarged theorem premise must receive an ID, source module,
reason for remaining open, and list of dependent public theorems.
