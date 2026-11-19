# Phase 17AE — fixed task interpretation and semantic novelty

## Baseline and purpose

This additive increment starts at completed Phase 17AD evidence commit
`e45af6bc66ed3484b8819ceefbbaf5e4bc8bef6f` on
`agent/rcp-rclm-v5-phase-17-controller`. The retained AD execution is
`artifacts/development/phase17ad/op-1feb4d24e918/gate/execution.json`, with SHA-256
`fe6d0665f2837765cb49e70de4edd204abcc9cfa75575cc1f43d52d84d144d66`.
AD's Windows evidence is complete within its declared scope. Its first accepted
finite step and state-indexed context transport remain the starting point.

AD proved that its selected catalog was saturated: its 22 nonreject meanings
were all in the selected successor's checked frontier. A second strict step
under that unchanged catalog therefore could not be supplied. AE fixes a richer
interpretation before any follow-up selection, proves that it preserves the
established meanings, and strengthens the actual finite kernel with semantic
novelty. It does not construct or select a second accepted candidate.

The new implementation is wholly additive. Inherited Lean templates are read
with exact source pins; the existing runtime, formal root, historical evidence,
and completed AD acceptance contract are retained. PR #68 remains draft and
unmerged.

## One fixed catalog

The catalog has 282 nonreject indices. All indices at or above 282 reject.

| Indices | Meaning | Identity rule |
| --- | --- | --- |
| 0–21 | The established thirteen theorem and nine finite vector meanings | Original meaning values and task names unchanged |
| 22–281 | Universal affine adapter contracts | Fixed slope and offset; no required program hash |
| 282 and above | Rejection | No admitted task outside this fixed palette |

For a variant `v` in `0..3` and an offset coordinate `j` in `0..64`, define

```text
slope  = v + 1
offset = j - 32
index  = 22 + 65*v + j
name   = phase17ae.adapter.affine.<v>.<j>
```

The corresponding behavior maps every component `x` to
`(v + 1)*x + (j - 32)`. Its meaning requires a registered program in family 0,
the existing `adapter_policy` family, with variant below 4 and both integer
parameters in `[-16,16]`. The offset is the difference of those parameters.
There are exactly `4*65 = 260` such slope/offset pairs. Neither a candidate,
objective, nonce, challenge, observed success bit nor desired result is an input
to this catalog definition.

The family qualification is part of the meaning. Other DSL families can express
some of the same functions; AE does not claim globally new functions across all
families. The original legacy meanings retain their original key requirements
where present. Key independence and the affine renaming theorem concern the
new affine tail.

### Universal semantics, probes and realizers

`TaskInterpretation.lean` defines a semantic `Realizes` predicate over all
four-tuples of mathematical integers. The executable check uses the equivalent
bounded adapter normal form. The proofs establish that the zero vector and a
unit vector identify the slope and offset in this declared grammar; agreement
on these probes implies the universal four-input contract. This implication is
a theorem about the affine grammar, not an extrapolation from arbitrary tests.

The inherited `Meaning` type provides soundness only: a successful check implies
its proposition. A failed generic check does not by itself imply semantic
failure. AE separately proves completeness for the selected legacy meanings,
the new affine meanings, and the resulting catalog. This is why the recomputed
false check can support semantic failure for this particular interpretation.

The proofs also establish distinct affine behaviors, injective palette indices,
and a bounded reference realizer for every palette member. One realizer uses
`a = max(-16, min(16, offset))` and `b = a - offset`. These are mathematical
program projections. They have no production candidate identity, search nonce,
installation receipt or acceptance evidence. Bounded syntax realizability does
not establish reachability by the current 32-proposal production sampler.

## Preservation and the actual guarded kernel

The new catalog equals the old catalog pointwise below 22, and the new task-name
function equals the old name function there. For a state whose declarations are
all below 22, its checked frontier is unchanged. The corresponding admissibility
and first-step Facts transport preserve the selected old transaction rather
than retrospectively labeling additional behaviors as its gains.

