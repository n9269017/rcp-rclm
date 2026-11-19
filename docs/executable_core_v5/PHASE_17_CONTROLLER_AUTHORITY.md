# Phase 17AI — controller authority and issued reference grants

## Baseline and purpose

This additive increment starts from completed AH Windows evidence commit
`8903e306229a1caf22315121b519443639537204` on
`agent/rcp-rclm-v5-phase-17-controller`. Its retained execution record is
`artifacts/development/phase17ah/op-817e423cdd0c/gate/execution.json`, SHA-256
`78338a9b6744ecd1ef7ec84abfe82f55b0335360c3ea1d2708160c368f481fa6`.
PR #68 remains draft and unmerged.

AH checks a finite producer domain and truthful controller evaluation under a
separately supplied reference grant. AI adds a local issuance protocol: an
externally anchored authority owns the permitted source registry, fixed
objective/evaluator policy, actual reference controller checkpoints, and a
shared allowance for declared reference work. A candidate cannot authorize
itself by constructing a grant with a matching hash.

## Trust and authentication boundary

The operator supplies the authority policy and expected journal head separately
from a candidate request. Validation checks content identity and protocol
provenance relative to those trusted inputs. The operator must provision the
authority legitimately and retain a trustworthy current head. Neither a file
path nor a hash establishes the origin or rollback resistance of that input.

The general consumption invariant permits each registered source identifier
to complete at most once. It does not prove that an arbitrary trusted registry
cannot assign different identifiers to the same physical source. The selected
policy fixes the distinct `af_before` and `af_after` entries and reconstructs
each retained source independently; the authority of that registry remains an
explicit assumption.

The reference sources remain AH's two retained inactive AF projections. The
checked controller states are the actual checkpoints produced by the unchanged
controller in these controlled reference sessions. They are not a newly
promoted active store, a newly authenticated external history, or a physical
root-transition certificate. The two source sessions retain their separate
source identities and do not become a new linked physical two-step execution.

The fixed evaluator retains AE's 282 task meanings, AH's canonical missing-task
selection, and AG's complete finite acceptance conditions. The authority binds
the relevant controller, evaluator, and interpretation implementation identities
outside candidate input. Altering a candidate's self-reported evaluator or
source identity cannot retarget an already anchored authorization.

The generic Lean model treats record identities as opaque values and takes
fixed context and evaluator functions as trusted parameters. The selected
certificate supplies the actual AH definitions and checks the complete
request, grant, and result bindings. The JSONL hash chain, filesystem locks,
durable writes, and Python execution are checked by the implementation and its
tests; this does not constitute a general Python or host refinement theorem.

## Issuance, execution, and completion

An authority reservation must name its permitted source, the current restored
controller checkpoint, the independently fixed policy, and a fresh lease
identity. A durable journal entry reserves the full declared session envelope
before candidate evaluation. A pending lease prevents another issuance. A stale
head, substituted policy, replayed lease, wrong checkpoint, or insufficient
aggregate allowance is refused.

Completion checks the exact issued lease and the recomputed AH evaluation
result, including its final controller checkpoint and original operation
journal. The complete envelope remains charged when a session accepts early or
stops. An interrupted pending reservation remains charged and unresolved; a
missing process handle does not justify completing, refunding, or taking over
the transaction.

The new protocol has a distinct typed completion record. The older campaign
authority's worker-completion inventory describes a different worker protocol
and is not relabeled as AH reference work.

## Resource interpretation

The shared allowance covers the inherited reference tariff: one descriptor
admission and two bounded DSL probes per attempted candidate, with counter
vector `(1, 2, 8, 8)` and cost 112. Issuance reserves a complete bounded envelope;
completion reports actual selected work within that envelope without refunding
unused capacity.

For every reachable abstract authority state, the formal accounting invariant
bounds completed declared cost plus the full pending envelope by permanently
reserved cost. Reserved cost is in turn bounded by the fixed authority pool.
The theorem concerns the AH reference tariff throughout; a pending lease never
becomes a completed receipt merely because its reservation was charged.

The selected examples keep issuance, actual declared work, and interruption
separate:

| Case | Authority allowance | Session allowance | Observed reference behavior |
| --- | ---: | ---: | --- |
| Shared two-source authority | 64 attempts | 32 per source | The two separately provisioned source sessions accept after 1 and 8 attempts; reopening between completed sessions preserves the first reservation. |
| Aggregate denial | 32 attempts | 32 per source | The first session accepts after 1 attempt; the second full envelope is refused before evaluation. |
| Reference allowance stop | 3 attempts | 3 | The second source stops after 3 attempts without claiming domain exhaustion. |
| Controller credit stop | 32 attempts | 32, with 4 controller credits | The second source stops after 4 attempts without claiming domain exhaustion. |
| Interrupted reservation | 32 attempts | 32 | One lease remains pending and fully charged; reopening cannot execute or complete it. |

Across these cases there are six issued leases, five completed reference
sessions, one denied lease, one retained pending reservation, 17 attempted
candidates, and 51 metered reference operations. The shared two-source case
reserves cost 7,168 while its actual declared reference cost is 1,008. The
unused reservation is retained. These numbers describe the selected reference
operations, excluding the work listed below.

Preparation, source reconstruction, grammar generation, planner scoring,
canonicalization, hashing, authority verification, controller bookkeeping,
catalog scans, AG acceptance checks, journal and filesystem operations, Lean
compilation, tests, host CPU and memory, historical work, and future campaigns
remain outside this reference tariff. This increment does not establish
complete resource accounting or OS containment. The generic mathematical
resource bounds concern the declared units and externally fixed policy.

## Evidence and recovery

Fresh preparation retains the original authority and operation journal bytes.
The gate copies those originals only after comparing them with the packet and
binds their individual hashes in the plan. Saved-evidence reconstruction
recomputes deterministic images in memory; those images are not presented as
newly persisted reservations or newly executed work.

The gate retains the explicit completed-stage lineage protocol. It binds the
tested source/tree, packet, generated proof sources, original journals, pinned
compiler environment, completed native commands, compiled artifacts, exact
theorem inventory, and designated rejection diagnostics. An unrelated error,
warning, timeout, or unobserved outcome cannot satisfy a negative control.

The application protocol freshly compiles ten modules, audits 68 named
theorems, and checks 18 designated rejection controls through 39 completed
formal stages. Its Python inventory is 112 tests, with 54 separate controlled
installer and Git-transaction tests. The source snapshot binds 565 files.
These inventory counts specify the required application; acceptance depends
on its completed native results and saved-evidence reconstruction.

Only a complete actual pinned Lean gate can set the new narrow completion flags:

```text
authority_bound_controller_state_checked
authority_issued_reference_grants_checked
```

Development drafts and controlled parser tests establish neither flag. The
finalized application inventory and selected results are recorded with the
sealed kit and source-bound execution evidence after validation.

## Remaining obligations

All 24 broader Phase 17 claim flags remain false. In particular, this local
authority protocol does not authenticate an external issuer, supply a
rollback-resistant service, integrate the full campaign budget authority into
promoted lineage, establish complete resource accounting, or certify arbitrary
Python execution against Lean.

The next integration work must justify the actual provisioning and trusted-head
authority across real controller lifetimes, connect objective/evaluator
authorization to the live process, and account for the complete work being
authorized. Physical/root-transition certification, active promotion,
independent replay, full frontier and recursive-productivity recertification,
Gate E, and Phase 17 exit remain separate open obligations. The finite catalog
still does not establish arbitrary repeated strict improvement.
