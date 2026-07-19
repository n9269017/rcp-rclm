# Phase 9 — learned-language-model refinement contract

## Purpose

Phase 9 freezes the exact executable interpretation of the Formal Core v3 Gate D
learned capability-frontier theorem before a compact language model is introduced.
The completed Runtime v2 checker, hashing, Lean bridge, promotion, rollback, and replay
components remain authoritative and unchanged.

## Selected scope

```text
model family:
compact_decoder_only_transformer_v1

maximum parameter count:
50,000,000

authoritative task class:
lean_theorem_completion_v1

authoritative task verifier:
pinned_lean_theorem_verifier_v1
```

The selected task class contains finite Lean theorem-completion packets whose success is
established by an independent pinned Lean verifier. Natural-language diagnostics may be
retained as nonauthoritative evidence but cannot create a capability-frontier entry.

## Learned state

A `LearnedRCLMState` contains:

```text
base RCLM state hash
model family and architecture hash
weight-tree, adapter, and tensor-manifest hashes
tokenizer and vocabulary hashes
training and optimizer policy hashes
data-curriculum hash
generator and planner policy hashes
retrieval policy and memory-state hashes
tool and verification policy hashes
resource policy and self-model hashes
self-hosting generator/planner/protocol binding
finite task ledger
finite certified capability frontier
parent package linkage
```

The trusted checker, Lean verifier, canonical serializer, trust anchor, promotion ledger,
and held-out answer store are deliberately absent from the learned package.

## Capability frontier

For state `M`, the runtime frontier is the sorted finite set `F(M)` in
`M.capability_frontier`. Every member must have exactly one independent certification
record bound to the current model identity.

A Phase 9 transition requires:

```text
F(M) subseteq F(M')
F(M') \ F(M) is nonempty
all protected predecessor tasks remain certified
all newly added tasks are in the held-out partition
certificate.new_task_ids = F(M') \ F(M)
```

This is an exact finite-set condition. A candidate Boolean such as
`strict_improvement: true` is not part of the schema and cannot authorize expansion.

## Typed updates

The update grammar includes:

```text
weight_update
adapter_update
optimizer_policy_update
training_policy_update
data_curriculum_update
retrieval_update
memory_update
planner_update
generator_update
architecture_extension
tokenizer_update
tool_policy_update
verification_policy_update
resource_policy_update
self_model_update
```

Every operation binds one semantic component target, a normalized package path, and
unequal before/after hashes. The operation-target set must equal the set of actual
component changes measured from predecessor and candidate records.

## Learned certificate

The `LearnedCertificatePacket` binds:

```text
predecessor, candidate, update, and base-certificate hashes
frontier before/after hashes
protected and newly certified task IDs
frontier-retention evidence
new-task verifier evidence
model-output density evidence
entropy/KL/QRE evidence
goal-drift evidence
training-data provenance
held-out isolation evidence
architecture compatibility
self-hosting evidence
resource evidence
rollback evidence
held-out access policy
active generator, planner, and proposal protocol
```

The evidence hashes are content references. Phase 9 freezes their presence and linkage;
later phases must implement and independently verify their payload semantics.

## Self-hosting hash boundary

The learned state includes a `SelfHostingBinding` containing the generator component,
planner component, proposal protocol, and self-hosting contract hashes. The canonical
state hash covers this binding. Therefore changing any self-hosting component changes the
learned-state semantic hash.

The state also requires:

```text
self_hosting.generator_component_hash = policies.generator_policy_hash
self_hosting.planner_component_hash   = policies.planner_policy_hash
```

The certificate binds the active predecessor generator, planner, and proposal protocol.
A later generator update must appear as a substantive typed operation and a changed
successor state hash.

## Numerical and trust boundary

Phase 9 introduces no new floating-point acceptance source. Exact task-set relations are
computed with finite sets and hashes. Future model-output KL/QRE evidence must continue to
use Runtime v2 exact rationals or certified outward intervals.

Always untrusted:

```text
learned model and weights
generator and planner
training and optimizer process
candidate task claims
candidate scores
candidate evidence declarations
```

Authoritative after validation:

```text
canonical serializer and hashes
held-out policy and external answer store
independent task verifier
pinned Lean bridge
hardened checker
promotion and rollback controller
independent replay
```

## Infinite-theorem boundary

Phase 9 preserves the Gate D theorem shape:

```text
frontier-expanding successor availability
implies
an infinite strictly frontier-expanding accepted trajectory
```

It does not prove the availability premise for the selected compact model family.
