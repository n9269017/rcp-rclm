# Executable Core v2 — Phase 5A deterministic reference generator

## Purpose

Phase 5A is the first untrusted proposal producer. It does not add intelligence,
search, learning, or self-certification. It implements the exact finite Gate B seed
library already declared in Lean and exercises the complete logical path:

```text
immutable predecessor view
→ separate untrusted generator process
→ strict proposal validation
→ independent certificate construction
→ deterministic single-proposal selection
→ successor derivation from the selected update
→ pinned Lean verification
→ Phase 4 hardened checker verdict
```

The final Boolean is derived from the hardened checker report. The generator never
supplies or controls that Boolean.

## Formal grammar mapping

The runtime mapping is frozen to
`RcpRclmFormalCoreV2.RCLM.ClassicalBinary.boundedPacketGrammar` and the associated
bounded packet-builder fields.

| Predecessor core | Word | Witness | Proposal | Certificate built by host | Selected update | Derived successor | Engine resource |
|---|---|---|---|---|---|---|---|
| `initial` | `improve` | `strict_improvement` | `improve` | `improvement` | `improve` | `target` | 1/1 |
| `target` | `stabilize` | `stable_continuation` | `stabilize` | `stability` | `stay` | `target` | 0/1 |

The declared maximum word depth, proof length, and proposal count are each one.
States outside `initial` and `target` are outside the Phase 5A seed domain.

The selected Gate C mathematical checker remains available, but no separate bounded
Gate C seed-library grammar is claimed here. Phase 5A therefore generates only the
formal Gate B reference words.

## Worker input boundary

The worker receives one canonical JSON object over standard input containing only:

```text
predecessor package ID and immutable hashes
canonical predecessor state view
public bounded-generator policy
public declared objective
declared resource and grammar bounds
transition identifier
```

The strict input schema has no fields for:

```text
checker source
trust anchor
previous manifests
promotion ledger
reference answers
Lean verdicts
candidate acceptance
```

Unknown fields are rejected.

## Worker output boundary

The worker emits one canonical proposal record over standard output. Its fields are:

```text
request, policy, predecessor-manifest, and objective hashes
bounded word
formal witness name
proposal name
word depth
proof length
resource units used
```

It does not emit a certificate, selected candidate, successor, checker report,
strict-progress declaration, containment declaration, or acceptance verdict.

## Process separation

The host invokes the worker as a separate Python process using isolated mode, disabled
bytecode writes, UTF-8 mode, a fresh empty temporary working directory, a minimized
environment, standard input, and standard output. No candidate path, checker path,
network endpoint, trust record, ledger handle, or write handle is passed to the
worker.

Before execution, the host parses the frozen worker, grammar, protocol, and package
initializer source with the Python AST. It rejects direct file, process, or network
capability imports; privileged runtime imports; dynamic module-table/path access; and
direct calls such as `open`, `exec`, `eval`, `compile`, `__import__`, `getattr`, and
`input`.

This is a capability-minimized reference worker, not a claim of universal operating-
system sandboxing. A later promotion controller must add platform sandbox controls
when arbitrary open-ended generators are admitted.

## Deterministic replay

Every request is executed twice in fresh processes. Phase 5A requires equality of:

```text
raw standard output
raw standard error
parsed proposal
structured process report
worker source-guard report
```

A timeout is indeterminate and nonaccepting. A process failure, malformed output, or
replay mismatch rejects.

## Host-owned construction, selection, and realization

After proposal validation, trusted orchestration independently:

1. maps the bounded word to the canonical RCLM certificate;
2. maps the proposal to the single permitted canonical RCLM update;
3. applies the update to the predecessor core;
4. canonicalizes the derived successor;
5. builds the candidate from the selected update and derived successor;
6. derives exact evaluation evidence;
7. invokes the pinned Lean bridge;
8. reconstructs Phase 4 package-integrity evidence; and
9. invokes the hardened checker.

No manually authored successor field is accepted. This is logical realization of the
selected finite reference state. Actual repository/workspace copying and file-level
update realization remain Phase 6 work.

## Invocation

Run the worker through the host wrapper:

```bash
python scripts/generate_reference_candidate.py \
  generator_request.json \
  --proposal-out proposal.json \
  --report-out process_report.json
```

Run the two-case process suite:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase5a_process_suite.py \
  --out artifacts/runtime_v2_phase_5a/local/process_suite.json
```

Run the complete pinned Lean and hardened-checker reference loop:

```bash
python scripts/run_phase5a_reference_loop.py \
  --repo-root . \
  --outdir artifacts/runtime_v2_phase_5a/local/reference_loop
```

## Claim boundary

A clean Phase 5A closure establishes a deterministic, bounded, replayable reference
proposal path for the declared Gate B seed grammar. It does not make the generator
trusted, authorize promotion, implement a real filesystem successor, establish an
open-ended search capability, or support arbitrary learned-system entry.
