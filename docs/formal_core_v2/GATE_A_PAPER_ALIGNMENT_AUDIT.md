# Gate A theorem-to-paper alignment audit — 2026-07-12

## Status

```text
comparison pass: complete
mismatch resolution: open
exact Paper I theorem equivalence: false
exact Paper II architecture theorem equivalence: false
Gate A abstract kernel build/audit: passed
Gate A paper-alignment closure: not yet passed
```

This audit compares the pinned Paper I and Paper II theorem statements against the
compiled Formal Core v2 declarations. It is an alignment audit, not a reinterpretation
of a successful build as proof of a stronger theorem.

## Immutable source pins

```text
Paper I:
  papers/paper-I-rcp-math/main.tex
  blob 084eae21d252d205d2012b62744c1506644e3e58

Paper II:
  papers/paper-II-rclm-architecture/main.tex
  blob 9b51be8294ad79fd4f63522b01e0f617f0bf2ffd

Formal Core v2 composition/audit baseline:
  source commit 2b68a0048482ad481dfe6b05ce3c5a3262c7a08a
  workflow run 29184258470
```

## Alignment vocabulary

- **Exact**: the assumptions and conclusion agree after only definitional unfolding
  or harmless renaming.
- **Structural**: the Lean theorem has the same inference shape, but paper-specific
  quantities, transports, laws, or certificate meanings are still abstracted away.
- **Deferred**: exact identification depends on Gate B, Gate C, or the substantive
  RCLM refinement layer.
- **Mismatch**: the current Lean declaration proves a genuinely different or weaker
  statement and must be strengthened or the mapped paper claim must be narrowed.
- **Additional Lean guarantee**: the Lean kernel proves an obligation not stated as a
  conclusion of the mapped paper theorem. This does not repair a missing paper
  conclusion.

## Executive verdict

The present Lean project is a clean, audited **abstract conditional successor
kernel**. It is not yet an exact mechanization of either paper's surfaced main
theorem.

The strongest current correspondences are structural:

1. trusted-checker acceptance can expose a complete one-step obligation packet;
2. accepted finite trajectories preserve the abstract theorem domain and invariant;
3. abstract protected values telescope under transported distinctions and additive
   loss budgets;
4. abstract progress is monotone;
5. an infinite accepted path can be selected under an explicit successor-availability
   hypothesis.

The main unresolved differences are substantive:

1. Paper I's main theorem has explicit Lyapunov, expectation, squared-motion,
   quantum-relative-entropy, ambiguity-collapse, mutual-information, and summability
   conclusions that do not occur in the current Lean theorem statements.
2. Paper I's finite constructive recovery theorem builds a composed endpoint recovery
   map; the current Lean theorem only bounds the sum of local recovery errors.
3. Paper I includes no-op feasibility and named RCP safe-set/admissibility semantics;
   these are not explicit in the current abstract checker theorem.
4. The current abstract protected-value theorem is not yet identified with finite KL
   divergence or quantum relative entropy.
5. Paper II's RCLM checker refinement and architecture successor theorem do not yet
   exist in Lean; the current RCLM files only freeze typed data and a partial
   structural refinement contract.

Accordingly, no Paper I or Paper II theorem is marked fully mechanized by this audit.

# Paper I alignment

## I.1 Conditional Non-Lossy Self-Update Preservation Theorem

Pinned paper label:

```text
thm:main_rcp
```

Current candidate Lean surface:

```lean
RCP.accepted_step_sound
RCP.finite_trajectory_closure
RCP.finite_trajectory_step_sound
RCP.finite_progress_monotone
RCP.finite_composed_nonloss_bound
RCP.finite_composed_recovery_bound
```

### Assumption-by-assumption comparison

