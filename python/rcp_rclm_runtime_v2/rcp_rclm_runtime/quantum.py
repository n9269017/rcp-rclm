from __future__ import annotations

from collections.abc import Mapping

from rcp_rclm_runtime.mathematics.diagonal_quantum import (
    SOURCE_DENSITY,
    TARGET_DENSITY,
    UNIFORM_DENSITY,
    ComplexRational,
    DensityMatrixEvidence,
    DiagonalChannelRecord,
    DiagonalDensityRecord,
    SelectedChannelRecord,
    apply_quantum_update,
    apply_selected_channel,
    quantum_relative_entropy_interval,
    quantum_state_density,
    recover_selected_channel,
    validate_dense_export,
    von_neumann_entropy_interval,
)


def validate_diagonal_density(
    value: DiagonalDensityRecord | Mapping[str, object],
) -> DiagonalDensityRecord:
    if isinstance(value, DiagonalDensityRecord):
        return value
    return DiagonalDensityRecord.from_json(value)


def apply_diagonal_channel(
    channel: SelectedChannelRecord,
    density: DiagonalDensityRecord,
) -> DiagonalDensityRecord:
    return apply_selected_channel(channel, density)


__all__ = [
    "ComplexRational",
    "DensityMatrixEvidence",
    "DiagonalChannelRecord",
    "DiagonalDensityRecord",
    "SOURCE_DENSITY",
    "SelectedChannelRecord",
    "TARGET_DENSITY",
    "UNIFORM_DENSITY",
    "apply_diagonal_channel",
    "apply_quantum_update",
    "apply_selected_channel",
    "quantum_relative_entropy_interval",
    "quantum_state_density",
    "recover_selected_channel",
    "validate_dense_export",
    "validate_diagonal_density",
    "von_neumann_entropy_interval",
]
