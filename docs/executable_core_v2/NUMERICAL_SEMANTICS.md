# Numerical semantics

## Purpose

Lean proves statements over exact mathematical objects. Native Python binary
floating-point values are not automatically refinements of those objects. This
profile freezes the first executable interpretation for Gate B and the selected
Gate C reference.

## Exact scalar representation

### Integers

Mathematical integers are serialized as canonical decimal strings:

```text
0
17
-4
```

Rules:

```text
no leading plus sign
no leading zeros except the single string "0"
negative zero is forbidden
ASCII digits only
```

### Rational values

A rational is serialized as:

```json
{
  "numerator": "-3",
  "denominator": "4"
}
```

Required invariants:

```text
denominator > 0
gcd(abs(numerator), denominator) = 1
zero is encoded as 0/1
```

Probability masses, declared budgets, exact trace values, and exact discrete costs
use this representation wherever possible.

## Distribution semantics

A finite distribution is valid only when:

```text
dimension >= 1
number of masses = dimension
every mass is a reduced exact rational
every mass >= 0
exact rational sum of masses = 1
```

There is no normalization tolerance for exact-rational distributions. A candidate
whose masses sum to a value merely close to one is rejected.

## Selected diagonal quantum semantics

The source of truth for a selected Gate C density state is its finite probability
spectrum.

```text
spectrum
→ diagonal complex matrix with real diagonal entries
```

The runtime does not accept a candidate-supplied dense matrix as an independent
source of truth.

The following properties are exact consequences of the validated spectrum and
construction:

```text
trace = exact rational sum = 1
Hermitian = exact diagonal construction with real entries
positive semidefinite = every diagonal mass >= 0
matrix dimension = spectrum dimension
```

If a dense matrix is exported for inspection, the checker re-derives it and rejects
any mismatch or any nonzero off-diagonal entry.

## Selected channel semantics

The first executable channel family is restricted to exact index permutations:

```text
identity
basis_swap for dimension 2
```

A channel record is valid only when its permutation is a bijection over the exact
dimension and matches the selected channel kind. Application is exact reindexing of
the spectrum. The selected recovery channel is the inverse permutation; for
identity and the two-element swap, it equals the forward permutation.

No floating-point matrix multiplication is required for the selected reference.

## Support conventions

For classical KL and selected diagonal QRE:

```text
SupportedBy(p, q) := for every i, p_i > 0 implies q_i > 0
```

This is checked on exact rational masses. It is not a tolerance test.

Terms follow the formal selected definition:

```text
p_i * log(p_i / q_i)
```

A zero source mass contributes exactly zero. A positive source mass with zero target
mass violates support and is rejected before logarithm evaluation.

## Certified interval representation

Every non-rational real result is represented by a closed rational interval:

```json
{
  "lower": {"numerator": "123", "denominator": "1000"},
  "upper": {"numerator": "124", "denominator": "1000"},
  "precision_bits": 256
}
```

Required invariants:

```text
lower <= upper
precision_bits >= 128
endpoints are outward-rounded rational bounds
no NaN
no positive or negative infinity
```

The numerical backend must compute certified enclosures, not point estimates with an
informal epsilon. The implementation may use any backend that returns independently
checkable outward rational bounds and passes the conformance suite.

## Adaptive precision

The initial precision is:

```text
256 bits
```

When an interval overlaps a decision boundary, the checker may double precision:

```text
256 → 512 → 1024 → 2048 → 4096 bits
```

The maximum permitted precision for the initial reference is 4096 bits. If the
verdict is still not separated, the result is `indeterminate`.

## Entropy, KL, and QRE

The runtime functions are:

```text
shannon_entropy_interval(distribution)
von_neumann_entropy_interval(diagonal_density)
kl_divergence_interval(source, target)
quantum_relative_entropy_interval(source, target)
```

At the selected diagonal scope:

```text
von Neumann entropy = Shannon entropy of the spectrum
quantum relative entropy = KL divergence of the spectra
```

The runtime must preserve these identities by using one shared spectral
implementation rather than two unrelated numerical functions.

## Directed decision rules

### Strict progress

A claimed strict witness is accepted only when:

```text
computed_progress_difference.lower > 0
```

The claimed margin is not trusted. The checker recomputes the interval.

### Nondecreasing progress

Progress nondecrease is accepted only when:

```text
computed_progress_difference.lower >= 0
```

An interval with a negative lower endpoint is not accepted even if its midpoint is
positive.

### Protected non-loss

For a required inequality of the form:

```text
protected_before <= protected_after + budget
```

acceptance requires an interval upper bound on the residual:

```text
upper(protected_before - protected_after - budget) <= 0
```

### Recovery

For a required inequality of the form:

```text
recovery_error <= recovery_budget
```

acceptance requires:

```text
upper(recovery_error - recovery_budget) <= 0
```

### Residuals

Every residual must have:

```text
upper(residual) <= 0
```

### Boundary overlap

If an interval overlaps zero or another required boundary after maximum precision,
the verdict is:

```text
indeterminate
```

It is never rounded toward acceptance.

## Native float policy

`float`, `numpy.float32`, `numpy.float64`, `torch.float32`, and GPU reduction output
may be used for untrusted proposal generation or diagnostics. They may not be the
authoritative input to any acceptance predicate.

Any native-float proposal that enters the checker must first be converted into an
exact rational or certified interval record with explicit provenance.

## Determinism

Given identical canonical input bytes and identical numeric-backend version, the
checker must produce identical interval endpoints and verdict bytes on every
supported platform. Backend identity, precision schedule, and rounding mode are
included in the checker report.

## Unsupported numerical claims

The first executable reference does not implement or claim:

```text
arbitrary dense noncommuting density matrices
matrix logarithms
arbitrary CPTP channel evaluation
general quantum data processing
trace-distance recovery
Petz recovery
approximate recovery beyond the declared abstract budget interface
```
