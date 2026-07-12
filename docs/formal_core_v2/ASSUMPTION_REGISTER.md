# Formal Core v2 assumption register

This register separates theorem assumptions from conclusions and prevents
checker soundness, successor existence, empirical validity, computational
tractability, and paper-specific semantics from being conflated.

An entry marked **open** is a tracked formalization obligation. It is not an
axiom that may silently be used by a public theorem.

## Abstract Gate A assumptions

| ID | Assumption | Required by | Discharged where | Status |
|---|---|---|---|---|
| A1 | predecessor is in the declared admissible domain | one-step theorem | caller / prior trajectory step | represented |
| A2 | predecessor satisfies the protected invariant | one-step theorem | caller / prior trajectory step | represented |
| A3 | divergence/protected-value laws used by the instantiation are lawful | non-loss theorem | Gate B or Gate C instance | interface represented; concrete discharge open |
| A4 | cross-time protected-distinction transport is correctly tied to the update | non-loss theorem | instantiation/refinement proof | interface represented; concrete discharge open |
| A5 | recovery map is tied to the actual candidate update | recovery theorem | certificate/instantiation proof | represented |
| A6 | residual evaluator is the declared evaluator for the certificate packet | checker theorem | concrete checker refinement | interface represented; concrete discharge open |
| A7 | trusted checker is sound | accepted-step theorem | proof field of `RCP.TrustedChecker`; concrete runtime checker still requires refinement | abstractly represented |
| A8 | trust/verifier evidence is valid | accepted-step theorem | certificate proof | represented as proposition |
| A9 | resource evidence is valid | accepted-step theorem | certificate proof | represented as proposition |
| A10 | reality/uncertainty containment evidence is valid | accepted-step theorem | certificate proof | represented as proposition |
| A11 | strict witness is semantically meaningful for the declared progress functional | strict-progress theorem | Gate B/C or RCLM instance | abstract implication represented; semantics open |
| A12 | every admissible invariant-preserving state has an accepted successor | infinite-horizon theorem | explicit `SuccessorAvailability` hypothesis | represented and intentionally undischarged abstractly |
| A13 | finite resource bounds permit the checker/generator to run | executable phase only | later cost theorem/implementation evidence | deferred |
| A14 | learned or empirical systems satisfy the formal abstraction boundary | learned-entry/benchmark phase only | later refinement and audit evidence | deferred |

## Paper-alignment assumptions and refinement obligations

| ID | Assumption or refinement obligation | Required by | Discharged where | Status |
|---|---|---|---|---|
| A15 | `admissible ∧ protectedInvariant` is equivalent to, or soundly refines, the Paper I state-only safe-set clauses | exact mapping to `K_RCP^state` | paper-specific kernel/refinement theorem | open |
| A16 | accepted `StepObligations` are equivalent to, or soundly refine, the Paper I update-admissibility relation | exact mapping to `A_RCP(t,rho,Phi)` | paper-specific checker/refinement theorem | open |
| A17 | the no-op update is feasible on the mapped theorem domain | exact Paper I main-theorem premise | explicit `NoOpFeasible` premise or documented paper narrowing | open |
| A18 | a named Lyapunov monitor satisfies the one-step drift inequality with a charged motion term and error budget | Paper I Lyapunov conclusion | `RCP.PreservationMonitors.lyapunovStep` and finite/infinite monitor theorems | abstract schema represented and composed; conditional-expectation interpretation open |
| A19 | unsupported ambiguity collapse is a nonnegative named monitor with a certified one-step budget | Paper I ambiguity conclusion | `PreservationMonitors.ambiguityStep` and ambiguity composition theorems | abstract schema represented and composed; semantic instance open |
| A20 | self-model relevance is a named transported monitor with a certified one-step loss budget | Paper I mutual-information conclusion | `PreservationMonitors.relevanceStep`, `transportedRelevance`, and composition theorems | abstract schema represented and composed; mutual-information instance open |
| A21 | error/budget sequences have bounded finite partial sums or satisfy the paper's standard summability hypotheses | Paper I infinite-horizon analytic conclusions | `RCP.UniformMonitorBudgetCaps` plus later `Summable` bridge | bounded-partial-sum premise represented; standard analytic bridge open |
| A22 | state distance has zero self-distance and triangle inequality, and each candidate-tied recovery map is nonexpansive | Paper I endpoint recovery theorem | `RCP.RecoveryCompositionLaws` and `RCP.finite_endpoint_recovery_bound` | abstractly represented and theorem discharged; concrete trace-distance/channel instance open |
| A23 | abstract protected value and transport are identified with finite KL or quantum relative entropy and protected-pair pushforward, with support/domain conditions | exact information-theoretic reading | Gate B and Gate C | open |
| A24 | every theorem-relevant RCP field, including endpoint-recovery and monitor laws, is preserved by RCLM forgetting/refinement | Paper II RCLM-to-RCP theorem | expanded `RCLM.Refinement` proof | open |
| A25 | an RCLM checker exists, has substantive packet semantics, and its acceptance refines to the RCP obligations | Paper II checker and architecture theorems | `RCLM.rclm_checker_refines_rcp` | open |
| A26 | architecture-specific generator, certifier, selector, realizer, witness-library, transport, trust, reality, and resource premises are supplied when a Paper II engine theorem is invoked | Paper II architecture theorem | substantive architecture structures and theorem parameters | open |

## Foundational proof dependencies

The preserved `#print axioms` audit for the public Gate A theorem set reports
standard Lean/mathlib foundational principles and no `sorryAx`. The current
recorded set is:

```lean
[propext, Classical.choice, Quot.sound]
```

The expanded endpoint and monitor theorem list is checked by
`docs/formal_core_v2/audit/GateAAxiomAudit.lean`. These foundational
dependencies are distinct from domain assumptions A1–A26.

## Prohibited implicit inferences

```text
checker soundness ⇒ successor existence
checker soundness ⇒ generator coverage or direct-engine construction
finite trajectory ⇒ unbounded empirical RSI
internal progress ⇒ external benchmark improvement
certificate fields marked true ⇒ certificate propositions
abstract divergence interface ⇒ finite KL theorem
abstract divergence interface ⇒ quantum relative entropy theorem
abstract admissibility ⇒ Paper I K_RCP^state membership
generic residual nonpositivity ⇒ named monitor inequalities
bounded partial sums ⇒ standard Summable without a bridge theorem
abstract endpoint recovery ⇒ concrete trace-distance/channel recovery
operator-declared policy ladder ⇒ predecessor-generated self-improvement
typed RCLM field names ⇒ substantive architecture semantics
RCP checker theorem ⇒ RCLM checker refinement
```

Any new axiom or undischarged theorem premise must receive an ID, source module,
reason for remaining open, and list of dependent public theorems.
