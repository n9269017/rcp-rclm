# Phase 17AC: controller continuation and finite exhaustion

## Baseline and purpose

AC starts from completed AB commit `3d1f1a663f2087c4e80dc18c0b208818ce2d2d3f`.
That commit contains the native Windows AB operator evidence; the earlier Linux
application is separately attributed. AC preserves both results and does not
rerun AB, its historical proof campaign, or any worker session.

There are two different continuation problems. The controller must choose its
next candidate deterministically from a valid present prefix, stop with the right
reason, and exhaust a finite grammar without repetition. Separately, the proof
checker must retain completed compilations across process or connection loss.
This increment addresses both while keeping their claims separate.

## Controller model and proof obligation

`lean/phase17_bridge/ControllerContinuation.lean` imports the original
`ProposalProvenance.lean` and uses its existing `Phase17Provenance.choose`.
The original selector is unchanged. It ranks candidates for the first four
attempts and subsequently uses the fixed stride-17 permutation of 32 indices.

The new model records actual initial credits, the ordered observations of
candidate indices and pass booleans, and an optional external-stop or safety-stop
cause. Its decision has the six existing controller actions. Stop causes take
precedence once recorded. An observed pass takes precedence over both exhaustion
conditions. Complete grammar exhaustion takes precedence over exhausted credits.
Only an ongoing evaluable prefix can acquire another observation or stop cause.

The generic theorems establish selector freshness and range, fallback coverage
and non-repetition, preservation of the prefix invariant, deterministic replay
and prefix composition, terminal-state immutability, and the action priorities.
For every valid 32-row context and offset below 32, a sequence of rejection
observations can continue while both candidates and credits remain. With at
least 32 actual credits it reaches complete finite exhaustion in 32 attempts;
with fewer credits it reaches the resource boundary. These are quantified
results about the model and selector, not deductions from a sampled success.

Credits are not normalized to 32 in checkpoint identities. The model accepts
arbitrary natural credits, including 40 and 100. Equal selector rows and offset
produce equal next choices even if unused context metadata differs. Equal
present histories with sufficient credit headroom produce equal decisions;
this does not identify their different budget/checkpoint records.

The model receives observation booleans and candidate-score data as inputs. It
does not prove the truth of an external evaluation, the authenticity of physical
inputs, or full Python/Lean semantic equivalence. A production controller
checkpoint's receipt authentication remains a separate Python obligation.

## Controlled implementation comparison

The new Python packet generator calls the unchanged production controller and
compares every retained prefix with a separate index-level decision/replay
implementation. Its deterministic controlled inventory includes:

- All 32 fallback offsets, each exercised through full rejection exhaustion.
- A pass at each of the 32 candidate positions, including a pass on the last
  available credit.
- Credits 0, 1, 3, 4, 5, 31, 32, 40, and 100, covering the ranked/fallback
  boundary and both exhaustion priorities.
- External and safety stops at multiple prefix lengths, kept distinct.
- Tied, negative, and varied candidate scores, and production checkpoint
  serialization/restoration at every tested prefix.

There are 86 controlled cases, 1,784 recorded observations, and 1,956 production
checkpoint round trips. This finite comparison supports the implementation
projection for those cases; it is not a universal equivalence theorem. The
generated Lean positive certificate independently evaluates the projected cases
using the original selector and new model. Its 35 named theorem audits cover
34 generic AC obligations and the aggregate selected-case theorem.

Nine negative controls assert a repeated choice, premature exhaustion, wrong
pass priority, wrong exhaustion priority, continuation after a pass, rewriting a
terminal cause, a reordered prefix, or confusion of external and safety stops.
Each control first proves that its own wrong claim is false, then must fail at
the intended final assertion. A timeout, import error, unexpected diagnostic,
or unrelated compiler failure is not a passing negative control.

## Compilation-stage continuation contract

The new `compilation_checkpoint.py` runner is additive and belongs to AC. The
historical AB contract required fresh modules within its own application; AC
does not retroactively change that rule or relabel old diagnostic objects as an
AB application result.

AC has 14 ordered stages: compile the unchanged provenance module, check its
import resolution, compile the new controller module, check its import
resolution, run the positive certificate and named audits, and run all nine
negative controls. Each invocation owns one new private directory and executes
one command supplied by the trusted gate code. Reports never supply executable
commands.

An invocation publishes `completion.json` only after a completed native wait,
the exact semantic result check, unchanged input hashes, source/artifact/log
inventory validation, and budget checks. Publication is exclusive and atomic
on the supported filesystem. The record includes the original producing
invocation for each retained step and compiled object. An interrupted stage
without a valid completion record is not reusable.

A subsequent invocation requires an explicitly selected completed parent and a
separately retained SHA-256, plus the execution plan's separately retained hash.
It checks the full source, tool, foundation and environment bindings, copies the
completed artifacts and logs, and performs fresh import-resolution checks in its
own directory before starting the next stage. It never infers a predecessor's
death from a missing process handle, steals a lock, or takes over an unfinished
process. Explicit unresolved branches remain in the record.

