"""Trusted AN wrapper: emit one observed boundary, then exec the fixed target."""
from pathlib import Path
import argparse
import json
import os
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'python/rcp_rclm_runtime_v5'))
    from rcp_rclm_runtime_v5.phase17 import protected_authority_isolation as boundary
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe-spec', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    spec = json.loads(args.probe_spec)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    boundary._need(command == spec['command'], 'wrapper command differs from specification')
    observed = boundary.observe_boundary(spec)
    frame = boundary.FRAME_PREFIX + boundary._canonical(observed) + b'\n'
    boundary._need(len(frame) <= boundary.MAX_BOUNDARY_BYTES, 'boundary frame exceeds profile')
    sys.stdout.buffer.write(frame); sys.stdout.buffer.flush()
    os.execv(command[0], command)


if __name__ == '__main__':
    main()
