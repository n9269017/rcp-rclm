"""Reviewable AO external-service plans and conservative read-only preflight.

This module does not create users, change ACLs, install services, perform access
probe writes, or commission a host. Native ownership observations are useful
preflight evidence; neither a self-authored receipt nor a collection of Boolean
assertions can turn them into independent commissioning or physical currentness.
No external currentness verifier is implemented in this reference increment.
"""
from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath
import platform
import shutil
import stat
import sys

from rcp_rclm_runtime.canonical.json import load_json_strict
from .resource_ledger import canonical, digest, exact, require, sha

PLAN_SCHEMA = 'phase17ao.external-service-plan.v1'
REPORT_SCHEMA = 'phase17ao.external-service-preflight.v1'
ROLES = ('service', 'controller', 'worker')
PATH_ROLES = ('immutable_source', 'immutable_runtime', 'authority_state',
              'broker_anchor', 'client_credentials', 'external_commission', 'currentness_anchor')
GLOBAL_CLAIMS = {'independently_protected_deployment_established': False,
                 'physical_currentness_established': False,
                 'global_authority_exclusivity_established': False,
                 'complete_resource_accounting': False,
                 'promotion_authorized': False}


def _copy(value):
    return load_json_strict(canonical(value), require_canonical=True)


def _absolute(value):
    require(type(value) is str and bool(value) and
            (Path(value).is_absolute() or PureWindowsPath(value).is_absolute()),
            'external deployment paths must be absolute')
    return value


def _principal(value, platform_name):
    if value is None:
        return None
    if platform_name == 'linux':
        exact(value, {'kind', 'uid', 'gid', 'user_namespace'})
        require(value['kind'] == 'posix_uid' and type(value['uid']) is int and
                type(value['gid']) is int and 0 <= value['uid'] < 2 ** 32 and
                0 <= value['gid'] < 2 ** 32 and type(value['user_namespace']) is str and
                value['user_namespace'].startswith('user:[') and value['user_namespace'].endswith(']'),
                'actual namespace-scoped POSIX identity required')
    else:
        exact(value, {'kind', 'sid', 'machine_identity_sha256'})
        require(value['kind'] == 'windows_sid' and type(value['sid']) is str and
                value['sid'].startswith('S-1-') and len(value['sid']) <= 184,
                'native Windows service or user SID required')
        digest(value['machine_identity_sha256'])
    return _copy(value)


def make_plan(*, source_root, runtime_path, platform_name=None, principals=None,
              protected_paths=None, external_commission_sha256=None, currentness_backend=None):
    """Describe a future administrator transaction; never treat defaults as commissioned."""
    target = platform_name or ('linux' if sys.platform.startswith('linux') else 'win32')
    require(target in ('linux', 'win32'), 'supported explicit external deployment platform required')
    identities = {role: None for role in ROLES} if principals is None else principals
    paths = {role: None for role in PATH_ROLES} if protected_paths is None else dict(protected_paths)
    paths['immutable_source'] = str(Path(source_root).resolve())
    paths['immutable_runtime'] = str(Path(runtime_path).resolve())
    plan = {'schema': PLAN_SCHEMA, 'target_platform': target,
        'profile': 'administrator_commissioned_native_service',
        'principals': identities, 'protected_paths': paths,
        'external_commission_sha256': external_commission_sha256,
        'currentness_backend': currentness_backend,
        'required_native_denials': [
            'controller_read_credentials', 'controller_write_authority_state',
            'controller_write_broker_anchor', 'controller_replace_runtime',
            'controller_replace_source', 'worker_read_credentials',
            'worker_write_authority_state', 'worker_write_broker_anchor',
            'worker_replace_runtime', 'worker_replace_source'],
        'required_operator_evidence': [
            'independently_retained_commission_identity',
            'live_service_and_controller_and_worker_principals',
            'protected_runtime_source_and_all_ancestor_ownership',
            'actual_process_access_denials',
            'service_restart_with_retained_pending_state',
            'external_current_head_and_launch_fencing_receipts',
            'rollback_and_clone_threat_argument',
            'complete_campaign_accounting_and_root_acceptance'],
        'planned_host_changes': [
            'administrator_provisions_dedicated_service_and_worker_principals',
            'administrator_installs_pinned_runtime_and_source_in_protected_directories',
            'administrator_protects_private_credentials_authority_state_and_broker_anchors',
            'administrator_installs_service_and_fixed_endpoint_policy',
            'independent_operator_retains_commission_identity_and_currentness_backend'],
        'automatic_host_mutation_permitted': False, 'claims': _copy(GLOBAL_CLAIMS)}
    validate_plan(plan, expected_plan_sha256=sha(canonical(plan)))
    return plan


