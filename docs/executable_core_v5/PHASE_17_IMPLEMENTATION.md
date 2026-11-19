# Phase 17 implementation — controller, historical bootstrap, and initial objective

## Resumption basis

Development resumes publicly from `358ff0efdc6bba6bdd1c8c30dc12c3695e3cf53f`.
Phase 15/16 source is public through `v4.6-phase15-phase16-full-source`.
The archived `v5-trajectory` release and its separate technical-note DOI remain
historical roadmap objects; their tag, assets, and checksum records are unchanged.

The owner's current instruction supersedes the historical private-implementation
publication policy. New implementation, tests, schemas, and phase workflows
belong in this public repository. This does not permit credentials in source,
nor disclose future held-out answers to a running proposer before freeze.

The Phase 17 target retains the fixed Phase 16 grammar, fixed verifier,
diagonal/classical semantics, and externally serialized atomic transaction.
It removes the predeclared successful trajectory from the controller. Full
executable Gate E closure remains Phase 18, not this development slice.

## Implemented here

- Strict present-only view and immutable search/checkpoint records.
- Phase 16 grammar/ranking adapter with fixed-identity and family checks.
- Four rejection-conditioned ranked attempts, then complete fair enumeration.
- Separate resource exhaustion, bounded-search exhaustion, external stop,
  fail-closed halt, and waiting for root verification.
- Decision/receipt binding and canonical resumable prefix validation.
- Explicit absence of candidate-authorized promotion or a successful-phase halt.
- A retained Phase 16 terminal-state serialization fixture, not a selected EGC
  baseline and not an independently reverified bootstrap certificate.

`candidate_passed` is an observation to be independently checked later. It is
not a trusted success bit. The controller cannot write an active package or
close Phase 17. A bounded exhaustion record establishes enumeration coverage
under retained observations; independent evaluation truth remains a separate
obligation.

## Validation boundaries and local-first continuation

The original selected-module result is retained byte-for-byte in
`artifacts/development/phase17/initial-selected-module-validation.json`.
It records 26 controller tests and seven adapter tests with a namespace loader.
It was not a complete-checkout replay and is not relabeled as one.

The owner subsequently ran the normal full-checkout entry point in Windows
PowerShell: **33 tests passed in 5.720 seconds**. They then generated and verified
1,907 canonical staged-blob checksum entries and pushed manifest-only commit
`197f4bc022a68123c20cfd5f146149249663f1db`. The test source was its parent
`e7a87487329aa38884a3798a339b7fb50c01bcb2`; only the manifest changed afterward.
The annotated transcript and structured operator-reported record are retained
under `artifacts/development/phase17/`. No original raw terminal file, precise
execution timestamp, Python version, or Windows build was supplied; no such
values are invented. This result does not require repetition simply because
hosted execution is unavailable.

The owner now reports GitHub's explicit message:

> The job was not started because your account is locked due to a billing issue.

The previously inspected hosted jobs executed zero steps. This is an execution
block, not a test failure or a successful CI check. No billing settings or
payments are changed by the project. Repeated hosted retries are not required
for local-first development, and old red/pending checks are not marked passed.

`PHASE_17_LOCAL_VALIDATION.json` is now a status index separating historical
selected-module evidence, owner-reported full-checkout Windows evidence, new
evidence-tool unit tests, blocked hosted execution, and outstanding obligations.
See `LOCAL_FIRST_VALIDATION.md` for the fixed local capture/verification profile.

The new recorder preserves command arguments, source commit/tree, environment,
stdout/stderr, exit codes, timing, and checksum anchors. It cannot authorize a
merge, promote a candidate, certify a Lean theorem, or close a phase. Its unit
tests passed in the assistant's Linux environment against synthetic temporary
repositories; they are not additional Phase 17 foundation/campaign results.

The root manifest must cover the current staged tree before merge. The owner's
1,907-entry result remains valid for its historical commit, not automatically
for later files. Run `python scripts/phase17_refresh_checksums.py` to verify the
current index; `--write` refreshes only the manifest. Keep PR #68 in draft until
its explicit review and validation obligations are met. The retained eight-
promotion Phase 16 terminal state is still only a serialization fixture.

## Phase 17B historical bootstrap and initial objective

The owner completed the next evidence-manifest refresh at
`0c72b00560f4164a3b044302b9b93f7d08ac170f`: five retained records checked,
1,916 canonical root entries verified, and a manifest-only update pushed.
No foundation tests were rerun by that bookkeeping step.

`phase17/bootstrap.py` now reopens three exact historical archives, binds the
accepted Phase 16 closure to its capture, inventories all 17 terminal states
(16 ladder campaigns plus the separate stretch campaign), reconstructs the
selected eight-transition state/package/frontier lineage, and reopens the
inherited M9 planner tensor. The selected state is fixed by the documented
minimum-rung/UTF-8-seed/stream rule, never by an EGC score. This is historical
hash-anchored evidence ingestion, not fresh Lean or full-tensor verification.
The old Phase 16 serialization fixture is not an archive-ingestion substitute.

