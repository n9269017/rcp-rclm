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

## Full Phase 12 trajectory

- [ ] A fresh proposal is produced after the first rejection under the original total budget.
- [ ] The fresh proposal is produced by the generator/planner inside the unchanged active package.
- [ ] `M0 -> M1` is realized, independently verified, and atomically promoted.
- [ ] `M0 -> M1` contains a genuine model-weight update.
- [ ] The generator inside `M1` produces the authoritative proposal for `M1 -> M2`.
- [ ] `M1 -> M2` is realized, independently verified, and atomically promoted.
- [ ] `M1 -> M2` contains a substantive memory or retrieval update.
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
- [ ] At least two rejected attempts are retained without changing the active package.
- [ ] The total manual repair count is zero.
- [ ] No operator modification occurs between attempts in the authoritative run.
- [ ] The complete chain passes Linux, Windows, and macOS validation.
- [ ] The complete chain passes pinned Lean and hardened-checker validation.
- [ ] The final workflow emits `phase12_exit_closed=true`.

## Explicit non-claims

Phase 12 does not close merely because one recursive proposal has been emitted. Full closure
requires all four accepted promotions and strict frontier expansions. Even after full Phase 12
closure, generic successor availability, autonomous unbounded RSI, and the conditional infinite
premise remain separate claims.
