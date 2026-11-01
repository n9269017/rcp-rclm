# Phase 17E — Pinned formal execution

Development increment. Phase 17, full-frontier and concrete successor-transition
verification, promotion, and Gate E remain open. EGC-0 is unstarted.

## Starting boundary

The Phase 17D source `a8adc0df3c841559633965be0c402188c65ef5e2` and evidence head
`e4e6852dd3e3a5d890a81d4c47e4c15cdaac3d28` retain successful Python execution of
21 selected capability obligations and preparation of 13 Lean source files.
The retained Lean status is `not_requested`; it is not proof success.

## Implementation

`scripts/phase17_pinned_lean.py` adds an explicit setup/verification execution lane.
It uses the existing 72-file root pin table without changing its hashes, Lean
version, Mathlib revision, allowed axioms, or existing formal-core definitions.

Setup is separate from acceptance. Without `--allow-network`, missing tooling or
dependencies block the run. With that flag, setup may obtain exactly the official
portable Windows-x64 Lean 4.31.0 ZIP, nine Git dependencies at the locked commits,
and Mathlib compiled caches. Existing operator-provided toolchains may be used;
their versions, paths and executable hashes are recorded. No system install,
registry update, global PATH modification, winget, GitHub CLI, Actions runner,
or `lake update` is used. Dependency heads and all pinned root files are checked
before and after cache setup/build. The tool workspace and caches are outside
the source checkout. Partial downloads/extractions and failed workspaces are
preserved rather than silently replaced.

The official Windows ZIP is 823,782,593 bytes with SHA-256
`f73208f53dcdc901745cb35fc916c476e0e18ed0856937740e46d07848f57f19`.
This pin was retrieved from the official Lean 4.31.0 release asset metadata.
Dependency source and cache downloads require additional storage and network
transfer. Setup executes trusted pinned build scripts; it is not an OS sandbox.

## Required real verification

1. Check pinned Lean and Lake versions and executable identities.
2. Require a positive kernel probe to succeed and a deliberately false theorem
   to be rejected with a real compiler error. A timeout is not proof rejection.
3. Build the existing formal-core v4 target and its inherited v2/v3 dependencies.
4. Audit the axioms of `autonomous_accepted_step_sound`,
   `recursive_productivity_retained`, and
   `recursive_productivity_strictly_expands_when_witnessed` at their complete
   `RcpRclmFormalCoreV4.Autonomous` names. Only the already approved logical axioms
   `propext`, `Classical.choice`, and `Quot.sound` are permitted.
5. Invoke the existing package gate with `--require-lean` against the actual
   materialized package and fresh selected-capability computation. All 13 named
   generated obligations must pass, with their source/hash/axiom checks intact.
6. Check source, dependencies, and executable identities again and retain logs.

Rebuilding and auditing conditional root theorems is NOT constructing a concrete
`AutonomousAcceptedStep` for a newly realized successor. The prerequisites of
those theorems still need to be discharged by the later concrete transition
bridge. The eight Phase 16 capability tasks keep their original finite integer
semantics; the separate recursive-productivity frontier is not certified here.
No live successor search, score-selected candidate, or synthetic improvement
is used in this execution lane.

The toolchain, operating system, and compiled import-cache integrity remain
explicit trusted-environment premises. Version strings, sentinel checks and
hashes do not constitute independent hardware attestation or hostile-same-user
isolation. The use of `--no-cache` for the root build suppresses implicit remote
build-cache retrieval; it is not a network sandbox.

## Reports and nonclaims

A missing prerequisite yields a blocked/incomplete report, never preparation-mode
success. A successful real run may set
`actual_lean_capability_verification=true` and
`capability_frontier_recertified=true` for these selected obligations only.
Regardless of that result, this increment retains:

```
root_transition_verified = false
recursive_productivity_recertified = false
full_frontier_recertified = false
promotion_authorized = false
phase17_exit_closed = false
gate_e_closed = false
egc0_started = false
```

The separate application helper requires a real successful report before
advancing/pushing the development branch. Evidence is committed separately from
tested source. Complete materialized tensors stay in the local workspace; retained
evidence has its own manifest, not a falsely complete copy of the model manifest.
Prior tests and failed runs are not overwritten or relabeled. No merge, release,
DOI change, or hosted-CI success is implied.

## Local execution

The application kit creates a full separate clone and runs the 51 new control and
source-pin tests, then the actual formal lane. Control tests use synthetic compiler
outputs where needed and are not Lean proofs. Existing historical foundation,
archive and process-suite results are not rerun merely for setup.

```
python scripts/phase17_pinned_lean.py --repository <source-checkout> \
  --output <new-evidence-directory> --cache <separate-tools-directory> --allow-network
```

Omit `--allow-network` only when the required prepared environment already exists.
Use `--toolchain-root` to select an existing pinned portable toolchain; on non-Windows
platforms, an existing toolchain must be supplied or found under Elan. The first
new operator execution remains required: assistant control-test results and a
blocked no-tool attempt are not a real 13-obligation validation.
