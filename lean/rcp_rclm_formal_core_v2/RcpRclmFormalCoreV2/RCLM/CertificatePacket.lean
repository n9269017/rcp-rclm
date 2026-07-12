namespace RcpRclmFormalCoreV2
namespace RCLM

/--
An RCLM certificate packet carries evidence objects, not booleans assigned true
by the constructor. The meaning of each evidence type is supplied by the
architecture instantiation and refinement proof.
-/
structure CertificatePacket
    (CoreCertificate SemanticEvidence TypeEvidence LedgerEvidence
      GoalTransportEvidence TrustEvidence ResourceEvidence RealityEvidence
      RecoveryEvidence ProgressEvidence : Type*) where
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
