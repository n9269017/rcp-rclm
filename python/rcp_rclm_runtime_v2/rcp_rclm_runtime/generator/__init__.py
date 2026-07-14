from __future__ import annotations

import importlib
from typing import Final

_EXPORTS: Final[dict[str, tuple[str, str]]] = {
    "CertificateConstructionRecord": (
        "rcp_rclm_runtime.generator.pipeline",
        "CertificateConstructionRecord",
    ),
    "GeneratorProcessObservation": (
        "rcp_rclm_runtime.generator.records",
        "GeneratorProcessObservation",
    ),
    "GeneratorReasonCode": (
        "rcp_rclm_runtime.generator.records",
        "GeneratorReasonCode",
    ),
    "GeneratorReplayReport": (
        "rcp_rclm_runtime.generator.records",
        "GeneratorReplayReport",
    ),
    "GeneratorResourceBudgetRecord": (
        "rcp_rclm_runtime.generator.records",
        "GeneratorResourceBudgetRecord",
    ),
    "Phase5PipelineExecution": (
        "rcp_rclm_runtime.generator.pipeline",
        "Phase5PipelineExecution",
    ),
    "Phase5ReferencePipelineReport": (
        "rcp_rclm_runtime.generator.pipeline",
        "Phase5ReferencePipelineReport",
    ),
    "PreparedReferenceTransition": (
        "rcp_rclm_runtime.generator.pipeline",
        "PreparedReferenceTransition",
    ),
    "RealizationRecord": (
        "rcp_rclm_runtime.generator.pipeline",
        "RealizationRecord",
    ),
    "ReferenceGeneratorInputRecord": (
        "rcp_rclm_runtime.generator.records",
        "ReferenceGeneratorInputRecord",
    ),
    "ReferenceGeneratorPolicyRecord": (
        "rcp_rclm_runtime.generator.records",
        "ReferenceGeneratorPolicyRecord",
    ),
    "ReferencePredecessorPackageRecord": (
        "rcp_rclm_runtime.generator.records",
        "ReferencePredecessorPackageRecord",
    ),
    "ReferenceWorkerResponse": (
        "rcp_rclm_runtime.generator.records",
        "ReferenceWorkerResponse",
    ),
    "SelectionRecord": (
        "rcp_rclm_runtime.generator.pipeline",
        "SelectionRecord",
    ),
    "UntrustedProposalRecord": (
        "rcp_rclm_runtime.generator.records",
        "UntrustedProposalRecord",
    ),
    "WorkerSandboxRecord": (
        "rcp_rclm_runtime.generator.records",
        "WorkerSandboxRecord",
    ),
    "build_reference_generator_input": (
        "rcp_rclm_runtime.generator.reference",
        "build_reference_generator_input",
    ),
    "construct_reference_certificate": (
        "rcp_rclm_runtime.generator.pipeline",
        "construct_reference_certificate",
    ),
    "execute_reference_pipeline": (
        "rcp_rclm_runtime.generator.pipeline",
        "execute_reference_pipeline",
    ),
    "finalize_reference_transition": (
        "rcp_rclm_runtime.generator.pipeline",
        "finalize_reference_transition",
    ),
    "interpret_reference_input": (
        "rcp_rclm_runtime.generator.grammar",
        "interpret_reference_input",
    ),
    "prepare_reference_transition": (
        "rcp_rclm_runtime.generator.pipeline",
        "prepare_reference_transition",
    ),
    "realize_reference_candidate": (
        "rcp_rclm_runtime.generator.pipeline",
        "realize_reference_candidate",
    ),
    "reference_declared_objective": (
        "rcp_rclm_runtime.generator.reference",
        "reference_declared_objective",
    ),
    "reference_generator_budget": (
        "rcp_rclm_runtime.generator.reference",
        "reference_generator_budget",
    ),
    "reference_generator_policy": (
        "rcp_rclm_runtime.generator.reference",
        "reference_generator_policy",
    ),
    "reference_transition_id": (
        "rcp_rclm_runtime.generator.reference",
        "reference_transition_id",
    ),
    "run_reference_generator_process": (
        "rcp_rclm_runtime.generator.process",
        "run_reference_generator_process",
    ),
    "run_reference_generator_replay": (
        "rcp_rclm_runtime.generator.process",
        "run_reference_generator_replay",
    ),
    "select_reference_update": (
        "rcp_rclm_runtime.generator.pipeline",
        "select_reference_update",
    ),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> object:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    module = importlib.import_module(module_name)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
