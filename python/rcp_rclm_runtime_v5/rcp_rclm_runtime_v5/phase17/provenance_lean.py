"""Actual pinned kernel checks of finite producer replay and root-field adapters."""
from __future__ import annotations
import copy
import os
from pathlib import Path
import re
import subprocess
import tempfile
from . import lean_frontier_gate as gate
from .proposal_provenance import PreparedProvenance, validate_packet, CLAIMS
from .materialized import require, sha
from .successor_lean import array, string, integer

BRIDGE_PATH='lean/phase17_bridge/ProposalProvenance.lean'
BRIDGE_SHA256='3cae873ff4dba673c926ac4ecf214d349c2ec6a635bf0ead44547bebc76056a4'
NAMES=tuple('Phase17Provenance.'+n for n in ('trace_no_repeat','attached_generator_bound','attached_package_bound',
    'attached_proposal_produced','attached_candidate_bound','selected_provenance','selected_candidate_binding','selected_rejection_prefix'))
LABELS=('Provenance','SkippedPrefix','WrongParent','WrongProgram')


def template(root:Path)->bytes:
    p=root/BRIDGE_PATH
    require(p.is_file() and not p.is_symlink(),'missing/linked provenance template')
    raw=p.read_bytes().replace(b'\r\n',b'\n');require(sha(raw)==BRIDGE_SHA256,'provenance template differs')
    return raw


def render_provenance(prepared:PreparedProvenance,*,source_root:Path,negative:str|None=None)->bytes:
    require(type(prepared) is PreparedProvenance and negative in (None,'prefix','parent','program'),'unsupported proof inputs')
    p=prepared.packet;validate_packet(p);t=p['trace'];b=p['producer'];c=p['candidate']
    require(t['terminal']=='await_root_verification' and c is not None,'no passing proposal for selected proof')
    text=template(source_root).decode('utf-8')
    text+='\nnamespace Phase17Provenance\nset_option maxRecDepth 16384\nset_option maxHeartbeats 4000000\n'
    context_hash=sha(prepared.packet_bytes)
    def nat(n):
        require(type(n) is int and 0<=n<2**64,'bounded Nat literal');return str(n)
    rows=['{ key := '+string(r['program_hash'])+', family := '+nat(r['family_index'])+', baseScore := '+integer(r['base_score'])+
          ', ties := '+array(r['ties'],nat)+' }' for r in t['table']]
    # All record fields deliberately share one line: no indentation-sensitive splice.
    text+=('def selectedContext : Context := { generator := '+string(b['generator_id'])+', parentPackage := '+string(b['physical_package_hash'])+
        ', contextHash := '+string(context_hash)+', transcriptHash := '+string(p['transcript_sha256'])+', credits := '+nat(t['initial_credits'])+
        ', offset := '+nat(t['enumeration_offset'])+', rows := ['+', '.join(rows)+'] }\n')
    choices=[r['selected_index'] for r in t['steps']]
    if negative=='prefix':choices=choices[-1:]
    parent='0'*64 if negative=='parent' else b['physical_package_hash']
    program=t['table'][0]['program_hash'] if negative=='program' else c['program_hash']
    require(negative!='program' or program!=c['program_hash'],'wrong-program control must differ')
    verdicts=[False]*(len(choices)-1)+[True]
    text+=('def selectedProposal : Proposal := { generator := '+string(b['generator_id'])+', parentPackage := '+string(parent)+
        ', contextHash := '+string(context_hash)+', transcriptHash := '+string(p['transcript_sha256'])+', choices := '+array(choices,nat)+
        ', verdicts := '+array(verdicts,lambda v:'true' if v else 'false')+', program := '+string(program)+
        ', candidatePackage := '+string(c['physical_package_hash'])+' }\n')
    text+=('def selectedCandidate : CandidateView := { parentPackage := '+string(b['physical_package_hash'])+
        ', contextHash := '+string(context_hash)+', program := '+string(c['program_hash'])+', package := '+string(c['physical_package_hash'])+' }\n')
    text+='''
theorem selected_provenance : Produced selectedContext selectedProposal := by decide

theorem selected_candidate_binding :
    CandidateMatches selectedContext selectedProposal selectedCandidate := by decide

theorem selected_rejection_prefix :
    selectedProposal.verdicts = List.replicate (selectedProposal.choices.length - 1) false ++ [true] := by decide

end Phase17Provenance
'''
    text+='\n'.join('#print axioms '+n for n in NAMES)+'\n'
    raw=text.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b',raw),'forbidden generated token')
    return raw


