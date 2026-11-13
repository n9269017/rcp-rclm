# Phase 17AD: successor context and one state-indexed finite kernel

## Baseline and purpose

AD starts from the completed AC evidence commit
`99600c67e9e7d0c71d7de5cf09f0d3b5d786ad1a`. AC's Linux and native Windows
results retain their own attribution. PR #68 remains draft and unmerged.

Q constructs an accepted step for one concrete finite observation model. Its
`Configuration.context` is fixed to one transaction. The source package changes
after that step, so the same context cannot satisfy the parent-package premise
for the successor. AC supplies the generic present-prefix controller, but it
does not construct a new source context. AD addresses this context boundary.

There is a second, independent limit: the selected Q catalog defines exactly
22 task meanings, and its selected successor already covers all 22. A new
context cannot create another strict expansion within that saturated catalog.
AD retains the catalog and makes this limit explicit. A second accepted
successor is not an outcome of this increment.

## Formal construction

`SuccessorContext.lean` constructs one `RCP.Kernel` and one
`Learned.FrontierKernel`. Their context and expected charge sequence are indexed
by the current source state. The immutable root, task catalog, task-name
interpretation, protected contract, and resource policy remain fixed.

The base keeps Q's actual update, admissibility, protected quantity, recovery,
progress, and residual functions. It changes only the source-dependent trust,
resource, and structural predicates. It preserves the inherited nonconstant
protected quantity and nonconstant residual witnesses, and separately proves
that the structural predicate is not universal for any choice of providers.

The learned kernel keeps the existing task meanings, sound frontier, goal
distance, information value, and resource functions. Its generator and proposal
bindings use the context of the state being checked. The provider is a
mathematical input; it does not authenticate itself.

The transport theorem proves a bidirectional equivalence between the new
kernel's obligations at a source state and Q's original obligations instantiated
with that state's context and expected charges. Consequently, independently
established Q `Facts` construct the actual `LearnedAcceptedStep` under this
single state-indexed kernel. The theorem does not replace the remaining
premises with an acceptance flag or an unspecified compatible kernel.

Additional theorems require the context's parent to equal the source package,
reject stale-parent reuse, preserve the semantic fields, and show that changing
provider values at other states cannot change acceptance of the present step.
With positive credits and a valid source context, the unchanged AC selector has
an in-range next candidate. Selection does not imply that the candidate passes.

The generic two-step theorem requires two separately supplied, linked `Facts`
bundles. It yields two accepted finite steps under the same kernel, retained
initial frontier, at least two additional frontier elements, and equal
protected views. It is conditional on both fact bundles and is not instantiated
as a second success for the selected fixture.

## Prospective context from the inactive candidate

The Python preparation reconstructs the fixed P/Q predecessor and candidate in
a new external directory. It reopens the anchored archives, staged transaction,
ordered transcript, installed registry, protected observations, and retained
reference-work evidence through the existing Q preparation. It does not launch
a worker or ask an evaluator for a challenge.

The new packet retains 37 complete input images totaling 256,043 bytes,
including canonical manifests, selected registry and historical-state images,
and both complete 65,536-byte planner images. It checks
their identities against the anchored physical packages and Q's typed/task
projections. The actual new program determines the changed family generation.
The installed registry grows from eight to nine entries; the selected frontier
grows from 21 to 22 meanings. The recursive frontier and historical archive
anchor are preserved.

The prospective `ModelState` is an input to the existing Phase 16 search adapter.
Its package field names the measured inactive candidate. It is not an active
store record. A separate prospective history identity binds the parent state,
historical archive root, staged transaction/head, transcript, candidate, added
program, and prospective state. No new accepted archive root is invented.

The additive objective policy recomputes all eight family scores using the
measured 84 nonzero planner weights, the new generation counts, and the current
state/history/nonce. It retains all score terms and tie breaks. It then binds
the unchanged 32-program grammar and ranking adapter to the prospective state.
An independent grammar/score-table implementation must agree with production;
the first decision and checkpoint round trip are checked as well.

The selected next-turn nonce and challenge commitment are explicitly public
synthetic inputs. No opening, future route, target number of improvements,
winning candidate, or stopping time enters this next-context interface. The
public caller API requires the selected state and prospective-history anchors;
it rejects stale anchors and reuse of the retained consumed commitment. It does
not establish the freshness, secrecy, or external authority of a new commitment.
The public API accepts only this validated selected projection. General
repeated-turn construction across arbitrary later model states remains open.

