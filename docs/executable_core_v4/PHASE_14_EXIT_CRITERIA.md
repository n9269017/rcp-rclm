# Phase 14 exit criteria

Phase 14 closes only when one exact source head satisfies every item below.

## Authoritative campaign

- The starting immutable store is the certified Phase 13 `M4` store.
- The source-bound challenge manifest and private answer store round-trip exactly.
- At least four promotions occur.
- At least two fail-closed rejections are retained.
- At least three substantive update families are promoted.
- Rejection-conditioned recovery is demonstrated.
- Every rejection preserves the active store pointer.
- Every promotion is parent-linked and atomic.
- The capability frontier grows from seven to at least eleven independently certified tasks.
- The recursive-productivity frontier is retained at every promotion.
- Manual repairs and pre-freeze held-out visibility are zero.
- No expected candidate hash, capability, model identity, accepted program bytes, or successful component schedule is supplied.

## Independent replay

Linux, Windows, and macOS each independently replay the retained bundle with:

```text
proposal-worker invocations   0
training invocations          0
generator invocations         0
planner invocations           0
manual repairs                0
```

Each platform must reopen all nine immutable packages, replay all six attempts, recertify protected and hidden tasks, recompute four Gate D transitions, recompute four Gate E reports, rerun four pinned Gate B/hardened-checker envelopes, and agree on the source, bundle, trajectory, final store package, and final semantic package.

## Adversarial closure

The retained attack suite must reject route hints, held-out leakage, manual repair, update-family forgery, rejection-history pointer forgery, private-answer-store substitution, proposal-worker private-source access, invalid direct/probe route markers, and post-freeze candidate mutation.

## Sole closing authority

Trajectory and replay reports must retain:

```text
phase14_exit_closed = false
next_phase = 14
```

Only the final three-platform aggregator may emit:

```json
{
  "accepted": true,
  "phase14_exit_closed": true,
  "gate_e_closed": false,
  "next_phase": 15
}
```
