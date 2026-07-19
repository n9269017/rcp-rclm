# Phase 9 Lean/Python/schema object map

| Semantic object | Lean declaration | JSON Schema definition | Immutable Python type | Runtime computation |
|---|---|---|---|---|
| Learned package state | `Learned.PackageState`; Phase 9 alias `LearnedRCLMState` | `$defs/LearnedRCLMState` | `LearnedRCLMState` | `state_hash`, `component_hash` |
| Learned update | `Learned.PackageUpdate`; Phase 9 alias `LearnedRCLMUpdate` | `$defs/LearnedRCLMUpdate` | `LearnedRCLMUpdate` | `update_hash`, operation/component equality |
| Learned certificate | `Learned.CertificatePacket`; alias `LearnedCertificatePacket` | `$defs/LearnedCertificatePacket` | `LearnedCertificatePacket` | `certificate_hash`, transition binding |
| Capability frontier | `CapabilityFrontier`, `FrontierRetention`, `FrontierExpansion` | `$defs/CapabilityFrontier` | `CapabilityFrontier` | exact subset and nonempty difference |
| Certified task | `CertifiedTask` | `$defs/CertificationRecord` plus `$defs/TaskRecord` | `CertificationRecord`, `TaskRecord` | current-model verifier binding |
| Task ledger | package frontier field plus `frontierSound` | `$defs/TaskLedger` | `TaskLedger` | task/certification uniqueness and lookup |
| Self-hosted generator | `SelfHostedGenerator` | `$defs/SelfHostingBinding` | `SelfHostingBinding` | state-hash and active-generator binding |
| Learned kernel refinement | `FrontierKernel`; alias `LearnedKernelRefinement` | contract manifest object map | transition validator inputs | Gate D-specific obligation recomputation |
| Learned checker refinement | `TrustedLearnedChecker`; alias `LearnedCheckerRefinement` | transition-report definition | `Phase9TransitionReport` | deterministic fail-closed report |
| Held-out isolation | executable refinement obligation | `$defs/HeldoutAccessPolicy` | `HeldoutAccessPolicy` | frozen access constants and policy hash |

## Correspondence rule

For every Phase 9 semantic record:

```text
Lean declaration
↔ JSON Schema definition
↔ frozen Python dataclass
↔ canonical JSON hash
↔ deterministic reference fixture
↔ cross-platform conformance test
```

The Python records do not replace the Lean theorem. They freeze the executable packet
shape that later Phase 10 candidates must refine.
