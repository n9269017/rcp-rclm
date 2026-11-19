import Std
import Lean.Elab.Tactic.Omega

/- Phase 17AL: the durable admission, launch and completion protocol for the
   existing Phase 17O bounded campaign. The runtime checks the complete journal,
   source closure, objective, sealed transcript and controller order before
   emitting these projections. Strings below are exact retained identities,
   not proofs of hashing, authentication, executable refinement or persistence.
   A single authoritative root, its transaction implementation and trusted
   backend dispatch are assumptions. Separate processes under one OS identity
   do not establish a protected external authority. Declared vector work omits
   host, provisioning, transport, storage, verification and other campaign work.
   This module therefore proves neither complete accounting nor physical root
   exclusivity. It does not call AK's specialized AI/AJ reference transition. -/
namespace Phase17DurableCampaign

structure Usage where
  candidates : Nat
  vectors : Nat
  inputs : Nat
  outputs : Nat
  deriving DecidableEq

def Usage.zero : Usage := ⟨0, 0, 0, 0⟩
def Usage.add (a b : Usage) : Usage :=
  ⟨a.candidates + b.candidates, a.vectors + b.vectors,
   a.inputs + b.inputs, a.outputs + b.outputs⟩
def Usage.cost (u : Usage) : Nat :=
  64 * u.candidates + 16 * u.vectors + u.inputs + u.outputs
def Usage.LE (a b : Usage) : Prop :=
  a.candidates ≤ b.candidates ∧ a.vectors ≤ b.vectors ∧
  a.inputs ≤ b.inputs ∧ a.outputs ≤ b.outputs

instance usageLEDecidable (a b : Usage) : Decidable (a.LE b) := by
  unfold Usage.LE
  infer_instance

structure Budget where
  limits : Usage
  costLimit : Nat
  deriving DecidableEq

def Fits (budget : Budget) (u : Usage) : Prop :=
  u.LE budget.limits ∧ u.cost ≤ budget.costLimit

instance fitsDecidable (budget : Budget) (u : Usage) : Decidable (Fits budget u) := by
  unfold Fits
  infer_instance

/-- The unchanged Phase 17O envelope: one predecessor replay, each installed
    program and at most `credits` candidate programs, eight four-value calls
    each. The mathematical operations counted here are explicitly finite. -/
def envelope (installed credits : Nat) : Usage :=
  ⟨credits, 8 * (1 + installed + credits),
   32 * (1 + installed + credits), 32 * (1 + installed + credits)⟩

theorem envelope_cost (installed credits : Nat) :
    (envelope installed credits).cost =
      64 * credits + 192 * (1 + installed + credits) := by
  simp only [envelope, Usage.cost]
  omega

theorem envelope_monotone (installed actual credits : Nat) (bound : actual ≤ credits) :
    (envelope installed actual).LE (envelope installed credits) := by
  simp only [envelope, Usage.LE]
  omega

theorem usage_cost_monotone (a b : Usage) (bound : a.LE b) : a.cost ≤ b.cost := by
  rcases bound with ⟨hc, hv, hi, ho⟩
  unfold Usage.cost
  omega

theorem usage_add_cost (a b : Usage) : (a.add b).cost = a.cost + b.cost := by
  simp only [Usage.add, Usage.cost]
  omega

theorem usage_not_refunded (a b : Usage) : a.LE (a.add b) := by
  simp only [Usage.LE, Usage.add]
  omega

structure Binding where
  campaign : String
  parentState : String
  parentPackage : String
  verifier : String
  policy : String
  implementation : String
  objectivePolicy : String
  evaluatorProtocol : String
  workerProtocol : String
  accountingProfile : String
  deriving DecidableEq

structure Provision where
  identity : String
  binding : Binding
  installed : Nat
  budget : Budget
  deriving DecidableEq

structure Cursor where
  provision : String
  epoch : Nat
  serial : Nat
  head : String
  journal : String
  image : String
  deriving DecidableEq

structure Pending where
  grant : String
  freeze : String
  credits : Nat
  reservationEpoch : Nat
  ownerEpoch : Option Nat
  launched : Bool
  deriving DecidableEq

inductive Status where
  | open | pending | denied
  deriving DecidableEq

