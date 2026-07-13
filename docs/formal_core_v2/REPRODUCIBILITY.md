# Formal Core v2 reproducibility

This document reproduces the active Lean project at:

```text
lean/rcp_rclm_formal_core_v2/
```

The authoritative validation is the clean GitHub Actions workflow in
`.github/workflows/formal-core-v2.yml`. A local build is useful, but a local cache
failure is not evidence that the synchronized source fails.

## Immutable inputs

```text
Lean toolchain:
  leanprover/lean4:v4.31.0

mathlib repository:
  https://github.com/leanprover-community/mathlib4.git

mathlib commit:
  fabf563a7c95a166b8d7b6efca11c8b4dc9d911f

Paper I source blob:
  084eae21d252d205d2012b62744c1506644e3e58

Paper II source blob:
  9b51be8294ad79fd4f63522b01e0f617f0bf2ffd
```

The Lean and mathlib pins are encoded in `lean-toolchain`, `lakefile.toml`, and
`lake-manifest.json`. The paper blobs and historical v1 blobs are recorded in
`formalization_manifest.json` and checked by the pin-audit script.

## Required tools

```text
git
elan
Lean/Lake through elan
bash for the paper-alignment script
sha256sum or an equivalent SHA-256 utility for artifact verification
```

The GitHub workflow runs on Ubuntu. Windows can build the project, but interrupted
mathlib downloads and partial `.olean` writes can leave invalid local caches.

# Clean reproduction on Linux or macOS

From a clean checkout:

```bash
git status --short
cd lean/rcp_rclm_formal_core_v2

cat lean-toolchain
cat lakefile.toml

export MATHLIB_NO_CACHE_ON_UPDATE=1
lake update
lake exe cache get
lake build
```

A successful build does not replace the separate source-admission and theorem-
axiom checks below.

## Paper/source pin audit

From the repository root:

```bash
bash docs/formal_core_v2/audit/verify_paper_alignment_pins.sh
```

This checks the pinned paper blobs, required theorem labels, mapped Gate A/Gate B/
RCLM surfaces, and closure-record claim-boundary text. A passing pin audit means
the audited sources and mapped declaration names have not drifted; it does not
prove semantic equivalence by itself.

## Theorem-axiom audits

From `lean/rcp_rclm_formal_core_v2`:

```bash
lake env lean ../../docs/formal_core_v2/audit/GateAAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateBAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/RCLMRefinementAxiomAudit.lean
lake env lean ../../docs/formal_core_v2/audit/GateCAxiomAudit.lean
```

Each audit elaborates named public declarations and prints the kernel axioms used
by them. The workflow fails if any report contains `sorryAx`.

## Source-admission scan

The workflow scans only project Lean source, excluding `.lake` and generated audit
output. Equivalent local checks from the project directory are:

```bash
if grep -RInE \
    --include='*.lean' \
    --exclude-dir='.lake' \
    --exclude-dir='audit-results' \
    '(^|[^[:alnum:]_])(sorryAx|sorry|admit)([^[:alnum:]_]|$)' \
    RcpRclmFormalCoreV2 RcpRclmFormalCoreV2.lean; then
  exit 1
fi

if grep -RInE \
    --include='*.lean' \
    --exclude-dir='.lake' \
    --exclude-dir='audit-results' \
    '^[[:space:]]*axiom[[:space:]]' \
    RcpRclmFormalCoreV2 RcpRclmFormalCoreV2.lean; then
  exit 1
fi
```

These scans answer whether the project source contains admitted proofs or project-
local axiom declarations. They do not remove standard Lean/mathlib foundational
dependencies.

# Clean reproduction on Windows PowerShell

From the repository root:

```powershell
cd $HOME\Desktop\rcp-rclm

git fetch origin --prune
git status --short

cd .\lean\rcp_rclm_formal_core_v2

Get-Content .\lean-toolchain
Get-Content .\lakefile.toml

$env:MATHLIB_NO_CACHE_ON_UPDATE = "1"

lake update
if ($LASTEXITCODE -ne 0) { throw "lake update failed" }

lake exe cache get
if ($LASTEXITCODE -ne 0) { throw "mathlib cache retrieval failed" }

lake build
if ($LASTEXITCODE -ne 0) { throw "Formal Core v2 build failed" }
```

