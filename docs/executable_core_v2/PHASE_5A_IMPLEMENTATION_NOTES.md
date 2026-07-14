# Phase 5A implementation notes

The implementation is intentionally modular rather than a single generated file:

```text
rcp_rclm_runtime/generator/records.py   immutable schemas and reports
rcp_rclm_runtime/generator/reference.py bounded grammar and public input builders
rcp_rclm_runtime/generator/sandbox.py   worker audit policy
rcp_rclm_runtime/generator/worker.py    isolated stdin/stdout worker
rcp_rclm_runtime/generator/process.py   process orchestration and deterministic replay
rcp_rclm_runtime/generator/pipeline.py  certificate, selection, realization, Lean, checker
```

This split keeps the untrusted proposal process separate from certificate construction,
selection, realization, Lean verification, and checker acceptance. The worker imports
no checker implementation and its canonical request does not contain control-plane
trust material.

The Phase 5A code does not add a hidden proposal score or success Boolean. Proposal
records carry only the finite grammar word, its bounded witness/proposal names,
resource count, and binding hashes.
