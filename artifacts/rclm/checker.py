#!/usr/bin/env python3
"""Replay checker for the RCLM Batch-13R-B controlled executable reference artifact.

This script is an executable replay checker, not an external Lean/Coq/Isabelle/Agda proof certificate.
"""
from __future__ import annotations
import json, math, hashlib, sys
from pathlib import Path
from typing import Any, Dict, List

RES_KEYS=['seed','cand','ver','trans','goal','unc','trust','budget','persist','world','proof','sound']

def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',',':')).encode()

def sha_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()

def rel_ent(p: List[float], q: List[float]) -> float:
    total=0.0
    for pi,qi in zip(p,q):
        if pi == 0:
            continue
        if qi == 0:
            raise AssertionError('q has zero where p positive')
        total += pi*math.log(pi/qi,2)
    return total

def append_alpha(probs: List[float]) -> List[float]:
    out=[]
    for x in probs:
        out.extend([0.0,x])
    return out

def recover(probs: List[float]) -> List[float]:
    if len(probs)%2:
        raise AssertionError('length not divisible by 2')
    return [probs[i]+probs[i+1] for i in range(0,len(probs),2)]

def close(a: float,b: float,tol: float=1e-12) -> bool:
    return abs(a-b) <= tol

def check_artifact(artifact: Dict[str, Any]) -> Dict[str, Any]:
    assert artifact.get('artifact_type') == 'RCLM-Batch13R-B-controlled-executable-reference-system'
    N=int(artifact['horizon_N'])
    assert N>=2
    rho_states=artifact['states']['rho']
    sigma_states=artifact['states']['sigma']
    assert len(rho_states)==N+1 and len(sigma_states)==N+1
    assert rho_states[0] == [2/3,1/3]
    assert sigma_states[0] == [1/3,2/3]
    D0=rel_ent(rho_states[0], sigma_states[0])
    steps=0
    for t in range(N):
        rho=rho_states[t]; sig=sigma_states[t]
        rho_next=rho_states[t+1]; sig_next=sigma_states[t+1]
        assert rho_next == append_alpha(rho), f'rho transition mismatch at t={t}'
        assert sig_next == append_alpha(sig), f'sigma transition mismatch at t={t}'
        assert recover(rho_next)==rho, f'rho recovery mismatch at t={t}'
        assert recover(sig_next)==sig, f'sigma recovery mismatch at t={t}'
        assert close(rel_ent(rho_next,sig_next),D0), f'relative entropy mismatch at t={t}'
        ab_t=set(artifact['abilities'][t]); ab_next=set(artifact['abilities'][t+1])
        assert ab_t < ab_next, f'strict ability expansion failed at t={t}'
        assert f'a{t+1}' in ab_next-ab_t, f'missing new ability at t={t}'
        pcs=artifact['pcs'][t]
        assert pcs['candidate']==f'AppendMem(a{t+1})'
        assert pcs['checker_result']==1
        residuals=pcs['explicit_rclm_sv_residuals']
        for key in RES_KEYS:
            assert key in residuals, f'missing residual {key} at t={t}'
            assert residuals[key] <= 0, f'positive residual {key} at t={t}'
        assert pcs['goal_identity_drift']==0.0
        assert pcs['reality_containment']['contained'] is True
        assert pcs['reality_containment']['beta_env']==0.0
        assert pcs['reality_containment']['epsilon_env']==0.0
        steps += 1
    nN=len(rho_states[-1])
    assert artifact['tractability']['dense_cost_bound'] >= N*(nN**3)
    assert artifact['tractability']['diagonal_table_cost_bound'] >= N*nN
    expected_hashes={
        'states_sha256':sha_obj(artifact['states']),
        'abilities_sha256':sha_obj(artifact['abilities']),
        'pcs_sha256':sha_obj(artifact['pcs']),
        'artifact_without_hash_manifest_sha256':sha_obj({k:v for k,v in artifact.items() if k!='hash_manifest'})
    }
    assert artifact['hash_manifest']==expected_hashes
    return {
        'ok': True,
        'N': N,
        'artifact_hash': sha_obj(artifact),
        'final_dimension': nN,
        'relative_entropy_base2': D0,
        'steps_checked': steps,
        'explicit_rclm_residuals_checked': True,
        'non_noop_updates': True,
        'strict_ability_expansion': True,
        'singleton_reality_containment': True,
        'external_mechanization_certificate_supplied': artifact['external_mechanization']['certificate_supplied'],
        'mechanization_status': artifact['external_mechanization']['status'],
        'artifact_type': artifact['artifact_type']
    }

def main() -> None:
    path=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/mnt/data/rclm_batch13rB_controlled_artifact.json')
    artifact=json.loads(path.read_text())
    result=check_artifact(artifact)
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__':
    main()
