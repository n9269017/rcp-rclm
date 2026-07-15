# First PyTorch pilot exit criteria

The first learned-successor pilot closes only when every item below passes at one exact
published head.

- [ ] PyTorch remains an optional dependency and is not imported by the checker,
      mathematics, canonicalization, promotion-store, or replay packages.
- [ ] The proposal backend runs in a separate process with a fixed timeout and a fresh
      atomic output path.
- [ ] The worker rejects a visible GPU and uses exactly one CPU thread.
- [ ] The PyTorch version, model architecture, seed, optimizer, learning rate, and step
      count are pinned.
- [ ] Exactly one optimizer step changes at least one raw packaged tensor hash.
- [ ] No held-out label is present in the backend input schema.
- [ ] The training-data, held-out-feature, architecture, tensor, optimizer, RNG, command,
      resource, evaluation-request, and rollback-binding manifests are complete.
- [ ] Tensor files use canonical little-endian int64 serialization rather than pickle.
- [ ] Tensor raw-byte hashes and Phase 1 domain-separated manifest hashes recompute.
- [ ] Two fresh proposal processes produce identical canonical outputs.
- [ ] The predecessor model tree is byte-identical before and after proposal generation.
- [ ] The Phase 6 selection record parses strictly and names `model_weights` as the
      substantive component.
- [ ] The existing Phase 6 package builder realizes and publicly verifies the candidate.
- [ ] Phase 6 independently records every actual changed file and rejects undeclared or
      falsely declared modifications.
- [ ] The Phase 6 rollback archive restores the exact predecessor tree.
- [ ] A framework-independent evaluator reads the realized int64 model package without
      importing PyTorch.
- [ ] Held-out correct count strictly improves under exact integer arithmetic.
- [ ] The protected class metric does not regress under exact integer arithmetic.
- [ ] Candidate-provided acceptance, certificate, and aggregate-score fields remain null.
- [ ] NaN, infinity, nonfinite gradients, gradient overflow, model-layout mismatch,
      malformed schema, predecessor tampering, output overwrite, and resource overflow
      remain nonaccepting.
- [ ] Linux, Windows, and macOS complete the proposal, exact evaluator, Phase 6 package,
      and deterministic two-process reference case.
- [ ] All Phase 0–8 authoritative workflows remain green.
- [ ] A pinned-Lean/hardened-checker admission adapter accepts or rejects without using a
      PyTorch reduction as mathematical evidence.
- [ ] A promoted pilot package, if any, is independently replayed without rerunning the
      original training backend.

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
