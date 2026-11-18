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


namespace Phase17DurableCampaignExamples
open Phase17DurableCampaign
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def packetSha256 : String := "5ff91c35e65eba43ed1df2d5141e32ad16c8b670983bfd7f4b0e793e5ea7ba20"
def provision0 : Provision := ⟨"9dce8d456d78d907611c8e4e68d4ebb5d6f025c2392d2d34b7d87dd021360ded", ⟨"10b005004da763425125d8d06be20c8595bab5629b069d0c2cf161064ea38a4e", "7d2b823c05e4e4cef7566a89d3d440dba60a6417c6a3401f1248e59f89e91567", "9a519919e2289cb5a568039b0d36f07c49570d07ccb92fca22ace408e4367c30", "fc4cf15ec370547b14fc67ae360269cea71cbc10d773536d1a77891acbe3bf7e", "90e4e1b6ac2b3cd77f59e875f75329ad866ba9a5056af6b464154e0f7b2ff68b", "905886f0cd43c49b527473eb2ddb727f40c6c11e34fab709ed2284424651b143", "phase17.inherited-projection-current-objective.v1", "runtime.v5.phase17.challenge-protocol.v1", "runtime.v5.phase17.campaign-worker.v1", "phase17n.bounded-vector-reference-work.v1"⟩, 8, ⟨⟨4, 176, 704, 704⟩, 4480⟩⟩
def state0_0 : State := ⟨"9dce8d456d78d907611c8e4e68d4ebb5d6f025c2392d2d34b7d87dd021360ded", 0, 0, "c78db769d8a7c53d63f275880999c1543e5c2e1cbc2970d14b408778842bbdf0", "4a26f04c733ed5816710ef0f121daaa043535a26fe5131544edacf78549c13ee", "b539792c01fd0cad1fc56e69e608506dc0b08f06682748b9d54d14f60800037e", ⟨0, 0, 0, 0⟩, 0, none, [], [], ⟨0, 0, 0, 0⟩, 0, .open⟩
theorem initial0 : state0_0 = initial provision0 state0_0.head state0_0.journal state0_0.image := rfl
theorem reachable0_0 : Reachable provision0 state0_0.head state0_0.journal state0_0.image state0_0 := by
  exact .initial
def state0_1 : State := ⟨"9dce8d456d78d907611c8e4e68d4ebb5d6f025c2392d2d34b7d87dd021360ded", 1, 1, "d944d1f75474f277f85e080e3215fb376b1672567eb7d4dc617df42a66d10d10", "4a26f04c733ed5816710ef0f121daaa043535a26fe5131544edacf78549c13ee", "b539792c01fd0cad1fc56e69e608506dc0b08f06682748b9d54d14f60800037e", ⟨0, 0, 0, 0⟩, 0, none, [], [], ⟨0, 0, 0, 0⟩, 0, .open⟩
def command0_1 : Command := .reopen
theorem step0_1 : commit provision0 provision0.binding state0_0 (cursor state0_0) .backend command0_1 state0_1.head state0_1.journal state0_1.image = some state0_1 := by decide +kernel
theorem reachable0_1 : Reachable provision0 state0_0.head state0_0.journal state0_0.image state0_1 :=
  .step reachable0_0 provision0.binding (cursor state0_0) .backend command0_1 state0_1.head state0_1.journal state0_1.image step0_1
def state0_2 : State := ⟨"9dce8d456d78d907611c8e4e68d4ebb5d6f025c2392d2d34b7d87dd021360ded", 1, 2, "c2680247b7eed28974c1a592e4558ec199715414b47ca38ca414238a5aebd894", "96e872b1aea9c1f6dda58ae1fa1ba0ce35c5ccb0cd4c7feacf3ee52b22439474", "15fe7a678adb10ef938701d2efd6492243f51f76ff5fc2022255ac21fdb7cf27", ⟨2, 88, 352, 352⟩, 1, some ⟨"8b5fe6b68dea419b3a17f852ec0bf3174ffb97f2aef320f112b064a6fc5c2752", "8d365613a2928814088ade2013bf5d4c7f61b606f31c240dfce58e3fb6af61bf", 2, 1, some 1, false⟩, ["b4a2b8a8eac06ff163878f5636e8d504eb0dc7680b4a98009c690833e4579c40"], ["8d365613a2928814088ade2013bf5d4c7f61b606f31c240dfce58e3fb6af61bf"], ⟨0, 0, 0, 0⟩, 0, .pending⟩
def command0_2 : Command := .reserve "b4a2b8a8eac06ff163878f5636e8d504eb0dc7680b4a98009c690833e4579c40" "8d365613a2928814088ade2013bf5d4c7f61b606f31c240dfce58e3fb6af61bf" "8b5fe6b68dea419b3a17f852ec0bf3174ffb97f2aef320f112b064a6fc5c2752" 2
theorem step0_2 : commit provision0 provision0.binding state0_1 (cursor state0_1) .request command0_2 state0_2.head state0_2.journal state0_2.image = some state0_2 := by decide +kernel
theorem reachable0_2 : Reachable provision0 state0_0.head state0_0.journal state0_0.image state0_2 :=
  .step reachable0_1 provision0.binding (cursor state0_1) .request command0_2 state0_2.head state0_2.journal state0_2.image step0_2
