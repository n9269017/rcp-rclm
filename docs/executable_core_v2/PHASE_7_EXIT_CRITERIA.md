# Phase 7 exit criteria

The executable implementation closed every criterion below at branch head
`001f060bb79015a7b9b06722977323e3f5f71063` in workflow run `29396211684`.
The subsequent evidence/status head must pass the same Phase 0–7 matrix before merge.

- [x] Phase 0 through Phase 6 authoritative regression workflows pass.
- [x] Linux, Windows, and macOS compile the controller and execute the Phase 7 tests.
- [x] The controller loads and revalidates the immutable active predecessor package.
- [x] A deterministic store lock rejects concurrent controller mutation.
- [x] The untrusted generator runs in its Phase 5A separate-process boundary.
- [x] Every proposal is executed twice and replay equality is required.
- [x] Proposal validation, selection, and realization remain separate stages.
- [x] The realized candidate is publicly reverified from actual package bytes.
- [x] Objective evidence is reconstructed from predecessor and candidate states.
- [x] Certificate construction occurs outside the generator.
- [x] Generated Lean source passes the pre-compilation forbidden-token gate.
- [x] The pinned Lean bridge accepts before final checker invocation.
- [x] The hardened checker owns the mathematical acceptance decision.
- [x] Candidate bytes are unchanged between realization and checker completion.
- [x] Every attempt records raw generator I/O, reports, evidence, reason codes, and hashes.
- [x] Manual repair and candidate mutation are absent and structurally forbidden.
- [x] Rejected attempts preserve the active package and append rejection ledger entries.
- [x] Retry count and attempt units are bounded independently of generator claims.
- [x] Indeterminate results are nonpromoting and stop the run.
- [x] Promotion packages bind the parent package hash and complete accepted evidence.
- [x] Promotion package and ledger entry are written before the active pointer changes.
- [x] The active pointer is replaced atomically and verified after replacement.
- [x] Promotion-store, package, ledger, and pointer tampering are rejected.
- [x] The initial reference promotes a genuine verification-policy successor.
- [x] The second reference promotes a genuine memory-policy successor.
- [x] The exhausted reference performs two rejected retries and preserves the active package.
- [x] The complete reference trajectory passes the pinned Formal Core and Lean bridge.
- [x] Final implementation artifacts bind the exact checked implementation head.

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

A clean final evidence-head revalidation and merge licenses Phase 8 independent replay
and finite recursive trajectory development. It does not make the generator trusted and
does not prove unbounded successor availability.
