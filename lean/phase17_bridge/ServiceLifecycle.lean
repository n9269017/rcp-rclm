import Std
import Lean.Elab.Tactic.Omega

/- Phase 17AO: a prepaid service-lifetime ledger. The six coordinates below are
   declared operational quantities, not physical time, energy or complete cost.
   Each selected value is reconstructed from the actual ledger and native
   service records. Source authentication, file transactions, OS protection,
   physical currentness, a single authoritative history and native sequencing
   remain separate implementation premises. This model cannot create root
   acceptance or forbid a second physical copy of its entire state. -/
namespace Phase17ServiceLifecycle

structure Usage where
  serviceLifetimes : Nat
  processLaunchAttempts : Nat
  frontendInputAttempts : Nat
  requestBytes : Nat
  responseBytes : Nat
  authorityTlsConnections : Nat
  deriving DecidableEq

def Usage.zero : Usage := ⟨0, 0, 0, 0, 0, 0⟩
def Usage.add (a b : Usage) : Usage :=
  ⟨a.serviceLifetimes + b.serviceLifetimes,
   a.processLaunchAttempts + b.processLaunchAttempts,
   a.frontendInputAttempts + b.frontendInputAttempts,
   a.requestBytes + b.requestBytes, a.responseBytes + b.responseBytes,
   a.authorityTlsConnections + b.authorityTlsConnections⟩
def Usage.LE (a b : Usage) : Prop :=
  a.serviceLifetimes ≤ b.serviceLifetimes ∧
  a.processLaunchAttempts ≤ b.processLaunchAttempts ∧
  a.frontendInputAttempts ≤ b.frontendInputAttempts ∧
  a.requestBytes ≤ b.requestBytes ∧ a.responseBytes ≤ b.responseBytes ∧
  a.authorityTlsConnections ≤ b.authorityTlsConnections

instance (a b : Usage) : Decidable (a.LE b) := by unfold Usage.LE; infer_instance

theorem usage_reflexive (a : Usage) : a.LE a := by
  unfold Usage.LE
  exact ⟨Nat.le_refl _, Nat.le_refl _, Nat.le_refl _, Nat.le_refl _, Nat.le_refl _, Nat.le_refl _⟩

theorem usage_not_refunded (a b : Usage) : a.LE (a.add b) := by
  simp only [Usage.LE, Usage.add]
  omega

theorem usage_zero_bounded (a : Usage) : Usage.zero.LE a := by
  simp only [Usage.LE, Usage.zero]
  omega

def launchUsage : Usage := ⟨1, 1, 0, 0, 0, 0⟩

structure Commission where
  identity : String
  source : String
  envelope : Usage
  budget : Usage
  deriving DecidableEq

structure Runtime where
  source : String
  owner : String
  deriving DecidableEq

structure Cursor where
  commission : String
  epoch : Nat
  serial : Nat
  head : String
  deriving DecidableEq

structure Grant where
  identity : String
  commission : String
  lifetimeId : String
  owner : String
  epoch : Nat
  envelope : Usage
  reservationCursor : Cursor
  deriving DecidableEq

structure Pending where
  grant : Grant
  launched : Bool
  used : Usage
  eventIds : List String
  deriving DecidableEq

structure State where
  current : Cursor
  reserved : Usage
  usedLifetimeIds : List String
  pending : Option Pending
  closedGrants : List String
  owner : Option String
  ownerNonces : List String
  deriving DecidableEq

structure Receipt where
  commission : String
  source : String
  grant : String
  lifetimeId : String
  epoch : Nat
  used : Usage
  deriving DecidableEq

inductive Command where
  | reopen
  | reserve (grant : Grant)
  | deny (grant : Grant)
  | launch (grant : Grant)
  | charge (grant : Grant) (eventId : String) (delta : Usage)
  | close (grant : Grant) (receipt : Receipt)
  deriving DecidableEq

def SourceBound (c : Commission) (r : Runtime) : Prop :=
  c.identity ≠ "" ∧ c.source ≠ "" ∧ r.source = c.source ∧ r.owner ≠ "" ∧
  c.envelope.serviceLifetimes = 1 ∧ launchUsage.LE c.envelope

instance (c : Commission) (r : Runtime) : Decidable (SourceBound c r) := by
  unfold SourceBound
  infer_instance

