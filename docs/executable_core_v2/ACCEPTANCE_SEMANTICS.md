# Acceptance semantics

## Verdict domain

The runtime checker returns exactly one semantic verdict:

```text
accept
reject
indeterminate
```

Only `accept` authorizes promotion.

`reject` means that at least one required condition is false or an input is
malformed, unsupported, tampered, or inconsistent.

`indeterminate` means that the required truth value could not be certified within
the declared deterministic resource or precision limits. It is fail-closed and is
not promotion-equivalent to acceptance.

## Required acceptance conjunction

For predecessor state `M`, candidate `u/next`, and certificate packet `c`, promotion
requires all of the following to be recomputed and accepted.

### A. Schema and canonical form

```text
known contract version
known schema identifiers
no unknown or duplicate fields
canonical number encodings
canonical JSON bytes
canonical paths
all referenced content present
```

### B. Package integrity

```text
candidate content hash valid
certificate packet hash valid
semantic tree hash valid
parent package ID valid
parent manifest hash valid
trust-anchor hash unchanged
checker-policy hash valid
Lean-verifier-policy hash valid
```

### C. Scope and type validity

```text
state belongs to a supported Gate B or selected Gate C domain
update belongs to the declared update type
certificate belongs to the declared certificate type
claimed successor belongs to the declared state type
selected quantum data are finite and diagonal
selected channel is identity or basis swap only
```

### D. Typed successor

The checker recomputes:

```text
candidate.next = apply(predecessor, candidate.update)
```

A candidate-provided equality assertion is ignored.

### E. Residual nonpositivity

Every required residual is recomputed. Acceptance requires:

```text
upper(residual_i) <= 0
```

for every residual index.

### F. Protected non-loss

For every protected distinction:

```text
upper(
  protected_before
  - protected_after_transported
  - declared_loss_budget
) <= 0
```

The checker derives transported distinctions and protected values from the
predecessor, candidate, and selected runtime instance.

### G. Constructive recovery

The candidate-tied recovery map is applied to the actual candidate successor.
Acceptance requires:

```text
upper(recovery_error - recovery_budget) <= 0
```

The recovery function is selected by the update type, not by an arbitrary
candidate-supplied callable.

### H. Protected invariant preservation

The successor must satisfy every declared protected invariant. In the selected
references this includes canonical-domain membership and rejection of the declared
outside state.

### I. Progress

Progress nondecrease requires:

```text
lower(progress_next - progress_before) >= 0
```

When the certificate claims a strict witness, strict progress additionally
requires:

```text
lower(progress_next - progress_before) > 0
```

A stability certificate does not create a strict-witness obligation.

### J. Trust, resources, and containment

The checker recomputes:

```text
trust validity
resource authorization
reality or uncertainty containment
successor-domain admissibility
```

No Boolean field supplied by the generator is authoritative.

### K. RCLM-to-RCP refinement consistency

The RCLM state, update, certificate, protected values, residuals, recovery,
progress, trust, resources, containment, and monitors must agree with their
forgotten RCP counterparts according to the selected refinement map.

Any mismatch is rejection.

### L. Monitor obligations

The checker recomputes the selected monitor evidence:

```text
Lyapunov value and motion charge
Lyapunov error budget
unsupported collapse and ambiguity error
relevance value, transport, and relevance error
```

Every required one-step monitor inequality must be certified.

### M. Lean conformance bridge

The pinned Lean bridge must return an accepting verifier report for the same
canonical semantic packet and the report hash must match the package record.

A Python-only accept result is not sufficient during the initial conformance phase.

### N. Provenance and run policy

```text
no manual repair inside the transition
no hidden oracle or answer lookup
resource record independently measured
immutable predecessor used
candidate realized in an isolated workspace
rollback snapshot complete
```

## Evaluation order

The checker evaluates conditions in this order:

```text
1. parse and schema validation
2. canonicalization and hash validation
3. parent and trust-anchor linkage
4. supported-scope validation
5. typed successor
6. residuals
7. protected non-loss
8. constructive recovery
9. invariant and domain preservation
10. progress and strict witness
11. trust, resources, and containment
12. RCLM-to-RCP refinement
13. monitor obligations
14. Lean bridge
15. provenance and promotion preconditions
```

Cheap structural failures precede expensive interval and Lean checks.

## Reason codes

Every nonaccepting verdict includes stable reason codes. The initial reserved set is:

```text
SCHEMA_UNKNOWN
SCHEMA_MALFORMED
CANONICALIZATION_FAILED
HASH_MISMATCH
PARENT_LINK_MISMATCH
TRUST_ANCHOR_CHANGED
UNSUPPORTED_SCOPE
TYPE_MISMATCH
TYPED_SUCCESSOR_FAILED
RESIDUAL_POSITIVE
NONLOSS_FAILED
RECOVERY_FAILED
INVARIANT_FAILED
PROGRESS_REGRESSION
STRICT_WITNESS_FAILED
TRUST_INVALID
RESOURCE_INVALID
CONTAINMENT_FAILED
SUCCESSOR_DOMAIN_FAILED
REFINEMENT_MISMATCH
MONITOR_FAILED
NUMERIC_INDETERMINATE
LEAN_SOURCE_FORBIDDEN_TOKEN
LEAN_VERIFIER_FAILED
PROVENANCE_FAILED
MANUAL_REPAIR_DETECTED
INTERNAL_ERROR
```

Reason-code meaning is versioned. Human-readable text may change without changing
semantics; reason codes may not.

## Candidate assertions

Candidate fields claiming success are never consumed as acceptance evidence. If a
schema permits them for debugging, they are placed in a nonsemantic annotation
section and excluded from all acceptance computations and semantic hashes.

## Failure behavior

The checker must not:

```text
catch an exception and return accept
substitute a default certificate
repair malformed input
normalize an invalid probability vector
round an overlapping interval toward success
skip Lean verification after a timeout
promote on partial evidence
```

Any internal exception produces a semantic nonaccepting verdict and a complete
error record.

## Promotion rule

The promotion controller may activate a candidate only when:

```text
runtime checker verdict = accept
Lean bridge verdict = accept
verdict input hashes equal the candidate package hashes
atomic successor manifest write succeeds
rollback snapshot has been validated
```

The controller has no override flag.
