# Gate D foundation validation

## Validation state

The abstract Gate D theorem stack and one-step reference have completed an initial
pinned build, forbidden-token scan, project-local-axiom scan, and public theorem
axiom audit.

This record distinguishes the validated implementation head from the later
documentation and manifest closure head.

## Validated implementation head

```text
branch head:
8cea1eabbc0f07abb4138a8afc0d7965f4dd637b

PR merge-test commit:
bf6780970815fcca7a2b3de8b905f08fa42987b6

workflow run:
29673278100

conclusion:
success
```

## Build result

```text
Lean toolchain:
leanprover/lean4:v4.31.0

build jobs:
2630

v2 dependency tree:
1c5a32b4a5c7a2d78ba820e535eac3e69a2a85b8

v3 project tree:
fefaa8c943c520f276d5b07428cbf3023839e07c

resolved v3 lake-manifest SHA-256:
02921d2d60e7ef077c7fdb5fd184a7b4e9dc240d0f145cb1747ff9d99386151a
```

The workflow verifies that the v2 project tree is unchanged relative to `main`.

## Proof hygiene

```text
forbidden proof tokens:
none

project-local axiom declarations:
none

sorryAx in public theorem reports:
none
```

## Public theorem audit

The audit covers:

```text
learned_accepted_step_sound
finite_learned_frontier_card_growth
finite_learned_final_frontier_growth
finite_learned_resource_bound
finite_learned_goal_drift_bound
finite_learned_information_nonregression
finite_learned_composed_nonloss_bound
finite_learned_endpoint_recovery_bound
finite_learned_lyapunov_motion_bound
conditional_infinite_learned_frontier_trajectory_exists
infinite_learned_frontier_strict
Reference.improvement_learned_accepted_step
Reference.reference_frontier_card_growth
```

The reported axiom union is:

```text
propext
Classical.choice
Quot.sound
```

These are the ordinary Lean/mathlib foundational dependencies already present in
the validated v2 theorem stack, not Gate D project-local axioms.

## Workflow artifact

```text
artifact name:
formal-core-v3-gate-d-29673278100-1

artifact digest:
sha256:1e44ba91495b1779bd11ff5892b6f4798fcec08f9225c6b6f13d85312082459a
```

The artifact contains:

```text
lake_build.log
forbidden_proof_tokens.txt
project_axiom_declarations.txt
gate_d_axioms.txt
audit_metadata.txt
```

## Implementation conclusions supported

The validated implementation head supports:

```text
one-step Gate D checker soundness
strict finite frontier inclusion and cardinal growth
card(F_0) + N ≤ card(F_N)
cumulative resource and goal-drift bounds
cumulative selected information non-regression
inherited protected-loss, recovery, Lyapunov/motion, trust, and domain results
conditional infinite learned trajectory under explicit successor availability
one non-vacuous Gate B RCLM frontier-expansion reference
```

## Final-head closure still required

Before Gate D foundation is marked ready for review, the repository must still:

```text
commit the exact v3 lake-manifest
commit and validate the machine-readable v3 formalization manifest
close every documentation exit criterion
rerun the pinned build and audit at the exact final branch head
record the final head, merge-test commit, workflow run, and artifact digest
```

## Claim boundary

This validation does not establish a real learned language model, open-ended planning,
generator self-modification, generic frontier-expanding successor availability,
self-hosted multi-generation recursion, arbitrary learned-system refinement, or
autonomous/unbounded RSI.
