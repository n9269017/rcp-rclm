# Phase 1 cross-platform validation record

## Clean synchronized runtime-bedrock validation

The deterministic Phase 1 runtime bedrock passed the dedicated Linux, Windows,
and macOS workflow at:

```text
validated implementation head:
ee22d11fb7472c1c8a3a61ee20fd10a28b76212a

workflow run:
29280052015

result:
success

test count per platform:
74

conformance-vector SHA-256:
447c3933d2be4904f2499a5be5f8cb32e5c9babe5e5cccd029ae3a95caec78b8
```

## Platform artifacts

```text
Linux
  artifact: runtime-v2-phase-1-platform-ubuntu-latest-29280052015-1
  SHA-256: 89c301efe020bfeafa07f1497bbbbdd982cdbcb4bfe348262402aae9d3c034d2

Windows
  artifact: runtime-v2-phase-1-platform-windows-latest-29280052015-1
  SHA-256: 4d6a278e9b9bea3152c3b4c598df32f17d7b9281c079c2591384c72f40517d17

macOS
  artifact: runtime-v2-phase-1-platform-macos-latest-29280052015-1
  SHA-256: c6821e6f9f8b784bf0db6fe0bc22fdd3ce8165ac351d9dcafb7c4c397027a41a
```

The cross-platform consistency artifact is:

```text
artifact:
runtime-v2-phase-1-final-29280052015-1

SHA-256:
3c81055228e43b318492d5187754b33e8487ac3aba85e02acc1baab27e285e94
```

## Validated behavior

Every platform completed:

```text
editable package installation
Python source compilation
syntax-aware source-quality validation
74 deterministic unit and conformance tests
platform validation-report generation
platform artifact upload
```

The final job compared the acceptance-relevant stable report fields from all three
platforms and established equality for:

```text
package version
contract version
Formal Core source commit
numeric backend identity
test count
conformance-vector hash
Phase 1 manifest hash
theorem-surface hash
vector schema version
claim boundary
validation status
```

## Portability repairs established by CI

The first Windows matrix exposed that some Windows filesystems do not supply a
portable globally unique `(st_dev, st_ino)` pair for unrelated files. The semantic
tree scanner was strengthened so that a matching stat pair is only classified as a
hard-link alias after `os.path.samefile` independently confirms identity.

A later Windows matrix exposed checkout line-ending conversion in the frozen JSON
vector. The repository now pins the Phase 1 package and validation documents to LF
through `.gitattributes`. This makes byte-level hashes authoritative and identical
on Linux, Windows, and macOS instead of depending on local `core.autocrlf` policy.

The workflow also preserves the combined deterministic unit-test log in every
platform artifact, including failed attempts, so future portability failures are
inspectable without relying on truncated web logs.

## Interpretation

This validation closes the deterministic runtime-bedrock phase. It establishes
cross-platform agreement for the frozen records, exact rational and interval
mathematics, selected Gate B and Gate C functions, canonical serialization,
content/tree hashing, RCLM forgetful mappings, and generated-Lean source guard.

It does not establish:

```text
Python-to-Lean differential conformance
pinned Lean compiler/verifier execution
production successor-checker soundness
generator correctness
successor promotion or rollback
independent replay
PyTorch proposal correctness
external benchmark performance
```

The final metadata-only PR head is validated after this machine-readable evidence is
committed. Its workflow run and final artifact digest are recorded on PR #15 so no
source file needs to predict the identifier or digest of the workflow created by
that same source-file commit.
