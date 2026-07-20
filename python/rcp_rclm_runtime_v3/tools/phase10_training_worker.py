from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import torch

MODEL_WIDTH = 320
REPORT_SCHEMA_ID = "runtime.v3.phase10.training_report.v1"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_request(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("request must be an object")
    forbidden = (
        "heldout_task_ids_present",
        "heldout_prompts_present",
        "heldout_reference_answers_present",
    )
    if any(value.get(name) is not False for name in forbidden):
        raise ValueError("held-out material is forbidden")
    if value.get("optimizer_steps") != 1:
        raise ValueError("worker requires exactly one optimizer step")
    if value.get("learning_rate_numerator") != 1 or value.get("learning_rate_denominator") != 1:
        raise ValueError("worker requires exact learning rate one")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--predecessor-tensor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.manual_seed(1729)

    request = load_request(args.request)
    predecessor = args.predecessor_tensor.read_bytes()
    expected_size = MODEL_WIDTH * MODEL_WIDTH * 2
    if len(predecessor) != expected_size:
        raise ValueError("unexpected predecessor tensor size")
    predecessor_hash = sha256_hex(predecessor)
    if predecessor_hash != request.get("predecessor_tensor_sha256"):
        raise ValueError("predecessor tensor hash mismatch")

    raw_pairs = request.get("pairs")
    if not isinstance(raw_pairs, list) or not raw_pairs:
        raise ValueError("training pairs are required")
    offsets: list[int] = []
    initial_values: list[int] = []
    seen_currents: set[int] = set()
    for item in raw_pairs:
        if not isinstance(item, dict):
            raise ValueError("training pair must be an object")
        current = item.get("current_token_id")
        target = item.get("target_token_id")
        if isinstance(current, bool) or not isinstance(current, int):
            raise ValueError("current token must be an integer")
        if isinstance(target, bool) or not isinstance(target, int):
            raise ValueError("target token must be an integer")
        if not 0 <= current < 260 or not 0 <= target < 260:
            raise ValueError("training token outside vocabulary")
        if current in seen_currents:
            raise ValueError("current-token training inputs must be unique")
        seen_currents.add(current)
        offset = target * MODEL_WIDTH + current
        offsets.append(offset)
        initial_values.append(struct.unpack_from("<h", predecessor, offset * 2)[0])

    target_raw = request.get("target_raw_value")
    if isinstance(target_raw, bool) or not isinstance(target_raw, int):
        raise ValueError("target raw value must be an integer")
    parameter = torch.nn.Parameter(torch.tensor(initial_values, dtype=torch.float64))
    target_tensor = torch.full_like(parameter, float(target_raw))
    optimizer = torch.optim.SGD([parameter], lr=1.0, momentum=0.0, weight_decay=0.0)
    optimizer.zero_grad(set_to_none=True)
    loss = 0.5 * torch.sum((parameter - target_tensor) ** 2)
    loss_before = float(loss.detach().item())
    loss.backward()
    gradient_finite = bool(torch.isfinite(parameter.grad).all().item())
    if not gradient_finite:
        raise ValueError("nonfinite gradient")
    optimizer.step()
    loss_after_tensor = 0.5 * torch.sum((parameter - target_tensor) ** 2)
    loss_after = float(loss_after_tensor.detach().item())

    trained_values = [int(round(float(value))) for value in parameter.detach().tolist()]
    if any(value != target_raw for value in trained_values):
        raise ValueError("one-step exact training target was not reached")
    candidate = bytearray(predecessor)
    changed = 0
    for offset, before, after in zip(offsets, initial_values, trained_values, strict=True):
        if before != after:
            changed += 1
        struct.pack_into("<h", candidate, offset * 2, after)
    if changed < 1:
        raise ValueError("training produced no changed tensor entry")

    output = args.output.resolve(strict=False)
    output.mkdir(parents=True, exist_ok=False)
    tensor_bytes = bytes(candidate)
    candidate_hash = sha256_hex(tensor_bytes)
    (output / "model.layers.00.attn_output.weight.i16le.bin").write_bytes(tensor_bytes)
    report = {
        "schema_id": REPORT_SCHEMA_ID,
        "request_hash": hashlib.sha256(b"RCPRCLM-CANONICAL-JSON-V2\0" + canonical_json_bytes(request)).hexdigest(),
        "predecessor_tensor_sha256": predecessor_hash,
        "candidate_tensor_sha256": candidate_hash,
        "mode": request.get("mode"),
        "torch_version": str(torch.__version__),
        "device": "cpu",
        "training_dtype": "float64",
        "optimizer": "sgd",
        "optimizer_steps": 1,
        "loss_before": format(loss_before, ".17g"),
        "loss_after": format(loss_after, ".17g"),
        "gradient_finite": gradient_finite,
        "changed_entry_count": changed,
        "heldout_task_ids_consumed": False,
        "heldout_prompts_consumed": False,
        "heldout_reference_answers_consumed": False,
    }
    (output / "training_report.json").write_bytes(canonical_json_bytes(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