def validate_plan(value, *, expected_plan_sha256):
    digest(expected_plan_sha256)
    exact(value, {'schema', 'target_platform', 'profile', 'principals', 'protected_paths',
        'external_commission_sha256', 'currentness_backend', 'required_native_denials',
        'required_operator_evidence', 'planned_host_changes',
        'automatic_host_mutation_permitted', 'claims'})
    require(value['schema'] == PLAN_SCHEMA and sha(canonical(value)) == expected_plan_sha256 and
            value['profile'] == 'administrator_commissioned_native_service' and
            value['target_platform'] in ('linux', 'win32'), 'external deployment plan identity differs')
    exact(value['principals'], set(ROLES))
    for identity in value['principals'].values():
        _principal(identity, value['target_platform'])
    exact(value['protected_paths'], set(PATH_ROLES))
    for path in value['protected_paths'].values():
        if path is not None:
            _absolute(path)
    if value['external_commission_sha256'] is not None:
        digest(value['external_commission_sha256'])
    if value['currentness_backend'] is not None:
        exact(value['currentness_backend'], {'provider', 'identity_sha256', 'outside_rollback_domain'})
        require(type(value['currentness_backend']['provider']) is str and
                0 < len(value['currentness_backend']['provider']) <= 128 and
                type(value['currentness_backend']['outside_rollback_domain']) is bool,
                'bounded external currentness provider declaration required')
        digest(value['currentness_backend']['identity_sha256'])
    require(value['automatic_host_mutation_permitted'] is False and
            canonical(value['claims']) == canonical(GLOBAL_CLAIMS),
            'external plan cannot establish deployment or global physical claims')
    for key in ('required_native_denials', 'required_operator_evidence', 'planned_host_changes'):
        require(type(value[key]) is list and 0 < len(value[key]) <= 32 and
                len(set(value[key])) == len(value[key]) and
                all(type(item) is str and 0 < len(item) <= 128 for item in value[key]),
                'finite explicit external deployment requirements required')
    # These are fixed obligations, not a caller-controlled way to weaken admission.
    require(value['required_native_denials'] == [
        'controller_read_credentials', 'controller_write_authority_state',
        'controller_write_broker_anchor', 'controller_replace_runtime',
        'controller_replace_source', 'worker_read_credentials',
        'worker_write_authority_state', 'worker_write_broker_anchor',
        'worker_replace_runtime', 'worker_replace_source'], 'actual controller/worker denial inventory differs')
    return _copy(value)


def _read_small(path, maximum=16384):
    try:
        with Path(path).open('rb') as stream:
            data = stream.read(maximum + 1)
        require(len(data) <= maximum, 'native observation exceeds finite read bound')
        return data.decode('utf-8', errors='strict')
    except (OSError, UnicodeError):
        return None


