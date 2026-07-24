# Phase 13 complete validation

The permanent workflow is `.github/workflows/runtime-v3-phase-13-complete.yml`.

## Capture

The capture job checks out the exact pull-request head, builds the frozen Formal Core v2 and pinned Formal Core v3 projects, rejects admitted proofs and local project axioms, reconstructs authoritative Phase 12 closure without a training backend, and emits a complete content-addressed trajectory bundle.

The bundle is verified before upload. Its source binding, closure report, all regular-file records, and declared empty-directory set are canonical and hashed.

## Portable replay matrix

Linux, Windows, and macOS independently download the same bundle and run the worker-free structural verifier. Each platform runs both the package tool and repository entry point; their canonical JSON outputs must be byte-identical.

## Pinned replay matrix

Linux, Windows, and macOS independently build the pinned Lean projects and replay:

- the exact immutable promotion-store and ledger chain;
- all seven final task certifications;
- all four generated Gate B Lean programs;
- all four logical evaluations and hardened-checker verdicts; and
- the Phase 13A source guard and 21-case attack suite.

No learned training, generator, or planner worker is imported or invoked by the replay source.

## Final closure

The final job downloads all three portable reports and all three pinned reports. It requires exact agreement on the source head and content-addressed evidence, emits the closure through two independent entry points, requires byte equality, validates Draft 2020-12 schema, and uploads the final report.

The claim boundary is fail-closed:

```text
Phase 13A report:       phase13_exit_closed = false
structural report:      phase13_exit_closed = false
pinned replay report:   phase13_exit_closed = false
final aggregate report: phase13_exit_closed = true only when every check passes
```
