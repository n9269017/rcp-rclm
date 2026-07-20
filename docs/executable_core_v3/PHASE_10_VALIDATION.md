# Phase 10 validation

## Phase 10A retained substrate proof

The canonical compact-transformer package and zero-output LoRA extension remain bound to
validated branch head:

```text
95a4679291b25da5093d757cc6e7baf5461a8a6a
```

with PR merge-test commit `482f065308cf4735d36959bf06fbe12f1e27ea3e`
and successful workflow `29710470650`. That historical slice deliberately recorded
`phase10_exit_closed=false` because it established only the package substrate and
conservative extension.

## Phase 10B retained learned-execution proof

The retained Phase 10B manifest is in
`phase10b_learned_execution_complete_at_declared_scope` status. Its exact portable
reference hashes are:

```text
predecessor model identity:
1f4f6cf62b435056e76a75c580f2d65b96506995560237dfd4e4c90179aef70c

candidate model identity:
5451b8dce561cc59b32953e6ed8606fc98c4bd0e80fd87bdec06fb8d9e03173d

predecessor package:
f03d496cf4fc1940ed0ebba0284e8c2586f7d19670e90b97694e0c16e152c29a

candidate package:
982a10efc8a517568ad169159b985cbeebd1f0cd65a6347a30e7a5dd20047949

Phase 9 learned transition:
679622c69e7e6e68416f2675e66186731461ffc358b10a22fe0879292a8cc09f

information report:
9fc8165c37408ecba7fa9b7edc719898c89499b273865579ea33919603726e61

Phase 10B summary:
f753c1e674184f97442f44446ad2470aec520852c1a1d5dff047b85ae5925de9
```

The manifest also binds the Git-object SHA-256 values for the selected information Lean
module, Draft 2020-12 schema, isolated training worker, and Phase 10B workflow.

## Full Phase 10 exact code proof

The complete promoted-successor path closed at:

```text
validated branch head:
23a33e4078766b404387d1fa9bb2737c664d9e54

PR merge-test commit:
a816c7af9119dcde1f7187590987d8cc16e05e40

workflow run:
29718918742

workflow attempt:
1
```

Every authoritative job succeeded at that exact proof point:

```text
Ubuntu portable lifecycle                         success
Windows portable lifecycle                        success
macOS portable lifecycle                          success
isolated duplicate PyTorch training/export        success
frozen Formal Core v2 build and Gate B bridge     success
Formal Core v3 build and information audit        success
Phase 6 realization and exact rollback            success
Gate D / Phase 9 lifecycle transition             success
Phase 7 atomic content-addressed promotion         success
physical training-backend removal                 success
independent replay with training invocations = 0  success
final phase10_exit_closed=true record              success
```

The authoritative closure report retained:

```text
closure report:
8276e32bed768cfaa2f4bc3ba462e473b0f257b798f86697283f49bf7a82623f

source verification:
fd138526b10c98f486b8ce9ebde2e6c4233fe89f1688dcccca841f0d3d05d44f

promoted package:
fdd88b005d44f11eedac5786e9cdbacc5bcd9ea45a2de3909a77726152c37fad

promotion report:
21d7c627725abea938fe499ad61f1a7564fa97bd505bb5837d0da2651f83c0dc

independent replay report:
06e8b8308035ea2867dd0da6273f61d01dc9037bbf6ed8ef9c3473b1e654b5f9
```

## Portable semantic references

`phase_10_closure_manifest.json` version 2 distinguishes semantic references that must be
identical on every supported operating system from exact runtime records that necessarily
include operating-system and execution-environment identity.

The portable reference set is:

```text
predecessor model identity:
1f4f6cf62b435056e76a75c580f2d65b96506995560237dfd4e4c90179aef70c

candidate model identity:
5451b8dce561cc59b32953e6ed8606fc98c4bd0e80fd87bdec06fb8d9e03173d

predecessor learned package:
f03d496cf4fc1940ed0ebba0284e8c2586f7d19670e90b97694e0c16e152c29a

candidate learned package:
982a10efc8a517568ad169159b985cbeebd1f0cd65a6347a30e7a5dd20047949

Phase 10B transition:
679622c69e7e6e68416f2675e66186731461ffc358b10a22fe0879292a8cc09f

Phase 6 selection:
8043c9828a04abf1da028bcedf8409e3374f758093e0a7d134d02e78f3bb1276

information report:
9fc8165c37408ecba7fa9b7edc719898c89499b273865579ea33919603726e61

rollback archive and restoration:
5203ca71056162b5714c56a158faf5c108bd4f6e8dcb0d73f900f648c0c171b7
```

These values are independently recomputed by the complete Phase 10 test suite on Ubuntu,
Windows, and macOS.

## Exact runtime-bound records

The following records include the Phase 6 environment or lifecycle certificate and are
therefore retained under the exact pinned code-proof run rather than compared across
operating systems:

```text
Phase 6 fixture:
2714c4e92c72c5b361731f92d725de2ee981ecea095b56d6a662ca17e1b93698

Phase 6 report:
09d52f3b0f13cfb7dda1864cbd023c9c95e58c644a18e5eff718afe7ad02abab

lifecycle certificate:
dcb59da84452657bd838c917e6918f0fa1067ba171b5d4b078335a894f55be1f

lifecycle Gate D transition:
e028404025d513870b93574d18557bd33e35d4b008b841d8f797f44189c3d24e

Phase 6 worker-free replay report:
a2d3993de1d1fb856c2399250067cba32c75e87fb4c8d22254d6b87acf5e4397
```

This classification preserves exact-run auditability without falsely treating platform
identity as a semantic model or rollback discrepancy.

## Authoritative workflow artifacts

```text
Ubuntu:
sha256:54ea7129b24bdd716f5f9485022a974106662b1c52590111ee325f72babe97f3

Windows:
sha256:b970bd229890690223e39e91658a718b47eb3ca483c3fdd673f66b86a1273a7f

macOS:
sha256:bd8d1ad8bdd90e3e52a34bf88b627b81f1f0775ee6769d880245a0aa1668e353

isolated training:
sha256:54deab0c37d084bf085c74a147b312eff3f546d16bfd7f426ad08fb420ab2f82

pinned promotion and replay:
sha256:9fd060ecc8a53f24afc32b3f604aeb49a8b2c96766dbfa9bd3279a816814f24d

final closure:
sha256:2b4173f7a220b96c1e8152729164e2b6d50d5040462e54acc444b70f6b0d3743
```

## Non-circular final-head binding

A committed source file cannot contain the digest of an artifact produced only after that
source commit exists. The repository therefore uses two complementary records:

1. `phase_10_closure_manifest.json` binds the portable semantic hashes and retains the
   exact successful code-proof run, its runtime-bound hashes, and its artifact digests.
2. The final repository head is rerun through the complete workflow. Its head commit,
   PR merge-test commit, closure report, and artifact digests are recorded in the PR
   description, which does not alter the source head.

This preserves exact-head evidence without a self-referential commit or artifact digest.

## Closed claim and remaining boundary

Phase 10 establishes one promoted learned successor for the selected compact decoder and
selected Lean theorem-completion task class. It does not claim general native-float
transformer equivalence, generic successor availability, recursive self-hosting, or
autonomous/unbounded recursive self-improvement.