def _process_identity(pid):
    require(type(pid) is int and pid > 0, 'positive native PID required')
    if not sys.platform.startswith('linux'):
        return {'pid': pid, 'observed': False, 'reason': 'native_windows_token_inspector_unimplemented'}
    status = _read_small('/proc/%d/status' % pid)
    if status is None:
        return {'pid': pid, 'observed': False, 'reason': 'native_process_unavailable'}
    fields = dict(line.split(':', 1) for line in status.splitlines() if ':' in line)
    try:
        uid = [int(item) for item in fields['Uid'].split()]
        gid = [int(item) for item in fields['Gid'].split()]
        namespace = os.readlink('/proc/%d/ns/user' % pid)
        executable = os.readlink('/proc/%d/exe' % pid)
    except (ValueError, KeyError, OSError):
        return {'pid': pid, 'observed': False, 'reason': 'native_identity_incomplete'}
    return {'pid': pid, 'observed': True, 'uids': uid, 'gids': gid,
        'identity': {'kind': 'posix_uid', 'uid': uid[1], 'gid': gid[1], 'user_namespace': namespace},
        'executable': executable, 'capabilities': {key: fields.get(key, '').strip() for key in
            ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')},
        'no_new_privs': fields.get('NoNewPrivs', '').strip(),
        'seccomp': fields.get('Seccomp', '').strip(),
        'uid_map': _read_small('/proc/%d/uid_map' % pid),
        'gid_map': _read_small('/proc/%d/gid_map' % pid)}


def observe_host():
    """Read native capability evidence without probing privilege transitions."""
    return {'schema': 'phase17ao.native-host-preflight.v1', 'platform': sys.platform,
        'system': platform.system(), 'process': _process_identity(os.getpid()),
        'tools': {name: shutil.which(name) for name in
            ('sudo', 'newuidmap', 'newgidmap', 'unshare', 'bwrap', 'setpriv', 'runuser',
             'systemctl', 'systemd-run', 'pwsh', 'powershell')},
        'system_service_manager_present': Path('/run/systemd/system').is_dir(),
        'cgroup_v2_controller_file_present': Path('/sys/fs/cgroup/cgroup.controllers').is_file(),
        'tpm_device_present': Path('/dev/tpm0').exists() or Path('/dev/tpmrm0').exists(),
        'host_configuration_changed': False, 'physical_attestation': False}


def _path_observation(name, raw_path):
    if raw_path is None:
        return {'role': name, 'path': None, 'observed': False, 'reason': 'path_not_commissioned'}
    path = Path(raw_path)
    if not path.is_absolute():
        return {'role': name, 'path': raw_path, 'observed': False, 'reason': 'foreign_platform_path'}
    chain = []
    for item in reversed((path, *path.parents)):
        try:
            info = item.lstat()
        except OSError:
            return {'role': name, 'path': raw_path, 'observed': False,
                    'reason': 'path_or_ancestor_unavailable', 'ancestors': chain}
        row = {'path': str(item), 'uid': info.st_uid, 'gid': info.st_gid,
               'mode': stat.S_IMODE(info.st_mode), 'symlink': stat.S_ISLNK(info.st_mode),
               'device': info.st_dev, 'inode': info.st_ino}
        chain.append(row)
        if row['symlink']:
            return {'role': name, 'path': raw_path, 'observed': False,
                    'reason': 'path_or_ancestor_is_symlink', 'ancestors': chain}
    return {'role': name, 'path': raw_path, 'observed': True, 'ancestors': chain,
            'effective_current_process_read_access': os.access(path, os.R_OK),
            'effective_current_process_write_access': os.access(path, os.W_OK),
            'access_queries_are_actual_denial_probes': False}


def inspect_deployment(plan, *, expected_plan_sha256, service_pid=None,
                       controller_pid=None, worker_pid=None, external_receipt=None):
    """Fail-closed native preflight; never accept self-authored external receipts."""
    plan = validate_plan(plan, expected_plan_sha256=expected_plan_sha256)
    host = observe_host(); reasons = []
    current_platform = 'linux' if sys.platform.startswith('linux') else 'win32'
    if plan['target_platform'] != current_platform:
        reasons.append('target_platform_not_exercised')
    if current_platform == 'win32':
        reasons.append('native_windows_service_token_and_dacl_verification_unimplemented')
    processes = {}
    for role, pid in zip(ROLES, (service_pid, controller_pid, worker_pid)):
        expected = plan['principals'][role]
        if expected is None:
            reasons.append(role + '_principal_not_commissioned')
        observed = {'observed': False, 'reason': 'actual_pid_not_supplied'} if pid is None else _process_identity(pid)
        processes[role] = observed
        if not observed['observed']:
            reasons.append(role + '_native_identity_not_observed')
        elif expected is None or canonical(observed['identity']) != canonical(expected):
            reasons.append(role + '_native_identity_differs_from_commission')
    identities = [processes[role].get('identity') for role in ROLES]
    known = [identity for identity in identities if identity is not None]
    if len(known) != 3 or len({canonical(identity) for identity in known}) != 3:
        reasons.append('three_distinct_native_principals_not_established')
    if len(known) == 3 and len({row.get('user_namespace') for row in known}) != 1:
        reasons.append('principal_scope_differs_namespace_labels_are_not_distinct_host_users')
    path_observations = {name: _path_observation(name, path)
                         for name, path in plan['protected_paths'].items()}
    for name, observation in path_observations.items():
        if not observation['observed']:
            reasons.append(name + '_ownership_not_observed')
            continue
        controller = plan['principals']['controller']; worker = plan['principals']['worker']
        forbidden_uids = set()
        if current_platform == 'linux':
            forbidden_uids = {identity['uid'] for identity in (controller, worker) if identity is not None}
        for ancestor in observation['ancestors']:
            if ancestor['uid'] in forbidden_uids or ancestor['mode'] & 0o022:
                reasons.append(name + '_ancestor_is_not_immutably_protected')
                break
        # The native stat chain does not enumerate POSIX ACLs or Windows DACLs.
        # An administrator's exhaustive access/probe evidence is still needed.
    if plan['external_commission_sha256'] is None:
        reasons.append('independently_retained_commission_identity_missing')
    reasons.extend(['independent_commission_authentication_not_verified',
                    'actual_controller_and_worker_denial_probes_not_executed',
                    'complete_acl_and_runtime_closure_protection_not_verified'])
    backend = plan['currentness_backend']
    if backend is None:
        reasons.append('independent_currentness_backend_missing')
    elif backend['outside_rollback_domain'] is not True:
        reasons.append('currentness_backend_shares_declared_rollback_domain')
    reasons.append('external_currentness_and_launch_fencing_verifier_unimplemented')
    if external_receipt is not None:
        reasons.append('self_supplied_external_receipt_cannot_establish_commissioning')
    reasons.extend(['complete_campaign_accounting_not_established', 'root_promotion_acceptance_not_established'])
    return {'schema': REPORT_SCHEMA, 'plan_sha256': expected_plan_sha256,
        'native_host': host, 'process_observations': processes,
        'path_observations': path_observations,
        'admitted': False, 'denial_reasons': list(dict.fromkeys(reasons)),
        'external_receipt_supplied': external_receipt is not None,
        'host_configuration_changed': False, 'service_installed': False,
        'actual_denial_probes_executed': False, 'claims': _copy(GLOBAL_CLAIMS)}


def operator_runbook(plan):
    """Concrete review sequence for the target host; no untested privilege script."""
    return {'schema': 'phase17ao.external-service-runbook.v1',
        'plan_sha256': sha(canonical(plan)), 'target_platform': plan['target_platform'],
        'steps': [
            'Review every planned path, native identity, runtime closure and host change with the administrator.',
            'Commission distinct service, controller and worker principals on the intended host.',
            'Install the pinned Python runtime and source closure under administrator-controlled immutable ancestors.',
            'Protect authority state, broker anchors and TLS credentials; keep the public commission identity independently.',
            'Install a persistent service under its dedicated principal and inspect the running native token or UID.',
            'Run retained access-denial probes under the actual controller and worker principals, including executable replacement.',
            'Exercise service restart and interrupted pending reconciliation without worker reissue or reservation refund.',
            'Commission and independently verify a durable current-head and launch-fencing backend outside the rollback domain.',
            'Retain the rollback/cloning argument, complete measured campaign accounting and immutable root acceptance evidence.',
            'Rerun read-only preflight; an AO preflight rejection remains rejection until a supported external verifier is implemented.'],
        'windows_requirement': 'SCM service lifecycle plus verified service SID/DACL and separate worker token; never execute from a controller-writable checkout.',
        'linux_requirement': 'Administrator-installed system service with distinct scoped UIDs and verified runtime/state ownership; user namespaces alone do not commission host accounts.',
        'changes_performed': [], 'claims': _copy(GLOBAL_CLAIMS)}


def reference_deployment_report(source_root, broker_commission_sha256):
    """Retain original read-only host facts and an explicitly uncommissioned plan."""
    from .resident_broker import runtime_identity
    digest(broker_commission_sha256)
    root = Path(source_root).resolve(strict=True)
    plan = make_plan(source_root=root, runtime_path=Path(sys.executable))
    pin = sha(canonical(plan))
    admission = inspect_deployment(plan, expected_plan_sha256=pin,
                                   controller_pid=os.getpid())
    result = {'schema': 'phase17ao.reference-deployment-report.v1',
        'source_root': str(root), 'runtime_sha256': runtime_identity(root),
        'broker_commission_sha256': broker_commission_sha256,
        'plan': plan, 'plan_sha256': pin, 'admission': admission,
        'runbook': operator_runbook(plan),
        'observation_scope': 'local_read_only_reference_host_preflight',
        'independent_administrator_commissioning_performed': False,
        'claims': _copy(GLOBAL_CLAIMS)}
    verify_reference_deployment_report(result, source_root=root)
    return result


def verify_reference_deployment_report(value, *, source_root):
    """Check retained structure/bindings; do not replace original native facts."""
    from .resident_broker import runtime_identity
    exact(value, {'schema', 'source_root', 'runtime_sha256', 'broker_commission_sha256',
        'plan', 'plan_sha256', 'admission', 'runbook', 'observation_scope',
        'independent_administrator_commissioning_performed', 'claims'})
    require(value['schema'] == 'phase17ao.reference-deployment-report.v1' and
            value['observation_scope'] == 'local_read_only_reference_host_preflight' and
            value['independent_administrator_commissioning_performed'] is False,
            'reference deployment observation scope differs')
    _absolute(value['source_root']); digest(value['broker_commission_sha256'])
    require(value['runtime_sha256'] == runtime_identity(source_root),
            'reference deployment runtime source binding differs')
    plan = validate_plan(value['plan'], expected_plan_sha256=value['plan_sha256'])
    require(all(identity is None for identity in plan['principals'].values()) and
            plan['external_commission_sha256'] is None and plan['currentness_backend'] is None,
            'reference preflight cannot invent independent commissioning')
    admission = value['admission']
    exact(admission, {'schema', 'plan_sha256', 'native_host', 'process_observations',
        'path_observations', 'admitted', 'denial_reasons', 'external_receipt_supplied',
        'host_configuration_changed', 'service_installed', 'actual_denial_probes_executed', 'claims'})
    require(admission['schema'] == REPORT_SCHEMA and admission['plan_sha256'] == value['plan_sha256'] and
            admission['admitted'] is False and admission['host_configuration_changed'] is False and
            admission['service_installed'] is False and admission['actual_denial_probes_executed'] is False and
            admission['external_receipt_supplied'] is False,
            'reference preflight escalates observation into deployment')
    required = {'service_principal_not_commissioned', 'controller_principal_not_commissioned',
        'worker_principal_not_commissioned', 'three_distinct_native_principals_not_established',
        'independently_retained_commission_identity_missing', 'independent_currentness_backend_missing',
        'independent_commission_authentication_not_verified',
        'actual_controller_and_worker_denial_probes_not_executed',
        'external_currentness_and_launch_fencing_verifier_unimplemented',
        'complete_campaign_accounting_not_established', 'root_promotion_acceptance_not_established'}
    require(type(admission['denial_reasons']) is list and required <= set(admission['denial_reasons']),
            'reference deployment omissions were erased')
    exact(admission['process_observations'], set(ROLES))
    exact(admission['path_observations'], set(PATH_ROLES))
    host = admission['native_host']
    exact(host, {'schema', 'platform', 'system', 'process', 'tools',
        'system_service_manager_present', 'cgroup_v2_controller_file_present',
        'tpm_device_present', 'host_configuration_changed', 'physical_attestation'})
    require(host['schema'] == 'phase17ao.native-host-preflight.v1' and
            host['host_configuration_changed'] is False and host['physical_attestation'] is False,
            'native host preflight scope differs')
    for claims in (value['claims'], admission['claims']):
        require(canonical(claims) == canonical(GLOBAL_CLAIMS),
                'reference deployment claims differ')
    require(canonical(value['runbook']) == canonical(operator_runbook(plan)),
            'reviewable external deployment obligations differ')
    return {'plan_sha256': value['plan_sha256'], 'runtime_sha256': value['runtime_sha256'],
            'admitted': False, 'native_platform': host['platform'],
            'independently_protected_deployment_established': False}
