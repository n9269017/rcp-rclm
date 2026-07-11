#!/usr/bin/env python3
"""Resolve six executable package-specific agent policies and bind them to RCLM_0..RCLM_5."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

THIS = Path(__file__).resolve().parent
if str(THIS) not in sys.path:
    sys.path.insert(0, str(THIS))

from crsi_re_bench_schema import (
    SCHEMA_VERSION,
    SUITE_NAME,
    core_packages,
    git_blob_sha1,
    git_tracked_files,
    load_json,
    safe_rel,
    sha256_file,
    sha256_obj,
    sha256_tree,
    utc_now,
    validate_crsi_chain,
    verify_clean_checkout,
    write_json,
)

ALLOWED_POLICY_PROVENANCE = ("operator_declared_integration_pilot", "predecessor_generated")
PROFILE_KEYS = ("toolkit", "prompter", "generator", "discriminator", "actor")


def generate_agent_manifest(agent_root: Path, generate_manifest_path: str) -> Dict[str, Any]:
    script = agent_root / generate_manifest_path
    if not script.is_file():
        raise FileNotFoundError(f"agent manifest generator missing: {script}")
    with tempfile.TemporaryDirectory(prefix="crsi_re_bench_agent_manifest_") as temp:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=temp,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            raise RuntimeError(json.dumps({"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}, indent=2))
        manifest_path = Path(temp) / "manifest.json"
        if not manifest_path.is_file():
            raise RuntimeError("agent manifest generator did not create manifest.json")
        return load_json(manifest_path)


def find_matching_settings_pack(profile: Mapping[str, Any], generated_manifest: Mapping[str, Any]) -> List[str]:
    expected = {key: profile[key] for key in PROFILE_KEYS}
    packs = generated_manifest.get("settingsPacks", {})
    if not isinstance(packs, Mapping):
        return []
    return sorted(
        name
        for name, value in packs.items()
        if isinstance(value, Mapping) and {key: value.get(key) for key in PROFILE_KEYS} == expected
    )


def validate_generation_trace(
    trace: Mapping[str, Any],
    *,
    predecessor_id: str,
    successor_id: str,
    profile_hash: str,
) -> List[str]:
    errors: List[str] = []
    if trace.get("predecessor_successor_id") != predecessor_id:
        errors.append("predecessor_successor_id_mismatch")
    if trace.get("successor_successor_id") != successor_id:
        errors.append("successor_successor_id_mismatch")
    if trace.get("generated_profile_sha256") != profile_hash:
        errors.append("generated_profile_sha256_mismatch")
    if trace.get("generated_by_predecessor") is not True:
        errors.append("generated_by_predecessor_not_true")
    for key in ("manual_repair", "diagnostic_oracle", "hidden_reference_solution_access", "human_patch"):
        if trace.get(key) is not False:
            errors.append(f"trace_field_not_false:{key}")
    return errors


def build_manifest(
    *,
    repo_root: Path,
    chain_summary_path: Path,
    agent_root: Path,
    expected_agent_commit: str,
    policy_provenance: str,
    generation_trace_dir: Optional[Path],
    template_path: Path,
    release_manifest_path: Path,
) -> Dict[str, Any]:
    errors: List[str] = []
    if policy_provenance not in ALLOWED_POLICY_PROVENANCE:
        errors.append(f"unsupported_policy_provenance:{policy_provenance}")

    chain = load_json(chain_summary_path)
    errors.extend(validate_crsi_chain(chain))
    packages = core_packages(chain)
    template = load_json(template_path)
    release = load_json(release_manifest_path)
    agent_release = release["agent_scaffold"]

    if expected_agent_commit != agent_release["commit"]:
        errors.append("expected_agent_commit_disagrees_with_release_manifest")
    checkout = verify_clean_checkout(agent_root, expected_agent_commit)
    errors.extend(f"agent_checkout:{err}" for err in checkout["errors"])

    generate_manifest_path = str(agent_release["generate_manifest_path"])
    generated_manifest: Dict[str, Any] = {}
    if checkout["ok"]:
        actual_blob = git_blob_sha1(agent_root, expected_agent_commit, generate_manifest_path)
        if actual_blob != agent_release["generate_manifest_git_blob_sha1"]:
            errors.append("agent_generate_manifest_git_blob_mismatch")
        try:
            generated_manifest = generate_agent_manifest(agent_root, generate_manifest_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"agent_manifest_generation_failed:{exc}")

    profile_templates = template.get("profiles", [])
    if not isinstance(profile_templates, list):
        errors.append("profile_template_not_list")
        profile_templates = []
    profile_by_index = {int(item["package_index"]): item for item in profile_templates if isinstance(item, Mapping)}
    if len(packages) != len(profile_by_index):
        errors.append(f"package_profile_count_mismatch:{len(packages)}!={len(profile_by_index)}")

    tracked_agent_files = git_tracked_files(agent_root, ".") if checkout["ok"] else []
    agent_tree_hash = sha256_tree(agent_root, paths=tracked_agent_files) if tracked_agent_files else None
    resolved_profiles: List[Dict[str, Any]] = []
    profile_hashes: List[str] = []
    parent_benchmark_successor_id: Optional[str] = None

    for package_index, package in enumerate(packages):
        item = profile_by_index.get(package_index)
        if item is None:
            errors.append(f"missing_profile_template:{package_index}")
            continue
        profile_path = THIS / str(item["path"])
        if not profile_path.is_file():
            errors.append(f"missing_profile_file:{profile_path}")
            continue
        profile = load_json(profile_path)
        profile_errors: List[str] = []
        for key in PROFILE_KEYS:
            if not isinstance(profile.get(key), str) or not profile[key]:
                profile_errors.append(f"missing_or_invalid_profile_key:{key}")
        if profile.get("autosubmit") is not True:
            profile_errors.append("autosubmit_must_be_true")
        matching_packs = find_matching_settings_pack(profile, generated_manifest) if generated_manifest else []
        if not matching_packs:
            profile_errors.append("profile_not_present_in_generated_agent_manifest")
        profile_hash = sha256_obj(profile)
        profile_hashes.append(profile_hash)

        trace_path: Optional[Path] = None
        trace_hash: Optional[str] = None
        trace_errors: List[str] = []
        if policy_provenance == "predecessor_generated" and package_index > 0:
            if generation_trace_dir is None:
                trace_errors.append("generation_trace_dir_required")
            else:
                trace_path = generation_trace_dir / f"policy_generation_trace_{package_index}.json"
                if not trace_path.is_file():
                    trace_errors.append(f"missing_generation_trace:{trace_path}")
                else:
                    trace = load_json(trace_path)
                    trace_errors.extend(
                        validate_generation_trace(
                            trace,
                            predecessor_id=str(packages[package_index - 1]["successor_id"]),
                            successor_id=str(package["successor_id"]),
                            profile_hash=profile_hash,
                        )
                    )
                    trace_hash = sha256_file(trace_path)

        benchmark_payload = {
            "schema_version": SCHEMA_VERSION,
            "package_index": package_index,
            "core_successor_id": package.get("successor_id"),
            "core_manifest_hash": package.get("manifest_without_hash_sha256"),
            "core_certificate_bundle_hash": package.get("certificate_bundle_hash"),
            "agent_commit": expected_agent_commit,
            "agent_tree_sha256": agent_tree_hash,
            "profile_sha256": profile_hash,
            "policy_provenance_mode": policy_provenance,
            "policy_generation_trace_sha256": trace_hash,
            "parent_benchmark_successor_id": parent_benchmark_successor_id,
        }
        benchmark_successor_id = f"REBENCH_RCLM_{package_index}_{sha256_obj(benchmark_payload)[:24]}"
        row = {
            "package_index": package_index,
            "core_successor_id": package.get("successor_id"),
            "core_parent_successor_id": package.get("parent_successor_id"),
            "core_manifest_hash": package.get("manifest_without_hash_sha256"),
            "core_certificate_bundle_hash": package.get("certificate_bundle_hash"),
            "benchmark_successor_id": benchmark_successor_id,
            "parent_benchmark_successor_id": parent_benchmark_successor_id,
            "profile_id": item.get("profile_id"),
            "improvement_axis": item.get("improvement_axis"),
            "profile_path": safe_rel(profile_path, repo_root),
            "profile": profile,
            "profile_sha256": profile_hash,
            "matching_settings_packs": matching_packs,
            "selected_settings_pack": matching_packs[0] if matching_packs else None,
            "policy_provenance_mode": policy_provenance,
            "policy_generation_trace_path": safe_rel(trace_path, repo_root) if trace_path else None,
            "policy_generation_trace_sha256": trace_hash,
            "errors": profile_errors + trace_errors,
            "ok": not profile_errors and not trace_errors,
        }
        resolved_profiles.append(row)
        errors.extend(f"package_{package_index}:{err}" for err in row["errors"])
        parent_benchmark_successor_id = benchmark_successor_id

    if len(set(profile_hashes)) != len(profile_hashes):
        errors.append("agent_profile_hashes_not_distinct")

    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "kind": "resolved_agent_entrypoint_manifest",
        "crsi_chain_id": chain.get("chain_id"),
        "crsi_chain_summary_path": safe_rel(chain_summary_path, repo_root),
        "crsi_chain_summary_sha256": sha256_file(chain_summary_path),
        "agent_repository_full_name": agent_release["repository_full_name"],
        "agent_root": str(agent_root.resolve()),
        "agent_commit": expected_agent_commit,
        "agent_checkout_clean": checkout.get("status") == "",
        "agent_head_matches": checkout.get("head") == expected_agent_commit,
        "agent_generate_manifest_path": generate_manifest_path,
        "agent_generate_manifest_git_blob_sha1": agent_release["generate_manifest_git_blob_sha1"],
        "agent_tree_sha256": agent_tree_hash,
        "generated_agent_manifest_sha256": sha256_obj(generated_manifest) if generated_manifest else None,
        "policy_provenance_mode": policy_provenance,
        "package_count": len(packages),
        "profiles": resolved_profiles,
        "all_profiles_present": len(resolved_profiles) == len(packages),
        "all_profile_hashes_distinct": len(profile_hashes) == len(set(profile_hashes)) and bool(profile_hashes),
        "all_profiles_match_executable_agent_manifest": all(row.get("matching_settings_packs") for row in resolved_profiles),
        "errors": errors,
        "created_utc": utc_now(),
    }
    manifest["ok"] = not errors and all(row.get("ok") is True for row in resolved_profiles)
    manifest["manifest_hash"] = sha256_obj({k: v for k, v in manifest.items() if k != "manifest_hash"})
    return manifest


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bind RCLM_0..RCLM_5 to six distinct executable modular-public settings profiles.")
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    p.add_argument("--crsi-chain-summary", type=Path, required=True)
    p.add_argument("--agent-root", type=Path, required=True)
    p.add_argument("--expected-agent-commit", required=True)
    p.add_argument("--policy-provenance", choices=ALLOWED_POLICY_PROVENANCE, required=True)
    p.add_argument("--generation-trace-dir", type=Path, default=None)
    p.add_argument("--template", type=Path, default=THIS / "agent_entrypoint_manifest.json")
    p.add_argument("--release-manifest", type=Path, default=THIS / "official_release_manifest.json")
    p.add_argument("--out", type=Path, required=True)
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    chain = args.crsi_chain_summary if args.crsi_chain_summary.is_absolute() else repo_root / args.crsi_chain_summary
    agent_root = args.agent_root.resolve()
    trace_dir = args.generation_trace_dir.resolve() if args.generation_trace_dir else None
    manifest = build_manifest(
        repo_root=repo_root,
        chain_summary_path=chain,
        agent_root=agent_root,
        expected_agent_commit=args.expected_agent_commit,
        policy_provenance=args.policy_provenance,
        generation_trace_dir=trace_dir,
        template_path=args.template,
        release_manifest_path=args.release_manifest,
    )
    write_json(args.out, manifest)
    print(json.dumps({
        "ok": manifest["ok"],
        "package_count": manifest["package_count"],
        "profile_count": len(manifest["profiles"]),
        "all_profile_hashes_distinct": manifest["all_profile_hashes_distinct"],
        "policy_provenance_mode": manifest["policy_provenance_mode"],
        "manifest": str(args.out),
        "errors": manifest["errors"],
    }, indent=2, sort_keys=True))
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
