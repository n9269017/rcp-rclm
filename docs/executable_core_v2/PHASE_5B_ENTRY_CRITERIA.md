# Phase 5B open-ended generator entry criteria

Phase 5B may begin only after Phase 5A has a clean exact-head validation record and the
bounded reference loop is reproducible from retained canonical inputs.

Every Phase 5B implementation remains untrusted. Search, program synthesis,
LLM/scaffold proposals, learned policies, and training-driven updates may produce only
proposal records. They may not:

```text
modify or import checker source through a privileged interface
receive trust-anchor secrets or promotion-ledger write access
receive reference answers used by authoritative evaluation
construct an authoritative checker or Lean verdict
control candidate promotion
supply candidate assertions as proof
bypass Phase 4 package-integrity checks
```

Before an open-ended generator is connected to the controller, it must have:

- a versioned public policy and strict input/output schema;
- a declared resource budget and timeout;
- captured raw standard input, output, and error bytes;
- immutable model/program/scaffold hashes where applicable;
- explicit randomness and seed records where applicable;
- a platform sandbox profile stronger than the Phase 5A source-only capability gate;
- deterministic replay where the backend permits it, or an explicit nondeterminism record;
- adversarial malformed-output and capability-escalation tests;
- no authority over certificate construction, realization, checking, Lean verification, or promotion.

PyTorch does not enter the mathematical checker. Native floating-point model output may
rank or propose candidates, but exact rational and certified-interval recomputation
remains checker-owned.
