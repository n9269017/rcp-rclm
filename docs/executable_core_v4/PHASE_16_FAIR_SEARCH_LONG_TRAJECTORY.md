# Phase 16 — fair search, recursive productivity, and long-trajectory scaling

Phase 16 begins from the exact accepted Phase 15 `M9` evidence and stress-tests the fixed diagonal/classical Gate E regime across longer certified lineages. It does not change the root verifier, semantic regime, or Phase 15 protected base package.

## Exact predecessor and learned-ranking boundary

The bootstrap verifier opens both retained Phase 15 archives and checks:

- final closure archive SHA-256 `197465275e7716a7a51eb4ffdc255696bd92129cdf0910e9712b7ca22028053e`;
- full bundle archive SHA-256 `56003f95ded054be21dd3f743c2145fdf6e92543af28bb350f64ec8f4fee00b5`;
- Phase 15 closure report `3c4d0b90143fddd5bcb1f8d9af266cda7b330dbec774fbe7d43708476fe99e49`;
- Phase 15 trajectory `0ed512aee0a7b75a8e533e189a2dec9840995ba9d583de175981dc931adc5b94`;
- bundle manifest `2426a8f5d4c4f0d327d55970b43441c274ca9b672a4280914a37a55b2ee31661`;
- final active store `2fd9aad1e508dae645e20b2545e274c1034fde109b6c2f4d5659eb17497bf472`;
- accepted `M9` semantic package `a20e01b73f6b6ab069ce93bcbb43d5b745d3210268a4f958be5e744057e53dc6`;
- multidomain planner manifest `67045ba2da9dd897b851bba31f05ed0e9faf93fa665245f87803904cfa5fe6d7`; and
- int16 planner weights `19869eac5b0da770505214a6c5817b94dfda05730f97598bf2f855aff82d6c8d`.

The learned-ranking prefix is a deterministic projection of the exact inherited planner weights. It is not replaced by a hash-only heuristic and it is never trusted as a completeness argument. After the bounded learned/rejection-conditioned prefix, the package-bound fair enumerator supplies the completeness boundary.

## Bounded mutation grammar

Each turn constructs exactly 32 legal mutation programs: four variants in each of eight executable update families.

```text
adapter policy
architecture policy
memory policy
optimizer policy
planner policy
retrieval policy
tool policy
verification-automation policy
```

A program changes only the Phase 16 overlay. The accepted Phase 15 `M9` base package remains immutable. Protected capability retention is therefore recertified through the exact Phase 15 closure plus an overlay noninterference certificate at every promotion.

## Post-freeze hidden challenge stream

For every turn:

1. the complete predecessor state is frozen;
2. the legal bounded grammar is generated from the frozen state;
3. an independent deterministic challenge stream selects one available legal successor after the freeze;
4. the target program and target output remain private during search;
5. every candidate is separately frozen and independently executed;
6. only the fixed evaluator may accept; and
7. promotion occurs atomically after predecessor-frontier and recursive-productivity checks.

The challenge stream deliberately constructs a successor-availability witness from the declared bounded grammar. This is a validation of fair search, rejection recovery, retention, and scaling under an explicit successor-existence premise. It is not evidence that every arbitrary predecessor has an available improving successor.

## Fair-search certificate

The active search combines:

- inherited planner-weight ranking;
- novelty pressure against overused update families;
- rejection-conditioned reranking;
- expanding candidate envelopes `4 → 8 → 16 → 32`; and
- a coprime-stride enumeration of the complete legal set.

Every promotion retains the legal-set hash, fair order, exact considered prefix, rejection trace, accepted index, and used resource envelopes. A separate impossible-target probe rejects every candidate and proves that all 32 legal mutations were considered before bounded exhaustion was emitted.

## Content-addressed experiment archive

The archive retains proposal hypotheses, candidate programs, rejection reasons, failed proof attempts, resource use, counterexamples, successful mutation motifs, recursive-productivity probes, and transfer evaluations. Every record is parent-linked and content-addressed.

The archive is explicitly untrusted for acceptance. It may condition future ranking, but it cannot override the fixed evaluator, fabricate a promotion, or replace the fair-search certificate.

## Scaling campaigns

The authoritative capture executes two seeds across two challenge streams at each declared rung:

```text
8 accepted promotions
16 accepted promotions
32 accepted promotions
64 accepted promotions
```

That is 16 independent campaigns and 480 accepted promotions before the optional 100-promotion stretch campaign. Campaign length is a validation envelope, not a host-authored successful transition schedule: the controller is not given the accepted program, update family, or candidate index for any turn.

Each eight-promotion block covers all eight substantive update families, retains the full protected frontier, retains the recursive-productivity frontier, and strictly adds the selected family-specific recursive ability on first use.

## Claim boundary

A successful Phase 16 supports a long-trajectory, multi-seed, fair-search scaling result inside the fixed diagonal/classical regime. It does not yet establish:

- open-horizon continuation;
- controller-selected termination;
- universal successor availability;
- noncommuting quantum semantics;
- verifier succession;
- asynchronous operation; or
- full Gate E closure.

Those remain Phase 17, Phase 18, X, Y, and Z work.
