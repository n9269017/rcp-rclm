# Phase 17M — concrete protected sparse goal and diagonal-information semantics

Development increment based on `a60eee75b3c4b9797fe362ffed7773d2eb6bdc85`.
Keep PR #68 draft and unmerged. This is NOT complete root acceptance or Phase 17 closure.

## The semantic interpretation is explicit, not a hash or success counter

Phase 17L already reconstructs one candidate and composes its typed bindings,
frontier meanings and producer provenance. Its learned-step assembler still needs
concrete base, goal, resource and information premises. Phase 17M supplies one
explicit protected interpretation using the existing byte-token sparse inference
profile. It does not declare that this profile covers the full model or all goals.

The protected contract reopens eleven original inherited byte-token tasks: seven
from the Phase 10–12 lineage and four from Phase 14. It binds their original task
identities, prompt hashes, expected completion bytes plus EOS and challenge
commitments. The contract digest is
`af34fb682a920122318f001bf2b76e826244f38202d0377f99f65515e4a14e28`.
It does not obtain new targets from the candidate or from an operator pass report.

Both physical packages are independently observed. The full 320×320 little-endian
int16 transition tensor is read and bound to the physical component inventory.
For every one of the 260 current token IDs, every one of the 260 target scores is
independently decoded, with the existing divisor 2048, clipping [-15,15], and exact
normalization:

`weight[j] = 2^(clipped_score[j] - minimum_clipped_score)`

`p[j] = weight[j] / sum(weight)`.

All 260 rows per package are compared to the existing production
`exact_dyadic_distribution`, using exact fractions: 520 row comparisons in total.
This is not a new softmax policy or a full-native-transformer equivalence claim.
The selected packages have 37 distinct conditional rows. A deterministic row
selector representation retains all 260 contexts without repeating equal rows.
The packet includes the exact tensor bytes, decoded scores, positive masses,
normalizers, selectors, physical identities and independently decoded goals.
Hash equality alone is not substituted for comparing the observed probability data.

## Concrete goal and information functions

For each of the eleven protected tasks, the goal observation is its effective
package-bound route marker and actual decoded completion tokens including EOS.
The original task target is checked, and its decode identity is bound to the
newly reconstructed Phase 17L task evidence. Goal drift counts changed protected
goal observations. Its declared policy allows no regression (budget zero).
It is not a universal value-alignment, objective-policy, or all-task guarantee.

The information function is the sum, over the original teacher-forced protected
positions, of the existing diagonal KL divergence. There are 28 positions. The
fixed positive target distribution uses mass 4096 for the correct target token
and mass 1 for every other token, exactly as in inherited Phase 10 information
semantics. Positions and targets are independently fixed; the candidate cannot
change the reference distribution or remove a difficult position.

`I(s) = sum_(current,target in protected positions) KL(p_s(current) || q_target)`

This is an actual information-valued function, not a package hash, frontier size,
or constant. For the selected unchanged probabilities, it is retained exactly.
A test swaps high/low probability labels: entropy alone stays equal while KL to
the fixed target increases. Such substitution must reject.

The numerical diagnostic uses inherited 256-bit rational interval arithmetic to
record Shannon entropy and KL sums. Equal intervals are not used to pretend an
uncertain subtraction proves zero. Formal preservation follows from exact
probability and fixed-target identity. These numerical interval calculations are
not new proofs about the implementation of the interval algorithm.

The current protected fixture has identical before/after rows and goals. This
establishes preservation, not new capability or strict information improvement.
The sparse task scope excludes the Phase 15 planner, the vector registry and
arbitrary full-transformer inputs; their complete information interpretation is
still outstanding. The whole 21→22 selected capability frontier is NOT relabeled
as eleven sparse semantic tasks or vice versa.

## Formal layer and actual root fields

`ProtectedSemantics.lean` constructs a positive normalized distribution from
positive integer masses and then the existing immutable-root diagonal density
object. It uses the root Shannon entropy, diagonal QRE and KL definitions, and
checks their diagonal identity. It defines the concrete protected information
sum and goal distance, and an adapter for the actual learned-root fields:

- `goalDrift` and zero `goalDriftBudget`;
- `informationValue` and zero `informationBudget` with its nonnegativity proof.

Zero budgets are the explicit no-regression policy, not invented zero resource
measurements. The information and goal functions remain data-dependent. Resource,
frontier, task-soundness and producer-binding fields are left unchanged. Thus the
adapter can be applied to the Phase 17L composed kernel without pretending that
its remaining base/resource/autonomous premises have been supplied.

The selected certificate binds the same joint transaction and proves equality of
the complete observed conditional table and goal observations. It checks concrete
protected goal and information bounds, plus entropy/QRE retention over each of
the 260 token contexts with any fixed positive row target.

Fourteen exact named theorem/axiom audits are required, plus compiler rejection of
four separate negative controls: ChangedProbability, ChangedGoal, ChangedTarget,
and MixedCandidate. The first swaps mass labels at an actually used protected
context; it does not merely change an unused table entry. An unrelated parser
error, missing compiler or timeout is not a successful negative control. The gate
requires Lean's explicit false-proposition diagnostic.

The new gate does not rerun the earlier Phase 17L 43-audit certificate, its old
negative controls, or the 172 Phase 17H plan proofs. It recomputes the exact joint
packet instead; a historical success report cannot stand in for current data.
Its trusted extraction relationship remains external, not a proof of universal
Python semantics or independent historical execution attestation.

## Trust and completion boundaries

Physical file/tensor parsing, canonical hashing, route decoding, Python reference
arithmetic, extraction of Lean literals, and toolchain/import-cache integrity
remain explicit externally checked bindings/assumptions. The original compiled
root is not edited. The physical observation refinement is not formally proved.
A caller's hash does not authenticate that the declared measurements happened.

No complete compatible base/RCLM kernel, full goal/information interpretation,
complete resource accounting, complete recursive-productivity frontier, active
atomic promotion/rollback, durable cross-turn challenge/history consumption,
autonomous campaign, independent replay or cross-platform closure is supplied.
No new hidden task, training, promotion or EGC-0 execution occurs in this increment.

Retain false: `root_transition_verified`, `recursive_productivity_recertified`,
`full_frontier_recertified`, `full_learned_semantic_refinement`,
`neural_decoder_formally_verified`, `complete_resource_accounting`,
`promotion_authorized`, `promotion_performed`, `live_capability_gain_demonstrated`,
`phase17_exit_closed`, `gate_e_closed`, `egc0_started`, and
`full_learned_step_instantiated`. The full-root assessment remains
`blocked_missing_semantic_witnesses`.

## Reproduction and installation

`scripts/run_phase17_protected_semantics_tests.py` requires 83 tests.
`scripts/run_phase17_joint_tests.py` supplies the 66 unchanged joint regressions.
The actual gate is:

`python scripts/run_phase17_protected_semantics_gate.py --test-fixture --require-lean --lean-workspace <prepared formal-root> --output <new external directory>`.

There is a preparation-only inspection mode, but it cannot satisfy the installer.
The application kit requires a clean exact local/remote base, creates a separate
short-path checkout, checks canonical Git-blob manifests, uses UTF-8 explicitly,
and advances only after successful actual Lean checks and both test commands.
All bundled and generated logs use `.txt` suffixes, avoiding ignored `.out`/`.log`
paths. No broad force-add exception is used. Source and evidence commits are
separate; evidence bytes are checked after staging. No reset, amend, force-push,
main merge, dependency installation, release/DOI operation or hosted-CI claim.
