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


namespace Phase17AuthenticatedAuthorityExamples
open Phase17AuthenticatedAuthority
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def packetSha256 : String := "d37229bc7e4d59ad1be25c371b4258e782aa06acc549577406a2375d112fd675"
def commission : Commission := ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", "22c36a5b10fda25ce2b76fc4847e60958734410fd9dd7f1077f517ef49c0f845", "546e44c82524cd1bcdfeeee432b106e94f6daf99e883536fb2a4d7445832e787", "ac06c32a887e7c9681bbeeca41cf0d9a20252233a8091f6954af75c610cdf884"⟩
def channel : Channel := ⟨"22c36a5b10fda25ce2b76fc4847e60958734410fd9dd7f1077f517ef49c0f845", "546e44c82524cd1bcdfeeee432b106e94f6daf99e883536fb2a4d7445832e787", "ac06c32a887e7c9681bbeeca41cf0d9a20252233a8091f6954af75c610cdf884", "TLSv1.3"⟩
def firstRequest : Request := ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", "run", "5367bb38d84a9fec6cf7689ee9756ea8bc848e8bdc21ac3e17f9f10edff8105a", "4bcf299adea5379321be82ec83c7b91d15cd461ce789dbd93a02ab4290a203f4", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, 2, "331e20147b6a11325b36407d76cd9908c39db57acaf89bf79ed3016dd3a416d5"⟩
def lostRequest : Request := ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", "run", "4f93c2af74840d679bbbbee02501aa8e3f62a85eed994e41943c0ee46b93fd74", "ccb895eb4716eeb1bee259971225a67f49b29ee9bd6633860a60aa80659784cc", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, 2, "af03b7a25cdb54e014aa2294812e6215b7ec2f00c1d00c0f5acd0c3e7d6e5824"⟩
def reconcileRequest : Request := ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", "read", "0420ee9f152c6bab42b82c4ef1c4931f67d2bc3b1d282be2c772fe585136d247", "5e04a7d4e6bf1b8577df480f0200b2ef1ab860d320ee788181d310782ad9e0a9", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, 0, "548828b64a288bcc38691df695c67d6adffb21be5e214ee4a44987fb6e88ce8a"⟩
def firstReply : Reply := ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", "331e20147b6a11325b36407d76cd9908c39db57acaf89bf79ed3016dd3a416d5", "4bcf299adea5379321be82ec83c7b91d15cd461ce789dbd93a02ab4290a203f4", "run", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, [⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 0, 0, "53e35d5446cd819dbded9b4032b53450cc2727f35d19df790f920bf70071b1e5", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "provision", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "reopen", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 2, "bd09961f98754e2611605f638b9b8d9b9eeea3543de68c9053046db6a4b8cf30", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "76acb256b6cbc3d6730d1413d583e85805fb657d602271f31d3c53dbcedffe68"⟩, "reserve", some ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "5367bb38d84a9fec6cf7689ee9756ea8bc848e8bdc21ac3e17f9f10edff8105a", 2⟩⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 3, "844f5820f6b00245e3a4c4ff6aef0ad4a12a3476ec55de1304db4d96517ec76f", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "4b411780911c4d7fd8090848a1a5bcd7f9cf910d973acb45f3dfc0b5a4065657"⟩, "launch", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, "complete", none⟩], true⟩
def lostReply : Reply := ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", "af03b7a25cdb54e014aa2294812e6215b7ec2f00c1d00c0f5acd0c3e7d6e5824", "ccb895eb4716eeb1bee259971225a67f49b29ee9bd6633860a60aa80659784cc", "run", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 7, "0778b39d7bd45b16c8f6f26f257dd06a67a7b35893b0dba713c986ceb3f7c792", "310d3035babb1843be7104494021b9ad1bd7bac8610d282390bd90834f5de8dd", "c705726f4c31c7a33631065518b91831ce620a80b1323127b88b8fb50d695c00"⟩, [⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 0, 0, "53e35d5446cd819dbded9b4032b53450cc2727f35d19df790f920bf70071b1e5", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "provision", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "reopen", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 2, "bd09961f98754e2611605f638b9b8d9b9eeea3543de68c9053046db6a4b8cf30", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "76acb256b6cbc3d6730d1413d583e85805fb657d602271f31d3c53dbcedffe68"⟩, "reserve", some ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "5367bb38d84a9fec6cf7689ee9756ea8bc848e8bdc21ac3e17f9f10edff8105a", 2⟩⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 3, "844f5820f6b00245e3a4c4ff6aef0ad4a12a3476ec55de1304db4d96517ec76f", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "4b411780911c4d7fd8090848a1a5bcd7f9cf910d973acb45f3dfc0b5a4065657"⟩, "launch", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, "complete", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 5, "86b85cebca575c7276ef31e545222e1f4e25caf9c002c8298cfc3b8bb9ce1ae1", "2c8684c9568540d6847f87b43bbc8e3afbacd805a28772c69d05b0bde27794fc", "ad3e8954515b2987952bc78e4e68fac3af3d3ed550505a04a3b4a94c235a1c05"⟩, "reserve", some ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, "4f93c2af74840d679bbbbee02501aa8e3f62a85eed994e41943c0ee46b93fd74", 2⟩⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 6, "f003796f22cff96c07d6b665b40725c343c2339d7106e1a06112071ef54c3550", "2c8684c9568540d6847f87b43bbc8e3afbacd805a28772c69d05b0bde27794fc", "c3370d1a6ac26519f64dd3d638f2169505ca02cf775b0d9a2b80ca87c9a42214"⟩, "launch", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 7, "0778b39d7bd45b16c8f6f26f257dd06a67a7b35893b0dba713c986ceb3f7c792", "310d3035babb1843be7104494021b9ad1bd7bac8610d282390bd90834f5de8dd", "c705726f4c31c7a33631065518b91831ce620a80b1323127b88b8fb50d695c00"⟩, "complete", none⟩], true⟩
def reconcileReply : Reply := ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", "548828b64a288bcc38691df695c67d6adffb21be5e214ee4a44987fb6e88ce8a", "5e04a7d4e6bf1b8577df480f0200b2ef1ab860d320ee788181d310782ad9e0a9", "read", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 2, 8, "0a0995aee5e95ad0f01f5dfda30600b7a4d4258e0f90852d6402a2b397be1586", "310d3035babb1843be7104494021b9ad1bd7bac8610d282390bd90834f5de8dd", "c705726f4c31c7a33631065518b91831ce620a80b1323127b88b8fb50d695c00"⟩, ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 2, 8, "0a0995aee5e95ad0f01f5dfda30600b7a4d4258e0f90852d6402a2b397be1586", "310d3035babb1843be7104494021b9ad1bd7bac8610d282390bd90834f5de8dd", "c705726f4c31c7a33631065518b91831ce620a80b1323127b88b8fb50d695c00"⟩, [⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 0, 0, "53e35d5446cd819dbded9b4032b53450cc2727f35d19df790f920bf70071b1e5", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "provision", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "reopen", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 2, "bd09961f98754e2611605f638b9b8d9b9eeea3543de68c9053046db6a4b8cf30", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "76acb256b6cbc3d6730d1413d583e85805fb657d602271f31d3c53dbcedffe68"⟩, "reserve", some ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "5367bb38d84a9fec6cf7689ee9756ea8bc848e8bdc21ac3e17f9f10edff8105a", 2⟩⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 3, "844f5820f6b00245e3a4c4ff6aef0ad4a12a3476ec55de1304db4d96517ec76f", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "4b411780911c4d7fd8090848a1a5bcd7f9cf910d973acb45f3dfc0b5a4065657"⟩, "launch", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, "complete", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 5, "86b85cebca575c7276ef31e545222e1f4e25caf9c002c8298cfc3b8bb9ce1ae1", "2c8684c9568540d6847f87b43bbc8e3afbacd805a28772c69d05b0bde27794fc", "ad3e8954515b2987952bc78e4e68fac3af3d3ed550505a04a3b4a94c235a1c05"⟩, "reserve", some ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, "4f93c2af74840d679bbbbee02501aa8e3f62a85eed994e41943c0ee46b93fd74", 2⟩⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 6, "f003796f22cff96c07d6b665b40725c343c2339d7106e1a06112071ef54c3550", "2c8684c9568540d6847f87b43bbc8e3afbacd805a28772c69d05b0bde27794fc", "c3370d1a6ac26519f64dd3d638f2169505ca02cf775b0d9a2b80ca87c9a42214"⟩, "launch", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 7, "0778b39d7bd45b16c8f6f26f257dd06a67a7b35893b0dba713c986ceb3f7c792", "310d3035babb1843be7104494021b9ad1bd7bac8610d282390bd90834f5de8dd", "c705726f4c31c7a33631065518b91831ce620a80b1323127b88b8fb50d695c00"⟩, "complete", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 2, 8, "0a0995aee5e95ad0f01f5dfda30600b7a4d4258e0f90852d6402a2b397be1586", "310d3035babb1843be7104494021b9ad1bd7bac8610d282390bd90834f5de8dd", "c705726f4c31c7a33631065518b91831ce620a80b1323127b88b8fb50d695c00"⟩, "reopen", none⟩], true⟩
def firstIdle : Anchor := ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, [⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 0, 0, "53e35d5446cd819dbded9b4032b53450cc2727f35d19df790f920bf70071b1e5", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "provision", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "reopen", none⟩], none⟩
def firstPending : Anchor := ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, [⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 0, 0, "53e35d5446cd819dbded9b4032b53450cc2727f35d19df790f920bf70071b1e5", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "provision", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "reopen", none⟩], some ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", "run", "5367bb38d84a9fec6cf7689ee9756ea8bc848e8bdc21ac3e17f9f10edff8105a", "4bcf299adea5379321be82ec83c7b91d15cd461ce789dbd93a02ab4290a203f4", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, 2, "331e20147b6a11325b36407d76cd9908c39db57acaf89bf79ed3016dd3a416d5"⟩⟩
def firstSettled : Anchor := ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, [⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 0, 0, "53e35d5446cd819dbded9b4032b53450cc2727f35d19df790f920bf70071b1e5", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "provision", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "reopen", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 2, "bd09961f98754e2611605f638b9b8d9b9eeea3543de68c9053046db6a4b8cf30", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "76acb256b6cbc3d6730d1413d583e85805fb657d602271f31d3c53dbcedffe68"⟩, "reserve", some ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "5367bb38d84a9fec6cf7689ee9756ea8bc848e8bdc21ac3e17f9f10edff8105a", 2⟩⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 3, "844f5820f6b00245e3a4c4ff6aef0ad4a12a3476ec55de1304db4d96517ec76f", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "4b411780911c4d7fd8090848a1a5bcd7f9cf910d973acb45f3dfc0b5a4065657"⟩, "launch", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, "complete", none⟩], none⟩
def lostIdle : Anchor := ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, [⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 0, 0, "53e35d5446cd819dbded9b4032b53450cc2727f35d19df790f920bf70071b1e5", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "provision", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "reopen", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 2, "bd09961f98754e2611605f638b9b8d9b9eeea3543de68c9053046db6a4b8cf30", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "76acb256b6cbc3d6730d1413d583e85805fb657d602271f31d3c53dbcedffe68"⟩, "reserve", some ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "5367bb38d84a9fec6cf7689ee9756ea8bc848e8bdc21ac3e17f9f10edff8105a", 2⟩⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 3, "844f5820f6b00245e3a4c4ff6aef0ad4a12a3476ec55de1304db4d96517ec76f", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "4b411780911c4d7fd8090848a1a5bcd7f9cf910d973acb45f3dfc0b5a4065657"⟩, "launch", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, "complete", none⟩], none⟩
def lostAnchor : Anchor := ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, [⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 0, 0, "53e35d5446cd819dbded9b4032b53450cc2727f35d19df790f920bf70071b1e5", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "provision", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "reopen", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 2, "bd09961f98754e2611605f638b9b8d9b9eeea3543de68c9053046db6a4b8cf30", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "76acb256b6cbc3d6730d1413d583e85805fb657d602271f31d3c53dbcedffe68"⟩, "reserve", some ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "5367bb38d84a9fec6cf7689ee9756ea8bc848e8bdc21ac3e17f9f10edff8105a", 2⟩⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 3, "844f5820f6b00245e3a4c4ff6aef0ad4a12a3476ec55de1304db4d96517ec76f", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "4b411780911c4d7fd8090848a1a5bcd7f9cf910d973acb45f3dfc0b5a4065657"⟩, "launch", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, "complete", none⟩], some ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", "run", "4f93c2af74840d679bbbbee02501aa8e3f62a85eed994e41943c0ee46b93fd74", "ccb895eb4716eeb1bee259971225a67f49b29ee9bd6633860a60aa80659784cc", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, 2, "af03b7a25cdb54e014aa2294812e6215b7ec2f00c1d00c0f5acd0c3e7d6e5824"⟩⟩
def reconciledAnchor : Anchor := ⟨"044c69445f3898bf69bceb230668013f4f1530adc246918c4159511731bb80c0", "19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", ⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 2, 8, "0a0995aee5e95ad0f01f5dfda30600b7a4d4258e0f90852d6402a2b397be1586", "310d3035babb1843be7104494021b9ad1bd7bac8610d282390bd90834f5de8dd", "c705726f4c31c7a33631065518b91831ce620a80b1323127b88b8fb50d695c00"⟩, [⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 0, 0, "53e35d5446cd819dbded9b4032b53450cc2727f35d19df790f920bf70071b1e5", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "provision", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "reopen", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 2, "bd09961f98754e2611605f638b9b8d9b9eeea3543de68c9053046db6a4b8cf30", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "76acb256b6cbc3d6730d1413d583e85805fb657d602271f31d3c53dbcedffe68"⟩, "reserve", some ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 1, "14775ae88a6d3eff25e1e163d8ffead596a78266e02aa5405d5537530f1b8dfe", "2778cabb7125728d5c5fad47e725846ef15db5a2f1673967b3d1510fcb4008f8", "a11de59022c10ecb18777bbb0b8cae14cc13c5910f66c2eeb435646f5fe1531a"⟩, "5367bb38d84a9fec6cf7689ee9756ea8bc848e8bdc21ac3e17f9f10edff8105a", 2⟩⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 3, "844f5820f6b00245e3a4c4ff6aef0ad4a12a3476ec55de1304db4d96517ec76f", "bb371a68cad7a083d8c42b016a72739ab33834f0234bc5df5ed6eb2546778d1a", "4b411780911c4d7fd8090848a1a5bcd7f9cf910d973acb45f3dfc0b5a4065657"⟩, "launch", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, "complete", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 5, "86b85cebca575c7276ef31e545222e1f4e25caf9c002c8298cfc3b8bb9ce1ae1", "2c8684c9568540d6847f87b43bbc8e3afbacd805a28772c69d05b0bde27794fc", "ad3e8954515b2987952bc78e4e68fac3af3d3ed550505a04a3b4a94c235a1c05"⟩, "reserve", some ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 4, "9756951b23292efe92bb3bd09638b7474f7583bb7d7a14eb4623bbb3270754db", "ed97d1eec22c60cd06091014d478285a336e0c474f1f74c9f1254b12bf9b52b4", "3599eb99077ab23c9702fcf7281d52c7c287d60adfdb6bb7f78f244b9ec694f2"⟩, "4f93c2af74840d679bbbbee02501aa8e3f62a85eed994e41943c0ee46b93fd74", 2⟩⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 6, "f003796f22cff96c07d6b665b40725c343c2339d7106e1a06112071ef54c3550", "2c8684c9568540d6847f87b43bbc8e3afbacd805a28772c69d05b0bde27794fc", "c3370d1a6ac26519f64dd3d638f2169505ca02cf775b0d9a2b80ca87c9a42214"⟩, "launch", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 1, 7, "0778b39d7bd45b16c8f6f26f257dd06a67a7b35893b0dba713c986ceb3f7c792", "310d3035babb1843be7104494021b9ad1bd7bac8610d282390bd90834f5de8dd", "c705726f4c31c7a33631065518b91831ce620a80b1323127b88b8fb50d695c00"⟩, "complete", none⟩, ⟨⟨"19cc29decad632ef2b1083bb66b7c19b7b2d02b0134da9678adb98aa35402362", 2, 8, "0a0995aee5e95ad0f01f5dfda30600b7a4d4258e0f90852d6402a2b397be1586", "310d3035babb1843be7104494021b9ad1bd7bac8610d282390bd90834f5de8dd", "c705726f4c31c7a33631065518b91831ce620a80b1323127b88b8fb50d695c00"⟩, "reopen", none⟩], none⟩
def firstConsumed : List String := []
def lostConsumed : List String := ["5367bb38d84a9fec6cf7689ee9756ea8bc848e8bdc21ac3e17f9f10edff8105a"]
theorem first_authenticated_dispatch :
    dispatch commission channel firstReply.before firstConsumed firstRequest = some "run" := by decide +kernel
