# Executable Core v2 — Phase 5A deterministic reference generator

## Purpose

Phase 5A is the first executable generator stage. It does not attempt intelligence,
search, learning, or self-modification. It implements the finite bounded grammar
already represented by the compiled Lean `ClassicalBinarySeedLibrary` and demonstrates
the following executable chain:

```text
immutable predecessor package
→ separate untrusted generator process
→ bounded proposal word
→ certificate construction outside the generator
→ typed update selection outside the generator
→ successor realization by applying the selected update
→ direct pinned-Lean grammar conformance
→ generated Lean candidate certificate and source guard
→ pinned Lean RCP/RCLM verdict
→ Phase 4 hardened checker verdict
```

The generator never decides whether its own proposal is accepted.

## Exact formal scope

The Lean bounded seed library currently provides this concrete grammar:

```text
seed domain:                 classical initial or target state
witness library:             strictImprovement, stableContinuation
active grammar at initial:   improve
active grammar at target:    stabilize
rejected word:               absent from every active grammar
maximum update-word depth:   1
maximum proof-word length:   1
```

The executable spelling is:

```text
initial  → word improve   → witness strict_improvement
                           → proposal improve

target   → word stabilize → witness stable_continuation
                           → proposal stabilize
```

The live Phase 5A Lean job compiles a generated conformance file that checks the
initial and target packet words, depth and proof bounds, witness and proposal maps,
certificate and candidate maps, active grammar membership, and rejection of the
inactive `rejected` word.

The selected Gate C mathematics and checker remain available, but the formal project
does not currently contain an equivalent Gate C bounded seed-library grammar.
Consequently, Phase 5A implements the declared Gate B classical grammar only. It does
not silently invent a quantum generator theorem.

## Read-only generator input

The worker receives one canonical JSON object on standard input containing exactly:

```text
predecessor package
public generator policy
declared task/objective
resource budget
```

The request schema has no fields for:

```text
checker source
trust anchor
previous-manifest history
promotion ledger
reference answers
candidate certificate
candidate successor
checker verdict
promotion decision
```

Unknown fields are rejected. The worker output is an untrusted proposal word plus
binding hashes. It contains no certificate packet, selected update, successor state,
Lean result, checker result, or `accepted` Boolean.

## Separate-process boundary

The orchestrator starts the worker as a separate Python process with:

```text
isolated interpreter mode
bytecode writes disabled
a fresh temporary working directory
a minimal environment
canonical request bytes only on stdin
stdout and stderr captured
fixed timeout
```

Package initialization is lazy so starting `rcp_rclm_runtime.generator.worker` does not
load any checker module. The worker checks that no `rcp_rclm_runtime.checker` module is
present before interpreting the request.

The worker necessarily loads its fixed generator, schema, canonicalization, and
mathematics modules during Python startup. After startup and after reading the bounded
stdin payload, it installs a Python audit hook before parsing or interpreting the
request. The hook rejects all later filesystem opens, filesystem mutations, process
creation, and socket events. Thus the active proposal computation has no filesystem,
network, subprocess, checker-module, or control-plane data path.

The worker also emits structured sandbox evidence showing that checker input, trust
anchors, manifest history, the promotion ledger, and reference-answer objects were not
part of its request.

The audit hook is a deterministic application-level boundary, not a claim of complete
operating-system sandboxing against malicious native extensions. The Phase 6 realizer
and Phase 7 controller must add the stronger OS-level mount, process, and resource
boundary before an open-ended generator is admitted.

## Deterministic replay

Every Phase 5A invocation is executed twice in fresh temporary directories. The replay
passes only when both executions have identical:

```text
canonical stdout SHA-256
structured status
ordered reason-code sequence
parsed response hash
```

A mismatch returns `GENERATOR_REPLAY_MISMATCH` and remains nonaccepting.

The generator uses no clock, RNG, network request, model, optimizer, native
floating-point computation, or mutable global search state.

## Proposal binding

The proposal binds to:

```text
predecessor package ID
predecessor manifest hash
generator policy hash
objective hash
resource-budget hash
complete generator-input hash
worker implementation version
```

The proposal grammar is validated independently after the worker exits. The
orchestrator does not trust the worker merely because it produced a parseable record.

## Certificate construction

Certificate construction occurs after proposal generation and outside the worker:

```text
improve   → canonical Gate B improvement certificate
stabilize → canonical Gate B stability certificate
```

The resulting packet is content-hashed. No proposal-supplied preservation,
containment, recovery, progress, or acceptance declaration is consumed as evidence.

## Selection and realization

Selection decodes the proposal into a typed core update:

```text
improve   → ClassicalBinaryUpdate.improve
stabilize → ClassicalBinaryUpdate.stay
```

Realization computes the successor from the immutable predecessor and selected update:

```text
successor = apply_binary_update(predecessor, selected_update)
```

It does not copy a successor field from generator output. The RCLM candidate is then
formed from the canonical lifted update and the computed canonical successor.

## Lean and checker boundary

The pinned workflow first compiles direct Lean assertions for the exact bounded seed
grammar. The realized candidate and independently constructed certificate are then
converted into the existing restricted Lean reference packet. Before either generated
Lean source is compiled, the Phase 2 source guard rejects:

```text
sorry
sorryAx
admit
project-local axiom declarations
invalid UTF-8
```

The pinned Lean bridge must return agreeing RCP and RCLM acceptance. The Phase 4
hardened checker then recomputes the mathematical obligations and package-integrity
bindings. The pipeline accepts only when direct grammar conformance, candidate Lean
verification, and the hardened checker all accept.

## Structured evidence

The pipeline retains structured records for:

```text
generator input
both separate-process observations
untrusted proposal
certificate construction
selection
realization
direct bounded-grammar Lean source and source-guard report
direct bounded-grammar Lean compilation
generated candidate Lean source and source-guard report
candidate Lean compilation and machine-readable verdict
hardened checker report
content hashes linking every stage
```

The final Boolean is derived from the structured pipeline verdict.

## Invocation

Run only the separate proposal worker through the command-line interface:

```bash
python -m pip install --no-deps -e python/rcp_rclm_runtime_v2
python scripts/generate_candidate.py generator_input.json \
  --out generator_replay.json
```

Run the complete pinned reference pipeline from the repository root:

```bash
python python/rcp_rclm_runtime_v2/tools/run_phase5_reference_pipeline.py \
  --repo-root . \
  --outdir artifacts/runtime_v2_phase_5/local
```

## Claim boundary

A clean Phase 5A result establishes a deterministic executable instance of the finite
classical bounded seed grammar through the already validated Lean and checker layers.
It does not establish:

```text
generator intelligence or useful novelty
unbounded grammar or proof-search completeness
Gate C bounded generator refinement
generator trust
candidate promotion
production selector/realizer filesystem isolation
independent replay without the generator
LLM, program-synthesis, search, or PyTorch proposal correctness
arbitrary learned-system entry
autonomous or unbounded RSI
```
