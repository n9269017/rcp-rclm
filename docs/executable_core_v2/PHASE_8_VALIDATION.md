# Phase 8 independent-replay validation

## Validation state

Phase 8 is implementation-complete and cross-platform/pinned-Lean validated at the
finite reference scope.

```text
executable repair head:
2e59dfa655a5fddec944d354b349be58591b7c8d

validated branch head:
5363153531f3e49a8a4d5397d68c1c684d1d8c0a

validated PR merge-test commit:
8a6887370002c492230bdda98a8fff5213265588
```

The branch-head commit contains the repaired cross-platform test and replay-summary
serialization, together with the validation-state update that triggered the complete
Phase 0–8 matrix. GitHub Actions tested the corresponding PR merge-test commit against
`main`; the workflow artifacts retain both the branch head in their run metadata and
the checked merge-test commit in the closure record.

## Exact workflow matrix

All authoritative workflows completed successfully for the validated branch head:

| Phase | Workflow run | Result |
|---|---:|---|
| Phase 0 contract | `29416547696` | Success |
| Phase 1 bedrock | `29416547779` | Success |
| Phase 2 Lean bridge | `29416547703` | Success |
| Phase 3 checker | `29416547681` | Success |
| Phase 4 adversarial rejection | `29416547729` | Success |
| Phase 5A bounded generator | `29416547762` | Success |
| Phase 6 successor package | `29416547691` | Success |
| Phase 7 promotion controller | `29416547705` | Success |
| Phase 8 independent replay | `29416547686` | Success |

The Phase 8 workflow passed its Ubuntu, Windows, macOS, pinned validation, and final
closure jobs.

## Cross-platform regression

```text
Python files scanned: 173
source-quality issues: 0

Phase 1 tests:  74 passed
Phase 2 tests:  19 passed
Phase 3 tests:  20 passed
Phase 4 tests:  10 passed
Phase 5A tests: 18 passed
Phase 6 tests:  22 passed
Phase 7 tests:  17 passed
Phase 8 tests:  23 passed
```

Each platform also completed the deterministic Phase 8 reference roundtrip.

## Pinned independent replay

The pinned job completed:

```text
complete Formal Core v2 build
all ten Phase 2 differential cases
both Phase 5A reference loops
both Phase 6 reference packages
pinned Phase 7 finite source trajectory
portable Phase 8 bundle construction
removal of generator/process.py and generator/worker.py
fresh pinned-Lean independent replay
zero-generator-invocation verification
generated-Lean admission/local-axiom scan
```

The independently reproduced pinned result is:

```text
verdict:                accept
generator invocations:  0
generator modules:       []
promotions reproduced:   2
rejections reproduced:   2
indeterminate entries:   0
package count:            3
```

Pinned package chain:

```text
0a80ac68151d9c64915472b0611d983f01622988cc32187ce9ff822c343c1211
→ 2928737e7f0edee72ea613b0c92d68eb62a2c3e318ecacb07fe6d35edbb4d8f5
→ a67beefadb254fd196ad6eca030334cdaccdee63f36a5e40a520e3e91928db52
```

Pinned evidence hashes:

```text
project pin hash:
32cbf7de4cf65298568432322fb428bceb4cb66269be934de537d0c8991a66d9

Phase 7 trajectory hash:
b7b74915825d4b6f35a91bc2af308f3e26e6f5f71af260d343612a40b8b685f5

source store tree hash:
955b2ed0ff753f4fbb2bac9613c99d3ac9479b2822972015a22539cc2bc931c5

replay bundle manifest hash:
dad5af369e0c103bad9de16a7b00f5ca499f119630660fca21ecd1d66ba9cf73

independent replay report hash:
5873599bc12358b2ad51a1cfa59558bd1aaa0c0cfc79ffbee2845f563d59f1e8

final active pointer hash:
0ed2999ebe545ede3b7b6ca4bb9dad54cae15f0d8c6c53b8492dfac0ac261358

ledger head hash:
4c3b5a36e95bf0c22d9fbf0f5e7da42449fde60890b4acb8deae830ad0652001
```

The four replay-attempt reports all have replay verdict `accept`: for the first two,
that means the captured promotions were recomputed; for the final two, it means the
captured nonpromotion outcomes were recomputed correctly. Every attempt records zero
generator invocations.

## Fixture-backed deterministic evidence

The platform fixture roundtrip remains separately recorded:

```text
source Phase 7 trajectory hash:
bb5440c2fc8abfa077ff500c19047305b417777accdd32c447185974755a092a

source store tree hash:
c88e84190c0d519001f415b1b1e5cbb583d4bf3110d14d6488c54dd725052d56

replay bundle manifest hash:
f9add553db0379f33fcbda5a52798b9f926aff5b29777d9832aa4e5ecf11f9b0

independent replay report hash:
17cea55d51f85581eac90e6397561ec86d5cda39b675eccb6061036253c92d67

roundtrip hash:
5f183f12a139cb50f3e68f437341526a38714fc7061a06b2ea1e1fa0698e7471
```

## Artifact digests

```text
final closure:
d1d741e788202c42e800a49da6a176f24e1b186e511bbc688e3284893878065a

pinned Lean and independent replay:
0fc9c9d997df290f5c535383f36b05489632e3bf477ef588b1dd680684828990

Ubuntu:
0bb208add8ded7a5cf7f7741ae84137f90b9f4477681648797a85fa833f8cb34

Windows:
b4728d2b29ca322921012a73a45466151b82a999b7c157e781f347cbebc69c1f

macOS:
3d7f4a5cc0f511dcd543b03cca02e920f08cf3009186f7598e87285bc7d8f189
```

## Attack coverage

The 23 Phase 8 tests cover strict bundle/report round trips, canonical bundle layout,
raw generator-output tampering, predecessor and candidate tampering, evaluation and
certificate tampering, checker/resource/rollback tampering, promotion-parent
substitution, rejection replay, Lean rejection and semantic disagreement, replay-source
capability rejection, zero generator invocation, two-fresh-directory determinism, and
existing-output protection.

## Claim boundary

The validated result supports only:

> A finite executable theorem-to-runtime refinement witness for the declared Gate B
> reference promotion path, with fail-closed successor promotion, retained rejection
> evidence, and independent generator-free replay; together with continued selected
> diagonal Gate C checker and Lean-conformance regression.

It does not establish generator trust, open-ended-generator correctness, learned
PyTorch proposal authority, arbitrary learned-system refinement, general noncommuting
quantum semantics, strict useful improvement at every step, unbounded successor
availability, external benchmark performance, or autonomous/unbounded RSI.
