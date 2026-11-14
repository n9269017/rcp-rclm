# Local-first Phase 17 development validation

This is an execution/evidence path, not relaxed phase-exit criteria.
GitHub CLI and hosted runners are optional services; pinned tools, independent
verification, isolation, required platform coverage, and replay remain separate
obligations. The project is public/open-source; do not expose credentials or
future hidden answers to the running proposer.

## Existing evidence is not a request to repeat the old run

The operator already completed 33 full-checkout Windows tests, the 1,907-entry
manifest verification, and commit `197f4bc022a68123c20cfd5f146149249663f1db`.
Those observations are retained as an attributed transcript, not machine-signed
or independently rerun Windows evidence. The earlier selected-module report
is also retained unchanged. The new recorder is for the next validation boundary.

The original script committed only `SHA256SUMS.txt`; terminal output was not
automatically committed. The operator record now closes that documentation gap.

## Capture future runs (ordinary Git + Python 3.11+, no gh)

Start from a clean, committed checkout with the current root manifest refreshed.
Run from the repository root in PowerShell:

```powershell
$Head = (git rev-parse HEAD).Trim()
$Out = Join-Path (Split-Path (Get-Location).Path -Parent) ("phase17-evidence-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
python scripts/phase17_local_evidence.py capture --expected-head $Head --output $Out
if ($LASTEXITCODE -ne 0) { throw "Local validation did not pass; retain the failure bundle." }
$Anchor = (Get-FileHash (Join-Path $Out "SHA256SUMS.txt") -Algorithm SHA256).Hash.ToLowerInvariant()
python scripts/phase17_local_evidence.py verify --expected-head $Head --bundle $Out --expected-manifest-sha256 $Anchor
if ($LASTEXITCODE -ne 0) { throw "Evidence verification failed." }
```

The capture profile runs syntax compilation, the normal Phase 17 foundation
tests, and canonical staged-blob manifest validation. It retains stdout/stderr
separately, per-command return codes and timing, UTC capture timestamps, commit,
tree and root-manifest identities, OS/Python/Git versions, and installed package
metadata. At least 33 tests and an unqualified unittest `OK` with zero skips are
required. The profile stops on the first failure and records remaining commands
as `not_run`; it never manufactures successful results for them.

Output is outside the repository, requires a new directory, and is never
committed or pushed automatically. The source must remain unchanged through
capture. This is not process sandboxing, secret isolation, a dependency lock,
or proof that the operating-system environment was fresh.

## Verify, retain, and publish evidence

Retain the printed manifest SHA-256 independently of the bundle. The verifier
checks that anchor, source commit, exact file/command sets, logs, exit statuses,
test count, and false closure/CI flags. It does not execute report-supplied
commands. A digest proves integrity relative to the retained anchor, not who
executed the commands; an attacker who controls both can fabricate reports.

Review logs and package metadata before publishing (paths and environment data
may be sensitive). Copy an approved bundle to a new source/run-specific evidence
directory, never over an old bundle. Stage intended new files, refresh the root
manifest, stage the manifest, verify it, and commit. Captured `source.commit`
continues to identify the tested source, not the later evidence-only commit.
Hashes, timestamps and unexecuted-run IDs must never be invented retroactively.

## Separate completion dimensions

| Dimension | Current boundary |
|---|---|
| Phase 17 controller/adapter | Initial slice implemented |
| Operator Windows foundation run | 33 passed; attributed transcript |
| Recorder unit tests | 22 passed on assistant Linux; fixture repositories |
| Hosted CI | Blocked before execution by reported billing lock |
| Fresh isolated environment | Not established |
| Cross-platform foundation | Not established; Linux/macOS not substituted by Windows |
| Pinned Lean/Phase 17 theorem checks | Not performed |
| Worker-free independent replay | Not implemented for Phase 17/18 |
| End-to-end successor/promotion campaigns | Not implemented |
| Phase 17 exit / full executable Gate E closure | False |
| EGC-0 | Not started; remains a frozen Phase 16 baseline |

Blocking a service does not waive a test. Historical Actions-dependent closure
code is not automatically compatible with local records: a future validated
local adapter must check the same evidence without fabricated workflow IDs.
This recorder is development evidence only and is not that closure adapter.

## PR and historical-publication policy

Continue on `agent/rcp-rclm-v5-phase-17-controller` and keep PR #68 draft.
Do not merge a development slice as Phase 17 closure. Do not reopen the closed
source-export helper PR #67. Do not rewrite v4.6, frozen v4.5 results, the
v5 roadmap tag/assets, Lean foundations, or DOI records for this transition.

A commit may explicitly use `[skip ci]` while the account is locked, avoiding
repeated zero-step Actions attempts. Skipped checks are not passes and may
remain pending; no required-check policy is bypassed. Hosted workflows remain
available for future execution. Do not change billing settings or retry jobs
as a side effect of evidence collection.

## Phase 17B extension

The inherited Phase 17A capture profile discovers the current foundation suite;
with the Phase 17B bootstrap/objective unit tests installed, it should run 67
checks (26 controller, seven Phase 16 adapter, 34 new bootstrap/objective tests).
The profile's historical minimum of 33 is not proof that new tests ran. The
Phase 17B application kit separately requires the exact 67-test count and then
runs the ten real-archive tests and `run_phase17_bootstrap.py`.

The latter reopens the pinned capture, closure, and Phase 15 M9 bundle, exercises
the normal Phase 16 `ModelState` constructor, selects the initial objective, and
writes a non-authorizing freeze receipt. Its output is outside the source tree.
All commands are fail-closed and no completed historical release is modified.
Evidence may be retained in a separate commit bound to the tested code commit;
this does not imply a rerun on the later evidence-only commit. Logs and public
OS/Python/package-version metadata are not private environment variables or
credentials, but should still be inspected before publication.
