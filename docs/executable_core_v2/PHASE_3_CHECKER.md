# Executable Core v2 — Phase 3 deterministic checker

## Purpose

Phase 3 is the first authoritative executable decision engine for the selected
Gate B classical and selected commuting/diagonal Gate C reference scopes. It is
a pure function over immutable records. The command-line program only performs
file input/output around that pure core.

The checker does not import, invoke, or trust a generator. It contains no model,
optimizer, network client, random source, clock read, environment-variable read,
or mutable global state.

## Input boundary

The canonical request contains:

```text
immutable RCLM predecessor
immutable RCLM candidate update and successor
RCLM certificate packet
pinned trust-anchor record
independently measured resource record
scope-specific protected distinctions
raw exact evaluation observations
packet-bound Phase 2 Lean bridge report
```

No success Boolean is accepted as evidence. Unknown fields are rejected. In
particular, fields such as `certificate_preserved`, `reality_containment`,
`strict_improvement`, `trust_valid`, or `accepted` cannot enter the request
schema.

## Recomputed obligations

The checker recomputes, in a fixed order:

1. schema, contract, scope, and evaluator-policy consistency;
2. the typed core successor;
3. the `typed` and `packet` residuals;
4. exact state-derived classical distributions or diagonal densities;
5. Shannon/von Neumann entropy and KL/QRE certified intervals;
6. zero-budget protected non-loss;
7. selected constructive recovery;
8. successor invariant, containment, and domain membership;
9. progress nondecrease and the derived strict witness;
10. frozen trust roots and checker/Lean/claim policies;
11. independently measured resource and provenance restrictions;
12. exact RCLM canonical-lift and RCLM-to-RCP refinement consistency;
13. Lyapunov, ambiguity-collapse, and relevance monitors;
14. the exact packet binding and accepting result of the Phase 2 Lean bridge;
15. canonical hashes of every authoritative input and derived binding.

The final verdict is derived from the component statuses:

```text
any definite failed obligation  -> reject
no failure, any indeterminate   -> indeterminate
every obligation certified      -> accept
```

Only `accept` sets the report's derived `accepted` field to `true`.

## Mathematical scope

### Gate B

The source of truth is the exact binary probability vector:

```text
outside / initial -> (1/2, 1/2)
target            -> (3/4, 1/4)
```

The checker recomputes Shannon entropy, support-aware KL divergence to the
target, progress, the strict improvement margin, exact selected recovery, and
the formal binary monitor values.

### Gate C

The source of truth is the exact two-entry spectrum of a diagonal density
matrix. The only channels are the exact identity and basis swap. The checker
recomputes spectral von Neumann entropy, support-aware diagonal QRE, progress,
selected swap recovery, trace-one preservation, and entropy preservation.

No arbitrary dense non-diagonal matrix, general CPTP channel, matrix logarithm,
general data-processing theorem, or Petz recovery claim is implemented.

## Lean boundary

The pure checker consumes an immutable Phase 2 bridge report. It does not spawn
Lean itself. Acceptance requires that the report:

```text
is bound to the recomputed canonical packet
has the expected scope, case ID, and packet hash
reports expected acceptance = true
reports RCP acceptance = true
reports RCLM acceptance = true
has exact Python/Lean differential agreement
did not time out
used the pinned compiler, mathlib, and project pin
```

A bridge report showing agreement on a rejected mutation is valid conformance
evidence but is not a Phase 3 acceptance result.

## Structured report

The report contains:

```text
verdict and derived accepted Boolean
stable reason codes
typed successor result
computed residuals
entropy, divergence, and progress intervals
evaluation-evidence comparison
protected non-loss result
recovery result
invariant result
reality-containment result
progress result
strict-witness result
trust result
resource/provenance result
domain result
RCLM-to-RCP refinement result
monitor result
Lean bridge result
computed artifact hashes
checker policy hash
```

## Invocation

From the repository root:

```bash
python -m pip install --no-deps -e python/rcp_rclm_runtime_v2
python scripts/check_candidate.py request.json --out checker_report.json
```

Both request and output use the canonical JSON rules. A nonaccepting report
causes the command to exit with status 1.

## Claim boundary

A green Phase 3 implementation licenses Phase 4 adversarial and tamper testing.
It does not yet license candidate promotion. The checker enters the trusted
computing base only after the Phase 4 mutation suite establishes fail-closed
rejection across the frozen attack surface.
