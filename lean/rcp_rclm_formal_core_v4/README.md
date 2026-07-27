# RCP/RCLM Formal Core v4

Formal Core v4 adds **Gate E: Constructive Endogenous Successor Availability and Recursive
Productivity** over the unchanged Formal Core v3 Gate D package.

The initial theorem surface proves deterministic finite-search soundness, proof-carrying
exhaustion, relative bounded-search completeness, recursive-productivity retention, finite
trajectory bounds, and conditional infinite autonomous trajectory construction.

Build:

```bash
cd lean/rcp_rclm_formal_core_v4
lake update
lake exe cache get
lake build
```

Claim boundaries and assumptions are recorded under `docs/formal_core_v4/`.

This foundation does not itself claim a completed schedule-free Phase 14 trajectory or generic
successor availability.
