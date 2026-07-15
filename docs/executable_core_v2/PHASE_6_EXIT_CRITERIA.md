# Phase 6 exit criteria

Phase 6 is closed at hardened implementation head
`6afbf8a395a9b41cd4f6d9b5accbe247974c8b20` in workflow run `29383092505`.
The retained validation record establishes:

- [x] Phase 0 through Phase 5A authoritative regression workflows pass.
- [x] Linux, Windows, and macOS compile the Phase 6 package and execute its tests.
- [x] The selector validates proposal, predecessor package, policy, objective, and hash bindings.
- [x] The generator never receives candidate-workspace or package write authority.
- [x] The predecessor package is independently measured from actual bytes.
- [x] Symlinks, non-regular files, and hard-link aliases are rejected.
- [x] The predecessor payload is copied into a fresh isolated workspace.
- [x] Only selected operations may modify the workspace.
- [x] Every changed path is recorded with exact before/after file hashes and modes.
- [x] Canonical policy changes receive metadata-stripped semantic hashes.
- [x] State-only, manifest-only, index-only, name-only, version-only, and timestamp-only changes are non-substantive.
- [x] At least one declared substantive component is changed.
- [x] Component classifications are restricted to their declared paths.
- [x] Every internal copy, write/delete, rollback, verification, and package action is recorded.
- [x] Runtime environment identity and fixed allowlisted environment-value hashes are retained.
- [x] File, byte, write, command, and snapshot budgets are recomputed and enforced.
- [x] A deterministic complete predecessor rollback archive is created.
- [x] The rollback archive is restored in a fresh directory and reproduces the predecessor tree hash.
- [x] The candidate package contains payload, rollback, evidence, and manifest trees only.
- [x] The candidate manifest binds parent, payload, proposal, selection, change ledger, command log, environment, resources, rollback, and substantive component kinds.
- [x] The public verifier restores the predecessor and independently recomputes selected before/after operation bindings.
- [x] The public verifier recomputes the actual modified-file ledger, substantive component kinds, command log, and resource usage.
- [x] A coherent selection/realization/manifest substitution is rejected when it does not match the actual predecessor and candidate bytes.
- [x] Candidate payload, evidence, rollback, and unexpected-entry tampering are rejected.
- [x] Existing candidate output directories are never overwritten.
- [x] Package staging is atomically renamed only after complete verification.
- [x] The `initial` reference changes the state and verification policy.
- [x] The `target` reference changes the memory policy while preserving the target state.
- [x] Both reference packages are reproducible on a fixed platform.
- [x] The pinned Formal Core and Phase 2/5A generated-source hygiene paths pass before closure.
- [x] Cross-platform and pinned artifacts are retained and bind to the exact implementation head through artifact metadata.

The following remain false after Phase 6:

```text
candidate promotion authorization
active-package replacement
promotion-ledger mutation
automatic generator retry
independent replay without the generator
open-ended generator correctness
learned PyTorch proposal acceptance
external benchmark claims
general noncommuting quantum semantics
autonomous or unbounded RSI
```

A clean Phase 6 closure licenses Phase 7 closed-loop promotion-controller development.
It does not make the generator trusted and it does not itself promote a package. The
final documentation/evidence PR head is revalidated separately and recorded in the
pull-request discussion before merge.
