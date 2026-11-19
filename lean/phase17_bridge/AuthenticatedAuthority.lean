import Std
import Lean.Elab.Tactic.Omega

/- Phase 17AM: structural authorization of the authenticated AL endpoint and
   independently retained client history. Channel identities are supplied by
   the checked TLS adapter's original peer-certificate observations; no caller
   field creates an authenticated channel. TLS, certificate validation, SHA-256,
   storage, operating-system isolation and legitimate provisioning are external
   premises. Header projections come from the actual AL events, whose complete
   byte/hash/transition checks precede generation. This module does not prove
   global exclusivity, complete accounting, physical execution, or promotion. -/
namespace Phase17AuthenticatedAuthority

structure Commission where
  identity : String
  root : String
  server : String
  client : String
  ca : String
  deriving DecidableEq

structure Channel where
  server : String
  client : String
  ca : String
  version : String
  deriving DecidableEq

def ChannelBound (c : Commission) (o : Channel) : Prop :=
  o.server = c.server ∧ o.client = c.client ∧ o.ca = c.ca ∧
  o.version = "TLSv1.3" ∧ c.identity ≠ "" ∧ c.root ≠ ""

instance (c : Commission) (o : Channel) : Decidable (ChannelBound c o) := by
  unfold ChannelBound
  infer_instance

structure Cursor where
  provision : String
  epoch : Nat
  serial : Nat
  head : String
  journal : String
  image : String
  deriving DecidableEq

structure Mutation where
  expected : Cursor
  nonce : String
  credits : Nat
  deriving DecidableEq

structure Request where
  commission : String
  root : String
  operation : String
  nonce : String
  challenge : String
  expected : Cursor
  credits : Nat
  digest : String
  deriving DecidableEq

def Request.mutation (q : Request) : Mutation := ⟨q.expected, q.nonce, q.credits⟩

def ControllerOperation (operation : String) : Prop :=
  operation = "read" ∨ operation = "run"

instance (operation : String) : Decidable (ControllerOperation operation) := by
  unfold ControllerOperation
  infer_instance

def DispatchGuard (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request) : Prop :=
  ChannelBound c o ∧ q.commission = c.identity ∧ q.root = c.root ∧
  q.expected.provision = c.root ∧ current.provision = c.root ∧
  ControllerOperation q.operation ∧ q.nonce ≠ "" ∧ q.challenge ≠ "" ∧ q.digest ≠ "" ∧
  (q.operation = "read" → q.credits = 0) ∧
  (q.operation = "run" → q.expected = current ∧ q.nonce ∉ consumed ∧ q.credits ≤ 32)

instance (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request) : Decidable (DispatchGuard c o current consumed q) := by
  unfold DispatchGuard
  infer_instance

def dispatch (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request) : Option String :=
  if DispatchGuard c o current consumed q then some q.operation else none

theorem dispatch_spec (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request) :
    dispatch c o current consumed q = some q.operation ↔ DispatchGuard c o current consumed q := by
  simp only [dispatch]
  split <;> simp_all

theorem dispatch_bound_identity (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request)
    (accepted : dispatch c o current consumed q = some q.operation) :
    ChannelBound c o ∧ q.commission = c.identity ∧ q.root = c.root := by
  have h := (dispatch_spec c o current consumed q).mp accepted
  exact ⟨h.1, h.2.1, h.2.2.1⟩

theorem wrong_server_refused (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request) (wrong : o.server ≠ c.server) :
    dispatch c o current consumed q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim (wrong h.1.1)
  · rfl

theorem wrong_client_refused (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request) (wrong : o.client ≠ c.client) :
    dispatch c o current consumed q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim (wrong h.1.2.1)
  · rfl

theorem wrong_ca_refused (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request) (wrong : o.ca ≠ c.ca) :
    dispatch c o current consumed q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim (wrong h.1.2.2.1)
  · rfl

theorem wrong_commission_refused (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request) (wrong : q.commission ≠ c.identity) :
    dispatch c o current consumed q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim (wrong h.2.1)
  · rfl

theorem wrong_root_refused (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request) (wrong : q.root ≠ c.root) :
    dispatch c o current consumed q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim (wrong h.2.2.1)
  · rfl