def state0_3 : State := ⟨"9dce8d456d78d907611c8e4e68d4ebb5d6f025c2392d2d34b7d87dd021360ded", 1, 3, "f87d908aba0b47a66461b998b927365ba1904809314694f125d29807d7446365", "96e872b1aea9c1f6dda58ae1fa1ba0ce35c5ccb0cd4c7feacf3ee52b22439474", "a5a6fb6ade8a2502f1208efd5a910985ed96b694a6f48629d7da94aeabe9dacd", ⟨2, 88, 352, 352⟩, 1, some ⟨"8b5fe6b68dea419b3a17f852ec0bf3174ffb97f2aef320f112b064a6fc5c2752", "8d365613a2928814088ade2013bf5d4c7f61b606f31c240dfce58e3fb6af61bf", 2, 1, some 1, true⟩, ["b4a2b8a8eac06ff163878f5636e8d504eb0dc7680b4a98009c690833e4579c40"], ["8d365613a2928814088ade2013bf5d4c7f61b606f31c240dfce58e3fb6af61bf"], ⟨0, 0, 0, 0⟩, 0, .pending⟩
def command0_3 : Command := .launch "8b5fe6b68dea419b3a17f852ec0bf3174ffb97f2aef320f112b064a6fc5c2752"
theorem step0_3 : commit provision0 provision0.binding state0_2 (cursor state0_2) .backend command0_3 state0_3.head state0_3.journal state0_3.image = some state0_3 := by decide +kernel
theorem reachable0_3 : Reachable provision0 state0_0.head state0_0.journal state0_0.image state0_3 :=
  .step reachable0_2 provision0.binding (cursor state0_2) .backend command0_3 state0_3.head state0_3.journal state0_3.image step0_3
def state0_4 : State := ⟨"9dce8d456d78d907611c8e4e68d4ebb5d6f025c2392d2d34b7d87dd021360ded", 1, 4, "6bbbc914337dd63d83969988149c3b5bc1c7ba67453ddf44d676799023ff2cad", "399f39884f1153870aa5fc1c3113b1eab809de3fa680a2f6fa3b1d3eab82bfca", "acabaf3e6075c837bfe1515a1629a9047f8e8b927ec7c79bdc46dc7f565ce632", ⟨2, 88, 352, 352⟩, 1, none, ["b4a2b8a8eac06ff163878f5636e8d504eb0dc7680b4a98009c690833e4579c40"], ["8d365613a2928814088ade2013bf5d4c7f61b606f31c240dfce58e3fb6af61bf"], ⟨2, 88, 352, 352⟩, 1, .open⟩
def command0_4 : Command := .complete "8b5fe6b68dea419b3a17f852ec0bf3174ffb97f2aef320f112b064a6fc5c2752" "5a6f6334eac719e2211e2b1b636a43013e51a7fdfa072b7398970b1642308e4f" 2
theorem step0_4 : commit provision0 provision0.binding state0_3 (cursor state0_3) .backend command0_4 state0_4.head state0_4.journal state0_4.image = some state0_4 := by decide +kernel
theorem reachable0_4 : Reachable provision0 state0_0.head state0_0.journal state0_0.image state0_4 :=
  .step reachable0_3 provision0.binding (cursor state0_3) .backend command0_4 state0_4.head state0_4.journal state0_4.image step0_4
def state0_5 : State := ⟨"9dce8d456d78d907611c8e4e68d4ebb5d6f025c2392d2d34b7d87dd021360ded", 2, 5, "ea727c30360c5f6c62bf3160ce072d261ea718381f67d1c9e1837f607c9b393f", "399f39884f1153870aa5fc1c3113b1eab809de3fa680a2f6fa3b1d3eab82bfca", "acabaf3e6075c837bfe1515a1629a9047f8e8b927ec7c79bdc46dc7f565ce632", ⟨2, 88, 352, 352⟩, 1, none, ["b4a2b8a8eac06ff163878f5636e8d504eb0dc7680b4a98009c690833e4579c40"], ["8d365613a2928814088ade2013bf5d4c7f61b606f31c240dfce58e3fb6af61bf"], ⟨2, 88, 352, 352⟩, 1, .open⟩
def command0_5 : Command := .reopen
theorem step0_5 : commit provision0 provision0.binding state0_4 (cursor state0_4) .backend command0_5 state0_5.head state0_5.journal state0_5.image = some state0_5 := by decide +kernel
theorem reachable0_5 : Reachable provision0 state0_0.head state0_0.journal state0_0.image state0_5 :=
  .step reachable0_4 provision0.binding (cursor state0_4) .backend command0_5 state0_5.head state0_5.journal state0_5.image step0_5
