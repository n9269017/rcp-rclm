# Phase 13 exit criteria

## Phase 13A — replay boundary and attack grammar

- [x] Replay-only contract is canonical and hashed.
- [x] Training, generator, and planner invocation counts are fixed to zero.
- [x] Forbidden learned-module and worker-path registries are frozen.
- [x] Replay source guard rejects training, generation, dynamic loading, network access, nondeterministic imports, and direct learned-worker calls.
- [x] Retained-evidence manifest is canonical and content-addressed.
- [x] Complete 21-case selected adversarial registry is implemented.
- [x] Every Phase 13A attack rejects deterministically with its expected reason code.
- [x] Phase 12 source completeness is independently audited and reported.
- [x] `phase13a_slice_closed=true` remains distinct from full Phase 13 closure.

## Phase 13B — worker-free structural trajectory replay

- [x] Retain immutable `M0` through `M4` packages, raw proposal evidence, rollback archives, the promotion store, and the closed Phase 12 report.
- [x] Content-address every retained byte and bind the bundle to one 40-character source head.
- [x] Track transport-sensitive empty directories so ZIP artifact transport cannot silently alter the promotion-store layout.
- [x] Exclude the original training, generator, planner, proposal-scaffold, optimizer-execution, and worker implementations from the trajectory bundle.
- [x] Independently reopen and verify all five model packages, tensor files, adapters, tokenizer data, support manifests, payload trees, and model identities.
- [x] Replay both captured rejection predicates.
- [x] Replay all four accepted candidate realizations from retained Phase 6 selections.
- [x] Verify exact component-change schedules for `M0→M1`, `M1→M2`, `M2→M3`, and `M3→M4`.
- [x] Restore every rollback archive and require byte-identical predecessor recovery.
- [x] Recompute selected Shannon/von Neumann entropy, KL, diagonal-QRE, and Gate D transition evidence.
- [x] Keep replay training, generator, and planner invocation counts equal to zero.

## Phase 13C — pinned formal and immutable-store replay

- [x] Verify the exact seven-entry `bootstrap → reject → promote → reject → promote → promote → promote` ledger.
- [x] Bind all six attempt directories and every artifact hash to the ledger.
- [x] Independently reopen all five immutable promotion-store packages and verify their parent links and substantive component sets.
- [x] Recompute all seven task certifications with pinned Lean.
- [x] Regenerate the four Gate B Lean programs and enforce the proof-token source guard.
- [x] Recompute all four hardened-checker verdicts without invoking learned workers.
- [x] Normalize only compiler duration and platform runtime identity when comparing cross-platform semantic evidence; toolchain, mathlib, project pin, generated source, and checker acceptance remain mandatory.
- [x] Require byte-identical tool and repository entry points.

## Full Phase 13 closure

- [x] Run complete structural replay on Linux, Windows, and macOS.
- [x] Run pinned Lean task and hardened-checker replay on Linux, Windows, and macOS.
- [x] Require one common bundle manifest, structural report, Phase 13A report, pinned semantic report, and exact source head across all six platform reports.
- [x] Validate the final record against Draft 2020-12 JSON Schema.
- [x] Permit only the final cross-platform aggregator to emit `phase13_exit_closed=true` and `next_phase=14`.

A source commit is closed only when the permanent `Runtime v3 Phase 13 independent replay and adversarial closure` workflow produces its accepted final artifact. Intermediate Phase 13A, structural, and pinned reports deliberately retain `phase13_exit_closed=false`.
