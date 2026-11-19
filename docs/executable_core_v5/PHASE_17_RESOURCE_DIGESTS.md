# Phase 17AB: selected resource-event and work SHA-256 refinement

Phase 17AB continues the completed AA controller head
`a0093cb8c25ec2ceefb0e5ad53f4719e30cb330d`. AB is an increment within
Phase 17. Phase 17 exit, Gate E, and the later roadmap phases remain open.

## Obligation

AA checks the complete retained resource journal against its typed protocol
and connects its reservation/result pairs to Z's actual work inventory and
Q's charge list. Its event hashes and work digests are opaque identities in
those Lean predicates. Python computes their SHA-256 values. Z also carries
the raw-descriptor digest in each of its nine candidate-admission results
without proving that digest computation.

AB checks these selected computations with the unchanged SHA-256 mathematical
reference introduced in X. It connects the resulting hashes to the actual
imported AA events and work references and the actual Z candidate descriptors
and admission digests. A freshly supplied collection of matching literals is
not a substitute for those imports.

## Exact selected inventory

| Group | Complete inputs | Input bytes | Padded-block occurrences |
| --- | ---: | ---: | ---: |
| Resource-event hash inputs | 316 | 109,566 | 1,919 |
| Work input images | 153 | 51,906 | 881 |
| Work output images | 153 | 2,816 | 162 |
| Candidate raw descriptors | 9 | 2,698 | 46 |
| Total | 631 | 166,986 | 3,008 |

The complete chains contain 2,134 distinct incoming-state/block transitions.
Deduplication shares an equality for the same incoming state and complete
64-byte block; it does not omit repeated occurrences or shorten a chain.
The new arithmetic modules contain respectively 512, 512, 512, 512, and 86
transitions. The inherited X/Y arithmetic modules retain their original scope
and sources.

All four journals already checked by AA are included in the event group, in
the order success, failed, exhausted, interrupted: 308, 3, 2, and 3 events.
The selected work inventory contains nine candidate admissions and 144 vector
calls, with the complete input and output images for every operation. The
nine raw-descriptor hashes are the inner digest values used in the actual
candidate-admission outputs, not the domain-prefixed public program hashes
proved earlier in X.

No fresh worker session or live challenge is launched. These are the same
retained historical inputs, with their attribution preserved.

## Event input construction and binding

The event hash input consists of the exact ASCII domain
`RCPRCLM-PHASE17N-EVENT-V1`, its terminating zero byte, and the complete canonical
JSON encoding of the object with keys `body`, `index`, and `previous`.
The body's complete typed value comes from AA's `bodyValue`; the index and
previous digest come from that same imported event. The event's own `hash`
field and the journal line's LF terminator are excluded from this hash input,
as required by the existing resource-ledger implementation.

The selected encoder relation uses W's unchanged canonical encoding reference.
AA's complete event decoding and LF-framing results remain imported. AB binds
each complete event preimage to its imported typed event and proves that the
computed lowercase digest equals that event's recorded hash. These results
compose with AA's complete protocol replays, including its predecessor links,
reservation/result matching, final heads, and failed/interrupted no-refund
behavior.

Work hashes use the complete imported work input/output byte images without
an added domain prefix. Candidate-admission descriptor hashes use the complete
canonical descriptor encodings of the actual imported Z candidates. Their
computed digests equal the digest strings already consumed by Z's admission
results. The selected composition retains AA's work/result binding and the
inherited finite accepted-step result; it does not instantiate a full physical
root transition.

## SHA-256 proof construction

The reference remains `Phase17Sha256` from `ProducerSha256.lean`: complete
padding, the 64-bit big-endian bit length, ordered 64-byte blocks, initial
state, message schedule, 64 rounds per block, feed-forward, and lowercase
digest encoding. No new SHA equations or native-evaluation shortcut are
introduced. The X Python input bound is unchanged; every selected AB input
fits it.

Each supplied compression witness is untrusted. Lean checks the schedule and
round equations and derives the compression equality. Ordered compression
chains consume every padded block and compose those equalities through the
final state. Complete input/preimage bindings and digest equalities connect
the arithmetic to the selected AA/Z declarations.

