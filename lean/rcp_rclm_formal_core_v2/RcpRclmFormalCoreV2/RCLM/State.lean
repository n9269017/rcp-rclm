namespace RcpRclmFormalCoreV2
namespace RCLM

/--
A typed RCLM architecture state. The registers are genuine data types supplied
by an instantiation; validity is expressed separately as propositions and is not
hardcoded into Boolean fields.
-/
structure State
    (Core Language WorldReference HumanReference Definitiveness Ambiguity
      Memory Verifier Resources SelfModel : Type*) where
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

end RCLM
end RcpRclmFormalCoreV2
