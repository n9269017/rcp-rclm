# RCP/RCLM Runtime v3

This package implements the executable correspondence for Formal Core v3 Gate D, the
selected compact language-model successor lifecycle, and the first complete bounded
active-model experiment cycle through realized rejection and atomic promotion.

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

## Full Phase 11 active-model lifecycle

`rcp_rclm_runtime_v3.phase11` implements one bounded autonomous experiment-planning cycle:

```text
host-installed active generator/planner bootstrap
bootstrap excluded from autonomous-improvement counting
canonical typed mutation-program grammar
fixed total wall-clock, accelerator, step, byte, candidate, and evaluation budgets
active predecessor model emits all proposal bytes
invalid proposal rejected before candidate realization
alpha model-generated candidate realized through Phase 6
alpha rollback verified exactly
alpha rejected for protected-capability regression
rejection ledger written with active package unchanged
fresh beta proposal bound to alpha rejection evidence
beta model-generated candidate realized through Phase 6
protected rfl and Phase 10 omega tasks retained
new Phase 11 held-out Lean task certified
selected entropy/KL/diagonal-QRE obligations accepted
complete Gate D / Phase 9 transition accepted
beta atomically promoted with unchanged active parent
final ledger sequence number = 2
changed generation-2 generator and planner installed in immutable promoted package
held-out material consumed = false
manual repair count = 0
phase11_exit_closed = true
```

Candidate generation and training remain untrusted. The host independently rebuilds accepted
bytes, evaluates decoded tasks, invokes pinned Lean after candidate freeze, constructs
certificates outside the candidate, runs the hardened checker, controls the Phase 7 ledger,
and performs the atomic promotion.

The alpha rejection and beta promotion are explicit store transactions. Alpha's rejection
entry does not move the active pointer. Beta's promoted package names that unchanged active
package as its parent, and the reopened immutable package is checked to contain the expected
successor generator and planner files.

## Retained Phase 11 evidence boundary

`phase_11_closure_manifest.json` deliberately separates portable semantic identities from
exact-run evidence:

- `stable_reference_hashes` covers active identities, the invalid and alpha proposal chain,
  the alpha semantic candidate, beta's semantic package/model identities, and the changed
  successor policy hashes;
- `code_proof.exact_runtime_hashes` covers Phase 6 reports, beta's rejection-bound invocation
  and fixture, lifecycle certificate and transition, ledger entries, promotion records, and
  installed policy-byte hashes.

Beta's proposal consumes alpha's Phase 6 rejection observation, so its invocation hash and
all downstream certificate identities are correctly retained as runtime-bound rather than
presented as cross-platform semantic identities.

## Build and test

Install Runtime v2 and Runtime v3:

```bash
python -m pip install --no-deps -e python/rcp_rclm_runtime_v2
python -m pip install -e "python/rcp_rclm_runtime_v3[test]"
```

Install the optional training dependency only for isolated untrusted training jobs:

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
  --out artifacts/runtime_v3_phase_11/generator_manifest.json

python python/rcp_rclm_runtime_v3/tools/validate_phase11_closure_manifest.py \
  --repo-root . \
  --out artifacts/runtime_v3_phase_11/closure_manifest.json

python python/rcp_rclm_runtime_v3/tools/run_phase11b_reference.py \
  --out artifacts/runtime_v3_phase_11/reference.json
```

The authoritative Phase 11 rejection and promotion additionally requires the pinned Lean
toolchain and built Formal Core v2/v3 projects:

```bash
python python/rcp_rclm_runtime_v3/tools/run_phase11b_closure.py \
  --repo-root . \
  --lean-project-root lean/rcp_rclm_formal_core_v3 \
  --out artifacts/runtime_v3_phase_11/phase_11_closure.json

python python/rcp_rclm_runtime_v3/tools/validate_phase11_closure_manifest.py \
  --repo-root . \
  --report artifacts/runtime_v3_phase_11/phase_11_closure.json \
  --out artifacts/runtime_v3_phase_11/retained_closure_validation.json
```

## Claim boundary

Phase 11 establishes one active predecessor, one invalid proposal rejection, one realized
model-generated candidate rejection, one later fresh model-generated candidate promotion,
and installation of changed generation-2 generator and planner policies. It does not establish
recursive use of those modified policies, generic successor availability, arbitrary
native-float equivalence, or autonomous/unbounded recursive self-improvement. Recursive use is
reserved for Phase 12.
