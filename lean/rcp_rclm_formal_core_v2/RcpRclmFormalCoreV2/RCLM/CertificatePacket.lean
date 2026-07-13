namespace RcpRclmFormalCoreV2
namespace RCLM

universe uCoreCertificate uSemanticEvidence uTypeEvidence uLedgerEvidence
  uGoalTransportEvidence uTrustEvidence uResourceEvidence uRealityEvidence
  uRecoveryEvidence uProgressEvidence

structure CertificatePacket
    (CoreCertificate : Type uCoreCertificate)
    (SemanticEvidence : Type uSemanticEvidence)
    (TypeEvidence : Type uTypeEvidence)
    (LedgerEvidence : Type uLedgerEvidence)
    (GoalTransportEvidence : Type uGoalTransportEvidence)
    (TrustEvidence : Type uTrustEvidence)
    (ResourceEvidence : Type uResourceEvidence)
    (RealityEvidence : Type uRealityEvidence)
    (RecoveryEvidence : Type uRecoveryEvidence)
    (ProgressEvidence : Type uProgressEvidence) where
  core : CoreCertificate
  semantics : SemanticEvidence
  typing : TypeEvidence
  ledger : LedgerEvidence
  goalTransport : GoalTransportEvidence
  trust : TrustEvidence
  resources : ResourceEvidence
  reality : RealityEvidence
  recovery : RecoveryEvidence
  progress : ProgressEvidence
  deriving DecidableEq

end RCLM
end RcpRclmFormalCoreV2
