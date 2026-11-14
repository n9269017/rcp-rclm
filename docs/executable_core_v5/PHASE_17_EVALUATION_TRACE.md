# Phase 17Z: selected evaluator trace and producer verdict prefix

Phase 17Z continues the completed Phase 17Y baseline
`06914d358d155916d8cd9760532ee60b022d3ff5`. It is the next additive increment
within Phase 17, not the later roadmap's separate Phase Z milestone.

## Obligation

Y derives the selected objective and challenge context. Q's
`Phase17Provenance.Produced` checks the actual choice order, a prefix of failed
verdicts followed by one success, and the selected program. Before this
increment, that predicate does not derive the truth of those verdicts from
the candidate programs and retained challenge opening.

Z reconstructs the selected reference evaluator, using the actual imported
Y opening, the eight inherited Q/V program descriptors, and the nine choices
in Q's checked proposal prefix. Stored outcomes are comparison targets, not
inputs to the independent evaluation calculation. This is a finite
refinement of the existing historical fixture. It does not initiate worker
sessions, request challenges, or exercise a promotion API.

## Concrete data and ordering

| Item | Selected inventory |
| --- | ---: |
| Retained probes | 8 four-integer vectors |
| Target vector calls | 8 |
| Inherited programs | 8 |
| Inherited-program vector calls | 64 |
| Candidate attempts | 9 |
| Candidate vector calls | 72 |
| Total vector calls | 144 |
| Input integer components | 576 |
| Output integer components | 576 |
| Candidate-admission operations | 9 |
| Complete declared work schedule | 153 operations |
| Complete JSON input/output/payload images | 315 |
| Complete JSON image bytes | 62,669 |

The complete reference work profile evaluates every probe for every program.
Its sequence consists of the target probes, the inherited programs, and
then each candidate admission followed by that candidate's eight probes.
Q/V's inherited descriptor array is in its checked key order. N's resource
journal visits those programs in historical promotion order, represented by
Q-array indices `[4, 0, 1, 3, 6, 7, 5, 2]`. Z retains and checks that
permutation explicitly; the two orders are not interchangeable.

The reference tariff counts `(9, 144, 576, 576)` and charges 4,032 declared
units. This is the existing selected tariff. It does not account for all
host resources or the cost of Z reconstruction and proof checking.

## Evaluator predicate

For the retained target family and probes, the evaluator computes:

1. Target outputs using the retained opening's family, variant, and integer
   parameters.
2. All inherited outputs and whether any inherited program of the target
   family agrees with every target output.
3. All candidate outputs and whether the candidate belongs to the target
   family and agrees on every probe.
4. Nontriviality: at least one target output differs from its input probe.

A candidate passes exactly when the target is nontrivial, no inherited
program passes, and the candidate has the target family and matches all
probe outputs. Otherwise the outcome is `reject` with the reason
`bounded_challenge_rejected`. A success is `candidate_passed` with an empty
reason list.

The fixture has eight rejections followed by one success. All eight
rejected candidates have a different family from the retained challenge.
Although their complete outputs are calculated and checked, these eight
observed rejections do not demonstrate rejection of a same-family,
incorrect candidate. The generic predicate and its explicit negative
controls test additional branches without claiming new live observations.

## Actual selected prefix

The inherited program inventory and current candidate sequence are finite.
The retained opening selects `tool_policy`, variant 1, with integer
parameters `a = -4` and `b = 16`. Under Q's existing semantics, its action on
`[x₀, x₁, x₂, x₃]` is `[x₀ + x₁ - 4, x₁ - x₂ + 16, 2x₂, x₃ - 20]`.
The certificate checks this action on the eight retained probes.

| Attempt | Q grammar index | Family | Variant | Matching probes | Derived verdict |
| --- | ---: | --- | ---: | ---: | --- |
| 1 | 21 | `adapter_policy` | 2 | 0/8 | `reject` |
| 2 | 28 | `adapter_policy` | 0 | 0/8 | `reject` |
| 3 | 1 | `adapter_policy` | 1 | 0/8 | `reject` |
| 4 | 29 | `adapter_policy` | 3 | 0/8 | `reject` |
| 5 | 20 | `retrieval_policy` | 3 | 0/8 | `reject` |
| 6 | 5 | `memory_policy` | 0 | 0/8 | `reject` |
| 7 | 22 | `planner_policy` | 2 | 0/8 | `reject` |
| 8 | 7 | `memory_policy` | 2 | 0/8 | `reject` |
| 9 | 24 | `tool_policy` | 1 | 8/8 | `candidate_passed` |

These are retained historical observations reconstructed and checked by Z.
They are not fresh worker or challenge results. The prefix terminates at
`await_root_verification`; it does not promote the candidate.

## Formal and runtime responsibilities

The Lean certificate imports the actual positive Y certificate, which
retains the preceding Q through X chain. It checks the selected opening,
program inventory, choice prefix, all target/inherited/candidate outputs,
nontriviality and predecessor novelty, complete outcomes and reasons,
evaluation payloads, reference work images and operation-kind schedule,
and the resulting verdict prefix. Its terminal result is connected to the
already checked task meaning and Q accepted-step result. The selected JSON
inventory comprises 153 work inputs (51,906 bytes), 153 work outputs (2,816
bytes), and nine complete evaluation payloads (7,947 bytes).

