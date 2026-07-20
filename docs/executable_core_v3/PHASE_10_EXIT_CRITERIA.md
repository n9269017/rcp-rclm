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

- [ ] The base package contains trained, nontrivial language-model weights.
- [ ] The training backend is isolated and treated as untrusted computation.
- [ ] Training-data provenance and curriculum evidence are independently checked.
- [ ] Held-out prompts and reference answers remain unavailable before candidate freeze.
- [ ] The candidate contains a genuine learned weight or adapter update.

## E. Authoritative inference and formal-language evaluation

- [ ] Deterministic CPU inference over canonical package tensors is implemented.
- [ ] Decoding policy and tie-breaking are fixed and hash bound.
- [ ] At least one protected Lean theorem-completion task is solved by the predecessor.
- [ ] Every protected predecessor task is solved by the candidate.
- [ ] At least one new held-out Lean task is solved only by the candidate.
- [ ] Every task success is established by the pinned independent Lean verifier.

## F. Information-theoretic evidence

- [ ] Model-output density records are constructed from actual model distributions.
- [ ] Selected entropy and KL/diagonal-QRE values are recomputed independently.
- [ ] Protected KL/QRE non-regression is certified by exact arithmetic or outward intervals.
- [ ] Any strict information witness is bound to the actual predecessor and candidate.

## G. Successor realization and promotion

- [ ] The candidate model hash differs from the predecessor model hash.
- [ ] The complete Phase 9/Gate D transition report accepts.
- [ ] Phase 6 realization records every changed file and component.
- [ ] Rollback restoration is byte exact.
- [ ] Pinned Lean and the hardened checker both accept.
- [ ] Phase 7 atomically promotes the candidate.

## H. Independent replay

- [ ] Replay succeeds after removing the training worker.
- [ ] Replay performs zero training invocations.
- [ ] Replay reconstructs package hashes, task evidence, KL/QRE evidence, Lean verdict,
      hardened-checker verdict, parent linkage, and rollback.
- [ ] Linux, Windows, and macOS produce the same authoritative result.

## Closure status

Phase 10 is **in progress**. Sections A–C close the canonical substrate and conservative
extension slice. The full Phase 10 claim remains open until Sections D–H are all closed
at one exact source head.
