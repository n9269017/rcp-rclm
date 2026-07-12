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
| A3 | divergence/protected-value laws used by an instantiation are lawful | concrete non-loss interpretation | `RCP.LawfulDivergence`; Gate B/C instance | interface represented; concrete discharge open |
| A4 | cross-time protected-distinction transport is correctly tied to the update | non-loss theorem | `Kernel.transportProtected`; instantiation/refinement proof | interface represented; concrete discharge open |
| A5 | recovery map is tied to the actual candidate update | recovery theorem | candidate-indexed `Kernel.recover` and `ConstructiveRecovery` | represented |
| A6 | residual evaluator is the declared evaluator for the certificate packet | checker theorem | candidate/certificate-indexed `Kernel.residual`; concrete checker refinement | interface represented; concrete discharge open |
| A7 | trusted checker is sound | accepted-step theorem | proof field of `RCP.TrustedChecker` | abstractly represented |
| A8 | trust/verifier evidence is valid | accepted-step theorem | `Kernel.trustValid` proposition and checker proof | represented |
| A9 | resource evidence is valid | accepted-step theorem | `Kernel.resourceValid` proposition and checker proof | represented |
| A10 | reality/uncertainty containment evidence is valid | accepted-step theorem | `Kernel.realityContained` proposition and checker proof | represented |
| A11 | strict witness is meaningful for the declared progress functional | strict-progress theorem | `Kernel.strictWitness` and `StrictProgressWhenWitness` | abstract implication represented; concrete semantics open |
| A12 | every admissible invariant-preserving state has an accepted successor | infinite-horizon theorem | explicit `RCP.SuccessorAvailability` | represented and intentionally assumed |
| A13 | finite resource bounds permit checker/generator execution | executable phase | later cost theorem/implementation evidence | deferred |
| A14 | learned or empirical systems satisfy the abstraction boundary | learned-entry/benchmark phase | later refinement and audit evidence | deferred |

## Paper-alignment assumptions and refinement obligations

| ID | Assumption or refinement obligation | Required by | Represented or discharged where | Status |
|---|---|---|---|---|
| A15 | paper state-safe membership is equivalent to kernel admissibility plus invariant preservation | Paper I `K_RCP^state` mapping | `RCP.PaperSemantics.stateSafe_iff` | abstract boundary represented; concrete equivalence open |
| A16 | paper update admissibility is equivalent to accepted formal step obligations | Paper I `A_RCP(t,rho,Phi)` mapping | `RCP.PaperSemantics.updateAdmissible_iff` | abstract boundary represented; concrete equivalence open |
| A17 | no-op is feasible on the mapped theorem domain | Paper I main-theorem premise | `RCP.AcceptedNoOp`, `RCP.NoOpFeasible`, paper wrappers | represented as explicit premise |
| A18 | a named Lyapunov monitor satisfies one-step drift with charged motion and error | Paper I Lyapunov conclusion | `PreservationMonitors.lyapunovStep` and composition theorems | abstractly represented and composed; expectation semantics open |
| A19 | unsupported ambiguity collapse has a nonnegative named monitor and one-step budget | Paper I ambiguity conclusion | `PreservationMonitors.ambiguityStep` and composition theorems | abstractly represented and composed; semantic instance open |
| A20 | self-model relevance has a transported named monitor and one-step loss budget | Paper I relevance conclusion | `PreservationMonitors.relevanceStep` and composition theorems | abstractly represented and composed; mutual-information instance open |
| A21 | the nonnegative error sequences satisfy standard summability hypotheses | Paper I infinite-horizon analytic conclusions | `RCP.SummableMonitorBudgets` and `toUniformMonitorBudgetCaps` | standard bridge implemented; concrete summability remains a theorem premise |
| A22 | state distance has zero self-distance and triangle inequality, and each recovery map is nonexpansive | Paper I endpoint recovery theorem | `RCP.RecoveryCompositionLaws`, `finite_endpoint_recovery_bound` | abstract theorem discharged; concrete metric/channel instance open |
| A23 | protected value/transport are finite KL or quantum relative entropy and pair pushforward, with support laws | exact information-theoretic reading | Gate B and Gate C | open |
| A24 | every theorem-relevant RCP field, paper monitor law, and recovery law is preserved by RCLM refinement | Paper II refinement theorem | expanded `RCLM.Refinement` proof | open |
| A25 | a substantive RCLM checker exists and acceptance refines to RCP obligations | Paper II checker/architecture theorem | `RCLM.rclm_checker_refines_rcp` | open |
| A26 | architecture generator/certifier/selector/realizer and witness-library premises are supplied when invoked | Paper II engine theorem | architecture structures and theorem parameters | open |

## Abstract Gate A assumption verdict

Every assumption used by the abstract Gate A public theorems is now represented
as a structure field, proposition, theorem parameter, or explicit availability
premise. No paper-specific semantic identification is inferred from notation.
Concrete Gate B/C and RCLM discharge obligations remain open by design.

## Foundational proof dependencies

The preserved `#print axioms` audit reports standard Lean/mathlib foundational
principles and no `sorryAx`. The expanded public theorem list is checked by
`docs/formal_core_v2/audit/GateAAxiomAudit.lean`.

## Prohibited implicit inferences

```text
checker soundness ⇒ successor existence
checker soundness ⇒ generator coverage or direct-engine construction
finite trajectory ⇒ unbounded empirical RSI
internal progress ⇒ external benchmark improvement
certificate fields marked true ⇒ certificate propositions
abstract divergence interface ⇒ finite KL theorem
abstract divergence interface ⇒ quantum relative entropy theorem
PaperSemantics equivalence field ⇒ concrete Paper I equivalence without proof
generic residual nonpositivity ⇒ named monitor inequalities
abstract endpoint recovery ⇒ concrete trace-distance/channel recovery
Summable monitor premise ⇒ empirical bounded error without a concrete proof
typed RCLM field names ⇒ substantive architecture semantics
RCP checker theorem ⇒ RCLM checker refinement
```

Any new axiom or undischarged theorem premise must receive an ID, source module,
reason for remaining open, and list of dependent public theorems.
