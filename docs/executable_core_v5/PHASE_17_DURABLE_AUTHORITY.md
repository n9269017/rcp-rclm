# Phase 17AK — atomic durable authority and exclusive reference lifetimes

## Baseline and obligation

This additive increment starts from completed AJ Windows evidence commit
`0ad2290b81d7b4a314b10dd0bcfa28725be4a452` on
`agent/rcp-rclm-v5-phase-17-controller`. AJ's tested source is
`1395d6ddf5ceed54525d2130faa1af2e220dd6a3`, with source tree
`48031d3a94812c796b6b1a3a3802f2ccb86e03aa`. The retained AJ execution record is
`artifacts/development/phase17aj/op-1395d6ddf5ce/gate/execution.json`, SHA-256
`e53bc075dd97d2ea0c005bb0ffbb28014e7a5bae73c867452f991cfa454e9ef4`.
The AJ semantic packet has SHA-256
`dd7a8197c66cc88beaa31c4c18dac5c88ced3c6cb754421a80bc94abeb552a2a`.
PR #68 remains draft and unmerged.

AJ requires a current independent restart anchor and one authoritative witness
history. Its filesystem witness and inner authority journal are separate writes:
a split is detected and refused. AJ already holds a local authority-journal
writer lock for the witness lifetime. It does not supply a transaction spanning
the two journals or a separately provisioned root, independent of each
execution directory, that owns the paired snapshot and lifetime epoch.

AK implements a separately provisioned durable root that owns the accepted
journal pair, current cursor, and lifetime epoch. A controller no longer supplies
the current witness restart head. It supplies an independently retained root
provision digest, and the trusted root supplies its accepted current snapshot.
This is a concrete reference backend under explicit storage and identity
assumptions. It does not establish the legitimacy, physical durability, or global
uniqueness of an external authority.

## Provisioning and authoritative state

An administrator invokes `provision_root` once with the exact AJ provision,
authentication key, root authority identifier, and provisioning nonce. Its
canonical root provision binds the AJ policy and implementation, durable backend
policy and implementation, key commitment, and authority identity. Provisioning
refuses an existing root. Opening an authority requires the expected root
provision digest; it cannot silently initialize a missing database or derive a
trusted provision from candidate input.

The durable root uses a SQLite database with a rollback journal and FULL
synchronization. One transaction stores an audit event and both complete journal
images. The published cursor contains:

| Field | Meaning |
| --- | --- |
| Root provision digest | Independently selected authority and policy identity |
| Epoch | Current exclusive authority lifetime |
| Serial | Accepted root publication number |
| Root head | Hash of the current root audit event |
| Image digest | Binding to the witness and authority image identities |
| Witness cursor | Exact AJ revision, witness head, and AI authority head |

The stored witness and authority images must agree with replay of the unchanged
AJ transition rules. The authoritative root is never reconstructed from a
controller's preferred working-directory snapshot. Root history, state, and
paired-image inconsistencies reject without automatic repair.

The key is supplied separately and is not embedded in the public root provision
or audit evidence. The selected experiment deliberately uses AJ's published
reference key. It provides reproducible authentication semantics, not external
key secrecy. HMAC security and the integrity of the independently retained root
pin remain assumptions. Every holder of the shared key can authenticate both
request and response directions.

## Exclusive lifetime and native execution

An authority process acquires a nonblocking lifetime lock for its root before
opening work. A second cooperating process using that same physical root must
fail while the first owns the lock. Each successful opening increments the
durable epoch and commits an AJ reopen transition before accepting requests.
The epoch and full current cursor are checked again in every transaction.

Opening creates a new execution directory from the authoritative paired images.
It does not reuse a caller-supplied directory or restore a former execution
owner. The unchanged AJ disk-backed witness performs actual reference work.
The path-free AJ replay implementation is used for evidence checking; it is not
substituted for the observed execution path.

A mutation request includes both the unchanged AJ request and the expected
durable root cursor. The root authenticates that envelope, checks currentness,
executes the AJ operation, checks the new paired images, and atomically compares
and publishes the new root snapshot. It releases a durable response only after
successful commit and exact readback. The response authenticates the request,
nonce, root cursor, commit indicator, and underlying AJ reply. An AJ reply alone
does not certify durable root publication.

Reads and protocol-refused requests do not add a root publication. Aggregate
budget denial is an accepted, retained AJ transition and does publish its root
snapshot. A stale root epoch,
serial, head, image, or witness cursor cannot authorize a new mutation. A current
root cursor does not override AJ's source, objective, evaluator, nonce, pending
lease, or execution-owner rules.

## Failure and restart behavior

The root record, rather than a staged file or a missing acknowledgement, decides
whether a transition committed. Staging files are retained as execution attempts.
They cannot become accepted state merely because a process stopped.

* Before root commit, a failed attempt leaves the prior authoritative snapshot.
* If a reservation committed, the complete declared envelope remains charged
  even if the process or acknowledgement is lost.
* If execution fails after reservation, the authoritative pending reservation
  remains; reopening revokes its old live owner and does not refund, complete,
  or reissue it.
* A commit followed by acknowledgement loss remains committed. A later opening
  reads that root history, advances the epoch, and rejects an old cursor.
* Ambiguous commit failures poison the live handle. Recovery requires a fresh
  authority lifetime and validation of the authoritative database.

The implementation retains the inherited bounded event and journal limits. It
does not promise an indefinitely growing database, application-selected journal
repair, resumption of interrupted task work, or recovery from arbitrary storage
damage. Normal SQLite transaction rollback and recovery remain part of the
backend contract.

