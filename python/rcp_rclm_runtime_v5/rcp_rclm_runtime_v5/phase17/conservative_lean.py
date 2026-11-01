"""Strict pinned checking of a scoped concrete base kernel and semantic retention.

The proofs quantify over the protected byte image and fixed interpreter. Python
supplies the measured image equality and binds key/program literals to physical
files. This gate never emits a complete learned/autonomous root acceptance.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import tempfile

from .materialized import require, sha
from .successor_evidence import FALSE_CLAIMS
from .conservative_extension import PreparedConservative, SCHEMA, RegistryImage
from . import lean_frontier_gate as gate

BRIDGE_PATH='lean/phase17_bridge/ConservativeRegistry.lean'
BRIDGE_SHA256='a6b4b24d6f5b783ec12617608098bd6aafa2ae99262b87a2044626b5e4801098'
NAMES=('Phase17Registry.base_step_sound','Phase17Registry.dispatch_retained',
       'Phase17Registry.solved_task_retained','Phase17Registry.exact_recovery',
       'Phase17Registry.selected_base_step','Phase17Registry.selected_registry_mapping')


def literal(s: str) -> str:
    require(type(s) is str and s.isascii() and len(s) <= 4096 and all(32<=ord(c)<127 for c in s),
            'bounded printable Lean literal required')
    return json.dumps(s,ensure_ascii=True)


def _entries(rows: list[dict]) -> str:
    require(type(rows) is list and 0<len(rows)<=256, 'bounded registry rows required')
    return '['+', '.join('('+literal(r['key'])+', '+literal(r['program_utf8'])+')' for r in rows)+']'


def render(prepared: PreparedConservative, template: bytes, *, negative=False) -> bytes:
    require(type(prepared) is PreparedConservative and type(negative) is bool, 'exact prepared type required')
    normalized=template.replace(b'\r\n',b'\n')
    require(sha(normalized)==BRIDGE_SHA256,'registry bridge pin differs')
    p=prepared.packet
    require(p.get('schema_id')==SCHEMA and set(p['claims'])==set(FALSE_CLAIMS) and
            all(p['claims'][k] is False for k in FALSE_CLAIMS),'claim/schema mismatch')
    # Reconstruct typed data before emitting literals. This is not an authority
    # to accept candidate-authored packets: the production runner recomputes p.
    before=RegistryImage(tuple((r['key'],r['program_utf8'].encode()) for r in p['registry_before']))
    after=RegistryImage(tuple((r['key'],r['program_utf8'].encode()) for r in p['registry_after']))
    key=p['new_key'];raw=p['new_program_utf8'].encode()
    require(before.extend(key,raw)==after,'invalid append mapping')
    require(p['logical_append_order']==before.to_json()+[{'key':key,'program_utf8':raw.decode()}],
            'logical order mismatch')
    used,budget=p['search_used'],p['search_budget']
    require(type(used) is int and type(budget) is int and 0<used<=budget<=32,'candidate-credit shape')
    # A shadowed inherited identifier is an invalid update, not a false theorem
    # accepted as evidence. The original data are never mutated.
    chosen=before.entries[0][0] if negative else key
    tail='\nnamespace Phase17Registry\nset_option maxRecDepth 8192\nset_option maxHeartbeats 1000000\n'
    tail+='-- Measured packet SHA256: '+sha(prepared.packet_bytes)+'\n'
    tail+='def selectedBefore (image : List Nat) : State String := { protectedImage := image, entries := '+_entries(p['registry_before'])+', root := '+literal(p['fixed_verifier_hash'])+' }\n'
    tail+='def selectedUpdate : Update String := { key := '+literal(chosen)+', program := '+literal(raw.decode())+' }\n'
    tail+='def selectedEvidence : Evidence String := { root := '+literal(p['fixed_verifier_hash'])+', parentEntries := (selectedBefore []).entries, used := '+str(used)+', budget := '+str(budget)+' }\n'
    tail+='theorem selected_base_step (image : List Nat) (validBytes : ∀ n ∈ image, n < 256) :\n'
    tail+='    RcpRclmFormalCoreV2.RCP.StepObligations kernel (selectedBefore image)\n      ⟨selectedUpdate, apply (selectedBefore image) selectedUpdate⟩ selectedEvidence := by\n'
    tail+='  apply base_step_sound\n  · constructor\n    · change (selectedBefore []).root ≠ ""\n      decide\n    · exact validBytes\n  · change lookup selectedUpdate.key (selectedBefore []).entries = none\n    decide\n  · decide\n  · rfl\n  · rfl\n  · decide\n  · decide\n'
    # Exact list equality binds the executable manifest order to Lean.
    tail+='def selectedAfter : List (Entry String) := '+_entries(p['registry_after'])+'\n'
    tail+='theorem selected_registry_mapping :\n  selectedAfter = ((selectedBefore []).entries ++ [(selectedUpdate.key, selectedUpdate.program)]) := by decide\n'
    tail+='end Phase17Registry\n'+''.join('#print axioms '+n+'\n' for n in NAMES)
    source=normalized+tail.encode('utf-8')
    require(not re.search(rb'\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b',source),
            'forbidden proof token')
    return source


def parse_audits(stdout: str) -> dict:
    result={};cursor=0
    for name in NAMES:
        m=re.compile(r"'"+re.escape(name)+r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*",re.S).match(stdout,cursor)
        require(m is not None,'exact semantic audit names required')
        result[name]=gate._axioms(m[0],name);cursor=m.end()
    require(cursor==len(stdout),'additional audit output')
    return result


def check_conservative(prepared: PreparedConservative, *, source_root: Path,
                       lean_workspace: Path, toolchain_root: Path|None=None) -> dict:
    result={'schema_id':'runtime.v5.phase17.conservative-kernel-check.v1','status':'blocked',
            'packet_sha256':sha(prepared.packet_bytes),'commands':[],'theorem_axioms':{},
            'scoped_base_obligations_checked':False,'universal_registry_preservation_checked':False,
            'negative_shadowing_rejected':False,'base_obligation_count':11,
            'claims':{k:False for k in FALSE_CLAIMS}}
    try:
        template=(source_root/BRIDGE_PATH).read_bytes()
        positive=render(prepared,template);negative=render(prepared,template,negative=True)
        roots=gate.root_source_fingerprint(lean_workspace)
        deps=gate._dependency_state(lean_workspace)
        tool=gate.resolve_toolchain(toolchain_root);env,git=gate._lean_environment(tool)
        ext='.exe' if os.name=='nt' else ''
        lean,lake=tool/'bin'/('lean'+ext),tool/'bin'/('lake'+ext)
        tools={str(p):sha(gate._read_regular(p)) for p in (lean,lake,git)}
        version=gate._process([str(lean),'--version'],lean_workspace/gate.ROOT_PROJECT,env,timeout=30)
        result['commands'].append(version)
        require(version['returncode']==0 and not version['stderr'] and
                re.match(r'^Lean \(version 4\.31\.0(?:,|\))',version['stdout']), 'pinned Lean version mismatch')
        result['status']='rejected'
        with tempfile.TemporaryDirectory(prefix='r17g-') as temp:
            directory=Path(temp).resolve(strict=True)
            good,bad=directory/'Conservative.lean',directory/'Shadowed.lean'
            good.write_bytes(positive);bad.write_bytes(negative)
            argv=[str(lake),'--keep-toolchain','--no-cache','env',str(lean)]
            # Compile the real theorem first. A malformed template must never
            # count as successful rejection of the deliberately invalid witness.
            accepted=gate._process([*argv,str(good)],lean_workspace/gate.ROOT_PROJECT,env,timeout=600)
            result['commands'].append(accepted)
            require(accepted['returncode']==0 and not accepted['stderr'],'conservative certificate did not pass')
            audits=parse_audits(accepted['stdout'])
            rejected=gate._process([*argv,str(bad)],lean_workspace/gate.ROOT_PROJECT,env,timeout=600)
            result['commands'].append(rejected)
            diagnostic=rejected['stdout']+rejected['stderr']
            require(rejected['returncode']==1 and 'error:' in diagnostic and
                    'decide' in diagnostic and ('false' in diagnostic.lower() or 'failed' in diagnostic.lower()),
                    'compiler did not reject shadowed registry certificate')
            require(good.read_bytes()==positive and bad.read_bytes()==negative,'proof bytes changed')
        require(roots==gate.root_source_fingerprint(lean_workspace) and deps==gate._dependency_state(lean_workspace),
                'root/dependency changed')
        require(tools=={str(p):sha(gate._read_regular(p)) for p in (lean,lake,git)},'compiler changed')
        require((source_root/BRIDGE_PATH).read_bytes()==template,'semantic template changed')
        result.update(status='passed',theorem_axioms=audits,scoped_base_obligations_checked=True,
                      universal_registry_preservation_checked=True,negative_shadowing_rejected=True,
                      positive_source_sha256=sha(positive),negative_source_sha256=sha(negative),
                      executable_sha256=tools,trusted_import_cache_assumption=True,
                      physical_byte_and_literal_binding_remains_trusted=True)
    except (ValueError,OSError,__import__('subprocess').SubprocessError) as exc:
        result['failure']={'type':type(exc).__name__,'reason':str(exc)}
    return result