def OwnerBound (r : Runtime) (s : State) : Prop :=
  s.owner = some r.owner ∧ 0 < s.current.epoch

instance (r : Runtime) (s : State) : Decidable (OwnerBound r s) := by
  unfold OwnerBound
  infer_instance

/-- The reservation cursor names the complete state BEFORE its reservation. -/
def ReservationReady (c : Commission) (r : Runtime) (s : State) (g : Grant) : Prop :=
  OwnerBound r s ∧ s.pending = none ∧ g.identity ≠ "" ∧ g.commission = c.identity ∧
  g.lifetimeId ≠ "" ∧ g.lifetimeId ∉ s.usedLifetimeIds ∧ g.owner = r.owner ∧
  g.epoch = s.current.epoch ∧ g.envelope = c.envelope ∧ g.reservationCursor = s.current

instance (c : Commission) (r : Runtime) (s : State) (g : Grant) :
    Decidable (ReservationReady c r s g) := by unfold ReservationReady; infer_instance

def GrantOwned (c : Commission) (r : Runtime) (s : State) (g : Grant) : Prop :=
  OwnerBound r s ∧ g.commission = c.identity ∧ g.owner = r.owner ∧ g.epoch = s.current.epoch

instance (c : Commission) (r : Runtime) (s : State) (g : Grant) :
    Decidable (GrantOwned c r s g) := by unfold GrantOwned; infer_instance

def ReceiptBound (c : Commission) (g : Grant) (p : Pending) (receipt : Receipt) : Prop :=
  receipt.commission = c.identity ∧ receipt.source = c.source ∧ receipt.grant = g.identity ∧
  receipt.lifetimeId = g.lifetimeId ∧ receipt.epoch = g.epoch ∧ receipt.used = p.used

instance (c : Commission) (g : Grant) (p : Pending) (receipt : Receipt) :
    Decidable (ReceiptBound c g p receipt) := by unfold ReceiptBound; infer_instance

def Allowed (c : Commission) (r : Runtime) (s : State) (command : Command) : Prop :=
  match command with
  | .reopen => s.pending = none ∧ r.owner ∉ s.ownerNonces
  | .reserve g => ReservationReady c r s g ∧ (s.reserved.add g.envelope).LE c.budget
  | .deny g => ReservationReady c r s g ∧ ¬ (s.reserved.add g.envelope).LE c.budget
  | .launch g => match s.pending with
      | none => False
      | some p => GrantOwned c r s g ∧ g = p.grant ∧ p.launched = false ∧
          (p.used.add launchUsage).LE g.envelope
  | .charge g eventId delta => match s.pending with
      | none => False
      | some p => GrantOwned c r s g ∧ g = p.grant ∧ p.launched = true ∧
          eventId ≠ "" ∧ eventId ∉ p.eventIds ∧ (p.used.add delta).LE g.envelope ∧
          delta.serviceLifetimes = 0 ∧ delta ≠ Usage.zero
  | .close g receipt => match s.pending with
      | none => False
      | some p => GrantOwned c r s g ∧ g = p.grant ∧ p.launched = true ∧ ReceiptBound c g p receipt

instance (c : Commission) (r : Runtime) (s : State) (command : Command) :
    Decidable (Allowed c r s command) := by
  cases command <;> unfold Allowed <;> cases s.pending <;> infer_instance

def Guard (c : Commission) (r : Runtime) (s : State) (expected : Cursor)
    (command : Command) (nextHead : String) : Prop :=
  SourceBound c r ∧ s.current.commission = c.identity ∧ expected = s.current ∧
  nextHead ≠ "" ∧ nextHead ≠ s.current.head ∧ Allowed c r s command

instance (c : Commission) (r : Runtime) (s : State) (expected : Cursor)
    (command : Command) (nextHead : String) : Decidable (Guard c r s expected command nextHead) := by
  unfold Guard
  infer_instance

