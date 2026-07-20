# Phase 10A — canonical compact-transformer substrate

## Status

Phase 10 has begun. This first auditable slice freezes and executes the model-package
substrate that the later learned-successor run must use. It does **not** close the full
Phase 10 exit criterion.

The implemented slice provides:

- one fixed 13.2-million-parameter decoder-only transformer architecture;
- one fixed UTF-8 byte tokenizer and 260-token vocabulary;
- exact architecture, tensor, adapter, policy, environment, resource, and package manifests;
- canonical little-endian `int16` tensor files and raw-byte hashes;
- exact Phase 9 `ModelIdentity` correspondence;
- a zero-output LoRA extension with a changed model identity;
- exact structural recovery to the predecessor model identity;
- a Lean theorem for the zero-output LoRA semantics;
- deterministic package construction, validation, mutation rejection, and schema validation.

Still open are actual language-model training, deterministic authoritative inference,
Lean task completion, KL/QRE evidence, promotion, rollback integration, and independent
replay without retraining.

## Selected model

The production substrate is frozen as:

```text
architecture id:     rclm-compact-decoder-13m-v1
model family:        compact_decoder_only_transformer_v1
context length:      512 tokens
vocabulary:          260 tokens
layers:              8
model width:         320
attention heads:     5
head width:          64
MLP hidden width:    1280
normalization:       RMSNorm
attention:           causal scaled dot product
activation:          gated SiLU
position encoding:   rotary_v1
token/output weights:tied
base parameters:     13,195,840
LoRA parameters:     430,080
total with LoRA:     13,625,920
```

The base parameter count is recomputed from the exact tensor graph. The graph contains
one token embedding, one final normalization vector, and for each of eight blocks:

```text
attention normalization
fused QKV projection
attention output projection
MLP normalization
MLP gate projection
MLP up projection
MLP down projection
```

No separate output-head tensor exists because the output head is the transpose of the
token embedding.

## Fixed tokenizer

`rclm-utf8-byte-tokenizer-v1` assigns token identifiers `0` through `255` directly to
byte values and reserves:

```text
256  <pad>
257  <bos>
258  <eos>
259  <sep>
```

The tokenizer therefore represents every valid UTF-8 Lean source string without an
unknown-token path. The package binds both the raw tokenizer bytes and the canonical
vocabulary manifest by SHA-256.

## Canonical tensor package

Every tensor record binds:

```text
semantic tensor name
canonical package path
shape
tensor role
storage dtype
byte order
exact rational quantization scale
element count
byte count
raw-file SHA-256
```

The selected storage form is little-endian signed `int16` with scale `1/4096`.
Floating-point training may later occur only in an untrusted worker. It cannot choose
the canonical accepted bytes, hashes, package identity, or checker verdict.

The reference predecessor materializes the complete 13,195,840-parameter tensor graph
as canonical raw files. These reference values are structural zeros and are not claimed
to be a trained language model.

## Package surface

The reference package contains:

```text
model/architecture.json
model/tokenizer/tokenizer.bin
model/tokenizer/vocabulary.json
model/tokenizer/manifest.json
model/tensors/manifest.json
model/tensors/*.i16le.bin
model/adapters/manifest.json
model/adapters/tensors/*.i16le.bin          when installed
training/training_policy.json
training/optimizer_state.json
training/data_curriculum.json
policies/generator_policy.json
policies/planner_policy.json
policies/tool_policy.json
policies/verification_policy.json
policies/resource_policy.json
retrieval/index_manifest.json
memory/memory_manifest.json
self_model/manifest.json
runtime/rng_state.json
runtime/environment.json
runtime/resource_measurement.json
package_manifest.json
```

`package_manifest.json` binds every component hash, the Phase 9 model identity, the
parameter count, parent package, payload tree hash, and package hash. The payload tree
excludes only the package manifest itself, preventing a self-referential hash.

## Conservative LoRA extension

The selected LoRA target set is:

```text
attn_qkv
attn_output
mlp_gate
mlp_up
mlp_down
```

for every transformer layer, with rank `8` and alpha `8`. For a base projection `W`,
the extension uses the abstract form:

```text
W'(x) = W(x) + B(A(x)).
```

The reference extension installs deterministic nonzero `A` tensors and exact-zero `B`
tensors. Therefore the installed adapter is nonempty while its functional contribution
is exactly zero.

Formal Core v3 now supplies:

```text
recover_adapter_extension_exact
lora_zero_output_preserves
lora_zero_output_preserves_function
```

The Python checker independently verifies the executable preconditions:

- architecture unchanged;
- base tensor manifest and tree unchanged;
- tokenizer unchanged;
- policy and support manifests unchanged;
- the complete expected LoRA graph is present;
- at least one `A` entry is nonzero;
- every `B` entry is byte-exact zero;
- the extended model identity differs;
- dropping the adapter reconstructs the predecessor model identity exactly.

This establishes the conservative-extension substrate. It is not itself an accepted
Gate D frontier-expanding successor because it intentionally adds no task capability.

## Reference result

The deterministic reference construction produces:

```text
predecessor parameters:       13,195,840
zero-LoRA parameters:            430,080
extended parameters:          13,625,920
predecessor files:                     79
extended files:                      159
predecessor package validation:   accept
extended package validation:      accept
conservative-extension verdict:   accept
```

The reference packages are generated during validation and are not committed as model
binaries.

## Trust boundary

Authoritative in this slice:

```text
canonical JSON and hashing
fixed architecture and tokenizer definitions
raw tensor shape/size/hash validation
package file-set and tree validation
Phase 9 model-identity reconstruction
zero-output adapter validation
Lean zero-output and recovery theorems
```

Not authoritative or not yet implemented:

```text
training loss or optimizer reports
learned model output claims
candidate-provided task success
floating-point logits
language-model decoding
KL/QRE evidence
promotion or replay claims
```

## Next Phase 10 slice

The next implementation boundary is deterministic model execution and task evaluation:

1. implement the untrusted PyTorch training/export worker for this exact graph;
2. implement deterministic CPU decoding over canonical exported tensors;
3. freeze Lean theorem-completion prompt and output grammars;
4. independently execute generated completions with pinned Lean;
5. produce selected output-distribution and KL/QRE evidence;
6. feed the resulting candidate through realization, rollback, Gate D admission,
   promotion, and generator-free replay.
