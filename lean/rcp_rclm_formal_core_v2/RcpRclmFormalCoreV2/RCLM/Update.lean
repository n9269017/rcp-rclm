namespace RcpRclmFormalCoreV2
namespace RCLM

/--
A typed architecture update. Concrete instantiations decide which components
are changed and must prove the corresponding realization and preservation
obligations.
-/
structure Update
    (CoreUpdate ParameterUpdate ArchitectureUpdate MemoryUpdate VerifierUpdate
      SemanticUpdate ToolUpdate ResourceUpdate : Type*) where
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