| Paper I premise | Current Lean representation | Status | Finding |
|---|---|---|---|
| `rho_0 ∈ K_RCP^state` | `K.admissible (state 0)` and `K.protectedInvariant (state 0)` | Structural | No theorem currently proves that these two abstract predicates are definitionally equivalent to the paper's full state-only RCP safe set. |
| no-op update is feasible | none | Mismatch | No `NoOpFeasible` field, predicate, or wrapper premise exists. The paper proof does not use this premise for telescoping, but exact statement agreement still requires it to be represented or removed from the paper theorem. |
| accepted update `Phi_t ∈ A_RCP(t,rho_t)` | `checker.check ... = true` plus `TrustedChecker.sound` | Structural | Lean packages the semantics of admissibility into the checker's soundness field. It does not yet define or refine the paper's named `A_RCP` relation. |
| Lyapunov drift with error `eta_t` | potentially one residual component; no dedicated field or law | Mismatch | Residual nonpositivity alone does not yield the paper's expectation and cumulative squared-motion inequality. |
| protected relative-entropy loss bounded by `epsilon_t` | `ProtectedNonLoss`, `protectedValue`, `transportProtected`, `lossBudget` | Deferred | The telescoping shape is present, but `protectedValue` is not yet proved to be the paper's quantum relative entropy. Gate C is required for that exact identification. |
| unsupported ambiguity collapse bounded by `zeta_t` | potentially one residual component | Mismatch | There is no explicit ambiguity-collapse monitor, one-step inequality, or finite cumulative theorem. |
| self-model relevance loss bounded by `xi_t` | potentially one residual component | Mismatch | There is no explicit mutual-information monitor, transport law, or finite telescoping theorem for `I(Z_t;Y_t)`. |
| all paper transports and estimator meanings are valid | generic `transportProtected`, residual evaluator, trust/resource/reality predicates | Structural / Deferred | The current kernel leaves these meanings to an instantiation. No Paper I refinement theorem supplies the specific maps and estimator laws. |

### Conclusion-by-conclusion comparison

| Paper I conclusion | Current Lean result | Status | Finding |
|---|---|---|---|
| `rho_T ∈ K_RCP^state` | `finite_trajectory_closure` proves admissibility and invariant preservation | Structural | Exact only after a refinement proves the abstract predicates coincide with the paper safe-set clauses. |
| Lyapunov expectation and total squared-motion bound | none | Mismatch | Not implied by `finite_progress_monotone` or generic residual nonpositivity. |
| quantum-relative-entropy endpoint lower bound | `finite_composed_nonloss_bound` | Structural / Deferred | Same additive telescoping pattern over an abstract protected value; exact quantum meaning requires Gate C. |
| bounded cumulative unsupported ambiguity collapse | none | Mismatch | Must be added as an explicit monitor theorem or removed from the mapped paper claim. |
| bounded self-model relevance loss | none | Mismatch | Must be added with explicit cross-time transport and mutual-information semantics. |
| infinite-horizon boundedness under summable `eta+epsilon+zeta+xi` | none | Mismatch | `conditional_infinite_trajectory_exists` proves path existence/domain closure, not the paper's analytic summability conclusions. |

### Additional Lean guarantees

The current one-step Lean obligation packet additionally exposes:

```text
typed successor equality
constructive one-step recovery
progress nondecrease
strict progress when a strict witness is certified
trust validity
resource validity
reality containment
successor admissibility
```

These are useful abstract obligations, but they do not substitute for the missing
Paper I quantitative conclusions.

### Alignment result

```text
Paper I thm:main_rcp versus current Lean bundle: NOT EXACT
classification: structural core plus substantive open mismatches
```

## I.2 Finite-horizon constructive predecessor recovery

Pinned paper label:

```text
thm:finite_horizon_constructive_recovery
```

Paper I assumes one-step recovery channels `R_t` and proves that the composed map

```text
R_0 ∘ R_1 ∘ ... ∘ R_{T-1}
```

recovers the initial state from the endpoint within `sum_t r_t`, using the triangle
inequality and contractivity/nonexpansiveness of the recovery channels.

Current Lean theorem:

```lean
RCP.finite_composed_recovery_bound
```

proves only

```text
sum of actual local recovery errors <= sum of local recovery budgets.
```

It does not define a composed endpoint recovery map and does not prove an endpoint
distance bound.

### Missing laws required for exact alignment

The abstract kernel currently supplies only nonnegativity of `stateDistance`. An exact
abstract version of the paper proof requires at least:

1. a triangle inequality for `stateDistance`;
2. a nonexpansiveness or declared Lipschitz law for each recovery map;
3. type-compatible composition of the per-step recovery maps;
4. a definition of the composed recovery map along a linked trajectory; and
5. an endpoint theorem comparing the recovered final state with the initial state.

### Alignment result

```text
Paper I finite endpoint recovery versus current Lean aggregate theorem: MISMATCH
```

The current theorem remains valid and useful, but the theorem map must not call it an
exact mechanization of the paper's endpoint rollback theorem.

## I.3 Checker soundness and canonical reference checking

Relevant pinned paper labels include:

```text
thm:batch13ra_canonical_checker_soundness
```

The current Lean object

```lean
RCP.TrustedChecker
```

