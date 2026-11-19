"""Pinned new resource-tariff proofs; never complete root acceptance."""
from __future__ import annotations
import os
from pathlib import Path
import re
import tempfile

from . import lean_frontier_gate as gate
from .resource_ledger import Policy, cost, sha, require
from .metered_evaluation import FALSE_CLAIMS, selected_binding

TEMPLATE = "lean/phase17_bridge/ResourceAccounting.lean"
TEMPLATE_SHA256 = "0dedb05591770f67e8ede705930d3c850edc0ff4ada0bb6768033def975b3ca5"
NAMES = tuple("Phase17Resource." + n for n in (
    "cost_matches_weighted_counters", "counter_prefix_non_decreasing", "cost_prefix_non_decreasing",
    "bounded_final_implies_bounded_prefix", "over_budget_excluded", "appended_charge_not_refunded",
    "unrelated_fields_unchanged", "attached_resource_bound", "selected_usage", "selected_budget",
    "selected_bindings", "selected_failed_charge"))
LABELS = ("Resource", "OverBudget", "OmittedOperation", "RefundedFailure", "MixedCandidate")


def template(root: Path) -> bytes:
    path = root / TEMPLATE
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)), "missing/linked resource template")
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    require(sha(raw) == TEMPLATE_SHA256, "resource template pin differs")
    return raw


def render(report: dict, failure: dict, *, source_root: Path, negative: str | None = None) -> bytes:
    require(negative in (None, *LABELS[1:]), "unknown negative control")
    p = Policy.from_json(report["policy"])
    require(report["binding"] == selected_binding(), "resource transaction differs")
    kinds = list(report["charge_sequence"])
    require(len(kinds) == 153 and kinds.count("candidate") == 9 and kinds.count("vector") == 144,
            "selected work inventory differs")
    require(report["spent"] == [9, 144, 576, 576] and report["charged_cost"] == 4032,
            "selected work accounting differs")
    require(failure["charge_sequence"] == ["vector"] and failure["spent"] == [0, 1, 4, 4] and
            failure["status"] == "safety_halt" and failure["charged_cost"] == 24,
            "failed-operation charge missing")
    observed = [report["binding"][k] for k in sorted(selected_binding())]
    expected = observed.copy()
    if negative == "MixedCandidate":
        observed[sorted(selected_binding()).index("candidate_package_hash")] = "0" * 64
    if negative == "OmittedOperation":
        kinds.pop(0)
    failed_kinds = [] if negative == "RefundedFailure" else ["vector"]
    limit = 4031 if negative == "OverBudget" else p.cost_limit
    def ks(items):
        require(all(v in ("candidate", "vector") for v in items), "invalid charge kind")
        return "[" + ", ".join("." + v for v in items) + "]"
    def strings(items):
        require(all(re.fullmatch(r"[0-9a-f]{64}", s) for s in items), "invalid bound hash")
        return "[" + ", ".join('"'+s+'"' for s in items) + "]"
    text = template(source_root).decode("utf-8") + "\nnamespace Phase17Resource\n"
    text += "set_option maxRecDepth 8192\nset_option maxHeartbeats 4000000\n"
    text += "def selectedTrace : List Kind := " + ks(kinds) + "\n"
    text += "def failedTrace : List Kind := " + ks(failed_kinds) + "\n"
    text += "def selectedPolicy : Policy := { limits := fun i => ([" + ", ".join(map(str,p.limits)) + "] : List Nat).getD i.val 0, costLimit := " + str(limit) + " }\n"
    text += "def expectedBinding : List String := " + strings(expected) + "\n"
    text += "def observedBinding : List String := " + strings(observed) + "\n"
    text += """
theorem selected_usage :
    counter selectedTrace 0 = 9 ∧ counter selectedTrace 1 = 144 ∧
    counter selectedTrace 2 = 576 ∧ counter selectedTrace 3 = 576 ∧
    totalCost selectedTrace = 4032 := by decide

theorem selected_budget : Fits selectedPolicy selectedTrace := by
  unfold Fits
  decide

theorem selected_bindings : observedBinding = expectedBinding := by decide

theorem selected_failed_charge : failedTrace = [Kind.vector] ∧ totalCost failedTrace = 24 := by decide
end Phase17Resource
"""
    text += "\n".join("#print axioms " + n for n in NAMES) + "\n"
    raw = text.encode("utf-8")
    require(not re.search(rb"\b(sorry|sorryAx|admit|axiom|unsafe|partial|native_decide)\b", raw), "forbidden proof token")
    return raw


