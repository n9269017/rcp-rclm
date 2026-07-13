from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from typing import Final

from rcp_rclm_runtime._version import FORMAL_SOURCE_COMMIT, LEAN_TOOLCHAIN, MATHLIB_COMMIT


@dataclass(frozen=True, slots=True)
class TheoremSurfaceEntry:
    object_id: str
    lean_path: str
    lean_declaration: str
    python_symbol: str
    runtime_function: str
    phase_1_status: str


PHASE_1_THEOREM_SURFACE: Final[Sequence[TheoremSurfaceEntry]] = (
    TheoremSurfaceEntry(
        "gate_a.candidate",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Types.lean",
        "structure Candidate",
        "rcp_rclm_runtime.records.CandidateRecord",
        "apply_candidate",
        "implemented",
    ),
    TheoremSurfaceEntry(
        "gate_b.distribution",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/ClassicalFinite.lean",
        "structure Distribution",
        "rcp_rclm_runtime.classical.DistributionRecord",
        "validate_distribution",
        "implemented",
    ),
    TheoremSurfaceEntry(
        "gate_b.shannon_entropy",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/ClassicalFinite.lean",
        "noncomputable def shannonEntropy",
        "rcp_rclm_runtime.numeric.IntervalEvidence",
        "shannon_entropy_interval",
        "implemented",
    ),
    TheoremSurfaceEntry(
        "gate_b.kl_divergence",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/ClassicalFinite.lean",
        "noncomputable def klDivergence",
        "rcp_rclm_runtime.numeric.IntervalEvidence",
        "kl_divergence_interval",
        "implemented",
    ),
    TheoremSurfaceEntry(
        "gate_b.zero_extension",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/ClassicalFinite.lean",
        "structure ZeroExtension",
        "rcp_rclm_runtime.classical.ZeroExtensionRecord",
        "extend_by_zero",
        "implemented",
    ),
    TheoremSurfaceEntry(
        "gate_c.diagonal_density",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/QuantumDensity.lean",
        "structure DiagonalDensityMatrix",
        "rcp_rclm_runtime.quantum.DiagonalDensityRecord",
        "validate_diagonal_density",
        "implemented",
    ),
    TheoremSurfaceEntry(
        "gate_c.von_neumann_entropy",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/QuantumDensity.lean",
        "noncomputable def vonNeumannEntropy",
        "rcp_rclm_runtime.numeric.IntervalEvidence",
        "von_neumann_entropy_interval",
        "implemented",
    ),
    TheoremSurfaceEntry(
        "gate_c.quantum_relative_entropy",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/QuantumDensity.lean",
        "noncomputable def quantumRelativeEntropy",
        "rcp_rclm_runtime.numeric.IntervalEvidence",
        "quantum_relative_entropy_interval",
        "implemented",
    ),
    TheoremSurfaceEntry(
        "gate_c.diagonal_channel",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/QuantumDensity.lean",
        "structure FiniteDiagonalChannel",
        "rcp_rclm_runtime.quantum.DiagonalChannelRecord",
        "apply_diagonal_channel",
        "implemented_selected_scope",
    ),
    TheoremSurfaceEntry(
        "gate_c.selected_channels",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/QuantumChannels.lean",
        "noncomputable def selectedChannel",
        "rcp_rclm_runtime.quantum.SelectedChannelRecord",
        "apply_selected_channel",
        "implemented",
    ),
    TheoremSurfaceEntry(
        "rclm.state",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCLM/State.lean",
        "structure State",
        "rcp_rclm_runtime.rclm.RclmStateRecord",
        "validate_rclm_state",
        "implemented",
    ),
    TheoremSurfaceEntry(
        "rclm.update",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCLM/Update.lean",
        "structure Update",
        "rcp_rclm_runtime.rclm.RclmUpdateRecord",
        "apply_rclm_update",
        "record_and_mapping_implemented",
    ),
    TheoremSurfaceEntry(
        "rclm.certificate_packet",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCLM/CertificatePacket.lean",
        "structure CertificatePacket",
        "rcp_rclm_runtime.rclm.RclmCertificatePacketRecord",
        "validate_certificate_packet",
        "implemented",
    ),
    TheoremSurfaceEntry(
        "rclm.kernel_refinement",
        "lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCLM/Refinement.lean",
        "structure KernelRefinement",
        "rcp_rclm_runtime.rclm.KernelRefinementRecord",
        "verify_kernel_refinement",
        "mapping_bedrock_implemented_checker_pending",
    ),
)


def theorem_surface_metadata() -> dict[str, object]:
    return {
        "schema_id": "runtime.phase_1_theorem_surface.v2",
        "formal_source_commit": FORMAL_SOURCE_COMMIT,
        "lean_toolchain": LEAN_TOOLCHAIN,
        "mathlib_commit": MATHLIB_COMMIT,
        "entries": [
            {
                "object_id": entry.object_id,
                "lean_path": entry.lean_path,
                "lean_declaration": entry.lean_declaration,
                "python_symbol": entry.python_symbol,
                "runtime_function": entry.runtime_function,
                "phase_1_status": entry.phase_1_status,
            }
            for entry in PHASE_1_THEOREM_SURFACE
        ],
    }
