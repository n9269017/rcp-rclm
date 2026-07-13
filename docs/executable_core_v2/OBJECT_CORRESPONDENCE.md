# Object correspondence

This table freezes the public correspondence surface for the first executable
reference. Python names are reserved interface names; except for the Phase 0
contract validator, they are not yet implemented.

## Gate A

| Lean declaration | Schema ID | Immutable Python type | Runtime function | Certificate evidence | Conformance test |
|---|---|---|---|---|---|
| `RCP.Kernel` | `rcp.kernel.v2` | `rcp_rclm_runtime.kernel.KernelRecord` | `evaluate_kernel` | `rcp.kernel_evidence.v2` | `conformance.gate_a.kernel` |
| `RCP.Candidate` | `rcp.candidate.v2` | `rcp_rclm_runtime.records.CandidateRecord` | `apply_candidate` | `rcp.typed_successor_evidence.v2` | `conformance.gate_a.candidate` |
| `RCP.StepObligations` | `rcp.step_obligations.v2` | `rcp_rclm_runtime.records.StepEvidenceRecord` | `recompute_step_obligations` | `rcp.step_evidence.v2` | `conformance.gate_a.step_obligations` |
| `RCP.TrustedChecker` | `rcp.trusted_checker.v2` | `rcp_rclm_runtime.checker.CheckerPolicyRecord` | `check_candidate` | `rcp.checker_report.v2` | `conformance.gate_a.checker` |
| `RCP.RecoveryCompositionLaws` | `rcp.recovery_laws.v2` | `rcp_rclm_runtime.recovery.RecoveryLawRecord` | `verify_recovery_laws` | `rcp.recovery_law_evidence.v2` | `conformance.gate_a.recovery_laws` |
| `RCP.PreservationMonitors` | `rcp.preservation_monitors.v2` | `rcp_rclm_runtime.monitors.MonitorRecord` | `evaluate_monitors` | `rcp.monitor_evidence.v2` | `conformance.gate_a.monitors` |
| `RCP.FiniteAcceptedTrajectory` | `rcp.finite_trajectory.v2` | `rcp_rclm_runtime.trajectory.TrajectoryRecord` | `verify_finite_trajectory` | `rcp.trajectory_evidence.v2` | `conformance.gate_a.finite_trajectory` |
| `RCP.TypedSuccessor` | `rcp.typed_successor.v2` | `rcp_rclm_runtime.verdict.TypedSuccessorEvidence` | `verify_typed_successor` | `rcp.typed_successor_evidence.v2` | `conformance.gate_a.typed_successor` |
| `RCP.ConstructiveRecovery` | `rcp.constructive_recovery.v2` | `rcp_rclm_runtime.verdict.RecoveryEvidence` | `verify_constructive_recovery` | `rcp.recovery_evidence.v2` | `conformance.gate_a.constructive_recovery` |

## Gate B

| Lean declaration | Schema ID | Immutable Python type | Runtime function | Certificate evidence | Conformance test |
|---|---|---|---|---|---|
| `RCP.ClassicalFinite.Distribution` | `gate_b.distribution.v2` | `rcp_rclm_runtime.classical.DistributionRecord` | `validate_distribution` | `gate_b.distribution_evidence.v2` | `conformance.gate_b.distribution` |
| `RCP.ClassicalFinite.SupportedBy` | `gate_b.support.v2` | `rcp_rclm_runtime.classical.SupportEvidence` | `verify_support` | `gate_b.support_evidence.v2` | `conformance.gate_b.support` |
| `RCP.ClassicalFinite.shannonEntropy` | `gate_b.entropy_interval.v2` | `rcp_rclm_runtime.numeric.IntervalEvidence` | `shannon_entropy_interval` | `gate_b.entropy_evidence.v2` | `conformance.gate_b.shannon_entropy` |
| `RCP.ClassicalFinite.klDivergence` | `gate_b.kl_interval.v2` | `rcp_rclm_runtime.numeric.IntervalEvidence` | `kl_divergence_interval` | `gate_b.kl_evidence.v2` | `conformance.gate_b.kl_divergence` |
| `RCP.ClassicalFinite.ZeroExtension` | `gate_b.zero_extension.v2` | `rcp_rclm_runtime.classical.ZeroExtensionRecord` | `extend_by_zero` | `gate_b.zero_extension_evidence.v2` | `conformance.gate_b.zero_extension` |
| `RCP.ClassicalFinite.recoverZeroExtension` | `gate_b.zero_recovery.v2` | `rcp_rclm_runtime.classical.ZeroRecoveryRecord` | `recover_zero_extension` | `gate_b.zero_recovery_evidence.v2` | `conformance.gate_b.zero_recovery` |
| `RCP.ClassicalFinite.BinaryState` | `gate_b.binary_state.v2` | `rcp_rclm_runtime.classical.BinaryStateRecord` | `decode_binary_state` | `gate_b.binary_state_evidence.v2` | `conformance.gate_b.binary_state` |
| `RCP.ClassicalFinite.BinaryUpdate` | `gate_b.binary_update.v2` | `rcp_rclm_runtime.classical.BinaryUpdateRecord` | `apply_binary_update` | `gate_b.binary_update_evidence.v2` | `conformance.gate_b.binary_update` |
| `RCP.ClassicalFinite.BinaryCertificate` | `gate_b.binary_certificate.v2` | `rcp_rclm_runtime.classical.BinaryCertificateRecord` | `decode_binary_certificate` | `gate_b.binary_certificate_evidence.v2` | `conformance.gate_b.binary_certificate` |
| `RCP.ClassicalFinite.binaryCheck` | `gate_b.binary_packet.v2` | `rcp_rclm_runtime.classical.BinaryPacketRecord` | `check_gate_b_binary` | `gate_b.binary_checker_report.v2` | `conformance.gate_b.binary_checker` |

