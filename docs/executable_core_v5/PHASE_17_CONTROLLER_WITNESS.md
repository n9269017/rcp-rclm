# Phase 17AJ — a separate current-head witness for controller authority

## Baseline and purpose

This additive increment starts from completed AI Windows evidence commit
`e8d3c035f1ebbb6a725db2a49583185e10016490` on
`agent/rcp-rclm-v5-phase-17-controller`. Its retained execution record is
`artifacts/development/phase17ai/op-cb5401cf6b98/gate/execution.json`, SHA-256
`e8ef5c0cdc23a0cad79280525394b3415207f51a151815a2aedb46c7281378bd`.
PR #68 remains draft and unmerged.

AI supplies an authority journal, independently fixed policy, issued leases,
and accounting for the declared AH reference tariff. AI assumes that the caller
already possesses a trustworthy current journal head. AJ makes a selected
current-head interaction concrete: a separate witness process owns that
authority journal and its transition logic. A controller must obtain and use
the witness's authenticated current cursor before requesting an action.

The increment addresses stale controller snapshots and controller lifetimes
relative to a still-current witness and an independently retained restart
anchor. It does not establish the legitimacy of an external issuer or provide
a physical monotonic counter. Those remain explicit trust obligations.

## Provisioning and current-head assumptions

The root supplies a provision identity, fixed authority policy, witness
implementation identity, and authentication key outside candidate input. The
selected reference cases use deterministic test credentials so their semantic
packets can be reconstructed across platforms. Those published credentials are
fixtures and are not suitable for protecting a deployed service.

A witness startup also requires an independently retained expected witness
head. Initialization uses the provisioned genesis anchor; a later startup uses
the head retained from the preceding authenticated response. The implementation
checks the witness ledger and the AI authority journal against that anchor.
Reading the head out of the same untrusted ledger and then supplying it as the
expected value would not establish freshness and is outside the contract.

The protocol assumes legitimate initial provisioning, protected authentication
material, a current independent anchor, and one authoritative witness for that
provision. A party that can roll back both the witness and every independent
anchor, or launch two independently accepted copies with the same authority,
can defeat those assumptions. The formal controls therefore include a
counterexample to an unconditional claim that rolling back the witness cannot
permit repeated issuance. A hash chain alone does not provide freshness.

The implementation uses domain-separated HMAC authentication for requests and
responses. The generic Lean model exposes authenticity predicates for reads
and mutation requests; it proves consequences conditional on those predicates
and the fixed provision.
It does not prove HMAC security, key secrecy, file-system isolation, or a general
refinement from arbitrary Python execution to Lean.

The request and response directions share a trusted key. A malicious holder of
that key can forge either direction; this protocol does not provide remote
nonrepudiation or distinguish such a holder from the witness. Its stale-state
protection assumes the trusted client/verifier arrangement and a current
witness. The public selected fixture makes no external authentication claim.

## Witness operations and controller lifetimes

The cursor binds the witness revision, witness head, and underlying AI authority
journal head. A fresh request nonce binds a response to the requesting
controller's current interaction. Reads disclose a current cursor and public
state; they do not confer the owner credential for an outstanding lease.

An advancement compares all cursor fields with the witness's current state and
checks the provision and nonce. The witness recomputes the AI issuance or
completion transition using its own fixed policy, source registry, contexts,
and evaluators. The caller cannot submit an arbitrary replacement authority
state or use a self-asserted completion as authorization.

Reservation durably charges the full declared envelope before evaluation. The
holder of a newly issued lease must supply the matching live owner capability
to execute it. This capability is not an attestation of OS process identity.
Observing a current lease through a read, replaying a
previous request, or presenting a competing request based on the old cursor
cannot acquire ownership or advance the authority a second time.

Completion uses the unchanged AI/AH reference evaluation and its exact source,
checkpoint, objective, evaluator, grant, and result bindings. The witness owns
that execution path. The permitted sources remain the two retained inactive AF
projections. These selected source sessions do not become a new linked physical
two-step execution or an update to an active store.

A witness reopening records a new witness lifetime and revokes the old live
owner capability. If a reservation was pending, its full envelope remains
charged and its completion remains unresolved. A restarted controller cannot
resume, refund, or complete that old lease merely by retaining the files or
recovering its identifier. Loss of an acknowledgement does not undo an already
persisted advancement; the current witness head determines whether a retry is
stale.

