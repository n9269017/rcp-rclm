from __future__ import annotations

import argparse
import json
from pathlib import Path

from rcp_rclm_runtime.canonical.hashing import canonical_json_hash
from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.generator.process import run_reference_generator_replay
from rcp_rclm_runtime.generator.records import GeneratorReasonCode
from rcp_rclm_runtime.generator.reference import build_reference_generator_input


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def run_replays(outdir: Path) -> int:
    resolved = outdir.resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, object]] = []
    ok = True
    for predecessor in ("initial", "target", "outside"):
        generator_input = build_reference_generator_input(predecessor)
        replay = run_reference_generator_replay(generator_input)
        case_dir = resolved / "cases" / predecessor
        _write_json(case_dir / "generator_input.json", generator_input.to_json())
        _write_json(case_dir / "generator_replay.json", replay.to_json())
        if replay.proposal is not None:
            _write_json(case_dir / "untrusted_proposal.json", replay.proposal.to_json())
        expected_status = "reject" if predecessor == "outside" else "generated"
        case_ok = replay.status == expected_status and replay.deterministic
        if predecessor == "outside":
            case_ok = case_ok and (
                GeneratorReasonCode.PREDECESSOR_OUTSIDE_DOMAIN in replay.reason_codes
            )
        cases.append(
            {
                "schema_id": "runtime.phase5_reference_replay_case.v2",
                "predecessor": predecessor,
                "expected_status": expected_status,
                "observed_status": replay.status,
                "deterministic": replay.deterministic,
                "reason_codes": [reason.value for reason in replay.reason_codes],
                "replay_hash": replay.report_hash,
                "ok": case_ok,
            }
        )
        ok = ok and case_ok
    payload = {
        "schema_id": "runtime.phase5_reference_replay_suite.v2",
        "case_count": len(cases),
        "generated_case_count": sum(
            1 for item in cases if item["observed_status"] == "generated"
        ),
        "rejected_case_count": sum(
            1 for item in cases if item["observed_status"] == "reject"
        ),
        "all_deterministic": all(item["deterministic"] is True for item in cases),
        "all_expected": ok,
        "cases": cases,
    }
    report = {**payload, "suite_hash": canonical_json_hash(payload)}
    _write_json(resolved / "phase_5_reference_replay_report.json", report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Phase 5A separate-process reference generator replay suite."
    )
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    return run_replays(args.outdir)


if __name__ == "__main__":
    raise SystemExit(main())