structure State where
  provision : String
  epoch : Nat
  serial : Nat
  head : String
  journal : String
  image : String
  reserved : Usage
  sessionCount : Nat
  pending : Option Pending
  nonces : List String
  freezes : List String
  completedWork : Usage
  completedCount : Nat
  status : Status
  deriving DecidableEq

def cursor (s : State) : Cursor :=
  ⟨s.provision, s.epoch, s.serial, s.head, s.journal, s.image⟩

inductive Command where
  | reopen
  | reserve (nonce freeze grant : String) (credits : Nat)
  | deny (nonce freeze grant : String) (credits : Nat)
  | launch (grant : String)
  | complete (grant transcript : String) (actual : Nat)
  deriving DecidableEq

inductive Mode where
  | backend | request
  deriving DecidableEq

/-- Backend-only operations are dispatched internally. The caller does not
    authenticate itself by choosing this mode in a request. -/
def ModeBound (mode : Mode) (command : Command) : Prop :=
  match command with
  | .reserve .. | .deny .. => mode = .request
  | _ => mode = .backend

instance modeBoundDecidable (mode : Mode) (command : Command) :
    Decidable (ModeBound mode command) := by
  cases command <;> unfold ModeBound <;> infer_instance

def Admission (p : Provision) (s : State) (nonce freeze grant : String) (credits : Nat) : Prop :=
  s.status = .open ∧ s.pending = none ∧ p.installed ≤ 1024 ∧ credits ≤ 32 ∧
  nonce ≠ "" ∧ nonce ∉ s.nonces ∧ freeze ≠ "" ∧ freeze ∉ s.freezes ∧ grant ≠ ""

instance admissionDecidable (p : Provision) (s : State) (nonce freeze grant : String) (credits : Nat) :
    Decidable (Admission p s nonce freeze grant credits) := by
  unfold Admission
  infer_instance

def CommandAllowed (p : Provision) (s : State) (command : Command) : Prop :=
  match command with
  | .reopen => True
  | .reserve nonce freeze grant credits =>
      Admission p s nonce freeze grant credits ∧ Fits p.budget (s.reserved.add (envelope p.installed credits))
  | .deny nonce freeze grant credits =>
      Admission p s nonce freeze grant credits ∧ ¬ Fits p.budget (s.reserved.add (envelope p.installed credits))
  | .launch grant =>
      match s.pending with
      | none => False
      | some pending => s.status = .pending ∧ pending.grant = grant ∧
          pending.ownerEpoch = some s.epoch ∧ pending.launched = false
  | .complete grant transcript actual =>
      match s.pending with
      | none => False
      | some pending => s.status = .pending ∧ pending.grant = grant ∧
          pending.ownerEpoch = some s.epoch ∧ pending.launched = true ∧
          transcript ≠ "" ∧ actual ≤ pending.credits

instance commandAllowedDecidable (p : Provision) (s : State) (command : Command) :
    Decidable (CommandAllowed p s command) := by
  cases command <;> cases hp : s.pending <;> simp only [CommandAllowed, hp] <;> infer_instance

def JournalBound (s : State) (command : Command) (journal : String) : Prop :=
  match command with
  | .reopen | .launch _ => journal = s.journal
  | _ => journal ≠ "" ∧ journal ≠ s.journal

instance journalBoundDecidable (s : State) (command : Command) (journal : String) :
    Decidable (JournalBound s command journal) := by
  cases command <;> unfold JournalBound <;> infer_instance

def Guard (p : Provision) (supplied : Binding) (s : State) (expected : Cursor)
    (mode : Mode) (command : Command) (head journal image : String) : Prop :=
  p.identity ≠ "" ∧ s.provision = p.identity ∧ supplied = p.binding ∧
  expected = cursor s ∧ ModeBound mode command ∧ CommandAllowed p s command ∧
  head ≠ "" ∧ head ≠ s.head ∧ image ≠ "" ∧ JournalBound s command journal ∧
  (command = .reopen ∨ 0 < s.epoch)

instance guardDecidable (p : Provision) (supplied : Binding) (s : State) (expected : Cursor)
    (mode : Mode) (command : Command) (head journal image : String) :
    Decidable (Guard p supplied s expected mode command head journal image) := by
  unfold Guard
  infer_instance

