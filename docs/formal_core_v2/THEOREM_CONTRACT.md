# Formal Core v2 theorem contract

## Contract status

This document freezes the implemented abstract Gate A kernel, the finite
classical Gate B reference, the substantive RCLM-to-RCP refinements, the
conditional architecture-engine theorem, the Paper II direct-engine and
robust-reflective alignment layer, the bounded seed-library packet-builder
refinement, and the selected finite-dimensional diagonal Gate C reference.

```text
abstract Gate A successor/preservation kernel: complete
finite classical/diagonal Gate B reference: complete
substantive Gate B RCLM-to-RCP refinement: complete at declared scope
conditional architecture successor/direct-engine theorem: implemented
Paper II robust-reflective alignment interfaces: implemented
bounded seed-library and packet-builder refinement: implemented
conditional bounded seed-library infinite trajectory: implemented
selected finite-dimensional diagonal Gate C reference: complete at declared scope
substantive selected quantum RCLM-to-RCP refinement: complete at declared scope
general noncommuting quantum extension: not complete
exact Paper I/Paper II semantic equivalence: not complete
executable theorem-to-runtime refinement: not licensed
```

A clean build or a structural theorem does not by itself establish exact paper
semantics. Every remaining semantic identification stays visible as a refinement
premise or a later obligation.

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

Its first step is strictly improving and its second step is an accepted stability
continuation.

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
Boolean checker acceptance. Concrete RCLM checkers also validate every canonical
architecture state, update, successor, and certificate field.

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

```lean
RCLM.rclm_architecture_successor_theorem
```

returns a typed RCLM successor, complete RCLM obligations, forgotten core checker
acceptance, complete forgotten RCP obligations, recovery and monitor refinement
evidence, successor-domain membership, admissibility, invariant preservation,
and trust/resource preservation.

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
tractability certificates, summable failure risk, and separately supplied
almost-sure consequences.

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

A grammar word is converted to the compiled architecture-engine step by:

```lean
RCLM.PaperIIBoundedSeedPacket.toEngineStep
```

```lean
RCLM.paper_ii_bounded_seed_packet_builder_sound
```

returns complete RCLM and successor-verification obligations, successor seed-domain
membership, verifier-schema persistence, uncertainty-envelope persistence, and
the declared goal-drift bound.

```lean
RCLM.paper_ii_bounded_seed_packet_refines_architecture
```

additionally returns the complete forgotten RCP obligations and recovery/monitor
refinement evidence.

`RCLM.PaperIISeedSemanticIdentification` requires pointwise equalities between the
paper-declared and compiled verifier, uncertainty, goal, transport, distance, and
budget objects. No identification is inferred from field names.

## Conditional bounded seed-library recursion

`RCLM.PaperIIBoundedSeedPredecessor` combines an architecture predecessor with
seed-domain membership. The recursive construction uses explicit grammar
nonemptiness and successor-closure fields. It proves:

```lean
RCLM.conditional_infinite_paper_ii_bounded_seed_trajectory_exists
RCLM.infinite_paper_ii_bounded_seed_step_result
RCLM.infinite_paper_ii_bounded_seed_step_refines_architecture
```

Every selected finite grammar word generates a checked packet and every successor
returns to the declared bounded seed domain. This does not imply unbounded grammar
completeness, arbitrary learned-system entry, or strict improvement at every step.

## Selected Gate C density-matrix contract

The selected finite-dimensional representation is:

```text
QuantumMatrix n = Matrix (Fin n) (Fin n) ℂ
```

A `DiagonalDensityMatrix n` contains a normalized nonnegative spectrum and exposes
the corresponding complex diagonal matrix. The formalization proves:

```text
matrix.IsHermitian
matrix.PosSemidef
Matrix.trace matrix = 1
```

`DensityMatrixEvidence` packages those obligations.
`PositiveDiagonalDensityMatrix n` additionally proves strict positivity of every
spectral mass.

The representation is exact for finite commuting/diagonal density matrices. It is
not a formalization of every noncommuting density operator.

## Selected Gate C entropy and QRE contract

For diagonal spectra `p` and `q`:

```text
S(ρ)      = - Σ_i p_i log p_i
D(ρ || σ) =   Σ_i p_i log(p_i/q_i)
```

The support relation is explicit. QRE nonnegativity requires denominator support
for every positive numerator mass; positive spectral densities discharge this
premise constructively. Self-QRE is zero.

The selected two-level source and target have spectra `(1/4,3/4)` and `(3/4,1/4)`.
The project proves:

```text
D(source || target) = (1/2) * log 3
0 < D(source || target)
```

