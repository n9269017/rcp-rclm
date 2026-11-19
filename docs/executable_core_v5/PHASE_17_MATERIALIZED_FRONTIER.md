# Phase 17D — materialized packages and the capability-frontier gate

Development only. No active-store promotion, Phase 17 exit, Gate E closure, or EGC-0 result.

## Physical rather than metadata-only handoff

`materialized.py` reads the externally pinned Phase 15 bundle and materializes the
complete selected M9 semantic package: 164 files, 27,434,256 bytes. This includes
base quantized tensors, adapters, tokenizer, policies, and the actual planner.
The published M9 package manifest declares 13,625,920 parameters. The selected
Phase 16 installed program registry and historical state are reconstructed from
the verified handoff. No answer store is installed in the model package.

Physical package identity is a new measurement of actual bytes. It is not the
historical semantic identity, and is not an accepted successor identity.
Verification reconstructs the expected files from pinned evidence, checks all
physical files, forbids extras/deletions/links/case collisions, and measures again
after evaluation. Output is a NEW inactive directory; no active-store pointer is
written. The workspace and toolchain remain trusted operating-system resources;
this is not a sandbox against another process with the same user privileges.

## Prospective candidate path

A candidate package can be materialized only from an externally anchored sealed
Phase 17C transcript that independently recomputes to `await_root_verification`.
Exhaustion, partial-resource stops, wrong transcript anchors, or mutated artifacts
cannot create a candidate package. The delta is a deterministic realization of
the program descriptor frozen before evaluation, not a new learned artifact
constructed after disclosure. Base model bytes stay identical. Eight sealed
probe outputs are freshly recomputed through a distinct matrix-based package
executor and compared with the reference semantics.

The test fixture `known_candidate_pass.json` was deliberately constructed offline
with known entropy for positive-path coverage. It is explicitly NOT an unseen
live improvement, EGC result, successor-discovery claim, or promotion evidence.

## Complete selected CAPABILITY coverage, not a complete recursive frontier

`prepare_frontier` obtains obligations from the pinned historical archives, not a
candidate-provided list. It enforces exact coverage of the selected 21 capability
IDs, with no additions, omissions, or duplicate IDs:

- Eleven inherited theorem-completion tasks execute the actual materialized
  package's selected quantized/sparse decoder and routes.
- Two Phase 15 tasks execute the actual inherited planner tensor. The decoded
  affine program is evaluated at every integer from -32 through 32 (65 cases).
- Eight Phase 16 obligations execute physical installed program bytes and compare
  with the independent reference plus the historical expected output hashes.

This is selected-profile model execution, NOT general dense-transformer inference.
The 21-task list does not certify the separate recursive-productivity frontier.
Historical Python success flags are not substituted for fresh task execution.

Thirteen named Lean sources are generated from grammar-checked actual outputs.
They are PREPARED, not proved, until a real pinned Lean check succeeds.

## Real pinned Lean boundary

`lean_frontier_gate.py` refuses missing toolchains/dependencies, altered root
sources, wrong versions, incomplete proofs, nonzero exits, stderr, or unapproved
axioms. It never uses the legacy `lean_project_root=None` simulation-success
branch. The exact published v2/v3/v4 root source trees supply 72 pinned files;
the toolchain is `leanprover/lean4:v4.31.0`. The pinned Mathlib dependency is
`fabf563a7c95a166b8d7b6efca11c8b4dc9d911f`.

The operator must already have the pinned toolchain and dependencies installed
and built. This increment does not download/install them or invoke `lake update`.
Actual Lean/Lake executable hashes, versions, commands, stdout/stderr, times, and
axiom audits are retained when requested. Imported compiled libraries and the
installed compiler remain trusted environment inputs; this is not independent
compiler bootstrap or hardware attestation.

Each generated theorem gets `#print axioms`; only `propext`, `Classical.choice`,
and `Quot.sound` are permitted. Neither `sorryAx` nor native-evaluation axioms
are accepted. The gate-control unit tests mock tool processes and are labeled as
such; they do not prove the generated Lean sources.

Even a successful capability gate leaves `root_transition_verified=false`,
`recursive_productivity_recertified=false`, `promotion_authorized=false`, and
`full_frontier_recertified=false`. Integration with the formal successor-transition
certificate, resource constitution, recursive frontier, and atomic promotion is
still required. Checking an inherited task theorem is not a proof of RSI.

## Local commands

With the complete source checkout and Python 3.11+:

```powershell
python scripts/run_phase17_package_tests.py
python scripts/run_phase17_package_gate.py --output <new-directory-outside-repo>
```

The second command's default mode materializes/evaluates/prepares, but records
`lean_gate.status=not_requested`. Its exit zero is a preparation result, not a
formal gate pass. After the existing pinned Lean environment is prepared:

```powershell
python scripts/run_phase17_package_gate.py --output <another-new-directory> --require-lean
```

The application kit can opt in with `--require-lean`; it then uses the operator's
original checkout only as the prepared Lean workspace, independently checks the
same 72 root-source pins there, and still tests the new runtime in a separate
clone. It does not pretend that a Git clone copied ignored dependency caches.
A direct run may specify `--lean-workspace` for this same purpose.

A missing or rejected Lean check under `--require-lean` returns nonzero and retains
the blocked/rejected report. Do not convert it to a passing result. Use the native
installed Elan toolchain directory; an explicit operator `--toolchain-root` is
available for a nondefault installation and is never accepted from candidate data.

## Still outstanding

Full recursive-productivity recertification; formal successor-transition/root
certificate integration; atomic promotion/rollback; durable cross-session
challenge consumption; durable cross-turn ledger and resource accounting; evolving
objectives; autonomous multi-turn campaigns; independent and required platform
replay. No phase-closure boolean changes in this increment.
