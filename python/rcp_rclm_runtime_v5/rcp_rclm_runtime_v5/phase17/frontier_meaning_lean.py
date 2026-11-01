"""Real pinned Lean gate for the selected task-meaning layer; no promotion."""
from __future__ import annotations
import copy
import os
from pathlib import Path
import re
import subprocess
import tempfile
from .frontier_meanings import PreparedMeanings, validate_packet, CLAIMS
from .materialized import require, sha
from .successor_lean import program, string, array, integer, FAMILY_CODES
from . import lean_frontier_gate as gate

BRIDGE_PATH='lean/phase17_bridge/TaskFrontier.lean'
BRIDGE_SHA256='fcc5cdfcbc87f3a0d5aeed901e685ecb5191aee293afc23f22d054291a99c114'
NEW_NAMES=tuple('Phase17TaskMeaning.'+n for n in (
    'checked_frontier_sound','attached_root_frontier_sound','selected_before_sound',
    'selected_after_sound','selected_frontier_retention','selected_frontier_expansion',
    'selected_predecessor_rejects_new','selected_catalog_bijection'))
INHERITED_NAMES=tuple('Phase17TaskMeaning.inherited_'+str(i) for i in range(13))
NAMES=NEW_NAMES+INHERITED_NAMES


def template(root:Path)->bytes:
    p=root/BRIDGE_PATH
    require(p.is_file() and not p.is_symlink(),'missing/linked task-meaning template')
    raw=p.read_bytes().replace(b'\r\n',b'\n');require(sha(raw)==BRIDGE_SHA256,'task-meaning template differs')
    return raw


def render_meanings(prepared:PreparedMeanings, *, source_root:Path, negative:str|None=None)->bytes:
    require(type(prepared) is PreparedMeanings and negative in (None,'target','observation'),'unsupported proof inputs')
    p=prepared.packet;validate_packet(p)
    text=template(source_root).decode('utf-8')
    text+='\nnamespace Phase17TaskMeaning\nset_option maxRecDepth 16384\nset_option maxHeartbeats 4000000\n'
    text+='-- Independently recomputed catalog SHA256: '+sha(prepared.packet_bytes)+'\n'
    rules=[];proof_index=0
    vec=lambda v:array(v,integer)
    for t in p['tasks']:
        if t['kind']=='proof':
            m=t['meaning'];ns='Inherited'+str(proof_index)
            text+='namespace '+ns+'\n'+m['normalized_proof']+'\ndef Target : Prop := '+m['proposition'].replace('(h :', '(_h :')+'\nend '+ns+'\n'
            text+='theorem inherited_'+str(proof_index)+' : '+ns+'.Target := '+ns+'.'+m['name']+'\n'
            rules.append('theoremMeaning '+string(t['task_id'])+' '+string(m['source_sha256'])+' '+string(t['decode_hash'])+
                         ' '+ns+'.Target inherited_'+str(proof_index))
            proof_index+=1
        else:
            targets=copy.deepcopy(t['targets'])
            if negative=='target' and t['task_id']==p['new_task_id']:targets[0][0]+=1
            required='none' if t['program_hash'] is None else '(some '+string(t['program_hash'])+')'
            rules.append('vectorMeaning { family := '+str(FAMILY_CODES[t['family']])+', requiredProgram := '+required+
                         ', inputs := '+array(t['inputs'],vec)+', targets := '+array(targets,vec)+' }')
    text+='def catalog : Nat → Meaning\n'+''.join('  | '+str(i)+' => '+r+'\n' for i,r in enumerate(rules))+'  | _ => rejectMeaning\n'
    text+='def taskIds : List String := '+array([t['task_id'] for t in p['tasks']],string)+'\n'
    from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
    for label in ('before','after'):
        s=p[label];obs=copy.deepcopy(s['proof_observations'])
        if negative=='observation' and label=='after':obs[0]['source_sha256']='0'*64
        proof_rows=['('+string(r['task_id'])+', '+string(r['source_sha256'])+', '+string(r['decode_hash'])+')' for r in obs]
        entries=['('+string(digest(q))+', '+program(q)+')' for q in s['programs']]
        text+='def '+label+' : ObservationState := { proofs := ['+', '.join(proof_rows)+'],\n programs := ['+', '.join(entries)+'] }\n'
    text+='''
def beforeDeclared : Finset Nat := Finset.range 21
def afterDeclared : Finset Nat := Finset.range 22

theorem before_coverage : checkedFrontier beforeDeclared catalog before = beforeDeclared := by decide
theorem after_coverage : checkedFrontier afterDeclared catalog after = afterDeclared := by decide

theorem selected_before_sound {task : Nat} (member : task ∈ beforeDeclared) :
    (catalog task).holds before := by
  apply checked_frontier_sound beforeDeclared catalog before
  rw [before_coverage]
  exact member

theorem selected_after_sound {task : Nat} (member : task ∈ afterDeclared) :
    (catalog task).holds after := by
  apply checked_frontier_sound afterDeclared catalog after
  rw [after_coverage]
  exact member

theorem selected_frontier_retention :
    checkedFrontier beforeDeclared catalog before ⊆ checkedFrontier afterDeclared catalog after := by
  rw [before_coverage, after_coverage]
  decide

theorem selected_frontier_expansion :
    (checkedFrontier beforeDeclared catalog before).card <
      (checkedFrontier afterDeclared catalog after).card := by
  rw [before_coverage, after_coverage]
  decide

theorem selected_predecessor_rejects_new : (catalog 21).check before = false := by decide

theorem selected_catalog_bijection : taskIds.length = 22 ∧ taskIds.Nodup := by decide

end Phase17TaskMeaning
'''
    text+='\n'.join('#print axioms '+n for n in NAMES)+'\n'
    raw=text.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b',raw),'forbidden generated token')
    return raw