The latest completed invocation contains the complete selected stage history,
raw log prefix, immutable sources, and required compiled objects. Recovery must
save that entire directory, the prepared packet/proofs, plan, environment
record, and their externally retained hashes. Saving only a progress JSON file
does not preserve reusable compiled work. Earlier unresolved/failed branches
remain separate historical evidence.

The invocation directory may be copied while keeping its UUID directory name.
Original producer paths remain historical observations. The actual compiler,
foundation, current working directory, and environment paths remain exact plan
bindings: automatic migration to different tool/foundation paths is not yet
implemented. A lost host must restore those bindings or begin a newly attributed
plan. The runner resumes at completed stage boundaries; it cannot restart a
half-finished Lean elaboration at an internal declaration.

Each major Lean stage keeps a 30-minute limit; import checks have a two-minute
limit. The new lineage budget sums measured active intervals of selected
completed invocations, with a four-hour maximum. It includes their checks and
restoration work through final validation. Downtime, final completion-file
publication, and unknown consumption of unresolved branches are explicitly
outside that measurement. This is not complete campaign resource accounting,
nor an alteration of AB's historical wall-clock allowance.

## Running and resuming

Use clean committed source and the existing pinned Lean 4.31.0 foundation.
Start a new gate with:

```text
python -B scripts/run_phase17_controller_continuation_gate.py --test-fixture --require-lean --lean-workspace <prepared-root> --toolchain-root <lean-4.31.0> --output <new-external-output> --one-stage
```

The command prints the execution-plan hash and, after successful completion, the
completed invocation path and hash. Continue that explicit lineage with:

```text
python -B scripts/run_phase17_controller_continuation_gate.py --output <same-output> --expected-plan-sha256 <saved-plan-hash> --resume-from <selected-invocation>/completion.json --expected-parent-sha256 <saved-parent-hash> --one-stage
```

Omit `--one-stage` to execute the remaining sequence. Each stage still receives
its own immutable completion. Add `--unresolved-invocation <uuid>` when selecting
a completed ancestor while preserving a known unresolved branch. If the final
stage completed but the aggregate execution record was interrupted, selecting
that complete parent finalizes the result without compiling again.

After completion, reconstruct the evidence using the original source and
matching pinned environment, without invoking Lean or workers:

```text
python -B scripts/run_phase17_controller_continuation_gate.py --verify-only --output <same-output> --expected-execution-sha256 <saved-execution-hash>
```

## Acceptance and remaining boundaries

AC revision 02 acceptance requires all 138 tests without failures or skips, the exact
prepared packet and generated sources, the completed selected
14-stage lineage, all named audits with only permitted axioms, all nine intended
negative rejections, and saved-evidence reconstruction. Controlled subprocess
tests of the runner do not replace real Lean compilation.

The resulting narrow claims are `controller_protocol_checked` and
`bounded_search_exhaustion_checked`. Every broader Phase 17 authority/closure
claim remains false: full root transition, complete learned or autonomous step,
physical projection or execution attestation, full goal/information semantics,
frontier and recursive-productivity recertification, complete resource/campaign
authority and OS containment, active promotion, live capability gain, Phase 17
exit, Gate E, EGC0, hosted CI, broader platform validation, and Phase 18 replay.

PR #68 remains a draft and unmerged. A successful selected Linux application and
a separately attributed native Windows application do not close those broader
obligations. The next architecture-level boundary remains the binding of this
controller model and selected executable projections to the full physical and
semantic witnesses required by the root transition.

## Revision 02: portable checkpoint byte capture

The first native Windows application stopped in the Python tests at the
checkpoint reader's file-stability check. Its reported result was 115 tests,
seven failures, and 38 errors; the formal Lean gate had not started. The
original Linux application remains separately attributed to revision 01, and
the Windows attempt's transcript remains historical failure evidence. Its
reported count does not replace the full 127-test revision 01 inventory.

The original reader compared `st_ctime_ns` from a file descriptor's `fstat`
with a pathname's `stat`. On affected Windows Python builds, these APIs can
report metadata-change time and creation time respectively for the same
unchanged file. This is documented in
[CPython issue 157671](https://github.com/python/cpython/issues/157671).
The retained Windows transcript does not identify the Python version or which
metadata field differed, so that exact native observation is not inferred.

Revision 02 compares the original descriptor before and after reading with a
fresh descriptor opened from the checked pathname, using `fstat` consistently.
It still checks device and file identity, size, modification time, and change
time. A final no-follow pathname check separately verifies identity, size,
modification time, and regular-file status. Link/junction rejection and bounded
binary capture remain required. Only the invalid comparison between the two
APIs' meanings of change time is removed; change detection is not disabled.

Eleven additional reader regressions cover exact binary bytes, an unchanged
file with different cross-API change-time meanings, descriptor-only change-time
mutation, size and modification-time changes, replacement by an identically
valued file, final pathname identity/link checks, and nonregular or oversized
inputs. The complete inventory is therefore 138 tests. These controlled
regressions require a new full application and do not establish a native
Windows pass. The controller model, Lean theorem statements and proof bodies,
14-stage acceptance sequence, checkpoint schema, and continuation attribution
rules are unchanged.
