# Formal Core v2 theorem contract

## Ordinary mathematical statement

Let `M_t` be an admissible predecessor system state at recursive time `t`.
Let `u_t` be a proposed typed update, let `M_{t+1}` be the candidate's claimed
successor state, and let `c_t` be a certificate packet. Let the formal kernel
supply:

- a typed successor semantics `Apply(M_t,u_t)`;
- a protected-distinction family with explicit cross-time transport;
- a nonconstant divergence/information quantity;
- a declared quantitative loss budget;
- a constructive recovery/rollback map tied to `u_t`;
- a state distance and recovery budget;
- a protected-invariant predicate;
- a progress functional and strict-witness predicate;
- computed certificate residuals;
- trust/verifier, resource, and reality/uncertainty predicates; and
- an admissible successor domain.

For a trusted checker `Check`, the one-step target is:

```text
Admissible(M_t)
∧ ProtectedInvariant(M_t)
∧ Check(M_t,u_t,M_{t+1},c_t) = true

⇒

M_{t+1} = Apply(M_t,u_t)
∧ every computed residual is nonpositive
∧ every declared protected distinction is preserved within the loss budget
∧ Recover(M_t,u_t,M_{t+1}) returns within the recovery budget of M_t
∧ ProtectedInvariant(M_{t+1})
∧ Progress(M_t) ≤ Progress(M_{t+1})
∧ (StrictWitness(M_t,u_t,M_{t+1},c_t)
    ⇒ Progress(M_t) < Progress(M_{t+1}))
∧ TrustValid(M_t,u_t,M_{t+1},c_t)
∧ ResourceValid(M_t,u_t,M_{t+1},c_t)
∧ RealityContained(M_t,u_t,M_{t+1},c_t)
∧ Admissible(M_{t+1}).
```

The checker theorem is a soundness theorem. It is not, by itself, a theorem that
an improving candidate exists.

## Finite composition target

For a finite sequence

```text
M_0 --(u_0,c_0)--> M_1 -- ... --> M_N
```

such that `M_0` is admissible and invariant-preserving and every transition is
accepted by the trusted checker, prove:

1. every `M_t`, `0 ≤ t ≤ N`, is admissible;
2. every `M_t` satisfies the protected invariant;
3. every transition satisfies the complete one-step obligations;
4. progress is monotone along the path;
5. total permitted information loss and recovery error are bounded by the
   declared composed budgets; and
6. strict progress occurs at every transition carrying a certified strict
   witness.

## Conditional infinite-horizon target

Assume explicitly:

```text
SuccessorAvailability:
  for every admissible invariant-preserving state M,
  there exists a candidate and certificate accepted by the trusted checker.
```

Under this assumption and an admissible invariant-preserving initial state,
construct an infinite accepted trajectory and prove that every state remains
admissible and invariant-preserving and every step satisfies the one-step
obligations.

`SuccessorAvailability` is the abstract generator-completeness/availability
hypothesis. It must remain visible in the final theorem statement. It may not be
silently inferred from checker soundness.

## Lean-facing target declarations

The public Lean theorem names are reserved as follows:

```lean
RCP.accepted_step_sound
RCP.finite_trajectory_closure
RCP.finite_progress_monotone
RCP.finite_composed_nonloss_bound
RCP.finite_composed_recovery_bound
RCP.conditional_infinite_trajectory_exists
RCLM.rclm_checker_refines_rcp
RCLM.rclm_architecture_successor_theorem
MainTheorem.mechanized_conditional_successor_closure
```

No theorem name above is considered delivered merely because it appears in this
contract. Its implementation status must be recorded in the formalization
manifest and theorem map.
