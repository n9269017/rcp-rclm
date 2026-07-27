# Gate E assumption register

This register separates inherited premises, newly represented Gate E premises, proved
consequences, and executable obligations that remain open for Phase 14.

## Inherited premises

| ID | Premise | Status |
|---|---|---|
| E1 | Formal Core v3 Gate D is the unchanged learned-step foundation | represented by path dependency |
| E2 | The inherited RCP checker is sound | inherited and unchanged |
| E3 | The Gate D learned checker is sound | inherited and unchanged |
| E4 | Gate D frontier members are independently certified tasks | inherited |
| E5 | Accepted Gate D steps preserve every base RCP obligation | inherited theorem |

## Gate E checker premises

| ID | Premise | Formal representation | Status |
|---|---|---|---|
| E6 | Recursive-productivity frontier membership implies actual productivity | `recursiveFrontierSound` | explicit field |
| E7 | Objective choice is endogenous to active package and bound history | `objectiveEndogenous` | checked per accepted step |
| E8 | Mutation program is endogenous to active package and objective | `programEndogenous` | checked per accepted step |
| E9 | Hidden challenge binding is fresh | `challengeFresh` | checked per accepted step |
| E10 | Search history hash binds the active state | `historyBound` | checked per accepted step |
| E11 | Route-level answers are absent | `noRouteHints` | checked per accepted step |
| E12 | Program binds the actual realized candidate | `programBindsCandidate` | checked per accepted step |
| E13 | Program binds the actual Gate D packet | `programBindsCertificate` | checked per accepted step |
| E14 | Complete predecessor recursive frontier is retained | `recursiveFrontierRetained` | checked per accepted step |
| E15 | Named recursive witness is new and present in successor | `recursiveWitnessValid` | checked when present |
| E16 | Autonomous search cost is within declared budget | `searchWithinBudget` | checked per accepted step |

## Search premises

| ID | Premise | Status |
|---|---|---|
| E17 | Enumeration order is finite and deterministic | represented by `List SearchAttempt` |
| E18 | The Gate E checker is the sole acceptance authority | represented by `firstAccepted` |
| E19 | The declared enumeration covers the frozen bounded search class | executable obligation; not inferred from the list alone |
| E20 | At least one accepted candidate exists in the declared enumeration | conditional availability premise |
| E21 | Expanding resource schedules eventually cover any finite-cost legal candidate | future fair-search theorem; not yet proved |

## Proved consequences

The following are proved from the represented premises:

```text
Gate E accepted-step soundness
first-accepted search soundness
sound exhaustion for every enumerated attempt
relative bounded-search completeness
nonstagnation or certified exhaustion
recursive-productivity retention
strict recursive witness validity
finite capability-frontier growth
finite recursive-productivity retention
finite autonomous search-resource bound
constructive availability from accepted-candidate existence in each enumeration
conditional infinite autonomous trajectory existence
```

## Phase 14 executable refinement obligations

| ID | Obligation | Status |
|---|---|---|
| X1 | Active `M4` package emits objective bytes without a host-selected objective | open |
| X2 | Active package emits update-class and mutation-program bytes without route hints | open |
| X3 | Generic parser accepts multiple legal update families rather than one frozen accepted string | open |
| X4 | Enumerator records complete canonical order and coverage of the declared bounded grammar | open |
| X5 | Every rejected candidate receives an immutable complete reason classification | open |
| X6 | Exhaustion packet binds every attempt and proves no accepted attempt was skipped | open |
| X7 | Recursive-productivity tasks have independent machine verifiers | open |
| X8 | Hidden challenges are generated or sampled only after predecessor freeze | open |
| X9 | Accepted Phase 14 trajectory contains no host-authored successful schedule | open |
| X10 | Independent replay removes generator, planner, and training workers | deferred to Phase 18 |

## Prohibited implicit inferences

```text
finite enumeration => complete coverage of an undeclared search space
search exhaustion => no successor exists outside the declared bounded grammar
learned candidate ranking => fair enumeration
one schedule-free step => generic successor availability
recursive-productivity manifest membership => actual recursive productivity
object-level frontier growth => recursive-productivity retention
conditional infinite theorem => empirically unbounded RSI
```
