# Phase 4 exit criteria

Phase 4 is closed at the declared finite Gate B binary and selected
commuting/diagonal Gate C scope. The following criteria were satisfied at the clean
implementation head recorded in `PHASE_4_VALIDATION.md`:

- [x] Phase 0 contract validation passes.
- [x] Phase 1 runtime regression passes on Linux, Windows, and macOS.
- [x] Phase 2 bridge regression passes on Linux, Windows, and macOS.
- [x] The pinned Phase 2 Lean build and generated-source conformance workflow pass.
- [x] Phase 3 checker regression passes on Linux, Windows, and macOS.
- [x] The hardened checker accepts the clean Gate B and selected Gate C references.
- [x] The hardened checker is deterministic and does not mutate its request.
- [x] Predecessor and candidate semantic-tree hashes are recomputed.
- [x] Candidate parent package ID and parent manifest hash are recomputed.
- [x] Candidate, certificate, trust, resource, policy, and claim hashes are recomputed.
- [x] The Phase 3 checker-manifest hash is pinned and checked.
- [x] The transition-binding hash includes predecessor, candidate, certificate, evaluation, and Lean evidence.
- [x] Every required attack is represented by a first-class structured result.
- [x] Every attack is executed twice with identical structured observation hashes.
- [x] No required attack produces an accepting verdict.
- [x] Malformed and unknown schemas are rejected.
- [x] Missing evidence is rejected.
- [x] Parent-hash substitution is rejected.
- [x] Certificate replay against another predecessor is rejected.
- [x] Candidate-file and checker-manifest tampering are rejected.
- [x] NaN and infinity are rejected.
- [x] Negative and non-normalized probability vectors are rejected.
- [x] Unsupported diagonal-QRE support is rejected.
- [x] Wrong dimensions, non-diagonal matrices, and unsupported channels are rejected.
- [x] Forged recovery and strict-progress witnesses are rejected.
- [x] Boundary-overlapping strict margins are nonaccepting.
- [x] Resource overflow, trust replacement, manual repair, and hidden-oracle markers are rejected.
- [x] `sorry`, `sorryAx`, `admit`, local `axiom`, and invalid UTF-8 generated Lean source are rejected before compilation.
- [x] Cross-platform Phase 4 artifacts and SHA-256 digests are retained.
- [x] The workflow closure artifact identifies the exact checked implementation head.
- [x] The final documentation-only PR head is independently revalidated and recorded in the pull-request discussion.

The following remain false after Phase 4:

```text
generator trust
candidate promotion authorization
selector or realizer implementation
promotion or rollback implementation
independent replay
PyTorch proposal acceptance
external benchmark claims
general noncommuting quantum semantics
autonomous or unbounded RSI
```

A clean Phase 4 closure licenses Phase 5A deterministic reference-generator
development only.
