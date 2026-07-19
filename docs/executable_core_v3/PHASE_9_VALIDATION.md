# Phase 9 validation

## Validation state

The Phase 9 contract source is complete at the selected compact-model and Lean
theorem-completion contract scope. One exact source head passed the Linux, Windows,
macOS, schema, reference, manifest, pinned Lean, source-hygiene, axiom-audit, and closure
jobs.

The evidence records intentionally bind that already validated source head. The later
evidence-only PR head must pass the same workflow and is recorded in the PR description
and closure comment rather than through a self-referential source-file hash.

## Validated source head

```text
branch head:
fb7a61b8083fcebf98f8c13c08a23ba8cfc59644

PR merge-test commit:
215675f533fa47371f13857f9f032631288e20f8

workflow run:
29677111722

conclusion:
success
```

## Cross-platform result

```text
Ubuntu:  success
Windows: success
macOS:   success

Python files scanned per platform: 16
source-quality issues:              0
focused Phase 9 tests:              10 passed
schema reference errors:            0
reference verdict:                  accept
```

All platforms recomputed identical predecessor, candidate, update, certificate,
held-out-policy, and transition-report hashes.

## Pinned Lean result

```text
Lean toolchain:
leanprover/lean4:v4.31.0

build jobs:
2631

forbidden proof tokens:
none

project-local axiom declarations:
none
```

The Phase 9 axiom audit covers:

```text
learned_accepted_step_frontier_retention
learned_accepted_step_frontier_expansion
learned_accepted_step_self_hosted_generator
```

The reported axiom union is:

```text
propext
Classical.choice
Quot.sound
```

These are the ordinary Lean/mathlib foundational dependencies inherited from the
validated Gate D and v2 theorem stack, not Phase 9 project-local axioms.

## Reference result

```text
predecessor frontier:
{lean.baseline}

candidate frontier:
{lean.baseline, lean.frontier_one}

new certified task:
lean.frontier_one

new task partition:
heldout

substantive changed component:
model_weights

verdict:
accept
```

Retained hashes:

```text
predecessor state:
84127baea242b390e91ecad239799fe2107b53ca64542ac0f6294b143ba73f4a

candidate state:
8bcd85f2d6f5ee5dde715598b0b89e51af00c9a3dd7cecb617e3af8c3809f8fa

update:
5df08b901a04b88886ce2fc21e7e8b7a41178940d1dcf39bc5ba04eff0bc1bb0

certificate:
ac518e5e1c1a66a5c92853a720c3a2f2e6dce7e5576e042c1c5cbb8c120eeff7

held-out access policy:
71ff754164ae3320525f384cb59a9de5cd7db7546608ed3dae6ba93ee0bcb1c6

transition report:
c4a1d8f22a4dd41dc4c929dcc8ce41d2c5fc30241fcdd7bd03a4579b09c953eb
```

## Contract artifact hashes

```text
Phase 9 schema:
646f00af321f7f243fb9005ece145159fb6bf3a86848d12113377fb4525995f5

Lean executable contract:
ef98e02f26e2977ed663a87ef99aa7decaf18351beb1772c656ca9fb5367e793

Phase 9 axiom audit:
cbd36d1d4ac5de26d29fc3c17a2f7cda49afa69e07dc67e52fd7f1ff7561ef89
```

Source-head workflow artifact digests:

```text
closure:
2b8990a6de6270487ce14481af8c6f3b09abf0a66c524f9b1f3aa1c81258df76

pinned Lean:
a8fc53ba86892828e41a1b526103d3f3678b45a4b37c03fa0b3f6c7ff0a3d94c

Ubuntu:
c66a961846af0368212b6cdb7cc19494d7aa2bf6cd9aad217a2a7e469a921495

Windows:
8343b5213a9e4561e50c9da81d51915948b6882d290d2c0b2949b8c3740ad86f

macOS:
15c68fb1c4d19531808653be6d69f1dde5677703abfae8f0dde165e435228bc4
```

## Claim boundary

This validation establishes a contract and non-vacuous finite reference only. It does
not train or promote a compact language model, authorize a learned generator, prove
generic frontier-expanding successor availability, establish generator self-modification,
produce self-hosted multi-generation recursion, or prove autonomous/unbounded RSI.
