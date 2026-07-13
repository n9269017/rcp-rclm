from __future__ import annotations

from collections.abc import Mapping

from rcp_rclm_runtime.mathematics.classical import (
    BIASED_BINARY,
    SOURCE_BINARY,
    UNIFORM_BINARY,
    DistributionRecord,
    ZeroExtensionRecord,
    apply_binary_update,
    binary_state_distribution,
    extend_by_zero,
    kl_divergence_interval,
    recover_zero_extension,
    require_supported_by,
    shannon_entropy_interval,
    supported_by,
)


def validate_distribution(value: DistributionRecord | Mapping[str, object]) -> DistributionRecord:
    if isinstance(value, DistributionRecord):
        return value
    return DistributionRecord.from_json(value)


__all__ = [
    "BIASED_BINARY",
    "DistributionRecord",
    "SOURCE_BINARY",
    "UNIFORM_BINARY",
    "ZeroExtensionRecord",
    "apply_binary_update",
    "binary_state_distribution",
    "extend_by_zero",
    "kl_divergence_interval",
    "recover_zero_extension",
    "require_supported_by",
    "shannon_entropy_interval",
    "supported_by",
    "validate_distribution",
]
