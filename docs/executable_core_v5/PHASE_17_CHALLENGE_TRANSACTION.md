# Phase 17C — bounded post-freeze challenge/evaluation transaction

Status: implemented development increment; not Phase 17 exit or Gate E closure.
Base development head: `bb1f8669311c099938cc299c2b4fd9f5f77be9e3`.

## What executes

1. Reopen the same three hash-pinned Phase 16 / M9 historical inputs as Phase 17B.
2. Select and recompute the initial objective and predecessor/objective freeze.
3. Start a dedicated evaluator process. It independently reopens the pinned
   inputs, verifies the objective freeze, and only then draws 32 bytes of OS
   randomness. No runtime seed, winner, evaluator path or executable is accepted.
4. Derive a target specification and eight hidden four-integer input vectors
   without consulting the candidate list or selecting an available winner.
5. Return a salted commitment and bounded public challenge description, never
   the target parameters, vectors, expected outputs or a target program hash.
6. Bind the unchanged Phase 16 32-program grammar/ranker to that commitment.
   Independently generated grammar identities must agree exactly.
7. For each selected candidate, construct a canonical bounded-DSL artifact,
   commit its hash, receive an evaluator freeze receipt, and only then evaluate
   the identical artifact. Altered, duplicate or unadmitted candidates reject.
8. Return generic rejection feedback or `candidate_passed` with parent, challenge,
   artifact and freeze bindings. The controller stops at `await_root_verification`
   on a candidate pass; it cannot promote.
9. Seal the terminal session. Only after sealing are the evaluator opening and
   test vectors revealed. The worker exits; that session cannot accept a new
   candidate. Recompute every transcript response, validate its external hash
   anchor, and replay the controller checkpoint.

The implementation is data-only. It never executes caller-supplied Python,
commands, compiler plugins, pickle data, URLs, or paths.

## Exact semantic and novelty scope

The eight existing families are bounded transformations of four-integer vectors.
A candidate artifact describes one such program and its predecessor binding; it
is NOT an installed model-weight successor. The evaluator uses a separate
reference interpreter rather than accepting a candidate's self-reported output.
Differential tests compare this interpreter and grammar to the unchanged
Phase 16 implementation.

The target variant and parameters are sampled independently of the candidate
set. The hash-to-range mapping is fixed and has modulo bias; no exact-uniformity
claim is made. There may be no acceptable candidate. Failed novelty, semantic
mismatch, or an unavailable target can all yield complete bounded exhaustion.
No retry-until-success policy or seeded winner is part of the live command.

Novelty here means: the target is non-identity on the eight retained probes,
and none of the historical predecessor's installed programs in the objective
family solves all probes. This is a finite, declared registry-relative test.
It is NOT a full-tensor predecessor evaluation, proof of semantic inequivalence
on all inputs, broad intelligence evaluation, or full-frontier recertification.

The live worker has no deterministic-seed parameter. A positive unit-test
fixture uses preselected entropy explicitly inside the test; it is not counted
as a fresh hidden campaign or as evidence of a discovered empirical improvement.

## Isolation and authority boundaries

The client launches fixed trusted repository code with Python `-I -S -B -u`,
no shell, bounded canonical JSON frames, a restricted inherited environment,
and a temporary working directory. Evaluator-owned answers remain in the worker
until the session is sealed. Invalid protocol messages fail closed, and a
transport timeout or worker death cannot yield an authorized success.

This is process/protocol separation for bounded data, NOT a hardened sandbox.
A hostile process with the same OS-user privileges, debugger access, modified
interpreter, compromised kernel, side-channel access, or write access to trusted
source is outside the demonstrated boundary. No arbitrary model-generated native
or Python executable should be launched through this service. Future hostile-
executable isolation remains an explicit requirement, not an implied success.

A transcript hash gives integrity relative to an independently retained anchor;
it does not authenticate its author or independently prove the time/quality of
randomness generation. The runtime samples after freeze in its actual control
flow; replay alone cannot prove that a third party used genuine entropy.

Session closure prevents reuse of that worker. Global challenge uniqueness,
anti-grinding across restarts, durable consumed-challenge bookkeeping, durable
crash recovery and multi-turn parent linkage are NOT implemented here.

## Resource scope

A session permits at most 32 evaluations, 66 protocol events, 128 KiB per message,
and 2 MiB per retained transcript. The client enforces a response timeout and
kills a failed worker. Candidate credits and elapsed duration are recorded.
These are engineering bounds, not full resource accounting: CPU/accelerator
usage, peak memory, all bootstrap costs, storage, and energy are not yet part of
a complete auditable resource envelope.

## Local entry points

```powershell
python scripts/run_phase17_tests.py
python scripts/run_phase17_bootstrap_tests.py
python scripts/run_phase17_challenge_tests.py
python scripts/run_phase17_challenge_transaction.py --output <new-external-directory> --candidate-credits 32
```

The enlarged foundation suite contains 110 tests. The challenge integration
suite contains 18 tests (12 real process tests plus 6 reference/driver tests).
The unchanged historical-archive suite has 10 tests. The installation helper
checks these exact counts and zero skips; the older generic evidence recorder's
historical profile is not rewritten to reinterpret prior reports.

The live transaction may finish with `search_exhausted` or
`await_root_verification`. Both are valid bounded transaction outcomes, NOT
successful Phase 17 completion. No survivor or accepted candidate is fabricated
to make a test or publication look more impressive.

## Evidence and installation

Assistant evidence records its reconstructed dependency checkout and selected-
module limitations. Five Phase 16 modules are byte-identical to the public Git
blobs; only the missing eager export initializer is bypassed in assistant
in-process differential tests. The shipped scripts use normal imports.

The application helper prepares a NEW full Git checkout from the owner's exact
local source, commits the new implementation there, runs normal foundation,
archive, process and fresh-transaction checks, and retains immutable logs and
source-bound reports. Only after success does it fast-forward the owner's
existing development branch and optionally push. No reset, force push, main
merge or hosted Actions invocation occurs. The fresh checkout uses the existing
Python environment: it is not a clean-environment or platform-matrix claim.

## Preserved nonclaims

```text
promotion_authorized          = false
full_frontier_recertified     = false
fresh_lean_verification       = false
os_security_sandbox          = false
phase18_independent_replay    = false
phase17_exit_closed          = false
gate_e_closed                = false
egc0_started                 = false
```

Next: integrate full-frontier/root verification and candidate realization beyond
this bounded descriptor, then atomic promotion/rollback, durable cross-turn
ledgering and complete resource accounting. Evolving objectives, open-horizon
campaign closure, Phase 18 replay and required platform evidence remain open.
Historical releases, their DOI records and previously retained failures stay
unchanged. PR #68 remains draft and unmerged.
