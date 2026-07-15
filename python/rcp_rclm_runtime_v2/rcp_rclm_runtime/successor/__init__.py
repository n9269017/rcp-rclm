"""Phase 6 successor-package public API with lazy imports.

Keeping this initializer side-effect free lets Phase 8 import the verifier and realizer
without importing the Phase 5 generator process through the Phase 6 reference helpers.
"""

from __future__ import annotations

from importlib import import_module
from typing import Final

_EXPORTS: Final[dict[str, tuple[str, str]]] = {
    "PHASE6_BUDGET_SCHEMA_ID": ("records", "PHASE6_BUDGET_SCHEMA_ID"),
    "PHASE6_CANDIDATE_MANIFEST_SCHEMA_ID": ("records", "PHASE6_CANDIDATE_MANIFEST_SCHEMA_ID"),
    "PHASE6_COMMAND_SCHEMA_ID": ("records", "PHASE6_COMMAND_SCHEMA_ID"),
    "PHASE6_ENVIRONMENT_SCHEMA_ID": ("records", "PHASE6_ENVIRONMENT_SCHEMA_ID"),
    "PHASE6_FILE_CHANGE_SCHEMA_ID": ("records", "PHASE6_FILE_CHANGE_SCHEMA_ID"),
    "PHASE6_OPERATION_SCHEMA_ID": ("records", "PHASE6_OPERATION_SCHEMA_ID"),
    "PHASE6_PACKAGE_REPORT_SCHEMA_ID": ("records", "PHASE6_PACKAGE_REPORT_SCHEMA_ID"),
    "PHASE6_PREDECESSOR_MANIFEST_SCHEMA_ID": ("records", "PHASE6_PREDECESSOR_MANIFEST_SCHEMA_ID"),
    "PHASE6_REALIZATION_SCHEMA_ID": ("records", "PHASE6_REALIZATION_SCHEMA_ID"),
    "PHASE6_RESOURCE_USAGE_SCHEMA_ID": ("records", "PHASE6_RESOURCE_USAGE_SCHEMA_ID"),
    "PHASE6_ROLLBACK_SCHEMA_ID": ("records", "PHASE6_ROLLBACK_SCHEMA_ID"),
    "PHASE6_SELECTION_SCHEMA_ID": ("records", "PHASE6_SELECTION_SCHEMA_ID"),
    "LoadedPredecessorPackage": ("workspace", "LoadedPredecessorPackage"),
    "Phase6CandidateManifestRecord": ("records", "Phase6CandidateManifestRecord"),
    "Phase6CommandRecord": ("records", "Phase6CommandRecord"),
    "Phase6EnvironmentRecord": ("records", "Phase6EnvironmentRecord"),
    "Phase6FileChangeRecord": ("records", "Phase6FileChangeRecord"),
    "Phase6PackageBuildEvidence": ("package_builder", "Phase6PackageBuildEvidence"),
    "Phase6PackageReport": ("records", "Phase6PackageReport"),
    "Phase6PredecessorManifestRecord": ("records", "Phase6PredecessorManifestRecord"),
    "Phase6RealizationDraft": ("realizer", "Phase6RealizationDraft"),
    "Phase6RealizationRecord": ("records", "Phase6RealizationRecord"),
    "Phase6ReasonCode": ("records", "Phase6ReasonCode"),
    "Phase6ReferenceCaseEvidence": ("reference", "Phase6ReferenceCaseEvidence"),
    "Phase6ResourceBudgetRecord": ("records", "Phase6ResourceBudgetRecord"),
    "Phase6ResourceUsageRecord": ("records", "Phase6ResourceUsageRecord"),
    "Phase6RollbackSnapshotRecord": ("records", "Phase6RollbackSnapshotRecord"),
    "Phase6SelectionError": ("selector", "Phase6SelectionError"),
    "Phase6SelectionRecord": ("records", "Phase6SelectionRecord"),
    "Phase6WorkspaceError": ("workspace", "Phase6WorkspaceError"),
    "SelectedFileOperationRecord": ("records", "SelectedFileOperationRecord"),
    "build_candidate_package": ("package_builder", "build_candidate_package"),
    "verify_candidate_package": ("package_builder", "verify_candidate_package"),
    "build_reference_predecessor_package": ("reference", "build_reference_predecessor_package"),
    "finalize_realization": ("realizer", "finalize_realization"),
    "load_predecessor_package": ("workspace", "load_predecessor_package"),
    "measure_payload_tree": ("workspace", "measure_payload_tree"),
    "realize_selected_successor": ("realizer", "realize_selected_successor"),
    "reference_phase6_budget": ("budget", "reference_phase6_budget"),
    "run_reference_phase6_case": ("reference", "run_reference_phase6_case"),
    "run_reference_phase6_suite": ("reference", "run_reference_phase6_suite"),
    "select_reference_successor": ("selector", "select_reference_successor"),
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