Let `L` be AD's state-indexed finite learned kernel instantiated with this fixed
richer interpretation. AE constructs an actual base kernel and an actual
`Learned.FrontierKernel`, with the same state, candidate, evidence, root,
protected observations, resource policy, context and charge providers. Its base
reality predicate is strengthened to

```text
old reality containment
and not (fixed catalog[candidate.task]).holds(predecessor observation)
```

The original reality nonuniversality witness remains a witness against this
stronger predicate. The other base fields and all learned fields are retained.
The transport theorems explicitly retain all eleven original base obligations
and all twelve learned obligations; the semantic guard does not replace any of
them.

`accepted_iff` proves guarded acceptance equivalent to AD acceptance in that
same richer configuration together with semantic failure in the predecessor.
`already_solved_rejected` rejects any candidate whose selected fixed meaning
already holds. `accepted_semantic_gain` proves that guarded acceptance implies
both predecessor failure and successor success for that same meaning; successor
success follows from the typed update, admissibility and checked-frontier
soundness. A new declaration alone cannot supply this result.

For a fixed affine meaning, `accepted_affine_program` further extracts the
appended candidate program as a universal-contract witness and proves that no
predecessor registry entry realizes that contract. It derives this from semantic
failure and success together with the typed append, without assuming new program
behavior as an additional premise. The selected already-solved rejection audit
uses this corollary.

For the affine tail, changing a program hash, metadata, or a redundant parameter
representation without changing its slope and offset cannot turn existing
behavior into novelty. The name of an already available task need not have been
declared for the guard to reject credit for it.

`guarded_two_step` is conditional composition in one fixed guarded kernel. It
requires independently supplied first and second Facts bundles and semantic
failure at each source state. It yields both accepted steps, frontier retention,
growth by at least two, and protected-view preservation. It does not assert
that the second bundle, truthful future context, charges or physical execution
exists. Later context and charge providers remain explicit mathematical inputs.

## Selected Q/P reconstruction

Preparation calls `prepare_finite_kernel` directly. It does not call AD's
follow-up objective, continuation controller or next-context selection.

The Python boundary freshly reconstructs the retained selected physical pair
and checks every complete snapshot byte against the fixed manifest anchors
before reducing it to 21 captured images: before/after package manifests, before/after
registry manifests, and all seventeen registered program images across the two
states. Canonical bytes, content hashes, manifest rows and fixed package anchors
bind these images to the inherited finite projections. Uncaptured package bytes
are checked by fresh physical preparation; the serialized image validator does
not claim to reconstruct missing bytes from hashes.

Two existing independently structured interpreters recompute the zero and unit
observations for every registered program. The adapter coefficient
characterization is compared with those observations, and all 260 availability
rows are derived from the fixed catalog. The physical interpreter probes are
within its allowed four-integer domain; the separate Lean theorem covers the
universal mathematical four-input interpretation.

| Selected property | Before | After |
| --- | ---: | ---: |
| Registered program images | 8 | 9 |
| Declared and checked legacy frontier | 21 | 22 |
| Available affine contracts | 1 | 1 |
| Unavailable affine contracts | 259 | 259 |
| Declared affine tasks | 0 | 0 |

The existing adapter has variant 3, `a=11`, `b=1`, so it realizes slope 4,
offset 10, and fixed task index 259. That task is already solved but undeclared
on both sides. The selected theorem and negative controls reject new credit for
that behavior. This separates semantic availability from declared-frontier
membership. The original selected task 21 does fail before and hold after; the
original first accepted finite step is recertified in the richer guarded kernel.
Because its legacy meaning is preserved exactly, this recertification retains
that meaning's original identity requirements. It is not a new claim that the
first step introduced a function unavailable under every other program key.

The 259 unavailable contracts show that AD's particular 22-task saturation is
not a theorem of this richer catalog. They do not establish an accepted
improvement, physical capability gain, successful future search or recursive
productivity.
The enriched catalog is still finite. Its larger bound supplies room for
separately justified steps; it does not prove indefinitely repeatable strict
improvement or eliminate eventual saturation of a fixed finite catalog.

