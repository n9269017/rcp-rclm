# Phase 5A exit criteria

Phase 5A closes only when all of the following are true at one exact implementation
head:

- [ ] Phase 0 contract validation passes.
- [ ] Phase 1 runtime regression passes on Linux, Windows, and macOS.
- [ ] Phase 2 bridge regression passes on Linux, Windows, and macOS.
- [ ] Phase 3 checker regression passes on Linux, Windows, and macOS.
- [ ] Phase 4 hardened/adversarial regression passes on Linux, Windows, and macOS.
- [ ] The pinned Formal Core v2 build passes.
- [ ] The generator request contains only predecessor package, public policy, declared objective, and resource budget.
- [ ] Unknown or forbidden control-plane fields are rejected.
- [ ] The generator runs in a separate process with a fresh temporary working directory.
- [ ] Generator package startup does not import any checker module.
- [ ] The worker verifies that no checker module is loaded before proposal interpretation.
- [ ] The worker audit hook denies all filesystem opens after startup, filesystem mutations, sockets, and subprocess creation.
- [ ] The worker receives no trust anchor, checker input, manifest history, promotion ledger, or reference-answer object.
- [ ] The active initial grammar contains only `improve`.
- [ ] The active target grammar contains only `stabilize`.
- [ ] Word depth and proof length are bounded by one.
- [ ] A generated Lean conformance file verifies the exact words, bounds, witness/proposal maps, certificate/candidate maps, membership, and rejected-word exclusion.
- [ ] The grammar conformance source passes the mandatory source guard before compilation.
- [ ] The grammar conformance source compiles with the pinned Lean project.
- [ ] The generator output contains no certificate, candidate successor, checker verdict, or promotion Boolean.
- [ ] Every generator invocation is replayed in a second fresh process.
- [ ] Both process outputs have identical canonical response hashes.
- [ ] Proposal bindings include predecessor, policy, objective, budget, input, and worker hashes or versions.
- [ ] Certificate construction occurs outside the generator.
- [ ] Typed update selection occurs outside the generator.
- [ ] The successor is computed from predecessor plus selected update, not copied from proposal output.
- [ ] The initial reference realizes the target state with an improvement certificate.
- [ ] The target reference realizes the target state with a stability certificate.
- [ ] Both realized transitions pass the mandatory generated-Lean source guard.
- [ ] Both realized transitions pass pinned Lean RCP/RCLM differential verification.
- [ ] Both realized transitions pass the Phase 4 hardened checker.
- [ ] Every stage emits a first-class structured record and content hash.
- [ ] The complete reference pipeline is deterministic across Linux, Windows, and macOS.
- [ ] Cross-platform artifacts and the exact checked head are retained.

The following remain false after Phase 5A:

```text
generator trust
open-ended search or synthesis
LLM/scaffold proposal support
learned PyTorch policy support
training-driven weight updates
Gate C bounded generator refinement
candidate promotion authorization
production selector/realizer isolation
promotion or rollback
independent replay without the generator
external benchmark claims
general noncommuting quantum semantics
autonomous or unbounded RSI
```

A clean Phase 5A closure licenses Phase 5B open-ended untrusted-generator development
and Phase 6 selector/realizer/package-builder development. It does not require Phase 5B
before Phase 6, and it does not make any generator trusted.
