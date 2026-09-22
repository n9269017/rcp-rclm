# Phase 15 — Dynamic Hidden Challenges and Quantized Autoregressive Planning

Phase 15 begins from the exact certified Phase 14 `M8` package and tests a materially broader learned-entry boundary without changing the external verifier, post-freeze evaluator, immutable store, rollback authority, or promotion authority.

## Selected substrate extension

The candidate package installs a package-bound quantized autoregressive plan decoder under:

```text
model/phase15_planner/
```

The selected reference profile is:

```text
vocabulary:             32 typed plan tokens
feature dimension:      1024
parameter count:        32,768
canonical storage:      little-endian int16
maximum plan length:    16 tokens
inference arithmetic:   exact integer sums
selection:              greedy, lowest-token tie break
training:               deterministic integer multiclass perceptron
training epochs:        24
```

The extension does not replace or mutate the inherited 13.2-million-parameter Phase 10 compact-transformer tensors or the promoted Phase 12/14 adapter package. It is an isolated planner extension bound to the complete active `M8` package context: model identity, adapters, memory, retrieval, generator, planner, optimizer, and tool policy.

This selected decoder is not claimed to be a full dense transformer execution engine or an LLM-scale model. It establishes bounded multi-token autoregressive execution and cross-domain compositional generalization inside the proof-carrying package boundary. GPU training is not authoritative in this phase; the reference worker is CPU-only and exports deterministic canonical bytes.

## Public curriculum and private challenge boundary

The isolated untrusted training worker receives only public curriculum examples. Public examples occupy the even-parameter-sum partition and contain no held-out task identifier, prompt, private parameter, reference answer, successful route, or candidate identity.

Two complete candidate packages are trained, built, and frozen before the independent challenge authority derives any private task parameters. The private challenge seed binds:

```text
Phase 15 source head
certified Phase 14 bundle identity
both candidate freeze hashes
external challenge seed
```

The generated tasks occupy the disjoint odd-parameter-sum partition. The challenge manifest exposes commitments and verifier specifications before evaluation; the private answer store remains separate and is available only after freeze.

## Two verifier-backed domains

### Multi-step Lean construction

The decoder must emit a seven-token plan for a dynamically parameterized finite order theorem. The plan is interpreted into a multi-step Lean proof, scanned for forbidden proof placeholders, and checked by the pinned Lean project.

### Integer-program synthesis

The decoder must emit a seven-token affine-program plan. The independent evaluator executes the synthesized program exhaustively on every integer in `[-16, 16]` and separately checks a generated Lean witness for its symbolic affine specification.

No external benchmark score authorizes promotion.

## Admission conditions

A new task enters the capability frontier only when all of the following are independently retained:

```text
challenge generated after both candidate freezes
challenge absent from training and candidate-building inputs
certified M8 predecessor fails the task
candidate passes the task
candidate-controlled memory contains no answer
all eleven M8 frontier tasks are recertified
odd-partition novelty criterion passes
multi-token/nontriviality criterion passes
independent exhaustive and/or pinned-Lean verifier accepts
```

## Selected trajectory

The reference campaign evaluates two fully frozen candidates:

```text
attempt 0  lean-only curriculum       reject: integer-program task unsolved
attempt 1  multidomain curriculum     accept and promote M8 → M9
```

The rejected candidate leaves the active package pointer unchanged. The accepted candidate expands the capability frontier from 11 to 13 tasks and expands the recursive-productivity frontier with post-freeze challenge binding, multi-token plan generation, and package-bound tool invocation.

## Claim boundary

Phase 15 establishes one finite, selected, dynamically generated, two-domain `M8 → M9` learned successor under the existing external fail-closed constitution. It does not establish arbitrary hidden-task competence, a general transformer execution theorem, deterministic GPU training, generic accepted-candidate existence, full Gate E closure, open-horizon continuation, asynchronous operation, general noncommuting semantics, or empirically unbounded RSI.
