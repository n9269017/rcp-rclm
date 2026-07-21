# RCP/RCLM Runtime v3

This package implements the executable correspondence for Formal Core v3 Gate D, the
selected compact language-model successor lifecycle, the first complete bounded active-model
experiment cycle, recursive use of a promoted successor generator, and the first accepted
self-hosted Phase 12 successor.

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

`phase_10_closure_manifest.json` separates stable semantic identities from environment-bound
Phase 6 and lifecycle evidence.

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
and performs atomic promotion.

`phase_11_closure_manifest.json` deliberately separates portable semantic identities from
exact-run Phase 6, rejection-observation, certificate, ledger, promotion, and installed-byte
identities.

## Phase 12A recursive successor-generator start

`rcp_rclm_runtime_v3.phase12` freezes the selected four-promotion trajectory contract and
performs the first recursive invocation:

```text
Phase 11 promoted beta semantic package reconstructed
retained Phase 11 closure manifest bound
changed generation-2 generator policy loaded from the active package
changed generation-2 planner policy loaded from the active package
installed Phase 11 proposal protocol verified
model decoding performed from the successor package
exact typed program independently replayed
stale generation request rejected fail-closed
active package tree unchanged
held-out material consumed = false
manual repair count = 0
accepted Phase 12 promotions = 0
phase12_exit_closed = false
```

The successor emits:

```text
V1;O=F;U=WLCGP;D=A;A=N;R=1,0,1,96,1,1;E=WLCGP;B=X;G=2;P=2
```

Because generator and planner generation 2 are already active, a program selecting generator
and planner updates must request a strictly newer generation. The immutable validator returns
exactly `PHASE12_GENERATION_NOT_ADVANCED`. Rejection occurs before Phase 6 realization and cannot
modify the active package.

## Phase 12B first accepted self-hosted successor

The next bounded invocation is conditioned on the retained Phase 12A rejection and comes from the
same unchanged generation-2 package. The installed planner projects the active package's rejected
draft onto transition zero of the frozen schedule and emits:

```text
V1;O=F;U=W;D=A;A=N;R=1,0,1,96,1,1;E=W;B=X;G=2;P=2
```

The program is bound to the active package, model, generator, planner, trajectory protocol,
objective, prior draft, prior validation, transition index, and original total budget. It changes
only model weights and leaves the generation-2 generator and planner unchanged.

The selected new held-out task is:

```lean
import Mathlib

macro "q" : tactic => `(tactic| omega)

example (n : Nat) : n <= n := by
  q
```

The Phase 12B runtime establishes:

```text
fresh rejection-conditioned proposal replay is byte-identical
held-out task IDs, prompts, source, and answers remain unavailable
isolated worker run 1 = isolated worker run 2 = host-exact tensor
M1 realized through Phase 6
M1 rollback to M0 verified exactly
protected rfl retained
Phase 10 omega retained
Phase 11 z retained
new Phase 12 q task certified
protected KL/QRE non-regression accepted
strict new-task information witness accepted
Gate D / Phase 9 changed_components = [model_weights]
pinned Lean and hardened checker accepted
Phase 12A rejection appended without moving the active pointer
M1 atomically promoted with unchanged M0 store package as parent
reopened immutable package contains the expected M1 semantic package
generation-2 generator/planner remain installed for M1 -> M2
```

The certified frontier advances from three tasks to four:

```text
F0 subsetneq F1
|F0| = 3
|F1| = 4
```

The completed Phase 12 prefix records:

```text
generator invocations:   2
rejected attempts:       1
candidate realizations:  1
candidate evaluations:   1
accepted promotions:     1
frontier expansions:     1
manual repairs:          0
phase12_exit_closed:      false
```

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

Run the focused suites and portable Phase 12 references:

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

python python/rcp_rclm_runtime_v3/tools/run_phase12_tests.py \
  --package-root python/rcp_rclm_runtime_v3 \
  --out artifacts/runtime_v3_phase_12/tests.log

python python/rcp_rclm_runtime_v3/tools/run_phase12_reference.py \
  --repo-root . \
  --out artifacts/runtime_v3_phase_12/phase12a_reference.json

python python/rcp_rclm_runtime_v3/tools/run_phase12b_reference.py \
  --repo-root . \
  --out artifacts/runtime_v3_phase_12/phase12b_reference.json

python python/rcp_rclm_runtime_v3/tools/validate_phase12b_schema.py \
  --schema python/rcp_rclm_executable_core_v3/contract/phase_12_first_promotion.schema.json \
  --instance artifacts/runtime_v3_phase_12/phase12b_reference.json \
  --out artifacts/runtime_v3_phase_12/phase12b_schema.json
```

Run the isolated Phase 12B worker only in the untrusted training environment:

```bash
python python/rcp_rclm_runtime_v3/tools/run_phase12b_training_reference.py \
  --repo-root . \
  --out artifacts/runtime_v3_phase_12/phase12b_training.json
```

The authoritative first promotion additionally requires the pinned Lean toolchain and built
Formal Core v2/v3 projects:

```bash
python python/rcp_rclm_runtime_v3/tools/run_phase12b_closure.py \
  --repo-root . \
  --lean-project-root lean/rcp_rclm_formal_core_v3 \
  --out artifacts/runtime_v3_phase_12/phase12b_closure.json
```

## Claim boundary

The completed prefix establishes one recursive fail-closed rejection followed by one later fresh,
accepted, model-weight successor promotion. It establishes `F0 subsetneq F1` and leaves the active
generation-2 generator and planner installed in `M1`.

It does not establish `M1 -> M2`, `M2 -> M3`, `M3 -> M4`, the complete four-promotion recursive
chain, generic successor availability, arbitrary native-float equivalence, or autonomous/unbounded
recursive self-improvement.