def state0_6 : State := ⟨"9dce8d456d78d907611c8e4e68d4ebb5d6f025c2392d2d34b7d87dd021360ded", 2, 6, "a0b8791a2c1c27c2154fd537f0a7c31c7f6815d7465e6b392eeff3426c09fabd", "bea2f8b00b4818e567918e456ba40926e6f9c040602a07e0be995ad4c5265cdb", "c402428372ef5f4f6697db3e3f5518bff8b741bc49d0d8e7f71411b9109827cc", ⟨4, 176, 704, 704⟩, 2, some ⟨"d7cc3c8f40b4bd5a4cef41e77a54ca259baa815e679fb550423e2c824aa0ce6c", "5100ab2f6f516eba80101c75d23363c09dc78aa8ac5234efc030433e26f47827", 2, 2, some 2, false⟩, ["b4a2b8a8eac06ff163878f5636e8d504eb0dc7680b4a98009c690833e4579c40", "5ec67ac0595c0170a6178866f406c8f9c71f521520a10ba0e02a716982cbb8ff"], ["8d365613a2928814088ade2013bf5d4c7f61b606f31c240dfce58e3fb6af61bf", "5100ab2f6f516eba80101c75d23363c09dc78aa8ac5234efc030433e26f47827"], ⟨2, 88, 352, 352⟩, 1, .pending⟩
def command0_6 : Command := .reserve "5ec67ac0595c0170a6178866f406c8f9c71f521520a10ba0e02a716982cbb8ff" "5100ab2f6f516eba80101c75d23363c09dc78aa8ac5234efc030433e26f47827" "d7cc3c8f40b4bd5a4cef41e77a54ca259baa815e679fb550423e2c824aa0ce6c" 2
theorem step0_6 : commit provision0 provision0.binding state0_5 (cursor state0_5) .request command0_6 state0_6.head state0_6.journal state0_6.image = some state0_6 := by decide +kernel
theorem reachable0_6 : Reachable provision0 state0_0.head state0_0.journal state0_0.image state0_6 :=
  .step reachable0_5 provision0.binding (cursor state0_5) .request command0_6 state0_6.head state0_6.journal state0_6.image step0_6
def state0_7 : State := ⟨"9dce8d456d78d907611c8e4e68d4ebb5d6f025c2392d2d34b7d87dd021360ded", 2, 7, "036ba16d5b0b05f4ffc713493e8145e9081e6fb8d07c0a1a545ab9e31eb12391", "bea2f8b00b4818e567918e456ba40926e6f9c040602a07e0be995ad4c5265cdb", "b1b7c6c613557cf46f28489b51ab3e691a3d00851e67c24f05ae352ab5a71b0e", ⟨4, 176, 704, 704⟩, 2, some ⟨"d7cc3c8f40b4bd5a4cef41e77a54ca259baa815e679fb550423e2c824aa0ce6c", "5100ab2f6f516eba80101c75d23363c09dc78aa8ac5234efc030433e26f47827", 2, 2, some 2, true⟩, ["b4a2b8a8eac06ff163878f5636e8d504eb0dc7680b4a98009c690833e4579c40", "5ec67ac0595c0170a6178866f406c8f9c71f521520a10ba0e02a716982cbb8ff"], ["8d365613a2928814088ade2013bf5d4c7f61b606f31c240dfce58e3fb6af61bf", "5100ab2f6f516eba80101c75d23363c09dc78aa8ac5234efc030433e26f47827"], ⟨2, 88, 352, 352⟩, 1, .pending⟩
def command0_7 : Command := .launch "d7cc3c8f40b4bd5a4cef41e77a54ca259baa815e679fb550423e2c824aa0ce6c"
theorem step0_7 : commit provision0 provision0.binding state0_6 (cursor state0_6) .backend command0_7 state0_7.head state0_7.journal state0_7.image = some state0_7 := by decide +kernel
theorem reachable0_7 : Reachable provision0 state0_0.head state0_0.journal state0_0.image state0_7 :=
  .step reachable0_6 provision0.binding (cursor state0_6) .backend command0_7 state0_7.head state0_7.journal state0_7.image step0_7