theorem administrative_operation_refused (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request) (wrong : ¬ ControllerOperation q.operation) :
    dispatch c o current consumed q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim (wrong h.2.2.2.2.2.1)
  · rfl

theorem run_current_cursor (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request)
    (accepted : dispatch c o current consumed q = some q.operation) (run : q.operation = "run") :
    q.expected = current ∧ q.nonce ∉ consumed ∧ q.credits ≤ 32 := by
  have h := (dispatch_spec c o current consumed q).mp accepted
  exact h.2.2.2.2.2.2.2.2.2.2 run

theorem stale_run_refused (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request) (run : q.operation = "run")
    (wrong : q.expected ≠ current) : dispatch c o current consumed q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim (wrong (h.2.2.2.2.2.2.2.2.2.2 run).1)
  · rfl

theorem replayed_run_refused (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request) (run : q.operation = "run")
    (used : q.nonce ∈ consumed) : dispatch c o current consumed q = none := by
  simp only [dispatch]
  split
  · rename_i h
    exact False.elim ((h.2.2.2.2.2.2.2.2.2.2 run).2.1 used)
  · rfl

structure Header where
  cursor : Cursor
  kind : String
  request : Option Mutation
  deriving DecidableEq

def Prefix (old next : List Header) : Prop := next.take old.length = old

instance (old next : List Header) : Decidable (Prefix old next) := by
  unfold Prefix
  infer_instance

theorem prefix_reflexive (history : List Header) : Prefix history history := by
  simp [Prefix]

theorem prefix_length (old next : List Header) (bound : Prefix old next) : old.length ≤ next.length := by
  have same := congrArg List.length bound
  simp only [List.length_take] at same
  omega

def HeadBound (history : List Header) (current : Cursor) : Prop :=
  history.length = current.serial + 1 ∧ (history.getLast?).map Header.cursor = some current

instance (history : List Header) (current : Cursor) : Decidable (HeadBound history current) := by
  unfold HeadBound
  infer_instance

structure Anchor where
  commission : String
  root : String
  current : Cursor
  history : List Header
  pending : Option Request
  deriving DecidableEq

structure Reply where
  commission : String
  root : String
  requestDigest : String
  challenge : String
  operation : String
  before : Cursor
  after : Cursor
  history : List Header
  accepted : Bool
  deriving DecidableEq

def ReplyBound (c : Commission) (o : Channel) (a : Anchor) (q : Request) (r : Reply) : Prop :=
  ChannelBound c o ∧ a.commission = c.identity ∧ a.root = c.root ∧
  q.commission = c.identity ∧ q.root = c.root ∧
  r.commission = c.identity ∧ r.root = c.root ∧
  r.requestDigest = q.digest ∧ r.challenge = q.challenge ∧ r.operation = q.operation ∧
  r.before.provision = c.root ∧ r.after.provision = c.root ∧
  HeadBound a.history a.current ∧ HeadBound r.history r.after ∧
  Prefix a.history r.history ∧ a.current.epoch ≤ r.after.epoch ∧
  r.before.serial ≤ r.after.serial ∧
  (r.history[r.before.serial]?).map Header.cursor = some r.before ∧
  (r.operation = "read" → r.before = r.after)

instance (c : Commission) (o : Channel) (a : Anchor) (q : Request) (r : Reply) :
    Decidable (ReplyBound c o a q r) := by
  unfold ReplyBound
  infer_instance

def acceptReply (c : Commission) (o : Channel) (a : Anchor) (q : Request) (r : Reply) : Bool :=
  decide (ReplyBound c o a q r)

theorem reply_bound_identity (c : Commission) (o : Channel) (a : Anchor) (q : Request) (r : Reply)
    (bound : ReplyBound c o a q r) :
    r.commission = c.identity ∧ r.root = c.root ∧ r.requestDigest = q.digest ∧
    r.challenge = q.challenge ∧ r.operation = q.operation := by
  exact ⟨bound.2.2.2.2.2.1, bound.2.2.2.2.2.2.1, bound.2.2.2.2.2.2.2.1,
    bound.2.2.2.2.2.2.2.2.1, bound.2.2.2.2.2.2.2.2.2.1⟩

