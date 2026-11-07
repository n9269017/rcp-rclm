# Phase 17O — bounded online sessions under a persistent budget

Status: development integration, not Phase 17 closure or an accepted successor.
The installation base is `6e487bf8000747123942255a9f21216d4c4c3b93`.
Existing A–N source, proof gates and historical results remain unchanged.

## The boundary advanced

Phase 17N charged a reconstructed, already sealed fixture. Phase 17O adds a fixed
online worker, a coordinator and an externally anchored persistent session budget.
Each worker creates its own new challenge after validating the objective freeze.
The unchanged present-only controller and actual Phase 16 grammar/ranking choose
candidates. Candidate success still means `await_root_verification`, not promotion.

Sessions evaluate the SAME historically authenticated predecessor. A session ordinal
is retained history, not a target promotion count. No model is installed or advanced.
The fixed two-session validation harness is not a two-turn termination rule in the
production controller. EGC-0 is neither selected nor evaluated.

## Grant before launch

One `CampaignAuthority` owns a fixed policy, campaign identity, predecessor-state
hash, logical active-package hash, verifier and installed-program inventory. The
logical active-package identity is the historical state's `active_package_hash`;
it is not silently substituted for the materialized tensor-package digest used by
other Phase 17 adapters.

Before launching a worker, the coordinator records and flushes (`os.fsync`) its
whole bounded-vector envelope. No worker callback occurs before this durable
reservation succeeds. Both every resource dimension and the scalar ceiling must
fit. A denied session launches no worker. Successful early stopping, rejection,
exceptions and interrupted work never refund any of the campaign reservation.

For `k` candidate credits and `m` installed programs, the envelope is:

- candidate attempts: `k`;
- vector calls: `8 * (1 + m + k)`;
- input values and reserved output values: four times the vector-call limit.

The inherited Phase 17N weights `(64, 16, 1, 1)` and tariffs are unchanged.
An attempt costs 64 declared work units; a vector call costs 24. These are abstract
charges, NOT measurements of CPU/GPU time, memory, energy, storage or money.

The worker's actual completed work is retained separately from the whole reserved
envelope. Unused capacity stays charged. Conservative precharging can stop a
campaign earlier than ideal packing; that is a declared safety/availability tradeoff,
not evidence that physical computation consumed every reserved unit.

## Evaluator and information boundary

`phase17_campaign_worker.py` is the only worker executable selected by the client.
The protocol accepts bounded canonical data, never executable candidates, arbitrary
paths, a replacement verifier, hidden seed, future route or successful horizon.
A reduced environment and separate process are used; they are NOT an OS sandbox.

A grant binds the objective freeze, history ordinal, predecessor, fixed policy and
previous campaign head. A grant is a hash-bound record, not a cryptographic
signature. The trusted coordinator is responsible for issuing it only after a
reservation. The exposed Python APIs and a worker invoked outside that coordinator
are not an access-control boundary against hostile same-user code.

The evaluator validates the opening request against the grant before its inherited
live entropy draw. Its output rules are unchanged, but work is deliberately eager:
eight target calls, every probe for every installed program, and every probe for
each considered candidate. No hidden-answer-dependent short circuit changes the
reported call count. Reference computation is bounded to the existing four-integer
DSL; it is not full-transformer inference or broad empirical intelligence.

Within a worker, each operation is charged before its fixed callback. The worker
meter is in memory; it is not falsely described as individually fsynced. If the
worker dies, the durable parent reservation still charges the ENTIRE envelope.
The accounting summary is withheld until the evaluator seals the challenge and
reveals its opening. Before that point the controller receives the inherited
public commitment and coarse rejection feedback only. No timing-side-channel
noninterference theorem is claimed.

## Completion and restart

A completed worker must exit normally. The parent independently recomputes its
sealed transcript, every metered vector result and hash, and the exact producer
choices using the unchanged controller/adapter. A passing receipt alone does not
complete the campaign record. The source exposes no promotion operation.

