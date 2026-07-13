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
| A3 | divergence/protected-value laws used by an instantiation are lawful | concrete non-loss interpretation | `RCP.LawfulDivergence`; Gate B/C instance | **finite Gate B discharged**; quantum instance open |
| A4 | cross-time protected-distinction transport is correctly tied to the update | non-loss theorem | `Kernel.transportProtected`; instantiation/refinement proof | **finite Gate B discharged for identity transport and zero-coordinate embedding**; general paper transport open |
| A5 | recovery map is tied to the actual candidate update | recovery theorem | candidate-indexed `Kernel.recover` and `ConstructiveRecovery` | represented; concrete binary and zero-extension recoveries supplied |
| A6 | residual evaluator is the declared evaluator for the certificate packet | checker theorem | candidate/certificate-indexed `Kernel.residual`; concrete checker refinement | **finite Gate B discharged** by `binaryResidual` and the binary checker theorem |
| A7 | trusted checker is sound | accepted-step theorem | proof field of `RCP.TrustedChecker` | abstractly represented; concrete RCP and RCLM binary checkers proved sound |
| A8 | trust/verifier evidence is valid | accepted-step theorem | `Kernel.trustValid` proposition and checker proof | represented; finite binary instances discharged |
| A9 | resource evidence is valid | accepted-step theorem | `Kernel.resourceValid` proposition and checker proof | represented; finite binary instances discharged |
| A10 | reality/uncertainty containment evidence is valid | accepted-step theorem | `Kernel.realityContained` proposition and checker proof | represented; finite binary instance discharged and non-universality witnessed |
| A11 | strict witness is meaningful for the declared progress functional | strict-progress theorem | `Kernel.strictWitness` and `StrictProgressWhenWitness` | **finite Gate B discharged** by KL-to-target progress and a proved strict gap |
| A12 | every admissible invariant-preserving state has an accepted successor | RCP infinite-horizon theorem | explicit `RCP.SuccessorAvailability` | represented and intentionally assumed |
| A13 | finite resource bounds permit checker/generator execution | executable phase | later cost theorem/implementation evidence | deferred |
| A14 | learned or empirical systems satisfy the abstraction boundary | learned-entry/benchmark phase | later refinement and audit evidence | deferred |

## Paper-alignment and RCLM refinement assumptions

