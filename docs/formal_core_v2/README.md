# RCP/RCLM Formal Core v2 Documentation

This directory documents the pinned Lean 4 theorem package underlying the RCP/RCLM v2
runtime. Gates A, B, and the selected Gate C instance are complete at their declared
scopes. Executable Core v2 Phases 0–8 and the first bounded PyTorch pilot consume this
formal surface without enlarging its claims.

## Formal status

| Gate | Status | Scope |
|---|---|---|
| Gate A | Complete, clean-CI built, axiom audited | Abstract conditional successor verification, finite composition, endpoint recovery, monitors, and conditional infinite closure under explicit successor availability |
| Gate B | Complete | Finite classical distributions, Shannon entropy, support-aware KL, conservative zero extension, exact recovery, binary improvement/stability checker, and finite trajectories |
| RCLM-to-RCP refinement | Complete at the binary reference scope | Architecture state/update/certificate mapping, checker refinement, recovery/monitor transport, and trust/resource/domain premises |
| Gate C | Complete and audited at the selected commuting/diagonal scope | Certified complex diagonal density matrices, spectral von Neumann entropy, support-aware diagonal QRE, identity/swap channels, exact selected recovery, checker, trajectory, and RCLM refinement |
| General noncommuting extension | Open | No arbitrary noncommuting densities, general CPTP maps, matrix-log QRE, general data-processing theorem, or Petz recovery |

Pinned project:

```text
lean/rcp_rclm_formal_core_v2/
Lean:    leanprover/lean4:v4.31.0
mathlib: fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
formal source commit: 012de4a55f326107f53f0e215c8aec62859d0bbf
```

## Documentation map

```text
THEOREM_CONTRACT.md              formal theorem and assumption boundary
GATE_A_*.md                      abstract-kernel design, closure, and audit
GATE_B_*.md                      finite classical/KL instance and closure
GATE_C_*.md                      selected diagonal-quantum scope and closure
RCLM_*.md                        architecture refinement and direct-engine status
ASSUMPTION_REGISTER.md           explicit premises and open assumptions
EXIT_CRITERIA.md                 formal completion and remaining open work
audit/                           Lean axiom-audit entry points and retained output
```

## Relation to Executable Core v2

The executable package does not treat a Python reimplementation as automatically covered
by Lean. It uses a pinned bridge and differential tests:

```text
canonical packet
→ independent Python interpretation
→ deterministic Lean source generation
→ pre-compilation rejection of sorry, sorryAx, admit, and local axiom declarations
→ pinned Lean compilation
→ structured RCP/RCLM verdict parsing
→ fail-closed differential comparison
```

Phases 3–8 then build the checker, attack suite, bounded generator, filesystem realizer,
promotion controller, and independent replay around that bridge.

The first PyTorch pilot does not add a learned theorem. Its model objective is evaluated
by framework-independent exact integer arithmetic. The formal packet remains the existing
Gate B stability reference, and the documentation explicitly records that Lean and the
checker do not prove the learned accuracy objective. PyTorch remains an untrusted proposal
source.

## Reproduction

```bash
cd lean/rcp_rclm_formal_core_v2
lake update
lake exe cache get
lake build
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateBAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateCAxiomAudit.lean
```

Executable bridge and runtime reproduction are indexed at
`docs/executable_core_v2/README.md`.

## Claim boundary

The formal package proves conditional verification and selected finite instances. The
conditional infinite theorem assumes successor availability; it does not prove generator
completeness or useful strict improvement at every recursive step. The selected Gate C
instance is not a theorem about arbitrary noncommuting quantum systems, and the PyTorch
pilot is not a proof of arbitrary learned-system refinement or autonomous RSI.
