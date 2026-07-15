# Phase 7 promotion and rollback controller

Phase 7 coordinates the already separated generator, selector, filesystem realizer,
objective evaluator, certificate constructor, pinned Lean bridge, and hardened checker.
It does not absorb their mathematical responsibilities and it never treats a generator
or candidate assertion as authoritative evidence.

## Frozen finite-reference path

```text
immutable active predecessor package
→ separate untrusted Phase 5A generator process, executed twice
→ strict proposal validation and replay comparison
→ Phase 6 typed selection and isolated filesystem realization
→ public candidate-package verification
→ independent state-derived objective evidence
→ host-owned certificate construction
→ mandatory generated-Lean source gate
→ pinned Lean verification
→ Phase 4 hardened checker
→ accepted candidate or fail-closed rejection
→ content-addressed package and append-only ledger
→ atomic active-pointer replacement or unchanged active package
```

The final checker invocation follows the Lean bridge because the Phase 3 checker
requires a packet-bound Lean report. The controller does not calculate entropy,
KL/QRE, recovery, progress, strict-witness, trust, or domain truth. It constructs the
existing immutable checker request and obeys the checker verdict.

## Store layout

```text
active.json
packages/<phase7-package-hash>/
  predecessor/
  source_candidate/        promoted packages only
  evidence/
  manifest.json
ledger/<entry-hash>.json
runs/<run-id>/
  attempt-0000/
    candidate/             when realization reached
    evidence/
  controller_report.json
```

The active pointer is the only mutable control-plane file. Package directories and
ledger entries are content addressed. A promotion writes and verifies the immutable
package and ledger entry first, then replaces `active.json` atomically. A failed or
rejected candidate never becomes active.

## Rejection and retry

A rejected attempt appends a first-class rejection ledger entry while preserving the
active package hash. The controller may invoke the untrusted generator again only
while the frozen attempt count and attempt-unit budget remain. Every attempt costs at
least one controller unit, including a generator-reported zero-cost proposal, so a
backend cannot obtain unbounded retries by claiming zero resource use.

An indeterminate Lean, checker, or infrastructure result stops the run and remains
nonpromoting. The controller never edits or repairs a rejected candidate between
attempts.

## Immutable promotion package

A promoted package binds:

- its parent Phase 7 package hash;
- the complete new active predecessor package tree;
- the accepted Phase 6 candidate package tree and manifest;
- the accepted attempt report;
- the controller policy;
- the controller evidence tree;
- the substantive component kinds.

The new active predecessor payload is copied from the accepted candidate payload.
Its inner Phase 6 predecessor manifest is rebuilt deterministically for the next
finite-reference generator invocation. The outer Phase 7 parent hash supplies the
immutable recursive chain.

## Reference trajectory

The declared Phase 7 reference suite performs:

```text
root initial package
→ promoted target package with a verification-policy change
→ promoted target package with a memory-policy change
→ two rejected retries after the fixed target grammar is exhausted
```

The final rejected run leaves the second promoted package active and advances only
the append-only rejection ledger.

## Scope and claim boundary

The implementation is restricted to the finite Gate B reference generator and the
existing selected checker semantics. Gate C remains supported by the checker but no
Gate C promotion generator is introduced here. General noncommuting quantum states,
arbitrary CPTP maps, matrix-log QRE, Petz recovery, open-ended generator correctness,
learned PyTorch acceptance, independent replay, external benchmark claims, and
unbounded autonomous RSI remain outside Phase 7.
