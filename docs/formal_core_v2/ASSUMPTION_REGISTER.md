# Formal Core v2 assumption register

This register separates theorem assumptions from conclusions and prevents checker
soundness, successor existence, empirical validity, computational tractability, and
paper-specific semantics from being conflated.

An entry marked **open** is a tracked formalization obligation. It is not an axiom that
may silently be used by a public theorem.

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

## Paper-alignment obligations discovered by the comparison audit

| ID | Assumption or refinement obligation | Required by | Discharged where | Status |
|---|---|---|---|---|
| A15 | the abstract predicates `admissible` and `protectedInvariant` are equivalent to, or soundly refine, the Paper I state-only safe-set clauses | exact mapping to Paper I `K_RCP^state` | paper-specific kernel/refinement theorem | open |
| A16 | checker-established `StepObligations` are equivalent to, or soundly refine, the Paper I update-admissibility relation `A_RCP(t,rho,Phi)` | exact mapping to Paper I main theorem | paper-specific checker/refinement theorem | open |
| A17 | the no-op update is feasible on the mapped theorem domain | exact Paper I main-theorem premise | explicit `NoOpFeasible` structure/premise, or a documented paper narrowing | open |
| A18 | a declared Lyapunov monitor satisfies the one-step conditional-expectation drift inequality and the laws needed for finite telescoping and squared-motion accumulation | Paper I Lyapunov conclusion | abstract monitor schema plus concrete instance | open |
| A19 | unsupported ambiguity collapse is represented by a nonnegative monitor with a certified one-step `zeta_t` bound | Paper I ambiguity conclusion | abstract monitor schema plus semantic instance | open |
| A20 | self-model relevance is represented by a transported monitor with a certified one-step `xi_t` bound and valid cross-time transport | Paper I mutual-information conclusion | abstract monitor schema plus Gate B/C or RCLM instance | open |
| A21 | the error/budget sequences satisfy the stated finite-sum or infinite summability hypotheses | Paper I analytic infinite-horizon conclusions | explicit theorem parameters/hypotheses | open |
| A22 | `stateDistance` satisfies the metric laws used in the paper endpoint-recovery proof, and each recovery map is typed and nonexpansive (or carries a declared Lipschitz factor) under composition | Paper I `thm:finite_horizon_constructive_recovery` | strengthened recovery interface and theorem | open |
| A23 | the abstract protected value and transport are identified with the paper's finite KL or quantum relative entropy and protected-pair pushforward, including support/domain conditions | exact information-theoretic reading | Gate B and Gate C | open |
| A24 | every theorem-relevant RCP kernel field is preserved by the RCLM forgetting/refinement maps | Paper II RCLM-to-RCP theorem | expanded `RCLM.Refinement` proof | open |
| A25 | an RCLM checker exists, its packet semantics are substantive, and its acceptance refines to the RCP checker obligations | Paper II checker and architecture theorems | `RCLM.rclm_checker_refines_rcp` | open |
| A26 | architecture-specific generator, certifier, selector, realizer, witness-library, transport, trust, reality, and resource premises are supplied when a Paper II direct-engine or robust-reflective theorem is invoked | Paper II architecture theorem | substantive architecture structures and theorem parameters | open |

## Foundational proof dependencies

The preserved `#print axioms` audit for the current public Gate A theorem set reports:

```lean
[propext, Classical.choice, Quot.sound]
```

No audited theorem reports `sorryAx`, and the project declares no local `axiom` in the
claimed source scope. These foundational dependencies are recorded in
`AXIOM_AUDIT.md`; they are distinct from the domain assumptions A1–A26 above.

## Prohibited implicit inferences

The following implications are not permitted without separate proofs:

```text
checker soundness ⇒ successor existence
checker soundness ⇒ generator coverage or direct-engine construction
finite trajectory ⇒ unbounded empirical RSI
internal progress ⇒ external benchmark improvement
certificate fields marked true ⇒ certificate propositions
abstract divergence interface ⇒ finite KL theorem
abstract divergence interface ⇒ quantum relative entropy theorem
abstract admissibility ⇒ Paper I K_RCP^state membership
abstract residual nonpositivity ⇒ Paper I Lyapunov/ambiguity/mutual-information bounds
sum of local recovery errors ⇒ composed endpoint rollback bound
operator-declared policy ladder ⇒ predecessor-generated self-improvement
typed RCLM field names ⇒ substantive architecture semantics
RCP checker theorem ⇒ RCLM checker refinement
```

Any new axiom or undischarged theorem premise introduced later must receive an ID, a
source module, a reason it cannot yet be discharged, and a list of public theorems that
depend on it.
