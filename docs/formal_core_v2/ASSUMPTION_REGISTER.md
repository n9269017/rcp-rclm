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
| A3 | divergence/protected-value laws used by an instantiation are lawful | concrete non-loss interpretation | `RCP.LawfulDivergence`; Gate B/C instance | **finite Gate B discharged** by support-aware KL and `binaryKLDivergence`; quantum instance open |
| A4 | cross-time protected-distinction transport is correctly tied to the update | non-loss theorem | `Kernel.transportProtected`; instantiation/refinement proof | **finite Gate B discharged for the declared identity transport and zero-coordinate embedding**; general paper transport open |
| A5 | recovery map is tied to the actual candidate update | recovery theorem | candidate-indexed `Kernel.recover` and `ConstructiveRecovery` | represented; concrete binary and zero-extension recoveries supplied |
| A6 | residual evaluator is the declared evaluator for the certificate packet | checker theorem | candidate/certificate-indexed `Kernel.residual`; concrete checker refinement | **finite Gate B discharged** by `binaryResidual`, `binaryCheck_eq_true_iff`, and `binary_checker_refines_kernel` |
| A7 | trusted checker is sound | accepted-step theorem | proof field of `RCP.TrustedChecker` | abstractly represented; concrete binary checker proved sound |
| A8 | trust/verifier evidence is valid | accepted-step theorem | `Kernel.trustValid` proposition and checker proof | represented; finite binary instance discharged |
| A9 | resource evidence is valid | accepted-step theorem | `Kernel.resourceValid` proposition and checker proof | represented; finite binary instance discharged |
| A10 | reality/uncertainty containment evidence is valid | accepted-step theorem | `Kernel.realityContained` proposition and checker proof | represented; finite binary instance discharged and non-universality witnessed |
| A11 | strict witness is meaningful for the declared progress functional | strict-progress theorem | `Kernel.strictWitness` and `StrictProgressWhenWitness` | **finite Gate B discharged** by KL-to-target progress and `binaryProgress_initial_lt_target`; general RCLM meaning open |
| A12 | every admissible invariant-preserving state has an accepted successor | infinite-horizon theorem | explicit `RCP.SuccessorAvailability` | represented and intentionally assumed; not discharged by Gate B's finite trajectory |
| A13 | finite resource bounds permit checker/generator execution | executable phase | later cost theorem/implementation evidence | deferred |
| A14 | learned or empirical systems satisfy the abstraction boundary | learned-entry/benchmark phase | later refinement and audit evidence | deferred |

## Paper-alignment assumptions and refinement obligations

| ID | Assumption or refinement obligation | Required by | Represented or discharged where | Status |
|---|---|---|---|---|
| A15 | paper state-safe membership is equivalent to kernel admissibility plus invariant preservation | Paper I `K_RCP^state` mapping | `RCP.PaperSemantics.stateSafe_iff` | abstract boundary represented; exact Paper I equivalence open |
| A16 | paper update admissibility is equivalent to accepted formal step obligations | Paper I `A_RCP(t,rho,Phi)` mapping | `RCP.PaperSemantics.updateAdmissible_iff` | abstract boundary represented; exact Paper I equivalence open |
| A17 | no-op is feasible on the mapped theorem domain | Paper I main-theorem premise | `RCP.AcceptedNoOp`, `RCP.NoOpFeasible`, paper wrappers | represented as explicit premise; Gate B does not claim global no-op feasibility |
| A18 | a named Lyapunov monitor satisfies one-step drift with charged motion and error | Paper I Lyapunov conclusion | `PreservationMonitors.lyapunovStep`; `binaryPreservationMonitors` | **finite Gate B discharged for KL-to-target Lyapunov and KL-derived motion charge**; conditional-expectation and squared-distance identification open |
| A19 | unsupported ambiguity collapse has a nonnegative named monitor and one-step budget | Paper I ambiguity conclusion | `PreservationMonitors.ambiguityStep`; binary malformed-certificate indicator | **finite Gate B discharged only for the declared packet indicator**; semantic ambiguity interpretation open |
| A20 | self-model relevance has a transported named monitor and one-step loss budget | Paper I relevance conclusion | `PreservationMonitors.relevanceStep`; binary target-fit/normalization relevance | **finite Gate B discharged only for the declared finite evidence labels**; mutual-information interpretation open |
| A21 | the nonnegative error sequences satisfy standard summability hypotheses | Paper I infinite-horizon analytic conclusions | `RCP.SummableMonitorBudgets` and `toUniformMonitorBudgetCaps` | standard bridge implemented; concrete infinite sequence premise remains explicit |
| A22 | state distance has zero self-distance and triangle inequality, and each recovery map is nonexpansive | Paper I endpoint recovery theorem | `RCP.RecoveryCompositionLaws`; `binaryRecoveryCompositionLaws` | **finite Gate B discharged for the binary discrete metric**; trace-distance/channel instance open |
| A23 | protected value/transport are finite KL or quantum relative entropy and pair pushforward, with support laws | exact information-theoretic reading | `ClassicalFinite` and future Gate C | **finite KL/support/conservative-extension component discharged at Gate B**; general pushforward/data-processing and quantum component open |
| A24 | every theorem-relevant RCP field, paper monitor law, and recovery law is preserved by RCLM refinement | Paper II refinement theorem | expanded `RCLM.Refinement` proof | open; next selected obligation |
| A25 | a substantive RCLM checker exists and acceptance refines to RCP obligations | Paper II checker/architecture theorem | `RCLM.rclm_checker_refines_rcp` | open |
| A26 | architecture generator/certifier/selector/realizer and witness-library premises are supplied when invoked | Paper II engine theorem | architecture structures and theorem parameters | open |

