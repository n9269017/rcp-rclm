# Gate E theorem contract

## Inherited objects

Gate E imports the complete Formal Core v3 Gate D surface:

```text
RCP base kernel and trusted checker
Gate D learned frontier kernel
Gate D trusted learned checker
learned certificate packet
learned accepted-step theorem
finite learned trajectory theorems
conditional infinite learned trajectory theorem
```

Gate E never substitutes search success for Gate D safety. An accepted autonomous step must
first be a complete accepted Gate D step.

## Gate E kernel

For an inherited Gate D kernel `learned`, the Gate E kernel adds:

```text
recursiveFrontier : State -> Finset RecursiveTask
recursivelyProductive : State -> RecursiveTask -> Prop
recursiveFrontierSound

objectiveEndogenous
programEndogenous
challengeFresh
historyBound
noRouteHints
programBindsCandidate
programBindsCertificate
searchCost
searchBudget
```

## Gate E certificate

The Gate E packet contains:

```text
complete Gate D learned packet
endogenous objective
endogenous typed mutation program
immutable history hash
hidden challenge hash
protected recursive-productivity frontier
optional strict recursive-productivity witness
```

These are untrusted fields until the Gate E checker proves every relation.

## Complete accepted step

For predecessor `M`, candidate `a`, and Gate E certificate `c`:

```text
AutonomousAcceptedStep M a c :=
  LearnedAcceptedStep M a c.learned
  and GateESpecificObligations M a c
```

The Gate E-specific obligations require:

```text
objective selected by the active package
program produced by the active package
fresh hidden challenge binding
immutable history binding
absence of route-level hints
program-to-candidate binding
program-to-Gate-D-certificate binding
protected recursive frontier certified and retained
complete recursive frontier retained
strict recursive witness valid when present
search cost within search budget
```

## Deterministic bounded search

Given a finite ordered attempt list:

```text
firstAccepted checker state attempts
```

returns the first candidate whose Gate E checker verdict is true.

The following are proved.

### Search soundness

```text
firstAccepted = some attempt
implies checker accepts attempt.
```

### Exhaustion soundness

```text
firstAccepted = none
implies every attempt in the declared enumeration is nonaccepted.
```

### Relative completeness

```text
if some enumerated attempt is accepted,
then firstAccepted returns some accepted attempt.
```

### Nonstagnation or certified exhaustion

For every finite attempt list, either:

```text
an accepted attempt is returned; or
a SearchExhaustionCertificate exists for that exact list.
```

## Recursive productivity

Every accepted Gate E step proves:

```text
R(M) subseteq R(M')
```

If `c.recursiveWitness = some r`, then:

```text
r notin R(M)
r in R(M')
```

## Finite trajectory

For every accepted Gate E trajectory of horizon `N`:

```text
|F(M_0)| + N <= |F(M_N)|
R(M_0) subseteq R(M_t) for every t <= N
cumulativeSearchCost(t) <= cumulativeSearchBudget(t)
```

All inherited Gate D and RCP finite-trajectory conclusions remain available through the
forgetful map to the Gate D trajectory.

## Constructive availability

A package-bound autonomous improver supplies:

```text
history : State -> HistoryHash
enumerate : State -> HistoryHash -> List SearchAttempt
```

Constructive successor availability means that deterministic bounded search returns an
accepted attempt at every admissible invariant-preserving state.

The theorem:

```text
constructive_successor_availability_on_declared_class
```

proves this availability from the narrower premise that an accepted candidate exists in each
declared finite enumeration.

## Conditional infinite theorem

The theorem:

```text
conditional_infinite_autonomous_rclm_trajectory_exists
```

constructs an infinite trajectory whose candidate at every step is the output selected by the
declared bounded autonomous search.

Its premise remains conditional:

```text
constructive successor availability on every reachable admissible state.
```

It does not prove generic accepted-candidate existence.
