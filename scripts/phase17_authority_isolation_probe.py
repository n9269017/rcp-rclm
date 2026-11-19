"""Fixed pre-exec observer for the AM Linux controller namespace profile."""
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 3, 4, 5)]
    from rcp_rclm_runtime_v5.phase17.authority_isolation import wrapper_main
    return wrapper_main()


if __name__ == '__main__':
    raise SystemExit(main())
