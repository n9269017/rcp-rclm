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
- [x] Linux, Windows, and macOS CI agree on the frozen conformance vectors.
- [x] The synchronized Phase 1 implementation head passes all CI jobs.
- [x] The validation workflow ID and artifact digest are recorded.

The machine-readable validation record is:

```text
python/rcp_rclm_runtime_v2/phase_1_validation.json
```

It records the clean implementation head, workflow run, all three platform artifact
digests, and the final cross-platform consistency artifact digest. The final
metadata-only PR head is validated separately and recorded on PR #15, avoiding a
self-referential source file that would need to predict its own future workflow ID.

## Licensing after Phase 1 closes

```text
Immutable runtime records: implemented
Exact and interval mathematical bedrock: implemented
Canonical serialization and hashing: implemented
Generated-source guard: implemented
Pinned Lean compiler/verifier bridge: licensed to begin, not implemented
Production successor checker: not licensed
Generator: not licensed
Promotion controller: not licensed
Independent replay: not licensed
PyTorch backend: not licensed
Benchmark adapter: not licensed
```

Phase 1 is closed at the deterministic runtime-bedrock boundary. The next phase may
build the pinned Lean verifier bridge and differential Python/Lean conformance
fixtures. The production aggregate checker remains after that bridge.
