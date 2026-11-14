# Phase 17AA: resource-journal protocol and selected work binding

Phase 17AA continues the completed Phase 17Z controller head
`d4d9cde8da7d2dc48c15a9dfc70f6c14d72bee55`. The suffix AA denotes an increment
within Phase 17. It does not start any of the roadmap's later phases.

## Obligation

N supplies arithmetic over a list of charged operation kinds. Q incorporates
that list in its finite observation kernel. Z checks the selected evaluator's
153 ordered work items and their complete input/output images. Before AA, the
connection from the resource journal's actual reservation/result records to
that charged list is checked only by the Python replay implementation.

AA adds a typed reference state machine and checks the complete retained event
images against it. The machine recomputes cumulative usage and enforces the
header, reservation, result, exhaustion, and terminal-state rules. Its selected
reservation sequence is connected to the actual imported Z work inventory and
the resource list used by Q. Supplied cumulative counters are comparison
targets, not trusted inputs to the calculation.

## Retained inventory

| Journal | Events | Complete bytes | Role |
| --- | ---: | ---: | --- |
| `resource-journal.jsonl` | 308 | 120,790 | Header, 153 reservation/result pairs, seal |
| `failed-work.jsonl` | 3 | 1,541 | Reserved operation fails; charge remains |
| `exhausted-work.jsonl` | 2 | 1,186 | Zero budget denies the operation before admission |
| `interrupted-work.jsonl` | 3 | 1,533 | Pending operation is abandoned; charge remains |
| Total | 316 | 125,050 | Four separately attributed retained journals |

These are the exact N records already retained in the completed repository.
They are not new executions, failures, challenges, or live observations. AA
does not relabel their elapsed-time fields as measurements of its own work.
The total includes 316 single LF terminators: 124,734 JSON bytes plus 316
framing bytes. The certificate binds the complete raw journals to those
ordered event images and terminators, rather than checking a list of
independently selected records.

The main journal's expected head is
`13eaa10744643e58a5cf44c433a8d0417f8183721199fb2fec2578effa47aa7a`.
Its SHA-256 is
`aa20e37afa57295bb094c5ad7cd093cfb922f189dc0f0d1ef060a6d696f794b5`.
The runtime fixes the complete policy, binding, journal bytes, and expected
heads from the retained evidence. A caller cannot select a different policy
or candidate merely by rehashing changed records.

## Protocol and arithmetic

The reference state records the event index and predecessor identity, current
status, pending reservation, admitted operation identities, charged kinds,
and cumulative resource counters. Exact structured event fields are checked
against their complete captured JSON images using the existing selected JSON
decoding definitions. An event's retained hash is an identity in this formal
model; computing that hash remains a separate boundary.

The generated certificate stores each complete byte image as its length and
a packed natural-number literal. A pure structural recursion reconstructs the
ordered bytes using remainder and division by 256; the exact reconstructed
list is passed to the same JSON decoder. This representation stores the bytes
compactly without omitting bytes or trusting a decoded event. These encoding
literals are not resource counters: all protocol
counter, index, and elapsed-time fields retain their declared 63-bit bounds.

A reservation requires an open state with no pending work, a fresh operation
identity, the fixed tariff, and sufficient capacity in all four dimensions
and the scalar budget. It adds its charge before entering the pending state.
A result must identify that pending reservation. Successful completion opens
the session for another operation; failure or interruption enters a safety
halt. Neither result removes the reservation charge. A denied reservation
records exhaustion without admitting or charging the denied operation. Sealing
or externally stopping requires an open session with no pending work, and
terminal sessions cannot admit another event.

The arithmetic retains Python's declared nonnegative 63-bit bounds. The four
dimensions and weights remain N's fixed profile: candidate admissions, vector
calls, input integer values, and reserved output integer values, weighted by
`(64,16,1,1)`. This is a declared reference-work tariff.

The selected successful replay ends sealed with no pending work, 153 distinct
operation identities, counters `(9,144,576,576)`, and cost 4,032. Its complete
grammar policy has limits `(32,328,1312,1312)` and scalar limit 9,920. The
failed and interrupted retained journals each keep one vector charge, costing
24, at safety halt. The zero-budget journal admits no work and retains zero
spent counters at resource exhaustion.

## Binding to Z and Q

The new certificate imports the actual Z positive declarations. Z in turn
retains the Q-through-Y chain. AA does not replace the selected programs,
opening, evaluation results, task meaning, or finite accepted-step theorem
with a newly supplied success flag.

