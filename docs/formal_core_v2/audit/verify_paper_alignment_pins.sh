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

check_blob \
  papers/paper-I-rcp-math/main.tex \
  084eae21d252d205d2012b62744c1506644e3e58

check_blob \
  papers/paper-II-rclm-architecture/main.tex \
  9b51be8294ad79fd4f63522b01e0f617f0bf2ffd

# Paper I theorem surfaces used by the alignment audit.
require_text papers/paper-I-rcp-math/main.tex \
  '\label{thm:main_rcp}'
require_text papers/paper-I-rcp-math/main.tex \
  '\label{thm:finite_horizon_constructive_recovery}'
require_text papers/paper-I-rcp-math/main.tex \
  '\label{thm:batch12b_combined_domain_relative_rrst}'
require_text papers/paper-I-rcp-math/main.tex \
  '\label{thm:batch13ra_canonical_checker_soundness}'

# Paper II theorem surfaces used by the alignment audit.
require_text papers/paper-II-rclm-architecture/main.tex \
  '\label{thm:rclm-constructive-direct-nl-rsi-engine}'
require_text papers/paper-II-rclm-architecture/main.tex \
  '\label{thm:rclm-batch13r-checker-soundness}'
require_text papers/paper-II-rclm-architecture/main.tex \
  '\label{thm:rclm-batch13r-proof-carrying-finite-trajectory}'
require_text papers/paper-II-rclm-architecture/main.tex \
  '\label{thm:rclm-batch12b-combined-domain-relative-rrst}'
require_text papers/paper-II-rclm-architecture/main.tex \
  '\label{thm:rclm-batch12b-domain-relative-infinite-rrst}'

# Compiled Gate A declarations to which the paper surfaces are compared.
require_text \
  lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Checker.lean \
  'theorem accepted_step_sound'
require_text \
  lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Trajectory.lean \
  'theorem finite_trajectory_closure'
require_text \
  lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Trajectory.lean \
  'theorem finite_progress_monotone'
require_text \
  lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Trajectory.lean \
  'theorem finite_composed_nonloss_bound'
require_text \
  lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/Trajectory.lean \
  'theorem finite_composed_recovery_bound'
require_text \
  lean/rcp_rclm_formal_core_v2/RcpRclmFormalCoreV2/RCP/InfiniteHorizon.lean \
  'theorem conditional_infinite_trajectory_exists'

# Ensure the audit preserves the two central non-equivalence findings.
require_text docs/formal_core_v2/GATE_A_PAPER_ALIGNMENT_AUDIT.md \
  'Paper I thm:main_rcp versus current Lean bundle: NOT EXACT'
require_text docs/formal_core_v2/GATE_A_PAPER_ALIGNMENT_AUDIT.md \
  'Paper II architecture successor theorem: NOT IMPLEMENTED'

printf '%s\n' \
  'PASS: paper blobs, theorem labels, mapped Lean declarations, and alignment findings are pinned.'
