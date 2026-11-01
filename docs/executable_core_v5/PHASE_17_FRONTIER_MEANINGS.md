# Phase 17J — explicit task meanings and a sound selected-frontier layer

Development increment after `97bd7b334be7b91aa87f9965180e5522dce14a3b` (Phase17I).
Keep PR #68 draft and unmerged. This is not a phase-exit, full-root acceptance,
recursive-productivity closure, or live-improvement result.

## Why this increment exists

The immutable v3 `Learned.FrontierKernel` has three distinct fields:
`frontier : State → Finset Task`, `solves : State → Task → Prop`, and
`frontierSound : task ∈ frontier state → solves state task`.
A retained list of task identifiers is not an implementation of task soundness.
Phase17I's component binding and finite-set retention did not supply that field.

This increment constructs a fixed catalog from pinned historical evidence and
an externally anchored, independently replayed sealed transcript. It checks the
physical predecessor and prospective candidate separately. A filtered frontier
admits only catalog tasks whose executable checks pass. Lean proof constructors
connect those checks to explicit task propositions, then provide the actual
three fields through a parameterized `Learned.FrontierKernel` adapter.

The adapter still takes the remaining kernel and its observation function as
parameters. It is NOT a complete concrete learned kernel or accepted step.

## Catalog and original task scopes

The selected predecessor catalog contains exactly 21 task identifiers:

| Type | Count | Meaning and evidence |
| --- | ---: | --- |
| Inherited theorem task | 13 | Exact decoded proof-source and decode binding from the actual package, plus the proposition checked by Lean |
| Phase16 vector task | 8 | The historical installed program, its original single four-integer input, and output bound to the original expected hash |
| Prospective Phase17 task | 1 new | At least one installed program in the selected family matches all eight sealed evaluator probes |

The eight historical vector meanings remain **single-input** contracts. They
are not silently upgraded to all-input semantic equivalence. The new vector
task remains an eight-probe contract. The historical catalog SHA-256 is pinned
so relabeling or changing an inherited oracle cannot masquerade as retention.
The new task name is bound to the sealed challenge commitment; its targets come
from the evaluator specification, not a candidate-supplied success record.

The catalog has 22 unique string identifiers. Its Lean selected certificate
uses an explicit nonduplicated index-to-identifier list. Unknown indices have a
rejecting meaning. Unknown identifiers cannot enter the Python catalog.

The positive candidate is the public synthetic known-answer fixture already
used in Phases17D-I. This run does not generate a new hidden challenge, train a
model, discover a live capability improvement, or promote an active successor.

## Physical checks

`prepare_meanings` independently reconstructs the Phase17F successor packet,
materialized before/after package identities, installed program registry, and
sealed-transcript bindings. It calls the existing capability evaluator on each
physical package. Thirteen model-decoded source observations must agree with
the pinned historical theorem identities. The fixed program interpreter
reexecutes the vector checks. Removing an observation, changing a target,
substituting a package or anchor, or altering canonical packet bytes rejects.

`check_task` does not accept `passed=true` or a report as an input. For proof
tasks, its Python part checks observation identity only; the corresponding
proposition must additionally be proved by the separate real Lean gate.

## Formal layer

`TaskFrontier.lean` contains a `Meaning` with an executable Boolean check, an
explicit proposition, and a proof that a true check implies that proposition.
The theorem constructor requires an actual proof argument, not a proof-pass
Boolean. Vector constructors use a separately structured Lean implementation of
the unchanged bounded integer program semantics. The checked frontier filters
an externally declared finite set through these meaning-specific checks.

Eight new audit targets cover generic checked-frontier soundness, the actual
root field adapter, the selected before/after soundness, retention and strict
finite expansion, predecessor rejection of the new probe task, and nonduplicated
catalog correspondence. The combined source also rechecks all 13 inherited
theorem propositions because they are proof arguments used by this new layer.
These are **13 inherited propositions rechecked**, not 13 new capabilities.
The 172 Phase17H plan proofs are not rerun or counted again.

The real compiler must accept the positive source and then reject two separate
controls: one altered target in the new vector contract, and one altered
candidate proof observation. A timeout, crash, missing compiler, admitted proof,
wrong theorem inventory, unexpected output, or unapproved axiom cannot satisfy
these checks. No test-mode or preparation-only fallback authorizes installation.

## Explicit trusted bindings and nonclaims

Lean does not formally establish the Python neural decoder, file/archive parser,
physical measurement, source/hash extraction, or the physical-model-to-observation
projection. Those are reexecuted and checked externally, but remain trusted
bindings. Trusted Lean/toolchain/import caches remain required. The finite DSL
checks are not a universal proof of equivalence of the Python and Lean interpreters.

The adapter's remaining kernel fields still require concrete compatible semantics
and witnesses: generator/proposal provenance, goal and information interpretation,
resources, recursive productivity, durable challenges/history, and active atomic
promotion/rollback. No complete operational recursive task is newly closed here.

Always retain:

```
root_transition_verified = false
recursive_productivity_recertified = false
full_frontier_recertified = false
full_learned_semantic_refinement = false
neural_decoder_formally_verified = false
complete_resource_accounting = false
promotion_authorized = false
promotion_performed = false
live_capability_gain_demonstrated = false
phase17_exit_closed = false
gate_e_closed = false
egc0_started = false
```

## Reproduction and evidence

Run `scripts/run_phase17_frontier_meaning_tests.py` for the 70 tests (62 original plus eight renderer regressions).
The application kit also requires the unchanged 36-test Phase17F suite.
`run_phase17_frontier_meaning_gate.py --test-fixture --require-lean
--lean-workspace <prepared formal-root> --output <new external directory>`
executes the physical pipeline and real pinned proof checks. It does not install
tools or fetch dependencies. A source-only preparation mode is available, but is
explicitly not a formal pass and is rejected by the application helper.

The kit creates a short-path separate clone at the exact base, uses canonical
Git-blob checksums and literal NUL-delimited staging, retains source-bound command
logs and negative controls, and advances/pushes normally only after validation.
No reset, amend, force-push, merge to main, release/DOI change, or hosted CI claim.
Local Windows results remain distinct from independent or cross-platform replay.