The main journal's reservation identities and operation kinds must match the
complete ordered Z work sequence. The corresponding result records must refer
to the right reservation. Complete retained input/output digest fields are
checked as identities, and the Python reconstruction computes those digests
from Z's complete work bytes. This does not assert a new Lean proof of those
SHA-256 computations. The inherited selected SHA proofs from X and Y retain
their original scope.

The header's predecessor, candidate, transcript, fixed verifier, and resource
policy are bound to the same selected transaction. The projected charge list
must equal the actual Q list, preserving the finite kernel's declared resource
interpretation. This establishes a protocol link for the finite observation
model; it does not authorize the physical transition or promotion.

## Runtime reconstruction and formal gate

The Python collector reconstructs the completed Z packet from its pinned
inputs, independently interprets every retained journal event, and compares
its result with the existing production replay function. All complete bytes,
derived states, fixed external anchors, work bindings, and source identities
are retained in a canonical immutable packet. Access returns detached values.
The new tests include malformed records, rehashed semantic changes, omitted
work, substituted bindings, stale reservations, budget violations, and attempts
to resume terminal sessions.

The real gate freshly compiles ten Q-through-Z dependencies and both existing
X/Y SHA auxiliaries in dependency order, checks all twelve same-run import
resolutions, and then checks the AA positive certificate and every specified
negative case. Z's reversible W proof factoring is retained exactly once.
The AA replay certificate composes separately checked event decodings and
state transitions. Its full replay is built from those proved transitions;
the derived state snapshots do not become unproved assumptions.
The immutable root sources, toolchain identities, environment, source bytes,
compiled artifacts, exact audit sequence, and command logs remain bound to
the same run. Prior execution reports do not substitute for fresh compilation
of those imported declarations.

Each negative case must first establish its intended false decision witness
and preconditions. Its only diagnostic must reject the final simplified
`False` goal at the source-derived file, line, and column. Missing imports,
timeouts, resource kills, failed setup lemmas, and other compiler diagnostics
do not count as successful controls. Generated sources prohibit proof
placeholders, arbitrary axioms, and native-evaluation shortcuts. The allowed
foundational axiom set remains `propext`, `Classical.choice`, and `Quot.sound`.

The result flags are emitted as true only after the complete actual Lean gate:

```
resource_journal_protocol_checked = true
resource_journal_work_binding_checked = true
```

A preparation-only result keeps both false. Saved-evidence reconstruction
regenerates the packet and proof sources and validates the saved records
without running compilers, workers, or live challenges. Controlled checker and
installer test logs are not Lean acceptance evidence.

## Remaining boundaries

The formal model checks structural hash links, not SHA-256 arithmetic for
the journal events or work digests. The runtime checks those computations.
Cryptographic collision resistance, external expected-head authenticity,
physical byte capture, actual operation execution, persistence, advisory
locking, and filesystem or power-loss behavior remain external assumptions.
This is not a general proof that every Python journal execution refines Lean.

The N profile excludes bootstrap, materialization, parsing, hashing, journal
IO, Python overhead, AA reconstruction, and proof checking. CPU/GPU time,
memory, storage, energy, and the omitted pipeline work remain unmeasured,
not zero. AA does not integrate O's campaign authority into promoted lineage
or provide OS containment.

All 24 broader claim flags remain false. Full root-transition verification,
full learned/autonomous-step instantiation, physical observation refinement,
full goal/information interpretation, complete resource accounting, recursive
productivity recertification, active atomic promotion/rollback, successor
context, multi-turn continuation, hosted CI, broader platform validation,
Phase 18 replay, Phase 17 exit, Gate E closure, and EGC-0 remain open. Challenge
freshness/secrecy, evaluator independence, objective-policy succession, and
the pinned foundation import cache retain their stated boundaries. Fresh
worker sessions and live challenges for this increment are zero.

## Application

The additive kit applies to a separate clean checkout of the exact completed
Z head. It checks the source manifest, runs the new tests and mandatory pinned
Lean gate, reconstructs the saved evidence, and only then creates its evidence
commit and fast-forwards the original checkout. An optional ordinary push
requires the remote baseline to remain unchanged. Failure preserves the
workspace, original outcomes, logs, and progress record.

Assistant Linux application and native Windows application are separately
attributed. Linux validation alone does not establish a native Windows pass,
and selected agreement does not close broader platform validation. PR #68
remains draft and unmerged. Existing sources and evidence are preserved.