def parse_audits(text:str)->dict:
    cursor=0;out={}
    for n in NAMES:
        m=re.compile(r"'"+re.escape(n)+r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*",re.S).match(text,cursor)
        require(m is not None,'exact provenance audit sequence required')
        out[n]=gate._axioms(m[0],n);cursor=m.end()
    require(cursor==len(text),'unexpected provenance audit output')
    return out


def check_provenance(prepared:PreparedProvenance,*,source_root:Path,lean_workspace:Path,toolchain_root:Path|None=None)->dict:
    result={'schema_id':'runtime.v5.phase17.proposal-provenance-lean.v1','status':'blocked','packet_sha256':sha(prepared.packet_bytes),
        'commands':[],'theorem_axioms':{},'finite_producer_replay_checked':False,'root_provenance_fields_checked':False,
        'negative_controls_rejected':[],'new_named_audits':len(NAMES),'claims':{k:False for k in CLAIMS}}
    try:
        sources={label:render_provenance(prepared,source_root=source_root,negative=neg)
                 for label,neg in zip(LABELS,(None,'prefix','parent','program'),strict=True)}
        raw_template=template(source_root)
        roots=gate.root_source_fingerprint(lean_workspace)
        require({k:v['canonical_sha256'] for k,v in roots.items()}==
            {k:v['canonical_sha256'] for k,v in gate.root_source_fingerprint(source_root).items()},'pinned root mismatch')
        deps=gate._dependency_state(lean_workspace)
        tool=gate.resolve_toolchain(toolchain_root);env,git=gate._lean_environment(tool)
        suffix='.exe' if os.name=='nt' else '';lean,lake=tool/'bin'/('lean'+suffix),tool/'bin'/('lake'+suffix)
        executables={str(p):sha(gate._read_regular(p)) for p in (lean,lake,git)}
        version=gate._process([str(lean),'--version'],lean_workspace/gate.ROOT_PROJECT,env,timeout=30);result['commands'].append(version)
        require(version['returncode']==0 and not version['stderr'] and re.match(r'^Lean \(version 4\.31\.0(?:,|\))',version['stdout']),'wrong pinned Lean')
        result['status']='rejected'
        with tempfile.TemporaryDirectory(prefix='r17k-') as tmp:
            directory=Path(tmp).resolve(strict=True);argv=[str(lake),'--keep-toolchain','--no-cache','env',str(lean)]
            for label,raw in sources.items():
                path=directory/(label+'.lean');path.write_bytes(raw)
                cmd=gate._process([*argv,str(path)],lean_workspace/gate.ROOT_PROJECT,env,timeout=900);result['commands'].append(cmd)
                if label==LABELS[0]:
                    require(cmd['returncode']==0 and not cmd['stderr'],'producer certificate rejected');audits=parse_audits(cmd['stdout'])
                else:
                    diagnostic=cmd['stdout']+cmd['stderr']
                    require(cmd['returncode']==1 and 'error:' in diagnostic and 'decide' in diagnostic and 'false' in diagnostic,
                            'invalid provenance was not rejected by proof checking')
                    result['negative_controls_rejected'].append(label)
                require(path.read_bytes()==raw,'proof source changed')
        require(roots==gate.root_source_fingerprint(lean_workspace) and deps==gate._dependency_state(lean_workspace),'root/dependency changed')
        require(executables=={str(p):sha(gate._read_regular(p)) for p in (lean,lake,git)} and template(source_root)==raw_template,'tool/template changed')
        result.update(status='passed',finite_producer_replay_checked=True,root_provenance_fields_checked=True,
            theorem_axioms=audits,source_sha256={k:sha(v) for k,v in sources.items()},executable_sha256=executables,
            python_selection_hash_and_physical_binding_remains_trusted=True,trusted_import_cache_assumption=True,
            historical_execution_attested=False,self_hosted_neural_generator=False,complete_learned_kernel_constructed=False)
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        result['failure']={'type':type(exc).__name__,'reason':str(exc)}
    return result
