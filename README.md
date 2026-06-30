# RCP/RCLM Robust Reflective Successor Verification

This repository contains the two companion papers, Lean 4 proof project, controlled reference artifacts, replay checkers, run logs, and documentation for the RCP/RCLM robust reflective successor-verification package.

## 1. What this repository contains

```text
papers/
  paper-I-rcp-math/
    main.tex
    main.pdf
    arxiv/
  paper-II-rclm-architecture/
    main.tex
    main.pdf
    arxiv/

lean/
  rcp_rclm_can_lean4/
    lakefile.toml
    lean-toolchain
    RcpRclmMech.lean
    RcpRclmMech/
      RCP.lean
      RCLM.lean
    cert/
      theorem_map.md
      mechanization_manifest.filled.json
      build_logs/
    artifacts/

artifacts/
  rcp/
    controlled_artifact.json
    checker.py
    runlog.json
    mechanization_status.json
  rclm/
    controlled_artifact.json
    checker.py
    runlog.json
    mechanization_status.json

docs/
  overview.md
  theorem_dependency_graph.md
  theorem_dependency_graph.pdf
  notation_table.md
  notation_table.pdf
  claim_boundary.md
```

## 2. Paper I / Paper II relationship

**Paper I** is the architecture-general mathematical paper. It develops the RCP/RCP-II theorem stack, including non-loss, recovery, conservative-extension algebra, direct-engine construction, seed-domain entry, successor-verification packet construction, finite/infinite certified paths, proof-carrying reference entry, controlled executable artifacts, Lean mechanization status, and the M3-Min learned-entry boundary.

**Paper II** is the architecture-instantiation paper. It realizes the Paper I theorem stack in the RSI--RCLM architecture, including typed RCLM densities, semantic coupling, verifier/trust structure, RCLM successor-verification packets, proof-carrying RCLM reference artifacts, the RCLM-to-RCP refinement, and the M3-Min learned RCLM entry audit boundary.

The two papers should be cited together when discussing the full RCP/RCLM package. Paper I may be cited independently for the architecture-general theorem stack; Paper II may be cited for the RCLM architecture realization.

## 3. Lean certificate scope

The Lean 4 project is shared by both papers. It contains two proof modules:

- `RcpRclmMech/RCP.lean`: the RCP canonical finite core.
- `RcpRclmMech/RCLM.lean`: the RCLM refinement module.

The supplied Lean certificate covers the canonical finite RCP/RCLM witness, finite checker core, and RCLM-to-RCP refinement module.

It does **not** mechanize the full 219-page mathematical paper, the full 187-page architecture paper, arbitrary learned-system entry, broad capable-agent entry, or empirical deployment claims.

Successful checked commands reported for the v5 root-module project:

```powershell
lake env lean .\RcpRclmMech\RCP.lean
lake build RcpRclmMech.RCP
lake env lean .\RcpRclmMech\RCLM.lean
lake build RcpRclmMech.RCLM
lake env lean .\RcpRclmMech.lean
lake build
```

## 4. Artifact replay instructions

### RCP controlled artifact

```bash
cd artifacts/rcp
python checker.py controlled_artifact.json
```

### RCLM controlled artifact

```bash
cd artifacts/rclm
python checker.py controlled_artifact.json
```

Expected status for both checkers: success / `ok: true`.

The replay artifacts are controlled executable references. They are not empirical validation of arbitrary trained systems or frontier-scale learned agents.

## 5. What is claimed

The papers claim a domain-relative, certificate-relative theorem stack for certified seed-library classes.

In compact form, the package supports:

- recoverable monotone self-update preservation under explicit gates;
- certified non-loss and recovery for declared protected distinctions;
- conservative-extension algebra and finite-word non-loss composition;
- direct-engine construction on declared certified domains;
- seed-domain entry and witness-library closure;
- successor-verification packet construction and finite/infinite certified trajectory closure;
- proof-carrying finite reference entry for a declared canonical class;
- controlled executable replay artifacts;
- Lean 4 checking of the canonical finite RCP/RCLM witness and refinement core;
- a minimal learned-entry boundary saying that learned systems that supply the full certificate boundary may invoke the theorem stack.

## 6. What is not claimed

The package does **not** claim:

- arbitrary-system RSI;
- universal successor trust;
- full L\"obian or Vingean reflection;
- automatic reality containment;
- frontier-scale tractability;
- broad learned-agent entry;
- empirical deployment validation;
- full mechanization of the two complete papers.

The Lean project mechanizes the narrow canonical finite proof core only.

## 7. How to build Lean

From the Lean project root:

```powershell
cd lean\rcp_rclm_can_lean4
lake env lean .\RcpRclmMech\RCP.lean
lake build RcpRclmMech.RCP
lake env lean .\RcpRclmMech\RCLM.lean
lake build RcpRclmMech.RCLM
lake env lean .\RcpRclmMech.lean
lake build
```

The project is proof-library-only and does not require building a Windows executable.

## 8. How to reproduce checker logs

For Lean logs, run:

```powershell
cd lean\rcp_rclm_can_lean4
powershell -NoProfile -ExecutionPolicy Bypass -File .\cert\run_build_and_fill_manifest.ps1
```

For RCP artifact replay:

```bash
cd artifacts/rcp
python checker.py controlled_artifact.json > runlog.new.json
```

For RCLM artifact replay:

```bash
cd artifacts/rclm
python checker.py controlled_artifact.json > runlog.new.json
```

Compare the generated logs with `runlog.json`.

## 9. How to cite

Use `CITATION.cff` for the package citation. Until arXiv IDs and a Zenodo DOI are added, cite the repository release and the two companion manuscripts:

- Paper I: *Recursive Coherence Preservation / RCP-II: A Domain-Relative Robust Reflective Successor Theorem for Certified RCP Seed-Library Classes*.
- Paper II: *RSI--RCLM Final v1: A Domain-Relative Robust Reflective Successor Theorem for Certified RCLM Seed-Library Classes*.

## License

Papers and documentation are intended to be distributed under CC BY 4.0. Lean code, Python checkers, scripts, and artifact utilities are intended to be distributed under MIT. See `LICENSE` and `LICENSES/`.
