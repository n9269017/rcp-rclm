"""Pinned Lean checking of the explicit protected sparse interpretation only."""
from __future__ import annotations
import copy
import os
from pathlib import Path
import re
import subprocess
import tempfile

from . import lean_frontier_gate as gate
from .protected_semantics import PreparedProtectedSemantics, observation_projection, CLAIMS, semantic_sources
from .materialized import require, sha
from .successor_lean import string

BRIDGE_PATH = 'lean/phase17_bridge/ProtectedSemantics.lean'
BRIDGE_SHA256 = '5b8f5bbf3806bd32659b60ce29e28c0d6b994c28ad7de5cd38a6317bab872c4b'
NAMES = tuple('Phase17Protected.' + n for n in (
    'mass_distribution_normalized', 'diagonal_density_sound', 'diagonal_information_is_kl',
    'information_sum_nonnegative', 'goal_distance_self', 'unrelated_root_fields_unchanged',
    'attached_protected_bounds', 'selected_wellformed', 'selected_targets_bound',
    'selected_observation_retained', 'selected_goal_bound', 'selected_information_bound',
    'selected_distribution_entropy_retention', 'selected_transaction_binding'))
LABELS = ('Protected', 'ChangedProbability', 'ChangedGoal', 'ChangedTarget', 'MixedCandidate')


def template(root: Path) -> bytes:
    path = root / BRIDGE_PATH
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)), 'missing/linked protected template')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'protected semantic template changed')
    return raw


def _list(value):
    if type(value) is list: return '[' + ', '.join(_list(v) for v in value) + ']'
    require(type(value) is int and 0 <= value <= (1 << 30), 'natural literal required')
    return str(value)


def _observation(name, o):
    return ('def ' + name + ' : Observation := { rows := ' + _list(o['mass_minus_one_dictionary']) +
            ', selectors := ' + _list(o['row_selectors']) + ', goals := ' + _list(o['goals']) + ' }\n')


def _contract(name, positions, goals):
    pairs = '[' + ', '.join('('+str(a)+', '+str(b)+')' for a,b in positions) + ']'
    return 'def ' + name + ' : Contract := { positions := ' + pairs + ', expectedGoals := ' + _list(goals) + ' }\n'


def render_protected(prepared: PreparedProtectedSemantics, *, source_root: Path, negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedProtectedSemantics and negative in (None,*LABELS[1:]), 'exact protected proof inputs')
    p = prepared.packet
    before = observation_projection(p['before']); after = observation_projection(p['after'])
    positions = copy.deepcopy(p['information_positions'])
    if negative == 'ChangedProbability':
        row = after['mass_minus_one_dictionary'][after['row_selectors'][positions[0][0]]]
        target = positions[0][1]
        alternative = next((j for j,w in enumerate(row) if w != row[target]), None)
        require(alternative is not None, 'nonuniform probability control required')
        row[target],row[alternative] = row[alternative],row[target]
    if negative == 'ChangedGoal': after['goals'][0][1] = (after['goals'][0][1]+1) % 256
    if negative == 'ChangedTarget': positions[0][1] = (positions[0][1]+1) % 260
    # Expected goals combine independently reopened original targets with the
    # authenticated predecessor route, not the candidate's claimed targets.
    expected_goals = [[g['effective_marker'], *t['expected_tokens']]
                      for g,t in zip(p['before']['goals'],p['task_contract']['tasks'],strict=True)]
    text = template(source_root).decode('utf-8') + '\nnamespace Phase17Protected\n'
    text += 'set_option maxRecDepth 16384\nset_option maxHeartbeats 8000000\n'
    text += '-- Prepared semantic packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    text += _observation('observedBefore', before) + _observation('observedAfter', after)
    text += _contract('selectedContract', positions, expected_goals)
    text += _contract('boundContract', p['information_positions'], expected_goals)
    order = ('historical_state_hash','predecessor_physical_hash','candidate_physical_hash','transcript_sha256',
             'program_hash','objective_hash','challenge_commitment_hash')
    expected = [p['joint_packet']['bindings'][k] for k in order] + [p['task_contract_sha256'],p['joint_packet_sha256']]
    observed = [p['bindings'][k] for k in order] + [p['task_contract_sha256'],p['joint_packet_sha256']]
    if negative == 'MixedCandidate': observed[2] = '0'*64
    text += 'def jointBinding : List String := [' + ', '.join(map(string,expected)) + ']\n'
    text += 'def semanticBinding : List String := [' + ', '.join(map(string,observed)) + ']\n'
    text += '''
theorem selected_wellformed : WellFormed observedBefore ∧ WellFormed observedAfter := by
  unfold WellFormed
  decide

theorem selected_targets_bound : selectedContract = boundContract ∧
    observedBefore.goals = boundContract.expectedGoals ∧
    boundContract.positions.length = 28 ∧
    (∀ pair ∈ boundContract.positions, pair.1 < 260 ∧ pair.2 < 260) := by decide

theorem selected_observation_retained : observedAfter = observedBefore := by decide

theorem selected_goal_bound : goalDistance observedBefore.goals observedAfter.goals ≤ 0 := by decide

theorem selected_information_bound : informationValue selectedContract observedAfter ≤
    informationValue selectedContract observedBefore + 0 := by
  rw [selected_observation_retained, add_zero]
  exact le_rfl

theorem selected_distribution_entropy_retention (current : Token) (target : List Nat) :
    (density (rowAt observedAfter current.val)).distribution =
      (density (rowAt observedBefore current.val)).distribution ∧
    RCP.QuantumFinite.vonNeumannEntropy (density (rowAt observedAfter current.val)) =
      RCP.QuantumFinite.vonNeumannEntropy (density (rowAt observedBefore current.val)) ∧
    RCP.QuantumFinite.quantumRelativeEntropy (density (rowAt observedAfter current.val)) (density target) =
      RCP.QuantumFinite.quantumRelativeEntropy (density (rowAt observedBefore current.val)) (density target) := by
  rw [selected_observation_retained]
  exact ⟨rfl, rfl, rfl⟩

theorem selected_transaction_binding : semanticBinding = jointBinding := by decide

end Phase17Protected
'''
    text += '\n'.join('#print axioms '+n for n in NAMES) + '\n'
    raw = text.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b',raw), 'forbidden proof token')
    return raw