contains soundness as a proof field, and `RCP.accepted_step_sound` simply exposes that
field after predecessor-domain hypotheses are supplied.

This matches the logical form

```text
checker accepts -> obligations
```

but it is not yet the paper's canonical finite checker proof. The paper theorem fixes a
particular finite packet grammar, concrete diagonal states, exact non-loss/recovery,
ability expansion, goal transport, singleton uncertainty containment, frozen trust
anchor, and finite cost ledger. None of those concrete objects is instantiated by the
current Gate A checker.

### Alignment result

```text
abstract checker-soundness schema: Structural
canonical Paper I checker theorem: Deferred to Gate B plus concrete checker refinement
```

## I.4 Finite proof-carrying trajectories

The current declarations

```lean
RCP.FiniteAcceptedTrajectory
RCP.finite_trajectory_closure
RCP.finite_trajectory_step_sound
```

match the induction skeleton of the paper's proof-carrying finite trajectory claims:
an initial domain witness, accepted linked steps, and preservation of the successor
domain.

They do not yet expose the paper-specific packet grammar, prefix checker, builder trace,
goal transport, uncertainty envelope, trust anchor, or cost ledger. Those facts can be
carried by an instantiation only after a refinement theorem proves that checker
acceptance implies the paper packet obligations.

### Alignment result

```text
finite induction shape: Structural
paper-specific finite reference theorem: Deferred
```

## I.5 Conditional infinite trajectory versus domain-relative RRST

Relevant pinned Paper I labels include:

```text
thm:batch12b_domain_relative_infinite_rrst
thm:batch12b_combined_domain_relative_rrst
```

The Lean definition

```lean
RCP.SuccessorAvailability checker
```

states that every admissible invariant-preserving state has a nonempty accepted
successor packet. `RCP.conditional_infinite_trajectory_exists` then uses this explicit
availability assumption to select an infinite accepted trajectory.

This correctly preserves the essential logical boundary:

```text
checker soundness does not imply successor existence.
```

It is nevertheless only a structural skeleton of the paper theorem. Paper I also
requires seed-domain entry/persistence, a sound packet builder, explicit residuals,
verifier-schema transport, uncertainty-envelope transport, goal-identity transport,
anti-circular trust evidence, resource/proof budgets, optional reality-containment and
tractability certificates, and summable failure/goal-drift budgets. The current Lean
infinite theorem packages none of those as named visible premises or conclusions.

### Alignment result

```text
explicit availability boundary and infinite recursion: Structural
full Paper I domain-relative infinite theorem: NOT EXACT
```

# Paper II alignment

## II.1 Typed architecture data

Current Lean files provide:

```lean
RCLM.State
RCLM.Update
RCLM.CertificatePacket
RCLM.Refinement
```

These are legitimate typed interfaces. They avoid booleans hardcoded to true and carry
architecture data/evidence as supplied types.

However, the paper's RCLM state and packet semantics are not obtained merely by naming
fields. The current structures do not prove that their fields realize the paper's
density state, semantic registers, protected pair sets, uncertainty envelopes,
verifier schemas, ability certificates, trust graph, goal transport, projection
realization, estimator protocols, or resource ledgers.

### Alignment result

```text
RCLM syntax/interface shape: Structural
Paper II semantic realization: Deferred
```

## II.2 RCLM-to-RCP refinement

The present `RCLM.Refinement` supplies:

```text
forgetState
forgetCandidate
forgetCertificate
RCLM admissibility -> RCP admissibility
candidate-next compatibility
RCLM invariant transport -> RCP invariant
```

It does not yet prove preservation of:

```text
update application semantics
protected values and protected transports
loss budgets
recovery maps, distances, and recovery budgets
progress and strict witnesses
residual evaluators
trust predicates
resource predicates
reality-containment predicates
checker results or checker soundness
```

Therefore the reserved theorem

```lean
RCLM.rclm_checker_refines_rcp
```

is not derivable from the current refinement contract without adding those obligations.

### Alignment result

```text
Paper II substantive RCLM-to-RCP refinement: NOT IMPLEMENTED
```

## II.3 RCLM checker soundness

Relevant pinned Paper II label:

```text
thm:rclm-batch13r-checker-soundness
```

Paper II's theorem assumes a concrete RCLM checker soundness contract and concludes
that an accepted proof-carrying successor packet satisfies typed transition validity,
explicit successor-verification residuals, goal identity, anti-circular trust,
proof/checking/resource budgets, and optional reality/tractability clauses.

