# Gate D assumption register

This register separates Gate D theorem premises from proved consequences and from
future learned-language-model refinement obligations.

## Abstract Gate D premises

| ID | Premise | Formal representation | Current status |
|---|---|---|---|
| D1 | The inherited v2 kernel is the intended base theorem kernel | `FrontierKernel base` | represented; supplied by unchanged Formal Core v2 |
| D2 | The inherited base checker is sound | `RCP.TrustedChecker base` | represented and discharged by selected v2 checkers |
| D3 | Every frontier member is actually solved under the selected task semantics | `FrontierKernel.frontierSound` | explicit field; concrete reference discharged definitionally |
| D4 | Learned-checker acceptance refines to base-checker acceptance | `TrustedLearnedChecker.refinesBase` | explicit proof field; concrete reference discharged |
| D5 | Learned-checker acceptance proves every Gate D-specific obligation | `TrustedLearnedChecker.learnedSound` | explicit proof field; concrete reference discharged |
| D6 | The certificate's protected frontier belongs to the predecessor frontier | `protectedFrontierCertified` | checked per accepted step |
| D7 | The protected frontier is retained by the candidate successor | `protectedFrontierRetained` | checked per accepted step |
| D8 | The complete predecessor frontier is included in the successor frontier | `StrictFrontierExpansion.1` | checked per accepted step |
| D9 | The successor frontier has strictly greater finite cardinality | `StrictFrontierExpansion.2` | checked per accepted step |
| D10 | The named generator is the predecessor's active generator | `generatorIsActive` | checked per accepted step |
| D11 | The generator satisfies the declared generator-domain predicate | `generatorBound` | checked per accepted step |
| D12 | The proposal was produced by the bound generator from the actual predecessor | `proposalProduced` | checked per accepted step |
| D13 | The proposal binds the actual realized candidate | `proposalBindsCandidate` | checked per accepted step |
| D14 | The certificate package hash equals the active predecessor package hash | `packageHashIsActive` | checked per accepted step |
| D15 | The generator is bound to that package hash | `packageHashBound` | checked per accepted step |
| D16 | Goal drift is no larger than its declared budget | `goalDriftWithinBudget` | checked per accepted step |
| D17 | Resource use is no larger than its declared budget | `resourceWithinBudget` | checked per accepted step |
| D18 | Selected information regression is no larger than its declared budget | `informationNonRegression` | checked per accepted step |
| D19 | Every admissible invariant-preserving state has an accepted frontier-expanding successor | `FrontierExpandingSuccessorAvailability` | explicit conditional-infinite premise; not proved generically |

## Finite-theorem consequences

The following are proved, not assumed:

```text
complete inherited RCP.StepObligations at every accepted step
initial-frontier retention at every finite time
strict adjacent frontier-cardinality growth
card(F_0) + t ≤ card(F_t)
cumulative resource bound
cumulative goal-drift bound
cumulative information-regression bound
inherited protected-loss bound
inherited endpoint-recovery bound
inherited Lyapunov/motion bound
inherited trust validity
```

## Concrete one-step reference premises

| ID | Reference fact | Status |
|---|---|---|
| R1 | The predecessor is the canonical Gate B RCLM initial state | discharged |
| R2 | The successor is the canonical Gate B RCLM target state | discharged |
| R3 | The inherited base packet is the proved improvement packet | discharged |
| R4 | Initial frontier is `{baseline}` | discharged |
| R5 | Target frontier is `{baseline, frontierOne}` | discharged |
| R6 | The active generator is `boundedReference` | discharged |
| R7 | The proposal is `improve` and binds the actual improvement candidate | discharged |
| R8 | The active package hash is `root` | discharged |
| R9 | Goal drift is zero | discharged |
| R10 | Resource use and budget are both one | discharged |
| R11 | Information value is Gate B KL distance to target | discharged for the one-step reference |
| R12 | Target information value does not exceed the initial value | proved from the positive Gate B KL gap |

## Future learned-language-model refinement obligations

These are open and are not assumptions silently used by the current public theorems.

| ID | Future obligation | Status |
|---|---|---|
| L1 | A real language-model package refines `Learned.PackageState` | open |
| L2 | A typed model/training/planner update refines `Learned.PackageUpdate` | open |
| L3 | `solves M q` is tied to an independent machine verifier for a declared task class | open |
| L4 | The capability frontier cannot be enlarged by manifest forgery | open executable refinement |
| L5 | The active generator bytes are inside the predecessor package hash | open executable refinement |
| L6 | Raw proposal evidence proves execution by the active generator | open executable refinement |
| L7 | Held-out tasks and answers are inaccessible to the proposal backend | open containment refinement |
| L8 | Model-output distributions refine selected exact/interval KL or diagonal QRE objects | open Gate D runtime refinement |
| L9 | A self-hosted promoted generator produces a later proposal | open |
| L10 | A multi-generation learned trajectory exists | open |
| L11 | Every admissible learned package has a frontier-expanding successor | open and intentionally not inferred |
| L12 | Frontier growth corresponds to broad external usefulness | open empirical/semantic claim |
| L13 | Strict useful improvement occurs at every unbounded recursive step | open |
| L14 | Autonomous or unbounded RSI follows | not proved |

## Prohibited implicit inferences

```text
frontier manifest membership ⇒ task solved
candidate-reported success ⇒ frontier expansion
strict cardinal growth ⇒ semantic usefulness outside the verifier
base checker acceptance ⇒ Gate D-specific obligations
learned checker soundness ⇒ successor availability
one bounded generator ⇒ open-ended generator completeness
one accepted learned step ⇒ self-hosted recursion
conditional infinite construction ⇒ the availability premise
finite self-hosted recursion ⇒ autonomous or unbounded RSI
```