def changed (r : Runtime) (s : State) (command : Command) : State :=
  match command with
  | .reopen => { s with
      current := { s.current with epoch := s.current.epoch + 1 }
      owner := some r.owner
      ownerNonces := s.ownerNonces ++ [r.owner] }
  | .reserve g => { s with
      reserved := s.reserved.add g.envelope
      usedLifetimeIds := s.usedLifetimeIds ++ [g.lifetimeId]
      pending := some ⟨g, false, Usage.zero, []⟩ }
  | .deny _ => s
  | .launch _ => { s with pending := s.pending.map (fun p =>
      { p with launched := true, used := p.used.add launchUsage }) }
  | .charge _ eventId delta => { s with pending := s.pending.map (fun p =>
      { p with used := p.used.add delta, eventIds := p.eventIds ++ [eventId] }) }
  | .close g _ => { s with pending := none, closedGrants := s.closedGrants ++ [g.identity] }

def installed (r : Runtime) (s : State) (command : Command) (nextHead : String) : State :=
  let next := changed r s command
  { next with current := { next.current with serial := s.current.serial + 1, head := nextHead } }

def advance (c : Commission) (r : Runtime) (s : State) (expected : Cursor)
    (command : Command) (nextHead : String) : Option State :=
  if Guard c r s expected command nextHead then some (installed r s command nextHead) else none

theorem advanced_spec (c : Commission) (r : Runtime) (s next : State) (expected : Cursor)
    (command : Command) (nextHead : String)
    (accepted : advance c r s expected command nextHead = some next) :
    Guard c r s expected command nextHead ∧ next = installed r s command nextHead := by
  unfold advance at accepted
  split at accepted
  · exact ⟨‹_›, (Option.some.inj accepted).symm⟩
  · cases accepted

theorem advanced_construct (c : Commission) (r : Runtime) (s : State) (expected : Cursor)
    (command : Command) (nextHead : String) (guard : Guard c r s expected command nextHead) :
    advance c r s expected command nextHead = some (installed r s command nextHead) := by
  simp only [advance, guard, if_true]

theorem advanced_source_bound (c : Commission) (r : Runtime) (s next : State) (expected : Cursor)
    (command : Command) (nextHead : String)
    (accepted : advance c r s expected command nextHead = some next) : SourceBound c r :=
  (advanced_spec c r s next expected command nextHead accepted).1.1

theorem advanced_current_cursor (c : Commission) (r : Runtime) (s next : State) (expected : Cursor)
    (command : Command) (nextHead : String)
    (accepted : advance c r s expected command nextHead = some next) : expected = s.current :=
  (advanced_spec c r s next expected command nextHead accepted).1.2.2.1

theorem stale_cursor_refused (c : Commission) (r : Runtime) (s : State) (expected : Cursor)
    (command : Command) (nextHead : String) (stale : expected ≠ s.current) :
    advance c r s expected command nextHead = none := by
  simp only [advance]
  split
  · rename_i h
    exact False.elim (stale h.2.2.1)
  · rfl

theorem advanced_serial (c : Commission) (r : Runtime) (s next : State) (expected : Cursor)
    (command : Command) (nextHead : String)
    (accepted : advance c r s expected command nextHead = some next) :
    next.current.serial = s.current.serial + 1 := by
  rw [(advanced_spec c r s next expected command nextHead accepted).2]
  rfl

theorem advanced_head (c : Commission) (r : Runtime) (s next : State) (expected : Cursor)
    (command : Command) (nextHead : String)
    (accepted : advance c r s expected command nextHead = some next) :
    next.current.head = nextHead ∧ next.current.head ≠ s.current.head := by
  have h := advanced_spec c r s next expected command nextHead accepted
  rw [h.2]
  exact ⟨rfl, h.1.2.2.2.2.1⟩

theorem reserved_exact (c : Commission) (r : Runtime) (s next : State) (expected : Cursor)
    (g : Grant) (nextHead : String)
    (accepted : advance c r s expected (.reserve g) nextHead = some next) :
    next.reserved = s.reserved.add g.envelope ∧
    next.pending = some ⟨g, false, Usage.zero, []⟩ ∧
    next.usedLifetimeIds = s.usedLifetimeIds ++ [g.lifetimeId] := by
  rw [(advanced_spec c r s next expected (.reserve g) nextHead accepted).2]
  exact ⟨rfl, rfl, rfl⟩

