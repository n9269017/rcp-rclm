# RCLM-CRSI-Core: Certified Recursive Successor Improvement Core Test

This folder adds the first **non-RE-Bench** core RSI-instantiation test for the
RCP/RCLM package.

The test asks:

```text
Can the instantiated RCLM architecture execute a nontrivial recursive successor
chain, with predecessor verification, certificate preservation, protected
non-loss constraints, adversarial rejection evidence, and measurable internal
improvement, before the loop is attached to an external benchmark?
```

## What is new relative to the existing closed-loop engine?

The existing closed-loop engine already builds a finite canonical successor trace
inside one RCP/RCLM artifact.  This CRSI core test adds an **outer package-level
successor chain**:

```text
RCLM_0
  -> generates successor package RCLM_1
  -> predecessor/root verifier accepts RCLM_1
  -> RCP/RCLM certificate bundle preserved
  -> protected non-loss invariants preserved
  -> CoreScore increases
  -> RCLM_1 becomes the active predecessor

RCLM_1
  -> generates successor package RCLM_2
  -> predecessor/root verifier accepts RCLM_2
  -> certificates and invariants preserved again
  -> CoreScore increases again

...
```

Each `RCLM_t` is a versioned successor package, not merely a JSON state and not
merely one append step.  Each package contains its own RCLM closed-loop run, RCP
core closed-loop run, checkers, learned-entry audit summaries, hash ledgers,
non-oracle manifest, score ledger, ability ledger, and paper-obligation ledger.

## Internal improvement functional

A successor package improves its predecessor iff the following tuple increases
lexicographically:

```text
CoreScore(M_t) =
  (
    certified_ability_count,
    verified_horizon_capacity,
    verifier_obligation_coverage,
    adversarial_rejection_coverage,
    generator_self_hosting_depth,
    reproducibility_score,
    -normalized_cost
  )
```

The default run makes package-level improvement nontrivial by increasing the
certified horizon capacity from `base_N` upward across the successor chain.  The
score improvement is accepted only when protected invariants and hash-chain
conditions also pass.

## Protected invariants

Every successor package must preserve:

```text
certificate_preserved == true
predecessor_checker_accepts_successor == true
all_pcs_checked == true
residuals_nonpositive == true
goal_identity_drift_zero == true
trust_anchor_unchanged == true
reality_containment == true
non_loss_recovery_preserved == true
hash_chain_valid == true
no_oracle_or_manual_repair == true
strict_ability_expansion == true
invalid_adversarial_candidates_rejected == true
```

## Minimum, strong, and maximal v1 runs

### Minimum serious version: 3-cycle chain

```powershell
python .\artifacts\crsi_core\rclm_crsi_core_harness.py `
  --successor-cycles 3 `
  --base-N 2 `
  --seeds 0 `
  --overwrite
```

This creates:

```text
RCLM_0 -> RCLM_1 -> RCLM_2 -> RCLM_3
```

### Strong version: 5-cycle, multi-seed

```powershell
python .\artifacts\crsi_core\rclm_crsi_core_harness.py `
  --successor-cycles 5 `
  --base-N 2 `
  --seeds 0 1 2 `
  --overwrite
```

### Offline reproduction check

After a run, validate one chain summary without rerunning the engine:

```powershell
python .\artifacts\crsi_core\reproduce_crsi_core.py `
  .\artifacts\crsi_core\results\rclm_crsi_core_k3_baseN2_seed0\rclm_crsi_core_chain_summary.json
```

The reproduction checker verifies schemas, artifact hashes, parent hash-chain
links, transition acceptance records, protected invariant flags, and CoreScore
monotonicity.

## Output layout

A run writes to:

```text
artifacts/crsi_core/results/
  rclm_crsi_core_multi_seed_summary.json
  rclm_crsi_core_k3_baseN2_seed0/
    root_trust_anchor.json
    rclm_crsi_core_chain_summary.json
    paper_obligations.md
    packages/
      RCLM_0/
        successor_package_manifest_0.json
        non_oracle_manifest_0.json
        certificate_bundle_0.json
        ability_ledger_0.json
        score_ledger_0.json
        paper_obligations_0.md
        rclm_closed_loop_run/
        rcp_closed_loop_run/
        learned_entry/
        learned_entry_rcp/
      RCLM_1/
        ...
    transitions/
      transition_0_to_1.json
      predecessor_verification_0_to_1.json
      transition_1_to_2.json
      predecessor_verification_1_to_2.json
      ...
```

Every successor package manifest includes at least:

```text
successor_id
parent_successor_id
source_commit_or_tree_hash
generator_hash
checker_hash
schema_hash
certificate_bundle_hash
accepted_trajectory_hash
rejected_candidates_hash
ability_ledger_hash
score_ledger_hash
claim_boundary_hash
```

Every transition emits:

```text
transition_t_to_t+1.json
predecessor_verification_t_to_t+1.json
```

Every package emits:

```text
successor_package_manifest_t.json
non_oracle_manifest_t.json
paper_obligations_t.md
```

## Pass/fail standard

The run passes only if:

```text
k >= 3 successor cycles
no manual repair inside the chain
all successor packages hash-logged
predecessor/root verifier accepts every successor
RCP certificate preserved every step
RCLM certificate preserved every step
non-loss invariant preserved every step
strict certified ability expansion every step
at least one nontrivial package-level improvement every transition
invalid/adversarial candidates rejected every step
score ledger improves lexicographically
full run reproducible from a single command
claim boundary explicitly says finite executable witness, not full autonomous RSI
```

## Claim boundary

A passing run supports this finite executable claim:

```text
We exhibit a reproducible finite certified recursive successor-improvement chain
for the RCLM instantiation: each successor package is generated,
predecessor/root-verified, certificate-preserving, non-lossy under the declared
protected invariants, non-oracular under the run manifest, and strictly improved
under the internal CoreScore functional.
```

It does **not** claim:

```text
full autonomous RSI
unbounded-horizon empirical proof
arbitrary trained-system entry
frontier-scale validation
RE-Bench, SWE-bench, MLE-bench, or EvalPlus leaderboard performance
```

Those are later external validation layers.
