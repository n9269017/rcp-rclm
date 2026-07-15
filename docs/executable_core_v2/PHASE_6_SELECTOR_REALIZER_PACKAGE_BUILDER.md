# Executable Core v2 — Phase 6 selector, realizer, and package builder

## Purpose

Phase 6 converts an untrusted proposal into an actual immutable filesystem candidate.
It does not promote the candidate. The boundary is:

```text
immutable predecessor package
→ independently measured predecessor bytes
→ validated untrusted proposal
→ deterministic selected update
→ isolated workspace copy
→ selected file operations
→ measured candidate payload tree
→ modified-file ledger
→ deterministic rollback snapshot
→ immutable candidate package
→ public package verification
```

The Phase 5A worker never receives a candidate workspace, package path, rollback
archive, checker source, trust anchor, or promotion-ledger write handle.

## Scope

The first Phase 6 reference implements the finite Gate B proposal grammar already
validated in Phase 5A. Gate B and selected diagonal Gate C mathematics remain owned by
the Phase 1–4 checker stack. Phase 6 adds no new entropy, KL, QRE, recovery, or quantum
claim and does not extend Gate C beyond the commuting/diagonal scope.

The two reference realizations are:

```text
initial + improve
  → state/rclm_state.json changes from initial to target
  → policies/verification_policy.json changes substantively

target + stabilize
  → state/rclm_state.json remains target
  → policies/memory_policy.json changes substantively
```

## Predecessor measurement

A predecessor package contains exactly:

```text
payload/
manifest.json
```

The loader rejects symlinks, non-regular files, hard-link aliases, unknown top-level
entries, malformed canonical JSON, and any mismatch in state, file count, byte count,
or semantic-tree hash. Measurements are reconstructed from actual bytes; a generator
or manifest declaration is not accepted as measurement evidence.

## Selection

The selector revalidates the Phase 5A proposal and checks its bindings to:

```text
generator request hash
proposal hash
filesystem predecessor package ID
filesystem predecessor manifest hash
Phase 5A predecessor-manifest hash
public selection policy
```

It maps the bounded proposal to a typed RCLM update and a sorted list of explicit file
operations. Every operation binds an expected before hash and mode. A write also binds
the complete after bytes, after mode, and after hash.

## Substantive successors

A candidate must change at least one declared substantive component:

```text
model weights
training policy
planning policy
tool policy
memory policy
retrieval policy
verification policy
code-generation policy
architecture code
```

Component kinds are permitted only on their declared semantic paths. State, package,
index, name, timestamp, version, schema, and manifest changes are not independently
substantive.

For canonical JSON policies, Phase 6 strips metadata-only keys before computing the
semantic before/after hashes. A change that modifies only metadata is rejected with
`PHASE6_METADATA_ONLY_CHANGE`. A state-only or manifest-only candidate is rejected
with `PHASE6_SUBSTANTIVE_CHANGE_REQUIRED` or by the strict selection schema.

## Isolated realization

The realizer copies the measured predecessor payload into a fresh staging workspace.
It applies only the selected write/delete operations. After application, it measures
the entire candidate tree and requires the actual changed-path set to equal the
selected-path set exactly.

The command ledger records deterministic internal actions:

```text
copy_payload
write_file or delete_file
build_rollback
verify_rollback
build_package
```

No shell command, network request, model invocation, optimizer, clock-derived semantic
value, or candidate-authored command result determines package validity.

## Environment and resource evidence

The environment record retains the Python implementation/version, operating-system
identity, machine identity, filesystem encoding, realizer policy ID, and SHA-256 hashes
of an allowlisted set of environment values.

The resource record recomputes:

```text
predecessor and candidate file counts
predecessor and candidate byte counts
bytes read and written
changed files
internal commands
rollback archive bytes
```

Any budget overflow rejects the candidate.

## Rollback snapshot

Before package publication, Phase 6 creates a deterministic complete predecessor
rollback archive using a canonical USTAR profile. File ordering, modes, ownership,
member times, and names are fixed. The archive is restored into a second fresh
directory and must reproduce the predecessor semantic-tree hash. The archive bytes are
then stored at:

```text
rollback/predecessor.tar
```

## Candidate package

A candidate package contains exactly:

```text
payload/
rollback/predecessor.tar
evidence/
  commands.json
  environment.json
  modified_files.json
  predecessor_manifest.json
  realization.json
  resources.json
  rollback.json
  selection.json
manifest.json
```

The candidate manifest binds the parent package and manifest, payload tree, proposal,
selection, change ledger, command log, environment, resource use, rollback snapshot,
and substantive component kinds. Its status is always:

```text
realized_unverified
```

The package is written to a temporary staging directory, publicly reverified, and only
then atomically renamed to its final output path. Existing output paths are never
overwritten.

## Public verification

`verify_candidate_package(...)` independently reparses every evidence record,
remeasures the payload, rechecks all hashes and parent links, validates the exact
package layout, verifies the rollback archive bytes, restores the archive again, and
recomputes the restored predecessor tree hash. Payload, evidence, manifest, or rollback
tampering is fail-closed.

## Generated Lean source gate

Phase 6 does not weaken the existing Lean boundary. The authoritative workflow rebuilds
the pinned Formal Core, reruns the Phase 2 conformance bridge and Phase 5A reference
loop, and scans every generated Lean file before compilation/closure for:

```text
sorry
sorryAx
admit
project-local axiom declarations
invalid UTF-8 through the structured source guard
```

## Claim boundary

A clean Phase 6 result establishes deterministic construction and verification of real
filesystem candidate packages for the declared finite reference proposal scope. It
does not establish or authorize:

```text
candidate promotion
active-package replacement
promotion-ledger mutation
generator trust
open-ended-generator correctness
independent replay without the generator
learned PyTorch proposal acceptance
external benchmark performance
general noncommuting quantum semantics
autonomous or unbounded RSI
```

Phase 7 remains responsible for objective evaluation, checker/Lean orchestration,
atomic promotion, rejection control, and rollback of the active package.
