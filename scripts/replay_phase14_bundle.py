from __future__ import annotations

import runpy
from pathlib import Path


def main() -> int:
    tool = (
        Path(__file__).resolve().parents[1]
        / "python/rcp_rclm_runtime_v4/tools/replay_phase14_bundle.py"
    )
    namespace = runpy.run_path(str(tool), run_name="phase14_tool")
    return int(namespace["main"]())


if __name__ == "__main__":
    raise SystemExit(main())
