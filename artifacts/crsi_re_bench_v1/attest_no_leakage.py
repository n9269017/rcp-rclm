#!/usr/bin/env python3
"""Create an auditable no-leakage/no-oracle/no-manual-repair attestation.

This is a signed-by-hash operator declaration plus evidence index, not a magical
proof. The runner still requires official scorer exports, immutable source pins,
trajectories, submissions, and usage records.
"""
from __future__ import annotations

import argparse
import json
import platform
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from crsi_re_bench_schema import (
    ATTESTATION_CONFIRMATION,
    NO_LEAKAGE_FALSE_FLAGS,
    NO_LEAKAGE_TRUE_FLAGS,
    SCHEMA_VERSION,
    SUITE_NAME,
    path_hash,
    self_hash,
    utc_now,
    write_json,
)


def parse_key_value(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("evidence labels must use LABEL=PATH")
    label, path = value.split("=", 1)
    if not label.strip() or not path.strip():
        raise argparse.ArgumentTypeError("evidence labels and paths must be non-empty")
    return label.strip(), path.strip()


def build_attestation(
    operator: str,
    notes: str,
    confirmation: str,
    evidence_items: Sequence[tuple[str, str]],
    execution_host_id: Optional[str],
) -> Dict[str, Any]:
    errors: List[str] = []
    if confirmation != ATTESTATION_CONFIRMATION:
        errors.append("explicit_attestation_confirmation_missing")
    evidence = []
    for label, raw_path in evidence_items:
        path = Path(raw_path).expanduser().resolve()
        if not path.exists():
            errors.append(f"evidence_missing:{label}:{path}")
            continue
        evidence.append({
            "label": label,
            "path": str(path),
            "kind": "directory" if path.is_dir() else "file",
            "sha256": path_hash(path),
        })

    declarations: Dict[str, Any] = {key: False for key in NO_LEAKAGE_FALSE_FLAGS}
    declarations.update({key: True for key in NO_LEAKAGE_TRUE_FLAGS})
    attestation = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "resolved": True,
        "operator": operator,
        "notes": notes,
        "confirmation_token": confirmation,
        "declarations": declarations,
        "evidence": evidence,
        "execution_host": {
            "host_id": execution_host_id or socket.gethostname(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "claim_boundary": {
            "attestation_is_operator_declaration": True,
            "attestation_is_cryptographic_proof_of_no_leakage": False,
            "official_re_bench_result": False,
            "official_metr_validated_result": False,
        },
        "created_utc": utc_now(),
        "errors": errors,
        "ok": not errors,
    }
    attestation["attestation_hash"] = self_hash(attestation, "attestation_hash")
    return attestation


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a CRSI-RE-Bench no-leakage/no-oracle attestation.")
    parser.add_argument("--operator", required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument("--confirm", required=True, help=f"Must equal {ATTESTATION_CONFIRMATION}")
    parser.add_argument("--evidence", action="append", type=parse_key_value, default=[], help="Repeatable LABEL=PATH evidence item.")
    parser.add_argument("--execution-host-id", default=None)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    result = build_attestation(args.operator, args.notes, args.confirm, args.evidence, args.execution_host_id)
    write_json(args.out.resolve(), result)
    print(json.dumps({
        "ok": result["ok"],
        "out": str(args.out.resolve()),
        "attestation_hash": result["attestation_hash"],
        "evidence_count": len(result["evidence"]),
        "errors": result["errors"],
    }, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