def bodyNext (p : Provision) (s : State) : Command → State
  | .reopen => { s with
      epoch := s.epoch + 1
      pending := s.pending.map (fun pending => { pending with ownerEpoch := none }) }
  | .reserve nonce freeze grant credits => { s with
      reserved := s.reserved.add (envelope p.installed credits),
      sessionCount := s.sessionCount + 1,
      pending := some ⟨grant, freeze, credits, s.epoch, some s.epoch, false⟩,
      nonces := s.nonces ++ [nonce], freezes := s.freezes ++ [freeze], status := .pending }
  | .deny nonce _ _ _ => { s with nonces := s.nonces ++ [nonce], status := .denied }
  | .launch _ => { s with pending := s.pending.map (fun pending => { pending with launched := true }) }
  | .complete _ _ actual => { s with
      pending := none
      status := .open
      completedWork := s.completedWork.add (envelope p.installed actual)
      completedCount := s.completedCount + 1 }

def installed (p : Provision) (s : State) (command : Command) (head journal image : String) : State :=
  { bodyNext p s command with serial := s.serial + 1, head := head, journal := journal, image := image }

def commit (p : Provision) (supplied : Binding) (s : State) (expected : Cursor)
    (mode : Mode) (command : Command) (head journal image : String) : Option State :=
  if Guard p supplied s expected mode command head journal image then
    some (installed p s command head journal image)
  else none

theorem committed_spec (p : Provision) (supplied : Binding) (s next : State) (expected : Cursor)
    (mode : Mode) (command : Command) (head journal image : String)
    (accepted : commit p supplied s expected mode command head journal image = some next) :
    Guard p supplied s expected mode command head journal image ∧
      next = installed p s command head journal image := by
  unfold commit at accepted
  split at accepted
  next valid => exact ⟨valid, (Option.some.inj accepted).symm⟩
  next invalid => cases accepted

theorem committed_construct (p : Provision) (supplied : Binding) (s : State) (expected : Cursor)
    (mode : Mode) (command : Command) (head journal image : String)
    (valid : Guard p supplied s expected mode command head journal image) :
    commit p supplied s expected mode command head journal image =
      some (installed p s command head journal image) := by simp only [commit, valid, if_true]

theorem committed_binding (p : Provision) (supplied : Binding) (s next : State) (expected : Cursor)
    (mode : Mode) (command : Command) (head journal image : String)
    (accepted : commit p supplied s expected mode command head journal image = some next) :
    supplied = p.binding ∧ expected = cursor s :=
  let valid := (committed_spec p supplied s next expected mode command head journal image accepted).1
  ⟨valid.2.2.1, valid.2.2.2.1⟩

theorem wrong_binding_refused (p : Provision) (supplied : Binding) (s : State) (expected : Cursor)
    (mode : Mode) (command : Command) (head journal image : String) (wrong : supplied ≠ p.binding) :
    commit p supplied s expected mode command head journal image = none := by
  have invalid : ¬ Guard p supplied s expected mode command head journal image := fun h => wrong h.2.2.1
  simp only [commit, invalid, if_false]

theorem stale_cursor_refused (p : Provision) (supplied : Binding) (s : State) (expected : Cursor)
    (mode : Mode) (command : Command) (head journal image : String) (stale : expected ≠ cursor s) :
    commit p supplied s expected mode command head journal image = none := by
  have invalid : ¬ Guard p supplied s expected mode command head journal image := fun h => stale h.2.2.2.1
  simp only [commit, invalid, if_false]

theorem request_cannot_reopen (p : Provision) (supplied : Binding) (s : State) (expected : Cursor)
    (head journal image : String) :
    commit p supplied s expected .request .reopen head journal image = none := by
  simp [commit, Guard, ModeBound]

theorem committed_serial (p : Provision) (supplied : Binding) (s next : State) (expected : Cursor)
    (mode : Mode) (command : Command) (head journal image : String)
    (accepted : commit p supplied s expected mode command head journal image = some next) :
    next.serial = s.serial + 1 := by
  rw [(committed_spec p supplied s next expected mode command head journal image accepted).2]
  rfl

