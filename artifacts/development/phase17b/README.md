# Phase 17B development evidence

The three logs retain assistant-run tests of this incremental source. They do
not assert Windows/macOS success, a full current repository checkout, fresh
Lean checking, Phase 18 replay or phase closure. The archive integration uses
actual historical input bytes rather than generated substitutes.

`bootstrap_receipt.json` and `terminal_catalog.json` are deterministic outputs
from reopening the pinned historical archives. They retain the existing evidence
boundary; no new candidate has been promoted. `assistant-validation.json` binds
the tested implementation hashes and labels the workspace limitations.

Later `operator-<tested-code-head>/` directories may retain machine-generated
local capture from the full checkout, explicitly linked to its tested code
commit. An evidence-only commit is not relabeled as a fresh test execution.

No record here is a GitHub check result, external signature, or phase-success
authority. The surrounding development PR remains in draft.
