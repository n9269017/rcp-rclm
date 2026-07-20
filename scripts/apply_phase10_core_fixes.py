from __future__ import annotations

import subprocess
from pathlib import Path

BRANCH = "agent/rcp-rclm-v3-phase-10-substrate"


def run(*args: str) -> str:
    completed = subprocess.run(args, check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def replace_exact(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(
            f"expected exactly one replacement in {path}, found {text.count(old)}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    current = run("git", "-C", str(repo), "branch", "--show-current")
    if current != BRANCH:
        raise RuntimeError(f"expected {BRANCH}, found {current}")

    lifecycle = (
        repo
        / "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/lifecycle.py"
    )
    replace_exact(
        lifecycle,
        "max_written_bytes=33_554_432,",
        "max_written_bytes=100_663_296,",
    )

    promotion = (
        repo
        / "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/promotion.py"
    )
    replace_exact(
        promotion,
        '_write_json(store_root / "phase10_promotion_report.json", result.to_json())',
        '_write_json(evidence_path.parent / "phase10_promotion_report.json", result.to_json())',
    )

    init_path = (
        repo
        / "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/__init__.py"
    )
    replace_exact(
        init_path,
        "from rcp_rclm_runtime_v3.phase10.package import (\n",
        "from rcp_rclm_runtime_v3.phase10.promotion import (\n"
        "    Phase10PromotionEvidence,\n"
        "    Phase10VerificationEvidence,\n"
        "    promote_phase10_candidate,\n"
        "    verify_phase10_candidate,\n"
        ")\n"
        "from rcp_rclm_runtime_v3.phase10.package import (\n",
    )
    replace_exact(
        init_path,
        '    "Phase10PackageReport",\n',
        '    "Phase10PackageReport",\n'
        '    "Phase10PromotionEvidence",\n'
        '    "Phase10VerificationEvidence",\n',
    )
    replace_exact(
        init_path,
        '    "phase10_phase6_budget",\n',
        '    "phase10_phase6_budget",\n'
        '    "promote_phase10_candidate",\n',
    )
    replace_exact(
        init_path,
        '    "verify_decoded_task",\n',
        '    "verify_decoded_task",\n'
        '    "verify_phase10_candidate",\n',
    )

    for relative in (
        "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/promotion_atomic.py",
        ".github/workflows/export-phase10-sources.yml",
        ".github/workflows/apply-phase10-core-fixes.yml",
        "scripts/apply_phase10_core_fixes.py",
    ):
        path = repo / relative
        if path.exists():
            path.unlink()

    run("git", "-C", str(repo), "config", "user.name", "github-actions[bot]")
    run(
        "git",
        "-C",
        str(repo),
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    )
    run("git", "-C", str(repo), "add", "-A")
    run(
        "git",
        "-C",
        str(repo),
        "commit",
        "-m",
        "Fix Phase 10 realization budget and promotion store boundary",
    )
    run("git", "-C", str(repo), "push", "origin", f"HEAD:{BRANCH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
