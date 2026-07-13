# Phase 2 pinned Lean conformance validation

## Authoritative clean implementation validation

The initial generated-source Lean bridge, including the repaired release validator
and complete source-guard failure metadata, passed its full validation matrix at:

```text
validated implementation head:
0de375d1c615c8d73eb26b53a7bddb47eaccec70

workflow run:
29293545142

result:
success
```

The successful workflow established:

```text
Linux Python bridge tests: success
Windows Python bridge tests: success
macOS Python bridge tests: success
Phase 1 regression suite: success on every platform
pinned Formal Core build: success
10 generated Lean reference cases: success
RCP/Python differential agreement: success
RCLM/Python differential agreement: success
generated-source admission/local-axiom scan: success
workflow closure: success
```

## Differential suite

```text
case count:        10
accepting cases:    4
rejecting cases:    6
all bridge reports accepted: true
all differential matches:    true
```

The accepted cases are Gate B improvement/stability and Gate C
improvement/stability. Rejected mutation cases use wrong successors, wrong
certificates, or malformed certificates.

The canonical conformance-report hash is:

```text
95ea6a835c054eb5148fe74c7987e8cab4f83125656539b7f1ee95ae89579aa2
```

## Source-guard evidence

Every persisted source-guard report now records:

```text
gate version
source path
source SHA-256
byte count
clean/rejected status
matched token and reason code
one-based line and column
```

The validated gate version is:

```text
rcp-rclm-lean-source-guard-v2.0.0
```

When a caller does not supply a semantic source path, the guard assigns a
deterministic content-addressed virtual path of the form
`generated/sha256-<source-hash>.lean`. Rejection remains pre-compilation and
fail-closed.

## Pinned project and runtime identity

```text
Formal Core commit:
012de4a55f326107f53f0e215c8aec62859d0bbf

Formal source tree:
e9eab104ea2bfe0372ccf43c4eb3da388fbd3344

Lean:
Lean 4.31.0, commit 68218e876d2a38b1985b8590fff244a83c321783

mathlib:
fabf563a7c95a166b8d7b6efca11c8b4dc9d911f

project pin hash:
32cbf7de4cf65298568432322fb428bceb4cb66269be934de537d0c8991a66d9

toolchain runtime hash:
d8c0c12a9127ef41ffd263d8c658b79cb75b0b97b17430ac6ac1f1742e8a670e
```

## Artifacts

```text
final workflow closure
  runtime-v2-phase-2-final-29293545142-1
  sha256:5aec0f20a075da6cbab01c5b3dad776f59c12fb5d55f819e4483f0fab7773a01

Lean conformance evidence
  runtime-v2-phase-2-lean-29293545142-1
  sha256:2523cbf545ca91938732d40a0046ca046cf2f121af695de8b438e648e274261f

Ubuntu Python evidence
  runtime-v2-phase-2-python-ubuntu-latest-29293545142-1
  sha256:26ba8830f8d3a2775ea4d2d3bddc7b669af6bed630ebc72894c78885535b3eb1

Windows Python evidence
  runtime-v2-phase-2-python-windows-latest-29293545142-1
  sha256:adb6dea1a7c434e621aa1d14bd4a3f488e2e10c308056e48827840ee35f3043a

macOS Python evidence
  runtime-v2-phase-2-python-macos-latest-29293545142-1
  sha256:b25d884e445bf9ac8f833ed7db1969efc539a0c270b3233aacfaff634d3d53fd
```

The Lean artifact preserves every generated source, packet, source-guard report,
compiler report, runtime identity, raw stdout and stderr, parsed verdict, and
bridge report.

## Interpretation

This closes the initial bridge at the declared finite reference scope. It
establishes Python/RCP/RCLM agreement for the ten selected cases under the pinned
Lean project.

It does not establish:

```text
arbitrary RCLM packet refinement
production checker soundness
candidate promotion authorization
untrusted generator correctness
successor realization
promotion or rollback
independent replay
PyTorch proposal correctness
external benchmark performance
general noncommuting quantum semantics
```

The final metadata-only PR head is validated after this evidence is committed. Its
workflow identifier and artifact digest are recorded on the pull request so a
source file does not attempt to predict the workflow created by that same source
commit.
