# Executable Core v2 — Phase 4 adversarial and tamper rejection

## Purpose

Phase 4 attacks the deterministic Phase 3 checker before any generator is allowed
to rely on it. The phase does not add proposal intelligence. It expands the trusted
boundary only by demonstrating that malformed, replayed, tampered, numerically
invalid, unsupported, or provenance-violating inputs remain nonaccepting.

The attack runner is deterministic, model-free, network-free, and independent of a
generator. Every attack is executed twice and its two structured observations are
hashed. A case passes only when:

```text
observed verdict is the declared reject or indeterminate result
required stable reason codes are present
the same attack produces byte-equivalent structured observations twice
no attack produces accept
```

## Hardened checker envelope

Phase 4 composes the Phase 3 mathematical checker with a pure package-integrity
layer. The hardened request contains:

```text
Phase 3 canonical checker request
predecessor package manifest
candidate package manifest
measured predecessor file records
measured candidate file records
pinned Phase 3 checker-manifest hash
transition-binding hash
```

The integrity layer recomputes:

```text
predecessor semantic-tree hash
candidate semantic-tree hash
candidate parent package ID
candidate parent manifest hash
candidate record hash
certificate packet hash
checker-policy hash
Lean-verifier-policy hash
trust-anchor hash
resource-record hash
claim-boundary hash
checker-manifest hash
transition binding to predecessor, candidate, certificate, evaluation, and Lean report
```

A mismatch is fail-closed. Parent-link failures receive `PARENT_LINK_MISMATCH`;
hash substitution receives `HASH_MISMATCH`; checker-manifest or transition-binding
drift also receives `PROVENANCE_FAILED`.

## First-class attack records

Every attack produces `runtime.phase4_attack_case_result.v2` with:

```text
case ID
attack class
expected verdict and reason-code subset
observed verdict and reason codes
first and second observation hashes
deterministic replay result
pass/fail result
case-specific evidence
```

The complete suite is recorded as `runtime.phase4_attack_suite_report.v2`. The
report is canonical JSON and has a content hash derived from all individual results.

## Frozen attack surface

The initial suite records at least the following attacks:

```text
malformed schema
unknown schema version
missing evidence
parent-hash substitution
certificate replay against another predecessor
tampered candidate file record
tampered checker manifest
NaN
infinity
negative probability
non-normalized probability
unsupported QRE support
wrong diagonal-matrix dimension
non-diagonal dense export under the selected Gate C scope
unsupported quantum channel
forged recovery witness
forged strict-progress witness
insufficient certified numerical margin
resource-budget overflow
trust-anchor replacement
manual-repair marker
hidden-oracle marker
generated Lean source containing sorry
generated Lean source containing sorryAx
generated Lean source containing admit
generated Lean source declaring a local axiom
invalid UTF-8 generated Lean source
```

The minimum clean suite count is 27 cases.

## Numerical attacks

Native JSON floating-point syntax is not part of the authoritative runtime profile.
`NaN`, positive or negative infinity, and ordinary native JSON floats are rejected by
the strict canonical parser.

Probability vectors remain exact reduced rationals. Negative masses and vectors whose
exact sum differs from one are rejected during record construction. Diagonal QRE is
computed only when support is valid. A positive source coordinate paired with a zero
target coordinate is an unsupported finite-QRE packet and is rejected.

Strict progress is accepted only when the certified lower endpoint is greater than
zero. An interval overlapping zero is recorded as `indeterminate`; it is never rounded
toward acceptance.

## Selected Gate C attacks

The authoritative Gate C runtime remains the two-entry exact spectrum. The suite
rejects:

```text
dimension other than two
non-diagonal dense matrix export
channel kind other than identity or basis swap
unsupported QRE support
forged recovery evidence
```

No arbitrary noncommuting density matrix, general CPTP map, matrix logarithm, data
processing theorem, or Petz recovery behavior is introduced by this phase.

## Lean source attacks

The Phase 2 source guard is attacked directly with content-addressed generated-source
records. The suite individually records rejection of:

```text
sorry
sorryAx
admit
project-local axiom
invalid UTF-8
```

The source guard runs before any Lean compiler process. These tests supplement, but
do not replace, the pinned Lean conformance workflow.

## Invocation

From the repository root:

```bash
python -m pip install --no-deps -e python/rcp_rclm_runtime_v2
python python/rcp_rclm_runtime_v2/tools/run_phase4_tests.py \
  --package-root python/rcp_rclm_runtime_v2 \
  --out phase_4_unit.log
python python/rcp_rclm_runtime_v2/tools/run_phase4_adversarial.py \
  --out phase_4_adversarial.json
```

The hardened checker CLI is:

```bash
python scripts/check_hardened_candidate.py request.json \
  --out hardened_checker_report.json
```

## Claim boundary

A clean Phase 4 closure licenses work on the deterministic bounded reference
generator. It does not make a generator trusted, does not license candidate promotion,
and does not implement selection, realization, rollback, independent replay,
PyTorch, external benchmarks, general noncommuting quantum semantics, or autonomous
unbounded RSI.
