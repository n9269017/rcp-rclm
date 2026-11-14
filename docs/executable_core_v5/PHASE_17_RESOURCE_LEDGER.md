# Phase 17N — precharged bounded-work accounting

Development increment based on `a54e67b9b4b4f9f519b20f3999ce604b724ab401`.
Keep PR #68 draft and unmerged. This is not complete resource accounting,
root acceptance, promotion, a live capability gain, or Phase 17 closure.

## Implementation

The trusted evaluation wrapper reserves a fixed tariff before invoking a bounded
operation. It writes and flushes the reservation and requests `os.fsync` before
calling the operation. Each operation then has one result record. Reservations
remain charged on rejection, exception, interruption, or an unfinished result.
There is no refund or retry-until-success path.

The four dimensions are candidate admissions, vector interpreter calls, input
integer values, and reserved output integer values. The candidate tariff is
`(1,0,0,0)` and the four-value vector-call tariff is `(0,1,4,4)`.
The declared conversion weights are `(64,16,1,1)`, so the respective costs are
64 and 24 work units. These are frozen abstract work tariffs, not measurements
of CPU instructions, seconds, energy, dollars, or full-model compute.

The policy is fixed from the inherited program count, eight probes, and the full
32-candidate grammar allowance. It does not use the winning candidate index.
For the current eight-program predecessor the maxima are `(32,328,1312,1312)`
and 9,920 work units. Every dimension and the scalar ceiling must both fit.
No operation is invoked when admission would exceed either bound.

`resource_exhausted` is distinct from complete search exhaustion. Exhausting
this work envelope does not certify that every possible program was searched.

## Journal and restart boundary

The canonical append-only journal binds the policy and exact predecessor,
prospective candidate, sealed transcript, and fixed verifier. Every event has
an index, predecessor hash, and domain-separated hash. The accounting verifier
recomputes every tariff, cumulative counter, reservation/result pairing, and
terminal state; a stored cumulative total is never accepted without checking.

A local OS advisory lock permits one writer. Existing journals require an
externally retained expected head and exact policy/binding. A truncated record,
changed file, stale head, duplicate operation, altered tariff, or unbound result
fails closed. A pending reservation cannot be silently rerun or sealed. Explicit
abandonment preserves its charge and ends the session in a safety halt.

This is local single-writer persistence, not a multi-machine consensus protocol,
a malicious-same-user sandbox, or a guarantee against every power-loss/filesystem
failure. Filesystem flush semantics, the trusted process, and an independently
retained head remain assumptions. Accepting a rolled-back external anchor permits
rollback; a hash does not solve that problem. A new path is not a campaign-wide
budget reset authority. Cross-session challenge consumption and campaign budget
ownership remain to be integrated.

## Actual selected profile

The profile authenticates the existing sealed synthetic transcript using the
current independent reference verifier. It then performs fresh reference work:
eight target-vector calls, 64 inherited-program calls, and all eight probes for
each of nine candidate attempts. There is no success-dependent probe shortcut.
All eight recorded rejections and the final passing verdict are recomputed from
those outputs and compared to the sealed transcript. No hidden challenge is
created, and no current controller is given a future winning schedule.

The expected measured reservation totals are `(9,144,576,576)`, costing 4,032
work units. The main journal has 308 events: one header, 153 reservation/result
pairs, and one seal. A second accounting pass derives the complete operation
schedule independently from the pinned inputs and recomputes each result hash.
Dropping an entire operation and rehashing all remaining events does not satisfy
that schedule. This is not an independent Phase 18 replay or attestation that
historical resource consumption occurred.

Separate controls retain an intentionally failed operation, a zero-budget denied
operation, and an explicitly abandoned pending operation. Their distinct journals
are not counted as operations in the selected profile. Unit tests also exercise
an actual process exit after reservation and cross-process lock contention.

## Precisely excluded resources

The profile does not count archive reopening, transcript validation, hash/JSON
processing, journaling, replay checking, Python runtime overhead, or Lean work.
CPU time, accelerator time, memory, storage, energy, and these omitted stages are
reported as unmeasured, not zero. An elapsed-nanosecond field is diagnostic only,
not a hard deadline or complete CPU measurement. The original worker service is
not silently replaced by this offline metered replay.

Therefore `complete_resource_accounting=false`, `os_resource_containment=false`,
and `campaign_budget_authority_integrated=false` remain mandatory. Future work
must meter/enforce the full declared campaign envelope; this scoped tariff must
not be relabeled as that result.

## Formal connection

`ResourceAccounting.lean` defines the operation kinds, counter and scalar sums,
and a finite policy. It proves monotone prefix charges, prefix bounds from a
bounded total, over-budget exclusion, and the no-refund append property. The
adapter supplies the actual learned-root `resourceUsed` and `resourceBudget`
fields while leaving goal/information, task/frontier and producer fields intact.
The selected certificate checks the concrete counts, bound, candidate binding,
and retained failed-operation charge. Twelve exact axiom audits and four actual
false-proposition rejections are required: OverBudget, OmittedOperation,
RefundedFailure, and MixedCandidate.

This does not instantiate the complete compatible base kernel, prove the Python
journal implementation in Lean, or construct a full LearnedAcceptedStep or
AutonomousAcceptedStep. Physical extraction, operation execution, the journal-to-
Lean correspondence, and the pinned toolchain/import cache remain external trust
boundaries. The twelve audits are authored source until actual compilation passes.
The previous M, L and H proof campaigns are not rerun or reassigned.

## Local validation and evidence

Run `python scripts/run_phase17_resource_tests.py` (79 tests, no skips).
The actual new gate is:

```text
python scripts/run_phase17_resource_gate.py --test-fixture --require-lean --lean-workspace <prepared formal-root> --output <new external directory>
```

The kit validates a clean exact source head, applies additive code plus the M
prose count correction, commits the implementation in a separate checkout,
runs the new tests and mandatory actual Lean gate, and retains a separate
source-bound evidence commit. It refreshes canonical Git-blob checksums before
normal fast-forward/push. No reset, amend, force push, main merge, dependency
installation, hosted workflow request, release or DOI operation is performed.
Original failures and evidence remain untouched. Unsuccessful new validation
cannot advance the original checkout.
