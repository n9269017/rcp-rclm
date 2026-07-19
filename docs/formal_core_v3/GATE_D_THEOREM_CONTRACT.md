# Gate D theorem contract

## Objects

Fix types:

```text
State
Update
BaseCertificate
Protected
ResidualIndex
Task
Generator
Proposal
PackageHash
```

with a finite decidable task equality and an inherited v2 kernel:

```text
base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex
```

A Gate D `FrontierKernel` supplies:

```text
frontier : State → Finset Task
solves : State → Task → Prop
frontierSound : task ∈ frontier state → solves state task

activeGenerator : State → Generator
activePackageHash : State → PackageHash
generatorBound : State → Generator → Prop
proposalProducedBy : Generator → State → Proposal → Prop
proposalBindsCandidate : State → Proposal → RCP.Candidate State Update → Prop
packageHashBound : State → Generator → PackageHash → Prop

goalDrift : State → Candidate → Nat
goalDriftBudget : State → Candidate → Nat
resourceUsed : State → Candidate → Nat
resourceBudget : State → Candidate → Nat

informationValue : State → Real
informationBudget : State → Candidate → Real
informationBudget_nonnegative : 0 ≤ informationBudget state candidate
```

## Strict frontier expansion

For predecessor state `M` and candidate `a` with successor `a.next`, define:

```text
StrictFrontierExpansion M a :=
  frontier M ⊆ frontier a.next ∧
  card (frontier M) < card (frontier a.next)
```

Because the frontiers are finite, this entails proper inclusion and at least one new
frontier element.

## Learned certificate

The Gate D certificate contains:

```text
base certificate
protected predecessor frontier
generator
proposal
generator package hash
```

These are untrusted fields until the learned checker proves their relations.

## Gate D-specific one-step obligations

For predecessor `M`, candidate `a`, and learned certificate `c`, the additional
obligations are:

```text
c.protectedFrontier ⊆ frontier M
c.protectedFrontier ⊆ frontier a.next
StrictFrontierExpansion M a

c.generator = activeGenerator M
generatorBound M c.generator
proposalProducedBy c.generator M c.proposal
proposalBindsCandidate M c.proposal a

c.generatorPackageHash = activePackageHash M
packageHashBound M c.generator c.generatorPackageHash

goalDrift M a ≤ goalDriftBudget M a
resourceUsed M a ≤ resourceBudget M a
informationValue a.next ≤ informationValue M + informationBudget M a
```

## Complete learned accepted step

The complete proposition is:

```text
LearnedAcceptedStep M a c :=
  RCP.StepObligations base M a c.base ∧
  SpecificObligations learned M a c
```

Thus Gate D never substitutes frontier growth for the inherited safety,
non-loss, recovery, trust, resource, containment, progress, or domain obligations.

## Trusted learned checker

A `TrustedLearnedChecker learned baseChecker` contains:

```text
check : State → Candidate → LearnedCertificate → Bool

check M a c = true →
  baseChecker.check M a c.base = true

base.admissible M →
base.protectedInvariant M →
check M a c = true →
  SpecificObligations learned M a c
```

## One-step theorem

The theorem:

```lean
Learned.learned_accepted_step_sound
```

has the exact form:

```text
base.admissible M
→ base.protectedInvariant M
→ learnedChecker.check M a c = true
→ LearnedAcceptedStep learned M a c
```

The inherited base obligations follow from base-checker soundness; the new learned
obligations follow from the learned checker proof field.

## Finite trajectory

A finite Gate D trajectory of horizon `N` contains:

```text
state t
candidate t
certificate t
accepted transition at every t < N
state (t + 1) = (candidate t).next
```

The project proves, for every `t ≤ N`:

```text
frontier (state 0) ⊆ frontier (state t)
card (frontier (state 0)) + t ≤ card (frontier (state t))
```

In particular:

```text
card (frontier (state 0)) + N ≤ card (frontier (state N))
```

It also proves:

```text
cumulativeResourceUsed t ≤ cumulativeResourceBudget t
cumulativeGoalDrift t ≤ cumulativeGoalDriftBudget t
informationValue (state t) ≤
  informationValue (state 0) + cumulativeInformationBudget t
```

and transports the existing v2 finite protected-loss, endpoint-recovery,
Lyapunov/motion, and trust conclusions through the forgotten base trajectory.

## Conditional infinite theorem

Define frontier-expanding successor availability:

```text
∀ M,
  base.admissible M →
  base.protectedInvariant M →
  Nonempty (AcceptedLearnedSuccessor checker M)
```

Then:

```lean
Learned.conditional_infinite_learned_frontier_trajectory_exists
```

constructs an infinite accepted learned trajectory beginning at the supplied initial
domain state.

Every transition in that trajectory satisfies `StrictFrontierExpansion`.

The theorem is therefore:

```text
frontier-expanding successor availability
→ existence of an infinite frontier-expanding accepted trajectory
```

It does not prove the availability premise.

## Non-implications

The theorem contract does not permit the following inferences:

```text
learned checker soundness → an accepted learned successor exists
one frontier-expanding reference step → open-ended generator completeness
finite card growth → semantic usefulness outside the task verifier
frontier inclusion → all model behavior is preserved
accepted stability → strict frontier growth
generator named in certificate → proposal was generated by it
package hash named in certificate → package binding is valid
conditional infinite theorem → autonomous or unbounded RSI
```
