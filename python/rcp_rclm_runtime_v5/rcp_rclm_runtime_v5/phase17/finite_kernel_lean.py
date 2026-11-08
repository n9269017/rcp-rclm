"""Render the Phase 17Q finite-observation kernel and exact selected certificate.

Old template bodies are preserved and checked in the combined new source.  Old
successful reports are not used as proofs.  Only the named Q audits are emitted.
Actual process checking lives in finite_kernel_check, not in this renderer.
"""
from __future__ import annotations

import copy
from pathlib import Path
import re

from . import joint_lean, protected_semantics_lean, resource_lean
from .finite_kernel import PreparedFiniteKernel, validate_packet
from .materialized import require, sha
from .protected_semantics import observation_projection
from .resource_ledger import Policy
from .successor_lean import program, string

BRIDGE_PATH = 'lean/phase17_bridge/FiniteObservationKernel.lean'
BRIDGE_SHA256 = '81e6371015b8f10c83312f0733a9df7b3b4a75bbbe36348e5b187dd564a60879'
NAMES = tuple('Phase17Finite.' + name for name in (
    'base', 'learned', 'protected_view_preserved', 'exact_recovery',
    'residuals_nonpositive', 'base_step', 'accepted',
    'accepted_protected_frontier', 'accepted_all_resource_dimensions',
    'selected_facts', 'selected_base_step', 'selected_learned_accepted',
    'selected_exact_recovery', 'selected_resource_totals',
))
LABELS = ('FiniteKernel', 'MixedCandidate', 'WrongParent', 'ChangedProbability',
          'OverBudget', 'OmittedCharge', 'SkippedProposal', 'WrongFrontier', 'WrongRoot')


def template(root: Path) -> bytes:
    path = root / BRIDGE_PATH
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'missing/linked finite kernel template')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == BRIDGE_SHA256, 'finite kernel template pin differs')
    return raw


def template_snapshot(root: Path) -> dict[str, str]:
    result = joint_lean.template_snapshot(root)
    result.update({protected_semantics_lean.BRIDGE_PATH: sha(protected_semantics_lean.template(root)),
                   resource_lean.TEMPLATE: sha(resource_lean.template(root)),
                   BRIDGE_PATH: sha(template(root))})
    return result


def _kinds(kinds: list[str]) -> str:
    require(type(kinds) is list and all(k in ('candidate', 'vector') for k in kinds),
            'invalid finite work kind')
    return '[' + ', '.join('.' + k for k in kinds) + ']'


