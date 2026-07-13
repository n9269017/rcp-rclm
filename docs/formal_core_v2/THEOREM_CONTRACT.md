# Formal Core v2 theorem contract

## Contract status

This document freezes the implemented abstract Gate A kernel, the finite
classical Gate B reference, the substantive Gate B RCLM-to-RCP refinement, the
conditional architecture-engine theorem, the Paper II direct-engine and
robust-reflective alignment layer, and the bounded seed-library packet-builder
refinement.

```text
abstract Gate A successor/preservation kernel: complete
finite classical/diagonal Gate B reference: complete
substantive Gate B RCLM-to-RCP refinement: complete at the declared scope
conditional architecture successor/direct-engine theorem: implemented
Paper II robust-reflective alignment interfaces: implemented
bounded seed-library and packet-builder refinement: implemented
conditional bounded seed-library infinite trajectory: implemented
finite-dimensional quantum Gate C: not complete
exact Paper I/Paper II semantic equivalence: not complete
executable theorem-to-runtime refinement: not licensed
```

A clean build or a structural theorem does not by itself establish exact paper
semantics. Every remaining semantic identification stays visible as a
refinement premise or a later-gate obligation.

## Abstract one-step contract

Let `M_t` be an admissible predecessor, `u_t` a typed update, `M_{t+1}` the
claimed successor, and `c_t` a certificate. Trusted-checker acceptance proves:

```text
M_{t+1} = Apply(M_t,u_t)
computed residuals are nonpositive
protected distinctions satisfy the declared quantitative non-loss bound
candidate-tied recovery satisfies the declared recovery bound
protected invariants are preserved
progress is nondecreasing
strict progress follows from a certified strict witness
trust evidence is valid
resource evidence is valid
reality-containment evidence is valid
the successor remains admissible
```

This is checker soundness. It is not successor existence, generator coverage,
grammar completeness, or useful-successor completeness.

## Finite and conditional infinite composition

For every finite accepted trajectory, the project proves:

```text
state-domain and invariant closure
complete per-step obligations
progress composition
transported protected-value bounds
aggregate local recovery accounting
composed endpoint rollback under explicit recovery laws
Lyapunov/motion composition
ambiguity-collapse composition
transported relevance composition
```

The endpoint recovery theorem uses explicit self-zero, triangle, and
nonexpansiveness laws. Aggregate local recovery accounting and endpoint rollback
remain distinct statements.

`RCP.SuccessorAvailability` is an explicit premise of the abstract infinite
trajectory theorem. Standard `Summable` assumptions bridge nonnegative monitor
budgets to uniform finite-prefix bounds. `NoOpFeasible` remains separate from
both checker soundness and successor availability.

## Gate B finite classical contract

For a normalized finite distribution `p`:

```text
H(p)         = - Σ_i p_i log p_i
D_KL(p || q) =   Σ_i p_i log(p_i/q_i)
```

Under the explicit denominator-support premise, finite KL is nonnegative and
self-divergence is zero. The uniform and biased binary distributions have a
proved strictly positive KL gap and supply a nonconstant divergence witness.

The zero-head conservative extension preserves support, Shannon entropy, and KL
exactly, and dropping the added coordinate recovers the predecessor exactly.
This is a theorem for the declared extension, not for every stochastic channel.

The concrete binary checker accepts exactly the declared improvement and
stability packets, rejects an invalid successor, and refines Boolean acceptance
to the complete abstract obligations. Progress is actual reduction in KL
distance to the target. The worked trajectory is:

```text
initial -> target -> target
```

Its first step is strictly improving and its second step is an accepted
stability continuation.

## Substantive RCLM-to-RCP refinement

`RCLM.KernelRefinement` preserves:

```text
state and typed update semantics
admissibility and protected invariants
protected values, transports, and budgets
state distance, recovery maps, and recovery budgets
progress and strict witnesses
computed residuals
trust, resource, and reality propositions
```

`RCLM.MonitorRefinement` preserves the named Lyapunov, motion, ambiguity, and
relevance quantities and transports. `RCLM.CheckerRefinement` preserves actual
Boolean checker acceptance. The concrete RCLM checker also validates every
canonical architecture state, update, successor, and certificate field.

## Conditional architecture-engine contract

`RCLM.ArchitectureEngine` separates:

```text
architecture theorem domain
witness-library coverage
generator proposal
certificate construction
candidate selection
successor realization
trust-anchor validity and preservation
resource authorization and soundness
successor-domain closure
```

An `ArchitectureEngineStep` contains an actual witness, proposal, certificate,
candidate, resource record, all engine-stage evidence, and checker acceptance.
The theorem

```lean
RCLM.rclm_architecture_successor_theorem
```

returns a typed RCLM successor, complete RCLM obligations, forgotten core
checker acceptance, complete forgotten RCP obligations, recovery and monitor
refinement evidence, successor-domain membership, admissibility, invariant
preservation, and trust/resource preservation.

