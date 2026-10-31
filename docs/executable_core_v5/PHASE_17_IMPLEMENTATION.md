# Phase 17 implementation — initial control-plane slice

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

## Next implementation obligations

1. Pin and independently reopen a declared Phase 16 terminal package, including
   its full predecessor and certified frontier evidence. Preserve all Phase 16
   terminal identities for subsequent EGC-0; do not choose by EGC scores.
2. Connect package-bound objective selection and fresh post-freeze commitments
   with evaluator seeds and answer material excluded from proposer state.
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