theorem reply_currentness_monotone (c : Commission) (o : Channel) (a : Anchor)
    (q : Request) (r : Reply) (bound : ReplyBound c o a q r) :
    a.current.serial ≤ r.after.serial ∧ a.current.epoch ≤ r.after.epoch := by
  rcases bound with ⟨_, _, _, _, _, _, _, _, _, _, _, _, oldHead, nextHead, prefixBound, epoch, _, _, _⟩
  have sizes := prefix_length a.history r.history prefixBound
  have oldSize := oldHead.1
  have nextSize := nextHead.1
  constructor
  · omega
  · exact epoch

theorem wrong_response_request_refused (c : Commission) (o : Channel) (a : Anchor)
    (q : Request) (r : Reply) (wrong : r.requestDigest ≠ q.digest) :
    acceptReply c o a q r = false := by
  apply decide_eq_false
  intro h
  exact wrong (reply_bound_identity c o a q r h).2.2.1

theorem wrong_response_challenge_refused (c : Commission) (o : Channel) (a : Anchor)
    (q : Request) (r : Reply) (wrong : r.challenge ≠ q.challenge) :
    acceptReply c o a q r = false := by
  apply decide_eq_false
  intro h
  exact wrong (reply_bound_identity c o a q r h).2.2.2.1

theorem rollback_reply_refused (c : Commission) (o : Channel) (a : Anchor)
    (q : Request) (r : Reply) (old : r.after.serial < a.current.serial) :
    acceptReply c o a q r = false := by
  apply decide_eq_false
  intro h
  have newer := (reply_currentness_monotone c o a q r h).1
  omega

theorem forked_prefix_refused (c : Commission) (o : Channel) (a : Anchor)
    (q : Request) (r : Reply) (fork : ¬ Prefix a.history r.history) :
    acceptReply c o a q r = false := by
  apply decide_eq_false
  intro h
  rcases h with ⟨_, _, _, _, _, _, _, _, _, _, _, _, _, _, prefixBound, _, _, _, _⟩
  exact fork prefixBound

def BeginGuard (c : Commission) (a : Anchor) (q : Request) : Prop :=
  a.commission = c.identity ∧ a.root = c.root ∧ HeadBound a.history a.current ∧
  a.pending = none ∧ q.commission = c.identity ∧ q.root = c.root ∧
  q.operation = "run" ∧ q.expected = a.current ∧ q.nonce ≠ "" ∧
  q.challenge ≠ "" ∧ q.digest ≠ ""

instance (c : Commission) (a : Anchor) (q : Request) : Decidable (BeginGuard c a q) := by
  unfold BeginGuard
  infer_instance

def beginMutation (c : Commission) (a : Anchor) (q : Request) : Option Anchor :=
  if BeginGuard c a q then some { a with pending := some q } else none

theorem begin_sets_pending (c : Commission) (a b : Anchor) (q : Request)
    (begun : beginMutation c a q = some b) : b.pending = some q := by
  unfold beginMutation at begun
  split at begun
  · cases begun
    rfl
  · contradiction

theorem begin_keeps_anchor (c : Commission) (a b : Anchor) (q : Request)
    (begun : beginMutation c a q = some b) :
    b.commission = a.commission ∧ b.root = a.root ∧ b.current = a.current ∧ b.history = a.history := by
  unfold beginMutation at begun
  split at begun
  · cases begun
    exact ⟨rfl, rfl, rfl, rfl⟩
  · contradiction

theorem pending_blocks_mutation (c : Commission) (a : Anchor) (q pending : Request)
    (ambiguous : a.pending = some pending) : beginMutation c a q = none := by
  unfold beginMutation
  split
  · rename_i h
    have idle := h.2.2.2.1
    rw [ambiguous] at idle
    contradiction
  · rfl

/-- The missing-response transition performs no mutation and issues no call. -/
def missingResponse (a : Anchor) : Anchor := a

theorem missing_response_keeps_pending (a : Anchor) : (missingResponse a).pending = a.pending := rfl

