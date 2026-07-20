import RcpRclmFormalCoreV3.Learned.ExecutableContract

namespace RcpRclmFormalCoreV3
namespace Learned

/--
A conservative adapter extension retains the predecessor base object together with
explicit adapter factors.  Recovery is structural projection back to the base.
-/
structure AdapterExtension (Base AdapterA AdapterB : Type*) where
  base : Base
  adapterA : AdapterA
  adapterB : AdapterB

/-- Install an adapter without changing the retained predecessor base object. -/
def extendWithAdapter
    {Base AdapterA AdapterB : Type*}
    (base : Base)
    (adapterA : AdapterA)
    (adapterB : AdapterB) : AdapterExtension Base AdapterA AdapterB :=
  { base := base
    adapterA := adapterA
    adapterB := adapterB }

/-- Exact recovery drops the adapter and returns the retained predecessor base. -/
def recoverAdapterBase
    {Base AdapterA AdapterB : Type*}
    (extension : AdapterExtension Base AdapterA AdapterB) : Base :=
  extension.base

/-- Structural recovery is a left inverse of adapter installation. -/
theorem recover_adapter_extension_exact
    {Base AdapterA AdapterB : Type*}
    (base : Base)
    (adapterA : AdapterA)
    (adapterB : AdapterB) :
    recoverAdapterBase (extendWithAdapter base adapterA adapterB) = base :=
  rfl

section LoRA

variable {Input Hidden Output : Type*}
variable [AddMonoid Output]

/--
Abstract LoRA semantics: the installed function is the base output plus the output
factor applied to the input-factor representation.
-/
def loraOutput
    (base : Input → Output)
    (adapterA : Input → Hidden)
    (adapterB : Hidden → Output)
    (input : Input) : Output :=
  base input + adapterB (adapterA input)

/-- A zero output factor makes the LoRA contribution exactly zero at every input. -/
theorem lora_zero_output_preserves
    (base : Input → Output)
    (adapterA : Input → Hidden)
    (input : Input) :
    loraOutput base adapterA (fun _ => 0) input = base input := by
  simp [loraOutput]

/-- Function-level form of exact preservation by a zero-output LoRA extension. -/
theorem lora_zero_output_preserves_function
    (base : Input → Output)
    (adapterA : Input → Hidden) :
    loraOutput base adapterA (fun _ => 0) = base := by
  funext input
  exact lora_zero_output_preserves base adapterA input

end LoRA

end Learned
end RcpRclmFormalCoreV3
