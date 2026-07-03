# B9-Bridge Phase 2: M3-Min learned-entry audit harness

This folder implements the Phase-2 bridge from the closed-loop certified successor generator to a controlled learned-system entry audit.

It creates executable objects corresponding to the M3-Min theorem boundary:

```text
LearnedEntryAudit_{0:N}(M_theta, D, L, C) ⇓ LECert_{0:N}
```

and reports:

```json
{
  "audit_status": "FullPass | PartialPass | Fail",
  "TypeCert": true,
  "RegSemCert": true,
  "CoverageCert": true,
  "SVWitLib": true,
  "SVBuilderTrace": true,
  "PCS": true,
  "Q_SV_A_nonpositive": true,
  "GoalId": true,
  "TrustRef": true,
  "RealCont": true,
  "SVTract": true,
  "ReplayTrace": true
}
```

## Files

```text
artifacts/learned_entry/
  learned_entry_audit.py        # executable M3-Min audit harness
  lecert_schema.py              # LECert schema, validation, status logic
  controlled_learned_system.py  # controlled M_theta surrogate object
  README.md
```

## Scope boundary

This harness is intentionally narrow.

It can certify a **controlled learned-system surrogate** whose update interface is bounded, typed, and certificate-gated by the existing closed-loop RCP/RCLM generator and checkers.

It does **not** prove:

```text
arbitrary trained-system entry,
broad capable learned-agent entry,
external public benchmark improvement,
frontier-scale validation,
full autonomous RSI.
```

A `FullPass` means: for this controlled finite run, every executable learned-entry certificate component was supplied and the generated closed-loop artifact passed the existing checker.

## Run a smoke test

From the repository root:

```powershell
python .\artifacts\learned_entry\learned_entry_audit.py --mode rclm --N 2 --seed 0
```

Expected summary fields:

```json
"audit_status": "FullPass",
"ok": true,
"checker_passed": true
```

## Run the default RCLM audit

```powershell
python .\artifacts\learned_entry\learned_entry_audit.py --mode rclm --N 5 --seed 0
```

This writes:

```text
artifacts/learned_entry/results/rclm_N5_seed0/
  learned_system.json
  lecert.json
  learned_entry_audit_summary.json
  audit_runlog.json
  closed_loop_run/
    generated_artifact.json
    accepted_trajectory.json
    rejected_candidates.json
    closed_loop_runlog.json
    hashes.json
```

## Run the RCP audit variant

```powershell
python .\artifacts\learned_entry\learned_entry_audit.py --mode rcp --N 5 --seed 0
```

## Interpret the result

`FullPass` supports the M3-Min statement for the controlled run:

```text
A controlled learned system that supplies the full finite learned-entry certificate boundary enters the existing RCP/RCLM successor-verification theorem domain for that declared finite run.
```

It does not license a claim that arbitrary trained systems enter the domain.

## Recommended next phase

After Phase 2 passes, the next bridge is Phase 3:

```text
certificate-preserving benchmark sidecar
```

That phase should wrap task-performance benchmarks with score deltas plus RCP/RCLM certificate preservation evidence.
