"""Run AO's finite resident broker on inherited administrator-owned pipes."""
from pathlib import Path
import argparse
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 3, 4, 5)]
    from rcp_rclm_runtime.canonical.json import load_json_strict
    from rcp_rclm_runtime_v5.phase17.resident_broker import serve
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--config-pin', required=True)
    args = parser.parse_args()
    config = load_json_strict(args.config.read_bytes(), require_canonical=True)
    stopped = serve(config, expected_config_sha256=args.config_pin,
                    input_stream=sys.stdin.buffer, output_stream=sys.stdout.buffer)
    return 0 if stopped['completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
