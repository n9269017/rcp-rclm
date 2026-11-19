"""Phase17AE fixed task interpretation and semantic novelty; no live workers.

Run one stage with --one-stage, or run the remaining sequence. A resumed
invocation requires the retained plan hash and the exact completed parent hash.
Unfinished invocation directories remain separate evidence. This does not resume
a Python/Lean process or reinterpret the completed AD acceptance contract.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys
import uuid
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'python' / f'rcp_rclm_runtime_v{v}') for v in (2, 3, 4, 5)]
from rcp_rclm_runtime_v5.phase17 import compilation_checkpoint as checkpoints
from rcp_rclm_runtime_v5.phase17 import task_interpretation_check as checker
from rcp_rclm_runtime_v5.phase17.task_interpretation import (
    BASE, FALSE_CLAIMS, prepare_task_interpretation, verify_packet_bytes, canonical, sha, require,
)
from rcp_rclm_runtime_v5.phase17.task_interpretation_lean import sources, NAMES, NEGATIVES

PLAN_SCHEMA = 'rcp-rclm.phase17ae.task-interpretation-plan.v1'
SCHEMA = 'rcp-rclm.phase17ae.task-interpretation-execution.v1'


def git(*args):
    return subprocess.check_output(['git', '--no-optional-locks', '-C', str(ROOT), *args]).decode().strip()


def source_identity():
    require(not git('status', '--porcelain'), 'clean committed AE source required')
    head, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
    subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', BASE, head], check=True)
    require(not git('diff', '--name-only', '--diff-filter=MDRTUXB', BASE, head, '--', 'python', 'lean', 'scripts'),
            'preexisting execution/formal source changed')
    return head, tree, checker.source_snapshot(ROOT)


def prepared_files(out, prepared, proof_sources):
    checkpoints._new_bytes(out / 'packet.json', prepared.packet_bytes)
    for label, raw in proof_sources.items():
        checkpoints._new_bytes(out / 'prepared' / (label + '.lean'), raw)


def setup(out, args):
    require(not out.exists(), 'new AE output required; preserve previous attempts')
    require(args.test_fixture and args.require_lean and args.lean_workspace is not None,
            'explicit retained-synthetic-fixture mode and prepared pinned Lean workspace required')
    head, tree, hashes = source_identity()
    out.mkdir(parents=True)
    prepared = prepare_task_interpretation(ROOT, out.parent.parent / (out.parent.name + "-" + out.name + "-physical"))
    proof_sources = sources(prepared, ROOT)
    prepared_files(out, prepared, proof_sources)
    environment = checker.capture_environment(out / 'compiler', source_root=ROOT,
        lean_workspace=checkpoints._path(args.lean_workspace.absolute()),
        toolchain_root=args.toolchain_root.absolute() if args.toolchain_root else None)
    environment_hash = sha(checkpoints._read(out / 'compiler/environment.json'))
    plan = {'schema': PLAN_SCHEMA, 'base': BASE, 'source_commit': head, 'source_tree': tree,
            'source_sha256': hashes, 'packet_sha256': sha(prepared.packet_bytes),
            'proof_source_sha256': {n: sha(b) for n, b in proof_sources.items()},
            'environment_sha256': environment_hash,
            'selected_interpretation': prepared.packet['summary'], 'theorem_names': list(NAMES),
            'negative_controls': list(NEGATIVES), 'claims': {n: False for n in FALSE_CLAIMS},
            'fresh_worker_sessions': 0, 'fresh_live_challenges': 0,
            'old_proof_campaigns_rerun': False, 'old_acceptance_reinterpreted': False}
    require(source_identity() == (head, tree, hashes), 'source changed during AE preparation')
    checkpoints._new_json(out / 'plan.json', plan)
    digest = sha(checkpoints._read(out / 'plan.json'))
    print(json.dumps({'prepared': True, 'plan_path': str(out / 'plan.json'),
                      'plan_sha256': digest, 'formal_acceptance': False}), flush=True)
    return plan, digest, environment, proof_sources


def reconstruct(out, expected_plan_hash):
    plan = checkpoints._load(out / 'plan.json', expected_plan_hash)
    require(plan['schema'] == PLAN_SCHEMA and plan['base'] == BASE, 'AE plan schema/base differs')
    head, tree, hashes = source_identity()
    require((plan['source_commit'], plan['source_tree'], plan['source_sha256']) == (head, tree, hashes),
            'continuation requires the original clean tested source')
    require(plan['claims'] == {n: False for n in FALSE_CLAIMS} and
            plan['fresh_worker_sessions'] == 0 and type(plan['fresh_worker_sessions']) is int and
            plan['fresh_live_challenges'] == 0 and type(plan['fresh_live_challenges']) is int and
            plan['old_proof_campaigns_rerun'] is False and plan['old_acceptance_reinterpreted'] is False,
            'AE scope differs')
    with tempfile.TemporaryDirectory(prefix="phase17ae-reconstruction-", dir=out.parent) as temporary:
        prepared = prepare_task_interpretation(ROOT, Path(temporary) / "packages")
    verify_packet_bytes(checkpoints._read(out / 'packet.json'), prepared, expected_sha256=plan['packet_sha256'])
    proof_sources = sources(prepared, ROOT)
    require(plan['proof_source_sha256'] == {n: sha(b) for n, b in proof_sources.items()} and
            plan['selected_interpretation'] == prepared.packet['summary'] and
            plan['theorem_names'] == list(NAMES) and plan['negative_controls'] == list(NEGATIVES),
            'AE deterministic reconstruction differs')
    require({p.name for p in (out / 'prepared').iterdir()} == {n + '.lean' for n in proof_sources},
            'AE prepared-source inventory differs')
    for label, raw in proof_sources.items():
        require(checkpoints._read(out / 'prepared' / (label + '.lean')) == raw, 'generated Lean source changed')
    raw = checkpoints._read(out / 'compiler/environment.json')
    require(sha(raw) == plan['environment_sha256'], 'compiler environment record changed')
    environment = json.loads(raw)
    checker.verify_environment(environment, ROOT)
    require(source_identity() == (head, tree, hashes), 'source changed during reconstruction')
    return plan, expected_plan_hash, environment, proof_sources


def configuration(plan, environment, proof_sources):
    return checker.configuration(source_root=ROOT, environment=environment,
        source_commit=plan['source_commit'], source_tree=plan['source_tree'],
        source_hashes=plan['source_sha256'], packet_sha256=plan['packet_sha256'],
        proof_sources=proof_sources)


def complete(out, plan, plan_hash, result, config):
    manifest = checkpoints.verify_manifest(result['manifest_path'], result['manifest_sha256'], **config)
    formal = checker.validate_lineage(manifest, config)
    require(source_identity() == (plan['source_commit'], plan['source_tree'], plan['source_sha256']),
            'source changed during selected compilation lineage')
    record = {'schema': SCHEMA, 'completed': True, 'status': 'passed',
              'completed_at_utc': datetime.now(timezone.utc).isoformat(),
              'platform': platform.system(), 'python_version': platform.python_version(),
              'plan_sha256': plan_hash, 'source_commit': plan['source_commit'],
              'source_tree': plan['source_tree'], 'source_sha256': plan['source_sha256'],
              'selected_manifest': Path(result['manifest_path']).relative_to(out).as_posix(),
              'selected_manifest_sha256': result['manifest_sha256'], 'formal': formal,
              'fixed_task_interpretation_extension_checked': True, 'semantic_novelty_guard_checked': True,
              'proof_mode': 'real_pinned_lean_completed_stage_lineage',
              'claims': {n: False for n in FALSE_CLAIMS},
              'physical_execution_attested': False, 'saved_evidence_reconstruction_required': True}
    checkpoints._new_json(out / 'execution.json', record)
    digest = sha(checkpoints._read(out / 'execution.json'))
    print(json.dumps({'completed': True, 'execution_path': str(out / 'execution.json'),
                      'execution_sha256': digest, 'formal': formal}), flush=True)
    return digest


def verify_only(out, expected_execution_hash):
    report = checkpoints._load(out / 'execution.json', expected_execution_hash)
    require(report['schema'] == SCHEMA and report['completed'] is True and report['status'] == 'passed' and
            report['proof_mode'] == 'real_pinned_lean_completed_stage_lineage' and
            report['fixed_task_interpretation_extension_checked'] is True and report['semantic_novelty_guard_checked'] is True and
            report['claims'] == {n: False for n in FALSE_CLAIMS} and report['physical_execution_attested'] is False and
            report['saved_evidence_reconstruction_required'] is True, 'AE completion scope differs')
    plan, _, environment, proof_sources = reconstruct(out, report['plan_sha256'])
    require(all(report[k] == plan[k] for k in ('source_commit', 'source_tree', 'source_sha256')),
            'execution source identity differs')
    config = configuration(plan, environment, proof_sources)
    manifest_path = out / checkpoints._relative(report['selected_manifest'])
    manifest = checkpoints.verify_manifest(manifest_path, report['selected_manifest_sha256'], **config)
    require(checker.validate_lineage(manifest, config) == report['formal'], 'reconstructed formal result differs')
    require(checkpoints._load(out / 'execution.json', expected_execution_hash) == report,
            'execution changed during reconstruction')
    print('PASS: AE fixed task interpretation and semantic novelty guard, generated proofs, compiled artifacts, exact stage lineage, named audits and designated rejections reconstructed; no compiler or worker runs', flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--test-fixture', action='store_true')
    parser.add_argument('--require-lean', action='store_true')
    parser.add_argument('--lean-workspace', type=Path)
    parser.add_argument('--toolchain-root', type=Path)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--one-stage', action='store_true')
    parser.add_argument('--resume-from', type=Path)
    parser.add_argument('--expected-parent-sha256')
    parser.add_argument('--expected-plan-sha256')
    parser.add_argument('--unresolved-invocation', action='append', default=[])
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--expected-execution-sha256')
    args = parser.parse_args(argv)
    out = checkpoints._path(args.output.absolute())
    require(out != ROOT and ROOT not in out.parents, 'external AE output required')
    if args.verify_only:
        require(args.expected_execution_sha256 and not any((args.test_fixture, args.require_lean,
            args.lean_workspace, args.toolchain_root, args.prepare_only, args.one_stage, args.resume_from,
            args.expected_parent_sha256, args.expected_plan_sha256, args.unresolved_invocation)),
            'verify-only requires only output and independently retained execution hash')
        return verify_only(out, args.expected_execution_sha256)
    require(args.expected_execution_sha256 is None, 'unused execution hash')
    require(bool(args.resume_from) == bool(args.expected_parent_sha256), 'explicit parent path and hash required together')
    require(not (args.prepare_only and (args.one_stage or args.resume_from)), 'prepare-only cannot execute or continue a stage')
    if args.expected_plan_sha256:
        require(not any((args.test_fixture, args.require_lean, args.lean_workspace, args.toolchain_root, args.prepare_only)),
                'existing plan defines immutable execution inputs')
        plan, plan_hash, environment, proof_sources = reconstruct(out, args.expected_plan_sha256)
    else:
        require(args.resume_from is None and not args.unresolved_invocation, 'continuation needs independently retained plan hash')
        plan, plan_hash, environment, proof_sources = setup(out, args)
    require(not (out / 'execution.json').exists(), 'completed gate must be verified, not continued')
    if args.prepare_only:
        return 0
    config = configuration(plan, environment, proof_sources)
    parent = checkpoints._path(args.resume_from.absolute()) if args.resume_from else None
    parent_hash = args.expected_parent_sha256
    unresolved = tuple(args.unresolved_invocation)
    if parent:
        existing = checkpoints.verify_manifest(parent, parent_hash, **config)
        checker.validate_lineage(existing, config, require_complete=False)
        if len(existing['steps']) == len(config['stages']):
            # A connection can disappear after the last atomic stage publication
            # but before the aggregate record. Preserve that completed lineage;
            # finalization performs verification and no further compilation.
            require(set(unresolved) <= set(existing['unresolved_invocations']),
                    'completed lineage cannot add unresolved invocation references during aggregation')
            require(out in parent.parents, 'aggregate finalization requires the retained local invocation copy')
            complete(out, plan, plan_hash,
                     {'manifest_path': parent, 'manifest_sha256': parent_hash}, config)
            return 0
    while True:
        result = checkpoints.run_stage(out / 'compilation', **config,
            parent_manifest=parent, expected_parent_sha256=parent_hash,
            restore_validator=checker.restore_validator(config), unresolved_invocations=unresolved)
        formal = checker.validate_lineage(result['manifest'], config, require_complete=False)
        receipt = {'schema': 'rcp-rclm.phase17ae.progress.v1', 'plan_sha256': plan_hash,
                   'manifest_path': str(result['manifest_path']), 'manifest_sha256': result['manifest_sha256'],
                   'completed_stages': result['completed_stage_count'], 'formal': formal}
        checkpoints._new_json(out / 'progress' / (result['manifest']['invocation_id'] + '.json'), receipt)
        print(json.dumps(receipt), flush=True)
        if result['all_stages_completed']:
            complete(out, plan, plan_hash, result, config)
            return 0
        if args.one_stage:
            return 0
        parent, parent_hash = result['manifest_path'], result['manifest_sha256']
        unresolved = ()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except checkpoints.StageFailure as error:
        print(json.dumps({'completed': False, 'failure': str(error),
                          'preserved_invocation': str(error.invocation)}), file=sys.stderr, flush=True)
        raise SystemExit(1)