def parse_audits(text: str) -> dict:
    cursor, result = 0, {}
    for name in NAMES:
        match = re.compile(r"'"+re.escape(name)+r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*",re.S).match(text,cursor)
        require(match is not None, 'exact protected audit sequence required')
        result[name] = gate._axioms(match[0],name); cursor = match.end()
    require(cursor == len(text), 'unexpected protected audit output')
    return result


def check_protected(prepared: PreparedProtectedSemantics, *, source_root: Path, lean_workspace: Path,
                    toolchain_root: Path | None = None) -> dict:
    result = {'schema_id':'runtime.v5.phase17.protected-semantics-lean.v1','status':'blocked',
              'packet_sha256':sha(prepared.packet_bytes),'commands':[],'theorem_axioms':{},
              'new_named_audits':len(NAMES),'negative_controls_rejected':[],
              'protected_sparse_goal_information_checked':False,
              'claims':{k:False for k in CLAIMS}}
    try:
        sources = {n:render_protected(prepared,source_root=source_root,negative=None if n=='Protected' else n) for n in LABELS}
        template_before = template(source_root); source_before = semantic_sources(source_root)
        roots = gate.root_source_fingerprint(lean_workspace)
        require({k:v['canonical_sha256'] for k,v in roots.items()} ==
                {k:v['canonical_sha256'] for k,v in gate.root_source_fingerprint(source_root).items()},'pinned root mismatch')
        deps = gate._dependency_state(lean_workspace)
        tool = gate.resolve_toolchain(toolchain_root); env, git = gate._lean_environment(tool)
        suffix = '.exe' if os.name=='nt' else ''
        lean,lake = tool/'bin'/('lean'+suffix),tool/'bin'/('lake'+suffix)
        exes = {str(p):sha(gate._read_regular(p)) for p in (lean,lake,git)}
        version = gate._process([str(lean),'--version'],lean_workspace/gate.ROOT_PROJECT,env,timeout=30)
        result['commands'].append(version)
        require(version['returncode']==0 and not version['stderr'] and
                re.match(r'^Lean \(version 4\.31\.0(?:,|\))',version['stdout']), 'wrong pinned Lean')
        result['status']='rejected'
        with tempfile.TemporaryDirectory(prefix='r17m-') as tmp:
            folder=Path(tmp).resolve(strict=True)
            for name,raw in sources.items():
                path=folder/(name+'.lean');path.write_bytes(raw)
                cmd=gate._process([str(lake),'--keep-toolchain','--no-cache','env',str(lean),str(path)],
                                  lean_workspace/gate.ROOT_PROJECT,env,timeout=1200)
                result['commands'].append(cmd)
                if name=='Protected':
                    require(cmd['returncode']==0 and not cmd['stderr'],'protected semantics certificate rejected')
                    audits=parse_audits(cmd['stdout'])
                else:
                    diagnostic=cmd['stdout']+cmd['stderr']
                    require(cmd['returncode']==1 and re.search(
                        r'error: Tactic `decide` proved that the proposition[\s\S]*?\bis false\b',diagnostic) is not None,
                        'negative control did not reject a false proposition')
                    result['negative_controls_rejected'].append(name)
                require(path.read_bytes()==raw,'proof source changed')
        require(roots==gate.root_source_fingerprint(lean_workspace) and deps==gate._dependency_state(lean_workspace),
                'root/dependency changed')
        require(exes=={str(p):sha(gate._read_regular(p)) for p in (lean,lake,git)} and
                template_before==template(source_root) and source_before==semantic_sources(source_root), 'tool/source changed')
        result.update(status='passed',protected_sparse_goal_information_checked=True,theorem_axioms=audits,
                      source_sha256={k:sha(v) for k,v in sources.items()},executable_sha256=exes,
                      full_goal_interpretation_supplied=False,full_information_interpretation_supplied=False,
                      physical_projection_formally_verified=False,full_learned_step_instantiated=False,
                      trusted_import_cache_assumption=True,prior_joint_proofs_rerun=False)
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        result['failure']={'type':type(exc).__name__,'reason':str(exc)}
    return result
