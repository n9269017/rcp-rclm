"""Create a reviewable AO deployment plan or inspect native preflight read-only."""
from pathlib import Path
import argparse
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 3, 4, 5)]
    from rcp_rclm_runtime.canonical.json import load_json_strict
    from rcp_rclm_runtime_v5.phase17 import commissioned_service_deployment as deployment
    from rcp_rclm_runtime_v5.phase17.resource_ledger import canonical, sha
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='operation', required=True)
    plan = commands.add_parser('plan')
    plan.add_argument('--target-platform', choices=('linux', 'win32'))
    inspect = commands.add_parser('inspect')
    inspect.add_argument('--plan', type=Path, required=True)
    inspect.add_argument('--plan-pin', required=True)
    for role in ('service', 'controller', 'worker'):
        inspect.add_argument('--' + role + '-pid', type=int)
    args = parser.parse_args()
    if args.operation == 'plan':
        value = deployment.make_plan(source_root=root, runtime_path=Path(sys.executable),
                                     platform_name=args.target_platform)
        output = {'plan': value, 'plan_sha256': sha(canonical(value)),
                  'runbook': deployment.operator_runbook(value)}
        code = 0
    else:
        value = load_json_strict(args.plan.read_bytes(), require_canonical=True)
        output = deployment.inspect_deployment(value, expected_plan_sha256=args.plan_pin,
            service_pid=args.service_pid, controller_pid=args.controller_pid, worker_pid=args.worker_pid)
        code = 0 if output['admitted'] else 2
    sys.stdout.buffer.write(canonical(output) + b'\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
