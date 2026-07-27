import RcpRclmFormalCoreV4.Autonomous.Types

namespace RcpRclmFormalCoreV4
namespace Autonomous

open RcpRclmFormalCoreV2
open RcpRclmFormalCoreV3

/--
Gate E extends Gate D with an endogenous search contract and a second finite frontier
for recursive-improvement productivity.  The trusted checker, trust anchor, hidden
challenge store, promotion authority, serializer, ledger, and rollback authority remain
outside this kernel.
-/
structure Kernel
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base) where
  recursiveFrontier : State → Finset RecursiveTask
  recursivelyProductive : State → RecursiveTask → Prop
  recursiveFrontierSound : ∀ {state task},
    task ∈ recursiveFrontier state → recursivelyProductive state task

  objectiveEndogenous : State → HistoryHash → Objective → Prop
  programEndogenous : State → HistoryHash → Objective → Program → Prop
  challengeFresh : State → ChallengeHash → Prop
  historyBound : State → HistoryHash → Prop
  noRouteHints : State → HistoryHash → Prop

  programBindsCandidate : State → Program → RCP.Candidate State Update → Prop
  programBindsCertificate : State → Program →
    Learned.CertificatePacket BaseCertificate Task Generator Proposal PackageHash → Prop

  searchCost : State → RCP.Candidate State Update → Nat
  searchBudget : State → RCP.Candidate State Update → Nat

/-- Gate E obligations beyond the already proved complete Gate D accepted step. -/
structure SpecificObligations
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    (autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned)
    (state : State)
    (candidate : RCP.Candidate State Update)
    (certificate : CertificatePacket BaseCertificate Task Generator Proposal PackageHash
      Objective Program HistoryHash ChallengeHash RecursiveTask) : Prop where
  objectiveSelectedEndogenously :
    autonomous.objectiveEndogenous state certificate.historyHash certificate.objective
  programProducedEndogenously :
    autonomous.programEndogenous state certificate.historyHash
      certificate.objective certificate.program
  hiddenChallengeFresh : autonomous.challengeFresh state certificate.challengeHash
  historyIsBound : autonomous.historyBound state certificate.historyHash
  routeHintsAbsent : autonomous.noRouteHints state certificate.historyHash

  programCandidateBinding :
    autonomous.programBindsCandidate state certificate.program candidate
  programCertificateBinding :
    autonomous.programBindsCertificate state certificate.program certificate.learned

  protectedRecursiveFrontierCertified :
    certificate.protectedRecursiveFrontier ⊆ autonomous.recursiveFrontier state
  protectedRecursiveFrontierRetained :
    certificate.protectedRecursiveFrontier ⊆ autonomous.recursiveFrontier candidate.next
  recursiveFrontierRetained :
    autonomous.recursiveFrontier state ⊆ autonomous.recursiveFrontier candidate.next
  recursiveWitnessValid :
    match certificate.recursiveWitness with
    | none => True
    | some task =>
        task ∉ autonomous.recursiveFrontier state ∧
          task ∈ autonomous.recursiveFrontier candidate.next

  searchWithinBudget :
    autonomous.searchCost state candidate ≤ autonomous.searchBudget state candidate

/-- Complete Gate E accepted step: complete Gate D soundness plus autonomous-search evidence. -/
structure AutonomousAcceptedStep
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    (autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned)
    (state : State)
    (candidate : RCP.Candidate State Update)
    (certificate : CertificatePacket BaseCertificate Task Generator Proposal PackageHash
      Objective Program HistoryHash ChallengeHash RecursiveTask) : Prop where
  learnedStep : Learned.LearnedAcceptedStep learned state candidate certificate.learned
  autonomousObligations : SpecificObligations autonomous state candidate certificate

/-- Boolean checker refinement from Gate E acceptance to the immutable Gate D checker. -/
structure TrustedAutonomousChecker
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    (autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned)
    {baseChecker : RCP.TrustedChecker base}
    (learnedChecker : Learned.TrustedLearnedChecker learned baseChecker) where
  check : State → RCP.Candidate State Update →
    CertificatePacket BaseCertificate Task Generator Proposal PackageHash
      Objective Program HistoryHash ChallengeHash RecursiveTask → Bool
  refinesLearned : ∀ {state candidate certificate},
    check state candidate certificate = true →
      learnedChecker.check state candidate certificate.learned = true
  autonomousSound : ∀ {state candidate certificate},
    base.admissible state →
    base.protectedInvariant state →
    check state candidate certificate = true →
      SpecificObligations autonomous state candidate certificate

/-- Gate E one-step checker soundness. -/
theorem autonomous_accepted_step_sound
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned}
    {baseChecker : RCP.TrustedChecker base}
    {learnedChecker : Learned.TrustedLearnedChecker learned baseChecker}
    (checker : TrustedAutonomousChecker autonomous learnedChecker)
    {state : State}
    {candidate : RCP.Candidate State Update}
    {certificate : CertificatePacket BaseCertificate Task Generator Proposal PackageHash
      Objective Program HistoryHash ChallengeHash RecursiveTask}
    (stateAdmissible : base.admissible state)
    (stateInvariant : base.protectedInvariant state)
    (accepted : checker.check state candidate certificate = true) :
    AutonomousAcceptedStep autonomous state candidate certificate := by
  exact
    { learnedStep := Learned.learned_accepted_step_sound learnedChecker
        stateAdmissible stateInvariant (checker.refinesLearned accepted)
      autonomousObligations :=
        checker.autonomousSound stateAdmissible stateInvariant accepted }

/-- Every accepted Gate E step retains all previously certified recursive productivity. -/
theorem recursive_productivity_retained
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned}
    {state : State}
    {candidate : RCP.Candidate State Update}
    {certificate : CertificatePacket BaseCertificate Task Generator Proposal PackageHash
      Objective Program HistoryHash ChallengeHash RecursiveTask}
    (accepted : AutonomousAcceptedStep autonomous state candidate certificate) :
    autonomous.recursiveFrontier state ⊆
      autonomous.recursiveFrontier candidate.next :=
  accepted.autonomousObligations.recursiveFrontierRetained

/-- A named recursive-productivity witness is genuinely new in the accepted successor. -/
theorem recursive_productivity_strictly_expands_when_witnessed
    {State Update BaseCertificate Protected ResidualIndex Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask : Type*}
    [DecidableEq Task]
    [DecidableEq RecursiveTask]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    {learned : Learned.FrontierKernel
      (Task := Task) (Generator := Generator) (Proposal := Proposal)
      (PackageHash := PackageHash) base}
    {autonomous : Kernel
      (Objective := Objective) (Program := Program) (HistoryHash := HistoryHash)
      (ChallengeHash := ChallengeHash) (RecursiveTask := RecursiveTask) learned}
    {state : State}
    {candidate : RCP.Candidate State Update}
    {certificate : CertificatePacket BaseCertificate Task Generator Proposal PackageHash
      Objective Program HistoryHash ChallengeHash RecursiveTask}
    (accepted : AutonomousAcceptedStep autonomous state candidate certificate)
    {task : RecursiveTask}
    (witness : certificate.recursiveWitness = some task) :
    task ∉ autonomous.recursiveFrontier state ∧
      task ∈ autonomous.recursiveFrontier candidate.next := by
  simpa [witness] using accepted.autonomousObligations.recursiveWitnessValid

end Autonomous
end RcpRclmFormalCoreV4
