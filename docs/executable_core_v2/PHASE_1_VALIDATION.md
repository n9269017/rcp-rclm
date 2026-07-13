# Phase 1 cross-platform validation record

## First clean synchronized runtime-bedrock validation

The deterministic Phase 1 runtime bedrock passed the dedicated Linux, Windows,
and macOS workflow at:

```text
validated branch head:
ab6a04ab80b7b2290ef76e56c017c070df55ff80

workflow run:
29274306289

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
  artifact: phase1-runtime-bedrock-Linux-X64
  SHA-256: 0b181d9703cdb4e806acc339d4751b0c4f1929989fab88541cb51607f2f78517

Windows
  artifact: phase1-runtime-bedrock-Windows-X64
  SHA-256: 508a9af2c1e7da83da1e3b027fe1f8f5dc6d7cde33a94557954f73fedf8b67e4

macOS
  artifact: phase1-runtime-bedrock-macOS-X64
  SHA-256: 05ba323f6039bd880b3cec2657ca87c5366eb6bbac53a218f3554f6e08a9f87b
```

The cross-platform consistency artifact is:

```text
artifact:
phase1-runtime-bedrock-final-29274306289-1

SHA-256:
00b52e02507161dd98cab0d81e972191ae501416905e01f62876aed6d577d2ae
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

## Windows portability repair

The first matrix attempt exposed that some Windows filesystems do not supply a
portable globally unique `(st_dev, st_ino)` pair for unrelated files. The semantic
tree scanner was strengthened so that a matching stat pair is only classified as a
hard-link alias after `os.path.samefile` independently confirms identity.

The repair preserves fail-closed rejection of actual hard links while preventing
unrelated ordinary files from being rejected on Windows.

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

The final PR head is validated once more after this record and the machine-readable
release evidence are added. That final workflow is recorded on PR #15 so no source
file needs to predict its own future workflow identifier.
