# Gate E formal validation

## Exact-source policy

The permanent Formal Core v4 workflow checks out the exact pull-request head rather than the
synthetic merge ref. It fails unless:

```text
git rev-parse HEAD = declared source head
Formal Core v3 tree = current main Formal Core v3 tree
lake update leaves the frozen v4 manifest byte-identical
```

The audit artifact records:

```text
exact source head
exact source tree
Lean toolchain
Formal Core v3 tree
Formal Core v4 tree
lake-manifest SHA-256
formalization-manifest SHA-256
complete build log
forbidden-proof scan
project-axiom scan
public-theorem axiom report
```

## Build boundary

The v4 package is pinned to:

```text
Lean 4:  leanprover/lean4:v4.31.0
mathlib: fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
```

Formal Core v3 is imported as an unchanged path dependency, and its transitive Formal Core
v2 dependency remains frozen.

## Public theorem audit

The workflow builds and prints axioms for all 13 public Gate E theorems:

```text
autonomous_accepted_step_sound
recursive_productivity_retained
recursive_productivity_strictly_expands_when_witnessed
firstAccepted_sound
firstAccepted_none
bounded_search_complete
search_exhaustion_sound
nonstagnation_or_certified_exhaustion
finite_autonomous_frontier_growth
finite_recursive_productivity_retained
finite_autonomous_resource_bound
constructive_successor_availability_on_declared_class
conditional_infinite_autonomous_rclm_trajectory_exists
```

The accepted foundation permits only the standard Lean/mathlib logical axioms reported by
the inherited projects. `sorryAx` is forbidden.

## Source audit

The Gate E source tree is rejected if it contains:

```text
sorry
sorryAx
admit
project-local axiom declarations
```

## Claim-boundary audit

The formalization manifest must:

```text
mark the formal foundation closed
mark the Runtime v4 contract foundation validated
retain Gate E, Phase 14, generic availability, empirical unboundedness,
mutable-checker, noncommuting, and asynchronous-daemon claims as false
```

## Evidence identity

Exact final source head, workflow, artifact ID, artifact digest, tree identities, and manifest
digests are recorded in the pull-request evidence after the final exact-head workflow is
green. They are not hardcoded into the source tree, avoiding an evidence-binding loop.
