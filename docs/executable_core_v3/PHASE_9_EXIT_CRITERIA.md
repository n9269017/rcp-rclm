# Phase 9 exit criteria

## A. Gate D and dependency boundary

- [x] Gate D Formal Core v3 is merged on `main`.
- [x] Runtime v2 remains the canonicalization, checker, promotion, rollback, and replay base.
- [ ] Phase 9 Lean correspondence declarations build with the pinned v3 project.
- [ ] The Phase 9 theorem-alias axiom audit contains no `sorryAx` or local axiom.

## B. Learned object correspondence

- [ ] Model architecture, weights, tokenizer/vocabulary, training, optimizer, generator,
      planner, retrieval, memory, tool, verification, resource, and self-model fields have
      Lean/Python/schema correspondence.
- [ ] Every record is immutable and strictly parsed.
- [ ] Unknown fields, floats, malformed hashes, duplicate tasks, and noncanonical ordering
      are rejected.

## C. Frontier semantics

- [ ] Frontier retention is exact set inclusion.
- [ ] Frontier expansion requires a nonempty exact set difference.
- [ ] Every frontier task has an independent current-model certification.
- [ ] The reference transition is accepted and non-vacuous.
- [ ] No-expansion, missing-certification, and forged-frontier mutations are rejected.

## D. Held-out isolation

- [ ] The held-out access policy is immutable and hash bound.
- [ ] Generator and training access to held-out prompts and answers is false.
- [ ] Evaluator access begins only after candidate freeze.
- [ ] Newly certified frontier tasks must be held out.

## E. Self-hosting semantic boundary

- [ ] Generator, planner, proposal protocol, and self-hosting contract hashes are in state.
- [ ] Mutating a self-hosting hash changes the canonical state hash.
- [ ] Certificate bindings use the active predecessor generator and planner.
- [ ] Generator/planner changes require substantive typed operations.

## F. Exact claim boundary

- [ ] Selected task class is exactly `lean_theorem_completion_v1`.
- [ ] Selected model family is exactly `compact_decoder_only_transformer_v1`.
- [ ] Generic frontier-expanding successor availability remains an explicit premise.
- [ ] No actual language-model training, learned proposal authority, or recursion claim is made.

## G. Validation

- [ ] Linux, Windows, and macOS compile and test the same records.
- [ ] JSON Schema Draft 2020-12 validates all reference records.
- [ ] Canonical hashes and the reference report are identical across platforms.
- [ ] Pinned Lean builds Formal Core v3 and the Phase 9 contract audit.
- [ ] Exact-head closure artifact and validation record are retained.
