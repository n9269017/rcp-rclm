# Phase 8 exit criteria

Phase 8 closes only when every item below passes at one exact implementation head.

- [ ] Phase 0 through Phase 7 authoritative workflows pass.
- [ ] Linux, Windows, and macOS compile the replay package and execute the Phase 8 tests.
- [ ] The replay source guard rejects generator-process, worker, stochastic, network,
      and subprocess capabilities.
- [ ] The core replay function itself enforces the source guard.
- [ ] The replay bundle contains only `manifest.json` and `store/`.
- [ ] The complete Phase 7 store tree is copied byte-for-byte and content-addressed.
- [ ] The active pointer, complete ledger chain, and all immutable packages revalidate.
- [ ] Every non-bootstrap ledger entry has one immutable attempt index.
- [ ] Every source transition preserves raw generator input, output, stderr, process
      reports, proposal, realization, evaluation, certificate, Lean, checker, resource,
      rollback, parent, and successor evidence as applicable.
- [ ] The reproducer invokes the original generator zero times.
- [ ] The pinned replay succeeds after the generator process and worker source files are removed.
- [ ] The replay CLI verifies that neither forbidden generator module is loaded.
- [ ] Generator input is reconstructed from the immutable predecessor package.
- [ ] Preserved generator outputs are parsed canonically and two-run equality is checked.
- [ ] Proposal validation is recomputed against the public bounded grammar.
- [ ] Phase 6 selection and actual filesystem realization are recomputed.
- [ ] Candidate package, payload, manifest, resource, and rollback hashes agree.
- [ ] Objective evaluation is reconstructed from predecessor and candidate states.
- [ ] Certificate construction is recomputed outside the generator.
- [ ] Captured Lean source is independently regenerated and scanned before compilation.
- [ ] The pinned Lean bridge reruns for each promoted transition.
- [ ] The captured hardened-checker result recomputes from its captured inputs.
- [ ] A fresh hardened-checker run with the fresh Lean report agrees mathematically.
- [ ] Promotion parent links and nonpromotion active-hash preservation are recomputed.
- [ ] Both bounded grammar-exhaustion rejection attempts replay correctly.
- [ ] Bundle, package, generator-output, evaluation, certificate, Lean, checker, resource,
      rollback, and parent-link tampering remain nonaccepting.
- [ ] Replaying the same bundle in two fresh directories yields identical report bytes.
- [ ] The pinned Formal Core build and all ten Phase 2 differential cases pass.
- [ ] Generated Lean source contains no admitted-proof token or project-local axiom.
- [ ] Final artifacts bind the exact checked head.

The following remain false after Phase 8:

```text
generator trust
open-ended generator correctness
learned PyTorch proposal authority
arbitrary learned-system refinement
general noncommuting quantum semantics
strict useful improvement at every recursive step
unbounded successor availability
external benchmark performance
autonomous or unbounded RSI
```

A clean Phase 8 closure licenses a small deterministic learned-proposal pilot and
optional Phase 5B backend experiments behind the same untrusted proposal boundary. It
does not move PyTorch, model output, or floating-point diagnostics into the checker or
replay source of truth.
