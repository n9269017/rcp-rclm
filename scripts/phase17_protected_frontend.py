"""Bounded reference request frontend; no credentials, anchor, or endpoint input.

The trusted broker launches this process with pipes. Linux also applies the
commissioned namespace profile before this entrypoint runs. It may propose an
arbitrary bounded JSON intent; only the broker decides whether to dispatch it.
"""
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 3, 4, 5)]
    from rcp_rclm_runtime.canonical.json import load_json_strict
    from rcp_rclm_runtime_v5.phase17.resource_ledger import canonical, require
    require(len(sys.argv) == 1, 'frontend takes no paths, credentials, or endpoint arguments')
    for _ in range(2):
        raw = sys.stdin.buffer.readline(65538)
        require(raw.endswith(b'\n') and len(raw) <= 65537, 'bounded complete broker pipe message required')
        value = load_json_strict(raw[:-1], require_canonical=True)
        require(type(value) is dict and canonical(value) + b'\n' == raw, 'canonical object required')
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
