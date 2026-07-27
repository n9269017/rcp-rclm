import RcpRclmFormalCoreV4.Autonomous.Kernel

namespace RcpRclmFormalCoreV4
namespace Autonomous

open RcpRclmFormalCoreV2
open RcpRclmFormalCoreV3

/-- The first accepted candidate in deterministic enumeration order. -/
def firstAccepted
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
    (state : State) :
    List (SearchAttempt State Update BaseCertificate Task Generator Proposal PackageHash
      Objective Program HistoryHash ChallengeHash RecursiveTask) →
    Option (SearchAttempt State Update BaseCertificate Task Generator Proposal PackageHash
      Objective Program HistoryHash ChallengeHash RecursiveTask)
  | [] => none
  | attempt :: rest =>
      if checker.check state attempt.candidate attempt.certificate = true then
        some attempt
      else
        firstAccepted checker state rest

/-- Any attempt returned by bounded search is actually accepted by the Gate E checker. -/
theorem firstAccepted_sound
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
    (state : State)
    {attempts : List (SearchAttempt State Update BaseCertificate Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask)}
    {attempt : SearchAttempt State Update BaseCertificate Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask}
    (found : firstAccepted checker state attempts = some attempt) :
    checker.check state attempt.candidate attempt.certificate = true := by
  induction attempts with
  | nil =>
      simp [firstAccepted] at found
  | cons head tail inductionHypothesis =>
      by_cases headAccepted :
          checker.check state head.candidate head.certificate = true
      · simp [firstAccepted, headAccepted] at found
        subst attempt
        exact headAccepted
      · simp [firstAccepted, headAccepted] at found
        exact inductionHypothesis found

/-- A `none` result classifies every enumerated candidate as nonaccepted. -/
theorem firstAccepted_none
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
    (state : State)
    {attempts : List (SearchAttempt State Update BaseCertificate Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask)}
    (exhausted : firstAccepted checker state attempts = none) :
    ∀ attempt ∈ attempts,
      checker.check state attempt.candidate attempt.certificate ≠ true := by
  induction attempts with
  | nil =>
      simp
  | cons head tail inductionHypothesis =>
      by_cases headAccepted :
          checker.check state head.candidate head.certificate = true
      · simp [firstAccepted, headAccepted] at exhausted
      · have tailExhausted : firstAccepted checker state tail = none := by
          simpa [firstAccepted, headAccepted] using exhausted
        intro attempt member
        rcases List.mem_cons.mp member with rfl | tailMember
        · exact headAccepted
        · exact inductionHypothesis tailExhausted attempt tailMember

/-- Relative completeness: any accepted member of the finite enumeration is found. -/
theorem bounded_search_complete
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
    (state : State)
    (attempts : List (SearchAttempt State Update BaseCertificate Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask))
    (acceptedExists : ∃ attempt ∈ attempts,
      checker.check state attempt.candidate attempt.certificate = true) :
    ∃ attempt, firstAccepted checker state attempts = some attempt := by
  cases found : firstAccepted checker state attempts with
  | none =>
      rcases acceptedExists with ⟨attempt, member, accepted⟩
      exact False.elim ((firstAccepted_none checker state found attempt member) accepted)
  | some attempt =>
      exact ⟨attempt, rfl⟩

/-- Proof-carrying bounded-search exhaustion. -/
structure SearchExhaustionCertificate
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
    (state : State) where
  attempts : List (SearchAttempt State Update BaseCertificate Task Generator Proposal
    PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask)
  exhausted : firstAccepted checker state attempts = none

/-- Every attempt covered by a search-exhaustion certificate is nonaccepted. -/
theorem search_exhaustion_sound
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
    (state : State)
    (certificate : SearchExhaustionCertificate checker state) :
    ∀ attempt ∈ certificate.attempts,
      checker.check state attempt.candidate attempt.certificate ≠ true :=
  firstAccepted_none checker state certificate.exhausted

/-- Deterministic search either returns an accepted attempt or a sound exhaustion witness. -/
theorem nonstagnation_or_certified_exhaustion
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
    (state : State)
    (attempts : List (SearchAttempt State Update BaseCertificate Task Generator Proposal
      PackageHash Objective Program HistoryHash ChallengeHash RecursiveTask)) :
    (∃ attempt,
      firstAccepted checker state attempts = some attempt ∧
        checker.check state attempt.candidate attempt.certificate = true) ∨
    (∃ certificate : SearchExhaustionCertificate checker state,
      certificate.attempts = attempts) := by
  cases found : firstAccepted checker state attempts with
  | none =>
      exact Or.inr ⟨⟨attempts, found⟩, rfl⟩
  | some attempt =>
      exact Or.inl ⟨attempt, rfl, firstAccepted_sound checker state found⟩

/-- Package-bound deterministic bounded-search engine. -/
structure AutonomousImprover
    (State HistoryHash Attempt : Type*) where
  history : State → HistoryHash
  enumerate : State → HistoryHash → List Attempt

end Autonomous
end RcpRclmFormalCoreV4
