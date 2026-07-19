# RCP/RCLM Formal Core v3 documentation index

This directory is the control plane for **Gate D: learned capability-frontier
RCLM refinement**.

Gate D is layered over the unchanged and already validated Formal Core v2 project:

```text
lean/rcp_rclm_formal_core_v2/
```

The new project is:

```text
lean/rcp_rclm_formal_core_v3/
```

## Current status

```text
Gate D abstract learned-frontier kernel: implemented
Gate D trusted learned-checker refinement: implemented
Gate D one-step soundness theorem: implemented
Gate D finite strict-frontier growth: implemented
Gate D conditional infinite trajectory: implemented with explicit availability
Gate D one-step Gate B RCLM reference: implemented
Pinned build and public axiom audit: successful for the implementation head
Real learned-language-model refinement: not yet implemented
Open-ended self-hosted generator: not yet implemented
Autonomous or unbounded RSI: not proved
```

## Reading order

```text
1. GATE_D_SCOPE.md
2. GATE_D_THEOREM_CONTRACT.md
3. GATE_D_ASSUMPTION_REGISTER.md
4. GATE_D_EXIT_CRITERIA.md
5. GATE_D_VALIDATION.md
6. audit/GateDAxiomAudit.lean
7. ../../lean/rcp_rclm_formal_core_v3/README.md
```

## Authority order

When records disagree, use:

```text
1. compiled Lean declarations and their explicit hypotheses
2. public theorem axiom audit
3. formalization manifest and assumption register
4. theorem contract and scope record
5. validation and exit-criteria records
6. README summaries
```

A README may explain the Gate D theorem but may not strengthen it.
