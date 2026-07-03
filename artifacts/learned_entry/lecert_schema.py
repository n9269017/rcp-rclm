#!/usr/bin/env python3
"""Schema and validation helpers for M3-Min learned-entry certificates.

This module intentionally uses only the Python standard library.  It defines a
small executable representation of the M3-Min learned-entry boundary from the
RCP/RCLM papers:

    LearnedEntryAudit_{0:N}(M_theta, D, L, C) ⇓ LECert_{0:N}

If every required certificate component is true, the audit status is FullPass.
If some but not all are supplied, the status is PartialPass.  If the underlying
closed-loop run or checker fails, the status is Fail.

Scope boundary:
    - This is a controlled learned-system entry audit harness.
    - It is not a proof that arbitrary trained systems satisfy the boundary.
    - It is not an external public AI-agent benchmark result.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple

CERTIFICATE_FIELDS: Tuple[str, ...] = (
    "TypeCert",
    "RegSemCert",
    "CoverageCert",
    "SVWitLib",
    "SVBuilderTrace",
    "PCS",
    "Q_SV_A_nonpositive",
    "GoalId",
    "TrustRef",
    "RealCont",
    "SVTract",
    "ReplayTrace",
)

# Human-readable mapping from executable field names to paper notation.
CERTIFICATE_SYMBOLS: Dict[str, str] = {
    "TypeCert": r"\\mathsf{TypeCert}_{0:N}",
    "RegSemCert": r"\\mathsf{RegSemCert}_{0:N}",
    "CoverageCert": r"\\mathsf{CoverageCert}_{0:N}",
    "SVWitLib": r"\\mathsf{SVWitLib}_{0:N}",
    "SVBuilderTrace": r"\\mathsf{SVBuilderTrace}_{0:N}",
    "PCS": r"\\mathsf{PCS}_{0:N}",
    "Q_SV_A_nonpositive": r"Q_{0:N}^{\\mathrm{SV},A}\\le 0",
    "GoalId": r"\\mathsf{GoalId}_{0:N}",
    "TrustRef": r"\\mathsf{TrustRef}_{0:N}",
    "RealCont": r"\\mathsf{RealCont}_{0:N}",
    "SVTract": r"\\mathsf{SVTract}_{0:N}",
    "ReplayTrace": r"\\mathsf{ReplayTrace}_{0:N}",
}

FULL_PASS = "FullPass"
PARTIAL_PASS = "PartialPass"
FAIL = "Fail"


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


@dataclass
class CertificateComponent:
    """One audit component in the learned-entry certificate packet."""

    name: str
    passed: bool
    evidence: Dict[str, Any] = field(default_factory=dict)
    failure_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LearnedEntryCertificate:
    """Executable version of LECert_{0:N} for a controlled learned system."""

    mode: str
    N: int
    seed: int
    learned_system_id: str
    components: Dict[str, CertificateComponent]
    source_paths: Dict[str, str]
    claim_boundary: Dict[str, bool]
    notes: List[str] = field(default_factory=list)

    def field_booleans(self) -> Dict[str, bool]:
        return {field: bool(self.components[field].passed) for field in CERTIFICATE_FIELDS}

    def missing_fields(self) -> List[str]:
        return [field for field in CERTIFICATE_FIELDS if not self.components[field].passed]

    def status(self, closed_loop_ok: bool, checker_passed: bool) -> str:
        if not closed_loop_ok or not checker_passed:
            return FAIL
        if all(self.field_booleans().values()):
            return FULL_PASS
        return PARTIAL_PASS

    def to_dict(self, closed_loop_ok: bool, checker_passed: bool) -> Dict[str, Any]:
        field_booleans = self.field_booleans()
        return {
            "audit_status": self.status(closed_loop_ok, checker_passed),
            "mode": self.mode,
            "N": self.N,
            "seed": self.seed,
            "learned_system_id": self.learned_system_id,
            **field_booleans,
            "missing_fields": self.missing_fields(),
            "components": {k: v.to_dict() for k, v in self.components.items()},
            "source_paths": self.source_paths,
            "claim_boundary": self.claim_boundary,
            "notes": list(self.notes),
            "certificate_hash": sha256_obj({
                "mode": self.mode,
                "N": self.N,
                "seed": self.seed,
                "learned_system_id": self.learned_system_id,
                "fields": field_booleans,
                "components": {k: v.to_dict() for k, v in self.components.items()},
                "source_paths": self.source_paths,
                "claim_boundary": self.claim_boundary,
                "notes": self.notes,
            }),
        }


def make_component(name: str, passed: bool, evidence: Optional[Dict[str, Any]] = None, failure_reasons: Optional[Iterable[str]] = None) -> CertificateComponent:
    if name not in CERTIFICATE_FIELDS:
        raise ValueError(f"Unknown certificate field: {name}")
    return CertificateComponent(
        name=name,
        passed=bool(passed),
        evidence=dict(evidence or {}),
        failure_reasons=list(failure_reasons or []),
    )


def summarize_components(components: Mapping[str, CertificateComponent]) -> Dict[str, Any]:
    total = len(CERTIFICATE_FIELDS)
    passed = sum(1 for field in CERTIFICATE_FIELDS if components[field].passed)
    return {
        "total_components": total,
        "passed_components": passed,
        "failed_components": total - passed,
        "component_pass_rate": passed / total if total else 0.0,
        "missing_fields": [field for field in CERTIFICATE_FIELDS if not components[field].passed],
    }


def validate_lecert_dict(lecert: Mapping[str, Any]) -> Tuple[bool, List[str]]:
    """Validate a serialized LECert-like dictionary.

    Returns (ok, errors).  The validation is intentionally strict about field
    presence and intentionally conservative about what a FullPass means.
    """
    errors: List[str] = []
    for field in CERTIFICATE_FIELDS:
        if field not in lecert:
            errors.append(f"missing field {field}")
        elif not isinstance(lecert[field], bool):
            errors.append(f"field {field} is not boolean")
    if lecert.get("audit_status") == FULL_PASS:
        for field in CERTIFICATE_FIELDS:
            if lecert.get(field) is not True:
                errors.append(f"FullPass requires {field}=true")
    if lecert.get("audit_status") not in {FULL_PASS, PARTIAL_PASS, FAIL}:
        errors.append("audit_status must be FullPass, PartialPass, or Fail")
    return (len(errors) == 0, errors)
