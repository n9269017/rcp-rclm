# Phase 10B — learned compact-model execution and certified language capability

## Status

Phase 10B implements the learned execution and language-capability layer over the
validated Phase 10A package substrate.  It is intentionally narrower than a general
transformer inference engine: the authoritative reference uses one exact sparse
execution profile inside the frozen 13.2-million-parameter decoder package.

This slice establishes:

- nontrivial canonical model weights in the selected compact transformer package;
- an isolated untrusted PyTorch CPU training/export worker;
- host-exact recomputation of every accepted learned tensor byte;
- deterministic integer next-token inference and fixed greedy decoding;
- protected Lean theorem-completion retention;
- one new held-out Lean theorem completion checked by pinned Lean;
- exact finite token distributions and certified entropy/KL/diagonal-QRE intervals;
- an accepting Phase 9 learned transition with exact frontier expansion.

It does not yet establish Phase 6 realization, atomic Phase 7 promotion, or independent
replay after the training worker is removed.  Those remain the final Phase 10 boundary.

## Selected sparse execution profile

The full package remains:

```text
architecture:       rclm-compact-decoder-13m-v1
model family:       compact_decoder_only_transformer_v1
base parameters:    13,195,840
storage:            little-endian signed int16
scale:              1/4096
```

The selected authoritative execution profile is:

```text
sparse_last_token_transition_v1
```

Its package constraints are fail-closed:

- the token embedding contains a canonical identity subspace for all 260 tokens;
- every selected RMSNorm vector is canonical unit raw value `4096`;
- the first block value projection contains the selected identity map;
- the first block output projection contains the learned byte-token transition table;
- every tensor not named by the profile is byte-exact zero;
- no adapter is active;
- every tensor shape, byte length, raw hash, tree hash, and model identity remains bound
  by the Phase 10A package manifest.

The authoritative evaluator reads the canonical first-block output tensor directly and
interprets each selected raw transition value through the frozen exact divisor `2048`.
It does not import PyTorch, consume native floating-point logits, or trust a candidate
score.  This is a selected sparse reduction of the compact architecture, not a claim of
general equivalence to arbitrary native-float transformer execution.

## Learned predecessor and successor

The protected learned predecessor contains the exact transition chain:

```text
R → r → f → l → <eos>
```

and therefore generates:

```text
rfl
```

for the protected Lean task.

The successor retains that chain and learns:

```text
O → o → m → e → g → a → <eos>
```

and therefore generates:

```text
omega
```

for the held-out task.  The candidate changes the canonical model and tensor-manifest
hashes while leaving the protected transition columns byte exact.

## Untrusted training boundary

The worker is a separate script under `tools/` and is launched through:

```text
python -I -B worker.py
```

with:

```text
device:              CPU
dtype:               float64
threads:             1
seed:                1729
optimizer:           SGD
optimizer steps:     1
learning rate:       1
momentum:            0
weight decay:        0
network input:       none
held-out task IDs:   absent
held-out prompts:    absent
held-out answers:    absent
```

The worker receives only a canonical request and one predecessor tensor.  It emits one
candidate tensor and one untrusted report.  The host:

1. scans the worker source against the frozen import/call policy;
2. validates every request and output field;
3. recomputes the expected candidate bytes independently with integer arithmetic;
4. requires byte equality with the worker output;
5. runs the worker twice in fresh directories and requires identical outputs.

PyTorch is therefore evidence that the selected candidate is reachable through a
learned SGD update.  It is not an acceptance authority.

## Deterministic decoding

For current token `x`, the evaluator reads all 260 signed integer transition scores,
clips only to the frozen dyadic-distribution bound, and selects:

```text
argmax score, with the lowest token identifier winning exact ties
```

Decoding stops on `<eos>` and is bounded to 16 generated tokens.  Every step records the
current token, selected token, selected score, runner-up score, exact margin, and a hash
of the complete exact distribution.

The selected model distribution is:

```text
mass_i = 2^(score_i - min_score)
p_i    = mass_i / Σ_j mass_j
```

so every probability is a strictly positive exact rational.  The learned target score
is `12`, yielding target mass `4096` against mass `1` for each other token.

## Lean capability frontier

The protected task is:

```lean
import Mathlib

example : (7 : Nat) = 7 := by
  rfl
```

The held-out task is:

```lean
import Mathlib

example (a b : Nat) (h : a + 2 <= b) : a < b := by
  omega
```

Before candidate freeze, neither the training request nor the worker contains the
held-out task identifier, prompt, source, or reference completion.  After candidate
freeze, the independent evaluator decodes the completion, applies the strict
`rfl|omega` completion grammar, constructs the complete source, rejects forbidden proof
tokens, and invokes pinned Lean.

The reference frontier is therefore:

```text
F(predecessor) = { lean.phase10.protected.reflexive_seven }

F(candidate) = {
  lean.phase10.protected.reflexive_seven,
  lean.phase10.heldout.linear_gap
}
```

with exact retention and a nonempty held-out set difference.

## Information evidence

For each teacher-forced completion position, the checker constructs the exact finite
token distribution and the corresponding diagonal density.  It independently computes
outward-certified intervals for:

```text
Shannon entropy
von Neumann entropy of the diagonal density
KL divergence to the strictly positive target distribution
diagonal quantum relative entropy
```

The selected diagonal identities are:

```text
S(diag(p)) = H(p)
D_Q^diag(diag(p) || diag(q)) = D_KL(p || q)
```

Formal Core v3 records these selected identifications in
`Learned/Phase10Information.lean`.  Runtime arithmetic uses exact rationals and the
existing certified logarithm interval backend.

The candidate leaves the protected distribution unchanged, so the protected KL/QRE
regression interval is exactly zero.  On the held-out task, the predecessor is uniform
at every target step while the candidate equals the frozen target distribution; the
lower endpoint of predecessor-minus-candidate KL/QRE is strictly positive.

## Gate D / Phase 9 refinement

The concrete predecessor and candidate packages are mapped into the frozen Phase 9
records.  The exact changed component set is:

```text
adapter_manifest
data_curriculum
model_weights
optimizer_policy
```

The adapter manifest changes only because it is rebound to the new base tensor-tree
hash; no adapter is active.  The Phase 9 validator independently checks the update set,
model identities, held-out partition, current-model task certifications, complete
frontier retention, strict frontier expansion, and active generator/planner/protocol
bindings.

This establishes one learned Gate D executable transition at the selected task and model
scope.  It does not establish generic successor availability or recursive use of a
promoted generator.

## Remaining Phase 10 boundary

Phase 10 remains open until one exact head additionally demonstrates:

- Phase 6 realization of the learned tensor and manifest changes;
- byte-exact rollback restoration;
- the inherited pinned-Lean and hardened-checker stability obligations;
- atomic Phase 7 promotion;
- independent replay with the training worker physically absent and zero training
  invocations.
