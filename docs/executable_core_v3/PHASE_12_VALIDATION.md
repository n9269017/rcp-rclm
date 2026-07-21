# Phase 12 validation

## Phase 12A selected scope

The first Phase 12 validation surface checks one recursive invocation of the generation-2
successor installed by Phase 11. The portable reference establishes:

```text
retained Phase 11 closure manifest accepted
promoted beta package identity bound
promoted beta model identity bound
successor generator identity bound
successor planner identity bound
active proposal-protocol binding accepted
model-generated typed program emitted
deterministic replay byte-identical
stale generation request rejected
active package tree unchanged
held-out material consumed = false
manual repairs = 0
accepted Phase 12 promotions = 0
phase12_exit_closed = false
```

`.github/workflows/runtime-v3-phase-12-recursion.yml` validates that slice on Linux, Windows, and
macOS and emits `phase12a_recursive_start_closed=true` while retaining
`phase12_exit_closed=false`.

## Phase 12B selected scope

The second validation surface checks the complete first accepted recursive successor prefix:

```text
Phase 12A rejection retained
fresh rejection-conditioned proposal produced
proposal source bound to active generation-2 generator and planner
proposal replay byte-identical
selected update class = model_weights
held-out material consumed = false
manual repair count = 0
isolated duplicate training agrees with host-exact tensor bytes
Phase 6 realization succeeds
rollback restores M0 exactly
all three F0 tasks retained
one new held-out Lean task certified
selected KL/QRE non-regression accepted
strict new-task information witness accepted
Gate D / Phase 9 transition accepted
Phase 12A rejection written to immutable ledger
active pointer unchanged after rejection
M1 atomically promoted with unchanged M0 store package as parent
reopened immutable package contains the expected M1 semantic package
accepted Phase 12 promotions = 1
frontier cardinality = 4
phase12_exit_closed = false
```

The portable evidence summary binds:

```text
active package:
a30dbf363cb28b05a4448b50acf78123d7472605455718afbecf7acce0252094

active state:
cd1bd288da804daaf0482eaa5a30ab3e3b9da0d094748db401e0163de6687abe

active generator:
f69553a4e11dc352e7f9406dbc8722fdf48e30c18c4014d0495e67e85607f95a

active planner:
b4d0c3ab75c4ed5aacf469e4a44915a67837e586b9f2aadd8023d4a3c6dd9c51

fresh proposal:
748bdb82802511428e7cd10369f742934594908cfba45b8b280dbd40b795be16

proposal validation:
8e93b3f55980c17c129c511dc1100899c77a14e3ab792b48fa9a259c4e85cf51

candidate package:
668ac439b7573abaa9b06963fc17d5b7c8028897d50504f556f7a66d7ca03651

candidate model:
379021b5fee92acf5d03bd89ae564193aa21aab5622d687e3bf294d18cb9249f

portable candidate fixture:
c39913171c3bf29a3dd0243cc812902374c5f5c166212260a29e3478437c45b6

portable Phase 6 evidence:
3fcb80016e7d7db0303577a13cbc62cba7971f383e7ccd6d5b0462c4b4dd9180

lifecycle certificate:
795bc4c3b34860cb1c99c2db232c1c8252272b3a281bd2c49786fa5131992020

Gate D transition:
96d16503cdcfc205d42b4811dd1c0d77fe043ad11a0f0bd0ae6610b54951df18

portable summary:
0de1c67cb5b2967271eb9ed91779eb1d102e1a97b372114a246e058ce6270e82
```

## Phase 12B workflow

`.github/workflows/runtime-v3-phase-12-first-promotion.yml` contains six independently visible
jobs:

```text
Ubuntu portable lifecycle
Windows portable lifecycle
macOS portable lifecycle
isolated untrusted training
pinned Lean, Gate D, hardened checking, rejection ledger, and atomic promotion
terminal Phase 12B closure
```

Every portable operating-system leg:

1. compiles the complete Runtime v3 and Phase 12 source;
2. applies the deterministic source-quality gate;
3. validates the retained Phase 11 closure dependency without reclassifying runtime-bound
   evidence as portable;
