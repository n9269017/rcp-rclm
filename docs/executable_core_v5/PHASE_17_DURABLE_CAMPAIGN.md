# Phase 17AL — durable authorization of fixed live campaign work

## Baseline and precise obligation

This additive increment starts from completed AK Windows evidence commit
`961beaaeeb1fe4461aa27fbec0af08469bd5c2aa` on
`agent/rcp-rclm-v5-phase-17-controller`. AK's tested source is
`b9183285606921f70f6dec1a99b397f3d1b919a6`, source tree
`e03ff894cdaf5731836b3b1e07dab55778a29ecd`. The retained execution record is
`artifacts/development/phase17ak/op-b91832856069/gate/execution.json`, SHA-256
`200a218f58066f6ac8b63be8be96e659b09bb2f4dc2fcb941462bb92ac0c3781`.
PR #68 remains draft and unmerged.

AK owns the paired AI/AJ reference journals. The existing Phase 17O live
campaign uses a different reservation protocol and worker tariff. Its
`CampaignAuthority` journal was not owned by AK's durable transaction. AL closes
that specific execution-path gap with a new campaign root: the root itself owns
the actual 17O journal, authorization, launch consumption and completed session
evidence in atomic snapshots. It does not pass an AI reference lease into a live
worker or claim that a new campaign transition is an existing AJ transition.

AL's selected deployment is explicitly `local_reference_only`. It does not
establish an independently protected external authority, legitimate external
issuer, globally unique history, or complete campaign/host accounting. A separate
service process and restrictive file modes do not isolate hostile code sharing
the same OS principal. Those are still deployment obligations.

## Provisioned authority and source authorization

An administrator explicitly provisions a previously absent root. The provision
binds the authority identifier and nonce, exact historical Phase 16 predecessor,
campaign context, aggregate resource policy, objective-selection policy, fixed
worker/evaluator protocols, accounting profile, scope, and project source closure.
Opening requires an independently supplied provision digest. Missing roots and
existing roots presented for reprovisioning are refused.

The service computes the objective and its freeze from the existing present-only
objective policy, accepted session ordinal, and current public nonce. It fixes
the worker script and recomputes the source identity before consuming a launch.
Controller input cannot select an evaluator, executable, import path, grant,
policy, completion result or source closure. A valid-looking legacy worker grant
is insufficient to invoke this admitted service path.

The provision digest identifies an operator-selected configuration. Its local
creation does not authenticate an external issuer. The source closure pins the
project implementation; Python, its standard library, Lean, SQLite, filesystem,
OS and hardware remain separately identified or trusted dependencies. File hash
checks do not establish resistance to hostile source replacement between a check
and execution.

## Atomic reservation and one-use launch

Each controller mutation supplies the complete current cursor: provision digest,
epoch, serial, root head, journal digest and snapshot digest. Accepted request
nonces are permanently retained. A stale/substituted cursor or replayed nonce
rejects before launch. Administrative reopening is outside controller dispatch.

The root uses SQLite transactions containing the root audit event and its entire
campaign snapshot. The snapshot includes the exact 17O journal, pending permit,
launch state, consumed nonces, and completed session evidence. There is no second
independently authoritative campaign journal to reconcile after a split write.

The launch sequence is:

1. Derive the fixed objective, freeze and full bounded worker envelope.
2. Commit the complete reservation and exact authorization, then read it back.
3. Commit the once-only launch consumption for the current epoch, then read it back.
4. Start the unchanged fixed metered evaluator through the recorded launcher.
5. Recheck the sealed transcript, actual controller proposal order, objective,
   grant and declared work inventory; commit completion and its retained evidence.

The authority holds the inherited cooperative lifetime lock for its physical
root. Each opening commits a new epoch. Reopening preserves every prior charge
and pending grant, clears its former owner, and refuses automatic continuation,
reissue or refund. A process lost between launch consumption and process creation
can therefore consume a grant without doing the intended work. That conservative
loss is deliberate: missing acknowledgment is not evidence that work was absent.

Budget denial is an accepted durable transition that launches no worker and adds
no reservation. Protocol refusals and reads add no publication. Worker or
verification failures retain unresolved charged work; they cannot synthesize
successful completion. Ambiguous transaction failures poison the handle.

## Storage and deployment boundary

