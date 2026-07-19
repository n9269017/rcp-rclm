# Phase 9 exit criteria

## A. Gate D and dependency boundary

- [x] Gate D Formal Core v3 is merged on `main`.
- [x] Runtime v2 remains the canonicalization, checker, promotion, rollback, and replay base.
- [x] Phase 9 Lean correspondence declarations build with the pinned v3 project.
- [x] The Phase 9 theorem-alias axiom audit contains no `sorryAx` or local axiom.

## B. Learned object correspondence

- [x] Model architecture, weights, tokenizer/vocabulary, training, optimizer, generator,
      planner, retrieval, memory, tool, verification, resource, and self-model fields have
      Lean/Python/schema correspondence.
- [x] Every record is immutable and strictly parsed.
- [x] Unknown fields, floats, malformed hashes, duplicate tasks, and noncanonical ordering
      are rejected by the frozen schema, canonical parser, or immutable record constructors.

## C. Frontier semantics

- [x] Frontier retention is exact set inclusion.
- [x] Frontier expansion requires a nonempty exact set difference.
- [x] Every frontier task has an independent current-model certification.
- [x] The reference transition is accepted and non-vacuous.
- [x] No-expansion, missing-certification, and forged-frontier mutations are rejected.

## D. Held-out isolation

- [x] The held-out access policy is immutable and hash bound.
- [x] Generator and training access to held-out prompts and answers is false.
- [x] Evaluator access begins only after candidate freeze.
- [x] Newly certified frontier tasks must be held out.

## E. Self-hosting semantic boundary

- [x] Generator, planner, proposal protocol, and self-hosting contract hashes are in state.
- [x] Mutating a self-hosting hash changes the canonical state hash.
- [x] Certificate bindings use the active predecessor generator and planner.
- [x] Generator/planner changes require substantive typed operations.

## F. Exact claim boundary

- [x] Selected task class is exactly `lean_theorem_completion_v1`.
- [x] Selected model family is exactly `compact_decoder_only_transformer_v1`.
- [x] Generic frontier-expanding successor availability remains an explicit premise.
- [x] No actual language-model training, learned proposal authority, or recursion claim is made.

## G. Validation

- [x] Linux, Windows, and macOS compile and test the same records.
- [x] JSON Schema Draft 2020-12 validates all reference records.
- [x] Canonical hashes and the reference report are identical across platforms.
- [x] Pinned Lean builds Formal Core v3 and the Phase 9 contract audit.
- [x] The exact source-head workflow and artifact digests are retained.
- [x] The final evidence-only head is required to run the same workflow without further
      source changes; its exact result is bound in PR #29 rather than self-referentially
      embedded in this file.

## Closure rule

All repository-source exit criteria are closed. Phase 9 is ready for review only after
PR #29 records a successful exact-head Linux, Windows, macOS, schema, reference,
manifest, pinned Lean, proof-hygiene, axiom-audit, and closure run for the evidence-only
head containing this file.
