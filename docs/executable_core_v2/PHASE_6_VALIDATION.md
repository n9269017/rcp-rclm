# Phase 6 selector, realizer, and package-builder validation

## Clean executable implementation head

The complete hardened Phase 6 implementation passed the authoritative Phase 0–6
validation matrix at:

```text
validated implementation head:
6afbf8a395a9b41cd4f6d9b5accbe247974c8b20

Phase 0 workflow:
29383092464 — success

Phase 1 workflow:
29383092479 — success

Phase 2 workflow:
29383092465 — success

Phase 3 workflow:
29383092462 — success

Phase 4 workflow:
29383092453 — success

Phase 5A workflow:
29383092516 — success

Phase 6 workflow:
29383092505 — success
```

All seven executable-core workflows completed successfully at that exact source head.

## Cross-platform runtime validation

The Phase 6 workflow passed on Linux, Windows, and macOS. Each platform completed:

```text
Python compilation
source-quality validation
Phase 1 regression
Phase 2 bridge regression
Phase 3 checker regression
Phase 4 hardened/adversarial regression
Phase 5A generator regression
Phase 6 successor-package regression
construction and public verification of both reference packages
artifact publication
```

The clean Ubuntu evidence recorded:

```text
Python files scanned: 135
source-quality issues: 0
Phase 1 tests:          74 passed
Phase 2 tests:          19 passed
Phase 3 tests:          20 passed
Phase 4 tests:          10 passed
Phase 5A tests:         18 passed
Phase 6 tests:          22 passed
```

The Phase 6 suite covers selector binding, substantive verification- and memory-policy
changes, exact before/after file hashes, command/environment/resource evidence,
rollback restoration, strict record round trips, public package verification, payload,
evidence, rollback, and unexpected-entry tampering, metadata-only and state-only
changes, component/path mismatches, resource overflow, predecessor tampering, output
overwrite protection, hard links, symlinks, deterministic package construction, and a
coherent selection/realization/manifest substitution attack.

## Filesystem predecessor and candidate packages

Each predecessor was built as an actual package containing:

```text
payload/
manifest.json
```

The loader independently reconstructed the semantic file records and tree hash from the
payload bytes. Symlinks, non-regular files, hard-link aliases, malformed manifests,
unknown top-level entries, and declared-versus-measured count, byte, state, or tree
mismatches are fail-closed.

Each candidate was built in a fresh staging workspace and published only after the
public verifier accepted this exact layout:

```text
payload/
rollback/predecessor.tar
evidence/
manifest.json
```

The candidate status is `realized_unverified`; no promotion was attempted or licensed.

## Initial-state reference package

The `initial` proposal selected the typed `improve` update. The realizer changed:

```text
state/rclm_state.json
policies/verification_policy.json
```

The state changed from `initial` to `target`. The verification policy changed from the
baseline checker-only policy to a fail-closed policy binding the Phase 3 checker,
Phase 4 hardened checker, and pinned Lean bridge. The policy change remained
substantive after metadata-only keys were removed.

Evidence:

```text
proposal SHA-256:
80bc33b5e36bf53a3dff0147ba1e8f0d44ca3c761ce9f130eb14a58729503fcf

predecessor manifest SHA-256:
a65327eabf526bf8d83984c98b1b778a5aa62318171b1084145ff955730912d0

selection SHA-256:
f360bff5302eee0676cd3e6f705bbad664e99ddb8f2506552029be3a4a67eba5

candidate payload tree SHA-256:
da118659b014357bdc07568bd16c1dcce701ccfaca72f54486ff3baca0894264

candidate manifest SHA-256:
fe29dcc45f9b510d4ef725ba353f700bc7560beccaf97af484b6ce73ee433bfd

package report SHA-256:
7e37f14a24549705036d9ae3a9b3603e99ffae45c837b82d2bb6ec35e871019c

rollback archive SHA-256:
437b12a44b865833bb9c93df90dd02816cb7706dec855cbdeb7288740cd30f21

changed files: 2
recorded internal commands: 6
substantive component: verification_policy
rollback restored predecessor tree: true
resource budget satisfied: true
```

## Target-state reference package

The `target` proposal selected the typed `stay` update. The state remained `target`, but
the realizer changed:

```text
policies/memory_policy.json
```

The memory policy moved from a bounded local snapshot policy to an append-only,
content-addressed policy requiring a rollback snapshot. The semantic hash changed after
metadata-only fields were removed.

Evidence:

```text
proposal SHA-256:
d7be93918f55419e5fc9eace2311e273bfbee6d4aa72f948079716ff6f9e23e8

predecessor manifest SHA-256:
5b75fefa5151661b9407ac1e6c7c056a3a28e7b01d62222b675a8ffdeb1d3c1b

selection SHA-256:
868d416a26f0e6a7cdb33fba0b40e5cd91e12e4033071dd80088dc89fe67e404

candidate payload tree SHA-256:
75ed50b2f14606e721e4eab212920bd2248d377dfd3f34e5a22788a48c43af47

candidate manifest SHA-256:
021c3614dcb776dff98284bc7f1fe9d45d808b021085358656082a160d3cef3b

package report SHA-256:
36a6ac61829e33f6eac5a535270bc4782a1a0d69b2e1072b5f241b35fc7b4162

rollback archive SHA-256:
1e3486ae116b0a7503692bcddd0aa868f482b5f57dd50499ff2982f38d74453c

changed files: 1
recorded internal commands: 5
substantive component: memory_policy
rollback restored predecessor tree: true
resource budget satisfied: true
```

The aggregate reference-suite record is:

```text
case count:       2
built cases:      2
all built:        true
promotion licensed: false
suite SHA-256:
6ccbb61ab9d92dd6ab6616f55dfeb56f99c9ab0e4ca1ae0e5407177920a6843c
```

## Deterministic rollback and public verification

The rollback snapshot uses a canonical USTAR profile with sorted semantic paths, fixed
modes, zero owner/group IDs, empty owner/group names, and zero modification times. Each
archive was restored in an independent fresh directory and reproduced the measured
predecessor semantic-tree hash.

The public candidate-package verifier reparses all evidence, remeasures the candidate
payload, validates the exact package layout, checks the rollback bytes, restores the
predecessor again, and independently recomputes:

```text
selected before-file hash and mode bindings
selected after-file content, hash, and mode bindings
actual modified-path set
metadata-stripped semantic change ledger
substantive component kinds
internal command sequence and hashes
resource accounting
manifest, parent, environment, rollback, and evidence bindings
```

A coherent attack that substitutes a new selection and updates the realization and
candidate manifest consistently is rejected because the substituted selected operation
no longer matches the actual predecessor and candidate bytes. The regression suite also
confirms fail-closed rejection of ordinary payload, evidence, rollback, and package
layout tampering.

## Pinned Lean and earlier-phase revalidation

The pinned Phase 6 job completed the full Formal Core build:

```text
2636 jobs
Build completed successfully
```

It reran the complete Phase 2 differential bridge:

```text
case count:                 10
accepting references:        4
rejecting mutations:         6
all differential matches: true
all bridge reports valid:  true
```

It also reran the Phase 5A reference loop:

```text
reference cases: 2
Lean acceptances: 2/2
hardened-checker acceptances: 2/2
all accepted: true
summary SHA-256:
74719025429b20de8dda7fa717571f0c5c13414401f4a96e535f56369cab431a
```

Every generated Lean source passed the mandatory pre-compilation rejection gate for
`sorry`, `sorryAx`, `admit`, project-local `axiom` declarations, and invalid UTF-8.

## Workflow artifacts

```text
final workflow closure
  runtime-v2-phase-6-final-29383092505-1
  sha256:73440a6a206c3edf8481e2dc1299f7592bf9473f756b3fe8eec495b4ff14ddcd

pinned Lean and complete Phase 6 path
  runtime-v2-phase-6-pinned-29383092505-1
  sha256:20e746cddeab9e86d0db4e675270ced05aa913476ce029abeafd1242f2d540db

Ubuntu runtime and reference packages
  runtime-v2-phase-6-ubuntu-latest-29383092505-1
  sha256:63f4363bfa912cb09ac2b1df00c127ea84ead75d2212b5276de0af3cb6cf2f98

Windows runtime and reference packages
  runtime-v2-phase-6-windows-latest-29383092505-1
  sha256:092ad18e00870aac832708ef07c32181d05fd6e4c8a13b82ebce3e3e5048d809

macOS runtime and reference packages
  runtime-v2-phase-6-macos-latest-29383092505-1
  sha256:6c1366e7aa07f7fc7a1f0639deb871745bb87c19b121bbf793189720f045f5f6
```

The closure JSON records pull-request merge revision
`7e25c728271f6da7d43599b5ee802763463c944d`. GitHub artifact metadata independently
binds every retained artifact to implementation head
`6afbf8a395a9b41cd4f6d9b5accbe247974c8b20`.

## Interpretation and claim boundary

This validation establishes deterministic construction, measurement, rollback, and
public verification of real filesystem candidate packages for the declared finite
Gate B reference proposal scope. It does not establish or authorize:

```text
candidate promotion
active-package replacement
promotion-ledger mutation
automatic generator retry
generator trust
open-ended-generator correctness
independent replay without the generator
learned PyTorch proposal acceptance
external benchmark performance
general noncommuting quantum semantics
autonomous or unbounded RSI
```

A clean Phase 6 closure licenses Phase 7 promotion-controller development. The Phase 7
controller must still perform authoritative objective evaluation, invoke the checker
and pinned Lean bridge, and atomically promote or roll back; Phase 6 itself never
performs those actions.