AL retains SQLite's DELETE rollback journal and strengthens synchronization to
`EXTRA`, checking the effective mode on opening. EXTRA additionally synchronizes
the containing directory after journal removal. SQLite documents that FULL in
rollback-journal mode does not necessarily provide durability across power loss;
EXTRA improves that contract. See the primary documentation:
[SQLite synchronization modes](https://www.sqlite.org/pragma.html#pragma_synchronous)
and [atomic commit assumptions](https://www.sqlite.org/atomiccommit.html).

This configuration and process-crash testing do not prove physical persistence,
correctness of SQLite/OS/filesystem implementation, or power-loss behavior of a
particular storage device. A complete trusted-root rollback or copied root can
repeat a previously admissible history. No local lock provides distributed
consensus or exclusion of copies on other hosts. The formal model retains that
counterexample.

The reference transport is an inherited stdio connection created by the trusted
launcher. It is not a remotely authenticated production service. AL adds no
public-key or hostile-client response authentication claim. The older standalone
worker remains runnable by a principal that can access it; protection must prevent
such execution from consuming resources attributed to an authorized campaign.

## Actual fresh work and original observations

The selected application captures three bounded cases against the fixed
historical predecessor:

| Case | Fresh completed workers | Retained condition |
| --- | ---: | --- |
| Two sessions across restart | 2 | Shared aggregate allowance and durable history across two epochs |
| Interrupted reservation | 0 | Full pending charge retained and old owner revoked on reopen |
| Aggregate denial | 1 | A second complete envelope is denied before worker creation |

Five authority process lifetimes and three fixed evaluator process lifetimes
are separately observed. Every worker uses newly generated hidden entropy from
the unchanged worker. The gate requires three distinct challenge commitments.
No hidden seed, successful stopping time, winning candidate or desired outcome
is supplied by the capture. Public case nonces supply present context only.

These are fresh bounded evaluations, not promotions or proof of live capability
gain. The accepted predecessor never changes. A worker may end in search/resource
exhaustion or request root verification; none of those outcomes authorizes promotion.

Original command, interpreter/source identities, input/output/error streams,
process identities, completed native waits, and root exports are retained.
Worker streams are checked against the actual sealed transcript and accounting
records. Service exchanges are checked against the retained root history. Native
records are launcher observations, not physical attestations. They are not
recreated by replay and are not replaced with historical process records.

## Lean scope and saved-evidence reconstruction

`lean/phase17_bridge/DurableCampaign.lean` specifies this distinct campaign state
machine. It binds immutable provision identities and exact current cursors,
derives the unchanged 17O envelope, commits reservation and launch consumption,
checks completion ownership, and revokes ownership on reopen. Generic proofs
establish one-use launch, nonrefunding completion/restart, exact declared work
bounds, and preservation of completed work plus pending allowance below permanent
reservations and the provisioned aggregate policy.

The generated certificate derives its state/event projections from the actual
retained root histories and replays every selected transition in Lean. Python
independently validates the full legacy campaign journal, objective/freeze,
transcript semantics, controller order, native streams, hashes and source closure
before proof generation. Lean checks the selected state/cost relationships and
identity joins. It does not newly verify SHA evaluation, SQLite pages, process
creation, physical work, or a general Python-to-Lean refinement.

AL freshly compiles its own module, verifies its import resolution, audits the
fixed theorem inventory, and requires each designated negative control's exact
intended final rejection. AK's unrelated reference proof modules retain their
historical attribution. Parser tests, generated text, or retained AK objects do
not count as new AL compilation.

Saved-evidence reconstruction starts no worker, service, live challenge or
compiler. It reopens the original source-bound packet, exports, native records,
generated sources, actual compiled objects and explicit completed-stage lineage.
The installer must pass this reconstruction before acceptance or publication.
An incomplete attempt remains retained and does not become a completed execution.

The two bounded result flags are:

```text
durable_campaign_reservation_checked
live_campaign_authorization_checked
```

They apply to the specified local reference service and selected actual sessions.
They do not establish independently protected production deployment.

## Accounting and remaining obligations

The unchanged 17O tariff counts candidate admissions, metered vector executions,
and their bounded operation inventory. Whole-envelope reservation is permanent
even when the worker uses less. This provides an explicit declared-work bound.

It excludes CPU/accelerator time, memory, storage, energy, bootstrap and validation,
journal I/O and synchronization, hashing, Python overhead, IPC/process startup,
source/authorization checks, transcript reconstruction, formal verification,
tests, deployment provisioning and historical/broader campaign activity. Unmeasured
categories are declared as exclusions, never represented by invented zero costs.

All 24 inherited broader claim flags remain false, including
`campaign_budget_authority_integrated` and `complete_resource_accounting`. The
former remains open for independently authorized actual campaign operation and
promoted lineage, beyond this fixed-predecessor reference integration.

The next obligation is to supply and assess a real deployment boundary: a
protected authority principal/host, independently retained provisioning identity,
authenticated transport, justified current durable history and exclusivity, and
complete declared campaign work accounting. Those facts cannot be discharged by
controller-provided booleans or a self-issued manifest. Then connect the authority
to the actual promotion-bearing campaign under the immutable root constitution.

Physical/root-transition certification, full learned/autonomous-step instantiation,
promotion, Phase 18 independent replay, full frontier and recursive-productivity
recertification, Gate E and Phase 17 exit remain open. The v5
Phase 17 → 18 → X → Y → Ω → Z roadmap is unchanged.