def state0_8 : State := ⟨"9dce8d456d78d907611c8e4e68d4ebb5d6f025c2392d2d34b7d87dd021360ded", 2, 8, "ac3278a3b010fce80897c8bb960e36849b7fb04f3ea6bb7df6aba53678b3384b", "eb2b92b933e57bb615454c6d11e017fdc31f262f01c57f781c0aadd71ebc1143", "66d2f2bffec71ec260f1bbeaefa732f1c3bae902e12ed27e584eabfc2ed24233", ⟨4, 176, 704, 704⟩, 2, none, ["b4a2b8a8eac06ff163878f5636e8d504eb0dc7680b4a98009c690833e4579c40", "5ec67ac0595c0170a6178866f406c8f9c71f521520a10ba0e02a716982cbb8ff"], ["8d365613a2928814088ade2013bf5d4c7f61b606f31c240dfce58e3fb6af61bf", "5100ab2f6f516eba80101c75d23363c09dc78aa8ac5234efc030433e26f47827"], ⟨4, 176, 704, 704⟩, 2, .open⟩
def command0_8 : Command := .complete "d7cc3c8f40b4bd5a4cef41e77a54ca259baa815e679fb550423e2c824aa0ce6c" "e05d3039bffb6c5ca239395a947eeedaa8bf766a4b533e9f004e34b652d0cb85" 2
theorem step0_8 : commit provision0 provision0.binding state0_7 (cursor state0_7) .backend command0_8 state0_8.head state0_8.journal state0_8.image = some state0_8 := by decide +kernel
theorem reachable0_8 : Reachable provision0 state0_0.head state0_0.journal state0_0.image state0_8 :=
  .step reachable0_7 provision0.binding (cursor state0_7) .backend command0_8 state0_8.head state0_8.journal state0_8.image step0_8
def provision1 : Provision := ⟨"f39c7ceb05563717215f4611d40d527db4ae929a6ce3f473a9f092606faeee26", ⟨"ad8d1687f9c78251a73d226f0120bfae1e33ad6c4b0cf4e506610d1c57220d09", "7d2b823c05e4e4cef7566a89d3d440dba60a6417c6a3401f1248e59f89e91567", "9a519919e2289cb5a568039b0d36f07c49570d07ccb92fca22ace408e4367c30", "fc4cf15ec370547b14fc67ae360269cea71cbc10d773536d1a77891acbe3bf7e", "b0f604fb001e045aeaee5eac7d15599135436c65344cb311aed5bccca3dd3e4b", "905886f0cd43c49b527473eb2ddb727f40c6c11e34fab709ed2284424651b143", "phase17.inherited-projection-current-objective.v1", "runtime.v5.phase17.challenge-protocol.v1", "runtime.v5.phase17.campaign-worker.v1", "phase17n.bounded-vector-reference-work.v1"⟩, 8, ⟨⟨2, 88, 352, 352⟩, 2240⟩⟩
def state1_0 : State := ⟨"f39c7ceb05563717215f4611d40d527db4ae929a6ce3f473a9f092606faeee26", 0, 0, "a7b99768ffbcd8fcd0c823f421ca076a3d44d5d53ac438989d3aa59f90aeff60", "32e571c5575fb6f113952b4e4b554f79e368bc32429fce2b89c9c25dd44e5e59", "716ea0a6f02eb461e9268ce203b166744240393d8bbac4ce774cba2135f3d46d", ⟨0, 0, 0, 0⟩, 0, none, [], [], ⟨0, 0, 0, 0⟩, 0, .open⟩
theorem initial1 : state1_0 = initial provision1 state1_0.head state1_0.journal state1_0.image := rfl
theorem reachable1_0 : Reachable provision1 state1_0.head state1_0.journal state1_0.image state1_0 := by
  exact .initial
def state1_1 : State := ⟨"f39c7ceb05563717215f4611d40d527db4ae929a6ce3f473a9f092606faeee26", 1, 1, "174788340abc6abc025a3dd902e9041b5b3f7ca207a94d294f23dc74801b83c8", "32e571c5575fb6f113952b4e4b554f79e368bc32429fce2b89c9c25dd44e5e59", "716ea0a6f02eb461e9268ce203b166744240393d8bbac4ce774cba2135f3d46d", ⟨0, 0, 0, 0⟩, 0, none, [], [], ⟨0, 0, 0, 0⟩, 0, .open⟩
def command1_1 : Command := .reopen
theorem step1_1 : commit provision1 provision1.binding state1_0 (cursor state1_0) .backend command1_1 state1_1.head state1_1.journal state1_1.image = some state1_1 := by decide +kernel
theorem reachable1_1 : Reachable provision1 state1_0.head state1_0.journal state1_0.image state1_1 :=
  .step reachable1_0 provision1.binding (cursor state1_0) .backend command1_1 state1_1.head state1_1.journal state1_1.image step1_1
