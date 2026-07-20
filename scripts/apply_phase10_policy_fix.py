from __future__ import annotations

import subprocess
from pathlib import Path

BRANCH = "agent/rcp-rclm-v3-phase-10-substrate"


def run(*args: str) -> str:
    completed = subprocess.run(args, check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one {label} replacement, found {count}")
    return text.replace(old, new)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    branch = run("git", "-C", str(repo), "branch", "--show-current")
    if branch != BRANCH:
        raise RuntimeError(f"expected {BRANCH}, found {branch}")
    path = (
        repo
        / "python/rcp_rclm_runtime_v3/rcp_rclm_runtime_v3/phase10/promotion.py"
    )
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from rcp_rclm_runtime.torch_backend.pilot_policy import (\n"
        "    PYTORCH_PILOT_CONTROLLER_ENVIRONMENT_HASH,\n"
        "    pytorch_pilot_phase7_budget,\n"
        "    pytorch_pilot_phase7_policy,\n"
        ")\n",
        "from rcp_rclm_runtime_v3.phase10.policy import (\n"
        "    PHASE10_CONTROLLER_ENVIRONMENT_HASH,\n"
        "    phase10_phase7_budget,\n"
        "    phase10_phase7_policy,\n"
        ")\n",
        "policy import",
    )
    text = replace_once(
        text,
        "environment_hash=PYTORCH_PILOT_CONTROLLER_ENVIRONMENT_HASH,",
        "environment_hash=PHASE10_CONTROLLER_ENVIRONMENT_HASH,",
        "controller environment",
    )
    text = replace_once(
        text,
        "policy = pytorch_pilot_phase7_policy()",
        "policy = phase10_phase7_policy()",
        "policy constructor",
    )
    text = replace_once(
        text,
        "budget = pytorch_pilot_phase7_budget()",
        "budget = phase10_phase7_budget()",
        "budget constructor",
    )
    text = replace_once(
        text,
        'PHASE10_PROMOTION_POLICY_NOTE: Final[str] = (\n'
        '    "immutable_runtime_v2_pytorch_policy_reused_as_transport_only"\n'
        ')',
        'PHASE10_PROMOTION_POLICY_NOTE: Final[str] = (\n'
        '    "phase10_specific_policy_over_immutable_runtime_v2_store"\n'
        ')',
        "policy note",
    )
    path.write_text(text, encoding="utf-8", newline="\n")
    run("git", "-C", str(repo), "config", "user.name", "github-actions[bot]")
    run(
        "git",
        "-C",
        str(repo),
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    )
    run("git", "-C", str(repo), "add", str(path.relative_to(repo)))
    run(
        "git",
        "-C",
        str(repo),
        "commit",
        "-m",
        "Bind Phase 10 promotion to its exact policy",
    )
    run("git", "-C", str(repo), "push", "origin", f"HEAD:{BRANCH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