theorem predecessor_cursor_consumed_once (p : Provision) (supplied : Binding) (s next : State)
    (expected : Cursor) (mode : Mode) (command : Command) (head journal image : String)
    (accepted : commit p supplied s expected mode command head journal image = some next)
    (laterMode : Mode) (laterCommand : Command) (laterHead laterJournal laterImage : String) :
    commit p supplied next expected laterMode laterCommand laterHead laterJournal laterImage = none := by
  apply stale_cursor_refused
  intro equal
  have before := (committed_binding p supplied s next expected mode command head journal image accepted).2
  have serialEqual := congrArg Cursor.serial (before.symm.trans equal)
  have step := committed_serial p supplied s next expected mode command head journal image accepted
  simp only [cursor] at serialEqual
  omega

theorem reserved_exact (p : Provision) (supplied : Binding) (s next : State) (expected : Cursor)
    (nonce freeze grant : String) (credits : Nat) (head journal image : String)
    (accepted : commit p supplied s expected .request (.reserve nonce freeze grant credits)
      head journal image = some next) :
    next.reserved = s.reserved.add (envelope p.installed credits) ∧
      Fits p.budget next.reserved ∧ next.sessionCount = s.sessionCount + 1 := by
  obtain ⟨valid, equal⟩ := committed_spec p supplied s next expected .request
    (.reserve nonce freeze grant credits) head journal image accepted
  rw [equal]
  exact ⟨rfl, valid.2.2.2.2.2.1.2, rfl⟩

theorem replayed_nonce_refused (p : Provision) (supplied : Binding) (s : State) (expected : Cursor)
    (nonce freeze grant : String) (credits : Nat) (head journal image : String) (used : nonce ∈ s.nonces) :
    commit p supplied s expected .request (.reserve nonce freeze grant credits) head journal image = none := by
  have invalid : ¬ Guard p supplied s expected .request (.reserve nonce freeze grant credits) head journal image := by
    intro valid
    exact valid.2.2.2.2.2.1.1.2.2.2.2.2.1 used
  simp only [commit, invalid, if_false]

theorem denied_no_reservation (p : Provision) (supplied : Binding) (s next : State) (expected : Cursor)
    (nonce freeze grant : String) (credits : Nat) (head journal image : String)
    (accepted : commit p supplied s expected .request (.deny nonce freeze grant credits)
      head journal image = some next) :
    next.reserved = s.reserved ∧ next.sessionCount = s.sessionCount ∧
      ¬ Fits p.budget (s.reserved.add (envelope p.installed credits)) := by
  obtain ⟨valid, equal⟩ := committed_spec p supplied s next expected .request
    (.deny nonce freeze grant credits) head journal image accepted
  rw [equal]
  exact ⟨rfl, rfl, valid.2.2.2.2.2.1.2⟩

theorem launched_consumed (p : Provision) (supplied : Binding) (s next : State) (expected : Cursor)
    (grant head journal image : String)
    (accepted : commit p supplied s expected .backend (.launch grant) head journal image = some next) :
    ∃ pending, s.pending = some pending ∧ pending.grant = grant ∧
      pending.ownerEpoch = some s.epoch ∧ pending.launched = false ∧
      next.pending = some { pending with launched := true } ∧ next.reserved = s.reserved := by
  obtain ⟨valid, equal⟩ := committed_spec p supplied s next expected .backend
    (.launch grant) head journal image accepted
  have allowed := valid.2.2.2.2.2.1
  cases hp : s.pending with
  | none => simp [CommandAllowed, hp] at allowed
  | some pending =>
      simp only [CommandAllowed, hp] at allowed
      refine ⟨pending, rfl, allowed.2.1, allowed.2.2.1, allowed.2.2.2, ?_, ?_⟩
      · simp only [equal, installed, bodyNext, hp, Option.map_some]
      · rw [equal]; rfl

theorem launch_not_reissued (p : Provision) (supplied : Binding) (s next : State) (expected : Cursor)
    (grant head journal image nextHead nextJournal nextImage : String)
    (accepted : commit p supplied s expected .backend (.launch grant) head journal image = some next) :
    commit p supplied next (cursor next) .backend (.launch grant) nextHead nextJournal nextImage = none := by
  obtain ⟨pending, _, _, _, _, retained, _⟩ :=
    launched_consumed p supplied s next expected grant head journal image accepted
  have invalid : ¬ Guard p supplied next (cursor next) .backend (.launch grant)
      nextHead nextJournal nextImage := by
    intro valid
    have allowed := valid.2.2.2.2.2.1
    simp only [CommandAllowed, retained] at allowed
    cases allowed.2.2.2
  simp only [commit, invalid, if_false]

