"""Phase17J: explicit, source-bound meanings for the selected capability frontier.

This is a verifier-side task catalog, not a source of new challenges or an active
frontier. Production input is physical packages + the authenticated predecessor
and externally anchored sealed transcript; caller-authored pass reports are not
accepted. The nine vector contracts retain their finite original scope. The
thirteen proof contracts retain the actual inherited theorem propositions.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from .bootstrap import HistoricalPredecessor, _validate_program
from .materialized import PackageReceipt, require, sha, snapshot, verify_package, execute_matrix
from .conservative_extension import registry_from_files
from .successor_evidence import prepare_successor
from .frontier_recertification import prepare_frontier
from .learned_state_binding import CLAIMS
from .challenge_protocol import execute_reference

SCHEMA = 'runtime.v5.phase17.selected-frontier-meanings.v1'
POLICY = 'phase17.selected-historical-21-plus-sealed-eight-probe.v1'
HISTORICAL_CATALOG_SHA256 = '3c3a412d4cc1c6eb9a0882ecaa94aa0519b5f2e8007f56d9501c434e03cf41c0'
LIMIT = 2 * 1024 * 1024
HEX = re.compile('[0-9a-f]{64}')
# These are the original named source bytes freshly produced by the inherited
# 21-task evaluator. They pin the task grammar, not a free-form proof input.
PROOF_SOURCE_HASHES = ('00a2b7cac3e41ec4f7f10326f38e7876550a166956b3133ab43b60a71d167d77', '2923a5127ebb2dce77b93f25bfacd4ff8d23778e9c045de8ddabed164da927fb', '29a44f8162d395296df0b6a3695ef84d4c53754badd4fc40ac572339afe81343', '2ccfa1a6941344d7717e88514799bc03b443551733ef5f6611568e3b709d11ad', '5f3d24df1725dd940f10edd1a1fc857d3e0a0a74aee4af2970c17e87e88e1387', '60e6bbca487b6807d97338b84253481f2884d25644d8f9274b716799a504d269', '74b00915a34bd9b2abc617337883e545052e5193f01de883549f4b61c1e9bb9e', '8410efe3df3b56346023950e05536e31d3ed1436ba189e5d081eca7ecae3c2a3', 'a269501136730bdcde4b1ab63efdb521ebb95bf9007b4dce32025cd893b3f830', 'e213d8c64ed0c514b3be2f8e1dabde63c3b432d738e0a603140a3c948ba6ddfa', 'e674398024eb21a38ba89194a88e47bdb9e76adc711744020733036883991f1e', 'ef24333062d901e017672cd228a08665df7fe26cd039bd30af051edfe0bf1f15', 'f17a5ce95e825ce7b1f160ea01b9af617754a0599dc79e598631d760d2737662')


def _hash(x, name):
    require(type(x) is str and HEX.fullmatch(x) is not None, name)


def _vec(v, bounded=False):
    require(type(v) is list and len(v)==4 and all(type(x) is int and abs(x)<2**31 for x in v),
            'exact four-integer vector required')
    if bounded: require(all(-64<=x<=64 for x in v), 'input vector outside inherited domain')


def proof_meaning(name: str, raw: bytes) -> dict:
    """Parse only the thirteen pinned inherited sources; never free-form code."""
    require(type(raw) is bytes and sha(raw) in PROOF_SOURCE_HASHES, 'unrecognized inherited proof source')
    text=raw.decode('utf-8')
    require(re.fullmatch('phase17_[0-9a-f]{24}',name) is not None, 'invalid inherited proof name')
    line=next((s for s in text.splitlines() if s.startswith('theorem '+name+' ')),None)
    require(line is not None and line.endswith(' := by'), 'unsupported theorem declaration')
    header=line[len('theorem '+name): -len(' := by')]
    # The source identity pin above makes this a parser of known literal data,
    # not a general parser for potentially adversarial Lean code.
    depth=0;pos=-1
    for i,c in enumerate(header):
        if c=='(':depth+=1
        elif c==')':depth-=1
        elif c==':' and depth==0:pos=i;break
    require(pos>=0,'missing theorem result type')
    binders,body=header[:pos].strip(),header[pos+1:].strip()
    require(not binders or binders.startswith('('), 'unsupported binder syntax')
    proposition=('∀ '+binders+', ' if binders else '')+body
    normalized=text.removeprefix('import Mathlib\n\n')
    normalized=normalized.replace('macro "q" : tactic => `(tactic| omega)\n\n','')
    normalized=normalized.replace('macro "z" : tactic => `(tactic| simp)\n\n','')
    normalized=normalized.replace('\n  q\n','\n  omega\n').replace('\n  z\n','\n  simp\n')
    normalized=normalized.replace('\n#print axioms '+name+'\n','\n')
    require('#' not in normalized and 'import ' not in normalized and 'macro ' not in normalized,
            'unrecognized source wrapper')
    return {'name':name,'source_sha256':sha(raw),'source_utf8':text,
            'proposition':proposition,'normalized_proof':normalized}


def _observation(rows: list[dict]) -> list[dict]:
    return [{'task_id':r['task_id'],'source_sha256':r['source_sha256'],'decode_hash':r['decode_hash']}
            for r in rows if r['lean_required']]


def contract_identity(contract: dict) -> str:
    return sha(canonical(contract))


def _matches(program: dict, task: dict) -> bool:
    return (program['family']==task['family'] and
            (task['program_hash'] is None or digest(program)==task['program_hash']) and
            [execute_matrix(program,x) for x in task['inputs']]==task['targets'])


def check_task(task: dict, state: dict) -> bool:
    """No success flags: recompute exact matching observations or integer outputs.

    The proof case checks output/source binding only. Its proposition must ALSO
    be checked by the separate real Lean gate before formal soundness is claimed.
    """
    if task['kind']=='proof':
        return {'task_id':task['task_id'],'source_sha256':task['meaning']['source_sha256'],
                'decode_hash':task['decode_hash']} in state['proof_observations']
    return any(_matches(p,task) for p in state['programs'])


def checked_ids(tasks: list[dict], state: dict) -> list[str]:
    """Unknown identifiers do not enter the catalog and cannot acquire semantics."""
    declared=set(state['declared_ids'])
    return [t['task_id'] for t in tasks if t['task_id'] in declared and check_task(t,state)]


def validate_packet(p: dict) -> None:
    require(type(p) is dict and set(p)=={'schema_id','policy','bindings','tasks','before','after',
        'new_task_id','checks','claims','scope'},'exact catalog fields required')
    require(p['schema_id']==SCHEMA and p['policy']==POLICY,'task meaning policy changed')
    require(p['claims']=={k:False for k in CLAIMS} and all(v is False for v in p['claims'].values()),'unsupported claim')
    bindings=p['bindings']
    require(type(bindings) is dict and set(bindings)=={'historical_state_hash','predecessor_physical_hash',
        'candidate_physical_hash','transcript_sha256','program_hash','objective_hash','challenge_commitment_hash'},'transaction bindings')
    for v in bindings.values():_hash(v,'transaction digest')
    tasks=p['tasks'];require(type(tasks) is list and len(tasks)==22,'complete 22-task catalog required')
    require(sha(canonical(tasks[:21]))==HISTORICAL_CATALOG_SHA256,'historical task meaning changed')
    ids=[t['task_id'] for t in tasks]
    require(len(set(ids))==22 and all(type(x) is str and re.fullmatch('[A-Za-z0-9_.-]{1,180}',x) for x in ids),'task ids')
    require(ids[:21]==sorted(ids[:21]) and ids[-1]==p['new_task_id']==
            'phase17.dynamic.'+bindings['challenge_commitment_hash'],'catalog order/challenge id')
    require(sum(t['kind']=='proof' for t in tasks)==13,'13 theorem meanings required')
    for index,t in enumerate(tasks):
        if t['kind']=='proof':
            require(set(t)=={'task_id','kind','meaning','decode_hash','origin'},'proof contract fields')
            m=t['meaning'];require(m==proof_meaning(m['name'],m['source_utf8'].encode('utf-8')),'proof proposition/source mismatch')
            _hash(t['decode_hash'],'decoded output identity')
            require(t['origin']=='pinned_historical_task_and_fresh_package_decode','proof origin')
        else:
            require(t['kind']=='vectors' and set(t)=={'task_id','kind','family','program_hash','inputs','targets','origin'},'vector contract fields')
            require(type(t['inputs']) is list and type(t['targets']) is list and len(t['inputs'])==len(t['targets'])==(8 if index==21 else 1),'finite task scope')
            for x in t['inputs']:_vec(x,True)
            for x in t['targets']:_vec(x)
            if index<21:
                _hash(t['program_hash'],'historical program binding')
                require(t['origin']=='pinned_phase16_target_output_hash','historical target origin')
            else:
                require(t['program_hash'] is None and t['origin']=='sealed_phase17_evaluator_specification','new task origin')
    for which,key in [('before','predecessor_physical_hash'),('after','candidate_physical_hash')]:
        s=p[which]
        require(type(s) is dict and set(s)=={'package_hash','declared_ids','proof_observations','programs'},'state fields')
        require(s['package_hash']==bindings[key],'wrong package binding')
        expected=ids[:21] if which=='before' else sorted(ids)
        require(s['declared_ids']==expected,'declared frontier differs')
        require(type(s['proof_observations']) is list and len(s['proof_observations'])==13,'proof observation coverage')
        expected_obs=[{'task_id':t['task_id'],'source_sha256':t['meaning']['source_sha256'],'decode_hash':t['decode_hash']} for t in tasks if t['kind']=='proof']
        require(s['proof_observations']==expected_obs,'actual source/decode observation mismatch')
        require(type(s['programs']) is list and len(s['programs'])==(8 if which=='before' else 9),'program count')
        for program in s['programs']:_validate_program(program)
        require(len({digest(q) for q in s['programs']})==len(s['programs']),'duplicate program')
    require(p['before']['package_hash']!=p['after']['package_hash'] and
            p['after']['programs'][:-1]==p['before']['programs'] and
            digest(p['after']['programs'][-1])==bindings['program_hash'],'registry extension mismatch')
    required={'before_ids':checked_ids(tasks,p['before']),'after_ids':checked_ids(tasks,p['after']),
              'predecessor_new_task_passed':check_task(tasks[-1],p['before']),
              'candidate_new_task_passed':check_task(tasks[-1],p['after'])}
    require(canonical(p['checks'])==canonical(required) and required['before_ids']==ids[:21] and required['after_ids']==ids and
            required['predecessor_new_task_passed'] is False and required['candidate_new_task_passed'] is True,
            'task-satisfaction or retention mismatch')
    require(canonical(p['scope'])==canonical({'inherited_proof_tasks':13,'historical_single_input_vector_tasks':8,
        'new_eight_probe_task':1,'universal_vector_claim':False,'observations_not_formally_verified_model_execution':True,
        'root_layer_attachment_not_accepted_step':True}),'scope substitution')


@dataclass(frozen=True)
class PreparedMeanings:
    packet_bytes: bytes
    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and 0<len(self.packet_bytes)<=LIMIT,'bounded immutable catalog')
        p=load_json_strict(self.packet_bytes);validate_packet(p)
    @property
    def packet(self):return load_json_strict(self.packet_bytes)


def prepare_meanings(before:PackageReceipt, after:PackageReceipt, parent:HistoricalPredecessor, *,
                     bundle:Path,capture:Path,transcript:bytes,expected_transcript_hash:str) -> PreparedMeanings:
    """Rebuild task meanings from pinned history and sealed evaluator evidence."""
    f=prepare_successor(before,after,parent,bundle=bundle,capture=capture,
                        transcript=transcript,expected_transcript_hash=expected_transcript_hash).packet
    # Reexecute on each physical package, rather than copying predecessor/candidate
    # answers or accepting caller-provided observations.
    old=prepare_frontier(before,parent,bundle=bundle,capture=capture)
    new=prepare_frontier(after,parent,bundle=bundle,capture=capture,
                         transcript=transcript,expected_transcript_hash=expected_transcript_hash)
    require(old.sources==new.sources,'inherited proof source changed')
    old_rows,new_rows=old.report['task_reports'],new.report['task_reports']
    require(_observation(old_rows)==_observation(new_rows),'inherited decoder/source binding changed')
    programs_before=[load_json_strict(raw) for _,raw in registry_from_files(snapshot(before.root)).entries]
    programs_after=[load_json_strict(raw) for _,raw in registry_from_files(snapshot(after.root)).entries]
    by_id={digest(q):q for q in programs_before};sources=dict(new.sources);tasks=[]
    for row in new_rows:
        if row['lean_required']:
            meaning=proof_meaning(row['proof_name'],sources[row['proof_name']])
            tasks.append({'task_id':row['task_id'],'kind':'proof','meaning':meaning,
                'decode_hash':row['decode_hash'],'origin':'pinned_historical_task_and_fresh_package_decode'})
        else:
            q=by_id[row['program_hash']]
            require(execute_reference(q,row['input_vector'])==row['output_vector'],'historical output reference mismatch')
            tasks.append({'task_id':row['task_id'],'kind':'vectors','family':q['family'],
                'program_hash':row['program_hash'],'inputs':[row['input_vector']],'targets':[row['output_vector']],
                'origin':'pinned_phase16_target_output_hash'})
    probes=f['candidate_evaluation']['probe_checks']
    tasks.append({'task_id':f['new_capability'],'kind':'vectors','family':f['candidate_program']['family'],
        'program_hash':None,'inputs':[r['input'] for r in probes],'targets':[r['expected'] for r in probes],
        'origin':'sealed_phase17_evaluator_specification'})
    states=[{'package_hash':receipt.package_hash,'declared_ids':sorted(frontier),
             'proof_observations':_observation(rows),'programs':programs}
            for receipt,frontier,rows,programs in [(before,f['capabilities_before'],old_rows,programs_before),
                (after,f['capabilities_after'],new_rows,programs_after)]]
    p={'schema_id':SCHEMA,'policy':POLICY,'bindings':f['bindings'],'tasks':tasks,'before':states[0],'after':states[1],
       'new_task_id':f['new_capability'],'checks':{'before_ids':checked_ids(tasks,states[0]),
        'after_ids':checked_ids(tasks,states[1]),'predecessor_new_task_passed':check_task(tasks[-1],states[0]),
        'candidate_new_task_passed':check_task(tasks[-1],states[1])},'claims':{k:False for k in CLAIMS},
       'scope':{'inherited_proof_tasks':13,'historical_single_input_vector_tasks':8,'new_eight_probe_task':1,
           'universal_vector_claim':False,'observations_not_formally_verified_model_execution':True,
           'root_layer_attachment_not_accepted_step':True}}
    return PreparedMeanings(canonical(p))


def verify_meaning_bytes(raw:bytes, expected:PreparedMeanings, *, expected_sha256:str) -> None:
    require(type(raw) is bytes and sha(raw)==expected_sha256 and raw==expected.packet_bytes,
            'catalog differs from independently recomputed anchored meanings')
