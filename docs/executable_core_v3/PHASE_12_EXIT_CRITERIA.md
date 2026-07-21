# Phase 12 exit criteria

## Phase 12A recursive-start slice

- [x] Phase 11 is merged and named as the Phase 12 dependency.
- [x] The retained Phase 11 closure manifest is loaded fail-closed.
- [x] The reconstructed active package matches the retained beta package identity.
- [x] The reconstructed active model matches the retained beta model identity.
- [x] The active generator matches the retained generation-2 successor generator identity.
- [x] The active planner matches the retained generation-2 successor planner identity.
- [x] The active generator policy has next-proposal authority.
- [x] The active generator remains unable to write a candidate directly.
- [x] Held-out task and answer material remain unavailable to generation.
- [x] The complete Phase 12 total budget is frozen before execution.
- [x] The four-transition component schedule is frozen before execution.
- [x] The promoted generation-2 successor emits the first Phase 12 typed program.
- [x] The decode is deterministic and independently replayed.
- [x] The first program is rejected for a stale generator/planner generation request.
- [x] No candidate realization occurs for the rejected program.
- [x] The active package tree is unchanged after rejection.
- [x] Manual repair count is zero.
- [x] Phase 12A declares zero accepted promotions and zero frontier expansions.
- [x] Phase 12A keeps `phase12_exit_closed=false`.

## Phase 12B first-promotion slice

- [x] A fresh proposal is produced after the Phase 12A rejection under the original total budget.
- [x] The proposal is bound to the generator and planner inside the unchanged generation-2 active package.
- [x] The prior rejected draft and its immutable validation report are inputs to the fresh invocation.
- [x] The active package's bounded planner projects the first scheduled update class without operator repair.
- [x] The canonical fresh program selects only `weight_update` / `model_weights`.
- [x] The fresh proposal is deterministic and independently replayed.
- [x] Held-out task IDs, prompts, source, and reference answers remain unavailable to generation and training.
- [x] Duplicate isolated untrusted training runs reproduce the host-exact candidate tensor.
- [x] `M0 -> M1` is realized through the inherited Phase 6 boundary.
- [x] The Phase 6 rollback archive restores `M0` exactly.
- [x] `M1` retains all three tasks in `F0`.
- [x] `M1` solves one new independently certified held-out Lean task.
- [x] The selected information report proves protected KL/QRE non-regression and a strict new-task witness.
- [x] The complete Gate D / Phase 9 transition accepts with `changed_components = {model_weights}`.
- [x] Pinned Lean verifies the retained and new task frontier after candidate freeze.
- [x] The inherited Gate B Lean bridge and hardened checker accept.
- [x] The Phase 12A rejected attempt is written to the immutable Phase 7 ledger without moving the active pointer.
- [x] `M1` is atomically promoted with the unchanged `M0` store package as parent.
- [x] The reopened immutable promoted package contains the expected semantic `M1` package.
- [x] The generation-2 generator and planner remain installed unchanged for `M1 -> M2`.
- [x] The certified frontier satisfies `F0 ⊊ F1` and `|F1| = 4`.
- [x] The completed prefix records two generator invocations, one rejection, one realization, one evaluation, one promotion, one frontier expansion, and zero manual repairs.
- [x] Linux, Windows, macOS, isolated training, pinned Lean, and hardened-checker validation pass at one code-proof head.
- [x] Phase 12B emits `phase12b_first_promotion_closed=true`.
- [x] Phase 12B correctly keeps `phase12_exit_closed=false`.

## Phase 12C memory and retrieval promotion

- [x] The generator and planner inside promoted `M1` produce the authoritative next proposals.
- [x] A retrieval-only proposal is rejected for incomplete component coverage.
- [x] The second rejected attempt leaves the active `M1` package unchanged.
- [x] A fresh rejection-conditioned memory/retrieval proposal is generated under the original budget.
- [x] The canonical accepted program selects `memory_update` and `retrieval_update` only.
- [x] No model training is invoked for `M1 -> M2`.
- [x] `M1 -> M2` is realized through the inherited Phase 6 boundary.
- [x] The Phase 6 rollback archive restores `M1` exactly.
- [x] `M2` retains all four tasks in `F1`.
- [x] `M2` solves one new retrieval-backed held-out Lean task.
- [x] The selected information report proves protected KL/QRE non-regression and a strict new-task witness.
- [x] The complete Gate D / Phase 9 transition accepts with `changed_components = {memory_state, retrieval_policy}`.
- [x] Pinned Lean verifies the five-task frontier after candidate freeze.
- [x] The inherited Gate B Lean bridge and hardened checker accept.
- [x] The second rejected attempt is written to the immutable Phase 7 ledger without moving the active pointer.
- [x] `M2` is atomically promoted with the unchanged `M1` store package as parent.
- [x] The reopened immutable promoted package contains the expected memory and retrieval bytes.
- [x] The generation-2 generator and planner remain installed unchanged for `M2 -> M3`.
- [x] The certified frontier satisfies `F1 ⊊ F2` and `|F2| = 5`.
- [x] The cumulative prefix records four generator invocations, two rejections, two realizations, two evaluations, two promotions, two frontier expansions, and zero manual repairs.
- [x] Phase 12C emits `phase12c_memory_retrieval_promotion_closed=true`.
- [x] Phase 12C correctly keeps `phase12_exit_closed=false`.

## Remaining full Phase 12 trajectory

- [x] A fresh proposal is produced after the first rejection under the original total budget.
- [x] The fresh proposal is produced by the generator/planner inside the unchanged active package.
- [x] `M0 -> M1` is realized, independently verified, and atomically promoted.
- [x] `M0 -> M1` contains a genuine model-weight update.
- [x] The generator inside `M1` produces the authoritative proposal for `M1 -> M2`.
- [x] `M1 -> M2` is realized, independently verified, and atomically promoted.
- [x] `M1 -> M2` contains a substantive memory and retrieval update.
- [ ] The generator inside `M2` produces the authoritative proposal for `M2 -> M3`.
- [ ] `M2 -> M3` is realized, independently verified, and atomically promoted.
- [ ] `M2 -> M3` contains a generator/planner self-modification.
- [ ] The modified generator inside `M3` produces the authoritative proposal for `M3 -> M4`.
- [ ] `M3 -> M4` is realized, independently verified, and atomically promoted.
- [ ] `M3 -> M4` contains a typed architecture or adapter and optimizer modification.
- [ ] Every accepted successor retains all tasks in its predecessor frontier.
- [ ] Every accepted successor adds one newly certified held-out Lean task.
- [ ] The certified frontiers satisfy `F0 ⊊ F1 ⊊ F2 ⊊ F3 ⊊ F4`.
- [ ] The final frontier satisfies `|F4| >= |F0| + 4`.
- [ ] Every accepted transition satisfies selected entropy/KL/diagonal-QRE obligations.
- [ ] Every transition remains within the precommitted resource budget.
- [ ] Every transition satisfies the selected goal-drift bound.
- [x] At least two rejected attempts are retained without changing the active package.
- [ ] The total manual repair count is zero for the complete four-promotion run.
- [ ] No operator modification occurs between attempts in the complete authoritative run.
- [ ] The complete chain passes Linux, Windows, and macOS validation.
- [ ] The complete chain passes pinned Lean and hardened-checker validation.
- [ ] The final workflow emits `phase12_exit_closed=true`.

## Explicit non-claims

Phase 12 does not close merely because two recursive promotions have succeeded. Full closure
requires all four accepted promotions and strict frontier expansions. Even after full Phase 12
closure, generic successor availability, autonomous unbounded RSI, and the conditional infinite
premise remain separate claims.