def render(prepared: PreparedFiniteKernel, *, source_root: Path,
           negative: str | None = None) -> bytes:
    require(type(prepared) is PreparedFiniteKernel and negative in (None, *LABELS[1:]),
            'exact finite kernel proof inputs required')
    p = prepared.packet
    validate_packet(p)
    parts = (
        (joint_lean.render_joint(prepared.joint(), source_root=source_root), joint_lean.NAMES),
        (protected_semantics_lean.render_protected(prepared.protected(), source_root=source_root),
         protected_semantics_lean.NAMES),
        (resource_lean.template(source_root), ()),
    )
    imports, bodies = [], []
    for raw, names in parts:
        head, body = joint_lean.source_bodies(raw, names)
        for line in head:
            if line not in imports:
                imports.append(line)
        bodies.append(body)
    text = '\n'.join(imports) + '\n' + '\n'.join(bodies) + '\n'
    text += template(source_root).decode('utf-8')
    text += '\nnamespace Phase17Finite\nopen RcpRclmFormalCoreV2 RcpRclmFormalCoreV3\n'
    text += 'set_option maxRecDepth 32768\nset_option maxHeartbeats 16000000\n'
    text += '-- Fresh Q packet SHA256: ' + sha(prepared.packet_bytes) + '\n'
    text += '-- Resource trace is retained N reference-work evidence, not new Q physical cost.\n'

    resource = p['resource']
    policy = Policy.from_json(resource['policy'])
    kinds = list(resource['charge_sequence'])
    actual_kinds = kinds[1:] if negative == 'OmittedCharge' else kinds
    cost_limit = 4031 if negative == 'OverBudget' else policy.cost_limit
    root_id = resource['binding']['fixed_verifier_hash']
    bindings = p['bindings']
    require(re.fullmatch('[0-9a-f]{64}', root_id) is not None, 'root identity must be a bound digest')
    text += 'def fixedRoot : String := ' + string(root_id) + '\n'
    text += 'def expectedTrace : List Phase17Resource.Kind := ' + _kinds(kinds) + '\n'
    text += 'def selectedTrace : List Phase17Resource.Kind := ' + _kinds(actual_kinds) + '\n'
    text += ('def selectedPolicy : Phase17Resource.Policy := { limits := fun i => ([' +
             ', '.join(str(v) for v in policy.limits) +
             '] : List Nat).getD i.val 0, costLimit := ' + str(cost_limit) + ' }\n')
    text += '''
def selectedConfiguration : Configuration :=
  { root := fixedRoot
    catalog := Phase17TaskMeaning.catalog
    taskName := fun n => Phase17TaskMeaning.taskIds.getD n ""
    contract := Phase17Protected.boundContract
    context := Phase17Provenance.selectedContext
    policy := selectedPolicy
    expectedCharges := expectedTrace }

def selectedBefore : State := ofObservations fixedRoot
  Phase17LearnedBinding.observedBefore Phase17TaskMeaning.before
  Phase17TaskMeaning.beforeDeclared Phase17Protected.observedBefore
'''
    after_semantic = 'Phase17Protected.observedAfter'
    if negative == 'ChangedProbability':
        changed = copy.deepcopy(observation_projection(p['protected_packet']['after']))
        current, target = p['protected_packet']['information_positions'][0]
        row = changed['mass_minus_one_dictionary'][changed['row_selectors'][current]]
        other = next((i for i, v in enumerate(row) if v != row[target]), None)
        require(other is not None, 'nonconstant probability control required')
        row[target], row[other] = row[other], row[target]
        text += ('def changedAfter : Phase17Protected.Observation := { rows := ' +
                 protected_semantics_lean._list(changed['mass_minus_one_dictionary']) +
                 ', selectors := ' + protected_semantics_lean._list(changed['row_selectors']) +
                 ', goals := ' + protected_semantics_lean._list(changed['goals']) + ' }\n')
        after_semantic = 'changedAfter'
    declared = ('Phase17TaskMeaning.beforeDeclared' if negative == 'WrongFrontier'
                else 'Phase17TaskMeaning.afterDeclared')
    text += ('def selectedAfter : State := ofObservations fixedRoot\n'
             '  Phase17LearnedBinding.observedAfter Phase17TaskMeaning.after\n'
             '  ' + declared + ' ' + after_semantic + '\n')
    parent_id = '0' * 64 if negative == 'WrongParent' else bindings['predecessor_physical_hash']
    selected_program = p['protected_packet']['joint_packet']['task_meanings']['after']['programs'][-1]
    text += ('def selectedUpdate : Update :=\n'
             '  { key := Phase17LearnedBinding.addedKey\n'
             '    program := ' + program(selected_program) + '\n'
             '    task := 21\n'
             '    taskName := Phase17LearnedBinding.addedTask\n'
             '    parentPackage := ' + string(parent_id) + '\n'
             '    candidatePackage := ' + string(bindings['candidate_physical_hash']) + '\n'
             '    contextHash := Phase17Provenance.selectedContext.contextHash\n'
             '    charges := selectedTrace }\n')
    text += 'def selectedCandidate : RCP.Candidate State Update := ⟨selectedUpdate, selectedAfter⟩\n'
    if negative == 'SkippedProposal':
        text += '''
def selectedProposal : Phase17Provenance.Proposal :=
  { Phase17Provenance.selectedProposal with
    choices := Phase17Provenance.selectedProposal.choices.drop 1
    verdicts := Phase17Provenance.selectedProposal.verdicts.drop 1 }
'''
    else:
        text += 'def selectedProposal : Phase17Provenance.Proposal := Phase17Provenance.selectedProposal\n'
    evidence_candidate = '0' * 64 if negative == 'MixedCandidate' else bindings['candidate_physical_hash']
    evidence_root = '0' * 64 if negative == 'WrongRoot' else root_id
    text += ('def selectedEvidence : Evidence :=\n'
             '  { root := ' + string(evidence_root) + '\n'
             '    parentPackage := ' + string(bindings['predecessor_physical_hash']) + '\n'
             '    candidatePackage := ' + string(evidence_candidate) + '\n'
             '    contextHash := Phase17Provenance.selectedContext.contextHash\n'
             '    transcriptHash := ' + string(bindings['transcript_sha256']) + '\n'
             '    proposal := selectedProposal\n'
             '    charges := selectedTrace }\n')
    text += '''
theorem selected_facts :
    Facts selectedConfiguration selectedBefore selectedCandidate selectedEvidence := by
  constructor
  · unfold admissible Phase17Protected.WellFormed
    decide
  · unfold admissible Phase17Protected.WellFormed
    decide
  · apply state_ext <;> decide
  · unfold UpdateValid
    decide
  · unfold trustValid Phase17Provenance.ContextValid
    decide
  · unfold resourceValid Phase17Resource.Fits
    decide
  · unfold Phase17Provenance.CandidateMatches Phase17Provenance.Produced
      Phase17Provenance.ContextValid
    decide
  · decide

theorem selected_base_step :
    RCP.StepObligations (base selectedConfiguration)
      selectedBefore selectedCandidate selectedEvidence :=
  base_step selectedConfiguration selectedBefore selectedCandidate selectedEvidence selected_facts

theorem selected_learned_accepted :
    Learned.LearnedAcceptedStep (learned selectedConfiguration)
      selectedBefore selectedCandidate (packet selectedConfiguration selectedBefore selectedEvidence) :=
  accepted selectedConfiguration selectedBefore selectedCandidate selectedEvidence selected_facts

theorem selected_exact_recovery : recover selectedUpdate selectedAfter = selectedBefore := by
  have typed := selected_facts.typed
  change selectedAfter = apply selectedBefore selectedUpdate at typed
  rw [typed]
  apply exact_recovery
  · decide
  · decide
  · decide

theorem selected_resource_totals :
    selectedTrace.length = 153 ∧ Phase17Resource.counter selectedTrace 0 = 9 ∧
    Phase17Resource.counter selectedTrace 1 = 144 ∧
    Phase17Resource.counter selectedTrace 2 = 576 ∧
    Phase17Resource.counter selectedTrace 3 = 576 ∧
    Phase17Resource.totalCost selectedTrace = 4032 := by decide

end Phase17Finite
'''
    text += '\n'.join('#print axioms ' + name for name in NAMES) + '\n'
    raw = text.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b', raw),
            'forbidden finite proof token')
    return raw


def parse_audits(output: str) -> dict:
    from . import lean_frontier_gate as gate
    cursor, result = 0, {}
    for name in NAMES:
        match = re.compile(r"'" + re.escape(name) +
            r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*", re.S).match(output, cursor)
        require(match is not None, 'exact finite audit sequence required')
        result[name] = gate._axioms(match[0], name)
        cursor = match.end()
    require(cursor == len(output), 'unexpected finite audit output')
    return result


def check(*args, **kwargs):
    from .finite_kernel_check import check as run
    return run(*args, **kwargs)


def validate_result(*args, **kwargs):
    from .finite_kernel_check import validate_result as validate
    return validate(*args, **kwargs)