## Mathematical scope

The generic interface proves current-state consequences of accepted reads,
exact issuance and completion consequences of accepted advancements, rejection
of stale provision/cursor/nonce inputs, and exclusion of competing advancement
from the same former cursor. Owner and reopen rules preserve the distinction
between observing a pending lease and holding a live execution capability.

Reachable witness states project to reachable AI authority states. The inherited
per-source consumption and reference-cost bounds therefore hold for those
projected states. Completed declared reference work plus the full envelope of
an outstanding reservation is bounded by permanently reserved work, and that
reservation is bounded by the fixed authority allowance. Reopening does not
refund an allowance or create a completion receipt.

Opaque identifiers in the generic model do not prove that two registered
identifiers correspond to different physical sources. Likewise, fixed context
and evaluator functions are parameters of the general result. The selected
certificate instantiates them with the retained AH reference definitions; it
does not authenticate arbitrary external campaign histories.

## Observed reference execution and reconstruction

Fresh preparation runs an actual separate stdio witness process for each
selected lifetime. The shared two-source case restarts the witness between
completed source sessions; the interrupted case reopens with a charged pending
reservation; the aggregate-denial case checks that unused charged capacity
cannot be reissued beyond the shared allowance.

The evidence retains three different kinds of material:

* The canonical semantic packet and exact witness/authority/operation journal
  images describe the selected protocol transitions and reference results.
* Original native process records retain each witness invocation's start,
  observed completion, input, output, and error streams. Their individual
  hashes are bound into the application plan separately from the deterministic
  packet.
* The pinned Lean completed-stage lineage binds generated sources, compiler
  identity, import resolution, native command results, compiled objects, named
  theorem audits, and designated negative controls.

The three selected cases require five witness lifetimes, four issued leases,
three completed reference sessions, one denied lease, and one fully charged
pending reservation. The completed sessions examine ten candidates and record
thirty metered reference operations. The shared two-source case reserves cost
7,168 and records actual declared reference cost 1,008. These are reference
tariff amounts; they do not measure the witness protocol's total work.

The gate copies original journals and native records only after checking them,
then verifies the copied bytes again. Saved-evidence reconstruction derives the
semantic images without launching a witness/task-worker process or compiler,
or persisting a new reservation. Reference evaluation is recomputed in memory,
and the retained original native records are verified. Reconstructed images do not count as newly observed execution.

Application validation freshly compiles all eleven required modules. Development
may reuse explicitly verified AI compiled imports to check the new module;
such reuse is recorded as development preparation and supplies no fresh AJ
application compilation credit. The finalized Python test count, named theorem
inventory, negative controls, and total formal stages are frozen in the sealed
kit and checked against the source-bound application records.

Only completed application validation and evidence reconstruction can set the
two narrow completion flags:

```text
witnessed_authority_head_checked
witnessed_controller_issuance_checked
```

Draft code, parser fixtures, generated proof text, an unfinished process, or an
existing compiled object alone cannot establish either flag.

## Resource interpretation and remaining obligations

The resource theorem retains the AH reference tariff: one descriptor admission
and two bounded DSL probes per attempted candidate, with vector `(1, 2, 8, 8)`
and cost 112. Full bounded envelopes are reserved permanently, including unused
capacity and interrupted reservations.

Provision verification, HMAC, RPC transport, nonce handling, ledger replay,
hashing, source reconstruction, preparation, objective/evaluator checks,
controller bookkeeping, journal and file-system work, proof checking, tests,
host CPU/memory, historical cost, and broader campaign activity remain outside
that tariff. This increment does not establish complete resource accounting or
OS containment. Reference witness processes are counted separately from live
task-worker sessions and live challenges, both of which remain zero.

All 24 broader Phase 17 claim flags remain false. In particular, AJ does not
close legitimate external provisioning, protection of the witness and restart
anchor against joint rollback or cloning, live campaign objective/evaluator
authorization, complete campaign budget authority, physical execution
attestation, or root-transition refinement.

The next integration work must bind this checked interface to an independently
provisioned durable authority with justified current-head persistence and
exclusivity, and connect its policy and accounting to the actual live campaign.
Active promotion, independent replay, full frontier and recursive-productivity
recertification, Gate E, and Phase 17 exit remain open. The fixed finite catalog
continues to give bounded results, not arbitrary repeated strict improvement.