def state1_2 : State := ⟨"f39c7ceb05563717215f4611d40d527db4ae929a6ce3f473a9f092606faeee26", 1, 2, "76b8cfa7ad04a699a0a24b194901864a388f0f7455834ed91974b92d17f93b40", "3b5765d7523c575895714dbd8466484e796464590d256ab4cd818e795b064fdb", "b7e9294bf8e3df4529b7747a69b3dc1ce9557241086e14995d0719389c0f7a53", ⟨2, 88, 352, 352⟩, 1, some ⟨"35514e24b5f994752e7ab69d4cb82f6020fe2bd4029e82b62f12d1e1e8e1c6fd", "678784a460caa043036a72ae0f8f0d316d96bcd2a6d511b5c5e4148d25818315", 2, 1, some 1, false⟩, ["2797a491af4bed95f15b87b8629cb91603a038b4d531c01d8f3a42900bc48a5e"], ["678784a460caa043036a72ae0f8f0d316d96bcd2a6d511b5c5e4148d25818315"], ⟨0, 0, 0, 0⟩, 0, .pending⟩
def command1_2 : Command := .reserve "2797a491af4bed95f15b87b8629cb91603a038b4d531c01d8f3a42900bc48a5e" "678784a460caa043036a72ae0f8f0d316d96bcd2a6d511b5c5e4148d25818315" "35514e24b5f994752e7ab69d4cb82f6020fe2bd4029e82b62f12d1e1e8e1c6fd" 2
theorem step1_2 : commit provision1 provision1.binding state1_1 (cursor state1_1) .request command1_2 state1_2.head state1_2.journal state1_2.image = some state1_2 := by decide +kernel
theorem reachable1_2 : Reachable provision1 state1_0.head state1_0.journal state1_0.image state1_2 :=
  .step reachable1_1 provision1.binding (cursor state1_1) .request command1_2 state1_2.head state1_2.journal state1_2.image step1_2
def state1_3 : State := ⟨"f39c7ceb05563717215f4611d40d527db4ae929a6ce3f473a9f092606faeee26", 2, 3, "91a2a743b91d16ab44c05ced7d1ff588f84665217f69a9b5bbcf3d6dd9179bfd", "3b5765d7523c575895714dbd8466484e796464590d256ab4cd818e795b064fdb", "0dde4f0f6ce2fb20374c153df7345a730aadb5aff3af46c6dab5307d675e71b8", ⟨2, 88, 352, 352⟩, 1, some ⟨"35514e24b5f994752e7ab69d4cb82f6020fe2bd4029e82b62f12d1e1e8e1c6fd", "678784a460caa043036a72ae0f8f0d316d96bcd2a6d511b5c5e4148d25818315", 2, 1, none, false⟩, ["2797a491af4bed95f15b87b8629cb91603a038b4d531c01d8f3a42900bc48a5e"], ["678784a460caa043036a72ae0f8f0d316d96bcd2a6d511b5c5e4148d25818315"], ⟨0, 0, 0, 0⟩, 0, .pending⟩
def command1_3 : Command := .reopen
theorem step1_3 : commit provision1 provision1.binding state1_2 (cursor state1_2) .backend command1_3 state1_3.head state1_3.journal state1_3.image = some state1_3 := by decide +kernel
theorem reachable1_3 : Reachable provision1 state1_0.head state1_0.journal state1_0.image state1_3 :=
  .step reachable1_2 provision1.binding (cursor state1_2) .backend command1_3 state1_3.head state1_3.journal state1_3.image step1_3
def provision2 : Provision := ⟨"c2e344c4a9611b7a6e7789c9bc1a2ac0902e4415f7bb59ab98afa3bc1c548d75", ⟨"1013e4727e5926a115333148706ccf089de8845543f9d012983ed5d21e9641b6", "7d2b823c05e4e4cef7566a89d3d440dba60a6417c6a3401f1248e59f89e91567", "9a519919e2289cb5a568039b0d36f07c49570d07ccb92fca22ace408e4367c30", "fc4cf15ec370547b14fc67ae360269cea71cbc10d773536d1a77891acbe3bf7e", "b0f604fb001e045aeaee5eac7d15599135436c65344cb311aed5bccca3dd3e4b", "905886f0cd43c49b527473eb2ddb727f40c6c11e34fab709ed2284424651b143", "phase17.inherited-projection-current-objective.v1", "runtime.v5.phase17.challenge-protocol.v1", "runtime.v5.phase17.campaign-worker.v1", "phase17n.bounded-vector-reference-work.v1"⟩, 8, ⟨⟨2, 88, 352, 352⟩, 2240⟩⟩
def state2_0 : State := ⟨"c2e344c4a9611b7a6e7789c9bc1a2ac0902e4415f7bb59ab98afa3bc1c548d75", 0, 0, "0345dde2b3bba3443562245f5441482ca8b0d11693290288f1d77dcadb6b40fb", "dc464cbe193a063d06068d2bdaeb2d6c09f5b180b70f114d715ce2ef9b8172db", "fcc1cecb6c4a37486f489bbfad2f22148fbc32a05401a78f7788951d924de689", ⟨0, 0, 0, 0⟩, 0, none, [], [], ⟨0, 0, 0, 0⟩, 0, .open⟩
theorem initial2 : state2_0 = initial provision2 state2_0.head state2_0.journal state2_0.image := rfl
theorem reachable2_0 : Reachable provision2 state2_0.head state2_0.journal state2_0.image state2_0 := by
  exact .initial