theorem reserved_commission_and_owner (c : Commission) (r : Runtime) (s next : State)
    (expected : Cursor) (g : Grant) (nextHead : String)
    (accepted : advance c r s expected (.reserve g) nextHead = some next) :
    g.commission = c.identity ∧ g.owner = r.owner ∧ g.epoch = s.current.epoch ∧
      g.envelope = c.envelope ∧ g.reservationCursor = s.current := by
  have ready := (advanced_spec c r s next expected (.reserve g) nextHead accepted).1.2.2.2.2.2.1
  rcases ready with ⟨_, _, _, hc, _, _, ho, he, hv, hp⟩
  exact ⟨hc, ho, he, hv, hp⟩

theorem reserved_within_budget (c : Commission) (r : Runtime) (s next : State) (expected : Cursor)
    (g : Grant) (nextHead : String)
    (accepted : advance c r s expected (.reserve g) nextHead = some next) :
    next.reserved.LE c.budget := by
  rw [(reserved_exact c r s next expected g nextHead accepted).1]
  exact (advanced_spec c r s next expected (.reserve g) nextHead accepted).1.2.2.2.2.2.2

theorem insufficient_budget_refused (c : Commission) (r : Runtime) (s : State) (expected : Cursor)
    (g : Grant) (nextHead : String) (insufficient : ¬ (s.reserved.add g.envelope).LE c.budget) :
    advance c r s expected (.reserve g) nextHead = none := by
  simp only [advance]
  split
  · rename_i h
    exact False.elim (insufficient h.2.2.2.2.2.2)
  · rfl

theorem denied_no_new_reservation (c : Commission) (r : Runtime) (s next : State)
    (expected : Cursor) (g : Grant) (nextHead : String)
    (accepted : advance c r s expected (.deny g) nextHead = some next) :
    next.reserved = s.reserved ∧ next.pending = s.pending ∧
    next.usedLifetimeIds = s.usedLifetimeIds := by
  rw [(advanced_spec c r s next expected (.deny g) nextHead accepted).2]
  exact ⟨rfl, rfl, rfl⟩

theorem denied_is_insufficient (c : Commission) (r : Runtime) (s next : State)
    (expected : Cursor) (g : Grant) (nextHead : String)
    (accepted : advance c r s expected (.deny g) nextHead = some next) :
    ¬ (s.reserved.add g.envelope).LE c.budget :=
  (advanced_spec c r s next expected (.deny g) nextHead accepted).1.2.2.2.2.2.2

theorem pending_blocks_reservation (c : Commission) (r : Runtime) (s : State)
    (expected : Cursor) (g : Grant) (nextHead : String) (pending : s.pending ≠ none) :
    advance c r s expected (.reserve g) nextHead = none := by
  simp only [advance]
  split
  · rename_i h
    exact False.elim (pending h.2.2.2.2.2.1.2.1)
  · rfl

theorem pending_blocks_reopen (c : Commission) (r : Runtime) (s : State)
    (expected : Cursor) (nextHead : String) (pending : s.pending ≠ none) :
    advance c r s expected .reopen nextHead = none := by
  simp only [advance]
  split
  · rename_i h
    exact False.elim (pending h.2.2.2.2.2.1)
  · rfl

theorem replayed_lifetime_refused (c : Commission) (r : Runtime) (s : State)
    (expected : Cursor) (g : Grant) (nextHead : String) (used : g.lifetimeId ∈ s.usedLifetimeIds) :
    advance c r s expected (.reserve g) nextHead = none := by
  simp only [advance]
  split
  · rename_i h
    exact False.elim (h.2.2.2.2.2.1.2.2.2.2.2.1 used)
  · rfl

theorem launched_requires_reservation (c : Commission) (r : Runtime) (s next : State)
    (expected : Cursor) (g : Grant) (nextHead : String)
    (accepted : advance c r s expected (.launch g) nextHead = some next) :
    ∃ p, s.pending = some p ∧ g = p.grant ∧ p.launched = false := by
  have h := (advanced_spec c r s next expected (.launch g) nextHead accepted).1.2.2.2.2.2
  cases hp : s.pending with
  | none => simp only [Allowed, hp] at h
  | some p =>
      simp only [Allowed, hp] at h
      exact ⟨p, rfl, h.2.1, h.2.2.1⟩

