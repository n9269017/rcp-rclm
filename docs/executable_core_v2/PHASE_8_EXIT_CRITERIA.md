# Phase 8 exit criteria

Phase 8 closes only when every item below passes at one exact implementation head.

- [x] Phase 0 through Phase 7 authoritative workflows pass.
- [x] Linux, Windows, and macOS compile the replay package and execute the Phase 8 tests.
- [x] The replay source guard rejects generator-process, worker, stochastic, network,
      and subprocess capabilities.
- [x] The core replay function itself enforces the source guard.
- [x] The replay bundle contains only `manifest.json` and `store/`.
- [x] The complete Phase 7 store tree is copied byte-for-byte and content-addressed.
- [x] The active pointer, complete ledger chain, and all immutable packages revalidate.
- [x] Every non-bootstrap ledger entry has one immutable attempt index.
- [x] Every source transition preserves raw generator input, output, stderr, process
      reports, proposal, realization, evaluation, certificate, Lean, checker, resource,
      rollback, parent, and successor evidence as applicable.
- [x] The reproducer invokes the original generator zero times.
- [x] The pinned replay succeeds after the generator process and worker source files are removed.
- [x] The replay CLI verifies that neither forbidden generator module is loaded.
- [x] Generator input is reconstructed from the immutable predecessor package.
- [x] Preserved generator outputs are parsed canonically and two-run equality is checked.
- [x] Proposal validation is recomputed against the public bounded grammar.
- [x] Phase 6 selection and actual filesystem realization are recomputed.
- [x] Candidate package, payload, manifest, resource, and rollback hashes agree.
- [x] Objective evaluation is reconstructed from predecessor and candidate states.
- [x] Certificate construction is recomputed outside the generator.
- [x] Captured Lean source is independently regenerated and scanned before compilation.
- [x] The pinned Lean bridge reruns for each promoted transition.
- [x] The captured hardened-checker result recomputes from its captured inputs.
- [x] A fresh hardened-checker run with the fresh Lean report agrees mathematically.
- [x] Promotion parent links and nonpromotion active-hash preservation are recomputed.
- [x] Both bounded grammar-exhaustion rejection attempts replay correctly.
- [x] Bundle, package, generator-output, evaluation, certificate, Lean, checker, resource,
      rollback, and parent-link tampering remain nonaccepting.
- [x] Replaying the same bundle in two fresh directories yields identical report bytes.
- [x] The pinned Formal Core build and all ten Phase 2 differential cases pass.
- [x] Generated Lean source contains no admitted-proof token or project-local axiom.
- [x] Final artifacts bind the checked implementation and PR merge-test heads.

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
