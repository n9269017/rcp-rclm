# First PyTorch pilot exit criteria

The first learned-successor pilot closes only when every item below passes at one exact
published head.

## Implementation and local validation

- [x] PyTorch is optional and confined to the untrusted proposal worker.
- [x] Importing the host admission and replay modules does not import PyTorch, the
      proposal backend, or its launcher.
- [x] The proposal backend runs in a separate isolated process with a fixed timeout and
      fresh atomic output path.
- [x] The worker rejects a visible GPU and uses one CPU thread.
- [x] PyTorch version, architecture, seed, optimizer, learning rate, and step count are
      pinned.
- [x] Exactly one optimizer step changes a canonical packaged tensor hash.
- [x] Held-out labels are absent from the backend request schema.
- [x] Architecture, tensor, optimizer, training-data, RNG, command, resource,
      evaluation-request, and rollback-binding manifests are complete.
- [x] Tensor files use canonical little-endian signed int64 serialization, not pickle.
- [x] Tensor byte hashes and Phase 1 domain-separated hashes recompute.
- [x] Two fresh proposal processes produce equal canonical evidence.
- [x] The predecessor remains byte-identical during training.
- [x] The host reconstructs the Phase 6 selection and ignores candidate-reported
      selection and self-certification fields.
- [x] Phase 6 realizes and publicly verifies a substantive `model_weights` candidate.
- [x] Phase 6 records every actual modification and verifies exact rollback.
- [x] A framework-independent integer evaluator observes strict held-out improvement and
      protected-metric non-regression.
- [x] Exact model-gate failure rejects and preserves the active predecessor.
- [x] Lean rejection is nonpromoting.
- [x] The accepted fixture passes Lean and the hardened checker and is atomically
      promoted through the Phase 7 store.
- [x] Model-free replay recomputes the retained candidate with zero training invocations.
- [x] Replay rejects retained-evidence, candidate-package, source, and loaded-training
      tampering.
- [x] Local source quality is clean and the 23 focused tests pass.

## Authoritative published-head validation

- [ ] Linux, Windows, and macOS pass the proposal, exact evaluation, promotion,
      rejection, rollback, and replay suites.
- [ ] All Phase 0–8 authoritative workflows remain green at the same final head.
- [ ] The pinned Formal Core builds and Phase 2 differential conformance passes.
- [ ] The real pinned Lean bridge and hardened checker admit the accepted learned
      candidate.
- [ ] The pinned exact-objective rejection preserves the active package.
- [ ] The original training worker and launcher are physically absent before replay.
- [ ] Pinned independent replay reports zero training invocations and no forbidden
      training modules.
- [ ] All regenerated Lean source passes the `sorry`/`sorryAx`/`admit` and local-axiom
      gate before compilation.
- [ ] Exact-head workflow IDs, package hashes, replay hashes, and artifact digests are
      committed to the validation record.
- [ ] The final documentation/evidence head is independently revalidated.

The following remain false after this pilot:

```text
generator trust
learned proposal authority
arbitrary learned-system refinement
open-ended generator correctness
GPU reproducibility
LLM-scale successor generation
general noncommuting quantum semantics
strict useful improvement at every recursive step
unbounded successor availability
external benchmark performance
autonomous or unbounded RSI
```
