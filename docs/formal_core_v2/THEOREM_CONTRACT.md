# Formal Core v2 theorem contract

## Contract status

This document freezes the **abstract Gate A successor kernel**. It is not, by itself,
the exact statement of Paper I's `thm:main_rcp` or any Paper II architecture theorem.
The completed line-by-line comparison is recorded in
`GATE_A_PAPER_ALIGNMENT_AUDIT.md`.

Current status:

```text
abstract one-step contract: implemented
abstract finite composition: implemented
abstract conditional infinite construction: implemented
clean build and proof-admission audit: passed
exact Paper I/Paper II agreement: not yet achieved
```

The paper-facing quantitative monitor, endpoint-recovery, concrete information-theory,
and RCLM-refinement obligations below remain part of theorem closure and may not be
inferred from the abstract kernel alone.

## Ordinary abstract mathematical statement

Let `M_t` be an admissible predecessor system state at recursive time `t`. Let `u_t`
be a proposed typed update, let `M_{t+1}` be the candidate's claimed successor state,
and let `c_t` be a certificate packet. Let the formal kernel supply:

- typed successor semantics `Apply(M_t,u_t)`;
- a protected-distinction family with explicit cross-time transport;
- a nonconstant divergence/information interface;
- a declared quantitative loss budget;
- a constructive recovery/rollback map tied to `u_t`;
- a state distance and recovery budget;
- a protected-invariant predicate;
- a progress functional and strict-witness predicate;
- computed certificate residuals;
- trust/verifier, resource, and reality/uncertainty predicates; and
- an admissible successor domain.

For a trusted checker `Check`, the abstract one-step target is:

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

The checker theorem is a soundness theorem. It is not, by itself, a theorem that an
improving candidate exists, that a generator covers a witness, or that a paper-specific
packet can be constructed.

## Abstract finite composition target

For a finite sequence

```text
M_0 --(u_0,c_0)--> M_1 -- ... --> M_N
```

such that `M_0` is admissible and invariant-preserving and every transition is accepted
by the trusted checker, prove:

1. every `M_t`, `0 ≤ t ≤ N`, is admissible;
2. every `M_t` satisfies the protected invariant;
3. every transition satisfies the complete one-step obligations;
4. the abstract progress functional is monotone along the path;
5. transported protected values satisfy the declared additive loss-budget bound;
6. the sum of actual local recovery errors is bounded by the sum of declared local
   recovery budgets; and
7. strict progress occurs at each transition carrying a certified strict witness.

Items 1–6 are currently implemented. Item 7 is available per step through
`StepObligations.strictProgressWhenWitness`; a separately named finite strict-witness
corollary may be added when needed by the paper-facing wrapper.

### Stronger endpoint-recovery target

Paper I's finite constructive-recovery theorem is stronger than item 6. Exact alignment
requires additional abstract structure:

```text
MetricLaws(stateDistance)
∧ TypedComposition(recover_0,...,recover_{N-1})
∧ Nonexpansive(recover_t) for every t

⇒

distance(
  Recover_0∘Recover_1∘...∘Recover_{N-1}(M_N),
  M_0
) ≤ Σ_t recoveryBudget_t.
```

This endpoint theorem is not currently delivered by
`RCP.finite_composed_recovery_bound`.

## Abstract conditional infinite-horizon target

Assume explicitly:

```text
SuccessorAvailability:
  for every admissible invariant-preserving state M,
  there exists a candidate and certificate accepted by the trusted checker.
```

Under this assumption and an admissible invariant-preserving initial state, construct
an infinite accepted trajectory and prove that every state remains admissible and
invariant-preserving and every step satisfies the one-step obligations.

`SuccessorAvailability` is the abstract generator-completeness/availability
hypothesis. It remains visible in the theorem statement and may not be inferred from
checker soundness.

This theorem is only the abstract recursion/domain-closure skeleton. It is not the
full Paper I or Paper II infinite seed-library theorem, whose named builder, witness
library, transport, uncertainty, trust, goal-identity, resource, reality-containment,
and summability premises remain to be refined into the kernel.

## Exact Paper I wrapper obligations

An exact Lean-facing wrapper for Paper I `thm:main_rcp` must additionally represent
and prove the following instead of hiding them inside an uninterpreted residual index:

1. the relation between `Admissible ∧ ProtectedInvariant` and the paper's
   `K_RCP^state`;
2. the relation between checker-established obligations and the paper's
   `A_RCP(t,rho,Phi)`;
3. the no-op-feasibility premise, or an explicit paper revision removing it from the
   mapped theorem;
4. the Lyapunov drift inequality with `eta_t`, conditional expectation, and the
   cumulative squared-motion conclusion;
5. the unsupported ambiguity-collapse monitor `U_t`, its `zeta_t` budget, and the
   cumulative bound;
6. the self-model-relevance monitor, valid cross-time transport, the `xi_t` budget,
   and its mutual-information telescoping bound;
7. the exact interpretation of protected values as finite KL or quantum relative
   entropy, including support/domain laws;
8. the summability assumptions and resulting infinite-horizon analytic conclusions;
   and
9. the stronger composed endpoint recovery-map theorem when the paper rollback claim
   is mapped.

Until those obligations are discharged, the abstract theorem bundle is structurally
related to, but not identical with, Paper I's main theorem.

## Exact Paper II refinement obligations

The RCLM architecture theorem layer must define substantive RCLM state, update,
certificate, and checker semantics and prove that forgetting an accepted RCLM packet
to RCP preserves every theorem-relevant object:

```text
update application and typed successor
protected values and their transports
loss and recovery budgets
state distance and recovery map
progress and strict witnesses
residual evaluator
trust, resource, and reality predicates
predecessor/successor admissibility and invariants
checker result and checker soundness
```

Only after this refinement exists may the project introduce:

```lean
RCLM.rclm_checker_refines_rcp
RCLM.rclm_architecture_successor_theorem
```

## Lean-facing target declarations

The public theorem names are reserved as follows:

```lean
RCP.accepted_step_sound
RCP.finite_trajectory_closure
RCP.finite_progress_monotone
RCP.finite_composed_nonloss_bound
RCP.finite_composed_recovery_bound
RCP.finite_endpoint_recovery_bound
RCP.conditional_infinite_trajectory_exists
RCLM.rclm_checker_refines_rcp
RCLM.rclm_architecture_successor_theorem
MainTheorem.mechanized_conditional_successor_closure
```

`RCP.finite_endpoint_recovery_bound` is newly reserved by the alignment audit and is
not yet implemented.

No theorem name above is considered delivered merely because it appears in this
contract. Implementation, build/audit status, paper alignment, and any narrowing must
be recorded in the formalization manifest and theorem map.
