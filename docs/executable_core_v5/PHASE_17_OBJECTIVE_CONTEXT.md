# Phase 17Y — selected objective policy and challenge context

This increment starts from completed Phase 17X at
`3582c6b591e3f392e6c2d453773b080adc036b65`. Keep PR #68 draft and
unmerged. Phase 17, Gate E, active promotion, and EGC-0 remain open.
The suffix Y denotes this Phase 17 development increment. The roadmap's later
standalone Phase Y concerning verifier succession remains separate.

## The computation addressed

Q constructs the selected finite-observation accepted step. R through X connect
the protected execution and producer-ranking computations to selected captured
inputs and the declared SHA-256 reference. The original present-only objective
policy, however, still runs in Python: it scores eight objective families from
the predecessor's frontiers, component generations, inherited planner projection,
current turn, and supplied public nonce. Its objective and challenge digests
enter Q's producer binding as supplied context.

Y adds a selected Lean interpretation of that policy. It reconstructs all eight
feature objects, hashes their complete canonical encodings, computes the 84
weighted terms for each family, checks the descending ranking and selected
family, and constructs the complete objective decision and freeze. Supporting
hash equations connect the complete captured historical-state image and retained
challenge-commitment opening to the same actual imported producer context.

This is a computation over the retained historical fixture. It does not claim
that the selected objective is globally optimal, that the objective policy was
learned, or that the policy can independently authorize a successor.

## Actual imported inputs

The proof uses V's actual decoded historical state and complete historical JSON
image, U's actual inherited planner projection, W's actual present-only view,
and Q's actual objective, historical-state, and challenge bindings. It composes
with X's actual selected accepted-step result. Literal witnesses in a new packet
must agree with those imports; a separately consistent set of substituted inputs
cannot supply acceptance.

The historical state contributes the complete capability frontier, complete
recursive-productivity frontier, per-family generations, historical logical
active-package identifier, verifier identity, and semantics identifier. The
planner contributes all 84 nonzero signed values with their original indices.
The selected turn and public nonce are current inputs. The nonce is the original
fixed known-fixture value; it is not a new entropy sample.

The historical logical active-package identifier is distinct from the
materialized predecessor package's filesystem-content identifier. The proof
preserves that distinction and does not equate them.

## Declared objective arithmetic and ordering

For family index `f`, generation `g`, and planner projection entry `(i, w)` at
position `j`, the reference reads the complete feature digest as lowercase
hexadecimal digits. It uses:

```text
offset = (i + 11*j) mod 64
feature = (digest_digit[offset] + 3*f + g + j) mod 9 - 4
term = w * feature
projection_score = sum of all 84 terms
score = 20,000 - 521*g + projection_score
```

Each feature hash input contains the exact policy domain, historical logical
active-package identifier, predecessor-state identifier, planner-image digest,
turn, public nonce, objective-family name, and both complete frontiers. Each tie
hash input contains the policy identifier, complete feature digest, and family
name.

The ranking is descending lexicographic order on `(score, tie_digest, family)`.
Family names, rather than numeric family indices, determine the final tie
component. The proof requires complete, unique coverage of all eight fixed
families. The selected fixture chooses `tool_policy`, with projection score 22
and final score 19,501. That is a selected policy result, not an independently
measured capability improvement or a proof of future success.

## Complete objective and challenge records

The decision includes the complete ordered ranking, selected family, declared
goal, bootstrap-report identifier, predecessor and package identifiers, planner
identifier, turn, nonce, fixed verifier, semantics, and false promotion flag.
The freeze binds that complete decision digest to the same predecessor, package,
turn, nonce, verifier and semantics. Its own hash field is excluded from its
hash preimage, as in the existing runtime contract.

The selected challenge-commitment preimage includes the complete fixed policy,
objective-freeze object, candidate-credit bound, and retained fixture secret.
The computed digest must equal the commitment in the actual imported W/Q view.
The objective digest must equal Q's actual `producerBinding.objective`, and the
historical-state digest must equal W/Q's actual predecessor-state binding.

The complete secret encoding also decodes to a typed opening containing the
selected program and all eight four-integer probes. Its reference execution
defines exactly Q's imported vector-task contract at catalog entry 21. This
connects the retained commitment to the actual checked task, while leaving the
opening's origin and operational handling as separate premises.

The retained opening is already public known-answer development data. Checking
its commitment does not attest to secret generation, secrecy from a proposer,
an independent evaluator, wall-clock ordering, or durable one-time consumption.
Those are separate operational obligations. No new challenge or worker is
launched by this increment.

## Complete selected hash inventory

