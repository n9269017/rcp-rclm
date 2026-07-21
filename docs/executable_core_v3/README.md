# Executable Core v3 documentation

Executable Core v3 implements the learned capability-frontier refinement introduced by
Formal Core v3 Gate D and carries the selected compact learned successor through bounded
proposal, realization, rejection, promotion, and recursive multi-generation lifecycles.

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
Phase 12 — self-hosted multi-generation recursion: in progress
Phase 12A — promoted generation-2 generator used recursively; first stale proposal rejected: complete and merged
Phase 12B — M0 -> M1 model-weight successor and frontier 3 -> 4: complete and merged
Phase 12C — M1 -> M2 memory/retrieval successor and frontier 4 -> 5: implemented at selected slice scope
Phase 12 remaining chain — M2 -> M3 -> M4: open
Phase 13 — broader independent adversarial closure: not started
```

Phase 12A closes the architectural handoff deferred by Phase 11: the promoted successor's own
changed generator is the source of a later proposal. Phase 12B carries a fresh proposal from that
active package through model-weight realization and atomic promotion. Phase 12C uses the generator
and planner inside promoted `M1`, retains a second fail-closed rejection, installs package-bound
memory and retrieval, and promotes `M2`. The complete four-promotion `M0 -> M4` chain remains open.

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

- a host-installed active generator/planner bootstrap, excluded from the autonomous-improvement
  count;
- a canonical typed mutation-program grammar and immutable total budget;
- deterministic active-model proposal invocations with no held-out material;
- rejection of an invalid proposal before realization;
- Phase 6 realization and exact rollback of an alpha candidate;
- rejection of alpha for protected-capability regression while leaving the active package unchanged;
- a fresh beta proposal bound to alpha's rejection evidence;
- duplicate isolated alpha and beta worker execution with host-exact tensor recomputation;
- Phase 6 realization, exact rollback, Gate D, pinned Lean, and hardened verification of beta;
- Phase 7 atomic promotion with the unchanged active package as parent;
- generation-2 generator and planner bytes installed inside the immutable promoted package;
- a terminal `phase11_exit_closed=true` record.

`phase_11_closure_manifest.json` keeps portable semantic identities separate from exact-run
Phase 6, ledger, promotion, and installed-byte evidence.

## Phase 12A recursive start

The first Phase 12 slice:

- reconstructs and binds the promoted Phase 11 semantic package;
- uses the promoted generation-2 successor to emit the next typed mutation program;
- independently replays the exact model decode;
- rejects the stale generator/planner-generation request;
- proves the active package tree is unchanged;
- consumes no held-out material and permits no manual repair.

This is the first recursive use of a modified successor generator in the project.

## Phase 12B first accepted promotion

The second Phase 12 slice:

- produces a fresh rejection-conditioned proposal from the unchanged active package;
- selects only the `model_weights` transition slot;
- runs duplicate isolated untrusted training and host-exact tensor recomputation;
- realizes `M1` through Phase 6 and verifies exact rollback;
- retains all three tasks in `F0`;
- certifies `lean.phase12.generation1.le_refl_macro`;
- satisfies selected KL/QRE, Gate D / Phase 9, pinned Lean, and hardened-checker obligations;
- records the Phase 12A rejection without moving the active pointer;
- atomically promotes `M1` with `M0` as parent;
- advances the frontier from cardinality three to four.

The generation-2 generator and planner remain active inside `M1`.

## Phase 12C memory and retrieval promotion

The third Phase 12 slice:

- uses the generator and planner inside promoted `M1` as the authoritative proposal source;
- rejects a retrieval-only proposal because the frozen schedule also requires memory-state change;
- leaves `M1` unchanged after that second rejection;
- produces a fresh `memory_update + retrieval_update` program with zero training steps;
- installs one package-bound memory entry and one exact-marker retrieval rule;
- realizes `M2` through Phase 6 and verifies exact rollback to `M1`;
- retains every task in the four-element `F1` frontier;
- certifies `lean.phase12.generation2.zero_le_macro` through retrieval-assisted deterministic decoding and pinned Lean;
- accepts selected KL/QRE non-regression and a strict new-task information witness;
- accepts Gate D / Phase 9 with exactly `memory_state` and `retrieval_policy` changed;
- appends the second rejection without moving the active pointer;
- atomically promotes `M2` with the unchanged `M1` store package as parent;
- verifies the installed memory/retrieval bytes and unchanged generation-2 generator/planner;
- advances the frontier from cardinality four to five;
- reaches two accepted promotions, two retained rejections, and zero manual repairs.

No PyTorch or other training backend is used for `M1 -> M2`. The new semantic capability comes
from independently verified composition of the unchanged compact model with changed package-bound
memory and retrieval components.

## Full Phase 12 boundary

Two accepted promotions remain under the original total budget:

```text
M2 -> M3  generator and planner self-modification
M3 -> M4  typed architecture or adapter and optimizer modification
```

The generator inside each promoted package must be the source of the following proposal. Every
accepted transition must retain its predecessor frontier, add one newly certified Lean task,
satisfy selected information and resource obligations, and preserve the immutable trust boundary.

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
14. PHASE_12_RECURSION.md
15. PHASE_12_EXIT_CRITERIA.md
16. PHASE_12_VALIDATION.md
```
