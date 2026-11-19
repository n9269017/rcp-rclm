import SelectedFiniteKernel
import TaskInterpretation
namespace Phase17TaskInterpretationExamples
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3 Phase17TaskInterpretation
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000

def selectedFixed : Phase17Finite.Configuration :=
  extendConfiguration Phase17Finite.selectedConfiguration

-- Later providers are mathematical parameters. No later candidate is selected.
def selectedContexts (laterContexts : Contexts) (s : State) : Phase17Provenance.Context :=
  if s.packageHash = Phase17Finite.selectedBefore.packageHash then
    Phase17Finite.selectedConfiguration.context else laterContexts s

def selectedCharges (laterCharges : Charges) (s : State) : List Phase17Resource.Kind :=
  if s.packageHash = Phase17Finite.selectedBefore.packageHash then
    Phase17Finite.selectedConfiguration.expectedCharges else laterCharges s

def available (s : State) : Finset Nat :=
  (Finset.range 282).filter (fun t => 22 ≤ t ∧
    (selectedFixed.catalog t).check (Phase17Finite.taskObservation s) = true)

def missing : Finset Nat := (Finset.range 282).filter (fun t => 22 ≤ t ∧ t ≠ 259)
def catalogDigest : String := "511a8e2783bfa6b4d2dcfda2a700967e5a9e101ba7f57d8ff6b61b164034cf5d"
def descriptorDigest : String := "25c0498782cadd5338a470c31a9247e3176ae4a74bd7ac35ac9b71fcb1c681de"
def paletteDigest : String := "6a2d373bc339c83966c0d5a7302729190d14fc0ce62c4922af04eabb56929656"
def wrongClaim : Bool := (selectedFixed.catalog 21).check (Phase17Finite.taskObservation Phase17Finite.selectedBefore)
theorem actual_rejection : wrongClaim = false := by decide +kernel
example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17TaskInterpretationExamples
