# Phase 6 exit criteria

Phase 6 closes only when all of the following pass at one exact implementation head:

- [ ] Phase 0 through Phase 5A authoritative regression workflows pass.
- [ ] Linux, Windows, and macOS compile the Phase 6 package and execute its tests.
- [ ] The selector validates proposal, predecessor package, policy, objective, and hash bindings.
- [ ] The generator never receives candidate-workspace or package write authority.
- [ ] The predecessor package is independently measured from actual bytes.
- [ ] Symlinks, non-regular files, and hard-link aliases are rejected.
- [ ] The predecessor payload is copied into a fresh isolated workspace.
- [ ] Only selected operations may modify the workspace.
- [ ] Every changed path is recorded with exact before/after file hashes and modes.
- [ ] Canonical policy changes receive metadata-stripped semantic hashes.
- [ ] State-only, manifest-only, index-only, name-only, version-only, and timestamp-only changes are non-substantive.
- [ ] At least one declared substantive component is changed.
- [ ] Component classifications are restricted to their declared paths.
- [ ] Every internal copy, write/delete, rollback, verification, and package action is recorded.
- [ ] Runtime environment identity and fixed allowlisted environment-value hashes are retained.
- [ ] File, byte, write, command, and snapshot budgets are recomputed and enforced.
- [ ] A deterministic complete predecessor rollback archive is created.
- [ ] The rollback archive is restored in a fresh directory and reproduces the predecessor tree hash.
- [ ] The candidate package contains payload, rollback, evidence, and manifest trees only.
- [ ] The candidate manifest binds parent, payload, proposal, selection, change ledger, command log, environment, resources, rollback, and substantive component kinds.
- [ ] A public verifier recomputes every candidate-package binding after construction.
- [ ] Candidate payload or evidence tampering is rejected.
- [ ] Existing candidate output directories are never overwritten.
- [ ] Package staging is atomically renamed only after complete verification.
- [ ] The `initial` reference changes the state and verification policy.
- [ ] The `target` reference changes the memory policy while preserving the target state.
- [ ] Both reference packages are reproducible on a fixed platform.
- [ ] The pinned Formal Core and Phase 2/5A generated-source hygiene paths pass before closure.
- [ ] Cross-platform and pinned artifacts identify the exact checked head.

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

A clean Phase 6 closure licenses Phase 7 closed-loop promotion-controller development. It does not make the generator trusted and it does not itself promote a package.
