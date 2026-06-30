$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force cert\build_logs | Out-Null

function Run-And-Log($cmd, $log) {
  Write-Host "Running: $cmd"
  powershell -NoProfile -Command "$cmd" *>&1 | Tee-Object -FilePath $log
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $cmd"
  }
}

Run-And-Log "lake env lean .\RcpRclmMech\RCP.lean" "cert\build_logs\RCP_build.log"
Run-And-Log "lake build RcpRclmMech.RCP" "cert\build_logs\RCP_module_build.log"
Run-And-Log "lake env lean .\RcpRclmMech\RCLM.lean" "cert\build_logs\RCLM_build.log"
Run-And-Log "lake build RcpRclmMech.RCLM" "cert\build_logs\RCLM_module_build.log"
Run-And-Log "lake env lean .\RcpRclmMech.lean" "cert\build_logs\Root_build.log"
Run-And-Log "lake build" "cert\build_logs\lake_build_library.log"

function FileHash($path) {
  if (Test-Path $path) {
    return (Get-FileHash -Algorithm SHA256 $path).Hash.ToLower()
  } else {
    return $null
  }
}

$manifest = [ordered]@{
  certificate = "MechCert_RCP_RCLM_can"
  proof_assistant = "Lean 4"
  scope = "canonical finite Batch-13R/M3-Min reference witness and checker/refinement core"
  not_scope = "entire RCP/RCLM theorem stack; arbitrary trained-system RSI; empirical deployment validation"
  build_status = "success"
  build_command = "lake build"
  individual_check_commands = @(
    "lake env lean .\\RcpRclmMech\\RCP.lean",
    "lake build RcpRclmMech.RCP",
    "lake env lean .\\RcpRclmMech\\RCLM.lean",
    "lake build RcpRclmMech.RCLM",
    "lake env lean .\\RcpRclmMech.lean",
    "lake build"
  )
  theorems_checked = @(
    "RcpRclmMech.RCP.relative_entropy_append_same",
    "RcpRclmMech.RCP.canonical_recovery_exact",
    "RcpRclmMech.RCP.strict_ability_expansion",
    "RcpRclmMech.RCP.canonical_residuals_nonpositive",
    "RcpRclmMech.RCP.checker_soundness_rcp",
    "RcpRclmMech.RCP.build_refsv_entry",
    "RcpRclmMech.RCP.checked_packet_implies_sv_domain",
    "RcpRclmMech.RCP.artifact_theorem",
    "RcpRclmMech.RCLM.checker_soundness_rclm",
    "RcpRclmMech.RCLM.rclm_forget_refines_rcp",
    "RcpRclmMech.RCLM.build_refsv_entry",
    "RcpRclmMech.RCLM.checked_packet_implies_sv_domain",
    "RcpRclmMech.RCLM.artifact_theorem"
  )
  source_hashes = [ordered]@{
    "RcpRclmMech.lean" = FileHash "RcpRclmMech.lean"
    "RcpRclmMech/RCP.lean" = FileHash "RcpRclmMech/RCP.lean"
    "RcpRclmMech/RCLM.lean" = FileHash "RcpRclmMech/RCLM.lean"
    "lakefile.toml" = FileHash "lakefile.toml"
    "lean-toolchain" = FileHash "lean-toolchain"
  }
  artifact_hashes = [ordered]@{
    "artifacts/rcp_batch13rB_controlled_artifact.json" = FileHash "artifacts/rcp_batch13rB_controlled_artifact.json"
    "artifacts/rclm_batch13rB_controlled_artifact.json" = FileHash "artifacts/rclm_batch13rB_controlled_artifact.json"
  }
  build_log_hashes = [ordered]@{
    "cert/build_logs/RCP_build.log" = FileHash "cert/build_logs/RCP_build.log"
    "cert/build_logs/RCP_module_build.log" = FileHash "cert/build_logs/RCP_module_build.log"
    "cert/build_logs/RCLM_build.log" = FileHash "cert/build_logs/RCLM_build.log"
    "cert/build_logs/RCLM_module_build.log" = FileHash "cert/build_logs/RCLM_module_build.log"
    "cert/build_logs/Root_build.log" = FileHash "cert/build_logs/Root_build.log"
    "cert/build_logs/lake_build_library.log" = FileHash "cert/build_logs/lake_build_library.log"
  }
}

$manifest | ConvertTo-Json -Depth 10 | Out-File -Encoding UTF8 "cert\mechanization_manifest.filled.json"
Write-Host "Wrote cert\mechanization_manifest.filled.json"
