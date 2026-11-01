# Phase 17F — prospective successor evidence and conditional root binding

Status: implementation increment, not Phase 17 closure. Base source is
`45dc3e1613f74357bf25e57ae67beb4f598ebf06`. The pinned v2/v3/v4 root source,
Lean 4.31.0 toolchain, Mathlib revision, and prior results are unchanged.

## Production computation

`prepare_successor` accepts the authenticated historical Phase 16 predecessor,
two physical package receipts, pinned historical archives, and a sealed Phase
17C transcript with an externally retained SHA-256. It independently replays
the transcript and measures both physical packages. Candidate-authored success
reports are not acceptance inputs. Search exhaustion and partial resource stops
cannot produce a prospective successor packet.

The selected implementation supports exactly one inactive registry extension
from the chosen historical predecessor. It compares 173 protected files byte
for byte (164 inherited model-package files, eight installed bounded programs,
and the historical state). The only changes are one additional bounded-program
file plus the two independently reconstructed package/registry metadata files.
Removing that file and restoring the old metadata reconstructs the predecessor
exactly. This is a structural projection, not an executed active-store rollback.

The candidate artifact must be the descriptor frozen in the anchored transcript.
The physical program is reevaluated on all eight sealed probes using the
independent matrix interpreter. Inherited programs in the selected family must
fail to reproduce the target on those probes. The current objective and the
complete 32-program grammar are recomputed without future-route inputs. The
inherited 21-task capability profile is freshly evaluated on the candidate.

The packet records an 8-to-9 program relation and a 21-to-22 PROSPECTIVE finite
capability relation. No active state, accepted successor identity, promotion
pointer, or trusted frontier is modified. The novelty claim is restricted to the
finite probes and the inherited same-family registry, not every possible
predecessor computation or general intelligence.

## Recursive-productivity obligations are not labels alone

Every one of the selected predecessor's 19 recursive-frontier labels is listed.
Three scoped probes are recomputed: the current fixed 32-program grammar, initial
package-conditioned family choice using the physically present inherited planner,
and two actual inherited multi-token planner decodes. The remaining 16 labels
are marked `operational_recertification_pending`. Even those three probes do not
establish the full operational meaning of the corresponding recursive abilities.
Every row therefore retains `full_task_semantics_recertified = false`.

No new recursive label is added simply because a candidate uses a particular
update-family name. Recursive expansion is not claimed.

## Immutable-root obligation inventory

The packet enumerates the actual 35 fields of the existing root structures:
11 `RCP.StepObligations`, 12 `Learned.SpecificObligations`, and 12
`Autonomous.SpecificObligations`. Tests compare that inventory with the actual
pinned source declarations. Each field distinguishes supporting measured evidence
from a discharged complete premise; none is relabeled as fully discharged.

Remaining gaps include the concrete base-kernel state/refinement and admissibility
proof, quantitative residual/information/goal/reality obligations, generator
refinement, full operational recursive-frontier soundness, durable history/fresh
challenge provenance, and complete resource accounting. An internally consistent
hash or finite-set inclusion cannot supply those semantic premises by itself.

## New Lean certificate

`lean/phase17_bridge/SuccessorEvidence.lean` IMPORTS the immutable formal core; it
does not alter its source or broaden its trusted axioms. The evidence compiler
pins this template and emits only bounded string/integer/list literals.

Four named declarations are audited:

- `Phase17Evidence.selected_facts`: the measured finite projection, program and
  capability relations, recursive-label retention, candidate-credit inequality,
  eight candidate outputs, inherited same-family failure, and nonidentity.
- `Phase17Evidence.protected_interpretation`: equal protected projections have
  equal outputs under any fixed deterministic interpretation.
- `Phase17Evidence.root_recursive_frontier_fields`: a conditional link to the
  THREE actual inherited/protected recursive-frontier subset fields. The
  mapping to the root kernel and its operational soundness remain hypotheses.
- `Phase17Evidence.selected_dsl_regression`: 128 finite comparisons between a
  separately structured Lean interpreter and the Python matrix interpreter,
  covering all 32 current grammar programs. This is not a universal interpreter
  equivalence theorem.

A second certificate changes one target integer. The pinned compiler must reject
it, and must accept the original. A timeout or missing executable is not a
successful negative check. All positive outputs must contain exactly the expected
named axiom audits. No `sorry`, added axiom, `native_decide`, test-mode compiler,
or candidate-supplied Lean source is accepted.

Lean checks statements about emitted literals. Python parsing, SHA-256, package
measurement, correct extraction of those literals, the external transcript
anchor, and toolchain/import-cache integrity remain explicit trust assumptions.
This is NOT a proof of `AutonomousAcceptedStep`, nor a boolean authorization for
promotion. It does not instantiate trivial/vacuous root semantics to obtain one.

## Runner and validation

The ordinary command `scripts/run_phase17_successor_tests.py` runs 36 tests. It
uses actual pinned archives and physical packages for integration, and explicitly
mocked compiler responses for gate-control tests. The positive candidate is the
EXISTING `tests_phase17d/fixtures/known_candidate_pass.json` known-answer fixture.
It is deliberately synthetic, not a fresh hidden task, autonomous improvement,
Phase 17 campaign, or EGC result. Live Phase 17C exhaustion remains exhaustion.

`run_phase17_successor_gate.py --test-fixture --output <new-external-dir>` prepares
the packet and sources without formal-success claims. Production formal mode
requires `--require-lean --lean-workspace <existing-formal-root>` and optionally
`--toolchain-root <existing-toolchain>`. It uses the same exclusive tool-cache lock
as Phase17E, performs no installation, and verifies the unchanged pinned root.
First it checks the new finite certificate and negative control. Only then does
it run the 13 inherited capability obligations on the prospective candidate,
using fresh capability execution rather than reusing the predecessor's pass.
Those 13 checks alone do not cover the new candidate probes; the new certificate
checks those separately. Neither is complete recursive-productivity verification.

The distribution installer requires real pinned Lean for both gates. It stages
in a short separate checkout, uses command-scoped Git long-path handling and exact
NUL-delimited filename staging, runs the 36 tests and the existing 35 package/gate
regressions, and retains all new command logs. It advances the development branch
only after successful local validation and an evidence-only commit. It does not
merge PR #68 or alter main, releases, DOIs, workflow/billing settings, or prior
reports. There is no hosted or cross-platform result implied by local execution.

## Nonclaims retained even after a passing incremental run

```
root_transition_verified           = false
recursive_productivity_recertified = false
full_frontier_recertified          = false
promotion_authorized              = false
promotion_performed               = false
phase17_exit_closed                = false
gate_e_closed                     = false
egc0_started                      = false
live_capability_gain_demonstrated  = false
complete_resource_accounting      = false
```

This increment implements and checks a concrete prospective-evidence bridge.
Full semantic discharge, atomic promotion/rollback, durable cross-turn state and
challenge consumption, evolving objectives, autonomous campaigns, and independent
replay remain separate unfinished work. No finite test establishes unbounded RSI.
