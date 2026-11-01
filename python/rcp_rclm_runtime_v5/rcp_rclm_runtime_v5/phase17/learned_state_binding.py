"""Phase17I: measured bindings into the immutable learned-package type.

A binding certificate is NOT a LearnedAcceptedStep. The latter also needs a
specified kernel with operational solve/provenance/resource predicates and their
proofs. This module makes the projection executable and rejects composition of
witnesses from different packages, transcripts, or contracts. It has no promotion
or admission override. Every production packet is independently recomputed.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from .bootstrap import HistoricalPredecessor
from .materialized import PackageReceipt, require, sha, snapshot, verify_package
from .conservative_extension import registry_from_files
from .operational_witnesses import (PreparedOperational, prepare_operational,
                                   PLAN_CONTRACT, TOOL_CONTRACT, CONTRACT_SHA256,
                                   component_projection, _COMPONENT_PREFIXES)
from .operational_lean import render_operational, parse_audits as operational_audits
from .successor_evidence import prepare_successor, FALSE_CLAIMS, obligation_ledger

SCHEMA = 'runtime.v5.phase17.typed-learned-state-binding.v1'
FIELDS = ('modelArchitecture', 'modelWeights', 'generator', 'planner',
          'trainingPolicy', 'retrievalPolicy', 'memory', 'tokenizer',
          'verificationPolicy', 'resourcePolicy', 'selfModel')
GROUPS = (*FIELDS, 'executionContext')
GROUP_COUNTS = (1, 140, 1, 6, 3, 1, 1, 3, 1, 1, 1, 5)
ROOT_TYPE = 'RcpRclmFormalCoreV3.Learned.PackageState'
TYPE_PATH = 'lean/rcp_rclm_formal_core_v3/RcpRclmFormalCoreV3/Learned/Types.lean'
KERNEL_PATH = 'lean/rcp_rclm_formal_core_v3/RcpRclmFormalCoreV3/Learned/Kernel.lean'
CLAIMS = (*FALSE_CLAIMS, 'full_learned_semantic_refinement', 'neural_decoder_formally_verified')
MISSING = (
    'full_base_kernel_semantic_refinement',
    'kernel_frontier_soundness_and_task_meaning_binding',
    'generator_production_and_package_provenance_refinement',
    'full_goal_and_information_semantic_binding',
    'complete_resource_measurement_and_enforcement',
    'complete_operational_recursive_frontier_and_root_binding',
    'durable_fresh_challenge_and_history_consumption',
    'active_atomic_promotion_and_rollback',
)


def hash_value(value: object, label: str) -> str:
    require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None, label)
    return value


def _file_rows(rows: object, count: int) -> None:
    require(type(rows) is list and len(rows) == count, 'complete component file inventory required')
    paths = []
    for r in rows:
        require(type(r) is dict and set(r) == {'path', 'size', 'sha256'}, 'file binding fields')
        p = r['path']
        require(type(p) is str and p.startswith('base/') and not any(c in p for c in '\\:\0\r\n')
                and PurePosixPath(p).as_posix() == p and '..' not in PurePosixPath(p).parts,
                'canonical base-file path required')
        require(type(r['size']) is int and 0 <= r['size'] <= 64 * 1024 * 1024, 'bounded integer file size')
        hash_value(r['sha256'], 'file digest')
        paths.append(p)
    require(paths == sorted(set(paths)) and len({p.casefold() for p in paths}) == len(paths),
            'sorted unique component paths required')


def _state(state: object) -> None:
    require(type(state) is dict and set(state) == {'package_hash', 'base', 'capabilityFrontier',
              *FIELDS, 'executionContext'}, 'exact typed learned-state fields required')
    hash_value(state['package_hash'], 'package identity')
    require(type(state['base']) is list and 1 <= len(state['base']) <= 256, 'bounded registry required')
    for h in state['base']: hash_value(h, 'registered program identity')
    require(len(set(state['base'])) == len(state['base']), 'registry shadowing')
    ids = state['capabilityFrontier']
    require(type(ids) is list and 0 < len(ids) <= 1024 and
            all(type(s) is str and 0 < len(s) <= 180 and re.fullmatch(r'[A-Za-z0-9_.-]+', s) for s in ids) and
            ids == sorted(set(ids)),
            'canonical frontier identifiers required')
    paths = []
    for group, count in zip(GROUPS, GROUP_COUNTS, strict=True):
        _file_rows(state[group], count)
        for row in state[group]:
            inner=row['path'][5:]
            matches=[g for g,prefixes in _COMPONENT_PREFIXES.items() if any(
                inner.startswith(prefix) if prefix.endswith('/') else inner==prefix for prefix in prefixes)]
            require(matches==[group], 'file mapped to wrong learned component')
        paths.extend(r['path'] for r in state[group])
    require(len(paths) == 164 and len(set(paths)) == 164, 'base files omitted or multiply assigned')


def state_projection(files: dict[str, bytes], package_hash: str, frontier: list[str]) -> dict:
    """Project *one independently measured* package, not copied before-state rows."""
    groups = component_projection(files, files)
    require(tuple(g['component'] for g in groups) == GROUPS, 'inherited component mapping changed')
    registry = registry_from_files(files)
    result = {g['component']: g['files'] for g in groups}
    result.update(package_hash=hash_value(package_hash, 'package identity'),
                  base=[key for key, _ in registry.entries], capabilityFrontier=sorted(frontier))
    _state(result)
    return result


def admission_boundary() -> dict:
    """Inventory the actual root fields without authorizing by count or labels.

    No caller-provided pass vector, root-certificate filename or ready=True is
    accepted. A future *separate* full root verifier must discharge its predicates.
    """
    rows = obligation_ledger()
    require(len(rows) == 35, 'immutable root inventory changed')
    return {
        'status': 'blocked_missing_semantic_witnesses',
        'root_acceptance_evaluated': False,
        'authorization_issued': False,
        'root_obligation_count': 35,
        'obligations': rows,
        'missing_witness_classes': list(MISSING),
        'reason': 'typed preservation and bounded operational proofs are not a complete root accepted-step proof',
    }


@dataclass(frozen=True)
class PreparedLearnedBinding:
    packet_bytes: bytes

    def __post_init__(self) -> None:
        require(type(self.packet_bytes) is bytes and 0 < len(self.packet_bytes) <= 2*1024*1024,
                'bounded immutable typed-binding bytes required')
        p = load_json_strict(self.packet_bytes)
        require(canonical(p) == self.packet_bytes, 'canonical binding bytes required')
        check_packet(p)

    @property
    def packet(self) -> dict:
        return load_json_strict(self.packet_bytes)


def check_packet(p: dict) -> None:
    keys = {'schema_id','root_type','component_order','bindings','predecessor','candidate',
            'new_program','new_capability','component_preservation','operational_packet_sha256',
            'successor_packet_sha256','operational_contract_sha256','bounded_operational_contracts',
            'root_admission','claims','trust_boundary'}
    require(type(p) is dict and set(p) == keys and p['schema_id'] == SCHEMA and
            p['root_type'] == ROOT_TYPE and p['component_order'] == list(GROUPS), 'binding schema/type/order')
    require(p['claims'] == {k: False for k in CLAIMS} and
            all(v is False for v in p['claims'].values()), 'unsupported acceptance claim')
    require(canonical(p['root_admission']) == canonical(admission_boundary()), 'root admission may not be overridden')
    for key in ('operational_packet_sha256','successor_packet_sha256'):hash_value(p[key], 'evidence digest')
    require(p['operational_contract_sha256'] == CONTRACT_SHA256 and
            p['bounded_operational_contracts'] == [PLAN_CONTRACT, TOOL_CONTRACT], 'operational contract substituted')
    bindings=p['bindings']
    required={'historical_state_hash','predecessor_physical_hash','candidate_physical_hash',
              'transcript_sha256','program_hash','objective_hash','challenge_commitment_hash'}
    require(type(bindings) is dict and set(bindings) == required, 'exact transaction bindings')
    for value in bindings.values():hash_value(value,'transaction digest')
    before, after = p['predecessor'], p['candidate'];_state(before);_state(after)
    require(before['package_hash']==bindings['predecessor_physical_hash'] and
            after['package_hash']==bindings['candidate_physical_hash'] and
            before['package_hash']!=after['package_hash'], 'package binding mismatch')
    require(p['new_program']==bindings['program_hash'] and
            p['new_program'] not in before['base'] and
            after['base']==before['base']+[p['new_program']], 'exact fresh registry extension required')
    require(p['new_capability']=='phase17.dynamic.'+bindings['challenge_commitment_hash'] and
            p['new_capability'] not in before['capabilityFrontier'] and
            after['capabilityFrontier']==sorted(before['capabilityFrontier']+[p['new_capability']]),
            'prospective frontier relation mismatch')
    expected=[]
    for group,count in zip(GROUPS,GROUP_COUNTS,strict=True):
        require(before[group]==after[group], 'frozen learned component changed: '+group)
        expected.append({'component':group,'files':count,
                         'binding_sha256':sha(canonical(before[group])),
                         'exact_physical_bytes_compared':True,
                         'semantic_interpreter_binding_proved':False})
    require(p['component_preservation']==expected and
            all(r['exact_physical_bytes_compared'] is True and r['semantic_interpreter_binding_proved'] is False
                for r in p['component_preservation']), 'component equality witness differs')
    require(p['trust_boundary']==[
        'Python measurement and content-address/literal extraction',
        'fixed pure interpretation of the frozen learned view; no mutable hidden state',
        'external transcript anchor; hashes do not authenticate execution or chronology',
        'root semantic interpretation, operational frontier soundness, and full resources remain open'],
        'semantic claim boundary changed')


def prepare_learned_binding(before: PackageReceipt, after: PackageReceipt, parent: HistoricalPredecessor,
                            *, bundle: Path, capture: Path, transcript: bytes,
                            expected_transcript_hash: str) -> tuple[PreparedLearnedBinding, PreparedOperational]:
    """Fresh physical validation and computation; no precomputed pass report input."""
    operational = prepare_operational(before,after,parent,bundle=bundle,capture=capture,transcript=transcript,
                                      expected_transcript_hash=expected_transcript_hash)
    successor = prepare_successor(before,after,parent,bundle=bundle,capture=capture,transcript=transcript,
                                  expected_transcript_hash=expected_transcript_hash)
    o,s = operational.packet, successor.packet
    require(o['bindings']['phase17f_packet_sha256']==sha(successor.packet_bytes) and
            {k:v for k,v in o['bindings'].items() if k!='phase17f_packet_sha256'} == s['bindings'],
            'operational/successor transaction mismatch')
    pf,cf=snapshot(before.root),snapshot(after.root)
    ps=state_projection(pf,before.package_hash,s['capabilities_before'])
    cs=state_projection(cf,after.package_hash,s['capabilities_after'])
    comparisons=[]
    for group,count in zip(GROUPS,GROUP_COUNTS,strict=True):
        require(ps[group]==cs[group], 'independently projected components differ')
        for row in ps[group]:require(pf[row['path']]==cf[row['path']], 'physical bytes differ')
        comparisons.append({'component':group,'files':count,'binding_sha256':sha(canonical(ps[group])),
                            'exact_physical_bytes_compared':True,'semantic_interpreter_binding_proved':False})
    p={'schema_id':SCHEMA,'root_type':ROOT_TYPE,'component_order':list(GROUPS),
       'bindings':s['bindings'],'predecessor':ps,'candidate':cs,
       'new_program':s['bindings']['program_hash'],'new_capability':s['new_capability'],
       'component_preservation':comparisons,
       'operational_packet_sha256':sha(operational.packet_bytes),'successor_packet_sha256':sha(successor.packet_bytes),
       'operational_contract_sha256':CONTRACT_SHA256,'bounded_operational_contracts':[PLAN_CONTRACT,TOOL_CONTRACT],
       'root_admission':admission_boundary(),'claims':{k:False for k in CLAIMS},
       'trust_boundary':['Python measurement and content-address/literal extraction',
         'fixed pure interpretation of the frozen learned view; no mutable hidden state',
         'external transcript anchor; hashes do not authenticate execution or chronology',
         'root semantic interpretation, operational frontier soundness, and full resources remain open']}
    require(snapshot(before.root)==pf and snapshot(after.root)==cf,'package changed during typed projection')
    verify_package(before.root,parent,bundle,expected_package_hash=before.package_hash)
    verify_package(after.root,parent,bundle,expected_package_hash=after.package_hash,
                   transcript=transcript,expected_transcript_hash=expected_transcript_hash)
    return PreparedLearnedBinding(canonical(p)), operational


def verify_binding_packet(raw: bytes, independently_prepared: PreparedLearnedBinding, *, expected_sha256: str) -> None:
    hash_value(expected_sha256,'external binding anchor')
    require(type(raw) is bytes and sha(raw)==expected_sha256 and raw==independently_prepared.packet_bytes,
            'typed binding differs from anchored independent recomputation')


def verify_retained_operational(prepared: PreparedOperational, raw_report: bytes, *,
                                expected_sha256: str, expected_source: str) -> dict:
    """Revalidate exact retained proof evidence, never rerun or authenticate it by hash.

    The expected digest/source must come from outside the untrusted candidate.
    The public installer pins the completed Phase17H result. Other candidates
    require correspondingly verified proof evidence, not this fixture's report.
    """
    hash_value(expected_sha256,'external formal-report anchor')
    require(type(raw_report) is bytes and 0 < len(raw_report) < 4*1024*1024 and
            sha(raw_report)==expected_sha256, 'retained formal evidence identity mismatch')
    # Historical execution reports are formatted JSON. Their original byte
    # digest is checked above; do not rewrite them or relax canonical packets.
    # Duplicate keys, invalid UTF-8/BOM, floats and nonfinite values still reject.
    r=load_json_strict(raw_report, require_canonical=False)
    require(type(expected_source) is str and re.fullmatch('[0-9a-f]{40}',expected_source) and
            r.get('source_commit')==expected_source and r.get('source_unchanged') is True and
            r.get('proof_mode')=='real_pinned_lean' and r.get('local_increment_checks_passed') is True,
            'retained formal execution/source mismatch')
    g=r['plan_semantics_gate']; p=prepared.packet
    require(r['packet_sha256']==g['packet_sha256']==sha(prepared.packet_bytes) and
            r['candidate_package_hash']==p['bindings']['candidate_physical_hash'] and
            r['predecessor_package_hash']==p['bindings']['predecessor_physical_hash'] and
            r['contract_sha256']==g['contract_sha256']==CONTRACT_SHA256, 'mixed operational proof bindings')
    require(g['status']=='passed' and g['task_semantics_checked'] is True and
            type(g['proof_count']) is int and g['proof_count']==172 and
            g['negative_oracle_substitution_rejected'] is True and
            g['bounded_contracts_certified']==[PLAN_CONTRACT,TOOL_CONTRACT], 'retained operational gate not passed')
    require(g['positive_source_sha256']==sha(render_operational(prepared)) and
            g['negative_source_sha256']==sha(render_operational(prepared,negative=True)), 'retained theorem source mismatch')
    commands=g['commands']
    require(type(commands) is list and len(commands)==3 and
            [c['returncode'] for c in commands]==[0,0,1] and
            all(type(c['returncode']) is int for c in commands), 'retained compiler outcomes')
    require(not commands[0]['stderr'] and re.match(r'^Lean \(version 4\.31\.0(?:,|\))',commands[0]['stdout']),
            'retained pinned compiler version')
    for c in commands:
        for stream in ('stdout','stderr'):
            require(type(c[stream]) is str and sha(c[stream].encode('utf-8'))==c[stream+'_sha256'],
                    'retained compiler log digest differs')
    require(not commands[1]['stderr'] and operational_audits(commands[1]['stdout'])==g['theorem_axioms'],
            'retained exact theorem audit differs')
    require('error:' in commands[2]['stdout']+commands[2]['stderr'] and
            'rfl' in commands[2]['stdout']+commands[2]['stderr'], 'negative control lacks compiler rejection')
    require(r['legacy_full_recursive_tasks_recertified']==[] and r['neural_decoder_formally_verified'] is False,
            'retained proof overclaim')
    for obj in (r['claims'],g['claims']):
        require(set(obj)==set(FALSE_CLAIMS) and all(v is False for v in obj.values()), 'retained acceptance claim')
    return {'retained_report_sha256':expected_sha256,'original_source_commit':expected_source,
            'packet_sha256':sha(prepared.packet_bytes),'proofs_retained_not_rerun':172,
            'bounded_contracts':[PLAN_CONTRACT,TOOL_CONTRACT],
            'original_execution_authenticated_by_this_check':False}
