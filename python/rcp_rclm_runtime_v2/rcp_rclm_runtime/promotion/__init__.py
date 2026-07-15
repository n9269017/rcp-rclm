"""Phase 7 promotion-controller public API with lazy imports.

The package initializer deliberately avoids importing the controller or generator-facing
modules. This lets Phase 8 verify and replay immutable promotion evidence while the
original generator process and worker modules are unavailable.
"""

from __future__ import annotations

from importlib import import_module
from typing import Final

_EXPORTS: Final[dict[str, tuple[str, str]]] = {
    "Phase7CertificateEvidence": ("certificate", "Phase7CertificateEvidence"),
    "construct_reference_certificate": ("certificate", "construct_reference_certificate"),
    "GeneratorCallable": ("controller", "GeneratorCallable"),
    "LeanVerifierCallable": ("controller", "LeanVerifierCallable"),
    "Phase7AttemptExecution": ("controller", "Phase7AttemptExecution"),
    "run_phase7_promotion_controller": ("controller", "run_phase7_promotion_controller"),
    "Phase7EvaluationError": ("evaluator", "Phase7EvaluationError"),
    "Phase7EvaluationEvidence": ("evaluator", "Phase7EvaluationEvidence"),
    "evaluate_realized_candidate": ("evaluator", "evaluate_realized_candidate"),
    "PHASE7_CONTROLLER_ENVIRONMENT_HASH": ("policy", "PHASE7_CONTROLLER_ENVIRONMENT_HASH"),
    "PHASE7_CONTROLLER_POLICY_ID": ("policy", "PHASE7_CONTROLLER_POLICY_ID"),
    "phase7_run_id": ("policy", "phase7_run_id"),
    "reference_phase7_budget": ("policy", "reference_phase7_budget"),
    "reference_phase7_policy": ("policy", "reference_phase7_policy"),
    "PHASE7_ACTIVE_POINTER_SCHEMA_ID": ("records", "PHASE7_ACTIVE_POINTER_SCHEMA_ID"),
    "PHASE7_ATTEMPT_SCHEMA_ID": ("records", "PHASE7_ATTEMPT_SCHEMA_ID"),
    "PHASE7_BUDGET_SCHEMA_ID": ("records", "PHASE7_BUDGET_SCHEMA_ID"),
    "PHASE7_CONTROLLER_REPORT_SCHEMA_ID": ("records", "PHASE7_CONTROLLER_REPORT_SCHEMA_ID"),
    "PHASE7_LEDGER_SCHEMA_ID": ("records", "PHASE7_LEDGER_SCHEMA_ID"),
    "PHASE7_PACKAGE_SCHEMA_ID": ("records", "PHASE7_PACKAGE_SCHEMA_ID"),
    "PHASE7_POLICY_SCHEMA_ID": ("records", "PHASE7_POLICY_SCHEMA_ID"),
    "PHASE7_STAGE_SCHEMA_ID": ("records", "PHASE7_STAGE_SCHEMA_ID"),
    "Phase7ActivePointerRecord": ("records", "Phase7ActivePointerRecord"),
    "Phase7AttemptReport": ("records", "Phase7AttemptReport"),
    "Phase7ControllerBudgetRecord": ("records", "Phase7ControllerBudgetRecord"),
    "Phase7ControllerPolicyRecord": ("records", "Phase7ControllerPolicyRecord"),
    "Phase7ControllerReport": ("records", "Phase7ControllerReport"),
    "Phase7ImmutablePackageManifestRecord": ("records", "Phase7ImmutablePackageManifestRecord"),
    "Phase7LedgerEntryRecord": ("records", "Phase7LedgerEntryRecord"),
    "Phase7ReasonCode": ("records", "Phase7ReasonCode"),
    "Phase7StageResult": ("records", "Phase7StageResult"),
    "Phase7ReferenceTrajectoryEvidence": ("reference", "Phase7ReferenceTrajectoryEvidence"),
    "bootstrap_reference_phase7_store": ("reference", "bootstrap_reference_phase7_store"),
    "run_reference_phase7_controller_once": ("reference", "run_reference_phase7_controller_once"),
    "run_reference_phase7_trajectory": ("reference", "run_reference_phase7_trajectory"),
    "Phase7PromotionCommit": ("store", "Phase7PromotionCommit"),
    "Phase7StoreError": ("store", "Phase7StoreError"),
    "Phase7StoreLock": ("store", "Phase7StoreLock"),
    "Phase7StoreSnapshot": ("store", "Phase7StoreSnapshot"),
    "append_phase7_nonpromotion": ("store", "append_phase7_nonpromotion"),
    "bootstrap_phase7_store": ("store", "bootstrap_phase7_store"),
    "load_active_phase7_store": ("store", "load_active_phase7_store"),
    "promote_phase7_candidate": ("store", "promote_phase7_candidate"),
    "verify_immutable_phase7_package": ("store", "verify_immutable_phase7_package"),
}

__all__ = tuple(sorted(_EXPORTS))


def __getattr__(name: str) -> object:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(f"{__name__}.{module_name}"), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
