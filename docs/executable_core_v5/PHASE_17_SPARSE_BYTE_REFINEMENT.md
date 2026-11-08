# Phase 17R — captured tensor bytes to protected sparse semantics

This increment continues from the completed Phase 17Q evidence head
`54de3a0841bb747207e2721566e38f6582b8874b`. It preserves Q's implementation and
Windows evidence. Keep PR #68 draft and unmerged. R does not authorize promotion,
close Phase 17, modify the pinned formal foundations, or alter releases or DOI
records.

## The remaining premise addressed

Q constructs a concrete finite-observation kernel and an actual selected
`Learned.LearnedAcceptedStep`. Its protected probability and goal observations
were freshly reconstructed in Python. Although M compared the independent
observation extractor with the existing production implementation, the actual
tensor-byte interpretation was not yet checked inside the new Lean certificate.

R adds that interpretation for the explicitly declared inherited sparse
transition profile. It supplies the complete captured tensor image to Lean as
canonical nonzero byte support plus an exact length. Lean independently reads
the byte literals, constructs scores and distributions, and checks protected
continuations. It does not receive a caller-selected score table as the tensor
interpretation. The expected Q score table is a comparison target whose equality
with the decoded image must be proved.

The result is a refinement of the selected captured image, rather than a proof
of OS reads, Python execution, prompt routing, SHA-256 collision resistance, or
full-transformer execution. Those remaining boundaries are explicit.

## Exact input and interpretation

The selected tensor has 204,800 bytes: 102,400 little-endian signed 16-bit words
in a 320 by 320 array. The inherited sparse probability domain contains 260
current tokens and 260 possible next tokens. Its word index is

\[
  \operatorname{index}(c,t) = 320t+c.
\]

The reference decoder reads the low and high bytes at twice that index. It forms
the unsigned value `lo + 256 * hi`, subtracts 65,536 at values at least 32,768,
and divides by the fixed score divisor 2,048. Every interpreted word must be
exactly divisible by the divisor. Negative division uses mathematical floor
division; nonintegral words are rejected by the profile.

For each complete conditional row, the probability interpretation clips scores
to `[-15, 15]`, subtracts the minimum clipped score, exponentiates base two, and
normalizes the resulting positive integer masses. The existing protected model
represents each unnormalized mass minus one. R proves equality to that exact
representation and consequently to its normalized distribution.

The Python preparation separately reconstructs the predecessor and inactive
candidate from the anchored historical inputs. Both complete tensor images are
encoded and decoded independently. The encoding must round-trip every byte,
including padding outside the interpreted 260 by 260 subdomain. Offsets must be
strictly increasing, unique, and in bounds; stored values must be nonzero bytes.
Boolean values, duplicate offsets, explicit zero entries, extra fields and
noncanonical encodings are refused. The selected image has 178 nonzero bytes.

The Lean representation uses a finite ordered search tree for this complete
nonzero support, with zero as the value at every omitted in-bounds offset. Its
canonicality condition checks the entire support and the exact image length.
The selected certificate checks every one of the 67,600 interpreted score cells
and binds all 260 conditional probability rows. Independently captured before
and after images are proved equal, which transports the entire interpretation
to both packages without copying one observed package into the other.

The retained Q packet remains externally fixed at
`b6dd8df26fb7efc25c6fed6cc7832bf65a42b933fd2d1276346695bd8451c9e5`.
Freshly reconstructed Q inputs must match it exactly. Q's execution, operator
record and generated positive source are separately pinned. A retained success
report is never accepted as a theorem.

## Goal execution and information transport

The sparse production decoder selects the largest **raw** score and chooses the
lowest token identifier on a tie. This happens before probability clipping.
Using clipped probabilities to choose the token would give different behavior
at some signed boundaries; R keeps those operations separate.

The reference decoder has a maximum of sixteen selected tokens. Token 258 is
EOS and ends a successful continuation. A different token at least 256 stops
unsuccessfully. Exhausting the token allowance also stops unsuccessfully. The
new certificate checks all eleven inherited protected continuations, including
their final EOS tokens, from their separately bound effective markers. Their
fixed targets contain 28 token positions in total. Before/after preparations
therefore perform 22 complete continuation comparisons.

The effective markers are outputs of the existing routed task interpretation.
R checks the subsequent tensor-driven decoding. It does not prove the earlier
prompt-to-marker memory/planner/adapter routing computation. It does not infer
full planner, vector-task or arbitrary-input neural semantics from these eleven
protected continuations.

The probability binding transports the existing fixed diagonal-KL information
function to distributions computed from the captured bytes. Before/after
information values are equal. The inherited Shannon/von Neumann and KL/diagonal
quantum-relative-entropy interpretations remain the same. R does not claim
strict information improvement or general goal preservation.

The selected `Phase17Sparse.selected_learned_acceptance_bound` theorem combines
Q's actual finite-model accepted step with the newly checked before/after
captured-byte, probability, and goal bindings. The full physical transition is
still not authorized by this result.

## Fresh formal checking and controls

The R gate uses the already prepared, pinned Lean 4.31.0 toolchain and immutable
root/dependency sources. It never installs dependencies. Every execution begins
with a new external temporary import directory.