`ArchitectureSuccessorAvailability` is a separate premise of
`conditional_infinite_architecture_trajectory_exists`. It is never derived from
checker soundness.

## Paper II direct-engine and robust-reflective alignment

The direct-engine layer explicitly distinguishes:

```text
accepted continuation
strict successor availability
predecessor-ability preservation
strict ability expansion
successor viability
projection realization
```

The robust-reflective layer explicitly represents verifier-schema transport,
uncertainty-envelope transport, goal transport and drift, anti-circular trust,
proof/checking budgets, successor-verification persistence, optional reality and
tractability certificates, summable failure risk, and the separately supplied
Borel-Cantelli consequence.

These are proposition-valued interfaces. Names alone do not identify them with
the full Paper II semantic objects.

## Bounded seed-library and packet-builder contract

`RCLM.PaperIIBoundedSeedLibrary` supplies:

```text
seedDomain
finite witness set
finite certificate-word grammar
word-depth and proof-length bounds
witness/proposal/certificate/candidate/resource decoders
seed-domain to architecture-domain refinement
grammar nonemptiness on the seed domain
word-to-witness membership
witness-library coverage
generator proposal evidence
certificate-construction evidence
candidate-selection evidence
successor-realization evidence
resource authorization
checker acceptance
successor seed-domain closure
```

A grammar word is converted to the already compiled architecture-engine step by:

```lean
RCLM.PaperIIBoundedSeedPacket.toEngineStep
```

The generic packet-builder theorem is:

```lean
RCLM.paper_ii_bounded_seed_packet_builder_sound
```

It yields complete RCLM obligations, complete successor-verification
obligations, successor seed-domain membership, verifier-schema persistence,
uncertainty-envelope persistence, and the declared goal-drift bound.

The architecture bridge is:

```lean
RCLM.paper_ii_bounded_seed_packet_refines_architecture
```

It additionally yields the complete forgotten RCP obligations and recovery and
monitor refinement evidence.

`RCLM.PaperIISeedSemanticIdentification` requires pointwise equalities between
the paper-declared and compiled objects:

```text
verifier schema, transport, and refinement relation
uncertainty envelope, transport, and refinement relation
goal, goal transport, goal distance, and goal-drift budget
```

No identification is inferred from field names.

## Conditional bounded seed-library recursion

`RCLM.PaperIIBoundedSeedPredecessor` combines an architecture predecessor with
seed-domain membership. The recursive bounded-seed construction uses the
library's explicit grammar-nonemptiness and successor-closure fields. It proves:

```lean
RCLM.conditional_infinite_paper_ii_bounded_seed_trajectory_exists
RCLM.infinite_paper_ii_bounded_seed_step_result
RCLM.infinite_paper_ii_bounded_seed_step_refines_architecture
```

Thus every selected finite grammar word generates a checked packet and every
successor returns to the declared bounded seed domain. This does not imply
unbounded grammar completeness, arbitrary learned-system entry, or strict
improvement at every step.

## Concrete bounded binary reference

The concrete bounded grammar is:

```text
initial: {improve}
target:  {stabilize}
maximum update-word depth: 1
maximum proof-word length: 1
rejected word: absent from every active grammar
```

The concrete semantic bridge identifies the declared verifier schema,
uncertainty envelope, and goal objects with the compiled finite binary Paper II
interfaces. The resulting path performs one strict KL-derived improvement and
then accepted stability continuations.

## Remaining exact-paper obligations

Exact Paper I/Paper II closure still requires:

1. exact safe-state and update-admissibility semantic refinement;
2. conditional-expectation and squared-motion identification;
3. semantic ambiguity and mutual-information identification;
4. finite-dimensional quantum relative entropy and channel recovery;
5. architecture-wide semantic identity beyond the bounded binary reference;
6. any theorem asserting strict useful successor availability at every step;
7. learned-system entry and generator/compiler refinement;
8. the final combined paper-facing wrapper.

## Public bounded-seed theorem surface

```lean
RCLM.paper_ii_bounded_seed_packet_available
RCLM.paper_ii_bounded_seed_packet_builder_sound
RCLM.paper_ii_bounded_seed_packet_refines_architecture
RCLM.conditional_infinite_paper_ii_bounded_seed_trajectory_exists
RCLM.infinite_paper_ii_bounded_seed_step_result
RCLM.infinite_paper_ii_bounded_seed_step_refines_architecture
RCLM.ClassicalBinary.initial_bounded_seed_packet_builder_refinement
RCLM.ClassicalBinary.initial_bounded_seed_direct_engine_refinement
RCLM.ClassicalBinary.classical_bounded_seed_packet_builder_refinement
RCLM.ClassicalBinary.classical_infinite_bounded_seed_trajectory_exists
RCLM.ClassicalBinary.classical_infinite_bounded_seed_step_result
RCLM.ClassicalBinary.classical_infinite_bounded_seed_step_refines_architecture
```

Reserved for later final closure:

```lean
MainTheorem.mechanized_conditional_successor_closure
```
