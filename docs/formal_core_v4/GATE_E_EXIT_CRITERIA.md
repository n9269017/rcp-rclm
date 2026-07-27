# Gate E exit criteria

Gate E is divided into a formal foundation and an executable closure. Completion of the
formal foundation does not by itself close the full gate.

## Gate E formal foundation

- [ ] Formal Core v4 imports Formal Core v3 as an unchanged path dependency.
- [ ] Gate E package builds with the pinned Lean 4 toolchain and frozen dependency graph.
- [ ] No `sorry`, `sorryAx`, `admit`, or project-local `axiom` declaration occurs.
- [ ] Gate E certificate retains the complete embedded Gate D packet.
- [ ] Trusted Gate E checker refines the trusted Gate D checker.
- [ ] `autonomous_accepted_step_sound` is proved.
- [ ] Deterministic `firstAccepted` search is defined over a finite ordered enumeration.
- [ ] Search-result soundness is proved.
- [ ] Search-exhaustion soundness is proved.
- [ ] Relative bounded-search completeness is proved.
- [ ] Nonstagnation-or-certified-exhaustion is proved.
- [ ] Recursive-productivity retention is proved.
- [ ] Strict recursive-productivity witness validity is proved.
- [ ] Finite Gate D capability-frontier growth is inherited.
- [ ] Finite recursive-productivity retention is proved.
- [ ] Finite autonomous search-resource bounds are proved.
- [ ] Constructive successor availability follows from accepted-candidate existence in every declared enumeration.
- [ ] Conditional infinite autonomous trajectory existence is proved.
- [ ] Public theorem axiom report contains no `sorryAx`.
- [ ] Formalization manifest explicitly marks unsupported claims false.

## Phase 14 executable foundation

- [ ] Draft 2020-12 Gate E contract schema is frozen.
- [ ] Canonical records exist for history, hidden challenge, route-hint policy, attempt, exhaustion, and accepted result.
- [ ] Runtime validates deterministic attempt order and unique indices.
- [ ] Runtime rejects every forbidden host route hint.
- [ ] Runtime selects the first accepted attempt and no later accepted attempt.
- [ ] Runtime emits a complete exhaustion packet when no attempt accepts.
- [ ] Exhaustion packet binds every ordered attempt and reason classification.
- [ ] Capability frontier strictly expands on promotion.
- [ ] Recursive-productivity frontier never regresses.
- [ ] Strict recursive witness is independently certified when claimed.
- [ ] Search cost remains within the immutable total budget.
- [ ] Manual repair count is fixed to zero.
- [ ] Held-out material is invisible before candidate freeze.
- [ ] Source-quality, mutation, schema, and deterministic replay tests pass.

## Full Gate E closure

The complete gate remains open until a later schedule-free learned trajectory demonstrates:

```text
active M4 package chooses objectives and mutation families
no successful route is host-authored
multiple substantive update families are promoted
at least one rejected attempt is followed by endogenous recovery
all predecessor capability and recursive-productivity tasks are retained
manual repairs = 0
held-out leakage = 0
accepted candidate existence is witnessed in each used bounded search envelope
independent replay reconstructs every search, rejection, and promotion
```

Only the final Gate E closure aggregator may emit:

```json
{
  "accepted": true,
  "gate_e_closed": true,
  "schedule_free_autonomous_rclm_closed": true,
  "next_phase": 15
}
```

The initial foundation branch must retain:

```text
gate_e_formal_foundation_closed = false until CI evidence is attached
gate_e_closed = false
phase14_exit_closed = false
```
