# Formal Core v2 documentation index

This directory is the documentation control plane for the active pinned project:

```text
lean/rcp_rclm_formal_core_v2/
```

It separates four things that must not be conflated:

```text
compiled Lean declarations
paper-facing semantic identifications
concrete finite reference instantiations
future or executable claims not yet licensed
```

## Current gate status

| Area | Status | Authoritative record |
|---|---|---|
| Gate A abstract theorem kernel | Complete and audited | `GATE_A_ALIGNMENT_RESOLUTION_LOG.md`, `AXIOM_AUDIT.md` |
| Gate B finite classical/diagonal instance | Complete at the declared finite reference scope | `GATE_B_CLOSURE.md` |
| Gate B RCLM-to-RCP refinement | Complete at the declared binary reference scope | `RCLM_GATE_B_REFINEMENT_STATUS.md` |
| Conditional architecture successor/direct-engine theorem | Implemented and audited | `RCLM_DIRECT_ENGINE_STATUS.md` |
| Paper II bounded seed-library and packet builder | Complete at the declared binary reference scope | `PAPER_II_BOUNDED_SEED_LIBRARY_REFINEMENT.md` |
| Gate C finite-dimensional quantum instance | Complete and audited at the selected commuting/diagonal matrix scope | `GATE_C_SCOPE.md`, `GATE_C_CLOSURE.md` |
| General noncommuting quantum extension | Not complete | `GATE_C_CLOSURE.md`, `ASSUMPTION_REGISTER.md` |
| Exact Paper I equivalence | Not complete | `PAPER_THEOREM_MAP.md`, `ASSUMPTION_REGISTER.md` |
| Exact Paper II equivalence | Not complete | `PAPER_THEOREM_MAP.md`, `ASSUMPTION_REGISTER.md` |
| Executable checker/generator/closed loop | Not licensed | `EXIT_CRITERIA.md` |

## Recommended reading paths

### Reviewer or auditor

```text
1. THEOREM_CONTRACT.md
2. PAPER_THEOREM_MAP.md
3. ASSUMPTION_REGISTER.md
4. EXIT_CRITERIA.md
5. AXIOM_AUDIT.md
6. Gate-specific closure/status record
7. REPRODUCIBILITY.md
8. AUDIT_ARTIFACTS.md
```

For Gate C, read `GATE_C_SCOPE.md` followed by `GATE_C_CLOSURE.md`.

### Lean contributor

```text
1. ../../lean/rcp_rclm_formal_core_v2/README.md
2. THEOREM_CONTRACT.md
3. ASSUMPTION_REGISTER.md
4. PAPER_THEOREM_MAP.md
5. EXIT_CRITERIA.md
6. Gate-specific scope and closure record
7. audit files relevant to the declarations being changed
```

### Reproducer

```text
REPRODUCIBILITY.md
AUDIT_ARTIFACTS.md
AXIOM_AUDIT.md
```

## Core control documents

### `THEOREM_CONTRACT.md`

Freezes the ordinary-mathematics and Lean-facing contract. It states the one-step
successor theorem, finite and conditional infinite composition, recovery and
monitor boundaries, concrete reference meanings, RCLM refinement, and architecture
engine assumptions.

### `PAPER_THEOREM_MAP.md`

Maps the pinned Paper I and Paper II theorem surfaces to Lean declarations. Its
status vocabulary distinguishes exact, abstract exact, concrete-reference exact,
structural, deferred, and mismatch results.

A declaration appearing in the map does not automatically mean that the full
paper semantics have been mechanized.

### `ASSUMPTION_REGISTER.md`

Records every theorem premise, who supplies it, where it is represented, and
whether it is discharged in the current reference scope. It also records explicit
non-implications such as:

```text
checker soundness does not imply successor availability
checker soundness does not imply grammar nonemptiness
accepted continuation does not imply strict useful improvement
finite grammar completeness does not imply unbounded proof-search completeness
selected diagonal QRE does not imply general noncommuting matrix QRE
identity/swap preservation does not imply general CPTP data processing
```

