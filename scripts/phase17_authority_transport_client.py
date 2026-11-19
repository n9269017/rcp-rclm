"""Fixed AM controller client. This launcher cannot provision a missing anchor."""
from pathlib import Path
import argparse
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 3, 4, 5)]
    from rcp_rclm_runtime.canonical.json import load_json_strict
    from rcp_rclm_runtime_v5.phase17.authority_transport import AuthorityTransportClient
    from rcp_rclm_runtime_v5.phase17.resource_ledger import canonical, require
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('commission', 'anchor', 'ca-file', 'client-cert', 'client-key', 'native-directory'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--commission-pin', required=True)
    parser.add_argument('--root-pin', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--operation', choices=('read', 'run', 'reconcile'), required=True)
    parser.add_argument('--credits', type=int)
    parser.add_argument('--request-nonce')
    parser.add_argument('--abandon-response', action='store_true',
                        help='administrator capture of deliberately unobserved reply; no wire flag')
    args = parser.parse_args()
    require(args.operation == 'run' or (args.credits is None and args.request_nonce is None and
            not args.abandon_response), 'read-only operation supplied mutation arguments')
    require(args.operation != 'run' or (args.credits is not None and args.request_nonce is not None),
            'run requires exact credits and request nonce')
    commission = load_json_strict(args.commission.read_bytes(), require_canonical=True)
    client = AuthorityTransportClient(commission,
        expected_commission_sha256=args.commission_pin, expected_root_pin=args.root_pin,
        anchor_path=args.anchor, host='127.0.0.1', port=args.port,
        ca_file=args.ca_file, client_cert=args.client_cert, client_key=args.client_key,
        native_directory=args.native_directory)
    if args.operation == 'read':
        result = client.read()
    elif args.operation == 'run':
        result = client.run(args.credits, args.request_nonce, abandon_response=args.abandon_response)
    else:
        result = client.reconcile()
    sys.stdout.buffer.write(canonical({'schema': 'phase17am.client-result.v1',
        'operation': args.operation, 'completed': True, 'result': result,
        'abandoned_response': args.abandon_response}) + b'\n')
    sys.stdout.buffer.flush()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