`phase17/objectives.py` implements a declared, deterministic, package-conditioned
initial objective heuristic using the 84 actual nonzero inherited tensor values.
It selects among the eight existing families without supplying a winner program
or altering the mutation grammar. It exposes no future horizon, target promotion
count, future task, evaluator seed, or EGC-score argument. An independently
recomputed objective freeze binds this decision to the predecessor and current
nonce. No hidden challenge has yet been generated or bound by this module.

This is NOT evidence that the objective policy learned to improve, that the
whole controller is horizon independent, or that a hostile host cannot influence
nonce selection. Cross-turn policy evolution and evaluator process isolation
remain open. `challenge_bound=false` and `promotion_authorized=false` are explicit.

Measured assistant results: 34 new unit tests, 26 controller regressions, and
10 real-archive integration tests passed on Linux/Python 3.13.5. The seven existing
Phase 16 adapter tests and the complete 67-test checkout suite were not rerun in
this reconstructed local workspace. The normal Phase 16 constructor round-trip
is exercised by the complete-checkout bootstrap entry point, not claimed by the
selected-module results. See `PHASE_17_BOOTSTRAP.md` and the phase17b evidence.

## Next implementation obligations

1. Integrate the reopened historical predecessor with the actual realization and
   pinned-root verification service. Historical hash/lineage validation does not
   replace fresh certificate checking or re-evaluation of the protected frontier.
2. Connect the initial objective freeze to a separate post-freeze challenge
   service. Keep evaluator secrets/answers out of proposer state and implement
   evolving, parent-bound cross-turn objectives rather than reusing the initial
   predecessor policy as if it already supported promoted successors.
3. Connect the single-candidate controller to actual realization, independent
   evaluation, full-frontier recertification, root checking, and atomic
   promotion/rollback. A generator must never approve its own output.
4. Add the cross-turn continuation driver with no target promotion count or
   predetermined successful stopping condition. Extend resource accounting to
   all relevant operations, not just candidate evaluation count.
5. Persist a parent-linked durable ledger with restart validation, stale-parent
   rejection, evaluator substitution attacks, and failure-safe transactions.
6. Run finite multi-seed/multi-envelope validation including natural exhaustion
   and externally stopped valid prefixes. A finite test is not empirical
   infinite execution, and selected-prefix tests are not a general Lean theorem.

Phase 18 independent worker-free closure, noncommuting Phase X, verifier
succession Y, improvement-space expansion Omega, asynchronous Z, and EGC-0 are
not implemented by this initial slice.

## ZIP-name portability repair and retained local validation

The failed Windows/Python 3.13.3 run at `89b8296c4973f7fa425518e4d407356766f7b6c9` remains retained as a failed run. ZIP fixture construction normalized a backslash before ingestion; the loader also used the normalized name. The correction preserves literal fixture header names and rejects invalid original names before normalization. No assertion is removed or skipped.

At `52c3b8f33293fc1a52a88c7ae73cc81d35e149c7`, the operator ran 70 foundation tests and 10 archive integration tests with zero failures/skips, plus the normal Phase 16 constructor check. Evidence: `artifacts/development/phase17b/operator-52c3b8f33293`. This is local Windows evidence, not hosted CI, fresh Lean verification, or phase closure.

## Phase 17C — bounded post-freeze evaluation

See [PHASE_17_CHALLENGE_TRANSACTION.md](PHASE_17_CHALLENGE_TRANSACTION.md). This adds one evaluator-separated bounded DSL turn, not full-model evaluation, a hostile-code sandbox, promotion, or phase closure. The Phase 17B Windows capture and bootstrap passed at `52c3b8f33293`; older `not_run` summary labels have been reconciled without changing historical evidence.

## Phase 17C local validation after memory-profile change

Tested implementation: `2d2695674a417cea04947400fa617ac6b34b9d5b`. Evidence: `artifacts/development/phase17c/operator-2d2695674a41-post-xmp/operator-validation.json`. This is a multi-run Windows record: the earlier 110 foundation and 10 archive passes are retained without relabeling them as post-change runs; the original failed process suite and intervening diagnostics remain preserved. After the operator changed XMP Profile 1 to Auto, firmware reported 4400 and the unchanged ordinary 18-test suite passed. One additional fresh bounded transaction was then executed and verified. No favorable terminal outcome was required, and no live challenge was retried. This supports a configuration contribution but does not prove a hardware root cause or permanent stability. No runtime source patch, full-frontier/Lean recertification, successor promotion, Phase 18 replay, phase closure, or EGC result is claimed.

## Phase 17D materialized package/capability gate

See PHASE_17_MATERIALIZED_FRONTIER.md. Physical model/registry construction, 21 capability outputs and 13 Lean obligations are distinct from recursive-frontier certification, root transition authorization, or promotion.

## Phase 17E pinned formal execution

See PHASE_17_PINNED_LEAN_EXECUTION.md. Explicit pinned setup and actual kernel/capability checks are separate from recursive-productivity, concrete successor transition verification, or promotion.