### `EXIT_CRITERIA.md`

Defines when Gate A, Gate B, the selected Gate C reference, paper-facing closure,
and any later executable phase may be claimed complete. It is the licensing
boundary for Python/runtime work.

### `AXIOM_AUDIT.md`

Explains the distinction between:

```text
admitted proof tokens in project source
project-local axiom declarations
standard Lean/mathlib foundational dependencies reported by #print axioms
```

## Gate-specific records

### Gate A

```text
GATE_A_PAPER_ALIGNMENT_AUDIT.md
GATE_A_ALIGNMENT_RESOLUTION_LOG.md
```

The first document records the initial paper-to-Lean mismatch audit. The second
records the abstract resolutions and the remaining concrete semantic work.

### Gate B

```text
GATE_B_CLOSURE.md
RCLM_GATE_B_REFINEMENT_STATUS.md
RCLM_DIRECT_ENGINE_STATUS.md
PAPER_II_BOUNDED_SEED_LIBRARY_REFINEMENT.md
```

Together these documents define the exact finite classical scope, the substantive
RCLM refinement, the conditional architecture theorem, and the bounded packet
builder.

### Gate C

```text
GATE_C_SCOPE.md
GATE_C_CLOSURE.md
audit/GateCAxiomAudit.lean
```

The selected Gate C reference uses finite complex diagonal density matrices,
spectral von Neumann entropy and quantum relative entropy, identity/swap matrix
channels, exact candidate-tied recovery, a concrete checker, a finite accepted
trajectory, and substantive RCLM refinement.

The closure is limited to the declared commuting/diagonal two-level reference.
General noncommuting density matrices, arbitrary CPTP channels, general matrix-log
QRE, data processing, and Petz/approximate recovery remain open.

## Reproducibility and artifacts

### `REPRODUCIBILITY.md`

Contains the exact local and CI build sequence, dependency pins, paper-source pin
check, theorem-axiom audit commands, Windows cache recovery, and clean-tree
requirements.

### `AUDIT_ARTIFACTS.md`

Catalogs the files uploaded by `.github/workflows/formal-core-v2.yml` and explains
how to interpret build logs, source scans, local-axiom scans, and the Gate A,
Gate B, RCLM, and Gate C theorem-axiom reports.

## Audit source files

```text
audit/verify_paper_alignment_pins.sh
audit/GateAAxiomAudit.lean
audit/GateBAxiomAudit.lean
audit/RCLMRefinementAxiomAudit.lean
audit/GateCAxiomAudit.lean
```

The shell audit pins the paper source blobs and required theorem surfaces. The
Lean audit files elaborate public declarations and print their kernel axiom sets.

## Machine-readable record

```text
../../lean/rcp_rclm_formal_core_v2/formalization_manifest.json
```

The manifest records exact toolchain and paper pins, gate status, validation
metadata, delivered interfaces, explicit non-implications, and the current claim
boundary.

## Authority hierarchy

When documents disagree, use this order:

```text
1. Compiled Lean declaration and its explicit hypotheses
2. Pinned source and theorem-surface audit
3. Formalization manifest and assumption register
4. Theorem map and theorem contract
5. Gate closure/status record
6. README or narrative summary
```

A README can explain a theorem but cannot strengthen it.

## Global claim discipline

The current package does not establish:

```text
exact full-paper mechanization
arbitrary learned-system entry
arbitrary or unbounded generator completeness
strict useful improvement at every recursive step
general noncommuting quantum closure
arbitrary CPTP data processing
Petz or approximate recovery
executable checker/generator correctness
closed-loop empirical RSI
external benchmark performance
```

Those statements remain false at the documentation level unless the corresponding
Lean declarations, refinements, audits, and exit criteria are completed.