The Python collector independently interprets the integer vector operations,
compares the complete reference work with the retained resource journal,
and binds the packet to the exact Y evidence and historical transcript.
Canonical work and response bytes are checked for the selected inputs.
Their SHA-256 strings are compared by the runtime. Z adds no new SHA-256
arithmetic certificates and does not claim that Lean computes the resource
journal or response hashes. Y's selected context-hash checks remain part of
the imported result.

The actual Lean gate compiles nine historical dependencies, Q through Y,
and both existing X/Y SHA-256 auxiliaries freshly in dependency order.
It checks the exact import resolution of each module, then the positive
certificate and every negative control: 19 named theorem audits and 15
negative cases. The full gate has 27 Lean compilations and 40 command
records, including the version check, environment capture, and 11 import
resolution commands. A negative case counts only when its sole diagnostic
rejects the simplified `False` goal at the final, source-derived tactic
location in `rejected_control`. The file path, line and column must match;
a failed precondition or false-decision witness cannot count as the intended
rejection. Recorded compiler environments
preserve the distinction between an absent variable and an empty value.
Each negative control first proves its decision-false witness, derives the
negation of its exact proposition, and rewrites that whole proposition to
`False` using `eq_false`. This explicit rewrite covers Boolean equalities
without relying on the simplifier's Boolean preprocessing. An earlier
application stopped because the family control reached `false = true`
instead of the required `False` diagnostic. That rejected run remains a
development record. The corrected tail preserves every control proposition,
precondition, and witness, and the checker still requires the sole exact
`False` rejection at its source-derived final tactic location.
Source bytes, executable identities, output artifacts, command arguments,
stdout/stderr hashes, theorem axioms, and the completed progress record are
checked together. Controlled Python test logs cannot establish Lean
acceptance. The pinned foundation import cache remains an explicit trust
assumption.

### Inherited W proof factoring

The Z renderer first regenerates the inherited Q–Y sources and checks the
unchanged X/Y source pins. It then factors only W's
`selected_freeze_preimage` proof. The original W module has SHA-256
`341f4a756c95cf8acd2b75080b391fabc02ace620f667ea18b344af5df0b9d98`.
Its existing definitions, captured data, theorem names, and theorem
statements are preserved. No preexisting repository source is edited.

The factored proof checks the 32 candidate encodings separately, composes
their complete ordered array, and joins it with the schema and view to
establish the original complete freeze-record bytes. Each composition
uses the original encoder's exact fuel and depth. Depth, length, sorted
unique object keys, string bounds, integer bounds, and the final byte bound
remain part of that encoder's conditions. The domain prefix, digest syntax,
and inventory counts are still required by the unchanged theorem statement.
The additional composition lemmas are checked by Lean's kernel; they do
not introduce axioms or a native-evaluation shortcut.

This change bounds the size of individual kernel computations after two
full application attempts were terminated during W compilation, whose
freeze proof used one monolithic reduction. The stopped compiler logs do
not identify a particular failing theorem. Those failed attempts remain
development records. The Z-local
transformation requires the exact original source, rejects an unexpected
or repeated transformation, and verifies that reversing it recovers the
original bytes exactly. The execution record includes both source hashes
and the transformation provenance. Saved-evidence reconstruction repeats
these checks. The factored W module still has to compile freshly in the
same complete Z application as the other ten prerequisite modules.

The new positive result flags are:

```
evaluator_outputs_from_opening_checked = true
producer_verdict_prefix_checked = true
```

These flags are emitted as completed gate results only after the real
pinned Lean run succeeds. A preparation-only report keeps them false.
Saved-evidence reconstruction regenerates the selected packet and proof
sources without invoking workers, challenges, or the compiler.

## Scope and retained assumptions

Z is a selected historical computation. It does not prove general
Python-to-Lean evaluator equivalence, arbitrary input/parser equivalence,
all future challenge behavior, or a new capability gain. The fixed
historical opening is already retained data; this increment establishes
neither fresh entropy nor secrecy, evaluator independence, temporal freeze
order, or physical input authenticity. Program and journal capture and
physical execution remain external. A source-bound compiler record is not
physical execution attestation.

The current context remains a single predecessor context. The selected
candidate is not promoted, and Z does not authorize objective-policy
succession or create the next operational context.

All 24 broader claim flags remain false, including root-transition
verification, full learned or autonomous step instantiation, complete
resource accounting, active promotion, live capability gain, full Phase 17
exit, Gate E, EGC-0, hosted CI, broader platform validation, and Phase 18
independent replay. Fresh workers and fresh live challenges remain zero.

## Application and evidence

The additive kit is applied to a separate clean checkout of the completed Y
head. It runs the new test inventory, the actual pinned Lean gate, and
saved-evidence reconstruction before creating an evidence commit and
fast-forwarding the existing development checkout. The optional `--push`
uses an ordinary push only after rechecking the exact remote baseline.
Any failure preserves the workspace and progress record.

Linux assistant application and native Windows operator application are
separate evidence records. Linux validation does not establish native
Windows success; agreement on selected local outputs does not close the
broader platform milestone. PR #68 remains draft and unmerged. Existing
proof sources and evidence are preserved.