| ID | Assumption or refinement obligation | Required by | Represented or discharged where | Status |
|---|---|---|---|---|
| A15 | paper state-safe membership is equivalent to kernel admissibility plus invariant preservation | Paper I state-safe mapping | `RCP.PaperSemantics.stateSafe_iff` | abstract boundary represented; exact Paper I equivalence open |
| A16 | paper update admissibility is equivalent to accepted formal step obligations | Paper I update-admissibility mapping | `RCP.PaperSemantics.updateAdmissible_iff` | abstract boundary represented; exact Paper I equivalence open |
| A17 | no-op is feasible on the mapped theorem domain | Paper I main-theorem premise | `RCP.AcceptedNoOp`, `RCP.NoOpFeasible` | represented as explicit premise |
| A18 | a named Lyapunov monitor satisfies one-step drift with charged motion and error | Paper I Lyapunov conclusion | `PreservationMonitors.lyapunovStep`; binary monitors | **finite Gate B discharged for KL-to-target accounting**; conditional-expectation/squared-motion identity open |
| A19 | unsupported ambiguity collapse has a nonnegative monitor and one-step budget | Paper I ambiguity conclusion | `PreservationMonitors.ambiguityStep`; binary malformed-packet indicator | **finite Gate B discharged only for the declared packet indicator** |
| A20 | self-model relevance has a transported monitor and one-step loss budget | Paper I relevance conclusion | `PreservationMonitors.relevanceStep`; binary target-fit evidence | **finite Gate B discharged only for the declared finite labels**; mutual-information identity open |
| A21 | nonnegative error sequences satisfy standard summability hypotheses | Paper I infinite analytic conclusions | `RCP.SummableMonitorBudgets` | standard bridge implemented; concrete sequence premise remains explicit |
| A22 | state distance has self-zero and triangle laws and each recovery map is nonexpansive | endpoint recovery theorem | `RCP.RecoveryCompositionLaws`; binary laws | **finite Gate B discharged for the discrete metric**; channel/trace-distance instance open |
| A23 | protected value/transport are finite KL or quantum relative entropy and pair pushforward, with support laws | exact information-theoretic reading | `ClassicalFinite` and future Gate C | **finite KL component discharged**; general data processing and quantum component open |
| A24 | every theorem-relevant RCP field, monitor law, and recovery law is preserved by RCLM refinement | Paper II refinement theorem | `RCLM.KernelRefinement`, `MonitorRefinement`, recovery-law transport | **discharged at the substantive Gate B classical scope**; architecture-wide semantic identity remains open |
| A25 | a substantive RCLM checker exists and Boolean acceptance refines to core checker acceptance and obligations | Paper II checker/architecture theorem | `RCLM.CheckerRefinement`, concrete `RCLM.ClassicalBinary.checker` | **discharged at the Gate B classical scope**; arbitrary compiler/checker refinement open |
| A26 | generator proposal, certificate construction, candidate selection, successor realization, and witness coverage are explicitly supplied | Paper II direct-engine theorem | `RCLM.ArchitectureEngine`, `ArchitectureEngineStep` | represented as explicit relational evidence; concrete binary instance discharged |
| A27 | the architecture trust anchor is valid for the predecessor and preserved by an accepted successor | Paper II trust boundary | `ArchitectureEngine.trustAnchorValid`, `trustAnchorSound`, `trustAnchorPreserved` | represented; concrete root-anchor instance discharged |
| A28 | the engine resource authorization implies the kernel resource proposition | Paper II resource boundary | `ArchitectureEngine.resourcePremise`, `resourcePremiseSound` | represented; concrete used/limit instance discharged |
| A29 | accepted generated successors remain in the declared architecture theorem domain | architecture recursion | `ArchitectureEngine.successorDomain` | represented; concrete binary domain discharged |
| A30 | every valid architecture predecessor has a generated, certified, selected, realized, resource-authorized, checker-accepted step | conditional infinite architecture theorem | explicit `RCLM.ArchitectureSuccessorAvailability` | intentionally assumed generically; discharged only for the declared binary reference engine |
| A31 | every recursive architecture step is strictly beneficial rather than merely accepted and non-lossy | indefinitely strict RSI claim | no current generic theorem | **open and not inferred**; the concrete reference path becomes stable after the first strict step |
| A32 | engine relations and RCLM fields have the exact pinned Paper II semantics | exact Paper II theorem equivalence | future line-by-line refinement | open |

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
| B10 | concrete engine coverage contains an improvement witness at `initial` and a stability witness at `target` | `ClassicalBinary.architectureSuccessorAvailability` | proved for the declared binary domain |

## Current verdict

Every assumption used by the abstract Gate A, finite Gate B, substantive RCLM
refinement, and conditional architecture-engine theorem surfaces is represented
as a structure field, proposition, theorem parameter, or explicit availability
premise.

The direct-engine theorem proves a conditional inference from actual engine-stage
evidence and checker acceptance. It does not turn checker soundness into generator
coverage. The concrete binary instance supplies coverage only for its declared
two-state architecture domain and does not prove indefinite strict improvement.

## Foundational proof dependencies

The preserved `#print axioms` audits report standard Lean/mathlib foundational
principles and no `sorryAx`. Gate A, Gate B, and RCLM theorem surfaces have
separate audit files under `docs/formal_core_v2/audit/`.

## Prohibited implicit inferences

```text
checker soundness ⇒ successor existence
checker soundness ⇒ generator coverage or direct-engine construction
architecture successor availability ⇒ strict improvement at every step
accepted stability continuation ⇒ recursive capability growth
finite or infinite formal trajectory ⇒ unbounded empirical RSI
internal progress ⇒ external benchmark improvement
certificate fields marked true ⇒ certificate propositions
finite Gate B KL ⇒ arbitrary stochastic-channel data processing
finite Gate B KL ⇒ quantum relative entropy
binary malformed-packet indicator ⇒ Paper I semantic ambiguity
binary target-fit relevance ⇒ mutual information
typed RCLM field names ⇒ exact Paper II semantics
conditional engine theorem ⇒ arbitrary learned-system engine completeness
```

Any new axiom or undischarged theorem premise must receive an ID, source module,
reason for remaining open, and list of dependent public theorems.
