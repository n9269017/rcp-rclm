# Release Notes

## v3-phase13-closure - 2026-07-26

This repository state closes the selected Formal Core v3 and Executable Core v3
trajectory through Phase 13 while preserving the narrower historical and v2
claim boundaries.

### Included

- Historical Lean v1 canonical finite RCP/RCLM certificate.
- Formal Core v2 Gates A, B, and the selected commuting/diagonal Gate C scope.
- Executable Core v2 Phases 0–8.
- The declared CPU-only PyTorch learned-successor pilot.
- Formal Core v3 Gate D learned-frontier contract.
- Executable Core v3 Phases 9–13.
- The selected independently replayed `M0 -> M4` successor trajectory.
- Cross-platform structural replay on Ubuntu, Windows, and macOS.
- Cross-platform pinned Lean and immutable-chain replay on Ubuntu, Windows, and macOS.
- Six-report Phase 13 aggregation and Draft 2020-12 schema validation.
- Permanent audit tags for the exact validated Gate D and Phase 9–13 source heads.

### Phase 13 closure evidence

```text
certified Phase 13 source head:
f7708932cdde13f6403aef43e3a152ce5ce5ce93

original complete closure workflow:
30071529144

original final closure artifact:
8589413591

post-merge finalization head:
c5556ac41b30a3bafb4ee28d1060651529e675fc

post-merge revalidation workflow:
30182521191

post-merge final closure artifact:
8626413241

ancestry-preserving main merge:
b0c616b35a430d803d0e7b40a0d9675d58d86c42
```

The post-merge finalization preserves the exact certified Phase 13 head as an
ancestor of `main`, removes completed one-shot transport scaffolding and
generated editable-install metadata, and retains the Phase 12E source audit
archive.

### Accepted boundary

```json
{
  "accepted": true,
  "phase13_exit_closed": true,
  "next_phase": 14
}
```

### Scope limitation

This is a finite, selected, domain-relative successor-verification and replay
result. It does not establish generic successor availability, arbitrary
learned-system refinement, autonomous or empirically unbounded RSI, general
noncommuting quantum semantics, generator completeness, or universal successor
trust.

### Presentation status

The root and component README presentation surfaces are intentionally unchanged
in this metadata release and may be updated in a later documentation-only pass.
The checksum manifest records the current unchanged README bytes and the updated
metadata files in this release.

## v1.0-preprint - 2026-06-29

Initial preprint/artifact package for the RCP/RCLM robust reflective successor-verification project.

### Included

- Paper I: RCP/RCP-II mathematical theorem paper (`papers/paper-I-rcp-math/`).
- Paper II: RSI--RCLM architecture instantiation paper (`papers/paper-II-rclm-architecture/`).
- Shared Lean 4 proof project (`lean/rcp_rclm_can_lean4/`).
- RCP controlled executable reference artifact and checker (`artifacts/rcp/`).
- RCLM controlled executable reference artifact and checker (`artifacts/rclm/`).
- Documentation: overview, claim boundary, notation table, theorem dependency graph.

### Lean status

Lean 4 certificate supplied for the canonical finite RCP/RCLM witness and refinement core.

Checked commands reported for the v5 root-module project:

```text
lake env lean .\RcpRclmMech\RCP.lean
lake build RcpRclmMech.RCP
lake env lean .\RcpRclmMech\RCLM.lean
lake build RcpRclmMech.RCLM
lake env lean .\RcpRclmMech.lean
lake build
```

### Scope limitation

The full 219-page mathematical paper and 187-page architecture paper are not fully mechanized. The Lean certificate covers only the canonical finite witness, checker core, and RCLM-to-RCP refinement module.

### Not claimed

This release does not claim arbitrary trained-system entry, broad learned-agent RSI, universal successor trust, frontier-scale tractability, or empirical deployment validation.
