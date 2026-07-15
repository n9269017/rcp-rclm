# Phase 7 exit criteria

Phase 7 closes only when all of the following pass at one exact implementation head:

- [ ] Phase 0 through Phase 6 authoritative regression workflows pass.
- [ ] Linux, Windows, and macOS compile the controller and execute the Phase 7 tests.
- [ ] The controller loads and revalidates the immutable active predecessor package.
- [ ] A deterministic store lock rejects concurrent controller mutation.
- [ ] The untrusted generator runs in its Phase 5A separate-process boundary.
- [ ] Every proposal is executed twice and replay equality is required.
- [ ] Proposal validation, selection, and realization remain separate stages.
- [ ] The realized candidate is publicly reverified from actual package bytes.
- [ ] Objective evidence is reconstructed from predecessor and candidate states.
- [ ] Certificate construction occurs outside the generator.
- [ ] Generated Lean source passes the pre-compilation forbidden-token gate.
- [ ] The pinned Lean bridge accepts before final checker invocation.
- [ ] The hardened checker owns the mathematical acceptance decision.
- [ ] Candidate bytes are unchanged between realization and checker completion.
- [ ] Every attempt records raw generator I/O, reports, evidence, reason codes, and hashes.
- [ ] Manual repair and candidate mutation are absent and structurally forbidden.
- [ ] Rejected attempts preserve the active package and append rejection ledger entries.
- [ ] Retry count and attempt units are bounded independently of generator claims.
- [ ] Indeterminate results are nonpromoting and stop the run.
- [ ] Promotion packages bind the parent package hash and complete accepted evidence.
- [ ] Promotion package and ledger entry are written before the active pointer changes.
- [ ] The active pointer is replaced atomically and verified after replacement.
- [ ] Promotion-store, package, ledger, and pointer tampering are rejected.
- [ ] The initial reference promotes a genuine verification-policy successor.
- [ ] The second reference promotes a genuine memory-policy successor.
- [ ] The exhausted reference performs two rejected retries and preserves the active package.
- [ ] The complete reference trajectory passes the pinned Formal Core and Lean bridge.
- [ ] Final artifacts bind the exact checked head.

The following remain false after Phase 7:

```text
independent replay without the generator
open-ended generator correctness
generator trust
learned PyTorch proposal acceptance
external benchmark performance
general noncommuting quantum semantics
autonomous or unbounded RSI
```

A clean Phase 7 closure licenses Phase 8 independent replay and finite recursive
trajectory development. It does not make the generator trusted and does not prove
unbounded successor availability.
