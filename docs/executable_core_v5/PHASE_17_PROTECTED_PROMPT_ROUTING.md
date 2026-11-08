# Phase 17S — original protected prompts to captured sparse execution

This increment starts from the completed Phase 17R evidence head
`4c58fe4d47e3d8fc8fb2e3aba5c759718fe5b8ae`. It preserves R's code and retained
Windows evidence. Keep PR #68 draft and unmerged. Phase 17 overall remains open.

## The premise addressed

R checked the complete captured sparse tensor image, its numerical
interpretation, and eleven protected continuations starting from effective
markers. The effective markers were still observations produced by Python's
package routing. S makes the intervening route computation explicit in Lean,
starting with the original protected prompt literals and captured package data.

The resulting selected theorem composes routing with R's byte-derived decoder
and Q's concrete finite-model acceptance result. It does not replace physical
capture or Python execution with a formal attestation, and it does not extend
the selected sparse profile to arbitrary transformer inference.

## Captured inputs and their bindings

The input contains complete captured values of six canonical JSON objects:
memory, retrieval, generator, planner, optimizer, and resource measurement. It
also contains the package and adapter manifests and the complete selected
adapter tensor image. Original file bytes, sizes and SHA-256 digests are retained
and checked against R's same-candidate typed package inventory. JSON projection
and adapter selection are recomputed from those bytes; a supplied hit flag or
effective marker cannot substitute for a route input.

The adapter profile selects `adapter.layers.00.attn_output.B` and its complete
5,120-byte image. The selected architecture and manifest checks are part of the
admitted profile. This is not a universal proof of adapter selection for arbitrary
architectures. The Lean model reads the captured manifest record and its hash;
it does not receive a caller-chosen successful adapter observation.

All eleven original task prompts and their challenge bindings are reopened from
the existing source definitions and pinned historical answer archive. Prompt
bytes, terminal marker, fixed target tokens, task identity, challenge commitment,
and challenge slot must agree with the protected contract. Targets retain their
original attribution; the selected historical fixture is not a fresh hidden
challenge or a new capability result.

Predecessor and candidate captures are performed independently. Each is compared
with the unchanged production route decoder. Both must produce the markers
already bound by R's protected packet. The entire R packet must match its pinned
published bytes, and the Q/R proof inputs are regenerated from that packet.

## Reference routing semantics

The Lean reference represents complete JSON values with explicit types and
ordered arrays. The accepted numeric profile uses bounded integers and excludes
Python's Boolean-as-integer coercion. JSON parsing and the relationship between
captured values and actual files remain explicit external obligations.

For a hidden task, the interpreter evaluates all four possible route families:

| Family | Reference condition |
| --- | --- |
| Memory/retrieval | Exactly one matching commitment in each table, with the task slot and common route marker |
| Generator/planner | Exactly one matching commitment in each table, with the task slot and common route marker |
| Adapter/optimizer | A unique optimizer entry, selected adapter record/hash, bounded byte offset, and the matching signed little-endian four-word tuple |
| Model weights | A unique resource route, matching slot and tensor-manifest identity, and the raw-score greedy selection computed from R's captured tensor |

Exactly one family must hit. Zero or multiple family hits fail the route. A
family entry is selected only when exactly one entry has the matching challenge
commitment; duplicate entries do not silently choose a winner.

The selected hidden route starts the legacy chain at marker 87. The legacy
interpreter applies its three tests in order: adapter 87 to 86, planner 86 to 85,
and retrieval 85 to 84. The planner and retrieval searches preserve the
production implementation's **first matching entry** rule. This is distinct
from the unique-entry rule for hidden challenge routes. The chain is not a loop
to a fixed point. On a required step's failure it restores the chain's starting
marker and records failure.

Adapter words use R's signed little-endian byte interpretation. Hidden adapter
checks use the tuple `(slot, 87, recorded_prefix, 1)` at the recorded offset.
The prefix is an opaque field checked against the captured bytes; S does not
invent a cryptographic prefix derivation that the production code does not
perform. Challenge commitment authenticity and digest collision resistance
remain outside the formal theorem.

