#!/usr/bin/env python3
"""Schema helpers for the RCP/RCLM internal RSI benchmark harness.

The schema describes a controlled internal benchmark suite over the closed-loop
certified successor generator. It is intentionally not a SWE-bench/RE-Bench/etc.
external benchmark schema.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Mapping, Sequence

Mode = Literal["rcp", "rclm"]

DEFAULT_MODES: List[Mode] = ["rcp", "rclm"]
DEFAULT_HORIZONS: List[int] = [2, 3, 5, 10]
DEFAULT_SEEDS: List[int] = [0, 1, 2]


@dataclass(frozen=True)
class BenchmarkCase:
    mode: Mode
    N: int
    seed: int

    @property
    def case_id(self) -> str:
        return f"{self.mode}_N{self.N}_seed{self.seed}"

    @property
    def expected_generated_candidates(self) -> int:
        # Current closed-loop grammar generates 9 candidates per step.
        return 9 * self.N

    @property
    def expected_accepted_candidates(self) -> int:
        return self.N

    @property
    def expected_rejected_candidates(self) -> int:
        return 8 * self.N

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self) | {
            "case_id": self.case_id,
            "expected_generated_candidates": self.expected_generated_candidates,
            "expected_accepted_candidates": self.expected_accepted_candidates,
            "expected_rejected_candidates": self.expected_rejected_candidates,
        }


@dataclass
class BenchmarkConfig:
    modes: List[Mode]
    horizons: List[int]
    seeds: List[int]
    outdir: str
    allow_failures: bool = False

    def cases(self) -> List[BenchmarkCase]:
        out: List[BenchmarkCase] = []
        for mode in self.modes:
            for N in self.horizons:
                for seed in self.seeds:
                    out.append(BenchmarkCase(mode=mode, N=N, seed=seed))
        return out


def validate_horizon(N: int) -> None:
    if N < 2:
        raise ValueError("internal closed-loop benchmark requires N >= 2")


def validate_mode(mode: str) -> Mode:
    if mode not in {"rcp", "rclm"}:
        raise ValueError(f"unknown mode {mode!r}; expected 'rcp' or 'rclm'")
    return mode  # type: ignore[return-value]


def benchmark_case_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": ["mode", "N", "seed", "ok", "checker_passed", "generated_candidates", "accepted_candidates", "rejected_candidates"],
        "properties": {
            "mode": {"enum": ["rcp", "rclm"]},
            "N": {"type": "integer", "minimum": 2},
            "seed": {"type": "integer"},
            "ok": {"type": "boolean"},
            "checker_passed": {"type": "boolean"},
            "generated_candidates": {"type": "integer", "minimum": 0},
            "accepted_candidates": {"type": "integer", "minimum": 0},
            "rejected_candidates": {"type": "integer", "minimum": 0},
            "acceptance_rate": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "internal_certification_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "additionalProperties": True,
    }


def benchmark_summary_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": ["suite_name", "total_cases", "passed_cases", "failed_cases", "pass_rate", "all_cases_ok"],
        "properties": {
            "suite_name": {"type": "string"},
            "suite_scope": {"type": "string"},
            "total_cases": {"type": "integer", "minimum": 0},
            "passed_cases": {"type": "integer", "minimum": 0},
            "failed_cases": {"type": "integer", "minimum": 0},
            "pass_rate": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "all_cases_ok": {"type": "boolean"},
        },
        "additionalProperties": True,
    }