theorem completed_no_refund (p : Provision) (supplied : Binding) (s next : State) (expected : Cursor)
    (grant transcript : String) (actual : Nat) (head journal image : String)
    (accepted : commit p supplied s expected .backend (.complete grant transcript actual)
      head journal image = some next) :
    next.reserved = s.reserved ∧ next.pending = none ∧
      next.completedWork = s.completedWork.add (envelope p.installed actual) := by
  rw [(committed_spec p supplied s next expected .backend (.complete grant transcript actual)
    head journal image accepted).2]
  exact ⟨rfl, rfl, rfl⟩

theorem completed_within_envelope (p : Provision) (supplied : Binding) (s next : State) (expected : Cursor)
    (grant transcript : String) (actual : Nat) (head journal image : String)
    (accepted : commit p supplied s expected .backend (.complete grant transcript actual)
      head journal image = some next) :
    ∃ pending, s.pending = some pending ∧ pending.launched = true ∧
      (envelope p.installed actual).LE (envelope p.installed pending.credits) := by
  have valid := (committed_spec p supplied s next expected .backend (.complete grant transcript actual)
    head journal image accepted).1.2.2.2.2.2.1
  cases hp : s.pending with
  | none => simp [CommandAllowed, hp] at valid
  | some pending =>
      simp only [CommandAllowed, hp] at valid
      exact ⟨pending, rfl, valid.2.2.2.1, envelope_monotone _ _ _ valid.2.2.2.2.2⟩

theorem reopened_retains_charges (p : Provision) (supplied : Binding) (s next : State) (expected : Cursor)
    (head journal image : String)
    (accepted : commit p supplied s expected .backend .reopen head journal image = some next) :
    next.epoch = s.epoch + 1 ∧ next.reserved = s.reserved ∧
      next.completedWork = s.completedWork ∧ next.sessionCount = s.sessionCount ∧
      next.pending = s.pending.map (fun pending => { pending with ownerEpoch := none }) := by
  rw [(committed_spec p supplied s next expected .backend .reopen head journal image accepted).2]
  exact ⟨rfl, rfl, rfl, rfl, rfl⟩

theorem reopened_owner_cannot_launch (p : Provision) (supplied : Binding) (s next : State) (expected : Cursor)
    (head journal image grant laterHead laterJournal laterImage : String)
    (accepted : commit p supplied s expected .backend .reopen head journal image = some next) :
    commit p supplied next (cursor next) .backend (.launch grant) laterHead laterJournal laterImage = none := by
  have pending := (reopened_retains_charges p supplied s next expected head journal image accepted).2.2.2.2
  have invalid : ¬ Guard p supplied next (cursor next) .backend (.launch grant)
      laterHead laterJournal laterImage := by
    intro valid
    have allowed := valid.2.2.2.2.2.1
    cases hp : s.pending <;> simp [CommandAllowed, pending, hp] at allowed
  simp only [commit, invalid, if_false]

theorem reopened_owner_cannot_complete (p : Provision) (supplied : Binding) (s next : State) (expected : Cursor)
    (head journal image grant transcript : String) (actual : Nat) (laterHead laterJournal laterImage : String)
    (accepted : commit p supplied s expected .backend .reopen head journal image = some next) :
    commit p supplied next (cursor next) .backend (.complete grant transcript actual)
      laterHead laterJournal laterImage = none := by
  have pending := (reopened_retains_charges p supplied s next expected head journal image accepted).2.2.2.2
  have invalid : ¬ Guard p supplied next (cursor next) .backend (.complete grant transcript actual)
      laterHead laterJournal laterImage := by
    intro valid
    have allowed := valid.2.2.2.2.2.1
    cases hp : s.pending <;> simp [CommandAllowed, pending, hp] at allowed
  simp only [commit, invalid, if_false]

def pendingUsage (p : Provision) (pending : Option Pending) : Usage :=
  match pending with
  | none => Usage.zero
  | some value => envelope p.installed value.credits

def Accounted (p : Provision) (s : State) : Prop :=
  Fits p.budget s.reserved ∧ (s.completedWork.add (pendingUsage p s.pending)).LE s.reserved

def initial (p : Provision) (head journal image : String) : State :=
  ⟨p.identity, 0, 0, head, journal, image, Usage.zero, 0, none, [], [], Usage.zero, 0, .open⟩

