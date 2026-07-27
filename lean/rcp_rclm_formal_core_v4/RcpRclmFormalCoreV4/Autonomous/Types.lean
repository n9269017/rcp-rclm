import Mathlib.Data.Finset.Card
import RcpRclmFormalCoreV3.Learned

namespace RcpRclmFormalCoreV4
namespace Autonomous

open RcpRclmFormalCoreV2
open RcpRclmFormalCoreV3

/-- Immutable search history supplied to the active package. -/
structure SearchHistory (Entry Hash : Type*) where
  entries : List Entry
  historyHash : Hash

/-- A state paired with the exact immutable history visible to autonomous search. -/
structure SearchState (State Entry Hash : Type*) where
  active : State
  history : SearchHistory Entry Hash

/-- A challenge source kept outside the learned package until candidate freeze. -/
structure FreshChallengeSource (State Challenge Commitment : Type*) where
  issue : State → Challenge
  commitment : Challenge → Commitment
  hiddenBeforeFreeze : State → Challenge → Prop

/-- Objective data whose authority comes from the active package rather than the host. -/
structure EndogenousObjective (State History Objective : Type*) where
  value : Objective
  selectedByActivePackage : State → History → Objective → Prop

/-- Typed mutation-program data whose authority comes from the active package. -/
structure EndogenousMutationProgram (State History Objective Program : Type*) where
  value : Program
  producedByActivePackage : State → History → Objective → Program → Prop

/-- Name-bearing object for independently certified recursive-improvement abilities. -/
structure RecursiveProductivityTask (Capability : Type*) where
  capability : Capability

/--
Gate E certificate packet.  The inherited Gate D packet remains authoritative for
accepted-step soundness; the additional fields bind objective choice, mutation program,
search history, hidden challenge, and recursive-productivity evidence.
-/
structure CertificatePacket
    (BaseCertificate Task Generator Proposal PackageHash Objective Program HistoryHash
      ChallengeHash RecursiveTask : Type*)
    [DecidableEq Task]
    [DecidableEq RecursiveTask] where
  learned : Learned.CertificatePacket BaseCertificate Task Generator Proposal PackageHash
  objective : Objective
  program : Program
  historyHash : HistoryHash
  challengeHash : ChallengeHash
  protectedRecursiveFrontier : Finset RecursiveTask
  recursiveWitness : Option RecursiveTask

/-- One concrete candidate considered by the bounded autonomous search procedure. -/
structure SearchAttempt
    (State Update BaseCertificate Task Generator Proposal PackageHash Objective Program
      HistoryHash ChallengeHash RecursiveTask : Type*)
    [DecidableEq Task]
    [DecidableEq RecursiveTask] where
  candidate : RCP.Candidate State Update
  certificate : CertificatePacket BaseCertificate Task Generator Proposal PackageHash
    Objective Program HistoryHash ChallengeHash RecursiveTask

/-- Deterministic finite candidate enumeration at one active package state. -/
structure CandidateEnumerator (State History Attempt : Type*) where
  enumerate : State → History → List Attempt

/-- A frozen fairness relation for a finite enumerator. -/
structure FairSearchPolicy (State History Attempt : Type*) where
  eligible : State → History → Attempt → Prop
  covered : State → History → List Attempt → Prop

end Autonomous
end RcpRclmFormalCoreV4