Q's exact generated positive source is freshly reconstructed. Only its exact
fourteen audit-print commands are removed to create `Phase17QDependency.lean`.
That source is compiled once during R into a new import artifact. The R positive
certificate and controls import this same-run module. The source, compiler,
command result, and every emitted import artifact are hashed and checked for
changes. An explicit dependency-resolution command must also resolve the R
certificate to that exact newly compiled module. Prior Q compiler output is not
an import artifact or a proof.

This fresh dependency compilation is recorded separately from the fifteen new
R named audits. It is not a rerun of Q's former nine-case gate or any earlier
worker/proof campaign. The prebuilt immutable foundation imports retain their
existing cache-trust boundary.

The R positive result must have the exact named audit sequence and only the
approved foundational dependencies `propext`, `Classical.choice`, and
`Quot.sound`. Accepted output may not contain placeholder-proof dependencies.
Generated source rejects placeholder, arbitrary-axiom, unsafe, partial and
native-decision escape tokens.

The score and integrality certificate is assembled from 260 separately checked
row lemmas, each covering all 260 target tokens. The outer proof combines those
lemmas over the complete context range. Closed positive decisions use Lean's
kernel-checking mode, and elaboration is serial to bound concurrent proof work.
The fifteen named audits include the dependencies of those internal row lemmas.

Eight changed certificates must fail with explicit false-proposition
diagnostics:

| Control | Necessary condition exercised |
| --- | --- |
| ChangedTensorByte | The selected interpreted-byte mutation must fail the original probability-row binding |
| TransposedTensor | Reversing the tensor axes must not pass the fixed indexing interpretation |
| AlteredProbability | A changed expected mass must not match the byte-derived normalization |
| WrongMarker | An incorrect effective marker must not produce the fixed protected continuation |
| MissingEOS | A target omitting its terminal EOS must not count as successful decoding |
| InvalidByteRange | A value outside the byte range must not be a canonical captured image |
| WrongSignedBoundary | The signed minimum must not be interpreted as positive 32,768 |
| WrongGreedyTie | The higher token identifier must not win a raw-score tie |

Each control uses the same reference condition or decoder as the positive
certificate. The final two are explicit boundary controls on those functions;
they are not changes to the physical fixture. Negative files emit no positive
audit claims. Missing imports, unrelated errors, successful compilation,
timeouts and process kills are failures of the gate, not accepted controls.

The actual gate records progress after each compiler command, so an interruption
retains completed command output. An incomplete or failed result cannot become
a successful installation. The formal execution record and the final progress
record must agree during retained verification.

## Runtime tests, reproduction, and attribution

The new tests cover independent byte arithmetic, complete sparse round trips,
padding changes, signed limits, exact and nonintegral division, transposition,
clipping/minimum normalization, raw-score ties, EOS/special-token/token-limit
stops, all selected score cells, all protected continuations, packet and hash
substitution, scope escalation, source paths, and formal log/audit/control
guards. Controlled compiler-log fixtures in tests are not actual Lean evidence.
Installer guard tests remain separately attributed from the actual formal gate.

The entry points are:

```text
python scripts/run_phase17_sparse_refinement_tests.py
python scripts/run_phase17_sparse_refinement_gate.py --test-fixture --require-lean --lean-workspace <prepared-formal-root> --output <new-external-output>
python scripts/run_phase17_sparse_refinement_gate.py --verify-only --output <same-output>
```

An optional `--toolchain-root` selects an already installed pinned toolchain.
Preparation-only mode cannot satisfy the installer. The verifier-only command
freshly reconstructs the physical inputs and compares packet bytes, generated
sources, and saved results without workers, fresh challenges or compiler runs.
It runs at the original tested source commit. It is not Phase 18 independent
replay or an independent attestation of an earlier physical execution.

The application helper starts from the exact clean Q baseline and creates a
separate short-path checkout. It checks every payload, commits source before
testing, runs the new test suite, actual R gate and retained reconstruction,
then writes a separate evidence commit and canonical checksums. Only after
successful validation may it fast-forward the original checkout and optionally
perform an ordinary development-branch push. It cannot merge PR #68 or promote
a candidate. Failures preserve workspaces and records without automatic retries.

## Scope retained after a successful R gate

Only `sparse_tensor_projection_checked` and
`protected_sparse_decoder_checked` become true for the new R result. The
existing Q finite-model result remains separately attributed. No new worker,
challenge, online candidate, frontier expansion, or live capability gain is
introduced by R.

All broader full-root claim flags remain false. In particular, R does not close
the universal physical-observation refinement, Python/OS/hash trust, full
transformer and routed task semantics, authenticated successor context,
autonomous continuation, full frontier/recursive-productivity recertification,
complete resource accounting, promoted-lineage authority, active atomic
promotion/rollback, platform campaigns, or independent replay obligations.

R's byte preparation, physical reconstruction, source generation, compiler work,
CPU/accelerator time, memory, storage and energy are outside the retained N
reference-work tariff. These costs remain unmeasured, not zero. The old
4,032-unit reference trace is not relabeled as R's execution cost.

Successful assistant Linux and later operator Windows runs must retain their
own tested commits, source trees, outputs and timings. Phase 17, Gate E, EGC-0
and Phase 18 closure remain open.
