"""Check the typed learned-package projection; never authorize a full transition."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from . import lean_frontier_gate as gate
from .materialized import require, sha
from .learned_state_binding import PreparedLearnedBinding, check_packet, FIELDS, CLAIMS

BRIDGE_PATH = 'lean/phase17_bridge/LearnedStateBinding.lean'
BRIDGE_SHA256 = '2184da4d22db9d9d55f5978968f7ba4e4d769b07d22f86a81cef678cb730f8ab'
NAMES = tuple('Phase17LearnedBinding.'+n for n in (
    'frozen_view_preserved','fixed_interpretation_retained','information_value_retained',
    'root_information_bound','frontier_retained','frontier_grows',
    'selected_typed_binding','selected_interpretation_retention'))


def template(root: Path) -> bytes:
    p=root/BRIDGE_PATH
    require(p.is_file() and not p.is_symlink(),'missing/linked learned-binding template')
    raw=p.read_bytes().replace(b'\r\n',b'\n')
    require(sha(raw)==BRIDGE_SHA256,'learned-binding template differs')
    return raw


def _string(s: str) -> str:
    require(type(s) is str and not any(ord(c)<32 for c in s),'Lean string must be plain text')
    return json.dumps(s,ensure_ascii=False)


def _image(rows: list[dict]) -> str:
    return '['+', '.join('⟨'+_string(r['path'])+', '+str(r['size'])+', '+_string(r['sha256'])+'⟩' for r in rows)+']'


def _state(name: str, s: dict, *, corrupt: bool = False) -> str:
    fields=[]
    for f in FIELDS:
        rows=[dict(r) for r in s[f]]
        if corrupt and f=='modelWeights':
            rows[0]['sha256']='0'*64 if rows[0]['sha256']!='0'*64 else '1'*64
        fields.append('      '+f+' := '+_image(rows))
    registry='['+', '.join(_string(k) for k in s['base'])+']'
    tasks='(['+', '.join(_string(t) for t in s['capabilityFrontier'])+'] : List String).toFinset'
    return ('def '+name+' : BoundState :=\n'
            '  { package :=\n'
            '    { base := '+registry+'\n'+ '\n'.join(fields)+'\n'
            '      capabilityFrontier := '+tasks+' }\n'
            '    executionContext := '+_image(s['executionContext'])+'\n'
            '    packageHash := '+_string(s['package_hash'])+' }\n')


def render_binding(prepared: PreparedLearnedBinding, *, source_root: Path, negative: bool = False) -> bytes:
    require(type(prepared) is PreparedLearnedBinding and type(negative) is bool,'exact binding/control types')
    p=prepared.packet;check_packet(p)
    start=template(source_root).decode('utf-8')
    text=start+'\nnamespace Phase17LearnedBinding\nset_option maxRecDepth 16384\nset_option maxHeartbeats 4000000\n'
    text+='-- Measured binding packet SHA256: '+sha(prepared.packet_bytes)+'\n'
    text+=_state('observedBefore',p['predecessor'])+_state('observedAfter',p['candidate'],corrupt=negative)
    text+='def addedKey : String := '+_string(p['new_program'])+'\n'
    text+='def addedTask : String := '+_string(p['new_capability'])+'\n'
    text+='''
theorem selected_typed_binding :
    frozenView observedAfter = frozenView observedBefore ∧
    observedAfter.package.base = observedBefore.package.base ++ [addedKey] ∧
    observedAfter.package.capabilityFrontier = insert addedTask observedBefore.package.capabilityFrontier ∧
    addedTask ∉ observedBefore.package.capabilityFrontier ∧
    observedAfter.packageHash ≠ observedBefore.packageHash := by
  decide

theorem selected_interpretation_retention {Input Output : Type*}
    (interpret : List Image → Input → Output) (input : Input) :
    interpret (frozenView observedAfter) input = interpret (frozenView observedBefore) input :=
  fixed_interpretation_retained interpret observedBefore observedAfter selected_typed_binding.1 input

end Phase17LearnedBinding
'''
    text+='\n'.join('#print axioms '+n for n in NAMES)+'\n'
    raw=text.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b',raw),'forbidden generated token')
    return raw


def parse_audits(text: str) -> dict:
    cursor=0;out={}
    for name in NAMES:
        m=re.compile(r"'"+re.escape(name)+r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*",re.S).match(text,cursor)
        require(m is not None,'exact typed-binding theorem audit sequence required')
        out[name]=gate._axioms(m[0],name);cursor=m.end()
    require(cursor==len(text),'extra typed-binding audit output')
    return out


def check_learned_binding(prepared: PreparedLearnedBinding, *, source_root: Path,
                          lean_workspace: Path, toolchain_root: Path | None = None) -> dict:
    result={'schema_id':'runtime.v5.phase17.typed-learned-binding-lean.v1','status':'blocked',
            'packet_sha256':sha(prepared.packet_bytes),'commands':[],'theorem_axioms':{},
            'typed_learned_state_binding_checked':False,'fixed_interpretation_preservation_checked':False,
            'root_information_connection':'conditional_on_explicit_semantic_binding',
            'negative_component_substitution_rejected':False,
            'claims':{k:False for k in CLAIMS}}
    try:
        pos=render_binding(prepared,source_root=source_root)
        neg=render_binding(prepared,source_root=source_root,negative=True)
        local_template=template(source_root)
        roots=gate.root_source_fingerprint(lean_workspace)
        require({k:v['canonical_sha256'] for k,v in roots.items()}==
                {k:v['canonical_sha256'] for k,v in gate.root_source_fingerprint(source_root).items()},'root mismatch')
        deps=gate._dependency_state(lean_workspace)
        tool=gate.resolve_toolchain(toolchain_root);env,git=gate._lean_environment(tool)
        suffix='.exe' if os.name=='nt' else ''
        lean,lake=tool/'bin'/('lean'+suffix),tool/'bin'/('lake'+suffix)
        binaries={str(p):sha(gate._read_regular(p)) for p in (lean,lake,git)}
        version=gate._process([str(lean),'--version'],lean_workspace/gate.ROOT_PROJECT,env,timeout=30)
        result['commands'].append(version)
        require(version['returncode']==0 and not version['stderr'] and
                re.match(r'^Lean \(version 4\.31\.0(?:,|\))',version['stdout']),'wrong pinned Lean')
        result['status']='rejected'
        with tempfile.TemporaryDirectory(prefix='r17i-') as temporary:
            d=Path(temporary).resolve(strict=True);good=d/'Binding.lean';bad=d/'ChangedComponent.lean'
            good.write_bytes(pos);bad.write_bytes(neg)
            argv=[str(lake),'--keep-toolchain','--no-cache','env',str(lean)]
            accepted=gate._process([*argv,str(good)],lean_workspace/gate.ROOT_PROJECT,env,timeout=900)
            result['commands'].append(accepted)
            require(accepted['returncode']==0 and not accepted['stderr'],'typed learned binding rejected')
            audits=parse_audits(accepted['stdout'])
            rejected=gate._process([*argv,str(bad)],lean_workspace/gate.ROOT_PROJECT,env,timeout=900)
            result['commands'].append(rejected)
            require(rejected['returncode']==1 and 'error:' in rejected['stdout']+rejected['stderr'] and
                    'decide' in rejected['stdout']+rejected['stderr'],'changed component did not fail compiler check')
            require(good.read_bytes()==pos and bad.read_bytes()==neg,'proof source changed')
        require(roots==gate.root_source_fingerprint(lean_workspace) and deps==gate._dependency_state(lean_workspace),
                'root/dependency changed')
        require(binaries=={str(p):sha(gate._read_regular(p)) for p in (lean,lake,git)} and
                template(source_root)==local_template,'tool/template changed')
        result.update(status='passed',theorem_axioms=audits,
                      typed_learned_state_binding_checked=True,fixed_interpretation_preservation_checked=True,
                      negative_component_substitution_rejected=True,
                      positive_source_sha256=sha(pos),negative_source_sha256=sha(neg),
                      executable_sha256=binaries,physical_byte_literal_binding_remains_trusted=True,
                      trusted_import_cache_assumption=True)
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        result['failure']={'type':type(exc).__name__,'reason':str(exc)}
    return result