4. runs the complete focused Phase 12 test suite;
5. recomputes the Phase 12B reference;
6. validates the Draft 2020-12 schema and canonical summary hash;
7. executes the repository-root entry point;
8. requires byte-identical tool and repository entry-point output;
9. uploads the portable evidence directory.

The isolated training job runs the untrusted worker twice and requires both reports and the
accepted candidate tensor to match host-exact recomputation. It confirms that no held-out task ID,
prompt, source, or answer was consumed.

The pinned closure job independently builds Formal Core v2 and v3, rejects admitted proofs and
project-local axioms, audits the inherited information theorem surface, runs all four Lean tasks,
recomputes selected information evidence, executes Gate D and the hardened checker, records the
Phase 12A rejection, and atomically promotes `M1`.

## Authoritative code proof

The first complete Phase 12B code proof passed at:

```text
validated branch head:
ce80712ac342852b77defedf87ccaef6ab99ea09

PR merge-test commit:
7e93727f1b6198655bcdb4fc8d3b248c25e17226

workflow:
29847443186
```

All six Phase 12B jobs passed. The pinned closure report binds:

```text
reference:
961853ad4628af54d6c055ccf6a9c2ccdadeb0fbee5e55e572727da9f49fd8ad

verification:
c5288d6cb9e01b2820dd36c3ee15b3db9da70389f76331c3cbf281321b29753c

promotion:
409ff6748d11b22027a037b25a2d7e412400f5b79b2b5889d8f1c8ba833ebe6e

closure report:
a5fe506d257259da132d25dcf39e435c4093e95d9cb7b7131b8c062e4b9d947d
```

The code-proof artifacts are:

| Evidence | Artifact ID | SHA-256 digest |
|---|---:|---|
| Ubuntu | `8501961230` | `sha256:f1d181eda3898891e15235cef294c019f47377afe9f703ef6b08a9dd97b438c2` |
| Windows | `8502000217` | `sha256:2386d6bcfb1e5d8eeb302715ecd7a0f2f34e0a4462d2624848d118e9e3334970` |
| macOS | `8501981565` | `sha256:31b9a9cbecbdaaa90b7449899aeff3ac654860a06e6605078a04aede44873e00` |
| Isolated training | `8501967912` | `sha256:2047f5dc99c0937a5dc41fee105d1871c35a91b5d09bea749d7bc9fe8a086d71` |
| Pinned rejection/promotion | `8502176122` | `sha256:8084eb0a83cd506dee949bc62c19b8f723cd9ea84fe528f8ee9fde6dc3eaab27` |
| Final closure | `8502179672` | `sha256:cf25bbb2454ee5ba0e7e3cd82c0824805d877d2862e71c227d4ac5986b0db3a9` |

The terminal record emits:

```text
phase12b_first_promotion_closed=true
accepted_phase12_promotions=1
rejected_phase12_attempts=1
frontier_cardinality=4
manual_repairs=0
heldout_material_consumed=false
phase12_exit_closed=false
```

## Evidence boundary

Portable Phase 12B identities stop at the deterministic semantic candidate, task frontier,
information report, and Gate D correspondence. Phase 6 environment identity, pinned verification,
ledger entries, content-addressed promotion records, and immutable store package hashes remain
attached to the exact authoritative run.

The active semantic model package is nested inside the Runtime v2 Phase 6/7 transport package.
The semantic package parent relation and the Phase 7 content-addressed store parent relation are
both checked, but they are not conflated into one hash namespace.

## Non-circular exact-head binding

The source tree freezes the Phase 12B contract, implementation, schema, tests, workflow, and this
prior exact code proof. The final documentation head is validated separately and is bound by its
workflow artifacts and the pull-request record. Final artifact digests are not written back into
the same artifact that they identify.

## Claim boundary

A green Phase 12B workflow proves the first accepted self-hosted transition and strict frontier
expansion `F0 subsetneq F1`. It does not prove `M1 -> M2`, `M2 -> M3`, `M3 -> M4`, the full
four-promotion chain, generic successor availability, or autonomous/unbounded RSI. Those remain
explicit open criteria in `PHASE_12_EXIT_CRITERIA.md`.
