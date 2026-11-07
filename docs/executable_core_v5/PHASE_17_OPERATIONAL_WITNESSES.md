# Phase 17H — Exhaustive package-bound planner and tool witnesses

Development increment, not complete Phase 17, full RCLM refinement, or Gate E.
Installation base: `4945e6d49aac9ac3751356e68adf010db39bed95` on the existing
draft PR #68 branch. Earlier source, releases, failures, and proof records remain
unchanged. The immutable v2-v4 formal core is not edited.

## Connection to the learned package

The learned root's `PackageState` explicitly separates architecture, weights,
generator, planner, training policy, retrieval, memory, tokenizer, verification
policy, resource policy, and self-model. This increment provides a measured file
projection for those eleven component categories plus an execution-context group.
The extra group binds runtime files, the tool policy, and package metadata.

Every one of the 164 inherited base files must belong to exactly one group. No
file may be ignored, assigned to two groups, added, removed, or changed. Rows
record actual paths, sizes and hashes only after direct predecessor/candidate
byte equality. The groups contain respectively 1, 140, 1, 6, 3, 1, 1, 3, 1, 1,
1, and 5 files. This is input to future full refinement, not itself a constructed
`LearnedAcceptedStep`, a channel theorem, or twelve discharged root premises.

## Two new explicit bounded operational contracts

The following contracts have their own identifiers and canonical content hash:

- `phase17.recursive.multi-token-plan.exhaustive-v1`
- `phase17.recursive.affine-tool.exhaustive-v1`

They provide task-specific evidence for bounded profiles associated with the
inherited `recursive.generate_multi_token_plan` and
`recursive.invoke_package_bound_tool` roles. They do not silently redefine or
fully recertify either historical role in an unrestricted sense. Every one of
the nineteen inherited labels remains separately inventoried; the other
seventeen have no newly executed profile in this increment. Every legacy row
retains `legacy_full_task_semantics_recertified=false`.

The domain is the complete selected parameter domain already admitted by Phase
15's `expected_plan`, not an arbitrary sample:

| Plan domain | Parameters | Queries per physical package |
| --- | --- | ---: |
| Affine integer program | -4 <= a <= 4, a != 0; -8 <= b <= 8 | 136 |
| Natural-number inequality | 0 <= a < b <= 8 | 36 |
| Total | Explicit, canonical ordering | 172 |

Both the actual inherited package and the materialized synthetic candidate run
the existing autoregressive `decode_plan` implementation on every query. Each
produces 1,204 tokens (seven per plan). Neither a training-answer store nor a
candidate-reported success value is consulted.

An independently structured reference decoder reads the actual 32,768 int16
planner parameters and accumulates sparse scores. It uses its own feature
selection, score calculation, tie breaking, token grammar, and plan parsing;
it does not call production prediction, argmax, expected-plan, or decode helpers.
It records deduplicated score traces. Its output must equal the actual model's
output and the independently specified task oracle on every query.

An offline zero-weight reference ablation must fail its selected plan. This is
explicitly a negative control on the reference computation, not a fresh trained
model, an ablated physical-package campaign, or a hardware-independence result.

## Package-bound tool behavior

The actual vocabulary, planner manifest, planner weights and tool policy must
agree with their package bindings. The tool policy must permit the declared
fixed tools, forbid dynamic code loading, and reject authoritative candidate
self-reports. There is no dispatch to an arbitrary executable or Python eval.

For every one of the 136 decoded affine plans, a fixed instruction machine
interprets the decoded MUL, ADD and RETURN instructions on all integers -16
through 16: 4,488 executions per package, 8,976 across predecessor and candidate.
The oracle is the separately supplied task expression a*x+b, not a second call
to the instruction machine. One validated tool session is used per plan. Exact
physical package snapshots are required to remain unchanged during evaluation.

