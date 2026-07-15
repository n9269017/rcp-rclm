# Phase 8 independent-replay validation

## Validation state

The independent-replay implementation is published. Exact-head cross-platform and
pinned Lean closure is being revalidated after repairing Windows newline normalization
and replay-summary manifest serialization. The repaired implementation head is
`2e59dfa655a5fddec944d354b349be58591b7c8d`; no closure claim is made until one
published branch head passes the full Phase 0–8 workflow matrix.

## Local deterministic evidence

The current local implementation reports:

```text
Python files scanned: 173
source-quality issues: 0

Phase 1 tests:  74
Phase 2 tests:  19
Phase 3 tests:  20
Phase 4 tests:  10
Phase 5A tests: 18
Phase 6 tests:  22
Phase 7 tests:  17
Phase 8 tests:  23
```

The fixture-backed Phase 8 roundtrip produced:

```text
source Phase 7 trajectory hash:
bb5440c2fc8abfa077ff500c19047305b417777accdd32c447185974755a092a

source store tree hash:
c88e84190c0d519001f415b1b1e5cbb583d4bf3110d14d6488c54dd725052d56

replay bundle manifest hash:
f9add553db0379f33fcbda5a52798b9f926aff5b29777d9832aa4e5ecf11f9b0

independent replay report hash:
17cea55d51f85581eac90e6397561ec86d5cda39b675eccb6061036253c92d67

roundtrip hash:
5f183f12a139cb50f3e68f437341526a38714fc7061a06b2ea1e1fa0698e7471
```

The finite package chain is:

```text
0a80ac68151d9c64915472b0611d983f01622988cc32187ce9ff822c343c1211
→ 29a6684c57a5f7dbe6919b942fe5f45ea305ba148411d550c781b5a844dcef10
→ 14ed1b50445e9d0f6444ebf7b1aa1a61acfe1e3a3c585ae8103f60bfb66c07d4
```

The replay report contains four attempt records: two reproduced promotions and two
reproduced bounded rejections. All attempts passed their replay obligations and every
attempt records zero generator invocations. A separate local isolation run removed the
original generator process and worker source files, deleted their bytecode caches, and
replayed the same bundle successfully. The replay CLI also observed no forbidden
generator module in `sys.modules` before or after reproduction.

## Local attack coverage

The 23 Phase 8 tests cover:

```text
strict bundle and report round trips
bundle layout and canonical-manifest rejection
byte tampering of raw generator output
predecessor and candidate package tampering
evaluation and certificate tampering
checker-report and resource-evidence tampering
rollback-archive tampering
promotion-parent substitution
rejected-attempt reproduction
Lean rejection and semantic disagreement
replay source capability rejection
proof that the generator process is never called
two-fresh-directory deterministic replay
existing-output protection
```

## Exact-head workflow requirements

The authoritative Phase 8 workflow must pass:

```text
Linux, Windows, and macOS compilation and Phase 1–8 regression
fixture-backed replay on all three platforms
complete pinned Formal Core build
all ten Phase 2 differential cases
pinned Phase 7 source trajectory creation
portable replay-bundle construction
pinned Lean independent replay after removing the generator process and worker
zero forbidden generator modules loaded during replay
generated Lean source admission/local-axiom scan
Phase 8 closure artifact
```

The final validation record will preserve the exact implementation head, workflow IDs,
test totals, chain and replay hashes, and platform, pinned, and closure artifact digests.
Those fields are populated only after CI completes and are not asserted
self-referentially by the commit that triggers the run.

## Claim boundary

Before exact-head closure, Phase 8 is an implementation candidate. After clean closure
it supports only the finite Gate B promoted trajectory and selected Gate C regression
claim described in `PHASE_8_INDEPENDENT_REPLAY.md`. It does not prove autonomous or
unbounded RSI.