The prepared packet contains canonical bytes and rederivable observations.
Consumers cannot replace its catalog, supply favorable success flags, change a
package identity, or escalate scope by recomputing only the packet's own hash.
The caller must supply the selected predecessor and candidate identities to the
novelty query. The serialized boundary is anchored to this selected pair; it is
not a universal physical-state refinement API.

## Verification and saved evidence

The AE-only test runner checks an exact inventory with no skipped tests. Its
runtime tests cover catalog separation and legacy preservation, all 260 bounded
references, actual byte-image bindings, disagreement between interpreters,
already-solved declarations, renamed behavior, substituted packages/catalogs,
and authority changes. Parser and gate tests exercise refusal behavior; their
synthetic compiler messages cannot create a formal acceptance record.

The real pinned Lean gate uses six compiled modules:

1. `ProposalProvenance`
2. `ControllerContinuation`
3. `FiniteObservationKernel`
4. `SuccessorContext`
5. `TaskInterpretation`
6. `SelectedFiniteKernel`

Each module has an import-resolution stage. One positive certificate and ten
designated negative controls then complete 23 stages. The positive certificate
requests 40 named axiom audits. Only `propext`, `Classical.choice` and `Quot.sound`
are allowed; `sorryAx`, extra diagnostics, missing audits or reordered audits
fail the validator. No historical proof campaign is rerun.

The ten controls are `LegacyMeaningChanged`, `LegacyNameChanged`, `WrongSlope`,
`WrongOffset`, `OutOfBoundsProgram`, `WrongFamily`, `MissingRegistryWitness`,
`AlreadySolvedCredit`, `RenamedProgramCredit`, and `OutsidePalette`. Each must
fail at its designated false assertion after its actual rejection lemma has
compiled. An import failure, unrelated error or nonzero exit alone cannot count
as a successful control.

The gate binds the exact source commit/tree and source hashes, prepared packet,
generated proof bytes, pinned environment, native command results, compiled
objects, import-resolution records and explicit completed-stage parents. Saved
evidence reconstruction regenerates the packet and proof sources and checks the
whole lineage without a compiler or worker run. A lost process handle does not
establish completion or authorize takeover of an interrupted installer.

The immutable sealed application kit must be the same at entry and exit of an
actual application. Linux development applies it in a separate checkout from
the exact completed AD baseline without pushing. The Windows handoff performs
its own full application and, only after its checks succeed, can fast-forward
the controller and push. Source commits, trees and platform records are
attributed separately. The complete execution recovery archive includes
compiled objects and invocations and is retained outside Git. Reuse requires
the source and exact pinned environment; automatic relocation is not asserted.

## Claim boundary and next substantive obligation

The two AE-specific completion flags are
`fixed_task_interpretation_extension_checked` and
`semantic_novelty_guard_checked`. They are set only by the actual complete gate.
The packet and every execution retain the existing exact map of 24 broader
claims as false, including complete root-transition verification, physical
refinement and attestation, full learned/autonomous instantiation, full goal and
information interpretation, complete frontier/productivity recertification,
resource accounting, campaign authority, containment, historical-cost recovery,
promotion, active-store changes, live capability gain, Gate E and Phase 17 exit,
EGC-0, hosted CI, broad cross-platform validation and Phase 18 replay.

AE verification costs are not folded into the inherited reference resource
tariff. No fresh worker, live challenge, follow-up candidate selection or proposal batch,
active model, promotion or second accepted successor is created by this increment.

The next substantive obligation is to construct a separately justified second
strict accepted step against this already fixed interpretation. That requires
an actually unavailable contract, a reachable and authenticated candidate,
truthful successor-bound context and evidence, all inherited base/learned
obligations, predecessor semantic failure and successor success, and separately
justified resource accounting. This document and the conditional composition
theorem do not supply those missing inputs.
