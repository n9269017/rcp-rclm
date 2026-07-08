#!/usr/bin/env python3
"""Run the declared RE/METR-style CRSI external bridge attachment.

This is a one-command wrapper around:
  1. make_declared_score_ledger.py
  2. crsi_external_bridge_harness.py
  3. reproduce_external_bridge.py

The run is a declared external-fixture bridge result, not an official RE-Bench or
METR result.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

THIS = Path(__file__).resolve().parent
BRIDGE = THIS.parent


def find_repo_root(start: Optional[Path] = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for path in [cur, *cur.parents]:
        if (path / "artifacts" / "crsi_external_bridge" / "crsi_external_bridge_harness.py").exists():
            return path
    raise FileNotFoundError("Could not find repo root containing artifacts/crsi_external_bridge/crsi_external_bridge_harness.py")


def run(cmd: Sequence[str], cwd: Path) -> Dict[str, Any]:
    proc = subprocess.run(list(cmd), cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    obj: Dict[str, Any] = {"cmd": list(cmd), "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    text = proc.stdout.strip()
    if text:
        try:
            obj["json"] = json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                obj["json"] = json.loads(text[start : end + 1])
    if proc.returncode != 0:
        raise RuntimeError(json.dumps(obj, indent=2, sort_keys=True))
    return obj


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run declared RE/METR-style CRSI external bridge attachment.")
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--crsi-chain-summary", type=Path, required=True)
    p.add_argument("--outdir", type=Path, default=Path("artifacts") / "crsi_external_bridge" / "results" / "declared_re_metr_v0_k5_seed0")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    repo = find_repo_root(args.repo_root)
    chain = args.crsi_chain_summary if args.crsi_chain_summary.is_absolute() else repo / args.crsi_chain_summary
    outdir = args.outdir if args.outdir.is_absolute() else repo / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    task_manifest = THIS / "task_manifest.json"
    scorer_artifact = THIS / "scorer_artifact.json"
    make_ledger = THIS / "make_declared_score_ledger.py"
    bridge_harness = BRIDGE / "crsi_external_bridge_harness.py"
    reproduce = BRIDGE / "reproduce_external_bridge.py"

    ledger_run = run([
        sys.executable,
        str(make_ledger),
        "--crsi-chain-summary",
        str(chain),
        "--task-manifest",
        str(task_manifest),
        "--scorer-artifact",
        str(scorer_artifact),
        "--outdir",
        str(outdir),
    ], repo)

    score_ledger = outdir / "declared_re_metr_score_ledger.json"
    bridge_run = run([
        sys.executable,
        str(bridge_harness),
        "--crsi-chain-summary",
        str(chain),
        "--task-manifest",
        str(task_manifest),
        "--score-ledger",
        str(score_ledger),
        "--scorer-artifact",
        str(scorer_artifact),
        "--benchmark-id",
        "declared_re_metr_ai_rd_v0",
        "--benchmark-kind",
        "declared_re_metr_external_ai_rd_adapter",
        "--outdir",
        str(outdir),
    ], repo)

    sidecar = outdir / "crsi_external_bridge_sidecar.json"
    reproduction_run = run([
        sys.executable,
        str(reproduce),
        str(sidecar),
        "--out",
        str(outdir / "crsi_external_bridge_reproduction_report.json"),
    ], repo)

    summary = {
        "ok": bool(bridge_run.get("json", {}).get("ok") is True and reproduction_run.get("json", {}).get("ok") is True),
        "ledger_ok": bool(ledger_run.get("json", {}).get("ok") is True),
        "sidecar_ok": bool(bridge_run.get("json", {}).get("ok") is True),
        "reproduction_ok": bool(reproduction_run.get("json", {}).get("ok") is True),
        "outdir": str(outdir),
        "score_ledger": str(score_ledger),
        "sidecar": str(sidecar),
        "reproduction_report": str(outdir / "crsi_external_bridge_reproduction_report.json"),
        "claim_boundary": bridge_run.get("json", {}).get("claim_boundary", {}),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
