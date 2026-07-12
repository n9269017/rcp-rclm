namespace RcpRclmFormalCoreV2
namespace RCLM

universe uCoreUpdate uParameterUpdate uArchitectureUpdate uMemoryUpdate
  uVerifierUpdate uSemanticUpdate uToolUpdate uResourceUpdate

/--
A typed architecture update. Concrete instantiations decide which components
are changed and must prove the corresponding realization and preservation
obligations.
-/
structure Update
    (CoreUpdate : Type uCoreUpdate)
    (ParameterUpdate : Type uParameterUpdate)
    (ArchitectureUpdate : Type uArchitectureUpdate)
    (MemoryUpdate : Type uMemoryUpdate)
    (VerifierUpdate : Type uVerifierUpdate)
    (SemanticUpdate : Type uSemanticUpdate)
    (ToolUpdate : Type uToolUpdate)
    (ResourceUpdate : Type uResourceUpdate) where
  core : CoreUpdate
  parameters : ParameterUpdate
  architecture : ArchitectureUpdate
  memory : MemoryUpdate
  verifier : VerifierUpdate
  semantics : SemanticUpdate
  tools : ToolUpdate
  resources : ResourceUpdate

end RCLM
end RcpRclmFormalCoreV2