This is host/evaluator dispatch of a model-produced bounded plan through its
allowlisted fixed tool. It does not demonstrate learned arbitrary tool choice,
new tool synthesis, autonomous tool scheduling, or hostile-executable isolation.

## Actual Lean checks required for installation

The source-bound runner freshly reconstructs the physical packages and sealed
Phase 17C transcript bindings, prepares Phase 17F successor facts, and produces
the operational packet. The packet is not accepted merely because it hashes
correctly: an externally anchored serialized packet must equal independent
recomputation byte for byte.

The renderer creates 172 named theorems in `Plans.lean`. In the 136 affine
cases, the program definition uses the coefficients parsed from actual model
tokens while the proposition's right-hand side uses the contract's task oracle.
The theorem quantifies over every integer x. In the 36 inequality cases, the
model-decoded bound is checked and lifted to x+a < x+b for every natural x.

A successful run must compile the positive source with the existing pinned Lean
4.31.0 environment, pass the exact 172-name axiom-audit inventory, and reject a
separate negative source that changes one affine oracle coefficient. Missing
tools, timeouts, wrong theorem names, extra audit output, unapproved axioms,
source mutation, or compiler success on the negative control cannot pass.
The restricted Lean environment retains the resolved Git executable directory.
No dependencies are installed or updated by this increment.

These proofs establish the arithmetic semantics of the generated decoded plans.
They do not prove the Python neural decoder, tool implementation, file parser,
byte-to-literal extraction, or complete learned/root refinement in Lean. The
Python runtime comparisons and trusted physical bindings remain explicit parts
of the result. The trusted toolchain/import-cache assumption is unchanged.

All 172 queries are **public exhaustive recertification cases**. The historical
curriculum partition is not presented as a new holdout. These are neither fresh
hidden challenges nor an EGC benchmark, and no broad generalization is claimed.
The candidate remains the explicitly known-answer synthetic fixture. No live
search, new training, promotion or capability gain is claimed.

## Evidence and integration

The implementation adds `operational_witnesses.py`, `operational_lean.py`, the
Phase 17H tests, and two fixed CLI entry points. All existing runtime and Lean
files remain unchanged. It freshly recomputes the selected predecessor/candidate
facts and the 21 selected Python capability checks through Phase 17F preparation,
but does not rerun or relabel the earlier 13 capability proofs, four finite
successor audits, or six Phase 17G audits.

Preparation mode reports `plan_semantics_gate.status=not_requested` and certifies
no formal contract. The guarded installer mandates real Lean and will not accept
preparation mode. Upon actual success, the separate gate report identifies only
the two explicit bounded contracts as certified. Full legacy-task recertification
remains empty. The prepared packet itself stays immutable and does not acquire
success flags after the compiler runs.

The installer validates in a new short-path local clone, records the source
commit/tree and complete command logs, and retains proof sources, packet, report,
checksums and failure details. The large materialized package directories remain
in the validation workspace rather than being duplicated in the evidence commit.
It refreshes the canonical staged-blob manifest and advances/pushes only after
all 57 new tests, 47 Phase 17G regressions, and the real new formal gate pass.
There is no force push, reset, amendment, main merge, release/DOI change or Actions
request. New commits use `[skip ci]`; local success is not hosted-CI success.

## Completion boundary

```
root_transition_verified           = false
recursive_productivity_recertified = false
full_frontier_recertified          = false
full_learned_semantic_refinement   = false
neural_decoder_formally_verified   = false
complete_resource_accounting       = false
promotion_authorized              = false
promotion_performed               = false
live_capability_gain_demonstrated  = false
phase17_exit_closed                = false
gate_e_closed                     = false
egc0_started                      = false
```

Full information/coherence/learned semantic refinement, the remaining operational
recursive witnesses and their integration into the immutable root, durable
challenge/history binding, full resources, active promotion/rollback, cross-turn
objectives and continuation, campaigns, and required independent/platform evidence
remain open. Keep PR #68 draft and unmerged.
