# Phase 17G — Conservative registry semantics and a scoped base kernel

Development increment, not complete Phase 17 or Gate E. The installation base is
`7de254018946dd4a782f758dc21913d0796273c1` on the existing draft PR #68 branch.
Earlier sources, releases, proof records and failures are unchanged.

## Executable semantics

`RegistryImage` stores detached canonical program bytes under unique program
hashes. Dispatch is fixed: look up the exact identifier, parse its canonical
bounded program, then use the already declared matrix interpreter. The order is
the manifest's inherited order followed by the fresh entry, never directory
iteration order. A new entry cannot replace or shadow an inherited identifier.
The prospective package is still inactive; dispatch here is an explicit evaluator
operation, not installation into an active model service.

The verifier calls the existing Phase 17F successor preparation, independently
measures both packages, then verifies the exact eight-to-nine extension. All 173
protected predecessor files are framed with explicit path and byte lengths and
compared exactly. The two mutable manifests are separately validated against the
independently reconstructed package. The inverse removes the new program and
restores those two old manifests only. Every tensor and inherited program in the
reconstructed predecessor comes from the candidate, not a separately copied old
model. This is a pure retraction, not atomic rollback of an active store.

The measured regression profile executes each of the eight inherited programs
on six declared vectors (48 comparisons), comparing predecessor, candidate and
reference outputs. The candidate is also executed on all eight sealed probes.
These finite executions test the implementation; they are not the universal
preservation theorem. Package contents are measured again after evaluation.

## Formal scope

`lean/phase17_bridge/ConservativeRegistry.lean` imports the unchanged formal core.
It gives concrete append, lookup, dispatch and retraction semantics. The new
statements quantify over all inputs and any *fixed deterministic* interpreter:
an inherited identifier still resolves to the identical program, so its output
and its solved task are preserved after extension. This does not prove that an
arbitrary interpreter agrees with Python, that a mutable executor is safe, or
that all future package transformations are conservative.

The same file constructs an explicitly scoped instance of the existing
`RcpRclmFormalCoreV2.RCP.Kernel`. Its eleven `StepObligations` use:

- equality observations over the complete protected byte image, with a concrete
  nonconstant witness;
- exact typed append and constructive retraction, with zero allowed loss and
  exact-state recovery distance;
- registry length as progress, not a general intelligence metric;
- consumed candidate credits minus declared credits as the residual, including
  a nonconstant witness;
- exact root and parent-registry bindings and a rejectable typed/fresh-key
  reality predicate.

This is an append-only registry observation model. It is **not** a replacement
for the project's full RCLM information/coherence/recovery semantics. In
particular its eleven checked fields do not discharge the corresponding fields
of a different kernel merely because their field names coincide. No complete
`LearnedAcceptedStep` or `AutonomousAcceptedStep` is constructed in this increment.
Quantum-information, thermodynamic, general goal-preservation, and full learned
semantic refinement remain outstanding.

The selected certificate binds the measured registry literals to exact list
append. The protected image is universally quantified rather than inserting
27 MB of bytes in Lean; Python measurement, injective framing, parsing, literal
extraction, and the binding of those literals to files remain trusted boundary
assumptions. Hashes are integrity bindings, not identity authentication or event
time attestations. Import-cache/toolchain assumptions are unchanged.

Six named audits are required:

```
Phase17Registry.base_step_sound
Phase17Registry.dispatch_retained
Phase17Registry.solved_task_retained
Phase17Registry.exact_recovery
Phase17Registry.selected_base_step
Phase17Registry.selected_registry_mapping
```

The actual compiler must accept the positive certificate first. It must then
reject a deliberately invalid certificate whose new identifier shadows an
inherited identifier. A timeout, missing executable, unexpected theorem name,
extra output, unapproved axiom, changed source, or mock tool response does not
satisfy the real gate. Compiler-control unit tests use mocks and are not proofs.

## Reusing rather than repeating Phase 17F

The default installer requires real NEW Lean checking. It does not repeat the
old 13 inherited capability proofs or four finite successor audits. Reuse requires
all of the following: the exact pinned Phase 17F execution bytes, the same
candidate-package identity, a freshly recomputed Phase 17F packet hash identical
to the checked packet, and no edits/deletions/renames to existing Python, Lean or
script files relative to the immutable base. The real new check independently
validates pinned root sources, dependency identities, tool binaries and permitted
axioms. Such reuse is explicitly reported as retained evidence, not a fresh run
of the previous obligations or an independent replay of the old tools.

The positive candidate remains the known-answer synthetic fixture. No live
challenge search is requested and no live improvement is claimed.

## Recursive productivity and completion boundaries

All 19 inherited recursive labels remain visible. The earlier three scoped
probes remain scoped. This increment recertifies **zero complete operational
recursive-productivity tasks**. A general solved-task retention theorem could
support future task-specific witnesses, but no automatic correspondence between
those labels and its `Task` structure is asserted.

Resource semantics cover candidate evaluation credits only. Wall time, CPU/GPU,
memory, storage, energy, evaluator isolation and durable consumption still need
their declared accounting and enforcement. No active-state pointer is changed.

```
root_transition_verified           = false
recursive_productivity_recertified = false
full_frontier_recertified          = false
complete_resource_accounting       = false
promotion_authorized              = false
promotion_performed               = false
live_capability_gain_demonstrated  = false
phase17_exit_closed                = false
gate_e_closed                     = false
egc0_started                      = false
```

## Execution and provenance

The guarded application kit validates in a new short-path clone, requires real
Lean, retains source-bound logs, creates a separate evidence-only commit, and
advances the original branch only after checks pass. Git long paths, literal
NUL-delimited staging, explicit UTF-8 and evidence byte-preservation are retained.
No forced update, reset, merge, release/DOI change or Actions run is requested.

The assistant's measurements and environment limits are in
`artifacts/development/phase17g/assistant-validation.json`. The operator result,
when successfully installed, is separately retained under `phase17g/op-*` and
updates `PHASE_17_LOCAL_VALIDATION.json`. Keep PR #68 draft and unmerged.
