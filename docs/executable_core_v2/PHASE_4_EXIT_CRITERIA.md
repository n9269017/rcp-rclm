# Phase 4 exit criteria

Phase 4 closes only when all of the following are true at one exact implementation
head:

- [ ] Phase 0 contract validation passes.
- [ ] Phase 1 runtime regression passes on Linux, Windows, and macOS.
- [ ] Phase 2 bridge regression passes on Linux, Windows, and macOS.
- [ ] The pinned Phase 2 Lean build and generated-source conformance workflow pass.
- [ ] Phase 3 checker regression passes on Linux, Windows, and macOS.
- [ ] The hardened checker accepts the clean Gate B and selected Gate C references.
- [ ] The hardened checker is deterministic and does not mutate its request.
- [ ] Predecessor and candidate semantic-tree hashes are recomputed.
- [ ] Candidate parent package ID and parent manifest hash are recomputed.
- [ ] Candidate, certificate, trust, resource, policy, and claim hashes are recomputed.
- [ ] The Phase 3 checker-manifest hash is pinned and checked.
- [ ] The transition-binding hash includes predecessor, candidate, certificate, evaluation, and Lean evidence.
- [ ] Every required attack is represented by a first-class structured result.
- [ ] Every attack is executed twice with identical structured observation hashes.
- [ ] No required attack produces an accepting verdict.
- [ ] Malformed and unknown schemas are rejected.
- [ ] Missing evidence is rejected.
- [ ] Parent-hash substitution is rejected.
- [ ] Certificate replay against another predecessor is rejected.
- [ ] Candidate-file and checker-manifest tampering are rejected.
- [ ] NaN and infinity are rejected.
- [ ] Negative and non-normalized probability vectors are rejected.
- [ ] Unsupported diagonal-QRE support is rejected.
- [ ] Wrong dimensions, non-diagonal matrices, and unsupported channels are rejected.
- [ ] Forged recovery and strict-progress witnesses are rejected.
- [ ] Boundary-overlapping strict margins are nonaccepting.
- [ ] Resource overflow, trust replacement, manual repair, and hidden-oracle markers are rejected.
- [ ] `sorry`, `sorryAx`, `admit`, local `axiom`, and invalid UTF-8 generated Lean source are rejected before compilation.
- [ ] Cross-platform Phase 4 artifacts and SHA-256 digests are retained.
- [ ] The final workflow closure artifact identifies the exact checked head.

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