## Gate C selected scope

| Lean declaration | Schema ID | Immutable Python type | Runtime function | Certificate evidence | Conformance test |
|---|---|---|---|---|---|
| `RCP.QuantumFinite.DiagonalDensityMatrix` | `gate_c.diagonal_density.v2` | `rcp_rclm_runtime.quantum.DiagonalDensityRecord` | `validate_diagonal_density` | `gate_c.density_evidence.v2` | `conformance.gate_c.diagonal_density` |
| `RCP.QuantumFinite.DensityMatrixEvidence` | `gate_c.density_matrix_evidence.v2` | `rcp_rclm_runtime.quantum.DensityMatrixEvidenceRecord` | `derive_density_matrix_evidence` | `gate_c.density_matrix_evidence.v2` | `conformance.gate_c.density_matrix` |
| `RCP.QuantumFinite.SupportedBy` | `gate_c.support.v2` | `rcp_rclm_runtime.quantum.QuantumSupportEvidence` | `verify_quantum_support` | `gate_c.support_evidence.v2` | `conformance.gate_c.support` |
| `RCP.QuantumFinite.vonNeumannEntropy` | `gate_c.entropy_interval.v2` | `rcp_rclm_runtime.numeric.IntervalEvidence` | `von_neumann_entropy_interval` | `gate_c.entropy_evidence.v2` | `conformance.gate_c.von_neumann_entropy` |
| `RCP.QuantumFinite.quantumRelativeEntropy` | `gate_c.qre_interval.v2` | `rcp_rclm_runtime.numeric.IntervalEvidence` | `quantum_relative_entropy_interval` | `gate_c.qre_evidence.v2` | `conformance.gate_c.quantum_relative_entropy` |
| `RCP.QuantumFinite.FiniteDiagonalChannel` | `gate_c.diagonal_channel.v2` | `rcp_rclm_runtime.quantum.DiagonalChannelRecord` | `apply_diagonal_channel` | `gate_c.channel_evidence.v2` | `conformance.gate_c.channel` |
| `RCP.QuantumFinite.identityChannel` | `gate_c.selected_channel.v2` | `rcp_rclm_runtime.quantum.SelectedChannelRecord` | `apply_identity_channel` | `gate_c.channel_action_evidence.v2` | `conformance.gate_c.identity_channel` |
| `RCP.QuantumFinite.swapChannel` | `gate_c.selected_channel.v2` | `rcp_rclm_runtime.quantum.SelectedChannelRecord` | `apply_basis_swap_channel` | `gate_c.channel_action_evidence.v2` | `conformance.gate_c.swap_channel` |
| `RCP.QuantumFinite.selectedRecoveryChannel` | `gate_c.recovery_channel.v2` | `rcp_rclm_runtime.quantum.SelectedRecoveryRecord` | `apply_selected_recovery` | `gate_c.recovery_evidence.v2` | `conformance.gate_c.selected_recovery` |
| `RCP.QuantumFinite.QuantumState` | `gate_c.quantum_state.v2` | `rcp_rclm_runtime.quantum.QuantumStateRecord` | `decode_quantum_state` | `gate_c.quantum_state_evidence.v2` | `conformance.gate_c.quantum_state` |
| `RCP.QuantumFinite.QuantumUpdate` | `gate_c.quantum_update.v2` | `rcp_rclm_runtime.quantum.QuantumUpdateRecord` | `apply_quantum_update` | `gate_c.quantum_update_evidence.v2` | `conformance.gate_c.quantum_update` |
| `RCP.QuantumFinite.QuantumCertificate` | `gate_c.quantum_certificate.v2` | `rcp_rclm_runtime.quantum.QuantumCertificateRecord` | `decode_quantum_certificate` | `gate_c.quantum_certificate_evidence.v2` | `conformance.gate_c.quantum_certificate` |
| `RCP.QuantumFinite.quantumCheck` | `gate_c.quantum_packet.v2` | `rcp_rclm_runtime.quantum.QuantumPacketRecord` | `check_gate_c_quantum` | `gate_c.quantum_checker_report.v2` | `conformance.gate_c.quantum_checker` |

