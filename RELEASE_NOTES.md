# Release Notes

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
