#!/usr/bin/env python3
"""Pin and verify a clean official METR/RE-Bench checkout.

The script refuses dirty or wrong-commit checkouts. It recomputes Git object IDs,
SHA-256 file hashes, deterministic task-family tree hashes, and scorer-bundle
hashes for all seven official environments. The output is a run-specific pin,
not an assertion that METR administered or validated the subsequent evaluation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from crsi_re_bench_schema import (
    SCHEMA_VERSION,
    SUITE_NAME,
    deterministic_tree_sha256,
    git_object_sha,
    load_json,
    self_hash,
    sha256_file,
    sha256_obj,
    utc_now,
    verify_clean_git_checkout,
    write_json,
)

THIS = Path(__file__).resolve().parent
DEFAULT_RELEASE_MANIFEST = THIS / "official_release_manifest.json"
DEFAULT_ENVIRONMENT_TEMPLATE = THIS / "official_environment_hashes.json"


def scorer_bundle_files(task_family_root: Path, declared_scorer: Path, implementation: Path, manifest: Path) -> List[Path]:
    selected = {declared_scorer.resolve(), implementation.resolve(), manifest.resolve()}
    for path in task_family_root.rglob("*"):
        if not path.is_file():
            continue
        lower = str(path.relative_to(task_family_root)).lower().replace("\\", "/")
        if "score" in path.name.lower() or "/scoring" in f"/{lower}" or path.name.lower() in {"scoring.py", "score.py"}:
            selected.add(path.resolve())
    return sorted(selected, key=lambda item: str(item).replace("\\", "/"))


def bundle_hash(paths: Sequence[Path], root: Path) -> str:
    rows = []
    for path in paths:
        rows.append({
            "path": str(path.resolve().relative_to(root.resolve())).replace("\\", "/"),
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        })
    return sha256_obj(rows)


def pin_release(
    official_root: Path,
    release_manifest_path: Path,
    environment_template_path: Path,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    release = load_json(release_manifest_path)
    template = load_json(environment_template_path)
    expected_commit = str(release["official_re_bench"]["commit"])
    checkout = verify_clean_git_checkout(official_root, expected_commit)
    errors: List[str] = list(checkout.get("errors", []))

    suite_manifest_path = official_root / str(release["official_re_bench"]["suite_manifest_path"])
    if not suite_manifest_path.is_file():
        errors.append(f"missing_suite_manifest:{suite_manifest_path}")
        suite_manifest_sha256 = None
        suite_manifest_git_blob = None
    else:
        suite_manifest_sha256 = sha256_file(suite_manifest_path)
        try:
            suite_manifest_git_blob = git_object_sha(official_root, str(release["official_re_bench"]["suite_manifest_path"]))
            expected_blob = release["official_re_bench"].get("suite_manifest_git_blob_sha1")
            if expected_blob and suite_manifest_git_blob != expected_blob:
                errors.append(f"suite_manifest_git_blob_mismatch:{suite_manifest_git_blob}!={expected_blob}")
        except Exception as exc:  # noqa: BLE001
            suite_manifest_git_blob = None
            errors.append(f"suite_manifest_git_object_error:{exc}")

    resolved_envs: List[Dict[str, Any]] = []
    scorer_entries: List[Dict[str, Any]] = []
    for index, environment in enumerate(template.get("environments", [])):
        if not isinstance(environment, Mapping):
            errors.append(f"environment_{index}:not_object")
            continue
        env = dict(environment)
        env_errors: List[str] = []
        task_family = str(env["task_family"])
        task_root = official_root / task_family
        manifest_path = official_root / str(env["manifest_path"])
        implementation_path = official_root / str(env["task_family_implementation_path"])
        scorer_path = official_root / str(env["official_scorer_path"])
        for label, path in [
            ("task_family", task_root),
            ("manifest", manifest_path),
            ("implementation", implementation_path),
            ("scorer", scorer_path),
        ]:
            if not path.exists():
                env_errors.append(f"missing_{label}:{path}")

        resolved = dict(env)
        if not env_errors:
            try:
                manifest_blob = git_object_sha(official_root, str(env["manifest_path"]))
                implementation_blob = git_object_sha(official_root, str(env["task_family_implementation_path"]))
                scorer_blob = git_object_sha(official_root, str(env["official_scorer_path"]))
                task_tree_object = git_object_sha(official_root, task_family)
                for field, actual in [
                    ("manifest_git_blob_sha1", manifest_blob),
                    ("task_family_implementation_git_blob_sha1", implementation_blob),
                    ("official_scorer_git_blob_sha1", scorer_blob),
                ]:
                    expected = env.get(field)
                    if expected and actual != expected:
                        env_errors.append(f"{field}_mismatch:{actual}!={expected}")
                scorer_files = scorer_bundle_files(task_root, scorer_path, implementation_path, manifest_path)
                resolved.update({
                    "suite_index": index,
                    "task_family_git_tree_object": task_tree_object,
                    "task_family_tree_sha256": deterministic_tree_sha256(task_root),
                    "manifest_sha256": sha256_file(manifest_path),
                    "manifest_git_blob_sha1_actual": manifest_blob,
                    "task_family_implementation_sha256": sha256_file(implementation_path),
                    "task_family_implementation_git_blob_sha1_actual": implementation_blob,
                    "official_scorer_sha256": sha256_file(scorer_path),
                    "official_scorer_git_blob_sha1_actual": scorer_blob,
                    "scorer_bundle_files": [str(path.relative_to(official_root)).replace("\\", "/") for path in scorer_files],
                    "scorer_bundle_sha256": bundle_hash(scorer_files, official_root),
                })
                scorer_entries.append({
                    "suite_index": index,
                    "environment_id": env["environment_id"],
                    "task_family": task_family,
                    "task_id": env["task_id"],
                    "official_scorer_path": env["official_scorer_path"],
                    "official_scorer_git_blob_sha1": scorer_blob,
                    "official_scorer_sha256": resolved["official_scorer_sha256"],
                    "scorer_bundle_files": resolved["scorer_bundle_files"],
                    "scorer_bundle_sha256": resolved["scorer_bundle_sha256"],
                    "raw_score_direction": env["raw_score_direction"],
                    "starting_score": env["starting_score"],
                    "reference_score": env["reference_score"],
                    "scores_must_be_scorer_produced": True,
                })
            except Exception as exc:  # noqa: BLE001
                env_errors.append(f"hashing_error:{exc}")
        resolved["errors"] = env_errors
        resolved["ok"] = not env_errors
        errors.extend(f"{env.get('environment_id', index)}:{error}" for error in env_errors)
        resolved_envs.append(resolved)

    pin = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "resolved": True,
        "source_template_path": str(environment_template_path.resolve()),
        "source_template_sha256": sha256_file(environment_template_path),
        "official_release_manifest_path": str(release_manifest_path.resolve()),
        "official_release_manifest_sha256": sha256_file(release_manifest_path),
        "repository_full_name": release["official_re_bench"]["repository_full_name"],
        "repository_commit": expected_commit,
        "checkout": checkout,
        "suite_manifest_path": release["official_re_bench"]["suite_manifest_path"],
        "suite_manifest_git_blob_sha1": suite_manifest_git_blob,
        "suite_manifest_sha256": suite_manifest_sha256,
        "environment_count": len(resolved_envs),
        "environments": resolved_envs,
        "created_utc": utc_now(),
        "errors": errors,
        "ok": checkout.get("ok") is True and len(resolved_envs) == 7 and not errors and all(env.get("ok") for env in resolved_envs),
    }
    pin["manifest_hash"] = self_hash(pin, "manifest_hash")

    scorer_manifest = {
        "schema_version": SCHEMA_VERSION,
        "suite_name": SUITE_NAME,
        "resolved": True,
        "source_kind": "official_re_bench_checkout_pin",
        "manual_or_declared_scores_accepted": False,
        "repository_full_name": release["official_re_bench"]["repository_full_name"],
        "repository_commit": expected_commit,
        "official_environment_pin_hash": pin["manifest_hash"],
        "environment_count": len(scorer_entries),
        "scorers": scorer_entries,
        "required_raw_log_provenance": "external_score_export_command",
        "created_utc": utc_now(),
        "errors": list(errors),
        "ok": pin["ok"] and len(scorer_entries) == 7,
    }
    scorer_manifest["manifest_hash"] = self_hash(scorer_manifest, "manifest_hash")
    return pin, scorer_manifest


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pin and hash a clean official METR/RE-Bench checkout.")
    parser.add_argument("--official-release-root", type=Path, required=True)
    parser.add_argument("--release-manifest", type=Path, default=DEFAULT_RELEASE_MANIFEST)
    parser.add_argument("--environment-template", type=Path, default=DEFAULT_ENVIRONMENT_TEMPLATE)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scorer-out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    pin, scorer = pin_release(
        args.official_release_root.resolve(),
        args.release_manifest.resolve(),
        args.environment_template.resolve(),
    )
    write_json(args.out.resolve(), pin)
    write_json(args.scorer_out.resolve(), scorer)
    print(json.dumps({
        "ok": pin["ok"] and scorer["ok"],
        "environment_count": pin["environment_count"],
        "official_environment_hashes": str(args.out.resolve()),
        "scorer_manifest": str(args.scorer_out.resolve()),
        "errors": pin["errors"],
    }, indent=2, sort_keys=True))
    return 0 if pin["ok"] and scorer["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