## RCLM

| Lean declaration | Schema ID | Immutable Python type | Runtime function | Certificate evidence | Conformance test |
|---|---|---|---|---|---|
| `RCLM.State` | `rclm.state.v2` | `rcp_rclm_runtime.rclm.RclmStateRecord` | `validate_rclm_state` | `rclm.state_evidence.v2` | `conformance.rclm.state` |
| `RCLM.Update` | `rclm.update.v2` | `rcp_rclm_runtime.rclm.RclmUpdateRecord` | `apply_rclm_update` | `rclm.update_evidence.v2` | `conformance.rclm.update` |
| `RCLM.CertificatePacket` | `rclm.certificate_packet.v2` | `rcp_rclm_runtime.rclm.RclmCertificatePacketRecord` | `validate_certificate_packet` | `rclm.certificate_evidence.v2` | `conformance.rclm.certificate_packet` |
| `RCLM.KernelRefinement` | `rclm.kernel_refinement.v2` | `rcp_rclm_runtime.rclm.KernelRefinementRecord` | `verify_kernel_refinement` | `rclm.kernel_refinement_evidence.v2` | `conformance.rclm.kernel_refinement` |
| `RCLM.MonitorRefinement` | `rclm.monitor_refinement.v2` | `rcp_rclm_runtime.rclm.MonitorRefinementRecord` | `verify_monitor_refinement` | `rclm.monitor_refinement_evidence.v2` | `conformance.rclm.monitor_refinement` |
| `RCLM.CheckerRefinement` | `rclm.checker_refinement.v2` | `rcp_rclm_runtime.rclm.CheckerRefinementRecord` | `verify_checker_refinement` | `rclm.checker_refinement_evidence.v2` | `conformance.rclm.checker_refinement` |
| `RCLM.ArchitectureEngine` | `rclm.architecture_engine.v2` | `rcp_rclm_runtime.engine.ArchitectureEngineRecord` | `validate_engine_contract` | `rclm.engine_contract_evidence.v2` | `conformance.rclm.architecture_engine` |
| `RCLM.ArchitecturePredecessor` | `rclm.predecessor.v2` | `rcp_rclm_runtime.engine.PredecessorRecord` | `validate_predecessor` | `rclm.predecessor_evidence.v2` | `conformance.rclm.predecessor` |
| `RCLM.ArchitectureEngineStep` | `rclm.engine_step.v2` | `rcp_rclm_runtime.engine.EngineStepRecord` | `validate_engine_step` | `rclm.engine_step_evidence.v2` | `conformance.rclm.engine_step` |
| `RCLM.ArchitectureSuccessorAvailability` | `rclm.successor_availability.v2` | `rcp_rclm_runtime.engine.SuccessorAvailabilityRecord` | `verify_declared_availability` | `rclm.availability_evidence.v2` | `conformance.rclm.successor_availability` |

## Package and verdict records

These records are executable infrastructure rather than direct Lean structures,
but they are required to preserve the theorem boundary.

| Schema ID | Immutable Python type | Runtime function | Purpose |
|---|---|---|---|
| `runtime.package_manifest.v2` | `rcp_rclm_runtime.package.PackageManifestRecord` | `verify_package_manifest` | Parent linkage, semantic tree hash, certificate hash, trust anchor, and scope |
| `runtime.check_verdict.v2` | `rcp_rclm_runtime.verdict.CheckVerdictRecord` | `derive_final_verdict` | Tri-state verdict and complete reason-coded evidence |
| `runtime.lean_verifier_report.v2` | `rcp_rclm_runtime.lean_bridge.LeanVerifierReport` | `verify_with_lean` | Pinned Lean invocation, source scan, output hashes, and theorem result |
| `runtime.replay_manifest.v2` | `rcp_rclm_runtime.replay.ReplayManifestRecord` | `replay_transition` | Independent re-evaluation without invoking the generator |

## Conformance rule

An implementation is conformant only if every row has:

1. a frozen immutable runtime type;
2. a parser that rejects unknown or duplicate fields;
3. canonical serialization round-trip tests;
4. positive and adversarial fixtures;
5. Python-to-Lean differential tests at the selected reference scope;
6. evidence that the runtime function never trusts the candidate's asserted verdict.