def parse_audits(text:str)->dict:
    cursor=0;out={}
    for n in NAMES:
        m=re.compile(r"'"+re.escape(n)+r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*",re.S).match(text,cursor)
        require(m is not None,'exact task-meaning audit sequence required')
        out[n]=gate._axioms(m[0],n);cursor=m.end()
    require(cursor==len(text),'extra task-meaning audit output')
    return out


def check_meanings(prepared:PreparedMeanings, *, source_root:Path, lean_workspace:Path,
                   toolchain_root:Path|None=None)->dict:
    result={'schema_id':'runtime.v5.phase17.task-meaning-lean.v1','status':'blocked','packet_sha256':sha(prepared.packet_bytes),
        'commands':[],'theorem_axioms':{},'selected_task_meanings_checked':False,'root_frontier_field_connection_checked':False,
        'negative_controls_rejected':[],'new_named_audits':8,'inherited_theorem_propositions_rechecked':13,
        'claims':{k:False for k in CLAIMS}}
    try:
        sources={label:render_meanings(prepared,source_root=source_root,negative=neg)
                 for label,neg in [('TaskMeaning',None),('WrongTarget','target'),('MissingProofObservation','observation')]}
        raw_template=template(source_root)
        roots=gate.root_source_fingerprint(lean_workspace)
        require({k:v['canonical_sha256'] for k,v in roots.items()}==
                {k:v['canonical_sha256'] for k,v in gate.root_source_fingerprint(source_root).items()},'root mismatch')
        deps=gate._dependency_state(lean_workspace)
        tool=gate.resolve_toolchain(toolchain_root);env,git=gate._lean_environment(tool)
        suffix='.exe' if os.name=='nt' else '';lean,lake=tool/'bin'/('lean'+suffix),tool/'bin'/('lake'+suffix)
        executables={str(p):sha(gate._read_regular(p)) for p in (lean,lake,git)}
        version=gate._process([str(lean),'--version'],lean_workspace/gate.ROOT_PROJECT,env,timeout=30)
        result['commands'].append(version)
        require(version['returncode']==0 and not version['stderr'] and
                re.match(r'^Lean \(version 4\.31\.0(?:,|\))',version['stdout']),'wrong pinned Lean')
        result['status']='rejected'
        with tempfile.TemporaryDirectory(prefix='r17j-') as tmp:
            directory=Path(tmp).resolve(strict=True);argv=[str(lake),'--keep-toolchain','--no-cache','env',str(lean)]
            for label,raw in sources.items():
                path=directory/(label+'.lean');path.write_bytes(raw)
                command=gate._process([*argv,str(path)],lean_workspace/gate.ROOT_PROJECT,env,timeout=900)
                result['commands'].append(command)
                if label=='TaskMeaning':
                    require(command['returncode']==0 and not command['stderr'],'task-meaning certificate rejected')
                    audits=parse_audits(command['stdout'])
                else:
                    diagnostic=command['stdout']+command['stderr']
                    require(command['returncode']==1 and 'error:' in diagnostic and
                            'decide' in diagnostic and ('false' in diagnostic or 'failed' in diagnostic),
                            'invalid control was not rejected by proof checking')
                    result['negative_controls_rejected'].append(label)
                require(path.read_bytes()==raw,'proof source changed')
        require(roots==gate.root_source_fingerprint(lean_workspace) and deps==gate._dependency_state(lean_workspace),'root/dependency changed')
        require(executables=={str(p):sha(gate._read_regular(p)) for p in (lean,lake,git)} and template(source_root)==raw_template,'tool/template changed')
        result.update(status='passed',selected_task_meanings_checked=True,root_frontier_field_connection_checked=True,
            theorem_axioms=audits,source_sha256={k:sha(v) for k,v in sources.items()},executable_sha256=executables,
            python_observation_projection_remains_trusted=True,trusted_import_cache_assumption=True,
            complete_learned_kernel_constructed=False)
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        result['failure']={'type':type(exc).__name__,'reason':str(exc)}
    return result
