import RcpRclmFormalCoreV4
import Mathlib.Tactic

/-
Phase 17G. A concrete, scoped append-only registry kernel.
Programs are immutable data. `eval` is a fixed deterministic interpretation,
not a candidate-supplied executor. Byte measurements and hash-to-data bindings
are discharged by the Python verifier, not by this file. Candidate credits are
the only resource modeled here. This is NOT the complete RCLM/Gate E kernel.
-/
namespace Phase17Registry

variable {Program : Type}

abbrev Entry (Program : Type) := String × Program

structure State (Program : Type) where
  protectedImage : List Nat
  entries : List (Entry Program)
  root : String
  deriving DecidableEq

structure Update (Program : Type) where
  key : String
  program : Program
  deriving DecidableEq

structure Evidence (Program : Type) where
  root : String
  parentEntries : List (Entry Program)
  used : Nat
  budget : Nat
  deriving DecidableEq

def lookup (key : String) : List (Entry Program) → Option Program
  | [] => none
  | e :: es => if e.1 = key then some e.2 else lookup key es

def erase (key : String) : List (Entry Program) → List (Entry Program)
  | [] => []
  | e :: es => if e.1 = key then erase key es else e :: erase key es

def apply (s : State Program) (u : Update Program) : State Program :=
  { s with entries := s.entries ++ [(u.key, u.program)] }

def recover (u : Update Program) (observed : State Program) : State Program :=
  { observed with entries := erase u.key observed.entries }

/-- Every inherited identifier keeps its program for arbitrary extension data. -/
theorem lookup_retained (xs : List (Entry Program)) (u : Update Program)
    (key : String) (p : Program) (h : lookup key xs = some p) :
    lookup key (xs ++ [(u.key, u.program)]) = some p := by
  induction xs with
  | nil => simp [lookup] at h
  | cons e es ih =>
    by_cases he : e.1 = key
    · simpa [lookup, he] using h
    · simp only [lookup, if_neg he] at h
      simpa [lookup, he] using ih h

/-- A fresh key is callable after extension. -/
theorem lookup_added (xs : List (Entry Program)) (u : Update Program)
    (h : lookup u.key xs = none) :
    lookup u.key (xs ++ [(u.key, u.program)]) = some u.program := by
  induction xs with
  | nil => simp [lookup]
  | cons e es ih =>
    by_cases he : e.1 = u.key
    · simp [lookup, he] at h
    · simp only [lookup, if_neg he] at h
      simpa [lookup, he] using ih h

theorem erase_extension (xs : List (Entry Program)) (u : Update Program)
    (h : lookup u.key xs = none) :
    erase u.key (xs ++ [(u.key, u.program)]) = xs := by
  induction xs with
  | nil => simp [erase]
  | cons e es ih =>
    by_cases he : e.1 = u.key
    · simp [lookup, he] at h
    · simp only [lookup, if_neg he] at h
      simpa [erase, he] using congrArg (List.cons e) (ih h)

theorem exact_recovery (s : State Program) (u : Update Program)
    (fresh : lookup u.key s.entries = none) : recover u (apply s u) = s := by
  cases s with
  | mk image entries root =>
    change State.mk image (erase u.key (entries ++ [(u.key, u.program)])) root = State.mk image entries root
    rw [erase_extension entries u fresh]

def dispatch {Input Output : Type} (eval : Program → Input → Output)
    (s : State Program) (key : String) (input : Input) : Option Output :=
  (lookup key s.entries).map (fun p => eval p input)

/-- Universal behavioral preservation, not a finite input sample. -/
theorem dispatch_retained {Input Output : Type}
    (eval : Program → Input → Output) (s : State Program) (u : Update Program)
    (key : String) (p : Program) (registered : lookup key s.entries = some p)
    (input : Input) :
    dispatch eval (apply s u) key input = dispatch eval s key input := by
  simp only [dispatch, apply]
  rw [lookup_retained s.entries u key p registered, registered]

structure Task (Input Output : Type) where
  key : String
  input : Input
  expected : Output

def Solves {Input Output : Type} (eval : Program → Input → Output)
    (s : State Program) (t : Task Input Output) : Prop :=
  dispatch eval s t.key t.input = some t.expected

/-- Old solved tasks retain their operational meaning under fixed evaluation. -/
theorem solved_task_retained {Input Output : Type}
    (eval : Program → Input → Output) (s : State Program) (u : Update Program)
    (t : Task Input Output) (solved : Solves eval s t) :
    Solves eval (apply s u) t := by
  cases h : lookup t.key s.entries with
  | none => simp [Solves, dispatch, h] at solved
  | some p =>
    change dispatch eval (apply s u) t.key t.input = some t.expected
    rw [dispatch_retained eval s u t.key p h t.input]
    exact solved

open RcpRclmFormalCoreV2

variable [DecidableEq Program]

