#!/usr/bin/env python3
"""Resolve six executable package-specific policies against a pinned agent checkout.

The pilot may use an explicitly operator-declared scaffold ladder. Full-suite
acceptance requires predecessor-generated policy traces. Every resolved profile
is bound to the actual recorded CRSI successor ID and a benchmark-extension hash
chain; six identical invocations cannot masquerade as six successors.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from crsi_re_bench_schema import (
    SCHEMA_VERSION,
    SUITE_NAME,
    canonical_json,
    deterministic_tree_sha256,
    git_object_sha,
    load_json,
    safe_rel,
    self_hash,
    sha256_file,
    sha256_obj,
    utc_now,
    validate_core_chain,
    verify_clean_git_checkout,
    write_json,
)

THIS = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = THIS / "agent_entrypoint_manifest.json"


def generated_agent_manifest(agent_root: Path) -> Dict[str, Any]:
    existing = agent_root / "manifest.json"
    if existing.is_file():
        return load_json(existing)
    generator = agent_root / "generate_manifest.py"
    if not generator.is_file():
        raise FileNotFoundError(f"agent manifest and generator missing under {agent_root}")
    with tempfile.TemporaryDirectory(prefix="crsi-agent-manifest-") as temp_dir:
        proc = subprocess.run(
            [sys.executable, str(generator)],
            cwd=temp_dir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"generate_manifest.py failed: {proc.stderr}")
        generated = Path(temp_dir) / "manifest.json"
        if not generated.is_file():
            raise RuntimeError("generate_manifest.py did not create manifest.json")
        return load_json(generated)


def profile_supported(profile: Mapping[str, Any], agent_manifest: Mapping[str, Any]) -> bool:
    required = ["toolkit", "prompter", "generator", "discriminator", "actor"]
    candidate = {key: profile.get(key) for key in required}
    settings_packs = agent_manifest.get("settingsPacks", {})
    if not isinstance(settings_packs, Mapping):
        return False
    for pack in settings_packs.values():
        if isinstance(pack, Mapping) and all(pack.get(key) == candidate[key] for key in required):
            return isinstance(profile.get("autosubmit", True), bool)
    return False


def load_generation_trace(
    trace_dir: Optional[Path],
    index: int,
    predecessor_id: str,
    successor_id: str,
    policy_hash: str,
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    errors: List[str] = []
    if trace_dir is None:
        return None, [f"profile_{index}:generation_trace_dir_missing"]
    path = trace_dir / f"policy_generation_trace_{index}.json"
    if not path.is_file():
        return None, [f"profile_{index}:generation_trace_missing:{path}"]
    trace = load_json(path)
    checks = {
        "predecessor_successor_id": predecessor_id,
        "successor_successor_id": successor_id,
        "generated_policy_hash": policy_hash,
    }
    for key, expected in checks.items():
        if trace.get(key) != expected:
            errors.append(f"profile_{index}:trace_{key}_mismatch")
    for key in ["manual_repair", "oracle_access", "hidden_benchmark_answer_access", "human_patch"]:
        if trace.get(key) is not False:
            errors.append(f"profile_{index}:trace_required_false:{key}")
    if trace.get("generated_by_predecessor") is not True:
        errors.append(f"profile_{index}:trace_not_predecessor_generated")
    actual_hash = sha256_file(path)
    return {
        "path": str(path.resolve()),
        "sha256": actual_hash,
        "content_hash": sha256_obj(trace),
    }, errors


def build_manifest(
    repo_root: Path,
    chain_path: Path,
    agent_root: Path,
    expected_agent_commit: str,
    template_path: Path,
    policy_provenance: str,
    generation_trace_dir: Optional[Path],
) -> Dict[str, Any]:
    chain = load_json(chain_path)
    template = load_json(template_path)
    errors = validate_core_chain(chain)
    checkout = verify_clean_git_checkout(agent_root, expected_agent_commit)
    errors.extend(checkout.get("errors", []))

    try:
        live_agent_manifest = generated_agent_manifest(agent_root)
    except Exception as exc:  # noqa: BLE001
        live_agent_manifest = {}
        errors.append(f"agent_manifest_generation_failed:{exc}")

    generate_manifest_path = agent_root / str(template["agent_repository"]["generate_manifest_path"])
    generate_blob = None
    if generate_manifest_path.is_file():
        try:
            generate_blob = git_object_sha(agent_root, str(template["agent_repository"]["generate_manifest_path"]))
            expected_blob = template["agent_repository"].get("generate_manifest_git_blob_sha1")
            if expected_blob and generate_blob != expected_blob:
                errors.append(f"agent_generate_manifest_blob_mismatch:{generate_blob}!={expected_blob}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"agent_generate_manifest_blob_error:{exc}")
    else:
        errors.append("agent_generate_manifest_missing")

    packages = chain.get("packages", []) if isinstance(chain.get("packages"), list) else []
    profiles = template.get("profiles", []) if isinstance(template.get("profiles"), list) else []
    if len(profiles) != len(packages):
        errors.append(f"template_profile_count_mismatch:{len(profiles)}!={len(packages)}")

    resolved_profiles: List[Dict[str, Any]] = []
    prior_benchmark_id: Optional[str] = None
    prior_extension_hash: Optional[str] = None
    for index, package in enumerate(packages):
        if index >= len(profiles):
            break
        profile_spec = profiles[index]
        source_path = THIS / str(profile_spec["path"])
        if not source_path.is_file():
            errors.append(f"profile_{index}:source_missing:{source_path}")
            continue
        settings = load_json(source_path)
        policy_hash = sha256_obj(settings)
        if not profile_supported(settings, live_agent_manifest):
            errors.append(f"profile_{index}:not_supported_by_pinned_agent_manifest")
        core_successor_id = str(package.get("successor_id", ""))
        extension_payload = {
            "package_index": index,
            "core_successor_id": core_successor_id,
            "core_manifest_hash": package.get("manifest_without_hash_sha256"),
            "core_certificate_bundle_hash": package.get("certificate_bundle_hash"),
            "policy_hash": policy_hash,
            "parent_benchmark_successor_id": prior_benchmark_id,
            "parent_extension_hash": prior_extension_hash,
            "policy_provenance_mode": policy_provenance,
        }
        extension_hash = sha256_obj(extension_payload)
        benchmark_successor_id = f"RE_RCLM_{index}_{extension_hash[:20]}"
        trace_record: Optional[Dict[str, Any]] = None
        if policy_provenance == "predecessor_generated" and index > 0:
            predecessor_id = str(packages[index - 1].get("successor_id", ""))
            trace_record, trace_errors = load_generation_trace(
                generation_trace_dir,
                index,
                predecessor_id,
                core_successor_id,
                policy_hash,
            )
            errors.extend(trace_errors)
        record = {
            "package_index": index,
            "profile_id": profile_spec["profile_id"],
            "improvement_axis": profile_spec["improvement_axis"],
            "source_profile_path": safe_rel(source_path, repo_root),
            "settings": settings,
            "policy_hash": policy_hash,
            "core_successor_id": core_successor_id,
            "core_manifest_hash": package.get("manifest_without_hash_sha256"),
            "core_certificate_bundle_hash": package.get("certificate_bundle_hash"),
            "parent_benchmark_successor_id": prior_benchmark_id,
            "benchmark_successor_id": benchmark_successor_id,
            "benchmark_extension_hash": extension_hash,
            "policy_provenance": policy_provenance,
            "generation_trace": trace_record,
            "supported_by_pinned_agent_manifest": profile_supported(settings, live_agent_manifest),
        }
        resolved_profiles.append(record)
        prior_benchmark_id = benchmark_successor_id
        prior_extension_hash = extension_hash

    policy_hashes = [str(record.get("policy_hash", "")) for record in resolved_profiles]
    if len(set(policy_hashes)) != len(policy_hashes):
        errors.append("resolved_policy_hashes_not_distinct")
    if policy_provenance not in {"operator_declared_integration_pilot", "predecessor_generated"}:
        errors.append("unsupported_policy_provenance")

    result = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "resolved": True,
        "policy_provenance_mode": policy_provenance,
        "pilot_only": policy_provenance == "operator_declared_integration_pilot",
        "crsi_chain_summary_path": safe_rel(chain_path, repo_root),
        "crsi_chain_summary_sha256": sha256_file(chain_path),
        "crsi_chain_id": chain.get("chain_id"),
        "agent_repository": {
            **template["agent_repository"],
            "checkout": checkout,
            "checkout_tree_sha256": deterministic_tree_sha256(agent_root),
            "generate_manifest_git_blob_sha1_actual": generate_blob,
            "generated_manifest_sha256": sha256_obj(live_agent_manifest),
            "agent_root": str(agent_root.resolve()),
        },
        "resolved_profile_count": len(resolved_profiles),
        "resolved_profiles": resolved_profiles,
        "all_profile_hashes_distinct": len(set(policy_hashes)) == len(policy_hashes) == len(packages),
        "created_utc": utc_now(),
        "errors": errors,
        "ok": checkout.get("ok") is True and len(resolved_profiles) == len(packages) and not errors,
    }
    result["manifest_hash"] = self_hash(result, "manifest_hash")
    return result


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve package-specific executable agent policies for CRSI-RE-Bench v1.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--crsi-chain-summary", type=Path, required=True)
    parser.add_argument("--agent-root", type=Path, required=True)
    parser.add_argument("--expected-agent-commit", required=True)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument(
        "--policy-provenance",
        choices=["operator_declared_integration_pilot", "predecessor_generated"],
        required=True,
    )
    parser.add_argument("--generation-trace-dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    chain_path = args.crsi_chain_summary if args.crsi_chain_summary.is_absolute() else repo_root / args.crsi_chain_summary
    agent_root = args.agent_root.resolve()
    trace_dir = args.generation_trace_dir.resolve() if args.generation_trace_dir else None
    result = build_manifest(
        repo_root,
        chain_path.resolve(),
        agent_root,
        args.expected_agent_commit,
        args.template.resolve(),
        args.policy_provenance,
        trace_dir,
    )
    write_json(args.out.resolve(), result)
    print(json.dumps({
        "ok": result["ok"],
        "resolved_profile_count": result["resolved_profile_count"],
        "policy_provenance_mode": result["policy_provenance_mode"],
        "all_profile_hashes_distinct": result["all_profile_hashes_distinct"],
        "out": str(args.out.resolve()),
        "errors": result["errors"],
    }, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
