"""Recompute producer order, not just candidate membership in a legal grammar.

The producer is the fixed external Phase17 controller plus the package-bound
inherited rank projection. This is deterministic conformance, not attestation
that a historical process ran, self-hosted neural synthesis, or active promotion.
The complete sealed transcript is consumed ONLY by the verifier. Selection uses
current public fields and already verified prior observations, never its opening.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
import struct

from rcp_rclm_runtime.canonical.json import canonical_json_bytes as canonical, load_json_strict
from rcp_rclm_runtime.canonical.hashing import canonical_json_hash as digest
from .bootstrap import HistoricalPredecessor, WEIGHTS_SHA256, SELECTED_STATE_HASH
from .controller import (Action, CurrentView, FrozenSearch, RankedCandidate, SearchPrefix,
                         FAMILIES, RANKING_POLICY, decide, record_evaluation, halt,
                         checkpoint, restore, _hash, _integer, _keys)
from .phase16_adapter import bind_phase16_search
from .objectives import select_bootstrap_objective, freeze_bootstrap_objective
from .challenge_protocol import verify_transcript, reference_grammar, realize_candidate
from .materialized import PackageReceipt, verify_package, snapshot, sha, require, MANIFEST, safe_relative

SCHEMA = 'runtime.v5.phase17.proposal-provenance.v1'
POLICY = 'phase17.public-prefix-producer-conformance.v1'
MAX_PACKET = 2 * 1024 * 1024
CLAIMS = ('root_transition_verified','recursive_productivity_recertified','full_frontier_recertified',
          'promotion_authorized','promotion_performed','phase17_exit_closed','gate_e_closed','egc0_started',
          'live_capability_gain_demonstrated','complete_resource_accounting',
          'full_learned_semantic_refinement','neural_decoder_formally_verified')
# Exact reviewed implementation closure of the unchanged selection algorithm.
# Added module itself is bound by the source commit/report, not by a circular hash.
SOURCE_PINS = {
    'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/controller.py': '1d122fd51e39cb68d397c598bec6318469db3012',
    'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/phase16_adapter.py': 'fd2a824c61f3fc13a3ddfb0dd771873858ac252d',
    'python/rcp_rclm_runtime_v5/rcp_rclm_runtime_v5/phase17/objectives.py': '9c99680c9fb79c0acc848a95140a6fc713c7d257',
    'python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase16/grammar.py': 'bcc24b9797d7adf2bab501893c939b2d0270d3a1',
    'python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase16/ranking.py': '192ff699763e854a7290a8c4b153d4cc34379889',
    'python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase16/records.py': '4fabef0768090d96e0b8157ee7ba1d1ff2b85d1b',
    'python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase16/constants.py': '6ec1117cb715b060ad46b4f56dd6bd727423c949',
    'python/rcp_rclm_runtime_v4/rcp_rclm_runtime_v4/phase16/codec.py': 'f6c011174dd76fddba5d2f4257a985795e82a706',
}


def _blob(raw: bytes) -> str:
    import hashlib
    return hashlib.sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw).hexdigest()


def producer_sources(root: Path) -> list[dict]:
    rows=[]
    for name, expected in sorted(SOURCE_PINS.items()):
        path=root/name
        require(path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)), 'missing/linked producer source')
        raw=path.read_bytes().replace(b'\r\n',b'\n')
        require(_blob(raw)==expected, 'producer source differs: '+name)
        rows.append({'path':name,'git_blob':expected,'sha256':sha(raw),'size':len(raw)})
    return rows


def measured_projection(files: dict[str, bytes], parent: HistoricalPredecessor) -> tuple[tuple[int,int],...]:
    matches=[raw for raw in files.values() if sha(raw)==WEIGHTS_SHA256]
    require(len(matches)==1, 'physical inherited planner tensor absent/duplicated')
    raw=matches[0]
    require(len(raw)==65536, 'wrong planner tensor shape')
    weights=struct.unpack('<32768h',raw)
    nonzero=tuple((i,w) for i,w in enumerate(weights) if w)
    require(nonzero==parent.planner_projection and len(nonzero)==84, 'inherited planner projection changed')
    return nonzero


def score_table(view: CurrentView, programs: tuple[dict,...], weights: tuple[tuple[int,int],...]) -> list[dict]:
    """Independent integer implementation using the actual physical tensor values.

    The public feature-hash rule is inherited unchanged. This is NOT arbitrary
    neural text generation. The table contains all alternatives, not only a winner.
    """
    seed=digest({'domain':'phase17.present_only_ranking_seed.v1','view':view.to_json()})
    rows=[]
    for p in sorted(programs,key=digest):
        h=digest(p);f=FAMILIES.index(p['family']);count=view.family_counts[f]
        features=digest({'domain':'phase16.inherited_planner_feature_projection.v1',
            'planner_weights_sha256':WEIGHTS_SHA256,'active_package_hash':view.active_package_hash,
            'program':p,'seed':seed,'challenge_stream':'phase17-present-only-v1'})
        terms=[w*((int(features[(i+j*11)%64],16)+f*3+p['variant']*5+p['generation']+j)%9-4)
               for j,(i,w) in enumerate(weights)]
        ties=[int(digest({'policy_id':RANKING_POLICY,'program_hash':h,'active_package_hash':view.active_package_hash,
                         'family_count':count,'rejection_count':rejections})[:16],16)
              for rejections in range(5)]
        rows.append({'program_hash':h,'family_index':f,'variant':p['variant'],
                     'base_score':20000-count*521+sum(terms),'ties':ties})
    return rows


def reference_choice(table:list[dict], seen:list[int], offset:int) -> int:
    """Independent chooser: table-driven ranked prefix then coprime-stride walk."""
    require(len(table)==32 and len(seen)<32 and len(seen)==len(set(seen)), 'invalid search prefix')
    require(all(type(i) is int and 0<=i<32 for i in seen), 'invalid seen index')
    remaining=[i for i in range(32) if i not in seen]
    if len(seen)<4:
        counts=Counter(table[i]['family_index'] for i in seen)
        def key(i):
            row=table[i];n=counts[row['family_index']]
            return row['base_score']+797*n,row['ties'][n],row['program_hash']
        return sorted(remaining,key=key,reverse=True)[0]
    return next(i for k in range(32) if (i:=(offset+17*k)%32) not in seen)


def _binding(package: PackageReceipt, parent: HistoricalPredecessor, files:dict, source_root:Path) -> dict:
    # Include actual generator/planner/policy metadata, without claiming those
    # legacy generator bytes implement this external-controller algorithm.
    names=sorted(n for n in files if n.startswith(('base/model/generator/','base/model/phase15_planner/')) or
                 ('generator' in n or 'planner' in n) and n.endswith('.json'))
    require(any(n.endswith('weights.i16le.bin') for n in names), 'planner binding missing')
    fields={'policy':POLICY,'producer_kind':'fixed_external_controller_with_package_bound_rank_projection',
        'physical_package_hash':package.package_hash,'historical_active_package_hash':parent.state['active_package_hash'],
        'predecessor_state_hash':SELECTED_STATE_HASH,'planner_weights_sha256':WEIGHTS_SHA256,
        'component_files':[{'path':n,'sha256':sha(files[n]),'size':len(files[n])} for n in names],
        'source_files':producer_sources(source_root),
        'self_hosted_generator_execution_demonstrated':False,'historical_execution_attested':False}
    return {**fields,'generator_id':digest(fields)}


def replay_proposals(parent: HistoricalPredecessor, transcript:bytes, *, expected_transcript_hash:str,
                     weights:tuple[tuple[int,int],...]) -> dict:
    """Verify evaluator truth first, then enforce actual controller order.

    No choice is conditioned on the opening or a future evaluation. Evaluator
    replay uses the opening only for independent verification; controller inputs
    are explicitly reconstructed from the current public view and past reports.
    """
    verified=verify_transcript(parent,transcript,expected_transcript_hash=expected_transcript_hash)
    events=load_json_strict(transcript)['events'];opening=events[0]['request'];objective=opening['objective']
    decision=select_bootstrap_objective(parent,turn_index=objective['turn_index'],public_nonce_hash=objective['public_nonce_hash'])
    freeze=freeze_bootstrap_objective(decision,parent,turn_index=objective['turn_index'],public_nonce_hash=objective['public_nonce_hash'])
    require(canonical(decision.to_json())==canonical(objective) and canonical(freeze)==canonical(opening['freeze']), 'objective provenance differs')
    public=events[0]['response']['payload']['public_challenge']
    bound=bind_phase16_search(parent.phase16_state(),turn_index=objective['turn_index'],
        challenge_commitment_hash=public['challenge_commitment_hash'],public_nonce_hash=objective['public_nonce_hash'],
        candidate_credits=opening['candidate_credits'])
    programs=tuple(p.to_json() for p in sorted(bound.programs.values(),key=lambda p:p.program_hash))
    require(programs==reference_grammar(parent.state,objective['turn_index'],objective['public_nonce_hash']), 'grammar interpreter disagreement')
    require(digest(list(programs))==public['grammar_hash'], 'grammar commitment mismatch')
    table=score_table(bound.prefix.frozen.view,programs,weights)
    require([r['base_score'] for r in table]==[c.base_score for c in bound.prefix.frozen.candidates], 'physical ranker/controller disagreement')
    offset=int(bound.prefix.frozen.freeze_hash[:16],16)%32
    prefix=bound.prefix;rows=[];seen=[]
    for i in range(1,len(events)-1,2):
        require(i+1<len(events)-1, 'incomplete candidate/evaluation pair')
        fr,ev=events[i],events[i+1];step=decide(prefix)
        require(step.action==Action.EVALUATE, 'evaluation after controller terminal')
        selected=reference_choice(table,seen,offset);h=table[selected]['program_hash']
        require(h==step.candidate_hash, 'independent selection disagreement')
        require(fr['request']['op']=='freeze_candidate' and ev['request']['op']=='evaluate', 'freeze/evaluation order differs')
        require(fr['request']['program_hash']==h, 'proposal is not the current controller choice')
        artifact=realize_candidate(bound.programs[h].to_json(),freeze)
        require(ev['request']['artifact']==artifact and fr['request']['artifact_hash']==artifact['artifact_hash'], 'generated artifact differs')
        report=ev['response']['payload'];before=prefix.prefix_hash
        prefix=record_evaluation(prefix,step,verdict=report['verdict'],evaluation_hash=report['evaluation_hash'],
            reason_codes=report['reason_codes'],predecessor_state_hash=report['predecessor_state_hash'],
            challenge_commitment_hash=report['challenge_commitment_hash'])
        rows.append({'selected_index':selected,'program_hash':h,'program':bound.programs[h].to_json(),
            'artifact_hash':artifact['artifact_hash'],'decision_hash':step.decision_hash,
            'prefix_before_hash':before,'prefix_after_hash':prefix.prefix_hash,
            'candidate_freeze_hash':fr['response']['payload']['receipt']['candidate_freeze_hash'],
            'evaluation_hash':report['evaluation_hash'],'verdict':report['verdict'],'reason_codes':report['reason_codes']})
        seen.append(selected)
    if verified.terminal_action in (Action.EXTERNAL_STOP.value,Action.SAFETY_HALT.value):
        prefix=halt(prefix,safety=verified.terminal_action==Action.SAFETY_HALT.value)
    require(decide(prefix).action.value==verified.terminal_action, 'controller/evaluator terminal disagreement')
    require(len(rows)==verified.candidate_evaluations, 'evaluation count differs')
    require(restore(checkpoint(prefix),expected_prefix_hash=prefix.prefix_hash)==prefix,'checkpoint replay differs')
    return {'current_view':bound.prefix.frozen.view.to_json(),'objective_hash':decision.decision_hash,
        'objective_freeze_hash':freeze['freeze_hash'],'grammar_hash':public['grammar_hash'],'search_freeze_hash':bound.prefix.frozen.freeze_hash,
        'initial_credits':opening['candidate_credits'],'enumeration_offset':offset,'table':table,'steps':rows,
        'terminal':verified.terminal_action,'selected_program_hash':verified.selected_candidate_hash,
        'checkpoint':load_json_strict(checkpoint(prefix)),'final_prefix_hash':prefix.prefix_hash,
        'selection_input_policy':'current_public_view_and_verified_prior_rejections_only'}


@dataclass(frozen=True, slots=True)
class PreparedProvenance:
    packet_bytes: bytes
    def __post_init__(self):
        require(type(self.packet_bytes) is bytes and len(self.packet_bytes)<=MAX_PACKET,'immutable bounded packet required')
        validate_packet(load_json_strict(self.packet_bytes))
    @property
    def packet(self):return load_json_strict(self.packet_bytes)


def validate_packet(p:dict) -> None:
    _keys(p,{'schema_id','policy','producer','transcript_sha256','trace','candidate','claims','scope'},'provenance packet')
    require(p['schema_id']==SCHEMA and p['policy']==POLICY,'provenance schema/policy')
    _hash(p['transcript_sha256'],'transcript anchor')
    require(set(p['claims'])==set(CLAIMS) and all(v is False for v in p['claims'].values()),'unauthorized claim')
    require(p['scope']=={'deterministic_conformance_only':True,'historical_process_attestation':False,
        'fresh_entropy_attested':False,'self_hosted_neural_generator':False,'full_root_certificate':False} and
        all(type(v) is bool for v in p['scope'].values()),'scope widened')
    b=p['producer'];_keys(b,{'policy','producer_kind','physical_package_hash','historical_active_package_hash','predecessor_state_hash',
        'planner_weights_sha256','component_files','source_files','self_hosted_generator_execution_demonstrated',
        'historical_execution_attested','generator_id'},'producer')
    require(b['generator_id']==digest({k:v for k,v in b.items() if k!='generator_id'}) and b['policy']==POLICY,'producer digest')
    require(b['producer_kind']=='fixed_external_controller_with_package_bound_rank_projection' and
        b['self_hosted_generator_execution_demonstrated'] is False and b['historical_execution_attested'] is False,'producer scope')
    for k in ('physical_package_hash','historical_active_package_hash','predecessor_state_hash','planner_weights_sha256','generator_id'):_hash(b[k],k)
    require(b['planner_weights_sha256']==WEIGHTS_SHA256 and b['predecessor_state_hash']==SELECTED_STATE_HASH,'historical producer identity')
    for group in ('source_files','component_files'):
        require(type(b[group]) is list and b[group] and len({r['path'] for r in b[group]})==len(b[group]),'producer file map')
        require([r['path'] for r in b[group]]==sorted(r['path'] for r in b[group]),'producer file order')
        for row in b[group]:
            _keys(row,{'path','sha256','size'}|({'git_blob'} if group=='source_files' else set()),'producer file')
            safe_relative(row['path']);_hash(row['sha256'],'file digest');_integer(row['size'],'file size',1)
    require({r['path']:r['git_blob'] for r in b['source_files']}==SOURCE_PINS,'source pin set')
    t=p['trace'];_keys(t,{'current_view','objective_hash','objective_freeze_hash','grammar_hash','search_freeze_hash','initial_credits',
        'enumeration_offset','table','steps','terminal','selected_program_hash','checkpoint','final_prefix_hash','selection_input_policy'},'trace')
    view=CurrentView.from_json(t['current_view'])
    require(view.predecessor_state_hash==b['predecessor_state_hash'] and view.active_package_hash==b['historical_active_package_hash'],'producer/view mismatch')
    require(t['selection_input_policy']=='current_public_view_and_verified_prior_rejections_only','future input policy')
    rows=t['table'];require(type(rows) is list and len(rows)==32,'complete score table')
    candidates=[]
    for row in rows:
        _keys(row,{'program_hash','family_index','variant','base_score','ties'},'score row')
        f=_integer(row['family_index'],'family');require(f<8,'family bound');_integer(row['variant'],'variant')
        require(type(row['base_score']) is int and type(row['ties']) is list and len(row['ties'])==5 and
                all(type(n) is int and 0<=n<2**64 for n in row['ties']),'score/tie values')
        candidates.append(RankedCandidate(row['program_hash'],FAMILIES[f],row['variant'],row['base_score']))
        ties=[int(digest({'policy_id':RANKING_POLICY,'program_hash':row['program_hash'],'active_package_hash':view.active_package_hash,
              'family_count':view.family_counts[f],'rejection_count':n})[:16],16) for n in range(5)]
        require(row['ties']==ties,'public tie hash mismatch')
    from rcp_rclm_runtime_v4.phase16.constants import PHASE16_INHERITED_PLANNER_PROJECTION
    state={'active_package_hash':view.active_package_hash,'component_generations':dict(zip(FAMILIES,view.family_counts,strict=True))}
    programs=reference_grammar(state,view.turn_index,view.public_nonce_hash)
    require(rows==score_table(view,programs,tuple(PHASE16_INHERITED_PLANNER_PROJECTION)), 'recomputed score table differs')
    require(t['grammar_hash']==digest(list(programs)), 'grammar hash differs')
    for key in ('objective_hash','objective_freeze_hash','search_freeze_hash','final_prefix_hash'):_hash(t[key],key)
    frozen=FrozenSearch(view,tuple(candidates));require([r['program_hash'] for r in rows]==sorted(r['program_hash'] for r in rows),'canonical grammar order')
    require(frozen.freeze_hash==t['search_freeze_hash'] and type(t['enumeration_offset']) is int and
            t['enumeration_offset']==int(frozen.freeze_hash[:16],16)%32,'enumeration binding')
    credits=_integer(t['initial_credits'],'credits');require(credits<=32,'credits exceed grammar');prefix=SearchPrefix(frozen,credits)
    require(type(t['steps']) is list and len(t['steps'])<=32,'step count');seen=[]
    for row in t['steps']:
        _keys(row,{'selected_index','program_hash','program','artifact_hash','decision_hash','prefix_before_hash','prefix_after_hash',
                  'candidate_freeze_hash','evaluation_hash','verdict','reason_codes'},'step')
        step=decide(prefix);idx=_integer(row['selected_index'],'selected index')
        require(step.action==Action.EVALUATE and idx==reference_choice(rows,seen,t['enumeration_offset']) and idx<32,'selected trace differs')
        require(row['program_hash']==rows[idx]['program_hash']==digest(row['program'])==step.candidate_hash,'program binding')
        require(row['prefix_before_hash']==prefix.prefix_hash and row['decision_hash']==step.decision_hash,'prefix binding')
        for k in ('artifact_hash','candidate_freeze_hash','evaluation_hash'):_hash(row[k],k)
        freeze={'predecessor_state_hash':view.predecessor_state_hash,'active_package_hash':view.active_package_hash,
                'freeze_hash':t['objective_freeze_hash']}
        require(row['program']==programs[idx] and realize_candidate(row['program'],freeze)['artifact_hash']==row['artifact_hash'],
                'reconstructed proposal artifact differs')
        prefix=record_evaluation(prefix,step,verdict=row['verdict'],evaluation_hash=row['evaluation_hash'],reason_codes=row['reason_codes'],
            predecessor_state_hash=view.predecessor_state_hash,challenge_commitment_hash=view.challenge_commitment_hash)
        require(prefix.prefix_hash==row['prefix_after_hash'],'post-prefix binding');seen.append(idx)
    if t['terminal'] in (Action.EXTERNAL_STOP.value,Action.SAFETY_HALT.value):prefix=halt(prefix,safety=t['terminal']==Action.SAFETY_HALT.value)
    require(decide(prefix).action.value==t['terminal'] and prefix.prefix_hash==t['final_prefix_hash'] and
            canonical(t['checkpoint'])==checkpoint(prefix),'terminal/checkpoint mismatch')
    chosen=t['steps'][-1]['program_hash'] if t['terminal']==Action.AWAIT_ROOT_VERIFICATION.value else None
    require(t['selected_program_hash']==chosen,'selected candidate mismatch')
    if chosen is None:require(p['candidate'] is None,'nonpassing trace cannot bind candidate')
    else:
        c=p['candidate'];_keys(c,{'physical_package_hash','program_hash','artifact_hash','transcript_sha256','parent_physical_hash'},'candidate binding')
        require(c['program_hash']==chosen and c['artifact_hash']==t['steps'][-1]['artifact_hash'] and
                c['transcript_sha256']==p['transcript_sha256'] and c['parent_physical_hash']==b['physical_package_hash'], 'candidate provenance mismatch')
        _hash(c['physical_package_hash'],'candidate hash');require(c['physical_package_hash']!=b['physical_package_hash'],'unchanged candidate package')


def prepare_provenance(predecessor:PackageReceipt,candidate:PackageReceipt|None,parent:HistoricalPredecessor,*,bundle:Path,
                       source_root:Path,transcript:bytes,expected_transcript_hash:str)->PreparedProvenance:
    parent.validate()
    old=verify_package(predecessor.root,parent,bundle,expected_package_hash=predecessor.package_hash)
    require(old.manifest_bytes==predecessor.manifest_bytes,'predecessor receipt substitution')
    files=snapshot(predecessor.root);weights=measured_projection(files,parent);binding=_binding(predecessor,parent,files,source_root)
    trace=replay_proposals(parent,transcript,expected_transcript_hash=expected_transcript_hash,weights=weights)
    c=None
    if trace['terminal']==Action.AWAIT_ROOT_VERIFICATION.value:
        require(type(candidate) is PackageReceipt,'passing trace needs measured candidate')
        checked=verify_package(candidate.root,parent,bundle,expected_package_hash=candidate.package_hash,
            transcript=transcript,expected_transcript_hash=expected_transcript_hash)
        require(checked.manifest_bytes==candidate.manifest_bytes,'candidate receipt substitution')
        proposed=snapshot(candidate.root);h=trace['selected_program_hash']
        require(proposed['registry/programs/'+h+'.json']==canonical(trace['steps'][-1]['program']), 'physical proposal changed')
        # Strict additive materialization: all inherited payload bytes remain.
        require(all(proposed[n]==b for n,b in files.items() if n not in (MANIFEST,'registry/manifest.json')), 'inherited producer bytes changed')
        c={'physical_package_hash':candidate.package_hash,'program_hash':h,'artifact_hash':trace['steps'][-1]['artifact_hash'],
           'transcript_sha256':expected_transcript_hash,'parent_physical_hash':predecessor.package_hash}
    else:require(candidate is None,'nonpassing search cannot bind a successor')
    packet={'schema_id':SCHEMA,'policy':POLICY,'producer':binding,'transcript_sha256':expected_transcript_hash,
        'trace':trace,'candidate':c,'claims':{k:False for k in CLAIMS},
        'scope':{'deterministic_conformance_only':True,'historical_process_attestation':False,
                 'fresh_entropy_attested':False,'self_hosted_neural_generator':False,'full_root_certificate':False}}
    require(snapshot(predecessor.root)==files and producer_sources(source_root)==binding['source_files'],'producer changed during verification')
    return PreparedProvenance(canonical(packet))


def verify_provenance_bytes(data:bytes,prepared:PreparedProvenance,*,expected_sha256:str)->None:
    _hash(expected_sha256,'external packet anchor')
    require(type(data) is bytes and sha(data)==expected_sha256,'provenance packet anchor mismatch')
    PreparedProvenance(data)
    require(data==prepared.packet_bytes,'provenance differs from independent recomputation')