Five bounded auxiliary modules keep the new arithmetic compilation units
separate. The gate freshly compiles eleven Q-through-AA dependencies, both
existing X/Y arithmetic auxiliaries, and all five AB arithmetic modules in
dependency order: eighteen modules in total. Eighteen same-run import
resolution checks bind the client imports to those exact compiled outputs.
The final certificate imports the actual AA certificate and all five AB
arithmetic modules. Earlier success reports cannot replace those compilations.

The gate then checks the positive certificate and all nineteen designated
negative controls. Eighteen named theorem audits allow only `propext`,
`Classical.choice`, and `Quot.sound`. The full inventory comprises 38 Lean
sources/checks and 58 formal command records, including version and isolated
environment capture. Z's reversible W proof factoring remains applied exactly
once, with its original source and theorem statements recoverable.

## Negative controls and evidence validation

The controls cover changed event index, previous digest, body, inclusion of
the event's own hash, missing domain terminator, wrong domain, wrong event
digest, changed work input/output, wrong work digest, changed admission
descriptor/digest, omitted event, wrong block order, wrong padding length,
wrong schedule word, wrong round state, wrong feed-forward, and wrong incoming
state.

Each control proves its explicit false-decision witness and checks its setup
before the final rejected proposition. The saved result must contain exactly
one intended final `False` diagnostic at the source-derived file, line, and
column, with return code 1 and empty stderr. Missing imports, failed setup
lemmas, unrelated compiler errors, timeouts, and resource kills do not count
as successful controls.

The Python collector independently reconstructs the complete selected inputs,
uses X's integer SHA implementation to produce/check all traces, and compares
the final digests with the captured values and the library SHA implementation.
The packet and returned views are immutable or detached. Source bindings cover
the runtime, original task definitions, formal templates, renderers, checkers,
tests, and fixed CLI entry points. Root sources, dependency pins, binaries,
the effective compiler environment, same-run artifacts, and complete logs are
bound by the actual gate.

The packet's `scope` section declares the intended selected certificate. Actual
acceptance is recorded by the execution and formal result fields. Only a
complete pinned-Lean gate sets those result fields to:

```
resource_event_hashes_checked = true
resource_work_digests_checked = true
```

Preparation-only mode keeps both result flags false. Controlled checker and
installer tests are separate from Lean acceptance. Saved-evidence verification
reconstructs the packet/proof sources and validates the retained records
without executing a compiler, worker, or live challenge.

## Remaining boundaries

AB's new inventory excludes the four whole-journal file checksums and the
producer-response hashes. Those computations remain Python/provenance
boundaries. The complete raw journal bytes and LF framing remain covered by
AA's imported selected decoding/protocol certificate; a new whole-file hash
theorem is not claimed.

Computing a selected hash does not authenticate the physical capture or the
external expected head and does not prove cryptographic collision resistance.
Actual work execution, persistence, advisory locking, filesystem/power-loss
behavior, contextual digest authenticity, challenge freshness/secrecy,
evaluator independence, objective-policy succession, and the pinned foundation
import cache retain their external assumptions. General Python/Lean resource
ledger, SHA-library, JSON-parser, evaluator, planner, and full-transformer
equivalence are not established.

The inherited cost of 4,032 is a declared reference-work tariff. AB's
reconstruction and proof checking, bootstrap, physical staging, hashing,
canonical parsing, journal I/O, Python overhead, CPU/GPU time, memory, storage,
energy, promotion, and rollback remain outside complete resource accounting.
Unmeasured work is not treated as zero.

All 24 broader claim flags remain false. Full learned/autonomous/root-step
instantiation, physical observation refinement, full goal/information
interpretation, full-frontier/recursive-productivity recertification, campaign
budget integration, OS containment, active promotion, live capability gain,
hosted CI, broader platform validation, Phase 18 independent replay, Phase 17
exit, Gate E closure, and EGC-0 remain open.

## Application and attribution

The additive kit applies to a separate clean checkout of the exact completed
AA head. It verifies the canonical source manifest, runs the new tests and the
mandatory pinned Lean gate, reconstructs the saved evidence, and only then
creates an evidence commit and advances the original checkout. An optional
ordinary push requires the remote baseline to remain unchanged. Failures
preserve their workspace, original outcomes, logs, and progress record.

Assistant Linux and native Windows applications are separately attributed.
Linux validation alone does not establish a native Windows pass, and selected
agreement does not close broader platform validation. PR #68 stays draft and
unmerged. Existing source, releases, evidence, and recorded failures remain
unchanged.
