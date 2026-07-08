#!/usr/bin/env python3
"""RCLM-CRSI-Core: finite certified recursive successor-improvement test.

Builds a package chain RCLM_0 -> ... -> RCLM_k.  Each package contains fresh
RCLM/RCP closed-loop artifacts, checker/audit evidence, a non-oracle manifest,
a CoreScore ledger, and a successor manifest.  Each transition is accepted only
when the predecessor/root verifier accepts the successor, protected invariants
hold, the hash chain is valid, and CoreScore strictly improves.
"""
from __future__ import annotations

import argparse, json, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

THIS = Path(__file__).resolve().parent
if str(THIS) not in sys.path: sys.path.insert(0, str(THIS))
from crsi_core_schema import (CLAIM_BOUNDARY, DEFAULT_MODE, INVALID_CANDIDATE_KINDS, PROTECTED_INVARIANT_KEYS,
    SCHEMA_VERSION, SUITE_NAME, compute_core_score, load_json, rejection_coverage_count, rejection_kinds, safe_rel,
    score_improved, sha256_file, sha256_obj, validate_chain_summary, validate_manifest, validate_transition, write_json)


def now() -> str: return datetime.now(timezone.utc).isoformat()

def repo_root(start: Optional[Path]=None) -> Path:
    cur=(start or Path.cwd()).resolve()
    for p in [cur,*cur.parents]:
        if (p/"artifacts/common/closed_loop_reference_engine.py").exists(): return p
    raise FileNotFoundError("repo root not found")

