# RCP/RCLM Canonical Mechanization Theorem Map

## Paper symbol → Lean definition/theorem map

| Paper symbol / claim | Lean module | Lean name |
|---|---|---|
| `D(Φ_t^can(ρ) || Φ_t^can(σ)) = D(ρ || σ)` | `RcpRclmMech.RCP` | `relative_entropy_append_same` |
| `R_t^can Φ_t^can(ρ) = ρ` | `RcpRclmMech.RCP` | `canonical_recovery_exact` |
| `A_t ⊊ A_{t+1}` | `RcpRclmMech.RCP` | `strict_ability_expansion` |
| `Q_t^{SV,A,can} ≤ 0` | `RcpRclmMech.RCP` | `canonical_residuals_nonpositive` |
| `Check_RCP^can(PCS_t^can)=1 ⇒ obligations` | `RcpRclmMech.RCP` | `checker_soundness_rcp` |
| `BuildRefSV ⇒ ρ_0 ∈ K_0^{SV-seedlib,N}` | `RcpRclmMech.RCP` | `build_refsv_entry` |
| checked finite trajectory | `RcpRclmMech.RCP` | `checked_packet_implies_sv_domain` |
| canonical replay artifact theorem | `RcpRclmMech.RCP` | `artifact_theorem` |
| singleton reality containment | `RcpRclmMech.RCP` | `canonical_reality_containment` |
| `Check_RCP^{RCLM,can}(PCS_t)=1 ⇒ RCLM obligations` | `RcpRclmMech.RCLM` | `checker_soundness_rclm` |
| `Forget_{RCLM→RCP}^can(RefSV_RCLM)=RefSV_RCP` | `RcpRclmMech.RCLM` | `rclm_forget_refines_rcp` |
| RCLM reference-entry theorem | `RcpRclmMech.RCLM` | `build_refsv_entry` |
| RCLM checked finite trajectory | `RcpRclmMech.RCLM` | `checked_packet_implies_sv_domain` |
| RCLM artifact theorem | `RcpRclmMech.RCLM` | `artifact_theorem` |

## Trusted scope statement

The Lean project checks only the canonical finite reference witness and RCLM refinement layer. It is not a mechanization of arbitrary RCP/RCLM theorem claims or arbitrary learned-agent entry.
