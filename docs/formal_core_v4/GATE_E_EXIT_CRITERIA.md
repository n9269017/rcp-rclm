# Gate E exit criteria

Gate E is divided into a formal foundation, an executable contract foundation, and a later
schedule-free learned closure. Completion of the foundations does not by itself close the
full gate.

## Gate E formal foundation

- [x] Formal Core v4 imports Formal Core v3 as an unchanged path dependency.
- [x] Gate E package builds with the pinned Lean 4 toolchain and frozen dependency graph.
- [x] No `sorry`, `sorryAx`, `admit`, or project-local `axiom` declaration occurs.
- [x] Gate E certificate retains the complete embedded Gate D packet.
- [x] Trusted Gate E checker refines the trusted Gate D checker.
- [x] `autonomous_accepted_step_sound` is proved.
- [x] Deterministic `firstAccepted` search is defined over a finite ordered enumeration.
- [x] Search-result soundness is proved.
- [x] Search-exhaustion soundness is proved.
- [x] Relative bounded-search completeness is proved.
- [x] Nonstagnation-or-certified-exhaustion is proved.
- [x] Recursive-productivity retention is proved.
- [x] Strict recursive-productivity witness validity is proved.
- [x] Finite Gate D capability-frontier growth is inherited.
- [x] Finite recursive-productivity retention is proved.
- [x] Finite autonomous search-resource bounds are proved.
- [x] Constructive successor availability follows from accepted-candidate existence in every declared enumeration.
- [x] Conditional infinite autonomous trajectory existence is proved.
- [x] Public theorem axiom report contains no `sorryAx`.
- [x] Formalization manifest explicitly marks unsupported claims false.

## Phase 14 executable contract foundation

- [x] Draft 2020-12 Gate E contract schema is frozen.
- [x] Canonical records exist for history, hidden challenge, route-hint policy, attempt, exhaustion, and accepted result.
- [x] Runtime validates deterministic attempt order and unique indices.
- [x] Runtime rejects every forbidden host route hint.
- [x] Runtime selects the first accepted attempt and no later accepted attempt.
- [x] Runtime emits a complete exhaustion packet when no attempt accepts.
- [x] Exhaustion packet binds every ordered attempt and reason classification.
- [x] Capability frontier strictly expands on promotion.
- [x] Recursive-productivity frontier never regresses.
- [ ] Strict recursive-productivity tasks are independently executed by their frozen machine verifiers.
- [x] Search cost remains within the immutable total budget.
- [x] Manual repair count is fixed to zero.
- [x] Contract records held-out material as invisible before candidate freeze.
- [ ] A live post-freeze hidden-challenge service is bound to the active `M4` search.
- [x] Source-quality, adversarial, schema, deterministic serialization, and entry-point replay tests pass on Ubuntu, Windows, and macOS.

The two open executable items belong to the live Phase 14 trajectory rather than the static
contract references.

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

The foundation boundary is:

```text
gate_e_formal_foundation_closed = true
gate_e_runtime_contract_foundation_validated = true
gate_e_closed = false
phase14_exit_closed = false
```
