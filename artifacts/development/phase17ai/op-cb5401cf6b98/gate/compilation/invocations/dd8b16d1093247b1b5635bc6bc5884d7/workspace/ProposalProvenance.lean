import RcpRclmFormalCoreV4
import Mathlib.Tactic

namespace Phase17Provenance

/- Hashes, score-table construction and physical bindings are checked externally.
   This model checks deterministic present-prefix selection from the entire table.
   It does not attest that a historical process ran or furnish a full root step. -/
structure RankedProgram where
  key : String
  family : Nat
  baseScore : Int
  ties : List Nat
  deriving DecidableEq

structure Context where
  generator : String
  parentPackage : String
  contextHash : String
  transcriptHash : String
  credits : Nat
  offset : Nat
  rows : List RankedProgram
  deriving DecidableEq

structure Proposal where
  generator : String
  parentPackage : String
  contextHash : String
  transcriptHash : String
  choices : List Nat
  verdicts : List Bool
  program : String
  candidatePackage : String
  deriving DecidableEq

structure CandidateView where
  parentPackage : String
  contextHash : String
  program : String
  package : String
  deriving DecidableEq

def rowAt (c : Context) (i : Nat) : RankedProgram :=
  c.rows.getD i { key := "", family := 8, baseScore := 0, ties := [] }

def rejectedCount (c : Context) (seen : List Nat) (family : Nat) : Nat :=
  (seen.filter (fun i => (rowAt c i).family == family)).length

def score (c : Context) (seen : List Nat) (i : Nat) : Int :=
  (rowAt c i).baseScore + 797 * Int.ofNat (rejectedCount c seen (rowAt c i).family)

def tie (c : Context) (seen : List Nat) (i : Nat) : Nat :=
  (rowAt c i).ties.getD (rejectedCount c seen (rowAt c i).family) 0

def beats (c : Context) (seen : List Nat) (i j : Nat) : Bool :=
  decide (score c seen i > score c seen j ∨
    (score c seen i = score c seen j ∧ tie c seen i > tie c seen j) ∨
    (score c seen i = score c seen j ∧ tie c seen i = tie c seen j ∧ i > j))

def choose (c : Context) (seen : List Nat) : Option Nat :=
  if seen.length < 4 then
    match (List.range c.rows.length).filter (fun i => !seen.contains i) with
    | [] => none
    | first :: rest => some (rest.foldl (fun best i => if beats c seen i best then i else best) first)
  else
    ((List.range 32).map (fun i => (c.offset + 17 * i) % 32)).find? (fun i => !seen.contains i)

def follows (c : Context) (seen : List Nat) : List Nat → Bool
  | [] => true
  | i :: rest => (choose c seen == some i) && follows c (seen ++ [i]) rest

def ContextValid (c : Context) : Prop :=
  c.rows.length = 32 ∧ c.credits ≤ 32 ∧ c.offset < 32 ∧
  (c.rows.map (fun r => r.key)).Nodup ∧
  ∀ r ∈ c.rows, r.family < 8 ∧ r.ties.length = 5

def Produced (c : Context) (p : Proposal) : Prop :=
  p.generator = c.generator ∧ p.parentPackage = c.parentPackage ∧
  p.contextHash = c.contextHash ∧ p.transcriptHash = c.transcriptHash ∧
  ContextValid c ∧ follows c [] p.choices = true ∧ p.choices.Nodup ∧
  p.choices.length ≤ c.credits ∧ p.choices ≠ [] ∧
  p.verdicts = List.replicate (p.choices.length - 1) false ++ [true] ∧
  p.program = (rowAt c (p.choices.getD (p.choices.length - 1) 32)).key ∧
  p.candidatePackage ≠ p.parentPackage

def CandidateMatches (c : Context) (p : Proposal) (result : CandidateView) : Prop :=
  Produced c p ∧ result.parentPackage = c.parentPackage ∧
  result.contextHash = c.contextHash ∧ result.program = p.program ∧
  result.package = p.candidatePackage

theorem trace_no_repeat (c : Context) (p : Proposal) (h : Produced c p) :
    p.choices.Nodup := by
  rcases h with ⟨_, _, _, _, _, _, unique, _⟩
  exact unique

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

/- Supplies the actual six provenance fields. The remaining compatible kernel and
   physical observation projections are parameters, not discharged premises. -/
def attachProvenance
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView) :
    Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base :=
  { other with
    activeGenerator := fun s => (observe s).generator
    activePackageHash := fun s => (observe s).parentPackage
    generatorBound := fun s g => g = (observe s).generator ∧ ContextValid (observe s)
    proposalProducedBy := fun g s p => g = (observe s).generator ∧ Produced (observe s) p
    proposalBindsCandidate := fun s p candidate => CandidateMatches (observe s) p (candidateView candidate)
    packageHashBound := fun s g hash => g = (observe s).generator ∧
      hash = (observe s).parentPackage ∧ ContextValid (observe s) }

theorem attached_generator_bound
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView)
    (s : State) (valid : ContextValid (observe s)) :
    (attachProvenance other observe candidateView).generatorBound s
      ((attachProvenance other observe candidateView).activeGenerator s) := ⟨rfl, valid⟩

theorem attached_package_bound
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView)
    (s : State) (valid : ContextValid (observe s)) :
    (attachProvenance other observe candidateView).packageHashBound s
      ((attachProvenance other observe candidateView).activeGenerator s)
      ((attachProvenance other observe candidateView).activePackageHash s) := ⟨rfl, rfl, valid⟩

theorem attached_proposal_produced
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView)
    (s : State) (p : Proposal) (produced : Produced (observe s) p) :
    (attachProvenance other observe candidateView).proposalProducedBy
      ((attachProvenance other observe candidateView).activeGenerator s) s p := ⟨rfl, produced⟩

theorem attached_candidate_bound
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView)
    (s : State) (p : Proposal) (candidate : RCP.Candidate State Update)
    (matched : CandidateMatches (observe s) p (candidateView candidate)) :
    (attachProvenance other observe candidateView).proposalBindsCandidate s p candidate := matched

end Phase17Provenance
