# Phase 1 runtime-bedrock exit criteria

## Required implementation

- [x] Python 3.11+ package boundary exists.
- [x] Runtime records are frozen and strict parsers reject unknown fields.
- [x] Exact reduced rational arithmetic exists.
- [x] Native float conversion is forbidden for authoritative rationals.
- [x] Closed rational interval records enforce 128 through 4096 precision bits.
- [x] Positive-rational logarithms use exact series terms and a rational tail bound.
- [x] Gate B distributions require exact normalization.
- [x] Shannon entropy and support-aware KL share the certified logarithm backend.
- [x] Zero-coordinate extension and exact recovery are implemented.
- [x] Gate C density records use spectra as the sole source of truth.
- [x] Derived dense matrices require exact diagonal complex-rational layout.
- [x] Von Neumann entropy reuses the Shannon implementation.
- [x] Diagonal QRE reuses the KL implementation.
- [x] Identity and two-element basis-swap channels are exact permutations.
- [x] Selected recovery is the exact inverse permutation.
- [x] Canonical JSON and strict canonical parsing are implemented.
- [x] Semantic path validation is implemented.
- [x] Content and semantic-tree hashing are implemented with frozen domains.
- [x] RCLM-to-RCP forgetful mappings are implemented.
- [x] Generated Lean source is guarded before any future compiler process.

## Required validation

- [x] Standard-library unit tests cover exact rationals.
- [x] Unit tests cover certified log enclosures and width bounds.
- [x] High-precision diagnostic references fall inside the exact enclosures.
- [x] Unit tests cover Gate B support, entropy, KL, extension, and recovery.
- [x] Unit tests cover Gate C density evidence, channels, QRE, and recovery.
- [x] Unit tests cover canonical JSON, paths, and tree hashes.
- [x] Unit tests cover strict runtime-record parsing and hash linkage.
- [x] Unit tests cover generated-Lean source rejection.
- [x] Frozen cross-platform conformance vectors exist.
- [ ] Linux, Windows, and macOS CI agree on the frozen conformance vectors.
- [ ] The final synchronized Phase 1 branch head passes all CI jobs.
- [ ] The final workflow ID and artifact digest are recorded.

## Licensing after Phase 1 closes

```text
Immutable runtime records: implemented
Exact and interval mathematical bedrock: implemented
Canonical serialization and hashing: implemented
Generated-source guard: implemented
Lean compiler/verifier bridge: not yet licensed as complete
Production successor checker: not yet licensed
Generator: not licensed
Promotion controller: not licensed
PyTorch backend: not licensed
Benchmark adapter: not licensed
```

The next phase may build the pinned Lean verifier bridge and differential
Python/Lean conformance fixtures. The production aggregate checker remains after
that bridge.
