#!/usr/bin/env python3
"""Self-test for HumanEval/32 semantic root predicate in certified_evalplus_harness.py.

This test checks the exact failure modes observed in the 40-task sidecar logs:
canonical exact-output mismatch values that are valid polynomial roots.
"""
from __future__ import annotations

from pathlib import Path
import sys

THIS = Path(__file__).resolve()
if str(THIS.parent) not in sys.path:
    sys.path.insert(0, str(THIS.parent))

from certified_evalplus_harness import run_one_test

CANONICAL = """import math\n\ndef poly(xs: list, x: float):\n    return sum([coeff * math.pow(x, i) for i, coeff in enumerate(xs)])\n\ndef find_zero(xs: list):\n    x = 0\n    while abs(poly(xs, x)) > 1e-4:\n        derivative = sum([i * coeff * math.pow(x, i - 1) for i, coeff in enumerate(xs) if i != 0])\n        x = x - poly(xs, x) / derivative\n    return x\n"""

# This is intentionally the previously failing numerically valid Newton/bisection-style solver.
SOLUTION = """import math\n\ndef poly(xs: list, x: float):\n    return sum([coeff * math.pow(x, i) for i, coeff in enumerate(xs)])\n\ndef find_zero(xs: list):\n    def dpoly(x):\n        return sum([i * coeff * math.pow(x, i - 1) for i, coeff in enumerate(xs) if i > 0])\n\n    x = 0.0\n    for _ in range(100):\n        fx = poly(xs, x)\n        if abs(fx) < 1e-10:\n            return x\n        dfx = dpoly(x)\n        if dfx == 0:\n            break\n        x = x - fx / dfx\n\n    lo, hi = -1.0, 1.0\n    while poly(xs, lo) * poly(xs, hi) > 0:\n        lo *= 2.0\n        hi *= 2.0\n\n    for _ in range(100):\n        mid = (lo + hi) / 2.0\n        if poly(xs, lo) * poly(xs, mid) > 0:\n            lo = mid\n        else:\n            hi = mid\n    return (lo + hi) / 2.0\n"""

TEST_INPUTS = [
    [[-3, 6, 9, -10]],
    [[2, -2, -8, -4, 8, 1]],
    [[1, 2]],
    [[-6, 11, -6, 1]],
]

all_ok = True
for inp in TEST_INPUTS:
    r = run_one_test(SOLUTION, CANONICAL, "find_zero", inp, 2.0, task_id="HumanEval/32")
    print(inp, r)
    all_ok = all_ok and bool(r.get("ok"))

bad = run_one_test("def find_zero(xs):\n    return 0\n", CANONICAL, "find_zero", [[2, -2, -8, -4, 8, 1]], 2.0, task_id="HumanEval/32")
print("bad_solution", bad)
if not all_ok:
    raise SystemExit(1)
if bad.get("ok"):
    raise SystemExit("bad solution unexpectedly passed")
print("HumanEval/32 semantic predicate self-test passed")