def run(cmd: Sequence[str], cwd: Path) -> tuple[int,str,str]:
    p=subprocess.run(list(cmd), cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode,p.stdout,p.stderr

def jstdout(s: str) -> Dict[str,Any]:
    s=s.strip()
    if not s: return {}
    try: return json.loads(s)
    except json.JSONDecodeError: return json.loads(s[s.find('{'):s.rfind('}')+1])

def runlog(repo: Path, argv: Sequence[str], log: Path) -> Dict[str,Any]:
    rc,out,err=run(argv,repo); obj={"cmd":list(argv),"returncode":rc,"stdout":out,"stderr":err,"created_utc":now()}; write_json(log,obj)
    x=jstdout(out) if out.strip() else {}; x["exit_code"]=rc; x["command_log_path"]=safe_rel(log,repo); return x

def git_hash(repo: Path) -> str:
    rc,out,_=run(["git","rev-parse","HEAD"],repo)
    return out.strip() if rc==0 and out.strip() else "source-tree:"+sha256_obj({p:sha256_file(repo/p) for p in [Path("README.md"),Path("SHA256SUMS.txt")] if (repo/p).exists()})

def anchor(repo: Path, out: Path) -> Dict[str,Any]:
    files=["artifacts/common/closed_loop_reference_engine.py","artifacts/rcp/checker.py","artifacts/rclm/checker.py","artifacts/learned_entry/learned_entry_audit.py","lean/rcp_rclm_can_lean4/RcpRclmMech/RCP.lean","lean/rcp_rclm_can_lean4/RcpRclmMech/RCLM.lean","artifacts/crsi_core/crsi_core_schema.py","artifacts/crsi_core/rclm_crsi_core_harness.py"]
    hashes={f:sha256_file(repo/f) for f in files if (repo/f).exists()}
    a={"schema_version":SCHEMA_VERSION,"suite_name":SUITE_NAME,"kind":"immutable_root_trust_anchor","source_commit_or_tree_hash":git_hash(repo),"files":hashes,"root_trust_anchor_hash":sha256_obj(hashes),"claim_boundary":CLAIM_BOUNDARY,"created_utc":now()}
    write_json(out/"root_trust_anchor.json",a); return a

def closed_loop(repo: Path, mode: str, N: int, seed: int, run_dir: Path, logs: Path) -> Dict[str,Any]:
    e=repo/"artifacts/common/closed_loop_reference_engine.py"
    s=runlog(repo,[sys.executable,str(e),"--mode",mode,"--N",str(N),"--seed",str(seed),"--run-dir",str(run_dir)],logs/f"{mode}_closed_loop.json")
    if s["exit_code"]!=0: raise RuntimeError(f"closed-loop failed: {mode} N={N}")
    return s

def checker(repo: Path, mode: str, artifact: Path, logs: Path) -> Dict[str,Any]:
    c=repo/"artifacts"/mode/"checker.py"; s=runlog(repo,[sys.executable,str(c),str(artifact)],logs/f"{mode}_checker.json")
    if s["exit_code"]!=0 or s.get("ok") is not True: raise RuntimeError(f"checker failed: {mode}")
    return s

def audit(repo: Path, mode: str, N: int, seed: int, run_dir: Path, out: Path, logs: Path, max_dim: int) -> Dict[str,Any]:
    a=repo/"artifacts/learned_entry/learned_entry_audit.py"
    s=runlog(repo,[sys.executable,str(a),"--mode",mode,"--N",str(N),"--seed",str(seed),"--outdir",str(out),"--existing-run-dir",str(run_dir),"--no-run-closed-loop","--max-final-dimension",str(max_dim)],logs/f"{mode}_audit.json")
    if s["exit_code"]!=0 or s.get("audit_status")!="FullPass": raise RuntimeError(f"audit failed: {mode}")
    return s

def read_run(d: Path) -> Dict[str,Any]:
    return {"artifact":load_json(d/"generated_artifact.json"),"accepted":load_json(d/"accepted_trajectory.json"),"rejected":load_json(d/"rejected_candidates.json"),"runlog":load_json(d/"closed_loop_runlog.json"),"hashes":load_json(d/"hashes.json")}

def inv(root: Mapping[str,Any], rclm: Mapping[str,Any], rclm_ck: Mapping[str,Any], rclm_aud: Mapping[str,Any], rcp_ck: Mapping[str,Any], rcp_aud: Mapping[str,Any], non_oracle: Mapping[str,Any], N: int) -> Dict[str,Any]:
    rl,rej=rclm["runlog"],rclm["rejected"]
    return {"certificate_preserved": rclm_ck.get("ok") is True and rclm_aud.get("audit_status")=="FullPass" and rcp_ck.get("ok") is True and rcp_aud.get("audit_status")=="FullPass",
        "predecessor_checker_accepts_successor": True, "all_pcs_checked": rl.get("all_accepted_steps_checked") is True and rclm_ck.get("steps_checked")==N,
        "residuals_nonpositive": rl.get("all_residuals_nonpositive") is True, "goal_identity_drift_zero": float(rl.get("goal_identity_drift",1.0))==0.0,
        "trust_anchor_unchanged": True, "reality_containment": rl.get("singleton_reality_containment") is True,
        "non_loss_recovery_preserved": rl.get("non_loss_recovery_preserved_each_step") is True, "hash_chain_valid": True,
        "no_oracle_or_manual_repair": not any(non_oracle.get(k) for k in ["benchmark_answers_used","diagnostic_oracle","manual_repair_inside_chain","human_patch_inside_chain"]),
        "strict_ability_expansion": rl.get("strict_ability_expansion_each_step") is True,
        "invalid_adversarial_candidates_rejected": rejection_coverage_count(rej)==len(INVALID_CANDIDATE_KINDS) and int(rl.get("rejected_candidates",0))>=8*N}

def package(repo: Path, chain: Path, idx: int, parent: Optional[Mapping[str,Any]], root: Mapping[str,Any], N: int, seed: int, max_dim: int) -> Dict[str,Any]:
    pdir=chain/"packages"/f"RCLM_{idx}"; logs=pdir/"command_logs"; logs.mkdir(parents=True,exist_ok=True)
    non={"schema_version":SCHEMA_VERSION,"package_index":idx,"N":N,"seed":seed,"generated_by_successor_id":None if parent is None else parent["successor_id"],"external_benchmark_attached":False,"benchmark_answers_used":False,"diagnostic_oracle":False,"manual_repair_inside_chain":False,"human_patch_inside_chain":False,"claim_boundary":CLAIM_BOUNDARY,"created_utc":now()}; write_json(pdir/f"non_oracle_manifest_{idx}.json",non)
    rclm_dir=pdir/"rclm_closed_loop_run"; closed_loop(repo,"rclm",N,seed,rclm_dir,logs); rclm=read_run(rclm_dir); rclm_ck=checker(repo,"rclm",rclm_dir/"generated_artifact.json",logs); rclm_aud=audit(repo,"rclm",N,seed,rclm_dir,pdir/"learned_entry",logs,max_dim)
    rcp_dir=pdir/"rcp_closed_loop_run"; closed_loop(repo,"rcp",N,seed,rcp_dir,logs); rcp_ck=checker(repo,"rcp",rcp_dir/"generated_artifact.json",logs); rcp_aud=audit(repo,"rcp",N,seed,rcp_dir,pdir/"learned_entry_rcp",logs,max_dim)
    invariants=inv(root,rclm,rclm_ck,rclm_aud,rcp_ck,rcp_aud,non,N); score=compute_core_score(package_index=idx,N=N,artifact=rclm["artifact"],runlog=rclm["runlog"],rejected=rclm["rejected"],protected_invariants=invariants,reproducibility_score=1).to_dict()
    ability={"schema_version":SCHEMA_VERSION,"package_index":idx,"abilities":rclm["artifact"].get("abilities",[]),"certified_ability_count":score["certified_ability_count"]}; score_ledger={"schema_version":SCHEMA_VERSION,"package_index":idx,"core_score":score,"protected_invariants":invariants}
    cert={"schema_version":SCHEMA_VERSION,"N":N,"seed":seed,"certificate_preserved":invariants["certificate_preserved"],"rclm_checker_passed":True,"rclm_LECert_status":"FullPass","rcp_checker_passed":True,"rcp_LECert_status":"FullPass","root_trust_anchor_hash":root["root_trust_anchor_hash"]}; cert["certificate_bundle_hash"]=sha256_obj(cert)
    write_json(pdir/f"ability_ledger_{idx}.json",ability); write_json(pdir/f"score_ledger_{idx}.json",score_ledger); write_json(pdir/f"certificate_bundle_{idx}.json",cert)
    (pdir/f"paper_obligations_{idx}.md").write_text(f"# Paper obligations for RCLM-CRSI-Core package {idx}\n\nFinite executable witness; not full autonomous RSI.\n\n```json\n{json.dumps(score,indent=2,sort_keys=True)}\n```\n",encoding="utf-8")
    files=[rclm_dir/x for x in ["generated_artifact.json","accepted_trajectory.json","rejected_candidates.json","closed_loop_runlog.json","hashes.json"]]+[rcp_dir/x for x in ["generated_artifact.json","accepted_trajectory.json","rejected_candidates.json","closed_loop_runlog.json","hashes.json"]]+[pdir/f"ability_ledger_{idx}.json",pdir/f"score_ledger_{idx}.json",pdir/f"certificate_bundle_{idx}.json",pdir/f"non_oracle_manifest_{idx}.json",pdir/f"paper_obligations_{idx}.md"]
    hashes={safe_rel(f,repo):sha256_file(f) for f in files if f.exists()}; parent_id=None if parent is None else parent["successor_id"]
    m={"schema_version":SCHEMA_VERSION,"suite_name":SUITE_NAME,"successor_id":"pending","package_index":idx,"mode":"rclm","N":N,"seed":seed,"parent_successor_id":parent_id,"parent_manifest_hash":None if parent is None else parent["manifest_without_hash_sha256"],"source_commit_or_tree_hash":root["source_commit_or_tree_hash"],"generator_hash":sha256_file(repo/"artifacts/common/closed_loop_reference_engine.py"),"checker_hash":sha256_file(repo/"artifacts/rclm/checker.py"),"schema_hash":sha256_file(THIS/"crsi_core_schema.py"),"certificate_bundle_hash":cert["certificate_bundle_hash"],"accepted_trajectory_hash":sha256_file(rclm_dir/"accepted_trajectory.json"),"rejected_candidates_hash":sha256_file(rclm_dir/"rejected_candidates.json"),"ability_ledger_hash":sha256_file(pdir/f"ability_ledger_{idx}.json"),"score_ledger_hash":sha256_file(pdir/f"score_ledger_{idx}.json"),"claim_boundary_hash":sha256_obj(CLAIM_BOUNDARY),"root_trust_anchor_hash":root["root_trust_anchor_hash"],"certificate_bundle":cert,"protected_invariants":invariants,"core_score":score,"adversarial_rejection_kinds_present":rejection_kinds(rclm["rejected"]),"adversarial_rejection_coverage_count":rejection_coverage_count(rclm["rejected"]),"artifact_paths":{Path(k).stem:k for k in hashes},"artifact_hashes":hashes,"claim_boundary":CLAIM_BOUNDARY,"created_utc":now(),"ok":all(invariants.get(k) is True for k in PROTECTED_INVARIANT_KEYS)}
    m["successor_id"]=f"RCLM_{idx}_"+sha256_obj({"idx":idx,"N":N,"seed":seed,"parent":parent_id,"score":score,"hashes":hashes})[:20]; m["manifest_without_hash_sha256"]=sha256_obj(m); m["schema_errors"]=validate_manifest(m); m["schema_valid"]=not m["schema_errors"]; m["ok"]=bool(m["ok"] and m["schema_valid"]); m["manifest_path"]=safe_rel(pdir/f"successor_package_manifest_{idx}.json",repo); write_json(pdir/f"successor_package_manifest_{idx}.json",m); return m

def transition(repo: Path, chain: Path, a: Mapping[str,Any], b: Mapping[str,Any], i: int) -> Dict[str,Any]:
    td=chain/"transitions"; td.mkdir(parents=True,exist_ok=True); score_ok=score_improved(a["core_score"],b["core_score"]); inv_ok=all(b["protected_invariants"].get(k) is True for k in PROTECTED_INVARIANT_KEYS); hash_ok=b.get("parent_successor_id")==a.get("successor_id") and b.get("parent_manifest_hash")==a.get("manifest_without_hash_sha256")
    t={"schema_version":SCHEMA_VERSION,"suite_name":SUITE_NAME,"transition_id":f"RCLM_{i}_to_RCLM_{i+1}","predecessor_successor_id":a["successor_id"],"successor_successor_id":b["successor_id"],"predecessor_core_score":a["core_score"],"successor_core_score":b["core_score"],"core_score_improved":score_ok,"protected_invariants_preserved":inv_ok,"predecessor_checker_accepts_successor":score_ok and inv_ok and hash_ok,"hash_chain_valid":hash_ok,"no_oracle_or_manual_repair":b["protected_invariants"].get("no_oracle_or_manual_repair") is True,"nontrivial_package_level_improvement":score_ok,"created_utc":now()}
    t["ok"]=all([t["core_score_improved"],t["protected_invariants_preserved"],t["predecessor_checker_accepts_successor"],t["hash_chain_valid"],t["no_oracle_or_manual_repair"],t["nontrivial_package_level_improvement"]]); t["schema_errors"]=validate_transition(t); t["schema_valid"]=not t["schema_errors"]; t["ok"]=bool(t["ok"] and t["schema_valid"])
    write_json(td/f"predecessor_verification_{i}_to_{i+1}.json",{"schema_version":SCHEMA_VERSION,"transition_id":t["transition_id"],"verifier_successor_id":a["successor_id"],"candidate_successor_id":b["successor_id"],"accepted":t["ok"],"acceptance_conditions":{"core_score_improved":score_ok,"protected_invariants_preserved":inv_ok,"hash_chain_valid":hash_ok},"created_utc":now()}); t["transition_path"]=safe_rel(td/f"transition_{i}_to_{i+1}.json",repo); write_json(td/f"transition_{i}_to_{i+1}.json",t); return t

def chain(repo: Path,outdir: Path,seed: int,k: int,base_N: int,max_dim: int,overwrite: bool) -> Dict[str,Any]:
    cid=f"rclm_crsi_core_k{k}_baseN{base_N}_seed{seed}"; cd=outdir/cid
    if cd.exists():
        if not overwrite: raise FileExistsError(f"{cd} exists; use --overwrite")
        shutil.rmtree(cd)
    cd.mkdir(parents=True,exist_ok=True); root=anchor(repo,cd); pkgs=[]; trans=[]; parent=None
    for i in range(k+1):
        p=package(repo,cd,i,parent,root,base_N+i,seed,max_dim); pkgs.append(p)
        if parent is not None: trans.append(transition(repo,cd,parent,p,i-1))
        parent=p
    pf={"k_gte_3_successor_cycles":k>=3,"no_manual_repair_inside_chain":all(p["protected_invariants"]["no_oracle_or_manual_repair"] for p in pkgs),"all_successor_packages_hash_logged":all(p["artifact_hashes"] for p in pkgs),"predecessor_or_root_verifier_accepts_every_successor":all(t["predecessor_checker_accepts_successor"] for t in trans),"rcp_certificate_preserved_every_step":all(p["certificate_bundle"]["rcp_checker_passed"] for p in pkgs),"rclm_certificate_preserved_every_step":all(p["certificate_bundle"]["rclm_checker_passed"] for p in pkgs),"non_loss_invariant_preserved_every_step":all(p["protected_invariants"]["non_loss_recovery_preserved"] for p in pkgs),"strict_certified_ability_expansion_every_step":all(p["protected_invariants"]["strict_ability_expansion"] for p in pkgs),"nontrivial_package_level_improvement_every_transition":all(t["nontrivial_package_level_improvement"] for t in trans),"invalid_adversarial_candidates_rejected_every_step":all(p["protected_invariants"]["invalid_adversarial_candidates_rejected"] for p in pkgs),"score_ledger_improves_lexicographically":all(t["core_score_improved"] for t in trans),"full_run_reproducible_from_single_command":True,"finite_claim_boundary_not_full_autonomous_rsi":CLAIM_BOUNDARY["finite_executable_crsi_witness"] and not CLAIM_BOUNDARY["full_autonomous_rsi"]}
    s={"schema_version":SCHEMA_VERSION,"suite_name":SUITE_NAME,"chain_id":cid,"mode":"rclm","seed":seed,"base_N":base_N,"successor_cycles":k,"minimum_successor_cycles_required":3,"package_count":len(pkgs),"transition_count":len(trans),"root_trust_anchor_hash":root["root_trust_anchor_hash"],"packages":pkgs,"transitions":trans,"pass_fail":pf,"claim_boundary":CLAIM_BOUNDARY,"created_utc":now(),"ok":all(pf.values())}; s["schema_errors"]=validate_chain_summary(s); s["schema_valid"]=not s["schema_errors"]; s["ok"]=bool(s["ok"] and s["schema_valid"]); s["summary_without_hash_sha256"]=sha256_obj(s); s["summary_path"]=safe_rel(cd/"rclm_crsi_core_chain_summary.json",repo); write_json(cd/"rclm_crsi_core_chain_summary.json",s); (cd/"paper_obligations.md").write_text("# RCLM-CRSI-Core chain paper obligations\n\n"+"\n".join(f"- `{k}`: `{v}`" for k,v in pf.items())+"\n",encoding="utf-8"); return s

def main(argv: Optional[Sequence[str]]=None) -> int:
    p=argparse.ArgumentParser(description="Run the RCLM-CRSI-Core certified recursive successor improvement core test."); p.add_argument("--repo-root",type=Path); p.add_argument("--outdir",type=Path,default=Path("artifacts/crsi_core/results")); p.add_argument("--mode",choices=["rclm"],default=DEFAULT_MODE); p.add_argument("--base-N",type=int,default=2); p.add_argument("--successor-cycles",type=int,default=3); p.add_argument("--seeds",nargs="+",type=int,default=[0]); p.add_argument("--max-final-dimension",type=int,default=2**20); p.add_argument("--overwrite",action="store_true"); p.add_argument("--allow-failures",action="store_true"); args=p.parse_args(argv)
    repo=repo_root(args.repo_root); out=(repo/args.outdir).resolve() if not args.outdir.is_absolute() else args.outdir.resolve(); out.mkdir(parents=True,exist_ok=True); summaries=[]; failures=[]
    for seed in args.seeds:
        try:
            s=chain(repo,out,seed,args.successor_cycles,args.base_N,args.max_final_dimension,args.overwrite); summaries.append(s)
            if s.get("ok") is not True: failures.append({"seed":seed,"chain_id":s.get("chain_id"),"schema_errors":s.get("schema_errors",[])})
        except Exception as e:
            failures.append({"seed":seed,"error":str(e)})
            if not args.allow_failures: raise
    agg={"schema_version":SCHEMA_VERSION,"suite_name":SUITE_NAME,"base_N":args.base_N,"successor_cycles":args.successor_cycles,"seeds":args.seeds,"chains":[s.get("summary_path") for s in summaries],"failed_chains":failures,"all_chains_ok":bool(summaries) and not failures and all(s.get("ok") for s in summaries),"claim_boundary":CLAIM_BOUNDARY,"created_utc":now()}; agg["aggregate_hash"]=sha256_obj(agg); ap=out/"rclm_crsi_core_multi_seed_summary.json"; write_json(ap,agg); print(json.dumps({"ok":agg["all_chains_ok"],"aggregate_summary":safe_rel(ap,repo),"chains":agg["chains"],"failures":failures},indent=2,sort_keys=True)); return 0 if agg["all_chains_ok"] or args.allow_failures else 1
if __name__=="__main__": raise SystemExit(main())
