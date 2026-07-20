# RCP/RCLM Runtime v3

This package implements the executable correspondence for Formal Core v3 Gate D, the
selected compact language-model successor lifecycle, and the first active-model proposal
surface.

## Phase 9 contract

The Phase 9 layer provides immutable Python records and deterministic validation for:

- the selected compact decoder-only transformer package identity;
- the selected Lean theorem-completion task class;
- model, tokenizer, training, optimizer, generator, planner, retrieval, memory, tool,
  verification, resource, and self-model bindings;
- finite certified capability frontiers and task ledgers;
- typed substantive update operations;
- held-out task and reference-answer isolation;
- learned certificate evidence hashes;
- active-generator and proposal-protocol bindings;
- exact frontier retention and strict expansion.

## Phase 10A substrate

`rcp_rclm_runtime_v3.phase10` defines the canonical model substrate:

```text
fixed 13.2M decoder-only transformer architecture
fixed 260-token UTF-8 byte tokenizer
canonical little-endian int16 tensors and raw-file hashes
complete model, policy, data, optimizer, RNG, and environment manifests
Phase 9 ModelIdentity reconstruction
rank-8 zero-output LoRA extension
exact recovery to the predecessor identity
fail-closed package and extension validation
```

## Phase 10B learned execution

The learned reference adds one deliberately narrow but genuine formal-language execution
profile:

```text
nontrivial sparse compact-model weights
isolated untrusted PyTorch CPU SGD worker
host-exact candidate tensor recomputation
integer deterministic decoding
exact dyadic token distributions
protected Lean task retention
new held-out Lean task certification
entropy/KL/diagonal-QRE interval evidence
accepting Phase 9 learned frontier transition
```

The trusted package imports no PyTorch, NumPy, random-number backend, or native
floating-point acceptance source. PyTorch is used only by the isolated worker under
`tools/`; every accepted tensor byte is independently recomputed by the host.

## Full Phase 10 lifecycle closure

The selected learned successor is realized and closed through the inherited Runtime v2
trust boundary:

```text
Phase 6 isolated realization
canonical rollback archive and byte-exact restoration
pinned Lean task verification
hardened Gate B checker
complete Gate D / Phase 9 transition validation
Phase 7 atomic content-addressed promotion
physical removal of the training worker and entry points
independent replay with training, generator, and planner invocations equal to zero
```

`phase_10_closure_manifest.json` separates two kinds of evidence:

- `stable_reference_hashes` are recomputed identically on Linux, Windows, and macOS;
- `code_proof.exact_runtime_hashes` retain environment-bound Phase 6 and lifecycle hashes
  from the exact successful pinned code-proof run.

This distinction prevents operating-system identity from being mistaken for a semantic
model difference while preserving the complete exact-run evidence.

## Phase 11A active-model typed proposal

`rcp_rclm_runtime_v3.phase11` begins the autonomous generator program with a bounded
selected profile:

```text
host-installed active generator/planner bootstrap
bootstrap excluded from autonomous-improvement counting
canonical typed mutation-program grammar
fixed per-run wall-clock, accelerator, step, byte, candidate, and evaluation budgets
active predecessor model emits proposal bytes
first proposal rejected for budget and immutable-policy violations
fresh second model invocation bound to the rejection report
second typed program validates under the original budget
held-out material consumed = false
manual repair count = 0
```

The active package retains the Phase 10 `rfl` and `omega` capabilities exactly. Generator,
planner, model, package, state, proposal-protocol, invocation, validation, and budget hashes
are canonical and included in the retained evidence.

Phase 11A does not realize or promote the validated program. Model-generated candidate
rejection, accepted promotion, and installation of changed successor generator/planner
bytes remain Phase 11B.

## Build and test

Install Runtime v2 and Runtime v3:

```bash
python -m pip install --no-deps -e python/rcp_rclm_runtime_v2
python -m pip install -e "python/rcp_rclm_runtime_v3[test]"
```

Install the optional training dependency only for the untrusted Phase 10 training job:

```bash
python -m pip install -e "python/rcp_rclm_runtime_v3[phase10-train]"
```

Run the focused suites and retained-reference validators:

```bash
python python/rcp_rclm_runtime_v3/tools/run_phase9_tests.py \
  --package-root python/rcp_rclm_runtime_v3 \
  --out artifacts/runtime_v3_phase_9/tests.log

python python/rcp_rclm_runtime_v3/tools/run_phase10_tests.py \
  --package-root python/rcp_rclm_runtime_v3 \
  --out artifacts/runtime_v3_phase_10/tests.log

python python/rcp_rclm_runtime_v3/tools/run_phase11_tests.py \
  --package-root python/rcp_rclm_runtime_v3 \
  --out artifacts/runtime_v3_phase_11/tests.log

python python/rcp_rclm_runtime_v3/tools/validate_phase10_closure_manifest.py \
  --repo-root . \
  --out artifacts/runtime_v3_phase_10/closure_manifest.json

python python/rcp_rclm_runtime_v3/tools/validate_phase11_manifest.py \
  --repo-root . \
  --out artifacts/runtime_v3_phase_11/manifest.json

python python/rcp_rclm_runtime_v3/tools/run_phase11_reference.py \
  --out artifacts/runtime_v3_phase_11/reference.json
```

The authoritative Phase 10 promotion and worker-free replay command additionally requires
the pinned Lean toolchain and built Formal Core v2/v3 projects:

```bash
python python/rcp_rclm_runtime_v3/tools/run_phase10_closure.py \
  --repo-root . \
  --lean-project-root lean/rcp_rclm_formal_core_v3 \
  --out artifacts/runtime_v3_phase_10/phase_10_closure.json
```

## Claim boundary

Phase 10 remains complete at its declared selected scope. Phase 11A additionally establishes
active-model typed proposal generation, immutable rejection, and a fresh validated program.
It does not yet establish a promoted model-generated candidate, installed modified successor
generator/planner bytes, recursive use of that modified generator, generic successor
availability, or autonomous/unbounded recursive self-improvement.
