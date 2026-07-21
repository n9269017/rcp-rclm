# Executable Core v3 documentation

Executable Core v3 implements the learned capability-frontier refinement introduced by
Formal Core v3 Gate D and carries the selected compact learned successor through bounded
proposal, realization, rejection, and promotion lifecycles.

## Current status

```text
Phase 9 — learned-language-model refinement contract: complete and merged
Phase 10 — promoted compact-language-model successor: complete at declared selected scope
Phase 10A — canonical 13.2M transformer package and zero-LoRA extension: complete
Phase 10B — learned sparse execution, Lean frontier expansion, and KL/QRE evidence: complete
Phase 10 lifecycle — Phase 6 realization, Phase 7 promotion, rollback, and worker-free replay: complete
Phase 11 — autonomous experiment planner and generator: complete at declared selected scope
Phase 11A — active-model typed proposal, rejection, and fresh validation: complete historical slice
Phase 11 lifecycle — realized alpha rejection, fresh beta promotion, and generation-2 policy installation: complete
Phase 12 — recursive use of the promoted generation-2 generator: next, not started
Phase 13 — broader independent adversarial closure: not started
```

Phase 11 closes one bounded active-predecessor experiment cycle. It does not claim generic
successor availability, arbitrary native-float model generation, an unbounded learned
trajectory, or recursive use of the newly installed generator. The latter is the central
Phase 12 condition.

## Phase 9

Phase 9 freezes:

- the selected compact decoder-only transformer family;
- the selected Lean theorem-completion task class;
- canonical learned state, update, certificate, task-ledger, and held-out-policy records;
- the Lean ↔ JSON Schema ↔ immutable Python correspondence;
- exact frontier retention and strict expansion semantics;
- active-generator and proposal-protocol hash inclusion;
- held-out task and reference-answer isolation;
- the claim boundary before a compact successor is trained and promoted.

## Phase 10A

The first Phase 10 slice freezes and executes:

- `rclm-compact-decoder-13m-v1`, a 13,195,840-parameter decoder-only transformer;
- a fixed 260-token UTF-8 byte tokenizer;
- canonical little-endian `int16` tensor and package manifests;
- exact Phase 9 model-identity reconstruction;
- a rank-8 zero-output LoRA extension with 430,080 adapter parameters;
- exact structural recovery and Lean zero-output preservation theorems;
- deterministic package construction, validation, mutation rejection, and schema checks.

The Phase 10A reference weights are structural zeros. This slice establishes the package
substrate and conservative architecture-extension boundary.

## Phase 10B

The second slice installs one selected sparse language-model execution profile inside the
same compact package. It adds:

- nontrivial canonical language-model weights;
- a separate untrusted PyTorch CPU SGD worker with two-run replay;
- host-exact integer recomputation of accepted learned tensor bytes;
- deterministic integer decoding with exact dyadic token distributions;
- one retained protected Lean completion and one new held-out Lean completion;
- pinned-Lean certification after candidate freeze;
- certified entropy/KL/diagonal-QRE intervals;
- an accepting Phase 9 learned transition with exact frontier expansion.

The selected profile does not claim general equivalence to arbitrary native-float
transformer execution.

## Full Phase 10 closure

The final Phase 10 lifecycle layer establishes:

- Phase 6 realization of the learned tensor and manifest changes;
- canonical byte-exact rollback restoration;
- inherited pinned-Lean and hardened-checker acceptance;
- complete Gate D / Phase 9 transition acceptance;
- Phase 7 atomic promotion into the content-addressed store;
- physical deletion of the training worker and its entry points before replay;
- independent replay with zero training, generator, and planner invocations;
- a final `phase10_exit_closed=true` workflow record.

Cross-platform validation compares stable semantic hashes only. Environment-bound Phase 6
and lifecycle hashes remain attached to the exact pinned code-proof run rather than being
misclassified as portable model identities.

## Full Phase 11 closure

Phase 11 adds one bounded model-facing experiment controller over the promoted Phase 10
package:

- a host-installed active generator/planner bootstrap, excluded from the autonomous-
  improvement count;
- a canonical typed mutation-program grammar and immutable total budget;
- three deterministic active-model proposal invocations with no held-out material;
- rejection of an invalid, over-budget proposal before realization;
- Phase 6 realization and exact rollback of an alpha candidate;
- rejection of alpha for protected-capability regression while leaving the active package
  unchanged;
- an immutable rejection-ledger entry;
- a fresh beta proposal bound to alpha's rejection evidence;
- duplicate isolated alpha and beta worker execution with host-exact tensor recomputation;
- Phase 6 realization and exact rollback of beta;
- retention of the protected `rfl` and Phase 10 `omega` tasks;
- certification of one new held-out Lean task under the pinned toolchain;
- selected entropy/KL/diagonal-QRE and strict-information obligations;
- complete Gate D / Phase 9 and hardened Gate B acceptance;
- Phase 7 atomic promotion with the unchanged active package as parent;
- ledger sequence number two: rejection followed by promotion;
- generation-2 generator and planner bytes installed inside the immutable promoted package;
- a terminal `phase11_exit_closed=true` record.

`phase_11_closure_manifest.json` keeps two evidence classes separate:

- `stable_reference_hashes` contains only source-deterministic semantic identities that
  recompute across Linux, Windows, and macOS;
- `code_proof.exact_runtime_hashes` retains Phase 6, rejection-observation, certificate,
  ledger, promotion, and installed-byte identities from the exact pinned code-proof run.

This separation is necessary because beta's proposal is intentionally bound to alpha's
realized rejection observation, which includes environment-bound Phase 6 evidence.

## Phase 12 boundary

The promoted successor is self-hosting-ready because its changed generation-2 generator and
planner are installed and cryptographically bound. Phase 11 does not claim that those changed
policies have already emitted another proposal. Phase 12 begins when the promoted successor
itself is used to generate the next bounded experiment program.

## Reading order

```text
1. PHASE_9_CONTRACT.md
2. PHASE_9_HELDOUT_POLICY.md
3. PHASE_9_OBJECT_MAP.md
4. PHASE_9_EXIT_CRITERIA.md
5. PHASE_9_VALIDATION.md
6. PHASE_10_SUBSTRATE.md
7. PHASE_10_LEARNED.md
8. PHASE_10_LIFECYCLE.md
9. PHASE_10_EXIT_CRITERIA.md
10. PHASE_10_VALIDATION.md
11. PHASE_11_GENERATOR.md
12. PHASE_11_EXIT_CRITERIA.md
13. PHASE_11_VALIDATION.md
```
