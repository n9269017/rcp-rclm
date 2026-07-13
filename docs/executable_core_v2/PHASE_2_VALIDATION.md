# Phase 2 pinned Lean conformance validation

## First clean synchronized implementation validation

The initial generated-source Lean bridge passed its full validation matrix at:

```text
validated implementation head:
01319d8be6c4025fb32092588e4f021a60596652

workflow run:
29287943656

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
3c6c35067e1e810fa21f09360451768ccb89f493416f9c0ff380c8f7775096c1
```

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
  runtime-v2-phase-2-final-29287943656-1
  sha256:a3b643f4298e63a7c46fb56781d87ca23b5a3e28150a27cc0a2e28837981b6a6

Lean conformance evidence
  runtime-v2-phase-2-lean-29287943656-1
  sha256:b90cd6e585bf7fc5e6c121391c6a4573cb0f5a7efa9e83807dabfb6e163ad9f2

Ubuntu Python evidence
  runtime-v2-phase-2-python-ubuntu-latest-29287943656-1
  sha256:1de4bcdefdf78a9d132fd8a1345c9de11fb403356d4ab5c369c7d9ca234fd602

Windows Python evidence
  runtime-v2-phase-2-python-windows-latest-29287943656-1
  sha256:d9449c4eeabde2df26e7f5933f6c0517da4cf1cdae343983d6433b1e82a72f94

macOS Python evidence
  runtime-v2-phase-2-python-macos-latest-29287943656-1
  sha256:d917d1bd63393945eb41a3ed444f62f8dbbb71bbd8ae377b50c9a35c6b94ab4e
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
