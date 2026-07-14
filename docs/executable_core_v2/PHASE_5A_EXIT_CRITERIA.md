# Phase 5A exit criteria

Phase 5A is closed at the declared finite Gate B classical bounded-seed scope. The
following criteria were satisfied at the clean implementation head recorded in
`PHASE_5A_VALIDATION.md`:

- [x] Phase 0 contract validation passes.
- [x] Phase 1 runtime regression passes on Linux, Windows, and macOS.
- [x] Phase 2 bridge regression passes on Linux, Windows, and macOS.
- [x] Phase 3 checker regression passes on Linux, Windows, and macOS.
- [x] Phase 4 hardened/adversarial regression passes on Linux, Windows, and macOS.
- [x] The pinned Formal Core v2 build passes.
- [x] The generator request contains only predecessor package, public policy, declared objective, and resource budget.
- [x] Unknown or forbidden control-plane fields are rejected.
- [x] The generator runs in a separate process with a fresh temporary working directory.
- [x] Generator package startup does not import any checker module.
- [x] The worker verifies that no checker module is loaded before proposal interpretation.
- [x] The worker audit hook denies all filesystem opens after startup, filesystem mutations, sockets, and subprocess creation.
- [x] The worker receives no trust anchor, checker input, manifest history, promotion ledger, or reference-answer object.
- [x] The active initial grammar contains only `improve`.
- [x] The active target grammar contains only `stabilize`.
- [x] Word depth and proof length are bounded by one.
- [x] A generated Lean conformance file verifies the exact words, bounds, witness/proposal maps, certificate/candidate maps, membership, and rejected-word exclusion.
- [x] The grammar conformance source passes the mandatory source guard before compilation.
- [x] The grammar conformance source compiles with the pinned Lean project.
- [x] The generator output contains no certificate, candidate successor, checker verdict, or promotion Boolean.
- [x] Every generator invocation is replayed in a second fresh process.
- [x] Both process outputs have identical canonical response hashes.
- [x] Proposal bindings include predecessor, policy, objective, budget, input, and worker hashes or versions.
- [x] Certificate construction occurs outside the generator.
- [x] Typed update selection occurs outside the generator.
- [x] The successor is computed from predecessor plus selected update, not copied from proposal output.
- [x] The initial reference realizes the target state with an improvement certificate.
- [x] The target reference realizes the target state with a stability certificate.
- [x] Both realized transitions pass the mandatory generated-Lean source guard.
- [x] Both realized transitions pass pinned Lean RCP/RCLM differential verification.
- [x] Both realized transitions pass the Phase 4 hardened checker.
- [x] Every stage emits a first-class structured record and content hash.
- [x] The complete reference pipeline is deterministic across Linux, Windows, and macOS.
- [x] Cross-platform artifacts and the exact checked implementation head are retained.

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

The final documentation/evidence PR head is independently revalidated and recorded in
the pull-request discussion before merge.
