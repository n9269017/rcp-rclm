from __future__ import annotations

import runpy
from pathlib import Path


def main() -> int:
    tool = Path(__file__).with_name("run_phase16_capture.py")
    namespace = runpy.run_path(str(tool), run_name="phase16_capture_tool")
    return int(namespace["main"]())


if __name__ == "__main__":
    raise SystemExit(main())
