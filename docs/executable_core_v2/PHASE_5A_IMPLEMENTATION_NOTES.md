# Phase 5A implementation notes

The implementation is intentionally modular rather than a single generated file:

```text
rcp_rclm_runtime/generator/records.py          immutable schemas and reports
rcp_rclm_runtime/generator/grammar.py          worker-safe finite grammar
rcp_rclm_runtime/generator/reference.py        control-plane reference input builders
rcp_rclm_runtime/generator/sandbox.py          worker audit and import policy
rcp_rclm_runtime/generator/worker.py           isolated canonical stdin/stdout worker
rcp_rclm_runtime/generator/process.py          process orchestration and deterministic replay
rcp_rclm_runtime/generator/lean_conformance.py direct bounded-grammar Lean checks
rcp_rclm_runtime/generator/pipeline.py         certificate, selection, realization, Lean, checker
```

The package initializer uses lazy exports so starting the worker does not import the
checker-facing pipeline or reference builders. The worker imports only canonicalization,
schema, bounded grammar, record, and sandbox modules. Its startup self-test fails if a
checker module is already loaded.

This split keeps the untrusted proposal process separate from certificate construction,
selection, realization, Lean verification, and checker acceptance. The worker's
canonical request does not contain control-plane trust material. After startup, its
audit hook denies all filesystem opens and mutations, sockets, and subprocess creation.

The Phase 5A code does not add a hidden proposal score or success Boolean. Proposal
records carry only the finite grammar word, its bounded witness/proposal names,
resource count, and binding hashes.
