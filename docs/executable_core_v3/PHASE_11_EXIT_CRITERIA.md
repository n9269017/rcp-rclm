# Phase 11 exit criteria

## A. Phase 10 dependency

- [x] Phase 10 is merged and complete at its declared selected scope.
- [x] The active package retains the Phase 10 compact-model family and task frontier.
- [x] The Runtime v2 checker, serializer, hashing, realization, promotion, and ledger
      authorities remain outside the learned package.

## B. Active-generator bootstrap

- [x] A bounded model-facing generator policy is installed in an active package.
- [x] A bounded model-facing planner policy is installed in the same package.
- [x] Generator, planner, model, package, and proposal-protocol hashes are bound into the
      Phase 9 state identity.
- [x] The Phase 10 protected `rfl` and learned `omega` completions are retained exactly.
- [x] The host-created bootstrap is explicitly excluded from the autonomous-improvement
      count.

## C. Typed mutation program

- [x] The program records objective, update classes, training policy, data selection,
      architecture mutation, resources, expected components, rollback, and successor
      generator/planner generations.
- [x] Canonical ASCII serialization and exact parser round trip are enforced.
- [x] The model cannot write directly into a candidate package.
- [x] Hardened checker, pinned Lean, trust anchor, serializer, hashing, promotion,
      held-out answers, and active ledger history are unaddressable.
- [x] Every invocation is bounded by wall-clock, accelerator, training-step, output-byte,
      candidate-count, and evaluation-call ceilings.

## D. Phase 11A active-model proposal sequence

- [x] The active predecessor model itself emits the first proposal bytes.
- [x] The proposal is generated without held-out task identifiers, prompts, source, or
      reference answers.
- [x] The first proposal is rejected by immutable host policy.
- [x] Rejection includes an independent resource violation and forbidden update class.
- [x] A second fresh invocation is bound to the first rejection report.
- [x] The second model output is a different canonical typed program.
- [x] The second program validates under the original fixed budget.
- [x] Manual repair count is zero.
- [x] Ubuntu, Windows, and macOS produce byte-identical stable reference evidence.

## E. Model-generated candidate lifecycle

- [ ] The host realizes a candidate from a model-generated typed program through Phase 6.
- [ ] At least one model-generated candidate is rejected without changing the active package.
- [ ] A later fresh model-generated candidate is accepted within the original total budget.
- [ ] No operator repair occurs between attempts.
- [ ] The accepted candidate satisfies complete Gate D / Phase 9 frontier obligations.
- [ ] Phase 7 atomically promotes the accepted candidate.

## F. Installed successor generator and planner

- [ ] The promoted successor's generator bytes differ from the active predecessor's.
- [ ] The promoted successor's planner bytes differ from the active predecessor's.
- [ ] The successor hashes bind the changed generator and planner artifacts.
- [ ] The changed policies are installed in the active promoted package.
- [ ] The successor remains ready to produce the next proposal without claiming that it has
      already done so.

## Closure status

Phase 11A is **complete at its declared typed-proposal scope**. Full Phase 11 remains in
progress until Sections E–F close at one exact source head.

The recursive-use condition intentionally remains outside Phase 11. Producing the next
proposal with the modified successor generator is the central Phase 12 condition.
