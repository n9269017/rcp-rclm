# Phase 0 exit criteria

Phase 1 runtime-bedrock work may begin only when every required Phase 0 item is
complete on one synchronized branch head.

## Formal-source freeze

- [x] Formal source commit is pinned.
- [x] Lean toolchain and mathlib commit are pinned.
- [x] Formal manifest blob is pinned.
- [x] Selected Gate C validation record is pinned.
- [x] Gate A, Gate B, selected Gate C, and RCLM public object surfaces are named.

## Object correspondence

- [x] Every mapped object has a Lean declaration.
- [x] Every mapped object has a schema identifier.
- [x] Every mapped object has a reserved immutable Python type name.
- [x] Every mapped object has a reserved runtime function name.
- [x] Every mapped object has a certificate-evidence identifier.
- [x] Every mapped object has a conformance-test identifier.
- [ ] Phase 1 implementations exist for the reserved Python interfaces.

The final unchecked item belongs to Phase 1 and is not required to declare the
contract frozen.

## Trust boundary

- [x] Root-of-trust inputs are enumerated.
- [x] Trusted-after-validation components are enumerated.
- [x] Untrusted components are enumerated.
- [x] Generator/checker process separation is required.
- [x] Generator self-certification is forbidden.
- [x] Manual override-to-accept is forbidden.

## Numerical semantics

- [x] Canonical integer representation is frozen.
- [x] Reduced rational representation is frozen.
- [x] Exact distribution normalization is required.
- [x] Selected diagonal density construction is frozen.
- [x] Selected identity/swap channel semantics are frozen.
- [x] Support semantics are frozen.
- [x] Certified interval representation is frozen.
- [x] Adaptive precision schedule and maximum are frozen.
- [x] Strict-progress and non-loss decision directions are frozen.
- [x] NaN, infinity, and boundary overlap are fail-closed.

## Serialization and hashing

- [x] Canonical JSON profile is frozen.
- [x] Unicode normalization is frozen.
- [x] Path normalization is frozen.
- [x] Semantic file record is frozen.
- [x] Semantic tree hash is frozen.
- [x] Candidate, certificate, parent, and trust-anchor linkage are frozen.
- [x] Timestamp exclusion from semantic hashes is frozen.

## Acceptance semantics

- [x] Tri-state verdict domain is frozen.
- [x] Only `accept` is promotable.
- [x] Complete obligation conjunction is enumerated.
- [x] Evaluation order is frozen.
- [x] Stable reason-code namespace is reserved.
- [x] Candidate assertions are nonauthoritative.
- [x] Internal errors are fail-closed.
- [x] Lean-backed conformance is mandatory for the initial runtime.

## Claim boundary

- [x] Phase 0 contract-only claim is explicit.
- [x] First executable reference claim is explicit.
- [x] General noncommuting quantum claims are excluded.
- [x] Arbitrary learned-system entry is excluded.
- [x] Indefinitely strict recursive improvement is excluded.
- [x] External benchmark claims are excluded.
- [x] Historical v1 artifacts are excluded from automatic v2 refinement.

## Machine-readable artifacts

- [x] `runtime_contract_manifest.json` exists.
- [x] `runtime_records.schema.json` exists.
- [x] Standard-library contract validator exists.
- [x] Contract-validator unit tests exist.
- [x] Contract CI workflow exists.
- [x] Clean CI validates the frozen contract, source pins, and mapped declaration surfaces.
- [x] The first clean validation report and artifact digest are recorded in
  `phase_0_validation.json` and `PHASE_0_VALIDATION.md`.
- [x] The final synchronized source head is required to pass the same workflow and
  is recorded on PR #14, avoiding a source file that self-references its own future
  workflow identifier.

## Phase 0 closure

```text
Phase 0 theorem-to-runtime contract: COMPLETE
Phase 1 runtime bedrock: LICENSED TO BEGIN
Production mathematical runtime engine: NOT IMPLEMENTED
Production checker: NOT IMPLEMENTED
Generator: NOT IMPLEMENTED
Promotion controller: NOT IMPLEMENTED
PyTorch backend: NOT IMPLEMENTED
Benchmark adapter: NOT LICENSED
```

## Python licensing status

```text
Contract validator licensed: true
Phase 1 immutable records and exact numerical bedrock: licensed to begin
Production checker licensed: false
Generator licensed: false
Promotion controller licensed: false
PyTorch backend licensed: false
Benchmark adapter licensed: false
```

## Next phase

The next branch may implement only the runtime bedrock:

```text
immutable records
strict parsers
exact rationals
certified intervals
selected Gate B mathematics
selected Gate C diagonal mathematics
canonical serialization
content and tree hashing
```

The production checker, generator, and promotion loop remain later phases.
