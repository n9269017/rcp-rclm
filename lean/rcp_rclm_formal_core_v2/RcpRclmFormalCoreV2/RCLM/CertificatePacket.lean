namespace RcpRclmFormalCoreV2
namespace RCLM

universe uCoreCertificate uSemanticEvidence uTypeEvidence uLedgerEvidence
  uGoalTransportEvidence uTrustEvidence uResourceEvidence uRealityEvidence
  uRecoveryEvidence uProgressEvidence

/--
An RCLM certificate packet carries evidence objects, not booleans assigned true
by the constructor. The meaning of each evidence type is supplied by the
architecture instantiation and refinement proof.
-/
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

end RCLM
end RcpRclmFormalCoreV2
