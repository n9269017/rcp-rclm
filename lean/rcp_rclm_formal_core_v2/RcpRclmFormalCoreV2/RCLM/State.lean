namespace RcpRclmFormalCoreV2
namespace RCLM

universe uCore uLanguage uWorldReference uHumanReference uDefinitiveness
  uAmbiguity uMemory uVerifier uResources uSelfModel

structure State
    (Core : Type uCore)
    (Language : Type uLanguage)
    (WorldReference : Type uWorldReference)
    (HumanReference : Type uHumanReference)
    (Definitiveness : Type uDefinitiveness)
    (Ambiguity : Type uAmbiguity)
    (Memory : Type uMemory)
    (Verifier : Type uVerifier)
    (Resources : Type uResources)
    (SelfModel : Type uSelfModel) where
  core : Core
  language : Language
  worldReference : WorldReference
  humanReference : HumanReference
  definitiveness : Definitiveness
  ambiguity : Ambiguity
  memory : Memory
  verifier : Verifier
  resources : Resources
  selfModel : SelfModel
  deriving DecidableEq

end RCLM
end RcpRclmFormalCoreV2