Use the committed `lake-manifest.json`. Do not delete or replace it merely because
a local `.lake` cache is corrupted.

## Windows recovery from corrupted `.olean` or `.ltar` files

Typical cache-corruption symptoms include:

```text
invalid header
bad .ltar file
expected value at line 1 column 1
unexpected input in a .trace file
failed to read ... .olean
```

These errors usually indicate an interrupted or corrupted local dependency cache,
not a Lean source error. The safest recovery is to remove generated state and
re-resolve from the committed pins:

```powershell
cd $HOME\Desktop\rcp-rclm\lean\rcp_rclm_formal_core_v2

Remove-Item .\.lake -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$HOME\.cache\mathlib" -Recurse -Force -ErrorAction SilentlyContinue

$env:MATHLIB_NO_CACHE_ON_UPDATE = "1"

lake update
if ($LASTEXITCODE -ne 0) { throw "lake update failed after cache reset" }

lake exe cache get
if ($LASTEXITCODE -ne 0) { throw "cache retrieval failed after cache reset" }

lake build
if ($LASTEXITCODE -ne 0) { throw "build failed after cache reset" }
```

Do not repair individual `.olean` files indefinitely. Once multiple dependency
headers are invalid, a full generated-cache reset is more reliable and easier to
audit.

If the official clean Linux workflow succeeds at the same source head while a
Windows cache remains corrupt, treat the workflow as the source validation and
the Windows failure as an environment problem.

# GitHub Actions equivalence

The authoritative workflow performs these steps in order:

```text
1. Clean repository checkout
2. Paper-source and theorem-surface pin verification
3. Pinned Lean installation
4. Pinned dependency resolution with cache-on-update disabled
5. Official mathlib cache retrieval
6. Full Lean build
7. Source scan for sorry/sorryAx/admit
8. Project-local axiom scan
9. Gate A theorem-axiom audit
10. Gate B theorem-axiom audit
11. RCLM/refinement/engine/bounded-seed theorem-axiom audit
12. Gate C selected quantum theorem-axiom audit
13. Artifact upload even if an earlier validation step fails
```

The workflow records:

```text
GitHub checkout commit
toolchain string
lake-manifest SHA-256
Paper I blob
Paper II blob
full build log
all source and theorem-axiom audit outputs
```

# Audit artifact verification

The artifact is named:

```text
formal-core-v2-audit-<workflow-run-id>-<attempt>
```

After downloading the ZIP, verify its external digest with the digest published by
GitHub or the corresponding closure record:

```bash
sha256sum formal-core-v2-audit-<run-id>-<attempt>.zip
```

PowerShell equivalent:

```powershell
Get-FileHash `
  .\formal-core-v2-audit-<run-id>-<attempt>.zip `
  -Algorithm SHA256
```

The archive layout is documented in `AUDIT_ARTIFACTS.md`.

# Clean-tree expectations

Generated files should not become source claims. Before committing:

```bash
git status --short
```

The following are generated and should normally remain uncommitted:

```text
lean/rcp_rclm_formal_core_v2/.lake/
lean/rcp_rclm_formal_core_v2/audit-results/
local downloaded workflow ZIPs
local build logs outside an explicitly reviewed provenance record
```

The committed `lake-manifest.json` is not disposable generated clutter; it is part
of the reproducibility pin.

# Reproduction levels

A complete reproduction distinguishes:

| Level | Evidence |
|---|---|
| Source identity | Git commit plus paper and historical-source blob pins |
| Dependency identity | `lean-toolchain`, `lakefile.toml`, `lake-manifest.json` |
| Elaboration | Successful clean `lake build` |
| Admission policy | No `sorry`/`sorryAx`/`admit`; no project-local `axiom` declaration |
| Public theorem dependencies | Saved Gate A, Gate B, RCLM, and Gate C `#print axioms` reports |
| Paper mapping | Passing pin/surface audit plus theorem map and assumption register |
| Claim boundary | Gate closure record, exit criteria, and formalization manifest |

No single level substitutes for the others.

# What this procedure does not reproduce

This procedure does not run or validate:

```text
a v2 Python checker
a v2 generator
a v2 recursive promotion loop
an external benchmark
empirical recursive self-improvement
```

Those artifacts are not licensed by the current Formal Core v2 exit criteria.
