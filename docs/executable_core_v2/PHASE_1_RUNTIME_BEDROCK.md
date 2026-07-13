# Phase 1 — Runtime bedrock

## Status

Phase 1 implements the deterministic data, arithmetic, serialization, hashing, and
selected-reference mathematics required before a production checker or Lean bridge
can be constructed.

The implementation lives at:

```text
python/rcp_rclm_runtime_v2/
```

## Formal and contract pins

```text
Runtime contract: rcp-rclm-runtime-contract-v2.0.0
Formal source:    012de4a55f326107f53f0e215c8aec62859d0bbf
Lean:             leanprover/lean4:v4.31.0
mathlib:          fabf563a7c95a166b8d7b6efca11c8b4dc9d911f
```

No Python result is declared a theorem refinement merely because it is implemented
in this package. The package provides the deterministic objects that later
Python/Lean conformance tests and the fail-closed checker will consume.

## Implemented package boundary

```text
rcp_rclm_runtime/
  schema/
    state.py
    update.py
    candidate.py
    certificate.py
    package.py
    verdict.py

  canonical/
    json.py
    hashing.py
    paths.py

  mathematics/
    rational.py
    intervals.py
    classical.py
    diagonal_quantum.py

  refinement/
    mapping.py
    theorem_surface.py

  lean_bridge/
    source_guard.py
```

The later checker, compiler bridge, generator, selector, realizer, promotion,
rollback, replay, and PyTorch modules are intentionally absent rather than present
as empty scaffolding.

## Exact rational layer

`Rational` stores normalized numerator and denominator integers and enforces:

```text
denominator > 0
reduced fraction
zero encoded as 0/1
no native-float conversion
```

Distribution normalization, traces, selected permutation channels, and exact
recovery operations are computed only with this exact representation.

## Certified logarithm intervals

The first numeric backend is:

```text
rcp-rclm-rational-atanh-log-v1
```

For a positive rational `x`, the implementation computes an exact power-of-two
range reduction:

```text
x = 2^k m
1 <= m < 2
```

It then uses the identity:

```text
log(m) = 2 * sum_{j >= 0} z^(2j+1)/(2j+1)
z = (m - 1)/(m + 1)
0 <= z <= 1/3
```

For a partial sum through index `N - 1`, the omitted tail is bounded exactly by:

```text
z^(2N+1) / ((2N+1) * (1 - z^2))
```

All series terms and tail bounds are rational. The returned endpoints therefore
form an independently inspectable outward enclosure. The implementation allocates
the requested width budget across `log(m)` and `k log(2)` and verifies the final
interval width before returning.

The accepted precision range is 128 through 4096 bits, with the contract schedule:

```text
256 -> 512 -> 1024 -> 2048 -> 4096
```

Adaptive acceptance decisions remain part of the later checker phase. Phase 1 only
provides deterministic enclosures and boundary predicates.

## Gate B selected runtime mathematics

Phase 1 implements:

```text
finite exact-rational distributions
exact structural support
Shannon entropy interval
support-aware KL interval
zero-coordinate conservative extension
exact zero-extension recovery
selected binary state and update transition functions
```

A zero source mass contributes exactly zero. A positive source mass with a zero
target mass is rejected before logarithm evaluation.

## Gate C selected runtime mathematics

Phase 1 implements only the completed two-level commuting/diagonal reference:

```text
spectrum-backed diagonal density records
exact derived complex diagonal matrix
exact trace/Hermitian/PSD evidence from construction
spectral von Neumann entropy
support-aware diagonal QRE
identity permutation channel
basis-swap permutation channel
inverse selected recovery
source/target state-density mapping
```

The probability spectrum is authoritative. An exported dense matrix is accepted
only when it equals the exactly re-derived diagonal matrix entry by entry. Nonzero
off-diagonal entries are rejected.

This phase does not implement arbitrary noncommuting density matrices, general
CPTP maps, matrix logarithms, general quantum data processing, or Petz recovery.

## Canonical bytes and hashes

The implementation follows `RCPRCLM-CJSON-V2`:

```text
UTF-8 without BOM
Unicode NFC
sorted object keys
no insignificant whitespace
no native JSON floats
strict duplicate-key rejection
```

It also implements:

```text
semantic POSIX path validation
0644/0755 file modes
raw file SHA-256
RCPRCLM-CANONICAL-JSON-V2 domain-separated object hashes
RCPRCLM-TREE-V2 domain-separated tree hashes
symlink and hard-link alias rejection during tree scans
```

Cross-platform conformance vectors freeze hashes for a distribution, quantum
candidate, logarithm interval, entropy interval, KL interval, and sample tree.

## RCLM refinement bedrock

The immutable RCLM records preserve all declared state, update, and certificate
registers. Forgetful functions map:

```text
RCLM state       -> RCP core state
RCLM update      -> RCP core update
RCLM certificate -> RCP core certificate artifact
RCLM candidate   -> RCP candidate
```

Phase 1 can compute content-addressed mapping evidence. The later checker must still
recompute substantive kernel, monitor, checker-acceptance, trust, resource, and
containment obligations.

## Generated Lean source guard

Before any later compiler invocation, `lean_bridge/source_guard.py` scans raw UTF-8
source and rejects:

```text
sorry
sorryAx
admit
project-local axiom declarations
```

The source guard is not a compiler and a clean report is not a proof. It is the
mandatory inexpensive gate that runs before the future pinned Lean subprocess.

## Explicitly unimplemented

```text
production aggregate successor checker
Lean compiler/verifier bridge
adversarial checker rejection suite
untrusted generator
candidate selector and realizer
package promotion controller
rollback controller
independent replay command
PyTorch proposal backend
external benchmark adapter
```

No executable RSI, learned-system entry, benchmark, or autonomous-improvement claim
is made by Phase 1.
