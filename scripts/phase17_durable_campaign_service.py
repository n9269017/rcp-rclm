"""Fixed local reference campaign authority; no candidate-selected execution."""
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 3, 4, 5)]
    from rcp_rclm_runtime_v5.phase17.durable_campaign_capture import serve
    return serve(root)


if __name__ == '__main__':
    raise SystemExit(main())
