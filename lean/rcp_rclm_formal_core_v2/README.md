# RCP/RCLM Formal Core v2 — Mechanized Conditional Successor Theorem Closure

This is a new Lean project. It does not overwrite or silently strengthen the
historical canonical v1 project at `lean/rcp_rclm_can_lean4/`.

## Current milestone

Milestone 0 freezes the theorem contract, source mapping, reproducibility pins,
assumption boundary, and module ownership before substantive theorem
implementation proceeds.

Current status:

```text
Gate A — abstract theorem kernel: contract frozen; implementation started
Gate B — finite classical/diagonal instantiation: not yet claimed
Gate C — finite-dimensional quantum instantiation: not yet claimed
RCLM architecture refinement: contract only
Python checker/generator/closed loop: prohibited at this phase
External benchmark result: none
```

## Exact dependency pins

```text
Lean:    leanprover/lean4:v4.31.0
mathlib: fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
```

The mathlib commit is the v4.31.0 toolchain-bump release commit. The generated
`lake-manifest.json` must be committed after the first successful `lake update`
and before this project is called reproducible.

## The central contract

For an admissible predecessor state, candidate successor, and certificate packet,
a trusted checker acceptance must imply all of the following:

```text
typed successor validity
quantitative protected-distinction non-loss
constructive recovery/rollback bound
computed residual nonpositivity
protected-invariant preservation
progress nondecrease
strict progress when a strict witness is certified
trust/verifier validity
resource validity
reality/uncertainty containment
successor-domain admissibility
```

The finite composition theorem must show that these obligations compose through
any finite accepted trajectory.

The infinite-horizon theorem must remain explicitly conditional on a successor
availability/generator-completeness assumption. Checker soundness alone is not
an existence theorem for useful successors.

## Module plan

```text
RcpRclmFormalCoreV2/
  RCP/
    Types.lean
    ProtectedDistinctions.lean
    RelativeEntropy.lean
    Recovery.lean
    Progress.lean
    Certificates.lean
    Checker.lean
    Trajectory.lean
    InfiniteHorizon.lean
    ClassicalFinite.lean
    QuantumFinite.lean
  RCLM/
    State.lean
    Update.lean
    CertificatePacket.lean
    Refinement.lean
    ArchitectureTheorem.lean
  RCP.lean
  RCLM.lean
  MainTheorem.lean
```

## Build

From this directory:

```powershell
lake update
lake build
```

After the first successful dependency resolution, commit `lake-manifest.json`.

## Claim discipline

No module may use a constant divergence, fixed-zero residual vector, `True` as
reality containment, or architecture gates set true merely by construction and
then describe the result as the v2 theorem.

No Python checker, generator, successor loop, or benchmark adapter is licensed by
this project until the exit criteria in `docs/formal_core_v2/EXIT_CRITERIA.md`
are satisfied.