## Lean model and selected binding

`lean/phase17_bridge/DurableAuthority.lean` models a root provision, durable
cursor, paired-image identities, authority lifetime, and exact AJ witness state.
An accepted publication checks the root guard and an actual `AJ.advance`
transition. Reopening is a separate epoch-advancing publication. Receipts refer
to the committed state, rather than an uncommitted tentative state.

Generic results establish fixed provision, exact cursor checking, epoch and
serial progression, exclusion of a second publication from the consumed cursor,
commit-before-acknowledgement conditions, restart fencing, owner revocation, and
preservation of the inherited AJ/AI reachability and declared reference-resource
bounds. Explicit counterexamples retain the boundary that restoring or cloning
the entire trusted root can repeat a previously admissible transition.

The model's reopen mode is selected by trusted backend dispatch. Its mutation
mode rejects a controller-supplied reopen; this is not a standalone theorem that
an arbitrary caller of the model cannot choose the backend mode. The runtime's
public request dispatcher enforces that separation. The crash lemmas state the
consequences of the specified transaction contract; they do not independently
prove that physical storage implements that contract.

These are protocol theorems conditional on the trusted backend contract. Lean
does not verify SQLite implementation correctness, filesystem power-loss
semantics, OS locking, HMAC security, process isolation, or a general refinement
from arbitrary Python execution to that model.

For the selected certificate, all native AJ requests and responses are exactly
the retained AJ reference packet. Each root publication's complete witness image
and authority image is checked against the corresponding AJ prefix before proof
emission. The Lean certificate then binds that root publication to the exact
already specified AJ witness state and its accepted transition theorem.

The paired-image hashes and root audit hashes are recomputed in Python. Lean
checks their identities and structural links; it does not newly certify their
SHA-256 evaluation or decode SQLite's binary pages. Historical SHA certificates
retain their original scope.

## Validation and evidence

Fresh capture uses three reference cases and five separately observed native
authority lifetimes. It includes two completed source sessions across a restart,
an interrupted charged reservation across a restart, and aggregate grant denial.
The underlying AJ results must match exactly: three completed reference
sessions, four issued leases, one denied lease, and one retained pending
reservation. The two-source case reserves reference cost 7,168 and completes
declared reference work of cost 1,008.

Original native records preserve command arguments, source and interpreter
identities, process lifetime observations, and the complete input/output/error
streams. Those records are bound separately from the deterministic semantic
packet. Runtime tests additionally exercise transaction failures, acknowledgement
loss, concurrent process contention, stale and replayed requests, tampered root
state, and the explicit whole-root cloning limitation.

Application validation freshly compiles all twelve required modules, checks each
import resolution, audits the designated theorem inventory, and requires each
negative control's exact final rejection. Development reuse of verified inherited
objects is labeled as such and gives no fresh application compilation credit.
The sealed installer freezes the test, module, theorem, and control inventories.

Saved-evidence reconstruction checks the exact source, packet, complete paired
images, original native records, generated proof sources, compiled objects, and
completed-stage lineage. It launches no compiler, witness, task worker, or live
challenge. Reconstructed bytes do not count as a new observed run. The installer's complete
execution-recovery ZIP preserves those evidence files and compiled objects; the
sibling physical-root databases and execution directories remain in the original
workspace. Preserve that whole workspace if those provisioned roots must also be
retained. The evidence ZIP alone is not a backup from which to reopen those roots.

The completed gate sets its two bounded result flags after all required formal
stages and the source, native-record, and manifest checks succeed:

```text
durable_authority_commit_checked
exclusive_authority_epoch_checked
```

The gate explicitly records that saved-evidence reconstruction is still required.
The installer requires that reconstruction to succeed before operator acceptance,
evidence publication, or advancement of the original checkout. Draft source,
successful parser tests, generated Lean text, restored historical objects, or an
unfinished native process establish neither completion flag.
The epoch result refers to the modeled and tested single-root contract; its name
does not assert global exclusion of physically cloned authorities.

## Remaining obligations and roadmap

All 24 broader Phase 17 claim flags remain false. AK supplies a concrete durable
authority adapter; it does not independently deploy or authenticate a real
external authority, prove host or root rollback resistance, or demonstrate
physical exclusivity between copied roots on separate hosts or storage domains.
A shared directory lock is not a distributed consensus or hardware monotonic
counter. The root database and its provisioning anchor must be protected and
presented as one authoritative history by the deployment environment.

The next integration obligation is to provision that authority outside the
untrusted controller/candidate boundary with justified durable currentness and
exclusivity, and bind actual live campaign policy, objective/evaluator authority,
and budget/work accounting to it. The current policy and evaluators remain the
selected inactive reference projections inherited from AJ/AI/AH.

The tariff still excludes provisioning, authentication, transport, hashing,
root transactions and synchronization, replay, preparation, objective/evaluator
checks, proof checking, tests, host resources, historical cost, and broader
campaign activity. Complete resource accounting and OS containment remain open.

Physical/root-transition certification, full learned/autonomous-step
instantiation, active promotion, Phase 18 independent replay, full frontier and
recursive-productivity recertification, Gate E, and Phase 17 exit remain open.
The Phase 17 → 18 → X → Y → Ω → Z roadmap is unchanged. A finite reference
catalog and a durable authority protocol do not establish arbitrary-domain or
unbounded strict self-improvement.
