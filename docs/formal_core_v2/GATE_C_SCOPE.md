# Gate C scope — implemented finite-dimensional diagonal quantum reference

## Current status

```text
Selected finite-dimensional diagonal implementation: complete
Complex matrix-valued density representation: complete
Hermitian/positive-semidefinite/trace-one evidence: complete
Spectral von Neumann entropy: complete
Support-aware diagonal quantum relative entropy: complete
Selected identity/swap channel family: complete
Exact selected recovery: complete
Concrete checker and invalid-packet rejection: complete
Finite accepted trajectory: complete
Substantive RCLM quantum refinement: complete
Dedicated Gate C theorem-axiom audit: complete
General noncommuting quantum extension: open
Exact full Paper I/Paper II semantic identity: open
```

The closure record is `GATE_C_CLOSURE.md`.

## Frozen representation

The implemented state representation is:

```text
QuantumMatrix n = Matrix (Fin n) (Fin n) ℂ
```

A `DiagonalDensityMatrix n` carries a finite normalized nonnegative spectrum and is represented by the corresponding complex diagonal matrix. A `PositiveDiagonalDensityMatrix n` additionally proves that every spectral mass is strictly positive.

For every selected density the Lean development proves:

```text
matrix.IsHermitian
matrix.PosSemidef
Matrix.trace matrix = 1
```

The reference dimension is two.

## Frozen information quantities

For a diagonal density with spectrum `p`, the selected entropy is:

```text
vonNeumannEntropy ρ = -∑ᵢ pᵢ log pᵢ
```

For diagonal densities with spectra `p` and `q`, the selected divergence is:

```text
quantumRelativeEntropy ρ σ = ∑ᵢ pᵢ log (pᵢ / qᵢ)
```

This is the exact spectral formula for the commuting diagonal reference. It is intentionally implemented through the proved finite Shannon/KL layer.

Nonnegativity for arbitrary diagonal densities carries an explicit support premise. Strictly positive spectral densities discharge that premise constructively.

## Frozen transition class

`FiniteDiagonalChannel n` packages:

```text
state action on diagonal density matrices
complex-linear matrix action
state/matrix action agreement
trace preservation
Hermitian preservation
positive-semidefinite preservation
```

The selected channel family is:

```text
stay -> identity channel
swap -> two-level basis-swap channel
```

The basis swap is an involution. The selected recovery channel is the same identity/swap channel indexed by the accepted update.

The implementation proves exact recovery and exact entropy/QRE preservation for this family.

No claim is made that `FiniteDiagonalChannel` is a formalization of every completely positive trace-preserving map.

## Frozen kernel instance

The quantum kernel contains:

```text
QuantumState: outside | source | target
QuantumUpdate: stay | swap
QuantumCertificate: improvement | stability | malformed
QuantumResidualIndex: typed | packet
```

The two accepted packets are:

```text
source + swap + target + improvement
target + stay + target + stability
```

Residuals test the actual typed transition and actual packet acceptance. Trust, resource, and reality containment are propositions with explicit failing cases.

The checker theorem retains the required form:

```text
check = true -> complete StepObligations
```

## Progress and recovery scope

The source and target spectra are `(1/4, 3/4)` and `(3/4, 1/4)`. Their selected quantum relative entropy is proved equal to `(1/2) * log 3` and strictly positive.

The progress functional is derived from this nonzero gap. The source-to-target swap has strict progress. The target-to-target stay step is accepted and stable.

Recovery is candidate-tied:

```text
stay: identity recovery
swap: involutive swap recovery
```

The concrete trajectory proves strict first-step progress, endpoint recovery, Lyapunov/motion composition, and relevance transport.

## RCLM refinement scope

`RCLM/QuantumBinary.lean` refines substantive architecture state, update, certificate, checker, recovery, and monitor data into the selected RCP quantum kernel.

The refinement also identifies:

```text
architecture state -> selected density
architecture update -> selected forward channel
architecture update -> selected recovery channel
architecture state -> selected entropy
architecture state pair -> selected quantum relative entropy
```

Checker acceptance returns both complete RCLM obligations and complete forgotten RCP obligations, together with density evidence and selected channel/recovery laws.

## Infinite-horizon boundary

The abstract Gate A conditional infinite theorem remains applicable only under explicit successor availability. The selected Gate C implementation does not infer availability, generator completeness, or indefinitely strict improvement from checker soundness.

The concrete trajectory proves one strict improvement followed by stable continuation. It is not an indefinitely strict RSI theorem.

## Audit boundary

The dedicated audit file is:

```text
docs/formal_core_v2/audit/GateCAxiomAudit.lean
```

The pinned workflow builds the complete project, scans the Lean source for admitted proofs and local axioms, evaluates the Gate C `#print axioms` surface, rejects `sorryAx`, and uploads the complete audit record.

## Open extensions

The following remain future formalization work rather than hidden assumptions of the selected closure:

```text
arbitrary noncommuting density matrices
general matrix logarithm and noncommuting QRE
general CPTP channels
general quantum data processing
trace-distance recovery laws
Petz or approximate recovery
infinite-dimensional operator algebras
exact full Paper I/Paper II quantum semantic identity
arbitrary learned-system RCLM refinement
executable checker/generator refinement
empirical RSI or benchmark validation
```
