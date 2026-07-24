# Phase 13 — Independent replay and adversarial closure

Phase 13 removes learned execution from the reproducer and asks whether the retained `M0 → M4` trajectory can be rederived from immutable evidence under an exact source binding.

## Trust boundary

The trajectory bundle contains only:

```text
manifest.json
source_binding.json
phase12_closure.json
trajectory/promotion_evidence/
trajectory/reference/
trajectory/store/
```

Training workers, generator workers, planner execution, proposal scaffolds, optimizer execution, PyTorch, dynamic loading, network access, and direct candidate mutation are not included. Every regular file is recorded by path, byte length, and SHA-256. Empty directories required by the promotion-store contract are separately hashed because ordinary ZIP transport can omit them; the verifier may rematerialize only those declared empty paths.

The selected replay contract requires:

```text
training invocations = 0
generator invocations = 0
planner invocations = 0
forbidden learned modules loaded = []
forbidden worker paths retained = []
```

## Phase 13A: adversarial grammar

The frozen selected attack suite contains 21 cases covering held-out leakage, answer access, manifest substitution, capability-ledger forgery, solved-task deletion, evaluation cherry picking, goal drift, model/tokenizer and adapter/base mismatch, architecture forgery, generator substitution, unbound external models, disguised trainer replay, poisoned retrieval, self-reported capability, memorization markers, resource evasion, dynamic loading, post-check mutation, parent substitution, and dependence on the original learned modules.

Each attack is executed twice. Acceptance requires byte-hash determinism and the exact fail-closed reason code.

## Phase 13B: structural trajectory replay

The worker-free structural verifier independently:

1. reopens `M0`, `M1`, `M2`, `M3`, and `M4`;
2. verifies every package manifest, model identity, tensor tree, adapter graph, tokenizer artifact, support policy, and payload-tree hash;
3. replays the two retained invalid-proposal predicates;
4. reopens all four Phase 6 selections and checks their exact substantive component schedules;
5. restores every rollback archive and compares the restored predecessor tree byte-for-byte;
6. recomputes the four selected entropy/KL/diagonal-QRE reports; and
7. recomputes the four semantic and retained Gate D transitions.

This stage does not import or invoke the original training, generator, or planner implementations.

## Phase 13C: immutable store and pinned formal replay

The store verifier reconstructs the Phase 12 controller policy independently and verifies the exact seven-entry ledger:

```text
bootstrap
rejection
promotion M0→M1
rejection
promotion M1→M2
promotion M2→M3
promotion M3→M4
```

All six attempt reports are hash-bound to their artifact sets and ledger entries. Rejections must preserve the active package. Promotions must bind the realized candidate tree, immutable evidence copy, parent package, active-pointer history, and expected substantive component set.

The pinned formal verifier then:

- decodes and recompiles all seven retained Lean tasks;
- binds every result to the final task-ledger certificate;
- regenerates each accepted transition’s Gate B Lean source;
- runs the proof-token source guard;
- recompiles with the pinned Lean/mathlib project;
- recomputes the logical evaluation and hardened checker; and
- requires the candidate tree to remain unchanged.

Cross-platform semantic comparison removes only measured compiler duration and the host-specific toolchain runtime identity hash. The pinned toolchain string, mathlib commit, formal project pin, generated source hash, theorem surface, compiler exit, and checker verdict remain checked on every operating system.

## Cross-platform closure

One capture job reconstructs closed Phase 12 evidence and emits a source-bound content-addressed bundle. Linux, Windows, and macOS each run:

- the independent structural replay; and
- the pinned Lean, task-ledger, immutable-store, and hardened-checker replay.

Tool and repository entry points must be byte-identical on each platform. The final aggregator rejects unless all six reports bind one source head, bundle manifest, structural report, Phase 13A report, and pinned semantic report.

Only that aggregator may emit:

```text
phase13_exit_closed = true
next_phase = 14
```