def state2_1 : State := ⟨"c2e344c4a9611b7a6e7789c9bc1a2ac0902e4415f7bb59ab98afa3bc1c548d75", 1, 1, "896d520c5829255c17f5f4e7e6a067ad4615a4ddb24454d19c15d0c02e35eac6", "dc464cbe193a063d06068d2bdaeb2d6c09f5b180b70f114d715ce2ef9b8172db", "fcc1cecb6c4a37486f489bbfad2f22148fbc32a05401a78f7788951d924de689", ⟨0, 0, 0, 0⟩, 0, none, [], [], ⟨0, 0, 0, 0⟩, 0, .open⟩
def command2_1 : Command := .reopen
theorem step2_1 : commit provision2 provision2.binding state2_0 (cursor state2_0) .backend command2_1 state2_1.head state2_1.journal state2_1.image = some state2_1 := by decide +kernel
theorem reachable2_1 : Reachable provision2 state2_0.head state2_0.journal state2_0.image state2_1 :=
  .step reachable2_0 provision2.binding (cursor state2_0) .backend command2_1 state2_1.head state2_1.journal state2_1.image step2_1
def state2_2 : State := ⟨"c2e344c4a9611b7a6e7789c9bc1a2ac0902e4415f7bb59ab98afa3bc1c548d75", 1, 2, "1b01a941139912fda555b0f2d65040fd87e5f73f68472f622ad4b510437b5cc5", "2861bdda696b4ff64b20f89d33b13fd077a5bafb3ee1cb3fa2cb864058357f94", "20d7a95bc12c7b520aec2e04519da12a546e7e23c69f9a6a8593abb0b7044efe", ⟨2, 88, 352, 352⟩, 1, some ⟨"21c923736c0660c8c3d79790ffc7b9145cd6aac8db82442f896d02c6e4b0b6a9", "4a3e815eaddbf0f05c35701a669e567ac851f4a582ee651de9bab5c30e8adb5c", 2, 1, some 1, false⟩, ["532984d59743e9d208d78cd7347a1c366e550c4c0bd82ac3cb2e4c40badc3ea2"], ["4a3e815eaddbf0f05c35701a669e567ac851f4a582ee651de9bab5c30e8adb5c"], ⟨0, 0, 0, 0⟩, 0, .pending⟩
def command2_2 : Command := .reserve "532984d59743e9d208d78cd7347a1c366e550c4c0bd82ac3cb2e4c40badc3ea2" "4a3e815eaddbf0f05c35701a669e567ac851f4a582ee651de9bab5c30e8adb5c" "21c923736c0660c8c3d79790ffc7b9145cd6aac8db82442f896d02c6e4b0b6a9" 2
theorem step2_2 : commit provision2 provision2.binding state2_1 (cursor state2_1) .request command2_2 state2_2.head state2_2.journal state2_2.image = some state2_2 := by decide +kernel
theorem reachable2_2 : Reachable provision2 state2_0.head state2_0.journal state2_0.image state2_2 :=
  .step reachable2_1 provision2.binding (cursor state2_1) .request command2_2 state2_2.head state2_2.journal state2_2.image step2_2
def state2_3 : State := ⟨"c2e344c4a9611b7a6e7789c9bc1a2ac0902e4415f7bb59ab98afa3bc1c548d75", 1, 3, "a5fc3e83bc4ea9f81c0699788ed131ece446994e6484b984b1d31914fae1d8f6", "2861bdda696b4ff64b20f89d33b13fd077a5bafb3ee1cb3fa2cb864058357f94", "9f1e68762a1c5e6b8b1b7eec18e9ada5f81586571ca7200a7a9cf22bbbff1753", ⟨2, 88, 352, 352⟩, 1, some ⟨"21c923736c0660c8c3d79790ffc7b9145cd6aac8db82442f896d02c6e4b0b6a9", "4a3e815eaddbf0f05c35701a669e567ac851f4a582ee651de9bab5c30e8adb5c", 2, 1, some 1, true⟩, ["532984d59743e9d208d78cd7347a1c366e550c4c0bd82ac3cb2e4c40badc3ea2"], ["4a3e815eaddbf0f05c35701a669e567ac851f4a582ee651de9bab5c30e8adb5c"], ⟨0, 0, 0, 0⟩, 0, .pending⟩
def command2_3 : Command := .launch "21c923736c0660c8c3d79790ffc7b9145cd6aac8db82442f896d02c6e4b0b6a9"
theorem step2_3 : commit provision2 provision2.binding state2_2 (cursor state2_2) .backend command2_3 state2_3.head state2_3.journal state2_3.image = some state2_3 := by decide +kernel
theorem reachable2_3 : Reachable provision2 state2_0.head state2_0.journal state2_0.image state2_3 :=
  .step reachable2_2 provision2.binding (cursor state2_2) .backend command2_3 state2_3.head state2_3.journal state2_3.image step2_3