Every next session rechecks the retained completed-session evidence before reserving
more work. Reopening requires an externally retained expected campaign head, exact
policy and context. A pending grant cannot be rerun, skipped, sealed or treated as
unused; explicit abandonment retains its charge and safety-halts the authority.

The journal enforces a single local writer with advisory locking and detects stale
anchors, mutated records, substituted contexts, forged totals and omissions. It
rejects a new-authority creation over an existing file. HOWEVER a new pathname is
not global campaign-budget authority, and accepting a rolled-back external anchor
permits rollback. Parent directory integrity, honest retention of the external head,
filesystem behavior and trusted code execution remain assumptions. `fsync` requests
local persistence; no cross-file power-loss, distributed-consensus or authenticated
physical-execution theorem is claimed.

## Validation contract

`scripts/run_phase17_campaign_tests.py` requires all 70 new tests, no failures or
skips. Direct deterministic-entropy tests are openly labeled fixtures; no replay
entropy is a live wire argument. The tests include actual child-process exit after
reservation, actual worker death, fixed-grammar verdict equivalence, prior-history
omission and tampering, and two live workers across a close/reopen.

`scripts/run_phase17_campaign_gate.py --output <new external directory>` requires
a clean committed source descended from the exact base, and the unchanged N report
hash `169f05f56749401bc1a348243468493ecc8bbb543fbd8a1e78844f6cea42d4db`.
It launches TWO fresh sessions once, with two candidate credits each and one shared
policy `(4,176,704,704)` costing 4480. Any valid resource-exhausted or candidate-pass
outcome is retained; there is no seed search, retry or winner filtering. It closes
and reopens the authority between sessions, then requires denial before a third
worker launch. The gate separately checks zero-budget denial, simulated failed-grant
retention and simulated pending-grant abandonment. Actual process-crash coverage
belongs to the separate unit suite, not those simulated gate controls.

`--verify-only --output <retained gate directory>` rechecks the saved journal,
transcripts, controller checkpoints, accounting, metadata and controls. It launches
no original workers and draws no new challenge entropy. This scoped recomputation
is NOT the complete Phase 18 independent replay implementation.

`--preparation-only` deliberately records no accepted Git provenance and cannot
satisfy the installer. It exists to report assistant-side reconstructed-checkout
validation honestly. The operator installer never requests it.

There are ZERO new Lean theorem claims in this increment. The N tariff theorem
record is checked for exact identity, not rerun or relabeled as a proof about the
new Python coordinator. The new state machine, IO implementation and protocol
composition have executable validation, not a newly kernel-checked refinement.

## Unmeasured and unfinished

CPU time, accelerator time, memory, storage, energy, bootstrap/validation, journal
IO, Python overhead, IPC/process startup, transcript recomputation and formal
verification remain outside this tariff profile. They are unmeasured, not zero.

`scoped_online_budget_authority_integrated=true` concerns this fixed-parent bounded
worker path only. `campaign_budget_authority_integrated=false` remains the broader
promoted-lineage/full-pipeline obligation. Full resource accounting/containment,
physical execution attestation, full goal/information interpretation, the compatible
base/RCP/RCLM kernel and accepted learned/autonomous step, full recursive-productivity
retention, active promotion/rollback, evolving cross-turn objectives, Phase 17 exit,
Gate E closure, EGC-0, hosted CI and independent/platform closure remain unestablished.

## Local application safety

The kit requires the exact clean local AND remote development head and ordinary Git.
It uses a separate short-path checkout, literal NUL-delimited staging and canonical
blob checksums. It creates one source commit, runs the required new validation and
retained-evidence recomputation, then creates an evidence-only commit. Only then
may the original branch fast-forward and normally push. No force push, reset,
amendment, merge, release, DOI edit, tool installation or old campaign rerun occurs.
Failure preserves its workspace and `progress.json`; a push rejection after local
advancement preserves the validated local commits and records that distinction.
Keep PR #68 draft and unmerged.
