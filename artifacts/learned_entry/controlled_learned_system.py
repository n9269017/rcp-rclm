#!/usr/bin/env python3
"""Controlled learned-system object for the M3-Min audit harness.

The object in this file is deliberately modest: it represents a bounded,
certificate-gated, synthetic/controlled learned system whose post-training
update interface is constrained to the canonical closed-loop RCP/RCLM reference
class.  It is a bridge artifact for M3-Min learned-entry testing, not a claim
that arbitrary trained models enter the theorem domain.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


@dataclass
class ControlledLearnedSystem:
    """A small executable stand-in for M_theta in the M3-Min theorem boundary."""

    mode: str
    N: int
    seed: int
    architecture: str
    theta: List[float]
    bounded_update_grammar: List[str]
    excluded_capabilities: List[str]
    certificate_gate: str = "M3-Min learned-entry audit"
    learned_origin: str = "controlled synthetic learned-system surrogate"
    created_utc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["theta_hash"] = self.theta_hash()
        d["system_id"] = self.system_id()
        d["claim_boundary"] = {
            "controlled_learned_system_surrogate": True,
            "arbitrary_trained_system_entry": False,
            "frontier_scale_validation": False,
            "external_public_benchmark_result": False,
        }
        return d

    def theta_hash(self) -> str:
        return sha256_obj({"theta": self.theta, "mode": self.mode, "N": self.N, "seed": self.seed})

    def system_id(self) -> str:
        return sha256_obj({
            "mode": self.mode,
            "N": self.N,
            "seed": self.seed,
            "architecture": self.architecture,
            "theta_hash": self.theta_hash(),
            "bounded_update_grammar": self.bounded_update_grammar,
        })[:24]


def make_controlled_learned_system(mode: str, N: int, seed: int) -> ControlledLearnedSystem:
    if mode not in {"rcp", "rclm"}:
        raise ValueError("mode must be 'rcp' or 'rclm'")
    if N < 1:
        raise ValueError("N must be positive")
    rng = random.Random(f"{mode}:{N}:{seed}:m3-min")
    theta = [round(rng.uniform(-1.0, 1.0), 6) for _ in range(8)]
    grammar = [
        "valid_append_mem",
        "wrong_dimension_append",
        "noop_no_ability_expansion",
        "residual_positive",
        "recovery_breaking",
        "bad_goal_transport",
        "bad_trust_anchor",
        "bad_cost_bound",
        "bad_reality_containment",
    ]
    return ControlledLearnedSystem(
        mode=mode,
        N=N,
        seed=seed,
        architecture=f"controlled-{mode}-closed-loop-canonical",
        theta=theta,
        bounded_update_grammar=grammar,
        excluded_capabilities=[
            "unrestricted_code_rewriting",
            "unbounded_tool_use",
            "hidden_self_modification",
            "unbounded_environment_interaction",
            "arbitrary_trained_system_generalization",
        ],
        created_utc=datetime.now(timezone.utc).isoformat(),
    )


def write_controlled_system(path: Path, system: ControlledLearnedSystem) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    obj = system.to_dict()
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
    return obj