/-- The concrete observation is equality of the entire protected image. -/
noncomputable def protectedValue (s : State Program) (image : List Nat) : ℝ :=
  if s.protectedImage = image then 1 else 0

noncomputable def distance (x y : State Program) : ℝ := if x = y then 0 else 1

def admissible (s : State Program) : Prop :=
  s.root ≠ "" ∧ ∀ n ∈ s.protectedImage, n < 256

def trustValid (s : State Program) (c : RCP.Candidate (State Program) (Update Program))
    (e : Evidence Program) : Prop :=
  e.root = s.root ∧ c.next.root = s.root ∧ e.parentEntries = s.entries

def realityContained (s : State Program)
    (c : RCP.Candidate (State Program) (Update Program)) (e : Evidence Program) : Prop :=
  c.next = apply s c.update ∧ lookup c.update.key s.entries = none ∧
    c.update.key ≠ "" ∧ e.parentEntries = s.entries

/-- Nonconstant protected observations, credit residuals, and rejectable reality
checks instantiate the actual immutable RCP.Kernel structure. Program validity,
unique identifiers, serialization, and physical binding are additional Python
checks; this formal instance deliberately covers only append-only registry state. -/
noncomputable def kernel [Inhabited Program] : RCP.Kernel (State Program) (Update Program)
    (Evidence Program) (List Nat) Unit where
  apply := apply
  admissible := admissible
  protectedInvariant := admissible
  protectedValue := protectedValue
  protectedValue_nonconstant := by
    refine ⟨⟨[], [], "r"⟩, [], ⟨[1], [], "r"⟩, [], ?_⟩
    norm_num [protectedValue]
  transportProtected := fun _ _ image => image
  lossBudget := fun _ _ => 0
  lossBudget_nonnegative := by intros; exact le_rfl
  stateDistance := distance
  stateDistance_nonnegative := by intros; unfold distance; split <;> norm_num
  recover := fun _ c observed => recover c.update observed
  recoveryBudget := fun _ _ => 0
  recoveryBudget_nonnegative := by intros; exact le_rfl
  progress := fun s => (s.entries.length : ℝ)
  strictWitness := fun s c _ => lookup c.update.key s.entries = none
  residual := fun _ _ e _ => (e.used : ℝ) - (e.budget : ℝ)
  residual_nonconstant := by
    let s : State Program := ⟨[], [], "r"⟩
    let c : RCP.Candidate (State Program) (Update Program) := ⟨⟨"k", default⟩, s⟩
    refine ⟨s, c, ⟨"r", [], 0, 0⟩, s, c, ⟨"r", [], 1, 0⟩, (), ?_⟩
    norm_num
  trustValid := trustValid
  resourceValid := fun _ _ e => e.used ≤ e.budget ∧ e.budget ≤ 32
  realityContained := realityContained
  realityContained_not_universal := by
    let s : State Program := ⟨[], [], "r"⟩
    let c : RCP.Candidate (State Program) (Update Program) := ⟨⟨"", default⟩, s⟩
    refine ⟨s, c, ⟨"r", [], 0, 0⟩, ?_⟩
    simp [realityContained, c]

/-- All eleven base obligations for this explicitly scoped concrete kernel.
No LearnedAcceptedStep or AutonomousAcceptedStep is asserted here. -/
theorem base_step_sound [Inhabited Program]
    (s : State Program) (u : Update Program) (e : Evidence Program)
    (valid : admissible s)
    (fresh : lookup u.key s.entries = none)
    (keyValid : u.key ≠ "")
    (rootBound : e.root = s.root)
    (parentBound : e.parentEntries = s.entries)
    (credits : e.used ≤ e.budget) (ceiling : e.budget ≤ 32) :
    RCP.StepObligations kernel s ⟨u, apply s u⟩ e := by
  constructor
  · rfl
  · intro _index
    change (e.used : ℝ) - (e.budget : ℝ) ≤ 0
    exact sub_nonpos.mpr (by exact_mod_cast credits)
  · intro image
    change protectedValue s image ≤ protectedValue s image + 0
    simpa only [add_zero] using (le_refl (protectedValue s image))
  · change distance (recover u (apply s u)) s ≤ 0
    rw [exact_recovery s u fresh]
    simp [distance]
  · change admissible (apply s u)
    exact valid
  · change (s.entries.length : ℝ) ≤ ((s.entries ++ [(u.key, u.program)]).length : ℝ)
    simp
  · intro _witness
    change (s.entries.length : ℝ) < ((s.entries ++ [(u.key, u.program)]).length : ℝ)
    simp
  · exact ⟨rootBound, rfl, parentBound⟩
  · exact ⟨credits, ceiling⟩
  · exact ⟨rfl, fresh, keyValid, parentBound⟩
  · change admissible (apply s u)
    exact valid

end Phase17Registry