theorem launched_consumes_exactly (c : Commission) (r : Runtime) (s next : State)
    (expected : Cursor) (g : Grant) (nextHead : String) (p : Pending) (pending : s.pending = some p)
    (accepted : advance c r s expected (.launch g) nextHead = some next) :
    next.pending = some { p with launched := true, used := p.used.add launchUsage } := by
  rw [(advanced_spec c r s next expected (.launch g) nextHead accepted).2]
  simp only [installed, changed, pending, Option.map_some]

theorem launched_once (c : Commission) (r : Runtime) (s next : State)
    (expected laterExpected : Cursor) (g : Grant) (nextHead laterHead : String)
    (accepted : advance c r s expected (.launch g) nextHead = some next) :
    advance c r next laterExpected (.launch g) laterHead = none := by
  obtain ⟨p, pending, _, _⟩ := launched_requires_reservation c r s next expected g nextHead accepted
  have installedPending := launched_consumes_exactly c r s next expected g nextHead p pending accepted
  simp only [advance]
  split
  · rename_i h
    have bad := h.2.2.2.2.2
    simp only [Allowed, installedPending] at bad
    cases bad.2.2.1
  · rfl

theorem charged_exactly (c : Commission) (r : Runtime) (s next : State) (expected : Cursor)
    (g : Grant) (eventId : String) (delta : Usage) (nextHead : String) (p : Pending)
    (pending : s.pending = some p)
    (accepted : advance c r s expected (.charge g eventId delta) nextHead = some next) :
    next.pending = some { p with used := p.used.add delta, eventIds := p.eventIds ++ [eventId] } := by
  rw [(advanced_spec c r s next expected (.charge g eventId delta) nextHead accepted).2]
  simp only [installed, changed, pending, Option.map_some]

theorem charged_within_envelope (c : Commission) (r : Runtime) (s next : State) (expected : Cursor)
    (g : Grant) (eventId : String) (delta : Usage) (nextHead : String)
    (accepted : advance c r s expected (.charge g eventId delta) nextHead = some next) :
    ∃ p, next.pending = some p ∧ p.used.LE g.envelope := by
  have h := (advanced_spec c r s next expected (.charge g eventId delta) nextHead accepted).1.2.2.2.2.2
  cases hp : s.pending with
  | none => simp only [Allowed, hp] at h
  | some p =>
      simp only [Allowed, hp] at h
      exact ⟨_, charged_exactly c r s next expected g eventId delta nextHead p hp accepted,
        h.2.2.2.2.2.1⟩

theorem charged_no_refund (c : Commission) (r : Runtime) (s next : State) (expected : Cursor)
    (g : Grant) (eventId : String) (delta : Usage) (nextHead : String) (p q : Pending)
    (before : s.pending = some p) (after : next.pending = some q)
    (accepted : advance c r s expected (.charge g eventId delta) nextHead = some next) :
    p.used.LE q.used := by
  have same := Option.some.inj (after.symm.trans
    (charged_exactly c r s next expected g eventId delta nextHead p before accepted))
  rw [same]
  exact usage_not_refunded p.used delta

theorem close_receipt_bound (c : Commission) (r : Runtime) (s next : State) (expected : Cursor)
    (g : Grant) (receipt : Receipt) (nextHead : String)
    (accepted : advance c r s expected (.close g receipt) nextHead = some next) :
    ∃ p, s.pending = some p ∧ ReceiptBound c g p receipt := by
  have h := (advanced_spec c r s next expected (.close g receipt) nextHead accepted).1.2.2.2.2.2
  cases hp : s.pending with
  | none => simp only [Allowed, hp] at h
  | some p =>
      simp only [Allowed, hp] at h
      exact ⟨p, rfl, h.2.2.2⟩

theorem closed_no_refund (c : Commission) (r : Runtime) (s next : State) (expected : Cursor)
    (g : Grant) (receipt : Receipt) (nextHead : String)
    (accepted : advance c r s expected (.close g receipt) nextHead = some next) :
    next.reserved = s.reserved ∧ next.pending = none ∧
    next.closedGrants = s.closedGrants ++ [g.identity] := by
  rw [(advanced_spec c r s next expected (.close g receipt) nextHead accepted).2]
  exact ⟨rfl, rfl, rfl⟩

