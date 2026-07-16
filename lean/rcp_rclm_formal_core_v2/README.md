# RCP/RCLM Formal Core v2 — Lean 4 Project

This is the active pinned Lean project for RCP/RCLM v2. It contains the completed Gate A
abstract theorem kernel, the Gate B finite classical/KL instance and RCLM refinement, and
the selected Gate C commuting/diagonal quantum instance.

## Pins

```text
Lean:    leanprover/lean4:v4.31.0
mathlib: fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
```

The complete dependency graph is committed in `lake-manifest.json`. Runtime v2 pins the
formal source at commit:

```text
012de4a55f326107f53f0e215c8aec62859d0bbf
```

## Proven scope

### Gate A

- abstract kernels, candidates, and obligation bundles;
- trusted-checker soundness;
- recovery-composition laws and preservation monitors;
- finite accepted trajectories and endpoint recovery;
- conditional infinite closure under an explicit successor-availability premise.

### Gate B

- finite distributions and Shannon entropy;
- support-aware KL divergence;
- zero-coordinate conservative extension;
- exact recovery;
- binary improvement and stability references;
- concrete checker and finite trajectory;
- RCLM-to-RCP state/update/certificate, checker, recovery, monitor, and architecture
  refinement;
- finite bounded seed-library relations.

### Gate C

- certified complex diagonal density matrices derived from finite spectra;
- Hermitian, positive-semidefinite, and trace-one laws;
- spectral von Neumann entropy;
- support-aware diagonal QRE;
- identity and basis-swap channels;
- exact selected recovery;
- quantum checker, monitors, finite trajectory, and RCLM refinement.

Gate C remains intentionally limited to the commuting/diagonal reference. Arbitrary
noncommuting density matrices, general CPTP maps, matrix-log QRE, general data processing,
and Petz recovery are not implemented or claimed.

## Build

```bash
lake update
lake exe cache get
lake build
```

## Axiom audits

From this directory:

```bash
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateBAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateCAxiomAudit.lean
```

## Executable relationship

The Python Runtime v2 does not claim equivalence merely by matching names. Phase 2
generates restricted Lean certificate instances, scans them before compilation, invokes
this pinned project, parses structured verdicts, and compares Lean with an independent
Python interpretation. Phases 3–8 use that bridge for checker admission, promotion, and
independent replay.

The first PyTorch pilot remains outside this project's mathematical authority. It proposes
one changed model package; exact model evaluation is framework-independent, while Lean
continues to verify the declared Gate B stability packet used by the promotion path. No
learned accuracy theorem or arbitrary learned-system refinement theorem is claimed.

See `../../docs/formal_core_v2/README.md` for the formal documentation index and
`../../docs/executable_core_v2/README.md` for the executable phase index.