No RCLM checker is currently defined in Formal Core v2. `RCP.TrustedChecker` is not a
substitute until an RCLM checker and a theorem preserving its result under the
RCLM-to-RCP forgetful maps are supplied.

### Alignment result

```text
Paper II RCLM checker theorem: NOT IMPLEMENTED
```

## II.4 RCLM finite and infinite architecture successor theorems

Relevant pinned Paper II labels include:

```text
thm:rclm-batch13r-proof-carrying-finite-trajectory
thm:rclm-batch12b-combined-domain-relative-rrst
thm:rclm-batch12b-domain-relative-infinite-rrst
thm:rclm-constructive-direct-nl-rsi-engine
```

The current RCP finite/infinite theorems provide reusable abstract induction and choice
machinery. They do not prove the architecture-specific conclusions above. In
particular, Formal Core v2 currently has no theorem that an RCLM engine constructs a
candidate, no theorem that a candidate carries the paper's RCLM packet, and no theorem
that RCLM checker acceptance refines to the RCP obligations.

The file `RCLM/ArchitectureTheorem.lean` correctly records these theorem names as
future targets and currently introduces no theorem declaration.

### Alignment result

```text
Paper II architecture successor theorem: NOT IMPLEMENTED
```

# Alignment-derived obligations

The comparison produces the following tracked obligations.

| ID | Obligation | Resolution gate | Current state |
|---|---|---|---|
| ALIGN-01 | Represent Paper I's state-safe-set and update-admissibility semantics explicitly, or publish a narrowed theorem mapping | Gate A / paper mapping | open |
| ALIGN-02 | Represent no-op feasibility in the exact paper-facing wrapper, or remove it from the mapped paper theorem if formally unused | Gate A / paper mapping | open |
| ALIGN-03 | Add explicit Lyapunov drift, expectation, squared-motion, and summability data/theorems for `thm:main_rcp` | Gate A schema plus concrete instance | open |
| ALIGN-04 | Add explicit ambiguity-collapse and self-model-relevance monitor composition | Gate A schema plus Gate B/C semantics | open |
| ALIGN-05 | Refine abstract protected values to finite KL and then quantum relative entropy | Gate B and Gate C | open |
| ALIGN-06 | Strengthen recovery composition to a typed endpoint recovery-map theorem with metric and nonexpansiveness laws | Gate A | open |
| ALIGN-07 | Distinguish the abstract availability theorem from the paper's seed-library/builder/transport/summability theorem | theorem map | resolved by explicit narrowing in this audit |
| ALIGN-08 | Expand `RCLM.Refinement` to preserve every theorem-relevant RCP field | RCLM after Gate B | open |
| ALIGN-09 | Define an executable/propositional RCLM checker and prove `rclm_checker_refines_rcp` | RCLM after Gate B | open |
| ALIGN-10 | Prove `rclm_architecture_successor_theorem` only after the substantive checker refinement exists | RCLM after Gate B | open |
| ALIGN-11 | Introduce the final paper-facing wrapper theorem only after Paper I quantitative and Paper II refinement obligations are discharged | final theorem layer | open |

# Selected resolution order

The optimal next order is:

1. **Gate A endpoint recovery strengthening.** This is a genuine abstract mismatch and
   can be resolved without waiting for KL or quantum matrices.
2. **Gate A paper-monitor schema.** Add explicit abstract monitor data for Lyapunov
   drift, ambiguity collapse, self-model relevance, and cumulative/summable budgets.
3. **Gate B concrete finite classical instance.** Identify the protected-value layer
   with actual finite KL or an explicitly equivalent finite information quantity and
   supply a nontrivial worked example.
4. **RCLM substantive refinement.** Expand field preservation and prove the RCLM
   checker refinement.
5. **Gate C quantum instance.** Discharge the exact quantum-relative-entropy and
   finite-dimensional channel claims used by Paper I and Paper II.
6. **Final paper-facing wrapper.** State the exact theorem with all assumptions visible
   and update the paper theorem map only after a clean build and axiom audit.

# Gate decision after this audit

The following statement is now justified:

```text
The Gate A abstract composition kernel is implemented, clean-CI-built, and audited.
```

The following stronger statements are not yet justified:

```text
Gate A is paper-aligned and closed.
Paper I's main theorem is mechanized.
Paper II's architecture theorem is mechanized.
The current aggregate recovery theorem is the paper's endpoint rollback theorem.
The abstract protected value is already KL or quantum relative entropy.
```

Therefore `gate_a_complete` remains `false` under the current project policy, and the
Python checker/generator/closed-loop phase remains unlicensed.