"""Fresh joint checking of one candidate; no historical certificate relabeling."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import re
import subprocess
import tempfile

from . import lean_frontier_gate as gate
from . import learned_binding_lean as typed_lean
from . import frontier_meaning_lean as task_lean
from . import provenance_lean as producer_lean
from .joint_evidence import PreparedJoint, CLAIMS, validate_packet
from .materialized import require, sha
from .successor_lean import string

BRIDGE_PATH = 'lean/phase17_bridge/JointEvidence.lean'
BRIDGE_SHA256 = 'fb2c7b1dc21a73ae6bcf1b2d554236d2f0569dc84568618b645a6f32cb61428d'
NEW_NAMES = tuple('Phase17Joint.' + n for n in (
    'composed_frontier_sound', 'composed_provenance_bound', 'remaining_semantics_unchanged',
    'assemble_learned_step', 'selected_shared_identity', 'selected_joint_facts'))
RECHECKED_NAMES = typed_lean.NAMES + task_lean.NAMES + producer_lean.NAMES
NAMES = RECHECKED_NAMES + NEW_NAMES
LABELS = ('Joint', 'MixedCandidate', 'MixedTranscript', 'WrongComponent', 'WrongTarget', 'SkippedPrefix')
OLD_CANDIDATE = '67a97c6d16b6097fd8f1c5e09a941d5b813dfd403e98a508491645d6aea18b65'
OLD_TRANSCRIPT = '369c30c469090fa357633aca596cb0c7ad3de31f2ecf16ca78e7699e79c79e6e'


def template(root: Path) -> bytes:
    p = root / BRIDGE_PATH
    require(p.is_file() and not p.is_symlink(), 'missing/linked joint template')
    raw = p.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'joint template differs')
    return raw


def source_bodies(raw: bytes, expected_audits: tuple[str, ...]) -> tuple[list[str], str]:
    """Hoist imports and defer audits; keep every existing definition/proof intact."""
    text = raw.decode('utf-8')
    suffix = '\n'.join('#print axioms ' + n for n in expected_audits) + '\n'
    require(text.endswith(suffix), 'unexpected component audit suffix')
    body = text[:-len(suffix)]
    imports, remaining = [], []
    leading = True
    for line in body.splitlines(keepends=True):
        if leading and line.startswith('import '):
            imports.append(line.strip())
        else:
            if line.strip(): leading = False
            require(not line.startswith('import ') and not line.startswith('#print'), 'unexpected embedded import/audit')
            remaining.append(line)
    require(bool(imports), 'component import preamble missing')
    return imports, ''.join(remaining)


def _binding(name: str, b: dict) -> str:
    fields = [('historicalState', 'historical_state_hash'), ('predecessor', 'predecessor_physical_hash'),
              ('candidate', 'candidate_physical_hash'), ('transcript', 'transcript_sha256'),
              ('program', 'program_hash'), ('objective', 'objective_hash'),
              ('challenge', 'challenge_commitment_hash')]
    return 'def ' + name + ' : Binding := { ' + ', '.join(k+' := '+string(b[v]) for k,v in fields) + ' }\n'


def render_joint(prepared: PreparedJoint, *, source_root: Path, negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedJoint and negative in (None, *LABELS[1:]), 'exact joint proof inputs')
    p = prepared.packet; validate_packet(p)
    typed, tasks, producer = prepared.components()
    originals = (
        (typed_lean.render_binding(typed, source_root=source_root, negative=negative == 'WrongComponent'), typed_lean.NAMES),
        (task_lean.render_meanings(tasks, source_root=source_root, negative='target' if negative == 'WrongTarget' else None), task_lean.NAMES),
        (producer_lean.render_provenance(producer, source_root=source_root, negative='prefix' if negative == 'SkippedPrefix' else None), producer_lean.NAMES),
    )
    imports, bodies = [], []
    for source, names in originals:
        head, body = source_bodies(source, names)
        for line in head:
            if line not in imports: imports.append(line)
        bodies.append(body)
    text = '\n'.join(imports) + '\n' + '\n'.join(bodies) + '\n' + template(source_root).decode('utf-8')
    text += '\nnamespace Phase17Joint\nset_option maxRecDepth 16384\nset_option maxHeartbeats 8000000\n'
    text += '-- Joint capsule SHA256: ' + sha(prepared.packet_bytes) + '\n'
    tb = copy.deepcopy(tasks.packet['bindings'])
    if negative == 'MixedCandidate':
        require(tb['candidate_physical_hash'] != OLD_CANDIDATE, 'candidate control must differ')
        tb['candidate_physical_hash'] = OLD_CANDIDATE
    if negative == 'MixedTranscript':
        require(tb['transcript_sha256'] != OLD_TRANSCRIPT, 'transcript control must differ')
        tb['transcript_sha256'] = OLD_TRANSCRIPT
    k = producer.packet
    pb = {'historical_state_hash': k['producer']['predecessor_state_hash'],
          'predecessor_physical_hash': k['producer']['physical_package_hash'],
          'candidate_physical_hash': k['candidate']['physical_package_hash'],
          'transcript_sha256': k['transcript_sha256'], 'program_hash': k['candidate']['program_hash'],
          'objective_hash': k['trace']['objective_hash'],
          'challenge_commitment_hash': k['trace']['current_view']['challenge_commitment_hash']}
    text += _binding('typedBinding', typed.packet['bindings'])
    text += _binding('taskBinding', tb) + _binding('producerBinding', pb)
    text += '''
theorem selected_shared_identity :
    typedBinding = taskBinding ∧ taskBinding = producerBinding ∧
    typedBinding.predecessor = Phase17LearnedBinding.observedBefore.packageHash ∧
    typedBinding.candidate = Phase17LearnedBinding.observedAfter.packageHash ∧
    producerBinding.predecessor = Phase17Provenance.selectedContext.parentPackage ∧
    producerBinding.candidate = Phase17Provenance.selectedCandidate.package ∧
    producerBinding.transcript = Phase17Provenance.selectedContext.transcriptHash ∧
    producerBinding.program = Phase17Provenance.selectedProposal.program ∧
    typedBinding.program = Phase17LearnedBinding.addedKey ∧
    Phase17LearnedBinding.addedTask = Phase17TaskMeaning.taskIds.getD 21 "" := by
  decide

theorem selected_joint_facts :
    Phase17LearnedBinding.frozenView Phase17LearnedBinding.observedAfter =
      Phase17LearnedBinding.frozenView Phase17LearnedBinding.observedBefore ∧
    (Phase17TaskMeaning.checkedFrontier Phase17TaskMeaning.beforeDeclared
      Phase17TaskMeaning.catalog Phase17TaskMeaning.before ⊆
     Phase17TaskMeaning.checkedFrontier Phase17TaskMeaning.afterDeclared
      Phase17TaskMeaning.catalog Phase17TaskMeaning.after) ∧
    (Phase17TaskMeaning.checkedFrontier Phase17TaskMeaning.beforeDeclared
      Phase17TaskMeaning.catalog Phase17TaskMeaning.before).card <
     (Phase17TaskMeaning.checkedFrontier Phase17TaskMeaning.afterDeclared
      Phase17TaskMeaning.catalog Phase17TaskMeaning.after).card ∧
    Phase17Provenance.Produced Phase17Provenance.selectedContext Phase17Provenance.selectedProposal ∧
    Phase17Provenance.CandidateMatches Phase17Provenance.selectedContext
      Phase17Provenance.selectedProposal Phase17Provenance.selectedCandidate :=
  ⟨Phase17LearnedBinding.selected_typed_binding.1,
   Phase17TaskMeaning.selected_frontier_retention,
   Phase17TaskMeaning.selected_frontier_expansion,
   Phase17Provenance.selected_provenance,
   Phase17Provenance.selected_candidate_binding⟩

end Phase17Joint
'''
    text += '\n'.join('#print axioms ' + n for n in NAMES) + '\n'
    raw = text.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', raw), 'forbidden proof token')
    return raw


def parse_audits(text: str) -> dict:
    cursor, result = 0, {}
    for name in NAMES:
        m = re.compile(r"'"+re.escape(name)+r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*", re.S).match(text, cursor)
        require(m is not None, 'exact joint audit sequence required')
        result[name] = gate._axioms(m[0], name); cursor = m.end()
    require(cursor == len(text), 'unexpected joint audit output')
    return result


def template_snapshot(root: Path) -> dict[str, str]:
    return {name: sha(fn(root)) for name, fn in (
        (BRIDGE_PATH, template), (typed_lean.BRIDGE_PATH, typed_lean.template),
        (task_lean.BRIDGE_PATH, task_lean.template), (producer_lean.BRIDGE_PATH, producer_lean.template))}


def check_joint(prepared: PreparedJoint, *, source_root: Path, lean_workspace: Path,
                toolchain_root: Path | None = None) -> dict:
    result = {'schema_id': 'runtime.v5.phase17.same-candidate-lean.v1', 'status': 'blocked',
              'packet_sha256': sha(prepared.packet_bytes), 'commands': [], 'theorem_axioms': {},
              'new_named_audits': len(NEW_NAMES), 'rechecked_named_audits': len(RECHECKED_NAMES),
              'same_candidate_composition_checked': False, 'negative_controls_rejected': [],
              'claims': {k: False for k in CLAIMS}}
    try:
        sources = {n: render_joint(prepared, source_root=source_root, negative=None if n == 'Joint' else n) for n in LABELS}
        templates = template_snapshot(source_root)
        roots = gate.root_source_fingerprint(lean_workspace)
        require({k:v['canonical_sha256'] for k,v in roots.items()} ==
                {k:v['canonical_sha256'] for k,v in gate.root_source_fingerprint(source_root).items()}, 'pinned root mismatch')
        deps = gate._dependency_state(lean_workspace)
        tool = gate.resolve_toolchain(toolchain_root); env, git = gate._lean_environment(tool)
        suffix = '.exe' if os.name == 'nt' else ''
        lean, lake = tool/'bin'/('lean'+suffix), tool/'bin'/('lake'+suffix)
        executable_hashes = {str(p):sha(gate._read_regular(p)) for p in (lean,lake,git)}
        version = gate._process([str(lean),'--version'],lean_workspace/gate.ROOT_PROJECT,env,timeout=30)
        result['commands'].append(version)
        require(version['returncode'] == 0 and not version['stderr'] and
                re.match(r'^Lean \(version 4\.31\.0(?:,|\))', version['stdout']), 'wrong pinned Lean')
        result['status'] = 'rejected'
        with tempfile.TemporaryDirectory(prefix='r17l-') as tmp:
            folder = Path(tmp).resolve(strict=True)
            argv = [str(lake),'--keep-toolchain','--no-cache','env',str(lean)]
            for label, raw in sources.items():
                path = folder/(label+'.lean'); path.write_bytes(raw)
                cmd = gate._process([*argv,str(path)],lean_workspace/gate.ROOT_PROJECT,env,timeout=1200)
                result['commands'].append(cmd)
                if label == 'Joint':
                    require(cmd['returncode'] == 0 and not cmd['stderr'], 'joint certificate rejected')
                    audits = parse_audits(cmd['stdout'])
                else:
                    diagnostic = cmd['stdout'] + cmd['stderr']
                    require(cmd['returncode'] == 1 and re.search(r'error: Tactic `decide` proved that the proposition[\s\S]*?\bis false\b', diagnostic) is not None,
                            'joint negative certificate not rejected for false proposition')
                    result['negative_controls_rejected'].append(label)
                require(path.read_bytes() == raw, 'proof source changed')
        require(roots == gate.root_source_fingerprint(lean_workspace) and deps == gate._dependency_state(lean_workspace),
                'root/dependency changed during joint gate')
        require(executable_hashes == {str(p):sha(gate._read_regular(p)) for p in (lean,lake,git)} and
                templates == template_snapshot(source_root), 'tool/template changed')
        result.update(status='passed', same_candidate_composition_checked=True, theorem_axioms=audits,
            source_sha256={k:sha(v) for k,v in sources.items()}, executable_sha256=executable_hashes,
            conditional_assembly_checked=True, remaining_semantics_preserved=True,
            full_learned_step_instantiated=False, physical_observation_refinement_proved=False,
            trusted_import_cache_assumption=True, historical_capability_reports_reassigned=False)
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        result['failure'] = {'type':type(exc).__name__, 'reason':str(exc)}
    return result