| Category | Complete records | Domain-prefixed input bytes | Padded SHA-256 blocks |
| --- | ---: | ---: | ---: |
| Historical-state image | 1 | 2,982 | 47 |
| Objective feature contexts | 8 | 18,429 | 296 |
| Objective tie contexts | 8 | 1,613 | 32 |
| Complete objective decision | 1 | 2,253 | 36 |
| Objective freeze without self-hash | 1 | 657 | 11 |
| Retained challenge commitment | 1 | 1,117 | 18 |
| **Total** | **20** | **27,051** | **440** |

Every input includes the existing 26-byte
`RCPRCLM-CANONICAL-JSON-V2` domain prefix **including** its terminating NUL.
The 440 ordered block occurrences use 304 distinct incoming-state/full-block
transitions. Each transition's complete schedule, 64 round equations and
feed-forward result is checked using X's unchanged declared SHA-256 reference.
Identical checked transitions can be shared while each input retains its
complete ordered chain, padding, and final digest equation.

The new arithmetic auxiliary imports X's actual arithmetic module. The final
certificate imports X's actual positive certificate and the new Y auxiliary.
No second SHA-256 interpretation or trusted intermediate-digest oracle is
introduced. Python supplies only checked witnesses and preparation consistency
checks; it cannot replace the Lean result.

## Validation and delivery

The gate reconstructs the exact retained X packet and all new selected inputs,
generates the proof sources, and freshly compiles Q through X together with the
X and Y arithmetic auxiliaries. Compilation follows dependency order: Q through
W, X arithmetic, X positive result, then Y arithmetic. There are eight historical
dependency modules and two arithmetic auxiliaries. Same-run import resolution
must bind every module to the object just compiled for this run.

The fixed environment probe, pinned Lean toolchain and foundational-source
checks, exact source and executable identities, durable command records, strict
axiom audits, and intended negative-control diagnostics retain X's requirements.
The approved axiom set is limited to `propext`, `Classical.choice`, and
`Quot.sound`. Placeholder proofs, new axioms, unsafe or partial shortcuts, and
native-decision shortcuts are prohibited. A process termination, timeout,
unrelated compiler error, or missing import cannot satisfy a negative control.

The Python suite independently checks selected objective reconstruction and
arithmetic, complete canonical encodings, ordering, boundary mutations, retained
input binding, generated-source composition, and saved-command validation.
Controlled log fixtures and installer transaction tests are identified as such;
they cannot establish actual Lean acceptance.

The application helper requires the exact clean completed X baseline. It checks
the sealed additive payload, works in an isolated checkout, runs the new tests
and actual Lean gate, and reconstructs the retained evidence before advancing
the user's development checkout. Source and execution evidence receive separate
commits. Native Windows validation remains pending until the operator's own
application succeeds; a Linux result cannot be relabelled as Windows evidence.

```text
python scripts/run_phase17_objective_context_tests.py
python scripts/run_phase17_objective_context_gate.py --test-fixture --require-lean --lean-workspace <prepared-formal-root> --output <new-external-output>
python scripts/run_phase17_objective_context_gate.py --verify-only --output <same-output>
```

Retained verification runs against the original clean tested source commit. It
reconstructs inputs and compares saved evidence without rerunning workers or
compilers. It is not physical attestation of a past execution or complete Phase
18 independent replay. Earlier proof campaigns are not repeated; historical
modules are compiled as dependencies of the new certificate.

## Claim boundaries

A successful actual Y gate may set:

```text
objective_policy_from_context_checked = true
objective_challenge_binding_checked   = true
```

These flags refer to selected computation in the declared Lean reference
semantics. They cover the eight objective scores and their ordering, complete
decision/freeze construction, selected state digest, retained commitment, and
their binding to the existing producer chain. They do not state that every
contextual identity has been authenticated.

Physical byte capture and filesystem behavior, authoritative origin of the
captured historical state, the historical logical package/archive identifiers,
bootstrap-report and public grammar-identifier authenticity, the full planner-image digest and physical
provenance, installed inherited-program identity hashes, nonce provenance,
challenge freshness/secrecy/order, fixed-verifier trust, Python or physical
execution, and the pinned foundation import-cache assumption remain external.
General objective-policy equivalence, policy succession, parser/grammar/planner/
transformer equivalence, external SHA implementation equivalence and collision
resistance remain open.

All twenty-four broader claim flags remain false. Full physical refinement and
attestation, full goal/information semantics, a complete learned or autonomous
transition, authenticated successor context, full-frontier and recursive-
productivity recertification, complete pipeline resource accounting and
authority, containment, active promotion/rollback, hosted CI, broader platform
and campaign validation, Phase 18 replay, Phase 17/Gate E closure, and EGC-0 are
not established. This historical fixture does not demonstrate a newly learned
or self-hosted proposer, an expanded update language, or a fresh live gain.
Unmeasured preparation, proof-checking, CPU, accelerator, memory, storage and
energy costs remain unmeasured rather than zero.