def state2_4 : State := ⟨"c2e344c4a9611b7a6e7789c9bc1a2ac0902e4415f7bb59ab98afa3bc1c548d75", 1, 4, "6e47f35a9322775710c79b0640d657e053c1ea43da3cb4f5d7507aba25262619", "2713b4273718569be4f931b72d216acd78638385c1a1cd19893816f87790d04c", "a2e9371b888dc820112cdcf5dbee50c5b519cfef3fbde0f1eb5bab78412bc3dd", ⟨2, 88, 352, 352⟩, 1, none, ["532984d59743e9d208d78cd7347a1c366e550c4c0bd82ac3cb2e4c40badc3ea2"], ["4a3e815eaddbf0f05c35701a669e567ac851f4a582ee651de9bab5c30e8adb5c"], ⟨2, 88, 352, 352⟩, 1, .open⟩
def command2_4 : Command := .complete "21c923736c0660c8c3d79790ffc7b9145cd6aac8db82442f896d02c6e4b0b6a9" "913708076bc6281c88e3ad035087938e2ebc0926cb56420ce3cbb516d24456b6" 2
theorem step2_4 : commit provision2 provision2.binding state2_3 (cursor state2_3) .backend command2_4 state2_4.head state2_4.journal state2_4.image = some state2_4 := by decide +kernel
theorem reachable2_4 : Reachable provision2 state2_0.head state2_0.journal state2_0.image state2_4 :=
  .step reachable2_3 provision2.binding (cursor state2_3) .backend command2_4 state2_4.head state2_4.journal state2_4.image step2_4
def state2_5 : State := ⟨"c2e344c4a9611b7a6e7789c9bc1a2ac0902e4415f7bb59ab98afa3bc1c548d75", 1, 5, "a22575d8c89fe40349659a167e991c707fde8d5fdf1cbdf3ace557a4a17a0a95", "4af5ed9f8427d5cbcc599bbb64c1817c590ed631cad1973a2ab82f7b647bbb2e", "b6a19e0487826d0130dec20e792b38f466739af182504ae2e53defb3c2f22b8d", ⟨2, 88, 352, 352⟩, 1, none, ["532984d59743e9d208d78cd7347a1c366e550c4c0bd82ac3cb2e4c40badc3ea2", "a0b3a1d7dca0e45486b13eeeec34e5fbbea203ee1c117740368c8d8025ab02ea"], ["4a3e815eaddbf0f05c35701a669e567ac851f4a582ee651de9bab5c30e8adb5c"], ⟨2, 88, 352, 352⟩, 1, .denied⟩
def command2_5 : Command := .deny "a0b3a1d7dca0e45486b13eeeec34e5fbbea203ee1c117740368c8d8025ab02ea" "9cb5ec2c6e24bcc94ba0de0d653680d307ffef24c39a8065e3feb56cc40ff283" "2deebbb13c6140ab092c8b3227db5cb6f98047a47dc33434cbc99f35b0c39182" 2
theorem step2_5 : commit provision2 provision2.binding state2_4 (cursor state2_4) .request command2_5 state2_5.head state2_5.journal state2_5.image = some state2_5 := by decide +kernel
theorem reachable2_5 : Reachable provision2 state2_0.head state2_0.journal state2_0.image state2_5 :=
  .step reachable2_4 provision2.binding (cursor state2_4) .request command2_5 state2_5.head state2_5.journal state2_5.image step2_5
