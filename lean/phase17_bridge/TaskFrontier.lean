import RcpRclmFormalCoreV4
import Mathlib.Tactic
import Mathlib.Data.Finset.Filter

namespace Phase17TaskMeaning

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

-- State projection is supplied by the external physical evaluator. These proofs
-- do not establish that arbitrary self-reported observations describe a model.
structure ObservationState where
  proofs : List (String × String × String)
  programs : List (String × Program)

structure Meaning where
  check : ObservationState → Bool
  holds : ObservationState → Prop
  sound : ∀ s, check s = true → holds s

def theoremMeaning (task source decode : String) (P : Prop) (proof : P) : Meaning where
  check := fun s => decide ((task, source, decode) ∈ s.proofs)
  holds := fun s => (task, source, decode) ∈ s.proofs ∧ P
  sound := by
    intro s h
    exact ⟨of_decide_eq_true h, proof⟩

structure VectorContract where
  family : Nat
  requiredProgram : Option String
  inputs : List (List Int)
  targets : List (List Int)

def vectorMeaning (t : VectorContract) : Meaning where
  check := fun s => s.programs.any (fun e => decide
    (e.2.family = t.family ∧
     (t.requiredProgram = none ∨ t.requiredProgram = some e.1) ∧
     t.inputs.map (execute e.2) = t.targets))
  holds := fun s => ∃ e ∈ s.programs,
    e.2.family = t.family ∧
    (t.requiredProgram = none ∨ t.requiredProgram = some e.1) ∧
    t.inputs.map (execute e.2) = t.targets
  sound := by
    intro s h
    simpa only [List.any_eq_true, decide_eq_true_eq] using h

def rejectMeaning : Meaning where
  check := fun _ => false
  holds := fun _ => False
  sound := by intro s h; cases h

def checkedFrontier (declared : Finset Nat) (catalog : Nat → Meaning)
    (s : ObservationState) : Finset Nat :=
  declared.filter (fun t => (catalog t).check s = true)

theorem checked_frontier_sound (declared : Finset Nat) (catalog : Nat → Meaning)
    (s : ObservationState) {task : Nat}
    (member : task ∈ checkedFrontier declared catalog s) : (catalog task).holds s := by
  exact (catalog task).sound s (Finset.mem_filter.mp member).2

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

-- Supplies the ACTUAL frontier/solves/frontierSound fields of the immutable root.
-- All other kernel fields and their adequacy remain obligations of the caller.
def attachTaskSemantics
    {State Update BaseCertificate Protected ResidualIndex Generator Proposal PackageHash : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → ObservationState) (declared : State → Finset Nat)
    (catalog : Nat → Meaning) :
    Learned.FrontierKernel (Task := Nat) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base :=
  { other with
    frontier := fun s => checkedFrontier (declared s) catalog (observe s)
    solves := fun s task => (catalog task).holds (observe s)
    frontierSound := by
      intro s task member
      exact checked_frontier_sound (declared s) catalog (observe s) member }

theorem attached_root_frontier_sound
    {State Update BaseCertificate Protected ResidualIndex Generator Proposal PackageHash : Type*}
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Nat) (Generator := Generator)
      (Proposal := Proposal) (PackageHash := PackageHash) base)
    (observe : State → ObservationState) (declared : State → Finset Nat)
    (catalog : Nat → Meaning) {s : State} {task : Nat}
    (member : task ∈ (attachTaskSemantics other observe declared catalog).frontier s) :
    (attachTaskSemantics other observe declared catalog).solves s task :=
  (attachTaskSemantics other observe declared catalog).frontierSound member

end Phase17TaskMeaning
