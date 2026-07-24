from __future__ import annotations

import argparse
from pathlib import Path

from rcp_rclm_runtime_v3.phase13.closure import close_phase13, write_phase13_exit_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ubuntu", type=Path, required=True)
    parser.add_argument("--windows", type=Path, required=True)
    parser.add_argument("--macos", type=Path, required=True)
    parser.add_argument("--pinned-ubuntu", type=Path, required=True)
    parser.add_argument("--pinned-windows", type=Path, required=True)
    parser.add_argument("--pinned-macos", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = close_phase13(
        portable_entries={
            "macos": args.macos,
            "ubuntu": args.ubuntu,
            "windows": args.windows,
        },
        pinned_entries={
            "macos": args.pinned_macos,
            "ubuntu": args.pinned_ubuntu,
            "windows": args.pinned_windows,
        },
        repo_root=args.repo_root,
        expected_source_head=args.source_head,
    )
    write_phase13_exit_report(report, args.out)
    return 0 if report.phase13_exit_closed else 1


if __name__ == "__main__":
    raise SystemExit(main())
