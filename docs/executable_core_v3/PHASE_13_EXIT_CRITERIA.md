# Phase 13 exit criteria

## Phase 13A — replay boundary and attack grammar

- [x] Replay-only contract is canonical and hashed.
- [x] Training, generator, and planner invocation counts are fixed to zero.
- [x] Forbidden learned-module and worker-path registries are frozen.
- [x] Replay source guard rejects training, generation, dynamic loading, subprocess, network, and nondeterministic imports/calls.
- [x] Retained-evidence manifest is canonical and content-addressed.
- [x] Complete 21-case selected adversarial registry is implemented.
- [x] Every Phase 13A attack rejects deterministically with its expected reason code.
- [x] Linux, Windows, and macOS portable validation is required by the permanent workflow.
- [x] Phase 12 merged-source completeness is independently audited and reported.
- [x] `phase13a_slice_closed=true` remains distinct from full Phase 13 closure.

## Full Phase 13 — still open

- [ ] Retain immutable `M0` through `M4` packages and all raw proposal inputs/outputs.
- [ ] Remove the original training, generator, planner, proposal-scaffold, and optimizer-execution implementations from the reproducer.
- [ ] Replay both captured rejections.
- [ ] Replay all four accepted candidate realizations.
- [ ] Recompute all package/model hashes.
- [ ] Recompute all seven task certifications with pinned Lean.
- [ ] Recompute selected entropy/KL/diagonal-QRE evidence.
- [ ] Recompute Gate D and hardened-checker verdicts.
- [ ] Verify exact rollback restoration for every realized candidate.
- [ ] Verify the complete parent and promotion-ledger chain.
- [ ] Verify generated Lean source with the proof-token gate.
- [ ] Pass Linux, Windows, and macOS complete replay.
- [ ] Bind one exact final source head and artifact set.
- [ ] Emit `phase13_exit_closed=true`.