theorem initial_accounted (p : Provision) (head journal image : String) :
    Accounted p (initial p head journal image) := by
  simp [Accounted, initial, Fits, Usage.LE, Usage.cost, Usage.add, Usage.zero, pendingUsage]

theorem committed_accounted (p : Provision) (supplied : Binding) (s next : State) (expected : Cursor)
    (mode : Mode) (command : Command) (head journal image : String)
    (before : Accounted p s)
    (accepted : commit p supplied s expected mode command head journal image = some next) :
    Accounted p next := by
  obtain ⟨valid, equal⟩ := committed_spec p supplied s next expected mode command head journal image accepted
  have allowed := valid.2.2.2.2.2.1
  rw [equal]
  rcases before with ⟨budget, accounted⟩
  cases command with
  | reopen =>
      cases hp : s.pending <;> simpa [Accounted, installed, bodyNext, pendingUsage, hp] using
        (show Fits p.budget s.reserved ∧ (s.completedWork.add (pendingUsage p s.pending)).LE s.reserved from ⟨budget, accounted⟩)
  | reserve nonce freeze grant credits =>
      have noPending := allowed.1.2.1
      refine ⟨allowed.2, ?_⟩
      simp only [installed, bodyNext, pendingUsage]
      simp only [noPending, pendingUsage, Usage.zero, Usage.add, Nat.add_zero, Usage.LE] at accounted
      simp only [Usage.LE, Usage.add]
      omega
  | deny nonce freeze grant credits => exact ⟨budget, accounted⟩
  | launch grant =>
      cases hp : s.pending <;> simpa [Accounted, installed, bodyNext, pendingUsage, hp] using
        (show Fits p.budget s.reserved ∧ (s.completedWork.add (pendingUsage p s.pending)).LE s.reserved from ⟨budget, accounted⟩)
  | complete grant transcript actual =>
      cases hp : s.pending with
      | none => simp [CommandAllowed, hp] at allowed
      | some pending =>
          simp only [CommandAllowed, hp] at allowed
          have bound := envelope_monotone p.installed actual pending.credits allowed.2.2.2.2.2
          refine ⟨budget, ?_⟩
          simp only [installed, bodyNext, pendingUsage, Usage.zero, Usage.add, Nat.add_zero, Usage.LE]
          simp only [hp, pendingUsage, Usage.add, Usage.LE] at accounted
          unfold Usage.LE at bound
          omega

inductive Reachable (p : Provision) (head journal image : String) : State → Prop where
  | initial : Reachable p head journal image (initial p head journal image)
  | step {s next : State} (before : Reachable p head journal image s)
      (supplied : Binding) (expected : Cursor) (mode : Mode) (command : Command)
      (nextHead nextJournal nextImage : String)
      (accepted : commit p supplied s expected mode command nextHead nextJournal nextImage = some next) :
      Reachable p head journal image next

theorem reachable_accounted (p : Provision) (head journal image : String) (s : State)
    (reachable : Reachable p head journal image s) : Accounted p s := by
  induction reachable with
  | initial => exact initial_accounted p head journal image
  | @step s next prior supplied expected mode command nextHead nextJournal nextImage accepted ih =>
      exact committed_accounted p supplied s next expected mode command nextHead nextJournal nextImage ih accepted

theorem reachable_completed_and_pending_cost (p : Provision) (head journal image : String) (s : State)
    (reachable : Reachable p head journal image s) :
    s.completedWork.cost + (pendingUsage p s.pending).cost ≤ s.reserved.cost ∧
      s.reserved.cost ≤ p.budget.costLimit := by
  have accounted := reachable_accounted p head journal image s reachable
  have bound := usage_cost_monotone _ _ accounted.2
  rw [usage_add_cost] at bound
  exact ⟨bound, accounted.1.2⟩

theorem identical_root_copies_accept_identically (p : Provision) (supplied : Binding)
    (s next : State) (expected : Cursor) (mode : Mode) (command : Command) (head journal image : String)
    (accepted : commit p supplied s expected mode command head journal image = some next) :
    ∃ first second : State, first = s ∧ second = s ∧
      commit p supplied first expected mode command head journal image = some next ∧
      commit p supplied second expected mode command head journal image = some next :=
  ⟨s, s, rfl, rfl, accepted, accepted⟩

end Phase17DurableCampaign
