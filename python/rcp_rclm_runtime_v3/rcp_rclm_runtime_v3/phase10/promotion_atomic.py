from __future__ import annotations

import os
from pathlib import Path

from rcp_rclm_runtime.canonical.json import canonical_json_bytes
from rcp_rclm_runtime.promotion.store_verifier import load_active_phase7_store
from rcp_rclm_runtime.torch_backend.pilot_policy import pytorch_pilot_phase7_policy
from rcp_rclm_runtime_v3.phase10.lifecycle import Phase10Phase6Fixture
from rcp_rclm_runtime_v3.phase10.promotion import (
    Phase10PromotionEvidence,
    Phase10VerificationEvidence,
    promote_phase10_candidate as _promote_phase10_candidate,
)


def promote_phase10_candidate_atomic(
    fixture: Phase10Phase6Fixture,
    verification: Phase10VerificationEvidence,
    *,
    store_root: Path,
    evidence_root: Path,
    report_path: Path,
) -> Phase10PromotionEvidence:
    """Promote and retain the summary outside the immutable Phase 7 store layout."""

    result = _promote_phase10_candidate(
        fixture,
        verification,
        store_root=store_root,
        evidence_root=evidence_root,
    )
    transient_report = store_root.resolve(strict=True) / "phase10_promotion_report.json"
    resolved_report = report_path.resolve(strict=False)
    if resolved_report.exists():
        raise FileExistsError(f"promotion report already exists: {resolved_report}")
    resolved_report.parent.mkdir(parents=True, exist_ok=True)
    if transient_report.is_file():
        os.replace(transient_report, resolved_report)
    else:
        resolved_report.write_bytes(canonical_json_bytes(result.to_json()))
    reopened = load_active_phase7_store(store_root, pytorch_pilot_phase7_policy())
    if reopened.pointer != result.promotion.snapshot.pointer:
        raise ValueError("Phase 7 store changed while externalizing the promotion report")
    return result


__all__ = ["promote_phase10_candidate_atomic"]
