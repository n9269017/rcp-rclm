#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$repo_root"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

check_blob() {
  local path="$1"
  local expected="$2"
  local actual
  actual="$(git hash-object "$path")"
  if [[ "$actual" != "$expected" ]]; then
    fail "$path blob mismatch: expected $expected, found $actual"
  fi
  printf 'PASS blob: %s = %s\n' "$path" "$actual"
}

require_text() {
  local path="$1"
  local text="$2"
  if ! grep -Fq -- "$text" "$path"; then
    fail "$path does not contain required text: $text"
  fi
  printf 'PASS mapped surface: %s :: %s\n' "$path" "$text"
}

check_blob papers/paper-I-rcp-math/main.tex 084eae21d252d205d2012b62744c1506644e3e58
check_blob papers/paper-II-rclm-architecture/main.tex 9b51be8294ad79fd4f63522b01e0f617f0bf2ffd

require_text papers/paper-I-rcp-math/main.tex '\label{thm:main_rcp}'
require_text papers/paper-I-rcp-math/main.tex '\label{thm:finite_horizon_constructive_recovery}'
require_text papers/paper-I-rcp-math/main.tex '\label{thm:batch12b_combined_domain_relative_rrst}'
require_text papers/paper-I-rcp-math/main.tex '\label{thm:batch13ra_canonical_checker_soundness}'

require_text papers/paper-II-rclm-architecture/main.tex '\label{thm:rclm-constructive-direct-nl-rsi-engine}'
require_text papers/paper-II-rclm-architecture/main.tex '\label{thm:rclm-batch13r-checker-soundness}'
require_text papers/paper-II-rclm-architecture/main.tex '\label{thm:rclm-batch13r-proof-carrying-finite-trajectory}'
require_text papers/paper-II-rclm-architecture/main.tex '\label{thm:rclm-batch12b-combined-domain-relative-rrst}'
require_text papers/paper-II-rclm-architecture/main.tex '\label{thm:rclm-batch12b-domain-relative-infinite-rrst}'

require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Checker.lean 'theorem accepted_step_sound'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Trajectory.lean 'theorem finite_trajectory_closure'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Trajectory.lean 'theorem finite_progress_monotone'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Trajectory.lean 'theorem finite_composed_nonloss_bound'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Trajectory.lean 'theorem finite_endpoint_recovery_bound'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Monitors.lean 'theorem finite_lyapunov_motion_bound'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Monitors.lean 'theorem finite_ambiguity_collapse_bound'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Monitors.lean 'theorem finite_self_model_relevance_bound'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/InfiniteHorizon.lean 'theorem conditional_infinite_trajectory_exists'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Summability.lean 'theorem infinite_monitor_bounds_of_summable'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/PaperContract.lean 'theorem finite_paper_preservation'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/PaperContract.lean 'theorem conditional_infinite_paper_trajectory_exists'

require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/ClassicalFinite.lean 'theorem klDivergence_nonnegative'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/ClassicalFinite.lean 'theorem shannonEntropy_extendByZero'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/ClassicalFinite.lean 'theorem conservative_extension_recovery'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/ClassicalBinary.lean 'theorem binary_checker_refines_kernel'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/ClassicalBinary.lean 'theorem binaryLyapunov_motion_step'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/ClassicalBinary.lean 'theorem binaryWorkedTrajectory_endpoint_recovery'
require_text lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/ClassicalBinary.lean 'theorem binaryWorkedTrajectory_first_step_strict'

require_text docs/formal_core_v2/GATE_A_PAPER_ALIGNMENT_AUDIT.md 'Paper I thm:main_rcp versus current Lean bundle: NOT EXACT'
require_text docs/formal_core_v2/GATE_A_PAPER_ALIGNMENT_AUDIT.md 'Paper II architecture successor theorem: NOT IMPLEMENTED'
require_text docs/formal_core_v2/GATE_A_ALIGNMENT_RESOLUTION_LOG.md 'ALIGN-06 typed endpoint recovery composition: resolved at abstract Gate A level'
require_text docs/formal_core_v2/GATE_A_ALIGNMENT_RESOLUTION_LOG.md 'Abstract Gate A theorem kernel: complete'
require_text docs/formal_core_v2/GATE_A_ALIGNMENT_RESOLUTION_LOG.md 'Exact Paper I theorem equivalence: still false'
require_text docs/formal_core_v2/GATE_B_CLOSURE.md 'Gate B is complete at the declared finite classical reference scope.'
require_text docs/formal_core_v2/GATE_B_CLOSURE.md 'Exact Paper I main-theorem equivalence: not claimed'
require_text docs/formal_core_v2/GATE_B_CLOSURE.md 'Executable RSI: not licensed'

printf '%s\n' 'PASS: paper blobs, theorem labels, Gate A declarations, Gate B finite-reference declarations, and claim boundaries are pinned.'