# Phase 6 selector, realizer, and package-builder validation

## Clean executable implementation head

The complete Phase 6 implementation passed the authoritative Phase 0–6 validation
matrix at:

```text
validated implementation head:
d3520abdc68fed9b7fd5fe3921ce63e9e00cf1f1

Phase 0 workflow:
29381815173 — success

Phase 1 workflow:
29381815211 — success

Phase 2 workflow:
29381815215 — success

Phase 3 workflow:
29381815168 — success

Phase 4 workflow:
29381815157 — success

Phase 5A workflow:
29381815164 — success

Phase 6 workflow:
29381815200 — success
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
Phase 6 tests:          21 passed
```

The Phase 6 suite covers selector binding, substantive verification- and memory-policy
changes, exact before/after file hashes, command/environment/resource evidence,
rollback restoration, strict record round trips, public package verification, payload,
evidence, and rollback tampering, unknown package entries, metadata-only and state-only
changes, component/path mismatches, resource overflow, predecessor tampering, output
overwrite protection, hard links, symlinks, and deterministic package construction.

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
predecessor semantic-tree hash. The public candidate-package verifier then reparsed all
evidence, remeasured the payload, verified the exact package layout, recomputed every
manifest binding, checked the rollback bytes, restored the archive again, and compared
the restored predecessor tree hash.

The regression suite separately confirms that any payload, evidence, rollback archive,
or unexpected package-entry mutation is rejected.

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
471d4ffb86a97accfe4e84a787384aae80d25cf12aff7b587c502c5b3a71ffc1
```

Every generated Lean source passed the mandatory pre-compilation rejection gate for
`sorry`, `sorryAx`, `admit`, project-local `axiom` declarations, and invalid UTF-8.

## Workflow artifacts

```text
final workflow closure
  runtime-v2-phase-6-final-29381815200-1
  sha256:09cb568fe21e3d665280c538cb19fa4610a3967e158d96bac8e34847b3f8c9b0

pinned Lean and complete Phase 6 path
  runtime-v2-phase-6-pinned-29381815200-1
  sha256:65fa81637fbc9e25ea2063ae1e2767c90c605dc2c1fc8d4a8c2e048b0d65328a

Ubuntu runtime and reference packages
  runtime-v2-phase-6-ubuntu-latest-29381815200-1
  sha256:b0710bd3ccc1f8d157e7f9c6c554e6bbec04042f6a7c61234ac148589fa47992

Windows runtime and reference packages
  runtime-v2-phase-6-windows-latest-29381815200-1
  sha256:58f2bd98fd7e3106223e85fe7ab46941a106fad2487df9b48b7f730a17b18263

macOS runtime and reference packages
  runtime-v2-phase-6-macos-latest-29381815200-1
  sha256:19aa40376a12c4b48f514e3f39647bf6a01c5438bfc953caf89da86c6647321f
```

The closure JSON records the pull-request merge revision used by the workflow. GitHub
artifact metadata independently binds every retained artifact to implementation head
`d3520abdc68fed9b7fd5fe3921ce63e9e00cf1f1`.

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