The original prompt must be nonempty and contain only bytes. Hidden tasks must
agree with their challenge task identity and terminal slot. Lean also checks the
captured commitment's 64-character lowercase hexadecimal syntax and derives the
slot as `180 + first_eight_hex_digits mod 64`; digest authenticity remains
external. The route result
determines the replacement terminal byte. R then supplies the independently
checked tensor interpretation, raw-score greedy selection, tie breaking,
sixteen-selection bound, and EOS behavior for the resulting continuation.

## Formal composition and remaining boundaries

The generic reference lemmas establish unique-route and unique-family
consequences, failure behavior, and the composition of routing with R's goal
binding. The selected certificate checks both captured packages, the original
protected tasks, route families and marker sequence, and the resulting protected
goal/information bindings. Its final acceptance statement retains Q's actual
selected finite-model accepted step and R's captured-image witnesses.

The two new scoped flags are `protected_prompt_routing_checked` and
`protected_task_execution_bound`. They become true only after the actual pinned
Lean gate passes. The second flag denotes execution in the declared Lean
reference semantics, not attestation of Python or physical model execution.

All 24 broader claim flags remain false. S does not close physical byte capture,
canonical JSON parser correctness, SHA-256 authenticity, Python execution,
full-transformer equivalence, general goal/information interpretation, full
frontier or recursive-productivity recertification, authenticated autonomous
succession, complete resource accounting, promoted-lineage authority, active
atomic promotion/rollback, or the remaining platform/campaign obligations.
Phase 17, Gate E, EGC-0 and Phase 18 independent replay remain open.

## Fresh checking and evidence

Each S gate uses the existing pinned Lean 4.31.0 workspace. It creates a new
external import directory and freshly compiles **two** source-bound dependencies:
Q's dependency followed by R's positive certificate with only its exact audit
print commands removed. It separately checks the resolution of R's Q import
and S's R import to those exact same-run artifacts. Each dependency's source,
emitted artifact, command streams, and resolved path are retained and checked.
Prior success reports or prior compiled Q/R artifacts cannot replace these
compilations. The immutable foundation import-cache assumption remains explicit.

The positive S source must emit the exact named audit sequence with only
`propext`, `Classical.choice`, and `Quot.sound` as permitted dependencies. The
source guard rejects placeholder proofs, arbitrary axioms, unsafe/partial
definitions, and native-decision shortcuts. Negative controls receive credit
only for explicit false-proposition rejection, never for unrelated compiler
errors, missing imports, timeouts, or interruption. The renderer is the
authoritative theorem/control inventory.

Command progress is written after each formal command. The final result must
match the retained progress record. Runtime tests use controlled malformed
packets and compiler logs to exercise rejection paths; such test fixtures are
not themselves formal evidence. Installer transaction tests are separately
attributed from runtime tests and actual Lean execution.

The entry points are:

```text
python scripts/run_phase17_prompt_routing_tests.py
python scripts/run_phase17_prompt_routing_gate.py --test-fixture --require-lean --lean-workspace <prepared-formal-root> --output <new-external-output>
python scripts/run_phase17_prompt_routing_gate.py --verify-only --output <same-output>
```

The verifier-only command reconstructs the captured inputs, packet, and generated
sources at the original tested source commit without workers, new challenges,
or compiler runs. It is not Phase 18 independent replay. The application helper
starts from exact clean R, creates a short separate checkout, commits source
before testing, runs the tests and actual gate, reconstructs retained evidence,
then creates a separate evidence commit. Only successful validation permits a
normal fast-forward of the caller checkout and an optional ordinary branch push.

S introduces no new worker sessions, live challenges, online candidate, or live
capability gain. The inherited frontier 21 to 22 is not a new S result. Byte
capture, routing, preparation, proof checking, CPU/accelerator time, memory,
storage and energy are not charged by the historical N reference tariff; their
complete accounting remains unmeasured. Successful Linux and Windows executions
must retain separate source commits, environments, logs and timings.
