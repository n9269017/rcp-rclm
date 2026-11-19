import RcpRclmFormalCoreV4

/-
Phase 17F: checked finite data and a conditional connection to the immutable
Gate E recursive-frontier fields. This file does not instantiate an RCP kernel,
prove a complete LearnedAcceptedStep, or authorize a package promotion.
The Python verifier must bind the literals below to freshly measured packages.
-/
namespace Phase17Evidence

structure Program where
  family : Nat
  variant : Nat
  a : Int
  b : Int
  deriving DecidableEq, Repr

def insertInt (a : Int) : List Int → List Int
  | [] => [a]
  | b :: bs => if a ≤ b then a :: b :: bs else b :: insertInt a bs

def sortInts : List Int → List Int
  | [] => []
  | a :: rest => insertInt a (sortInts rest)

/-- Independent Lean semantics of the unchanged four-integer mutation DSL. -/
def execute (p : Program) (xs : List Int) : List Int :=
  let v := p.variant + 1
  let vi : Int := Int.ofNat v
  let x := fun (i : Nat) => xs.getD i 0
  match p.family with
  | 0 => xs.map (fun z => vi * z + p.a - p.b)
  | 1 => (List.range 4).map (fun i => x ((i + v + 1) % 4) + p.a * Int.ofNat (i + 1) + p.b)
  | 2 => (List.range 4).map (fun i => x ((i + v) % 4) + if i = 0 then p.a else 0)
  | 3 => (List.range 4).map (fun i => xs.sum + p.a + Int.ofNat (v * (i + 1) * (i + 2) / 2) - p.b * Int.ofNat (i + 1))
  | 4 => [x 0 + p.a, x 1 * vi, x 2 - p.b, x 3 + x 0 * vi]
  | 5 => (List.range 4).map (fun i => x ((i * v + p.b.natAbs) % 4))
  | 6 => [x 0 + x 1 + p.a, x 1 - x 2 + p.b, x 2 * vi, x 3 + p.a - p.b]
  | 7 => sortInts (xs.map (fun z => z + p.a * vi - p.b))
  | _ => []

abbrev FileIdentity := String × String × Nat

structure Packet where
  protectedBefore : List FileIdentity
  protectedAfter : List FileIdentity
  programsBefore : List String
  programsAfter : List String
  newProgram : String
  capabilitiesBefore : List String
  capabilitiesAfter : List String
  newCapability : String
  recursiveBefore : List String
  recursiveAfter : List String
  searchUsed : Nat
  searchBudget : Nat
  program : Program
  inheritedFamilyPrograms : List Program
  inputs : List (List Int)
  targets : List (List Int)

/-- These are literal finite facts, not the complete Gate E acceptance relation. -/
structure FiniteFacts (p : Packet) : Prop where
  protectedFilesEqual : p.protectedBefore = p.protectedAfter
  inheritedProgramSubset : p.programsBefore.toFinset ⊆ p.programsAfter.toFinset
  oneNewProgram : p.programsBefore.length + 1 = p.programsAfter.length
  programFresh : p.newProgram ∉ p.programsBefore
  programPresent : p.newProgram ∈ p.programsAfter
  capabilityRetained : p.capabilitiesBefore.toFinset ⊆ p.capabilitiesAfter.toFinset
  oneNewCapability : p.capabilitiesBefore.length + 1 = p.capabilitiesAfter.length
  capabilityFresh : p.newCapability ∉ p.capabilitiesBefore
  capabilityPresent : p.newCapability ∈ p.capabilitiesAfter
  recursiveRetained : p.recursiveBefore.toFinset ⊆ p.recursiveAfter.toFinset
  noRecursiveExpansionClaim : p.recursiveBefore = p.recursiveAfter
  budgetBounded : p.searchUsed ≤ p.searchBudget ∧ p.searchBudget ≤ 32 ∧ 0 < p.searchUsed
  probeCount : p.inputs.length = 8 ∧ p.targets.length = 8
  candidateMatches : p.inputs.map (execute p.program) = p.targets
  predecessorRejects : p.inheritedFamilyPrograms.all
    (fun q => decide (p.inputs.map (execute q) ≠ p.targets)) = true
  nontrivial : p.inputs ≠ p.targets

/-- Any deterministic interpretation of the identical protected projection agrees.
This does not prove that the extraction or hash-to-bytes binding is sound. -/
theorem protected_interpretation {p : Packet} (checked : FiniteFacts p)
    {Output : Type*} (interpret : List FileIdentity → Output) :
    interpret p.protectedBefore = interpret p.protectedAfter :=
  congrArg interpret checked.protectedFilesEqual

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

/-- Bind checked finite inclusion to THREE actual fields of the existing root.
The mapping equalities and the operational meaning of recursive productivity
remain explicit premises; this is not a complete AutonomousAcceptedStep. -/
theorem root_recursive_frontier_fields
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Mutation HistoryHash ChallengeHash : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    (autonomous : RcpRclmFormalCoreV4.Autonomous.Kernel
      (Objective := Objective) (Program := Mutation) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := String) learned)
    (state : State) (candidate : RCP.Candidate State Update)
    (certificate : RcpRclmFormalCoreV4.Autonomous.CertificatePacket
      BaseCertificate Task Generator Proposal PackageHash Objective Mutation
      HistoryHash ChallengeHash String)
    (p : Packet) (checked : FiniteFacts p)
    (beforeBinding : autonomous.recursiveFrontier state = p.recursiveBefore.toFinset)
    (afterBinding : autonomous.recursiveFrontier candidate.next = p.recursiveAfter.toFinset)
    (protectedBinding : certificate.protectedRecursiveFrontier = p.recursiveBefore.toFinset) :
    certificate.protectedRecursiveFrontier ⊆ autonomous.recursiveFrontier state ∧
    certificate.protectedRecursiveFrontier ⊆ autonomous.recursiveFrontier candidate.next ∧
    autonomous.recursiveFrontier state ⊆ autonomous.recursiveFrontier candidate.next := by
  rw [protectedBinding, beforeBinding, afterBinding]
  exact ⟨fun _ h => h, checked.recursiveRetained, checked.recursiveRetained⟩

end Phase17Evidence