theorem reopened_no_refund (c : Commission) (r : Runtime) (s next : State) (expected : Cursor)
    (nextHead : String) (accepted : advance c r s expected .reopen nextHead = some next) :
    next.reserved = s.reserved ∧ next.current.epoch = s.current.epoch + 1 ∧
    next.owner = some r.owner ∧ next.ownerNonces = s.ownerNonces ++ [r.owner] := by
  rw [(advanced_spec c r s next expected .reopen nextHead accepted).2]
  exact ⟨rfl, rfl, rfl, rfl⟩

theorem cumulative_reservation_nondecreasing (c : Commission) (r : Runtime) (s next : State)
    (expected : Cursor) (command : Command) (nextHead : String)
    (accepted : advance c r s expected command nextHead = some next) : s.reserved.LE next.reserved := by
  rw [(advanced_spec c r s next expected command nextHead accepted).2]
  cases command <;> simp only [installed, changed]
  · exact usage_reflexive _
  · exact usage_not_refunded _ _
  · exact usage_reflexive _
  · exact usage_reflexive _
  · exact usage_reflexive _
  · exact usage_reflexive _

theorem advance_preserves_budget (c : Commission) (r : Runtime) (s next : State)
    (expected : Cursor) (command : Command) (nextHead : String) (before : s.reserved.LE c.budget)
    (accepted : advance c r s expected command nextHead = some next) : next.reserved.LE c.budget := by
  cases command with
  | reserve g => exact reserved_within_budget c r s next expected g nextHead accepted
  | _ =>
    rw [(advanced_spec c r s next expected _ nextHead accepted).2]
    exact before

def initial (c : Commission) (head : String) : State :=
  ⟨⟨c.identity, 0, 0, head⟩, Usage.zero, [], none, [], none, []⟩

inductive Reachable (c : Commission) (head : String) : State → Prop where
  | initial : Reachable c head (initial c head)
  | step {s next : State} (prior : Reachable c head s) (r : Runtime) (expected : Cursor)
      (command : Command) (nextHead : String)
      (accepted : advance c r s expected command nextHead = some next) : Reachable c head next

theorem reachable_reservations_bounded (c : Commission) (head : String) (s : State)
    (reachable : Reachable c head s) : s.reserved.LE c.budget := by
  induction reachable with
  | initial => exact usage_zero_bounded _
  | step prior r expected command nextHead accepted ih =>
      exact advance_preserves_budget c r _ _ expected command nextHead ih accepted

/-- Copying the entire authoritative ledger is outside the single-history
    transition relation. Identical copies still have identical admissibility. -/
theorem cloned_complete_ledgers_accept_identically (c : Commission) (r : Runtime)
    (s next : State) (expected : Cursor) (command : Command) (nextHead : String)
    (accepted : advance c r s expected command nextHead = some next) :
    ∃ first second : State, first = s ∧ second = s ∧
      advance c r first expected command nextHead = some next ∧
      advance c r second expected command nextHead = some next :=
  ⟨s, s, rfl, rfl, accepted, accepted⟩

structure TraceStep where
  runtime : Runtime
  before : State
  expected : Cursor
  command : Command
  nextHead : String
  after : Option State
  deriving DecidableEq

def stepValid (c : Commission) (step : TraceStep) : Bool :=
  decide (advance c step.runtime step.before step.expected step.command step.nextHead = step.after)

/-- No deployment or root conclusion is inferred from a lifecycle certificate.
    A future full verifier must separately supply its actual root obligations. -/
def promotionAdmission (completeAccounting independentlyCommissioned rootAccepted : Bool) : Bool :=
  completeAccounting && independentlyCommissioned && rootAccepted

theorem root_required (completeAccounting independentlyCommissioned rootAccepted : Bool)
    (accepted : promotionAdmission completeAccounting independentlyCommissioned rootAccepted = true) :
    rootAccepted = true := (Bool.and_eq_true_iff.mp accepted).2

theorem unknown_accounting_blocks_promotion (independentlyCommissioned rootAccepted : Bool) :
    promotionAdmission false independentlyCommissioned rootAccepted = false := rfl

theorem missing_commission_blocks_promotion (completeAccounting rootAccepted : Bool) :
    promotionAdmission completeAccounting false rootAccepted = false := by
  simp [promotionAdmission]

end Phase17ServiceLifecycle