def parse_audits(output: str) -> dict:
    position, audits = 0, {}
    for name in NAMES:
        match = re.compile(r"'" + re.escape(name) + r"' (?:does not depend on any axioms|depends on axioms: \[[^\]]*\])\s*", re.S).match(output, position)
        require(match is not None, "exact resource audit sequence required")
        audits[name] = gate._axioms(match[0], name)
        position = match.end()
    require(position == len(output), "unexpected resource audit output")
    return audits


def check(report: dict, failure: dict, *, source_root: Path, lean_workspace: Path, toolchain_root: Path | None = None) -> dict:
    result = {"schema": "runtime.v5.phase17.resource-lean.v1", "status": "blocked", "commands": [],
              "theorem_axioms": {}, "negative_controls_rejected": [], "new_named_audits": len(NAMES),
              "scoped_resource_fields_checked": False, "claims": {k: False for k in FALSE_CLAIMS}}
    try:
        sources = {n: render(report,failure,source_root=source_root,negative=None if n == "Resource" else n) for n in LABELS}
        old_template = template(source_root)
        roots = gate.root_source_fingerprint(lean_workspace)
        require({k:v["canonical_sha256"] for k,v in roots.items()} ==
                {k:v["canonical_sha256"] for k,v in gate.root_source_fingerprint(source_root).items()}, "root mismatch")
        deps = gate._dependency_state(lean_workspace)
        tool = gate.resolve_toolchain(toolchain_root)
        env, git = gate._lean_environment(tool)
        suffix = ".exe" if os.name == "nt" else ""
        lean, lake = tool/"bin"/("lean"+suffix), tool/"bin"/("lake"+suffix)
        exes = {str(p):sha(gate._read_regular(p)) for p in (lean,lake,git)}
        version = gate._process([str(lean),"--version"],lean_workspace/gate.ROOT_PROJECT,env,timeout=30)
        result["commands"].append(version)
        require(version["returncode"] == 0 and not version["stderr"] and
                re.match(r"^Lean \(version 4\.31\.0(?:,|\))",version["stdout"]), "wrong pinned Lean")
        result["status"] = "rejected"
        with tempfile.TemporaryDirectory(prefix="r17n-") as tmp:
            folder = Path(tmp).resolve(strict=True)
            for label, data in sources.items():
                path = folder/(label+".lean")
                path.write_bytes(data)
                cmd = gate._process([str(lake),"--keep-toolchain","--no-cache","env",str(lean),str(path)],
                                    lean_workspace/gate.ROOT_PROJECT,env,timeout=600)
                result["commands"].append(cmd)
                if label == "Resource":
                    require(cmd["returncode"] == 0 and not cmd["stderr"], "resource certificate rejected")
                    audits = parse_audits(cmd["stdout"])
                else:
                    require(cmd["returncode"] == 1 and re.search(
                        r"error: Tactic `decide` proved that the proposition[\s\S]*?\bis false\b",
                        cmd["stdout"]+cmd["stderr"]) is not None, "negative did not reject false proposition")
                    result["negative_controls_rejected"].append(label)
                require(path.read_bytes() == data, "executed source changed")
        require(old_template == template(source_root) and roots == gate.root_source_fingerprint(lean_workspace) and
                deps == gate._dependency_state(lean_workspace), "root/template/dependencies changed")
        require(exes == {name:sha(gate._read_regular(Path(name))) for name in exes}, "tool bytes changed")
        result.update(status="passed", theorem_axioms=audits, scoped_resource_fields_checked=True,
                      source_sha256={n:sha(b) for n,b in sources.items()}, trusted_import_cache_assumption=True)
    except (ValueError, OSError, KeyError) as exc:
        result["failure"] = {"type":type(exc).__name__, "reason":str(exc)}
    return result