def mainFinal : State := state0_8
theorem main_reachable : Reachable provision0 state0_0.head state0_0.journal state0_0.image mainFinal := reachable0_8
def interruptedFinal : State := state1_3
theorem interrupted_reachable : Reachable provision1 state1_0.head state1_0.journal state1_0.image interruptedFinal := reachable1_3
def denialFinal : State := state2_5
theorem denial_reachable : Reachable provision2 state2_0.head state2_0.journal state2_0.image denialFinal := reachable2_5
def firstBeforeReserve : State := state0_1
def firstReserved : State := state0_2
def firstBeforeLaunch : State := state0_2
def firstLaunched : State := state0_3
def interruptedReserved : State := state1_2
def beforeDenial : State := state2_4
def afterDenial : State := state2_5
def firstNonce : String := "b4a2b8a8eac06ff163878f5636e8d504eb0dc7680b4a98009c690833e4579c40"
def firstFreeze : String := "8d365613a2928814088ade2013bf5d4c7f61b606f31c240dfce58e3fb6af61bf"
def firstGrant : String := "8b5fe6b68dea419b3a17f852ec0bf3174ffb97f2aef320f112b064a6fc5c2752"
def interruptedGrant : String := "35514e24b5f994752e7ab69d4cb82f6020fe2bd4029e82b62f12d1e1e8e1c6fd"
def firstCredits : Nat := 2
def firstReservation : Command := .reserve firstNonce firstFreeze firstGrant firstCredits
theorem firstReservationStep : commit provision0 provision0.binding firstBeforeReserve (cursor firstBeforeReserve) .request firstReservation firstReserved.head firstReserved.journal firstReserved.image = some firstReserved := step0_2
theorem firstLaunchStep : commit provision0 provision0.binding firstBeforeLaunch (cursor firstBeforeLaunch) .backend (.launch firstGrant) firstLaunched.head firstLaunched.journal firstLaunched.image = some firstLaunched := step0_3
theorem main_completed_pending_accounted :
    mainFinal.completedWork.cost + (pendingUsage provision0 mainFinal.pending).cost ≤ mainFinal.reserved.cost ∧
      mainFinal.reserved.cost ≤ provision0.budget.costLimit :=
  reachable_completed_and_pending_cost provision0 state0_0.head state0_0.journal state0_0.image mainFinal main_reachable
theorem main_exact_declared_work : mainFinal.completedWork = ⟨4, 176, 704, 704⟩ ∧ mainFinal.completedCount = 2 := by decide +kernel
theorem interrupted_charge_retained : interruptedFinal.reserved = interruptedReserved.reserved ∧
    0 < interruptedFinal.reserved.cost := by decide +kernel
theorem interrupted_owner_revoked : interruptedFinal.pending.map Pending.ownerEpoch = some none := by decide +kernel
theorem first_launch_consumed :
    ∃ pending, firstBeforeLaunch.pending = some pending ∧ pending.grant = firstGrant ∧
      pending.ownerEpoch = some firstBeforeLaunch.epoch ∧ pending.launched = false ∧
      firstLaunched.pending = some { pending with launched := true } ∧
      firstLaunched.reserved = firstBeforeLaunch.reserved :=
  launched_consumed provision0 provision0.binding firstBeforeLaunch firstLaunched (cursor firstBeforeLaunch)
    firstGrant firstLaunched.head firstLaunched.journal firstLaunched.image firstLaunchStep
theorem first_launch_cannot_repeat :
    commit provision0 provision0.binding firstLaunched (cursor firstLaunched) .backend (.launch firstGrant)
      "new-head" firstLaunched.journal "new-image" = none :=
  launch_not_reissued provision0 provision0.binding firstBeforeLaunch firstLaunched (cursor firstBeforeLaunch)
    firstGrant firstLaunched.head firstLaunched.journal firstLaunched.image
    "new-head" firstLaunched.journal "new-image" firstLaunchStep
theorem aggregate_denial_no_new_charge : afterDenial.reserved = beforeDenial.reserved ∧ afterDenial.sessionCount = beforeDenial.sessionCount ∧
    ¬ Fits provision2.budget (beforeDenial.reserved.add (envelope provision2.installed 2)) :=
  denied_no_reservation provision2 provision2.binding beforeDenial afterDenial (cursor beforeDenial) "a0b3a1d7dca0e45486b13eeeec34e5fbbea203ee1c117740368c8d8025ab02ea" "9cb5ec2c6e24bcc94ba0de0d653680d307ffef24c39a8065e3feb56cc40ff283" "2deebbb13c6140ab092c8b3227db5cb6f98047a47dc33434cbc99f35b0c39182" 2 afterDenial.head afterDenial.journal afterDenial.image step2_5
theorem root_copy_outside_guarantee :
    ∃ first second : State, first = firstBeforeReserve ∧ second = firstBeforeReserve ∧
      commit provision0 provision0.binding first (cursor firstBeforeReserve) .request firstReservation
        firstReserved.head firstReserved.journal firstReserved.image = some firstReserved ∧
      commit provision0 provision0.binding second (cursor firstBeforeReserve) .request firstReservation
        firstReserved.head firstReserved.journal firstReserved.image = some firstReserved :=
  identical_root_copies_accept_identically provision0 provision0.binding firstBeforeReserve firstReserved
    (cursor firstBeforeReserve) .request firstReservation firstReserved.head firstReserved.journal
    firstReserved.image firstReservationStep
end Phase17DurableCampaignExamples
