# Formal Core v2 assumption register

This register separates theorem assumptions from conclusions and prevents
checker soundness, successor existence, empirical validity, and computational
tractability from being conflated.

| ID | Assumption | Required by | Discharged where |
|---|---|---|---|
| A1 | predecessor is in the declared admissible domain | one-step theorem | caller / prior trajectory step |
| A2 | predecessor satisfies the protected invariant | one-step theorem | caller / prior trajectory step |
| A3 | divergence/protected-value laws used by the instantiation are lawful | non-loss theorem | Gate B or Gate C instance |
| A4 | cross-time protected-distinction transport is correctly tied to the update | non-loss theorem | instantiation/refinement proof |
| A5 | recovery map is tied to the actual candidate update | recovery theorem | certificate/instantiation proof |
| A6 | residual evaluator is the declared evaluator for the certificate packet | checker theorem | concrete checker refinement |
| A7 | trusted checker is sound | accepted-step theorem | `Checker.lean` concrete proof, not assumed by runtime |
| A8 | trust/verifier evidence is valid | accepted-step theorem | certificate proof |
| A9 | resource evidence is valid | accepted-step theorem | certificate proof |
| A10 | reality/uncertainty containment evidence is valid | accepted-step theorem | certificate proof |
| A11 | strict witness is semantically meaningful for the declared progress functional | strict-progress theorem | Gate B/C or RCLM instance |
| A12 | every admissible invariant-preserving state has an accepted successor | infinite-horizon theorem | explicit generator-completeness/availability hypothesis |
| A13 | finite resource bounds permit the checker/generator to run | executable phase only | later cost theorem/implementation evidence |
| A14 | learned or empirical systems satisfy the formal abstraction boundary | learned-entry/benchmark phase only | later refinement and audit evidence |

## Prohibited implicit inferences

The following implications are not permitted without separate proofs:

```text
checker soundness ⇒ successor existence
finite trajectory ⇒ unbounded empirical RSI
internal progress ⇒ external benchmark improvement
certificate fields marked true ⇒ certificate propositions
abstract divergence interface ⇒ quantum relative entropy theorem
operator-declared policy ladder ⇒ predecessor-generated self-improvement
```

Any axiom introduced later must receive a new ID, a source module, a reason it
cannot yet be discharged, and a list of public theorems that depend on it.
