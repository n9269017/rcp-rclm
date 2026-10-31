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

## Validation boundaries

The local control-plane suite passes 26 tests. Seven adapter tests also pass
against five byte-identical Phase 16 modules fetched at the pinned public base:
`codec.py`, `constants.py`, `records.py`, `grammar.py`, and `ranking.py`.
The offline adapter test loader bypasses the Phase 16 package's eager export
initializer only; it substitutes no grammar, ranking, or state implementation.
This is selected-module integration testing, not a fresh complete v4.6 replay.

The retained reference campaign and terminal-state logical hashes were checked
before extracting the fixture. Its accepted eight-promotion campaign is only a
serialization test input, not a new Phase 17 campaign or an EGC selection rule.

GitHub-hosted bootstrap export attempts executed zero steps. Consequently no
new cross-platform CI, pinned Lean execution, authenticated bootstrap, full
successor campaign, or Phase 17 closure is asserted. The normal checkout test
entry point does NOT bypass package initializers.

The full repository checksum manifest must cover every new tracked file before
merge. Run `python scripts/phase17_refresh_checksums.py` to check the staged Git
blobs; `--write` refreshes the manifest without committing or pushing anything.
Do not merge a draft while its root checksum or complete-checkout tests remain
unverified.

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
