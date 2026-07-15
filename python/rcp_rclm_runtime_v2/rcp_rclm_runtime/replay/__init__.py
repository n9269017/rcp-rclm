"""Phase 8 independent-replay public API with lazy imports."""

from __future__ import annotations

from importlib import import_module
from typing import Final

_EXPORTS: Final[dict[str, tuple[str, str]]] = {
    "Phase8AttemptIndexRecord": ("records", "Phase8AttemptIndexRecord"),
    "Phase8AttemptReplayReport": ("records", "Phase8AttemptReplayReport"),
    "Phase8BundleError": ("bundle", "Phase8BundleError"),
    "Phase8ReasonCode": ("records", "Phase8ReasonCode"),
    "Phase8ReferenceRoundtripEvidence": ("reference", "Phase8ReferenceRoundtripEvidence"),
    "Phase8ReplayBundleEvidence": ("bundle", "Phase8ReplayBundleEvidence"),
    "Phase8ReplayBundleManifestRecord": ("records", "Phase8ReplayBundleManifestRecord"),
    "Phase8ReplayEvidence": ("reproduce", "Phase8ReplayEvidence"),
    "Phase8ReplayReport": ("records", "Phase8ReplayReport"),
    "Phase8StageResult": ("records", "Phase8StageResult"),
    "ReplaySourceFinding": ("guard", "ReplaySourceFinding"),
    "ReplaySourceGuardReport": ("guard", "ReplaySourceGuardReport"),
    "build_phase8_replay_bundle": ("bundle", "build_phase8_replay_bundle"),
    "guard_independent_replay_source": ("guard", "guard_independent_replay_source"),
    "reproduce_phase8_bundle": ("reproduce", "reproduce_phase8_bundle"),
    "run_reference_phase8_roundtrip": ("reference", "run_reference_phase8_roundtrip"),
    "verify_phase8_replay_bundle": ("bundle", "verify_phase8_replay_bundle"),
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
