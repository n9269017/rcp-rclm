# Phase 13 post-merge ancestry and closure attestation

## Purpose

PR #36 was certified at exact source head
`f7708932cdde13f6403aef43e3a152ce5ce5ce93` by the complete Phase 13
workflow. GitHub subsequently integrated the PR through squash commit
`dc8a1016d1f5e656f1644185207bd1798c5ce328`. The squash preserved the
certified source tree byte-for-byte but did not preserve the certified head as
an ancestor of `main`.

The no-content merge commit
`883118f811139c1f858103ef77fbe1c05d2a2cdf` repairs that provenance boundary.
Its first parent is the squash integration commit and its second parent is the
exact certified Phase 13 head. It introduces no repository-content difference
relative to its first parent.

## Exact Git identity

```text
pull request:
36

certified Phase 13 source head:
f7708932cdde13f6403aef43e3a152ce5ce5ce93

GitHub squash integration commit:
dc8a1016d1f5e656f1644185207bd1798c5ce328

post-merge ancestry bridge:
883118f811139c1f858103ef77fbe1c05d2a2cdf

ancestry-bridge parents:
dc8a1016d1f5e656f1644185207bd1798c5ce328
f7708932cdde13f6403aef43e3a152ce5ce5ce93

certified-head Git tree:
0514afaf633a62256b7a316be69a3c363b86ea70

squash-integration Git tree:
0514afaf633a62256b7a316be69a3c363b86ea70
```

Therefore the initial integration preserved the complete certified source
bytes, and the ancestry bridge additionally preserves the exact certified
commit as a reachable ancestor without rewriting `main`.

## Authoritative Phase 13 closure evidence

```text
authoritative workflow:
30071529144

workflow conclusion:
success

bundle manifest hash:
8fb457b08aaf587dd408b686ff66b0df7ea4079f74257c7fbc283bbf01e56da8

Phase 13A report hash:
0f7112dc5daf98fca9a439ea0fe364358423c836d4e7a7c26c4f109b3f53ada1

structural report hash:
ce364b0c5a03c85aaf6b5581b915e4f5a2a2d861b95dcb7dace528b6c5b2e0c5

pinned report hash:
9001b4c857fa811c6a282af2884bbbd65ee33d77f580f280d7d585b801187bc0

exit report hash:
1967dad3254e7c62c33971929d6937b4e62722260719a2360162b27deaefb49f

exit JSON SHA-256:
37fd111b8a2979dd33387cd0186c251396ccb670d52165598ebef0684dfbccb1

final closure artifact ID:
8589413591

final closure artifact SHA-256:
2ef167a5969c1372e96472351192e02ed1a036dc91c91f80a4a7465b5bdb8715
```

The workflow passed authoritative `M0 -> M4` capture, independent structural
replay on Ubuntu, Windows, and macOS, pinned Lean and immutable-chain replay on
all three platforms, six-report aggregation, byte-identical tool and repository
closure entry points, and Draft 2020-12 schema validation.

## Final accepted boundary

```json
{
  "accepted": true,
  "phase13_exit_closed": true,
  "next_phase": 14
}
```

This is a finite, selected, independently replayed trajectory result. It does
not establish generic successor availability, arbitrary learned-system
refinement, autonomous RSI, unbounded empirical RSI, or the general
noncommuting quantum extension.

## Repository-hygiene boundary

The post-merge finalization removes generated editable-install metadata and the
completed one-shot Phase 12E payload transport fragments. The retained
`artifacts/phase12e-source/` audit archive and its digest remain preserved.

README presentation changes are intentionally excluded from this attestation
commit and may be supplied separately without altering the certified Phase 13
source identity recorded above.

## Branch-retirement boundary

The Gate D and Phase 9-13 development branches may be deleted only after:

1. this ancestry-preserving finalization is merged with a merge commit;
2. the resulting `main` checks complete successfully;
3. `f7708932cdde13f6403aef43e3a152ce5ce5ce93` is confirmed as an ancestor of
   updated `main`; and
4. permanent audit tags for the exact validated Gate D and Phase 9-13 heads
   have been pushed.
