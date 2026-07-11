#!/usr/bin/env python3
"""Verify and content-address a clean checkout of the pinned official RE-Bench release."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

THIS = Path(__file__).resolve().parent
if str(THIS) not in sys.path:
    sys.path.insert(0, str(THIS))

from crsi_re_bench_schema import (
    SCHEMA_VERSION,
    SUITE_NAME,
    git_blob_sha1,
    git_tracked_files,
    git_tree_sha1,
    load_json,
    sha256_file,
    sha256_obj,
    sha256_tree,
    utc_now,
    verify_clean_checkout,
    write_json,
)


def resolve_official_release(
    *,
    official_root: Path,
    release_manifest: Mapping[str, Any],
    environment_template: Mapping[str, Any],
    scorer_template: Mapping[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    official = release_manifest["official_re_bench"]
    expected_commit = str(official["commit"])
    checkout = verify_clean_checkout(official_root, expected_commit)
    errors = list(checkout["errors"])

    top_level_files: Dict[str, Dict[str, Any]] = {}
    for name, path_key, blob_key in [
        ("readme", "readme_path", "readme_git_blob_sha1"),
        ("setup_readme", "setup_readme_path", "setup_readme_git_blob_sha1"),
        ("suite_manifest", "suite_manifest_path", "suite_manifest_git_blob_sha1"),
    ]:
        rel = str(official[path_key])
        path = official_root / rel
        row: Dict[str, Any] = {"path": rel, "exists": path.is_file()}
        if not path.is_file():
            errors.append(f"missing_official_file:{rel}")
        else:
            actual_blob = git_blob_sha1(official_root, expected_commit, rel)
            row.update({
                "git_blob_sha1": actual_blob,
                "expected_git_blob_sha1": official[blob_key],
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            })
            if actual_blob != official[blob_key]:
                errors.append(f"git_blob_mismatch:{rel}:{actual_blob}!={official[blob_key]}")
        top_level_files[name] = row

    scorer_by_id = {str(x["environment_id"]): x for x in scorer_template.get("environments", [])}
    resolved_environments = []
    resolved_scorers = []

    for item in environment_template.get("environments", []):
        env = dict(item)
        env_id = str(env["environment_id"])
        family = str(env["task_family"])
        family_root = official_root / family
        tracked = git_tracked_files(official_root, family)
        row_errors = []
        if not family_root.is_dir():
            row_errors.append(f"missing_task_family:{family}")
        if not tracked:
            row_errors.append(f"no_tracked_files:{family}")

        checked_files: Dict[str, Dict[str, Any]] = {}
        for label, path_field, blob_field in [
            ("manifest", "manifest_path", "manifest_git_blob_sha1"),
            ("implementation", "task_family_implementation_path", "task_family_implementation_git_blob_sha1"),
            ("scorer", "official_scorer_path", "official_scorer_git_blob_sha1"),
        ]:
            rel = str(env[path_field])
            path = official_root / rel
            file_row: Dict[str, Any] = {"path": rel, "exists": path.is_file()}
            if not path.is_file():
                row_errors.append(f"missing_file:{rel}")
            else:
                actual_blob = git_blob_sha1(official_root, expected_commit, rel)
                file_row.update({
                    "git_blob_sha1": actual_blob,
                    "expected_git_blob_sha1": env[blob_field],
                    "sha256": sha256_file(path),
                    "size": path.stat().st_size,
                })
                if actual_blob != env[blob_field]:
                    row_errors.append(f"git_blob_mismatch:{rel}:{actual_blob}!={env[blob_field]}")
            checked_files[label] = file_row

        tree_sha1 = git_tree_sha1(official_root, expected_commit, family) if family_root.is_dir() else None
        tree_sha256 = sha256_tree(official_root, paths=tracked) if tracked else None
        scorer_bundle = {
            "manifest_sha256": checked_files.get("manifest", {}).get("sha256"),
            "implementation_sha256": checked_files.get("implementation", {}).get("sha256"),
            "scorer_sha256": checked_files.get("scorer", {}).get("sha256"),
            "task_family_tree_sha256": tree_sha256,
        }
        resolved = {
            **env,
            "task_family_git_tree_sha1": tree_sha1,
            "task_family_tree_sha256": tree_sha256,
            "tracked_file_count": len(tracked),
            "files": checked_files,
            "scorer_bundle_sha256": sha256_obj(scorer_bundle),
            "errors": row_errors,
            "ok": not row_errors,
        }
        resolved_environments.append(resolved)
        errors.extend(f"{env_id}:{err}" for err in row_errors)

        template_scorer = scorer_by_id.get(env_id)
        if template_scorer is None:
            errors.append(f"missing_scorer_template:{env_id}")
            continue
        scorer_row = {
            **template_scorer,
            "scorer_sha256": checked_files.get("scorer", {}).get("sha256"),
            "aggregate_implementation_sha256": checked_files.get("implementation", {}).get("sha256"),
            "task_family_tree_sha256": tree_sha256,
            "scorer_bundle_sha256": sha256_obj(
                {
                    "environment_id": env_id,
                    "scorer_sha256": checked_files.get("scorer", {}).get("sha256"),
                    "aggregate_implementation_sha256": checked_files.get("implementation", {}).get("sha256"),
                    "aggregation": template_scorer.get("aggregation"),
                    "starting_score": template_scorer.get("starting_score"),
                    "reference_score": template_scorer.get("reference_score"),
                }
            ),
            "resolved": not row_errors,
        }
        resolved_scorers.append(scorer_row)

    environment_manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "kind": "resolved_official_environment_hash_manifest",
        "repository_full_name": official["repository_full_name"],
        "repository_commit": expected_commit,
        "checkout_root": str(official_root.resolve()),
        "checkout_clean": checkout["status"] == "",
        "head_matches_pinned_commit": checkout["head"] == expected_commit,
        "top_level_files": top_level_files,
        "environment_count": len(resolved_environments),
        "environments": resolved_environments,
        "errors": errors,
        "created_utc": utc_now(),
    }
    environment_manifest["ok"] = not errors and len(resolved_environments) == 7
    environment_manifest["manifest_hash"] = sha256_obj({k: v for k, v in environment_manifest.items() if k != "manifest_hash"})

    scorer_manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "kind": "resolved_official_scorer_manifest",
        "repository_full_name": official["repository_full_name"],
        "repository_commit": expected_commit,
        "score_source_policy": scorer_template.get("score_source_policy"),
        "normalization_policy": scorer_template.get("normalization_policy"),
        "environment_count": len(resolved_scorers),
        "environments": resolved_scorers,
        "source_environment_manifest_hash": environment_manifest["manifest_hash"],
        "errors": errors,
        "created_utc": utc_now(),
    }
    scorer_manifest["ok"] = environment_manifest["ok"] and len(resolved_scorers) == 7
    scorer_manifest["manifest_hash"] = sha256_obj({k: v for k, v in scorer_manifest.items() if k != "manifest_hash"})
    return environment_manifest, scorer_manifest


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verify a clean pinned METR/RE-Bench checkout and recompute official environment/scorer hashes.")
    p.add_argument("--official-release-root", type=Path, required=True)
    p.add_argument("--release-manifest", type=Path, default=THIS / "official_release_manifest.json")
    p.add_argument("--environment-template", type=Path, default=THIS / "official_environment_hashes.json")
    p.add_argument("--scorer-template", type=Path, default=THIS / "scorer_manifest.json")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--scorer-out", type=Path, required=True)
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    official_root = args.official_release_root.resolve()
    env_manifest, scorer_manifest = resolve_official_release(
        official_root=official_root,
        release_manifest=load_json(args.release_manifest),
        environment_template=load_json(args.environment_template),
        scorer_template=load_json(args.scorer_template),
    )
    write_json(args.out, env_manifest)
    write_json(args.scorer_out, scorer_manifest)
    print(json.dumps({
        "ok": env_manifest["ok"] and scorer_manifest["ok"],
        "environment_count": env_manifest["environment_count"],
        "repository_commit": env_manifest["repository_commit"],
        "checkout_clean": env_manifest["checkout_clean"],
        "head_matches_pinned_commit": env_manifest["head_matches_pinned_commit"],
        "environment_manifest": str(args.out),
        "scorer_manifest": str(args.scorer_out),
        "errors": env_manifest["errors"],
    }, indent=2, sort_keys=True))
    return 0 if env_manifest["ok"] and scorer_manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
