from __future__ import annotations

import argparse
import struct
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message=r"Failed to initialize NumPy.*",
    category=UserWarning,
)

import torch

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash, sha256_hex
from rcp_rclm_runtime.canonical.json import canonical_json_bytes, load_json_strict


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--tensor-out", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    args = parser.parse_args()
    request = load_json_strict(args.request.resolve(strict=True).read_bytes(), require_canonical=True)
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    if request.get("schema_id") != "runtime.v3.phase12e.training_request.v1":
        raise ValueError("request schema mismatch")
    element_count = request.get("tensor_element_count")
    targets = request.get("target_raw_values")
    steps = request.get("optimizer_steps")
    seed = request.get("seed")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (element_count, steps, seed)):
        raise ValueError("training integers are malformed")
    if (
        not isinstance(targets, list)
        or len(targets) != 4
        or any(isinstance(value, bool) or not isinstance(value, int) for value in targets)
    ):
        raise ValueError("training targets are malformed")
    if element_count < len(targets) or steps != 1 or request.get("heldout_material_present") is not False:
        raise ValueError("training request violates the selected boundary")
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    parameter = torch.nn.Parameter(torch.zeros(element_count, dtype=torch.float32))
    optimizer = torch.optim.SGD([parameter], lr=1.0, momentum=0.0)
    optimizer.zero_grad(set_to_none=True)
    target_tensor = torch.tensor(targets, dtype=torch.float32)
    loss = 0.5 * torch.sum((parameter[: len(targets)] - target_tensor) ** 2)
    loss.backward()
    optimizer.step()
    values = parameter.detach().round().to(torch.int16).tolist()
    if values[: len(targets)] != targets or any(value != 0 for value in values[len(targets) :]):
        raise ValueError("selected one-step adapter training result differs")
    content = struct.pack("<" + "h" * element_count, *values)
    args.tensor_out.parent.mkdir(parents=True, exist_ok=True)
    args.tensor_out.write_bytes(content)
    request_hash = canonical_json_hash(request)
    report = {
        "schema_id": "runtime.v3.phase12e.training_worker_report.v1",
        "accepted": True,
        "request_hash": request_hash,
        "candidate_tensor_sha256": sha256_hex(content),
        "optimizer": "sgd",
        "optimizer_steps": 1,
        "loss_before_numerator": sum(value * value for value in targets),
        "loss_before_denominator": 2,
        "loss_after_numerator": 0,
        "loss_after_denominator": 1,
        "heldout_material_consumed": False,
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_bytes(canonical_json_bytes(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