This supplies a nonconstant information quantity and a non-vacuous strict progress
witness.

## Selected Gate C channel and recovery contract

`RCP.QuantumFinite.FiniteDiagonalChannel n` contains:

```text
action on diagonal density matrices
complex-linear matrix action
state/matrix action agreement
trace preservation
Hermitian preservation
positive-semidefinite preservation
```

The selected update family is:

```text
stay -> identity channel
swap -> two-level basis-swap channel
```

The selected recovery channel is indexed by the actual update. Identity is its own
recovery; basis swap is involutive. The project proves exact recovery, von Neumann
entropy preservation, and QRE preservation for this selected family.

This contract does not assert a general CPTP data-processing theorem or a Petz
recovery theorem.

## Selected Gate C checker and trajectory contract

The substantive quantum state/update/certificate grammar accepts exactly:

```text
source + swap + target + improvement certificate
target + stay + target + stability certificate
```

The residual evaluator checks the actual typed transition and packet acceptance.
Trust, resource, and reality-containment gates are proposition-valued and have
explicit failure witnesses.

```lean
RCP.QuantumFinite.quantum_checker_refines_kernel
```

proves that Boolean checker acceptance, together with predecessor admissibility
and invariance, yields the complete abstract `StepObligations` bundle. A declared
invalid candidate is rejected.

The worked trajectory is:

```text
source -> target -> target
```

and proves strict first-step progress, endpoint recovery, Lyapunov/motion
composition, and transported relevance composition.

## Selected Gate C RCLM refinement contract

`RCLM.QuantumBinary` preserves the Gate A theorem-relevant fields and additionally
identifies:

```text
architecture state -> selected positive diagonal density
architecture update -> selected forward matrix channel
architecture update -> selected recovery matrix channel
architecture state -> selected von Neumann entropy
architecture state pair -> selected quantum relative entropy
```

```lean
RCLM.QuantumBinary.accepted_quantum_architecture_successor
```

returns:

```text
canonical architecture evidence
complete RCLM StepObligations
complete forgotten RCP StepObligations
successor density-matrix evidence
forward-channel realization
exact selected recovery
entropy preservation
quantum-relative-entropy preservation
```

The concrete improvement and stability packets instantiate this theorem.

## Gate C infinite-horizon boundary

The selected Gate C implementation instantiates the finite Gate A composition
results. Any infinite accepted quantum trajectory continues to require explicit
`RCP.SuccessorAvailability` or an independently supplied architecture availability
premise.

The checker does not prove that a next accepted candidate exists. The finite
trajectory proves one strict step followed by stable continuation, not indefinitely
strict improvement.

## Remaining exact-paper obligations

Exact Paper I/Paper II closure still requires, among other items:

1. exact safe-state and update-admissibility semantic refinement;
2. conditional-expectation and squared-motion identification;
3. semantic ambiguity and mutual-information identification;
4. arbitrary noncommuting density matrices and general matrix-log QRE;
5. arbitrary CPTP channels and general data processing;
6. trace-distance, Petz, or approximate recovery where claimed;
7. architecture-wide semantic identity beyond the finite references;
8. any theorem asserting strict useful successor availability at every step;
9. learned-system entry and generator/compiler refinement;
10. the final combined paper-facing wrapper.

## Public selected Gate C theorem surface

```lean
RCP.QuantumFinite.DiagonalDensityMatrix.matrix_isHermitian
RCP.QuantumFinite.DiagonalDensityMatrix.matrix_posSemidef
RCP.QuantumFinite.DiagonalDensityMatrix.matrix_trace_one
RCP.QuantumFinite.quantumRelativeEntropy_nonnegative
RCP.QuantumFinite.quantumRelativeEntropy_self
RCP.QuantumFinite.source_target_quantumRelativeEntropy_pos
RCP.QuantumFinite.selectedChannel_state_action
RCP.QuantumFinite.selectedChannel_recovery_exact
RCP.QuantumFinite.selectedChannel_vonNeumannEntropy_preserving
RCP.QuantumFinite.selectedChannel_quantumRelativeEntropy_preserving
RCP.QuantumFinite.quantum_checker_refines_kernel
RCP.QuantumFinite.quantumWorkedTrajectory_first_step_strict
RCP.QuantumFinite.quantumWorkedTrajectory_endpoint_recovery
RCLM.QuantumBinary.accepted_quantum_architecture_successor
RCLM.QuantumBinary.improvement_quantum_architecture_successor
RCLM.QuantumBinary.stability_quantum_architecture_successor
```

Reserved for later exact paper closure:

```lean
MainTheorem.mechanized_conditional_successor_closure
```
