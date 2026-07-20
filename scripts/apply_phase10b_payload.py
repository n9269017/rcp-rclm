from __future__ import annotations

import base64
import hashlib
import io
import shutil
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

PAYLOAD_SHA256 = "33b5c2e44171e06e922989534a02908f01d46388254f76834bd0dbb731e0d47c"
BRANCH = "agent/rcp-rclm-v3-phase-10-substrate"
EXPECTED_PATHS = {
    ".github/workflows/runtime-v3-phase-10-learned.yml",
    "docs/executable_core_v3/PHASE_10_EXIT_CRITERIA.md",
    "docs/executable_core_v3/PHASE_10_LEARNED.md",
    "docs/executable_core_v3/PHASE_10_VALIDATION.md",
    "docs/executable_core_v3/README.md",
    "docs/formal_core_v3/audit/Phase10InformationAxiomAudit.lean",
    "lean/rcp_rclm_formal_core_v3/RcpRclmFormalCoreV3/Learned.lean",
    "lean/rcp_rclm_formal_core_v3/RcpRclmFormalCoreV3/Learned/Phase10Information.lean",
    "python/rcp_rclm_executable_core_v3/contract/README.md",
    "python/rcp_rclm_executable_core_v3/contract/phase_10_learned.schema.json",
    "python/rcp_rclm_runtime_v3/README.md",
    "python/rcp_rclm_runtime_v3/phase_10_learned_manifest.json",
    "python/rcp_rclm_runtime_v3/pyproject.toml",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/__init__.py",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/information.py",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/learned_data.py",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/learned_package.py",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/learned_reference.py",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/sparse_profile.py",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/tasks.py",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/training_process.py",
    "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/training_protocol.py",
    "python/rcp_rclm_runtime_v3/tests_phase10/test_learned_substrate.py",
    "python/rcp_rclm_runtime_v3/tools/phase10_training_worker.py",
    "python/rcp_rclm_runtime_v3/tools/run_phase10_lean_tasks.py",
    "python/rcp_rclm_runtime_v3/tools/run_phase10_learned_reference.py",
    "python/rcp_rclm_runtime_v3/tools/run_phase10_training_reference.py",
    "python/rcp_rclm_runtime_v3/tools/validate_phase10_learned_manifest.py",
    "python/rcp_rclm_runtime_v3/tools/validate_phase10_learned_schema.py",
    "scripts/run_phase10_learned.py",
}


def run(*args: str) -> str:
    completed = subprocess.run(args, check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def canonical_member_path(name: str) -> str | None:
    normalized = name[2:] if name.startswith("./") else name
    if normalized in {"", "."}:
        return None
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"unsafe archive path: {name}")
    if pure.as_posix() != normalized:
        raise ValueError(f"noncanonical archive path: {name}")
    return normalized


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    current_branch = run("git", "-C", str(repo_root), "branch", "--show-current")
    if current_branch != BRANCH:
        raise RuntimeError(f"expected branch {BRANCH}, found {current_branch}")

    parts_root = repo_root / ".phase10b"
    part_paths = sorted(parts_root.glob("payload.part*"), key=lambda path: path.name)
    if len(part_paths) != 7:
        raise RuntimeError(f"expected seven payload parts, found {len(part_paths)}")
    encoded = "".join(path.read_text(encoding="ascii").strip() for path in part_paths)
    payload = base64.b64decode(encoded, validate=True)
    observed = hashlib.sha256(payload).hexdigest()
    if observed != PAYLOAD_SHA256:
        raise RuntimeError(f"payload digest mismatch: {observed}")

    observed_paths: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            normalized = canonical_member_path(member.name)
            if normalized is None:
                continue
            if member.issym() or member.islnk() or member.isdev():
                raise ValueError(f"forbidden archive member type: {member.name}")
            destination = repo_root / normalized
            resolved_parent = destination.parent.resolve(strict=False)
            if repo_root.resolve() not in (resolved_parent, *resolved_parent.parents):
                raise ValueError(f"archive member escapes repository: {member.name}")
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise ValueError(f"unsupported archive member: {member.name}")
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"archive file has no payload: {member.name}")
            data = source.read()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            destination.chmod(0o644)
            observed_paths.add(normalized)

    if observed_paths != EXPECTED_PATHS:
        missing = sorted(EXPECTED_PATHS - observed_paths)
        unknown = sorted(observed_paths - EXPECTED_PATHS)
        raise RuntimeError(f"payload path mismatch; missing={missing}; unknown={unknown}")

    shutil.rmtree(parts_root)
    (repo_root / "scripts" / "apply_phase10b_payload.py").unlink()
    (repo_root / ".github" / "workflows" / "apply-phase10b-payload.yml").unlink()

    run("git", "-C", str(repo_root), "config", "user.name", "github-actions[bot]")
    run("git", "-C", str(repo_root), "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run("git", "-C", str(repo_root), "add", "-A")
    staged = run("git", "-C", str(repo_root), "diff", "--cached", "--name-only")
    if not staged:
        raise RuntimeError("payload application produced no staged changes")
    run("git", "-C", str(repo_root), "commit", "-m", "Implement Phase 10 learned execution and frontier evidence")
    run("git", "-C", str(repo_root), "push", "origin", f"HEAD:{BRANCH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