## Gate B finite-reference premises

| ID | Premise | Represented or discharged where | Status |
|---|---|---|---|
| B1 | finite masses are nonnegative and normalized | `ClassicalFinite.Distribution` | represented by proof fields |
| B2 | KL denominator support covers every positive numerator mass | `ClassicalFinite.SupportedBy` | explicit theorem hypothesis; automatically discharged for `PositiveDistribution` |
| B3 | the binary information witness has strictly positive KL gap | `uniformBinary_kl_biasedBinary_pos` | proved |
| B4 | the conservative extension adds exactly one zero-mass head coordinate | `ZeroExtension`, `extendByZero` | represented and proved normalized |
| B5 | recovery drops the declared head coordinate | `recoverZeroExtension`, `recover_extendByZero` | exact recovery proved |
| B6 | the finite packet grammar consists exactly of improvement and stability packets | `binaryCheck_eq_true_iff` | proved |
| B7 | strict progress means a strict reduction in KL distance to `biasedBinary` | `binaryProgress`, `binaryProgress_initial_lt_target` | proved |
| B8 | the binary monitor semantics are the scoped KL/packet/evidence meanings recorded in `GATE_B_CLOSURE.md` | `binaryPreservationMonitors` | proved for all `StepObligations`; no Paper I expectation/MI identity claimed |

## Gate verdicts

Every assumption used by the abstract Gate A public theorems is represented as
a structure field, proposition, theorem parameter, or explicit availability
premise.

Gate B discharges the finite reference obligations for actual Shannon/KL
quantities, support-aware nonnegativity, conservative extension, exact recovery,
KL-derived strict progress, concrete residuals and checker soundness, a discrete
recovery metric, and scoped finite monitors. It does not discharge the remaining
Paper I probability/semantic/quantum identifications or Paper II RCLM refinement.

## Foundational proof dependencies

The preserved `#print axioms` audits report standard Lean/mathlib foundational
principles and no `sorryAx`. Gate A and Gate B have separate public theorem audit
files under `docs/formal_core_v2/audit/`.

## Prohibited implicit inferences

```text
checker soundness ⇒ successor existence
checker soundness ⇒ generator coverage or direct-engine construction
finite trajectory ⇒ unbounded empirical RSI
internal progress ⇒ external benchmark improvement
certificate fields marked true ⇒ certificate propositions
finite Gate B KL ⇒ arbitrary stochastic-channel data processing
finite Gate B KL ⇒ quantum relative entropy
binary malformed-packet indicator ⇒ Paper I semantic ambiguity
binary target-fit relevance ⇒ mutual information
PaperSemantics equivalence field ⇒ concrete Paper I equivalence without proof
abstract endpoint recovery ⇒ trace-distance/channel recovery
Summable monitor premise ⇒ empirical bounded error without a concrete proof
typed RCLM field names ⇒ substantive architecture semantics
RCP checker theorem ⇒ RCLM checker refinement
```

Any new axiom or undischarged theorem premise must receive an ID, source module,
reason for remaining open, and list of dependent public theorems.