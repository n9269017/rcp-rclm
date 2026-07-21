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

## C. Typed mutation program and immutable budget

- [x] The program records objective, update classes, training policy, data selection,
      architecture mutation, resources, expected components, rollback, and successor
      generator/planner generations.
- [x] Canonical ASCII serialization and exact parser round trip are enforced.
- [x] The model cannot write directly into a candidate package.
- [x] Hardened checker, pinned Lean, trust anchor, serializer, hashing, promotion,
      held-out answers, and active ledger history are unaddressable.
- [x] Every invocation is bounded by wall-clock, accelerator, training-step, output-byte,
      candidate-count, and evaluation-call ceilings.

## D. Active-model proposal sequence

- [x] The active predecessor model itself emits proposal bytes.
- [x] Proposals are generated without held-out task identifiers, prompts, source, or answers.
- [x] The first proposal is rejected for an independent resource violation and forbidden
      update class.
- [x] Later invocations are fresh and bound to prior rejection evidence.
- [x] Manual repair count remains zero.

## E. Model-generated candidate lifecycle

- [x] The host realizes alpha from a model-generated typed program through Phase 6.
- [x] Alpha's exact rollback path is verified.
- [x] Alpha is rejected for protected-capability regression after realization.
- [x] The rejection ledger entry leaves the active package hash unchanged.
- [x] A later fresh model invocation produces beta within the original total budget.
- [x] The host realizes beta through Phase 6 with exact rollback.
- [x] Beta retains every predecessor frontier task.
- [x] Beta independently solves one new held-out Lean task.
- [x] Beta satisfies selected entropy/KL/diagonal-QRE obligations.
- [x] Beta satisfies complete Gate D / Phase 9 frontier obligations.
- [x] Phase 7 atomically promotes beta with the unchanged active package as parent.
- [x] The final immutable ledger sequence is two: rejection, then promotion.

## F. Installed successor generator and planner

- [x] The promoted successor's generator bytes differ from the active predecessor's.
- [x] The promoted successor's planner bytes differ from the active predecessor's.
- [x] The successor hashes bind the changed generator and planner artifacts.
- [x] Generation-2 generator and planner files are installed in the immutable promoted package.
- [x] The successor remains ready to produce the next proposal without claiming that it has
      already done so.

## G. Authoritative closure evidence

- [x] Ubuntu, Windows, and macOS recompute byte-identical portable lifecycle evidence.
- [x] Duplicate isolated alpha and beta worker executions reproduce host-expected tensors.
- [x] Frozen Formal Core v2 and complete Formal Core v3 build under the pinned toolchain.
- [x] Proof-token, local-axiom, and selected-information theorem audits pass.
- [x] The pinned run independently executes all three selected Lean tasks.
- [x] The final record binds the rejection ledger, unchanged active hash, promotion parent,
      ledger sequence, and installed generator/planner bytes.
- [x] The terminal workflow records `phase11_exit_closed=true`.

## Closure status

Phase 11 is **complete at its declared selected scope**: one active predecessor model emits
bounded typed programs, one realized model-generated candidate is rejected without changing
the active package, and a later fresh model-generated candidate is promoted with changed
generator and planner policies installed.

The recursive-use condition intentionally remains outside Phase 11. Producing the next
proposal with the modified successor generator is the central Phase 12 condition.
