"""Administrative launcher for the loopback AM TLS authority.

The inherited stdin channel belongs to the launcher and only stops the lifetime;
network controller requests cannot initialize, reopen, export, or stop it.
"""
from pathlib import Path
import argparse
import os
import sys
import threading


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 3, 4, 5)]
    from rcp_rclm_runtime.canonical.json import load_json_strict
    from rcp_rclm_runtime_v5.phase17 import authority_transport as transport
    from rcp_rclm_runtime_v5.phase17.durable_campaign import DurableCampaignAuthority
    from rcp_rclm_runtime_v5.phase17.durable_campaign_capture import predecessor
    from rcp_rclm_runtime_v5.phase17.resource_ledger import canonical, exact, require
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('directory', 'commission', 'ca-file', 'server-cert', 'server-key', 'native-directory', 'export'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('commission-pin', 'root-pin', 'boot-nonce'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    require(not args.export.exists(), 'administrative export path must be absent')
    commission = load_json_strict(args.commission.read_bytes(), require_canonical=True)
    stop = threading.Event()
    admin = {'valid': False}

    def control():
        line = sys.stdin.buffer.readline(1025)
        try:
            require(line.endswith(b'\n') and len(line) <= 1024, 'bounded administrative stop required')
            value = load_json_strict(line[:-1], require_canonical=True)
            exact(value, {'operation'})
            require(value['operation'] == 'stop', 'unknown administrative lifetime command')
            admin['valid'] = True
        finally:
            stop.set()

    with DurableCampaignAuthority(args.directory, predecessor(str(root)),
            expected_root_provision_sha256=args.root_pin, source_root=root,
            boot_nonce=args.boot_nonce) as authority:
        service = transport.AuthorityTransportServer(authority, commission,
            expected_commission_sha256=args.commission_pin, expected_root_pin=args.root_pin,
            ca_file=args.ca_file, server_cert=args.server_cert, server_key=args.server_key,
            native_directory=args.native_directory, source_root=root, port=args.port)
        address = service.start()
        ready = {'schema': 'phase17am.authority-ready.v1', 'pid': os.getpid(),
            'address': list(address), 'commission_sha256': args.commission_pin,
            'root_provision_sha256': args.root_pin, 'cursor': authority.cursor}
        sys.stdout.buffer.write(canonical(ready) + b'\n'); sys.stdout.buffer.flush()
        thread = threading.Thread(target=control, daemon=True); thread.start()
        service.serve_forever(stop)
        require(admin['valid'], 'administrative channel ended without a valid stop')
        exported = service.export()
        transport._new(args.export, canonical(exported))
        sys.stdout.buffer.write(canonical({'schema': 'phase17am.authority-stopped.v1',
            'pid': os.getpid(), 'export_sha256': transport.sha(canonical(exported)),
            'connections': service.connection_count}) + b'\n')
        sys.stdout.buffer.flush()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
