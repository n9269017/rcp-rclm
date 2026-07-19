# Gate D foundation validation

## Validation state

The Gate D formal foundation is implementation-complete at the declared abstract and
one-step reference scope. The theorem stack, exact dependency manifest, documentation,
machine-readable claim record, source gates, and public theorem audit have passed at
one exact source head.

A final evidence-only head will rerun the same workflow before the PR is marked ready.

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

This head closed the Lean implementation itself.

## Validated source-and-documentation head

```text
branch head:
411a89afe0549fc3190ee4f47d20a72fac37aa06

PR merge-test commit:
f56f533f88693a87be6cddccaa86807e57bd70da

workflow run:
29673625985

conclusion:
success
```

This head additionally contained the committed dependency graph, formalization
manifest, theorem contract, scope, assumption register, exit criteria, and workflow
manifest validation.

## Build result

```text
Lean toolchain:
leanprover/lean4:v4.31.0

build jobs:
2630

v2 dependency tree:
1c5a32b4a5c7a2d78ba820e535eac3e69a2a85b8

validated v3 project tree:
99d5e42311f5293d2df3fdb36f04fb968946e63d

resolved v3 lake-manifest SHA-256:
02921d2d60e7ef077c7fdb5fd184a7b4e9dc240d0f145cb1747ff9d99386151a

validated formalization-manifest SHA-256:
f312017dadab7a9b8506bb48be167446308f3127264c4aa4f0f050a6173cb1ca
```

The workflow verifies that the v2 project tree is unchanged relative to `main` and
that `lake update` does not alter the committed v3 dependency manifest.

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

## Workflow artifacts

Implementation artifact:

```text
name:
formal-core-v3-gate-d-29673278100-1

digest:
sha256:1e44ba91495b1779bd11ff5892b6f4798fcec08f9225c6b6f13d85312082459a
```

Source-and-documentation artifact:

```text
name:
formal-core-v3-gate-d-29673625985-1

digest:
sha256:a712bde46b6309b8a45429f9c9616cc1877a3c5946ecc1e33d5fc6d51bf0517e
```

The latter artifact contains:

```text
lake_build.log
forbidden_proof_tokens.txt
project_axiom_declarations.txt
gate_d_axioms.txt
audit_metadata.txt
lake-manifest.json
formalization_manifest.json
```

## Conclusions supported

The validated source supports:

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

## Evidence-head revalidation

The evidence records intentionally refer to the already validated source head rather
than attempting a self-referential hash. After these evidence-only updates, the same
pinned workflow must pass once more. The PR discussion will bind that final evidence
head and workflow artifact without changing source files again.

## Claim boundary

This validation does not establish a real learned language model, open-ended planning,
generator self-modification, generic frontier-expanding successor availability,
self-hosted multi-generation recursion, arbitrary learned-system refinement, full
Paper I or Paper II equivalence, or autonomous/unbounded RSI.