Numerical objective/ranking recomputation and physical extraction are Python
checks. The new Lean certificate checks the supplied successor context's
structural validity, parent binding, selected first decision, and its connection
to the finite state. This increment does not universally verify that Python
implements Lean or extend U/Y's old selected numerical proofs to these new data.
The Lean context uses the supplied prospective-history digest as a literal;
there is no new SHA proof, universal unique-history rule, or
`Autonomous.historyBound` certificate. The Python recomputation supplies the
selected state/history derivation and rejects substitutions.

## Selected formal result and catalog boundary

The selected certificate rechecks Q's original proof bodies as a dependency,
then transports its actual finite accepted step into the new state-indexed
kernel. It supplies the new context for the inactive successor and verifies the
next initial controller decision. Later charge sequences remain explicit
parameters; no future work trace or second candidate fact bundle is invented.

The selected catalog has a reject meaning outside indices 0 through 21. AD
checks the resulting frontier bound and the successor's saturation. Therefore
no provider choice can create a further strictly expanding accepted step under
that exact selected catalog. A larger fixed task interpretation with explicit
soundness and preservation witnesses is a remaining obligation. This does not
authorize arbitrary changes to the fixed improvement language or verifier.

## Proof execution and reconstruction

The gate uses the unchanged AC completed-stage runner and environment capture.
AD's validator fixes its own source inventory, module sequence, named theorem
audits, and ten designated negative controls. Five modules are compiled freshly:
the unchanged provenance and AC controller, the unchanged generic Q template
bodies, the new successor-context module, and Q's selected proof bodies.
Imports are checked against the actual new compiled objects. Historical proof
campaigns and their negative suites are not rerun or relabeled as AD evidence.

Generic templates are factored into modules without changing their definitions
or proofs. Exact original template pins, import inventories, generated source
bytes, compilation outputs, and approved axiom audits are checked. Negative
controls must first prove their wrong claim false and then fail only at the
designated final `False` assertion. Import errors, timeouts, unexpected
diagnostics, and incomplete invocations do not establish a rejection.

The five identity controls (`StaleParent`, `ReusedContext`, `StaleHistory`,
`StaleStateIdentity`, and `WrongGenerator`) refute particular old/new identity
equalities. They do not establish general authentication of those identities.
The other controls check an incorrect next choice, premature root submission,
missing source charges, an unchanged frontier, and an out-of-catalog task.
The separate audited generic stale-parent theorem rejects an accepted step
whose provider's parent differs from the actual source package.

Start with clean committed source and the existing pinned Lean 4.31.0 foundation:

```text
python -B scripts/run_phase17_successor_context_tests.py
python -B scripts/run_phase17_successor_context_gate.py --test-fixture --require-lean --lean-workspace <prepared-root> --toolchain-root <lean-4.31.0> --output <new-external-output>
```

The gate retains the plan hash and each completed invocation's hash. Its
`--one-stage`, `--resume-from`, `--expected-parent-sha256`, and
`--expected-plan-sha256` options preserve AC's explicit continuation contract.
No incomplete stage is reused. Source/tool/foundation paths and bytes remain
bound; a lost host must restore them or begin a separately attributed plan.

Saved-evidence verification reconstructs the physical inputs and generated
proofs, then checks the retained completed lineage without invoking Lean or
workers:

```text
python -B scripts/run_phase17_successor_context_gate.py --verify-only --output <same-output> --expected-execution-sha256 <saved-hash>
```

## Acceptance and remaining work

Acceptance requires all 97 Python tests without skips,
fresh preparation, all 21 formal stages, the exact 38 named audits, ten intended
negative rejections, unchanged inputs, and saved-evidence reconstruction.
Controlled installer and subprocess tests are separately attributed and never
stand in for actual Lean acceptance.

The two narrow AD results are `successor_context_transport_checked` and
`prospective_successor_context_checked`. All 24 broader claim flags remain
false. In particular, this does not establish full physical/root/autonomous
acceptance, a second accepted successor, full transformer/goal/information
semantics, complete resource accounting or campaign authority, physical
activation/rollback, challenge freshness, full recursive-productivity
recertification, hosted CI, broad platform validation, Phase 18 replay,
Phase 17 exit, Gate E, or EGC-0.

The next substantive work must connect a sufficiently rich fixed task
interpretation, independently verified successor context, actual next-turn
evaluation, and physical/semantic/resource witnesses to root-checked
continuation. Context availability alone does not discharge those obligations.
