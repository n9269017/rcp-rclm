# Phase 10 exit criteria

## A. Phase 9 dependency

- [x] Phase 9 is merged and closed at its declared contract scope.
- [x] The Phase 10 substrate depends on the unchanged Runtime v2 trust foundation.
- [x] Phase 10 records refine the selected `compact_decoder_only_transformer_v1` identity.

## B. Canonical compact-model substrate

- [x] A fixed 5–50 million parameter decoder-only transformer graph is defined.
- [x] The exact base parameter count is recomputed from the tensor graph.
- [x] A fixed tokenizer, vocabulary, context length, and architecture family are bound.
- [x] Tensor names, shapes, dtype, byte order, scales, sizes, and raw hashes are canonical.
- [x] Training, optimizer, curriculum, generator, planner, retrieval, memory, tool,
      verification, resource, RNG, environment, and self-model manifests are present.
- [x] The concrete package reconstructs an exact Phase 9 `ModelIdentity`.
- [x] Unknown files, missing files, tensor tampering, and manifest mismatches fail closed.

## C. Conservative architecture extension

- [x] A rank-8 LoRA graph targets attention and MLP projections in every layer.
- [x] The extension has deterministic nonzero `A` tensors and exact-zero `B` tensors.
- [x] Lean proves pointwise and function-level preservation for zero output factor.
- [x] Python verifies the concrete zero-output preconditions.
- [x] The extension changes the model identity while retaining the base tensor tree.
- [x] Dropping the adapter reconstructs the predecessor model identity exactly.

## D. Actual learned language model

- [x] The base package contains nontrivial canonical language-model weights at the selected
      sparse transformer execution profile.
- [x] A separate PyTorch CPU training/export worker performs genuine one-step SGD updates.
- [x] The worker is isolated, source scanned, invoked with `-I -B`, and treated as untrusted.
- [x] Host integer arithmetic recomputes and byte-compares every accepted candidate tensor.
- [x] Training-data provenance and curriculum evidence are independently hash bound.
- [x] Held-out task IDs, prompts, source, and reference answers remain unavailable before
      candidate freeze.
- [x] The candidate contains a genuine learned model-weight update.
- [x] Two fresh worker invocations are required to produce identical output.

## E. Authoritative inference and formal-language evaluation

- [x] Deterministic CPU inference over canonical package tensors is implemented for the
      selected `sparse_last_token_transition_v1` profile.
- [x] The selected execution profile is fail-closed and does not claim general
      native-float transformer equivalence.
- [x] Decoding policy, maximum length, distribution normalization, and tie-breaking are
      fixed and hash bound.
- [x] At least one protected Lean theorem-completion task is solved by the predecessor.
- [x] Every protected predecessor task is solved by the candidate.
- [x] At least one new held-out Lean task is solved only by the candidate.
- [x] Every accepted task success is established by the pinned independent Lean verifier.
- [x] Candidate self-reported task success is never consumed.

## F. Information-theoretic evidence

- [x] Strictly positive exact model-output distributions are constructed from canonical
      model scores.
- [x] Each distribution is represented as a selected diagonal token density.
- [x] Shannon/von Neumann entropy intervals are recomputed independently.
- [x] KL/diagonal-QRE intervals are recomputed independently.
- [x] Protected KL/QRE non-regression is certified with exact zero regression.
- [x] A strict held-out information witness has a positive certified lower endpoint.
- [x] Formal Core v3 records the selected diagonal entropy and QRE/KL identities.

## G. Gate D refinement, realization, and promotion

- [x] The candidate model hash differs from the predecessor model hash.
- [x] Every protected task is recertified for the candidate model identity.
- [x] The complete Phase 9 learned transition report accepts exact frontier expansion.
- [ ] Phase 6 realizes every learned tensor, manifest, and policy change.
- [ ] Phase 6 records and verifies byte-exact rollback restoration.
- [ ] The inherited pinned-Lean and hardened-checker stability obligations accept.
- [ ] Phase 7 atomically promotes the candidate.

## H. Independent replay

- [ ] Replay succeeds after physically removing the training worker.
- [ ] Replay performs zero training invocations.
- [ ] Replay reconstructs package hashes, task evidence, KL/QRE evidence, Lean verdict,
      hardened-checker verdict, parent linkage, and rollback.
- [ ] Linux, Windows, and macOS produce the same authoritative replay result.

## Closure status

Phase 10 is **in progress**. Sections A–F and the Gate D/Phase 9 portion of Section G are
implemented by the Phase 10A/10B source.  The full Phase 10 claim remains open until the
unchecked realization, promotion, rollback, and independent-replay obligations in
Sections G–H close at one exact source head.