def settled (a : Anchor) (r : Reply) : Anchor :=
  { a with current := r.after, history := r.history, pending := none }

def receiveReply (c : Commission) (o : Channel) (a : Anchor) (q : Request) (r : Reply) : Option Anchor :=
  if ReplyBound c o a q r ∧ a.pending = some q then some (settled a r) else none

theorem settlement_matches_pending (c : Commission) (o : Channel) (a b : Anchor)
    (q : Request) (r : Reply) (received : receiveReply c o a q r = some b) :
    a.pending = some q ∧ b.pending = none ∧ b.current = r.after ∧ b.history = r.history := by
  unfold receiveReply at received
  split at received
  · rename_i h
    cases received
    exact ⟨h.2, rfl, rfl, rfl⟩
  · contradiction

/-- AL's selected serialized history can finish a request only by direct denial
    or the adjacent reserve/launch/complete path for the same mutation. A reopen
    between reservation and completion therefore cannot resolve ambiguity. -/
def terminalFor (q : Request) : List Header → Bool
  | [] => false
  | h :: tail =>
      if h.kind = "deny" ∧ h.request = some q.mutation then true
      else if h.kind = "reserve" ∧ h.request = some q.mutation then
        match tail with
        | launch :: complete :: _ =>
            if launch.kind = "launch" ∧ complete.kind = "complete" then true else terminalFor q tail
        | _ => terminalFor q tail
      else terminalFor q tail

def reconciledPending (a : Anchor) (r : Reply) : Option Request :=
  match a.pending with
  | none => none
  | some pending => if terminalFor pending r.history then none else some pending

def reconcile (c : Commission) (o : Channel) (a : Anchor) (read : Request) (r : Reply) : Option Anchor :=
  if ReplyBound c o a read r ∧ read.operation = "read" ∧ a.pending.isSome then
    some { a with current := r.after, history := r.history, pending := reconciledPending a r }
  else none

theorem reconcile_is_read_only (c : Commission) (o : Channel) (a b : Anchor)
    (read : Request) (r : Reply) (received : reconcile c o a read r = some b) :
    read.operation = "read" ∧ b.commission = a.commission ∧ b.root = a.root := by
  unfold reconcile at received
  split at received
  · rename_i h
    cases received
    exact ⟨h.2.1, rfl, rfl⟩
  · contradiction

theorem reconcile_clear_requires_terminal (c : Commission) (o : Channel) (a b : Anchor)
    (read pending : Request) (r : Reply) (waiting : a.pending = some pending)
    (received : reconcile c o a read r = some b) (cleared : b.pending = none) :
    terminalFor pending r.history = true := by
  unfold reconcile at received
  split at received
  · cases received
    simp only [reconciledPending, waiting] at cleared
    split at cleared
    · assumption
    · contradiction
  · contradiction

theorem unresolved_reconcile_preserves_pending (c : Commission) (o : Channel) (a b : Anchor)
    (read pending : Request) (r : Reply) (waiting : a.pending = some pending)
    (received : reconcile c o a read r = some b) (unresolved : terminalFor pending r.history = false) :
    b.pending = some pending := by
  unfold reconcile at received
  split at received
  · cases received
    simp [reconciledPending, waiting, unresolved]
  · contradiction

/-- Authentication gives identical copies identical authority. Exclusion of
    cloned physical roots and credentials is not a consequence of this model. -/
theorem identical_authorities_accept_identically (c : Commission) (o : Channel) (current : Cursor)
    (consumed : List String) (q : Request)
    (accepted : dispatch c o current consumed q = some q.operation) :
    ∃ first second : Cursor, first = current ∧ second = current ∧
      dispatch c o first consumed q = some q.operation ∧
      dispatch c o second consumed q = some q.operation := by
  exact ⟨current, current, rfl, rfl, accepted, accepted⟩

/-- Rolling back both a trusted anchor and the authority is invisible to the
    prefix predicate. The anchor's independent retention is a real premise. -/
theorem joint_rollback_preserves_local_consistency (history : List Header) :
    Prefix history history := prefix_reflexive history

end Phase17AuthenticatedAuthority
