# Phase 17I — Typed learned-package and evidence bindings

Development increment. Base: `3826d94cd3af510e9fbdc1b38a8e83071b8c0aec`.
PR #68 remains draft and unmerged. This is not full Phase 17 or Gate E closure.

## What is integrated

Phase 17H independently compared physical components and supplied two bounded
operational contracts. This increment projects the measured predecessor and
candidate separately into the **actual immutable**
`RcpRclmFormalCoreV3.Learned.PackageState` structure. It does not define a duplicate
structure with similar field names and then treat it as the root structure.

The eleven component fields are architecture, weights, generator, planner,
training policy, retrieval, memory, tokenizer, verification policy, resource
policy and self-model. An external execution-context field binds runtime/tool
policy/package metadata. All 164 inherited files are assigned exactly once.
Each binding includes a canonical path, byte length and content digest. The
physical verifier compares predecessor and candidate bytes directly before
constructing these records, then remeasures the packages after evaluation.

The typed `base` field holds the selected installed-program identities; the
capability-frontier field holds the prospective task identifiers. The selected
synthetic candidate must preserve all component groups, append exactly one
fresh program (8 to 9), and insert exactly its transcript-bound finite capability
(21 to 22). These are prospective registry/set facts, not an active package or
a newly accepted frontier. A task identifier alone is not a proof that it is solved.

The generated Lean source contains independently measured before and after
literals. The candidate is not defined by copying the predecessor. A negative
control changes one candidate weight-file digest without changing the premise
being checked; the real compiler must reject its selected equality certificate.

## Operational evidence composition

The runtime recomputes Phase 17F successor facts and Phase 17H operational facts
from physical packages and an externally anchored sealed transcript. Package,
parent, objective, challenge, program and transcript bindings must all agree.
The serialized binding packet is canonical, immutable and detached on access;
rehashing altered input does not replace independent recomputation.

The default fixture runner pins the already completed Phase 17H operator report:

- source `eb78c099106d1d9e5b6523646a5139a0c5c8dff5`;
- report `artifacts/development/phase17h/op-eb78c099106d/gate/execution.json`;
- SHA-256 `6cfacc08015a8e2ace156c3ddb3de68e380c9e840d2e19f83b01fffd2981fdac`.

Reuse requires that exact report, its original source identity, successful real
compiler outcomes, log digests, exact 172-name axiom inventory, and a rejected
negative control. The freshly recomputed operational packet and both regenerated
proof sources must match it. The runner rejects modifications to existing Python,
script or Lean execution sources since the completed H boundary. New additive
files are allowed. Historical proof execution is not claimed to occur again;
a hash comparison is not identity authentication or independent replay.

The 172 public planner queries and 4,488 integer-tool executions per package are
recomputed because the new binding must refer to the physical candidate now
being checked. The 172 old arithmetic proofs are **retained, not rerun**.
No new recursive contract is declared. All nineteen historical recursive labels
remain as before; no complete legacy task is newly recertified.

## Eight new formal audit targets

`LearnedStateBinding.lean` imports the unchanged formal root. Its `RootState`
is an abbreviation for the actual `Learned.PackageState`, instantiated with
file-reference lists and the selected registry/frontier identifiers.

1. `frozen_view_preserved`: typed append leaves the eleven component projections
   and execution context unchanged.
2. `fixed_interpretation_retained`: equal frozen views give equal results on every
   input under the **same fixed pure interpretation**.
3. `information_value_retained`: equal frozen views give the same value under a
   fixed real-valued functional of that view.
4. `root_information_bound`: connects this equality to the real
   `Learned.FrontierKernel.informationValue` and its nonnegative budget, **provided
   an explicit semantic-binding hypothesis is supplied**.
5. `frontier_retained`: inclusion under the declared task insertion.
6. `frontier_grows`: strict cardinal growth when the inserted identifier is fresh.
7. `selected_typed_binding`: exact relations for independently measured literals.
8. `selected_interpretation_retention`: specializes fixed-interpretation retention
   to that measured pair.

The information lemma's premise says the root information field factors through
the frozen view. This increment does **not** establish that premise for the full
RCLM information/coherence semantics. It does not redefine quantum entropy as a
hash, file count, registry size, or constant. Frontier inclusion and cardinality
do not establish the root's `solves` relation or frontier-soundness premise.

Physical-byte-to-digest/literal extraction remains a trusted Python binding.
The Lean file references are not 27 MB of embedded model bytes. Arbitrary mutable
execution state, changed interpreters, the neural decoder implementation, and
hostile same-user execution are not formally verified here. The pinned compiler,
imports and compiled dependency caches retain their declared trust assumptions.

## Fail-closed completion assessment — not an acceptance checker

The packet inventories the existing 11 base, 12 learned and 12 autonomous fields.
It retains eight explicit missing witness classes: full base refinement; task
meaning/frontier soundness; generator/proposal/package provenance refinement;
full goal and information semantics; complete resources; complete recursive
frontier/root binding; durable fresh-challenge/history consumption; and active
atomic promotion/rollback.

The assessment is intentionally:

```
status                    = blocked_missing_semantic_witnesses
root_acceptance_evaluated = false
authorization_issued      = false
```

This is **not a new complete trusted checker** and cannot be enabled with a caller
boolean or report filename. The old field inventory is used as an obligation
catalog, not as a claim that every field has been discharged. A later full root
verifier still has to construct/check the actual semantics and accepted-step
certificate. No `LearnedAcceptedStep` or `AutonomousAcceptedStep` is constructed.

A passed typed-binding gate and a blocked full-root assessment are different
results. Passing this increment does not change a pending full-root claim to true.

## Validation and installer

The guarded kit uses an exact-head short-path clone, UTF-8 reads/writes, resolved
temporary directories, command-scoped Git long paths, NUL-delimited literal
staging, and byte-preserving evidence. It requires all 54 new tests, 57 operational
regressions, the retained H report binding, and actual checking of all eight new
Lean audits plus negative rejection. Mock compiler-control tests are not proofs.
It installs or updates no tools/dependencies and requests no hosted workflows.

The source commit and later evidence-only commit are distinct. A failure before
advancement leaves the original checkout unchanged and preserves the failed
workspace. A network push failure after local advancement is explicitly recorded.
No reset, amendment, force push, main merge, release, DOI or billing change is made.

The fixture is synthetic and known-answer; no live challenge campaign or training
is started. New claims remain false: full learned/root acceptance, complete
recursive-productivity/frontier recertification, decoder formal verification,
complete resources, promotion, live capability gain, Phase 17/Gate E closure and
EGC-0. Cross-turn continuation/objectives, campaigns and required independent/
platform validation remain outstanding. Keep PR #68 draft and unmerged.
