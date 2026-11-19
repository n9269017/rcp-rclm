"""Selected native AM client operations and designated hostile requests.

The diagnostic action is selected by the trusted capture. It supplies no server
administrative capability and adds no remote protocol operation.
"""
from pathlib import Path
import argparse
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 3, 4, 5)]
    from rcp_rclm_runtime.canonical.json import load_json_strict
    from rcp_rclm_runtime_v5.phase17 import authority_transport as transport
    from rcp_rclm_runtime_v5.phase17.resource_ledger import canonical, require, sha, ResourceError
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'anchor', 'native-directory'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('commission-pin', 'root-pin', 'action', 'request-nonce'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--stale-cursor-json')
    args = parser.parse_args()
    actions = ('initial_read', 'run_one', 'stale', 'replayed_nonce',
               'forbidden_operation', 'extra_field', 'run_abandon',
               'blocked_retry', 'reconcile', 'aggregate_denial')
    require(args.action in actions, 'unknown selected client action')
    commission = load_json_strict((args.bundle / 'commission.json').read_bytes(), require_canonical=True)
    before_raw = args.anchor.read_bytes()
    before = load_json_strict(before_raw, require_canonical=True)
    client = transport.AuthorityTransportClient(commission,
        expected_commission_sha256=args.commission_pin, expected_root_pin=args.root_pin,
        anchor_path=args.anchor, host='127.0.0.1', port=args.port,
        ca_file=args.bundle / 'ca.pem', client_cert=args.bundle / 'client.pem',
        client_key=args.bundle / 'client.key', native_directory=args.native_directory / 'transport')
    result = None
    error_type = None
    request = None
    if args.action == 'initial_read':
        result = client.read()
        require(result['accepted'] is True and result['before'] == result['after'], 'read did not complete')
    elif args.action in ('run_one', 'run_abandon', 'aggregate_denial'):
        result = client.run(2, args.request_nonce, abandon_response=args.action == 'run_abandon')
        if args.action == 'run_abandon':
            require(result is None, 'abandoned response was observed')
        elif args.action == 'run_one':
            require(result['accepted'] is True, 'selected first session refused')
        else:
            require(result['accepted'] is False and result['reason'] == 'aggregate_budget_denied',
                    'selected aggregate denial differs')
    elif args.action == 'reconcile':
        result = client.reconcile()
        require(result['observed_outcome'] == 'complete' and result['pending_retained'] is False
                and result['worker_reissued'] is False, 'lost response not reconciled without reissue')
    elif args.action == 'blocked_retry':
        try:
            client.run(2, args.request_nonce)
        except ResourceError as error:
            error_type = type(error).__name__
            require('unresolved request' in str(error), 'unexpected local refusal')
        require(error_type is not None and client.sequence == 0, 'pending request allowed network retry')
    else:
        request = client._request('run', before, credits=2, request_nonce=args.request_nonce)
        if args.action == 'stale':
            require(args.stale_cursor_json is not None, 'stale cursor test input missing')
            request['expected_cursor'] = load_json_strict(args.stale_cursor_json.encode(), require_canonical=True)
        elif args.action == 'forbidden_operation':
            request['operation'] = 'finish'
        elif args.action == 'extra_field':
            request['evaluator'] = 'caller-selected-code'
        if args.action in ('forbidden_operation', 'extra_field'):
            try:
                client._exchange(request)
            except (EOFError, OSError, ValueError, ResourceError) as error:
                error_type = type(error).__name__
            require(error_type is not None, 'invalid request received an application response')
        else:
            result = client._exchange(request)
            require(result['accepted'] is False and result['reason'] == 'protocol_or_authority_refused'
                    and result['before'] == result['after'], 'stale/replayed request changed root')
    after_raw = args.anchor.read_bytes()
    after = load_json_strict(after_raw, require_canonical=True)
    if args.action in ('stale', 'replayed_nonce', 'forbidden_operation', 'extra_field', 'blocked_retry'):
        require(after_raw == before_raw, 'diagnostic refusal modified trusted anchor')
    if args.action in ('run_abandon', 'blocked_retry'):
        require(after['pending'] is not None, 'ambiguous request lost its pending record')
    record = {'schema': 'phase17am.selected-client-operation.v1', 'action': args.action,
        'request_nonce': args.request_nonce, 'anchor_before_hex': before_raw.hex(),
        'anchor_after_hex': after_raw.hex(), 'anchor_before_sha256': sha(before_raw),
        'anchor_after_sha256': sha(after_raw), 'request': request, 'result': result,
        'error_type': error_type, 'network_attempts': client.sequence, 'completed': True,
        'automatic_retries': 0, 'physical_attestation': False}
    transport._new(args.native_directory / 'operation.json', canonical(record))
    sys.stdout.buffer.write(canonical({'schema': 'phase17am.selected-client-result.v1',
        'action': args.action, 'completed': True, 'record_sha256': sha(canonical(record))}) + b'\n')
    sys.stdout.buffer.flush()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
