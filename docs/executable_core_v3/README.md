# Executable Core v3 documentation

Executable Core v3 implements the learned capability-frontier refinement introduced by
Formal Core v3 Gate D.

## Current status

```text
Phase 9 — learned-language-model refinement contract: complete and merged
Phase 10 — real compact language-model substrate: in progress
Phase 10A — canonical 13.2M transformer package and zero-LoRA extension: implemented, under CI validation
Phase 11 — autonomous experiment planner and generator: not started
Phase 12 — self-hosted multi-generation recursion: not started
Phase 13 — independent replay and adversarial closure: not started
```

## Phase 9

Phase 9 freezes:

- the selected compact decoder-only transformer family;
- the selected Lean theorem-completion task class;
- canonical learned state, update, certificate, task-ledger, and held-out-policy records;
- the Lean ↔ JSON Schema ↔ immutable Python correspondence;
- exact frontier retention and strict expansion semantics;
- active-generator and proposal-protocol hash inclusion;
- held-out task and reference-answer isolation;
- the claim boundary before any larger learned model is trained.

Phase 9 does not train or promote a compact language model.

## Phase 10A

The first Phase 10 slice freezes and executes:

- `rclm-compact-decoder-13m-v1`, a 13,195,840-parameter decoder-only transformer;
- a fixed 260-token UTF-8 byte tokenizer;
- canonical little-endian `int16` tensor and package manifests;
- exact Phase 9 model-identity reconstruction;
- a rank-8 zero-output LoRA extension with 430,080 adapter parameters;
- exact structural recovery and Lean zero-output preservation theorems;
- deterministic package construction, validation, mutation rejection, and schema checks.

The generated reference weights are structural zeros. Phase 10A establishes the package
substrate, not the learned-successor exit criterion.

## Reading order

```text
1. PHASE_9_CONTRACT.md
2. PHASE_9_HELDOUT_POLICY.md
3. PHASE_9_OBJECT_MAP.md
4. PHASE_9_EXIT_CRITERIA.md
5. PHASE_9_VALIDATION.md
6. PHASE_10_SUBSTRATE.md
7. PHASE_10_EXIT_CRITERIA.md
8. PHASE_10_VALIDATION.md
```