theorem first_reply_bound : ReplyBound commission channel firstIdle firstRequest firstReply := by decide +kernel
theorem first_write_ahead_pending : beginMutation commission firstIdle firstRequest = some firstPending := by decide +kernel
theorem first_matching_settlement :
    receiveReply commission channel firstPending firstRequest firstReply = some firstSettled := by decide +kernel
theorem restart_reconciliation : lostRequest.expected.epoch < reconcileReply.after.epoch ∧
    dispatch commission channel lostReply.before lostConsumed lostRequest = some "run" := by decide +kernel
theorem lost_reply_blocks_retry : lostAnchor.pending = some lostRequest ∧
    beginMutation commission lostAnchor lostRequest = none := by decide +kernel
theorem reconcile_requires_read : reconcileRequest.operation = "read" ∧
    reconcile commission channel lostAnchor reconcileRequest reconcileReply = some reconciledAnchor := by decide +kernel
theorem reconcile_terminal_completion : terminalFor lostRequest reconcileReply.history = true ∧
    reconciledAnchor.pending = none ∧ lostAnchor.current.serial ≤ reconciledAnchor.current.serial := by decide +kernel
theorem cloned_authenticated_root_outside_guarantee :
    ∃ first second : Cursor, first = firstReply.before ∧ second = firstReply.before ∧
      dispatch commission channel first firstConsumed firstRequest = some firstRequest.operation ∧
      dispatch commission channel second firstConsumed firstRequest = some firstRequest.operation := by
  apply identical_authorities_accept_identically
  exact first_authenticated_dispatch
end Phase17AuthenticatedAuthorityExamples
