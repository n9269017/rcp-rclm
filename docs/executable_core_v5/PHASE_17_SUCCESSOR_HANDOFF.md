# Phase 17P — parent-linked, consumed, inactive successor handoff

Development integration only. Required base: `11e866f7a843bccb95f4a8e3f86a10aa594ff677`.
Earlier A–O sources, immutable Lean roots, accepted historical proofs and reports
are unchanged. This increment introduces no new Lean theorem or accepted model
transition. No active-package pointer is written.

## Online evidence to physical staging

The production handoff capsule contains the externally anchored O campaign
journal, exact policy and context, selected completed grant, and ALL completed
session evidence. It does not accept just a candidate-pass receipt. The adapter
recomputes the O campaign, metered transcripts, current-view controller choices,
objective freeze and checkpoint. A pending/safety-halted campaign is refused.
The capsule is bounded canonical JSON; its bytes are retained as an immutable
snapshot, and its external digest is required. Hashes are integrity bindings,
not signatures or independent attestations of who executed the worker.

Historical logical active-package identity and physical materialized-package
identity are separate fields. The parent physical digest is independently
reconstructed from the pinned M9 bundle and historical state before consumption.
The parent, fixed verifier, campaign scope and execution mode are fixed for a
transition journal. A handoff from another parent/campaign/mode cannot enter it.

The candidate branch is conditional on `await_root_verification`. It materializes
a new INACTIVE prospective package from the exact sealed transcript, then freshly
reconstructs the typed package, task-meaning and producer-provenance subpackets
through `prepare_joint`. Both physical packages are reopened and measured. Old
success reports, candidate-supplied proof paths, caller callbacks, and arbitrary
acceptance booleans are not arguments of the staging entry point.

The no-candidate branch retains consumption and a no-candidate assessment without
creating a prospective candidate. Search exhaustion is not rewritten as success.
For the full-grammar development gate, exhaustion requires all 32 candidates;
smaller-credit resource exhaustion remains distinguishable in the generic path.

## Durable one-time consumption

`TransitionJournal` appends a domain-separated canonical hash chain. Every event
has its exact index and prior hash. It recomputes state on reopen against an
external expected head and exact binding. Rehashing malformed events cannot add
an acceptance event or permit a result without its consumed handoff.

The trusted staging entry audits all previous completed dossiers before starting
another. It writes and flushes a `consume` record and requests `os.fsync` BEFORE
candidate materialization. That event consumes the challenge commitment and input
snapshot identity. The same challenge cannot be submitted again under a different
snapshot identity in the same journal. The source and derived handoff bytes are
then retained before physical construction begins.

A failed materialization/evidence write leaves consumption retained and enters a
safety halt when that failure record can be persisted. If the journal itself
cannot persist, the handle is poisoned; the existing bytes and pending state
remain for explicit investigation. A process exit after consumption leaves a
pending transaction. Reopen neither retries it nor forgets it. Explicit abandonment
retains the challenge and safety-halts. Completed inactive staging does not refund
or mutate any O campaign reservation.

The only completed outcomes are `no_candidate` and
`blocked_missing_root_witnesses`. There is no promote, accepted, refund,
unconsume, or active rollback event. The low-level journal records trusted
metadata; it does not by itself verify source semantics. The public staging path
and retained-dossier audit perform that verification. Exposed Python internals
are not a hostile-same-user security boundary.

Advisory locks coordinate one local writer. `fsync` requests local persistence,
but directory metadata/cross-file power-loss atomicity and distributed consensus
are not proved. An honest externally retained head is required. Accepting a
rolled-back anchor permits rollback, and creating a new pathname is not authority
to reset global challenge consumption or campaign budgets. The scope is one
externally anchored fixed-parent journal, not a promoted multi-parent campaign.

## Positive fixture versus fresh execution

The mandatory gate launches ONE new O worker with the complete 32-candidate
allowance, once. Its hidden entropy remains evaluator-owned. It retains either
valid terminal (candidate pass or full search exhaustion) without retry, seed
search, or winner filtering. A new challenge does not imply a new live gain.

A SEPARATE staging journal exercises the positive package path using the pinned
historical K transcript:

`16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f`.

This original known-answer fixture is explicitly `retained_synthetic_fixture`.
It has no claimed live campaign head, grant, fresh worker, or session cost. Its
expected inactive candidate remains
`b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e`.
Fixture capsules cannot enter online-mode journals; unknown fixture transcripts
are refused. The common physical staging implementation is tested without
misrepresenting a historical answer as a fresh hidden-challenge improvement.

Both paths check duplicate submission after a close/reopen. The retained-input
verifier reconstructs source semantics and physical candidates in fresh scratch
space, comparing every dossier byte and completion hash. It launches no original
worker, samples no challenge entropy, and runs no Lean proof. This is scoped
reconstruction, not the complete Phase 18 independent replay system.

## Why the successful staging result remains blocked

The positive assessment explicitly states `root_acceptance_evaluated=false`.
The Python joint packet is not a complete Lean acceptance certificate. Remaining
witness classes include the compatible base/RCP/RCLM obligations, physical
observation refinement, full goal/information semantics, complete resource
measurement/enforcement, same-candidate root-checked capability and recursive
productivity, and a fully instantiated learned/autonomous accepted step.

No previous joint or protected-semantics proof is silently reassigned to a new
live transcript. This increment does not rerun older proof campaigns or substitute
unit-test success for missing root premises. Candidate realization is inactive;
active atomic promotion/rollback and promoted-lineage continuation remain open.

## Resource and validation scope

The O reservation and worker accounting are retained unchanged for the online
source. Fixture resource fields are null, not fabricated O charges. Materialization,
joint evidence reconstruction, bootstrap, parsing/hashing, IO, process startup,
CPU/GPU time, memory, storage, energy and formal verification are outside the
bounded-vector tariff. They are explicitly unmeasured, not zero.

The new runner requires 70 tests with no errors/failures/skips. Coverage includes
real process exit after consume, pending reopen, exact external anchors, no-refund
consumption, prior-history omission, journal tampering and rehash attacks, malformed
source capsules, a real zero-credit worker source, and the physical positive
fixture. Some narrow rejection/control tests use explicitly mocked filesystem or
reconstruction outcomes. They are not physical execution attestations.

The operator gate rejects preparation-only results and requires a clean exact-base
descendant source. It binds the original O execution record by its exact hash
`7c7d0d68ab78ae08069839e54453bb5a1fe376189a393e62062e6a9a2f4a0d62`.
That is prior evidence attribution, not a rerun or a new proof about P.

The installer creates a source commit, runs the new tests and gate, then performs
separate verifier-only reconstruction. It retains source-bound logs and evidence
in a distinct evidence commit and updates the canonical index checksums. Only
then may the exact original branch fast-forward and push normally. No reset,
force-push, amendment, main merge, release/DOI change, dependency install, or hosted
workflow request occurs. Failures preserve workspaces and progress. A push rejection
after local advancement preserves validated local commits.

Keep PR #68 draft and unmerged. Phase 17/Gate E/EGC-0 closure, full root acceptance,
complete resources, hosted CI and independent/platform closure remain false.
