# Formal Core v2 audit artifacts

The workflow `.github/workflows/formal-core-v2.yml` uploads one audit archive for
every attempt, including failed attempts:

```text
formal-core-v2-audit-<workflow-run-id>-<attempt>
```

The archive is the reproducibility record for the clean checkout used by GitHub
Actions. It is not a runtime artifact and does not contain an executable RSI
system.

## Retention

The workflow currently requests a 90-day GitHub artifact retention period.
Long-term releases should preserve selected audit archives and their external
SHA-256 digests separately from the ephemeral workflow retention window.

## Archive contents

### `paper_alignment_pin_audit.txt`

Output from:

```text
docs/formal_core_v2/audit/verify_paper_alignment_pins.sh
```

It records passing or failing checks for:

```text
Paper I Git blob
Paper II Git blob
required paper theorem labels
required Gate A theorem surfaces
required Gate B theorem surfaces
required RCLM/refinement/architecture theorem surfaces
required closure-record claim-boundary text
```

A passing result establishes source and mapped-name identity, not mathematical
semantic equivalence.

### `audit_metadata.txt`

Records the clean workflow context:

```text
GitHub checkout commit
Lean toolchain string
lake-manifest SHA-256
Paper I blob
Paper II blob
```

Use this file to determine exactly what the remaining logs refer to.

### `lake_build.log`

The complete `lake build` output from the pinned project. The workflow prints only
the tail to the web log but uploads the entire file.

A successful build establishes that the project elaborates at the recorded source
and dependency pins. It does not establish exact paper agreement or empirical
validity.

### `forbidden_proof_tokens.txt`

Contains matching source locations if a project Lean file contains a forbidden
`admit` or admitted-proof token. It is empty on a passing source scan.

### `no_sorry_audit.txt`

Human-readable passing summary for the admitted-proof token scan.

### `project_axiom_declarations.txt`

Contains matching source locations if a project Lean file declares a local
`axiom`. It is empty on a passing source scan.

### `project_axiom_audit.txt`

Human-readable passing summary for the project-local axiom declaration scan.

### `gate_a_axioms.txt`

Output of:

```bash
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
```

It prints the kernel axiom dependencies of the audited Gate A public declarations.

### `gate_a_axiom_audit_summary.txt`

Passing summary confirming that all named Gate A audit declarations elaborated
and that no report contained `sorryAx`.

### `gate_b_axioms.txt`

Output of:

```bash
lake env lean ../../docs/formal_core_v2/audit/GateBAxiomAudit.lean
```

It prints the kernel axiom dependencies of the audited finite classical Gate B
declarations.

### `gate_b_axiom_audit_summary.txt`

Passing summary confirming that all named Gate B audit declarations elaborated
and that no report contained `sorryAx`.

### `rclm_refinement_axioms.txt`

Output of:

```bash
lake env lean ../../docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
```

It covers the substantive RCLM-to-RCP refinement, architecture engine,
Paper II direct/robust-reflective interfaces, bounded seed-library packet builder,
and the concrete binary reference declarations listed in that audit file.

### `rclm_refinement_axiom_audit_summary.txt`

Passing summary confirming that all named RCLM audit declarations elaborated and
that no report contained `sorryAx`.

## Foundational dependency interpretation

At the completed Gate B and bounded-seed reference scope, the union reported by
the audited public declarations is:

```lean
[propext, Classical.choice, Quot.sound]
```

Interpretation:

```text
propext
  standard propositional extensionality used by Lean/mathlib proofs

Classical.choice
  expected in noncomputable existence/selection constructions, including
  choosing a successor packet from an explicit Nonempty premise

Quot.sound
  standard quotient soundness used by imported mathematical constructions
```

This union is not a list of project-local axioms. The project-local axiom scan is
separate and must remain empty.

Some concrete equality, projection, and finite-domain declarations are axiom-free.
The exact dependency of each theorem is preserved in the corresponding report.

## Completed Gate B/bounded-seed validation records

The theorem surface was validated at source head:

```text
a09c742ca2541ad3302a5c1041852974649e09c8
```

with:

```text
workflow run: 29224543624
build jobs: 1953
RCLM audited declarations: 47
artifact: formal-core-v2-audit-29224543624-1
artifact SHA-256:
  e1f00cad76ac2799b8006e01cfdf6ba47f9348b4074d664bb4d1a2314716b6b2
```

The subsequently synchronized pre-documentation PR head:

```text
f8dc519d38e9187f809b4e2d00a0432e847a1f41
```

passed:

```text
workflow run: 29224928725
artifact: formal-core-v2-audit-29224928725-1
artifact SHA-256:
  83d7d00838a6849254fc981ea7448b90f461e183c89cacb8621d5c723441d74c
```

Later documentation-only synchronization commits may have newer successful
workflow runs. Use `audit_metadata.txt` inside the downloaded artifact rather than
assuming that an artifact name refers to a particular source head.

## Download from GitHub UI

1. Open the repository **Actions** tab.
2. Open the relevant **Formal Core v2 Lean build** run.
3. Confirm that the checkout commit matches the intended branch head.
4. Download the artifact listed under **Artifacts**.
5. Verify the external SHA-256 if a digest is recorded in the closure record or
   release notes.

## Verify the ZIP digest

Linux or macOS:

```bash
sha256sum formal-core-v2-audit-<run-id>-<attempt>.zip
```

Windows PowerShell:

```powershell
Get-FileHash `
  .\formal-core-v2-audit-<run-id>-<attempt>.zip `
  -Algorithm SHA256
```

## Failure artifacts

The workflow uploads the audit directory even when an earlier step fails. A
failure archive may therefore contain only:

```text
paper pin output
partial metadata
partial or failed build log
one or more missing later audit reports
```

Do not interpret the presence of an artifact as a passing validation. Check the
workflow conclusion and every required summary file.

## Required passing evidence

A Formal Core v2 validation is complete only when all of the following hold at the
same checkout commit:

```text
paper/source pin audit passes
lake build passes
no admitted-proof token is found
no project-local axiom declaration is found
Gate A axiom audit elaborates and contains no sorryAx
Gate B axiom audit elaborates and contains no sorryAx
RCLM axiom audit elaborates and contains no sorryAx
artifact is uploaded and attributable to that checkout
```

## What the audit archive does not establish

The archive does not prove:

```text
exact full Paper I or Paper II semantic identity
successor availability from checker soundness
strict improvement at every recursive step
arbitrary learned-system entry
unbounded grammar or generator completeness
Gate C quantum closure
Python checker/generator refinement
an empirical RSI or benchmark result
```

Those claims require separate Lean declarations, refinements, and evidence.