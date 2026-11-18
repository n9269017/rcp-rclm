import AuthorityWitness

/- Phase 17AK: a provisioned durable root serializes paired witness/authority
   images and fences successive witness lifetimes. `commit` is the specified
   atomic root operation. The file system, database, process lock, independent
   provisioning and cryptographic implementations are outside this theorem.
   Image strings name the exact paired bytes checked by the executable gate;
   they are not a theorem about a digest algorithm or physical persistence.
   A second physical copy of the root is not a transition of this model. -/
namespace Phase17DurableAuthority

open Phase17AuthorityWitness

structure RootProvision where
  identity : String
  witness : Provision
  deriving DecidableEq

structure Image where
  rootHead : String
  pair : String
  deriving DecidableEq

def ImageValid (image : Image) : Prop := image.rootHead ≠ "" ∧ image.pair ≠ ""

instance imageValidDecidable (image : Image) : Decidable (ImageValid image) := by
  unfold ImageValid
  infer_instance

structure RootState where
  identity : String
  epoch : Nat
  serial : Nat
  image : Image
  witness : WitnessState
  deriving DecidableEq

structure Handle where
  identity : String
  epoch : Nat
  deriving DecidableEq

/- A handle is structural current-epoch data, not an authentication secret or
   an attestation of an exclusive physical process. The configured backend
   authenticates requests and owns the lifetime lock outside this model. -/

structure Cursor where
  identity : String
  epoch : Nat
  serial : Nat
  image : Image
  revision : Nat
  head : String
  journal : String
  deriving DecidableEq

def handle (state : RootState) : Handle := ⟨state.identity, state.epoch⟩

def cursor (state : RootState) : Cursor :=
  ⟨state.identity, state.epoch, state.serial, state.image, state.witness.revision, state.witness.head, state.witness.journal⟩

inductive Mode where
  | mutation
  | reopen
  deriving DecidableEq

/- Mode is selected by trusted backend dispatch. Controllers cannot choose the
   reopening mode. ModeBound proves that ordinary mutation cannot carry AJ's
   administrative reopen operation; it does not authenticate the backend. -/

def ModeBound (mode : Mode) (request : Request) : Prop :=
  match mode with
  | .mutation => request.command ≠ .reopen
  | .reopen => request.command = .reopen

instance modeBoundDecidable (mode : Mode) (request : Request) : Decidable (ModeBound mode request) := by
  cases mode <;> unfold ModeBound <;> infer_instance

def nextEpoch (mode : Mode) (epoch : Nat) : Nat :=
  match mode with
  | .mutation => epoch
  | .reopen => epoch + 1

def RootGuard (p : RootProvision) (state : RootState) (owner : Handle)
    (expected : Cursor) (mode : Mode) (request : Request) (nextImage : Image) : Prop :=
  p.identity ≠ "" ∧ state.identity = p.identity ∧ owner.identity = p.identity ∧
  owner.epoch = state.epoch ∧ expected = cursor state ∧
  ModeBound mode request ∧ ImageValid nextImage ∧
  (nextImage.rootHead ≠ state.image.rootHead ∧ nextImage.pair ≠ state.image.pair)

instance rootGuardDecidable (p : RootProvision) (state : RootState) (owner : Handle)
    (expected : Cursor) (mode : Mode) (request : Request) (nextImage : Image) :
    Decidable (RootGuard p state owner expected mode request nextImage) := by
  unfold RootGuard
  infer_instance

def installed (state : RootState) (mode : Mode) (nextImage : Image)
    (nextWitness : WitnessState) : RootState :=
  { state with
    epoch := nextEpoch mode state.epoch
    serial := state.serial + 1
    image := nextImage
    witness := nextWitness }

/-- The only root mutation: test the current provision, lifetime and complete
    cursor, recompute AJ's transition, and install its paired image once. -/
def commit (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image) : Option RootState :=
  if RootGuard p state owner expected mode request nextImage then
    (advance p.witness contexts evaluators state.witness request nextHead nextJournal).map
      (installed state mode nextImage)
  else none

theorem committed_spec (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected mode request
      nextHead nextJournal nextImage = some next) :
    RootGuard p state owner expected mode request nextImage ∧
    ∃ nextWitness, advance p.witness contexts evaluators state.witness request
      nextHead nextJournal = some nextWitness ∧
      next = installed state mode nextImage nextWitness := by
  unfold commit at accepted
  split at accepted
  next valid =>
    refine ⟨valid, ?_⟩
    cases result : advance p.witness contexts evaluators state.witness request nextHead nextJournal with
    | none => simp only [result, Option.map_none] at accepted; cases accepted
    | some nextWitness =>
        simp only [result, Option.map_some] at accepted
        exact ⟨nextWitness, rfl, (Option.some.inj accepted).symm⟩
  next invalid => cases accepted

theorem committed_construct (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image) (nextWitness : WitnessState)
    (guard : RootGuard p state owner expected mode request nextImage)
    (transition : advance p.witness contexts evaluators state.witness request
      nextHead nextJournal = some nextWitness) :
    commit p contexts evaluators state owner expected mode request nextHead nextJournal nextImage =
      some (installed state mode nextImage nextWitness) := by
  simp only [commit, guard, if_true, transition, Option.map_some]

theorem committed_witness_exact (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected mode request
      nextHead nextJournal nextImage = some next) :
    advance p.witness contexts evaluators state.witness request nextHead nextJournal = some next.witness := by
  rcases (committed_spec p contexts evaluators state next owner expected mode request
    nextHead nextJournal nextImage accepted).2 with ⟨nextWitness, transition, equal⟩
  rw [equal]
  exact transition

theorem committed_serial (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected mode request
      nextHead nextJournal nextImage = some next) : next.serial = state.serial + 1 := by
  rcases (committed_spec p contexts evaluators state next owner expected mode request
    nextHead nextJournal nextImage accepted).2 with ⟨_, _, equal⟩
  rw [equal]
  rfl

theorem committed_epoch (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected mode request
      nextHead nextJournal nextImage = some next) : next.epoch = nextEpoch mode state.epoch := by
  rcases (committed_spec p contexts evaluators state next owner expected mode request
    nextHead nextJournal nextImage accepted).2 with ⟨_, _, equal⟩
  rw [equal]
  rfl

theorem committed_epoch_nondecreasing (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected mode request
      nextHead nextJournal nextImage = some next) : state.epoch ≤ next.epoch := by
  rw [committed_epoch p contexts evaluators state next owner expected mode request
    nextHead nextJournal nextImage accepted]
  cases mode <;> simp [nextEpoch]

theorem committed_identity (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected mode request
      nextHead nextJournal nextImage = some next) : next.identity = p.identity := by
  have spec := committed_spec p contexts evaluators state next owner expected mode request
    nextHead nextJournal nextImage accepted
  rcases spec.2 with ⟨_, _, equal⟩
  rw [equal]
  exact spec.1.2.1

theorem committed_image (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected mode request
      nextHead nextJournal nextImage = some next) :
    next.image = nextImage ∧ next.image ≠ state.image := by
  have spec := committed_spec p contexts evaluators state next owner expected mode request
    nextHead nextJournal nextImage accepted
  rcases spec.2 with ⟨_, _, equal⟩
  rw [equal]
  refine ⟨rfl, ?_⟩
  intro sameImage
  exact spec.1.2.2.2.2.2.2.2.1 (congrArg Image.rootHead sameImage)

theorem committed_image_fields_change (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected mode request
      nextHead nextJournal nextImage = some next) :
    next.image.rootHead ≠ state.image.rootHead ∧ next.image.pair ≠ state.image.pair := by
  have spec := committed_spec p contexts evaluators state next owner expected mode request
    nextHead nextJournal nextImage accepted
  rcases spec.2 with ⟨_, _, equal⟩
  rw [equal]
  exact spec.1.2.2.2.2.2.2.2

theorem committed_witness_revision (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected mode request
      nextHead nextJournal nextImage = some next) :
    next.witness.revision = state.witness.revision + 1 :=
  advanced_revision p.witness contexts evaluators state.witness next.witness request nextHead nextJournal
    (committed_witness_exact p contexts evaluators state next owner expected mode request
      nextHead nextJournal nextImage accepted)

theorem wrong_root_refused (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image) (wrong : owner.identity ≠ p.identity) :
    commit p contexts evaluators state owner expected mode request nextHead nextJournal nextImage = none := by
  have invalid : ¬ RootGuard p state owner expected mode request nextImage :=
    fun valid => wrong valid.2.2.1
  simp only [commit, invalid, if_false]

theorem wrong_stored_root_refused (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image) (wrong : state.identity ≠ p.identity) :
    commit p contexts evaluators state owner expected mode request nextHead nextJournal nextImage = none := by
  have invalid : ¬ RootGuard p state owner expected mode request nextImage :=
    fun valid => wrong valid.2.1
  simp only [commit, invalid, if_false]

theorem stale_epoch_refused (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image) (stale : owner.epoch ≠ state.epoch) :
    commit p contexts evaluators state owner expected mode request nextHead nextJournal nextImage = none := by
  have invalid : ¬ RootGuard p state owner expected mode request nextImage :=
    fun valid => stale valid.2.2.2.1
  simp only [commit, invalid, if_false]

theorem stale_cursor_refused (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image) (stale : expected ≠ cursor state) :
    commit p contexts evaluators state owner expected mode request nextHead nextJournal nextImage = none := by
  have invalid : ¬ RootGuard p state owner expected mode request nextImage :=
    fun valid => stale valid.2.2.2.2.1
  simp only [commit, invalid, if_false]

theorem unchanged_image_refused (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) :
    commit p contexts evaluators state owner expected mode request nextHead nextJournal state.image = none := by
  have invalid : ¬ RootGuard p state owner expected mode request state.image :=
    fun valid => valid.2.2.2.2.2.2.2.1 rfl
  simp only [commit, invalid, if_false]

theorem predecessor_cursor_consumed_once (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner competingOwner : Handle) (expected competingCursor : Cursor)
    (mode competingMode : Mode) (request competing : Request)
    (nextHead nextJournal competingHead competingJournal : String) (nextImage competingImage : Image)
    (accepted : commit p contexts evaluators state owner expected mode request
      nextHead nextJournal nextImage = some next)
    (oldSerial : competingCursor.serial = state.serial) :
    commit p contexts evaluators next competingOwner competingCursor competingMode competing
      competingHead competingJournal competingImage = none := by
  apply stale_cursor_refused
  intro equal
  have serial := congrArg Cursor.serial equal
  have increased := committed_serial p contexts evaluators state next owner expected mode request
    nextHead nextJournal nextImage accepted
  change competingCursor.serial = next.serial at serial
  omega

theorem reopened_epoch_strict (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected .reopen request
      nextHead nextJournal nextImage = some next) : next.epoch = state.epoch + 1 :=
  committed_epoch p contexts evaluators state next owner expected .reopen request
    nextHead nextJournal nextImage accepted

theorem reopened_old_handle_refused (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected .reopen request
      nextHead nextJournal nextImage = some next)
    (laterCursor : Cursor) (laterMode : Mode) (laterRequest : Request)
    (laterHead laterJournal : String) (laterImage : Image) :
    commit p contexts evaluators next owner laterCursor laterMode laterRequest
      laterHead laterJournal laterImage = none := by
  have oldEpoch := (committed_spec p contexts evaluators state next owner expected .reopen request
    nextHead nextJournal nextImage accepted).1.2.2.2.1
  apply stale_epoch_refused
  rw [oldEpoch, reopened_epoch_strict p contexts evaluators state next owner expected request
    nextHead nextJournal nextImage accepted]
  omega

theorem reopened_pending_charges_retained (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected .reopen request
      nextHead nextJournal nextImage = some next) :
    next.witness.authority.pending = state.witness.authority.pending ∧
    Phase17ControllerAuthority.reservedCost next.witness.authority =
      Phase17ControllerAuthority.reservedCost state.witness.authority ∧
    next.witness.authority.liveLease = none ∧ next.witness.journal = state.witness.journal := by
  have kind := (committed_spec p contexts evaluators state next owner expected .reopen request
    nextHead nextJournal nextImage accepted).1.2.2.2.2.2.1
  exact reopened_pending_retained p.witness contexts evaluators state.witness next.witness request
    nextHead nextJournal kind
    (committed_witness_exact p contexts evaluators state next owner expected .reopen request
      nextHead nextJournal nextImage accepted)

theorem reopened_owner_cannot_execute (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (request : Request)
    (nextHead nextJournal token : String) (nextImage : Image) (result : Phase17ControllerAuthority.Completion)
    (accepted : commit p contexts evaluators state owner expected .reopen request
      nextHead nextJournal nextImage = some next) :
    perform p.witness contexts evaluators next.witness (.execute token result) = none := by
  have kind := (committed_spec p contexts evaluators state next owner expected .reopen request
    nextHead nextJournal nextImage accepted).1.2.2.2.2.2.1
  exact Phase17AuthorityWitness.reopened_owner_cannot_execute p.witness contexts evaluators
    state.witness next.witness request nextHead nextJournal token result kind
    (committed_witness_exact p contexts evaluators state next owner expected .reopen request
      nextHead nextJournal nextImage accepted)

structure Receipt where
  identity : String
  epoch : Nat
  cursor : Cursor
  request : String
  deriving DecidableEq

def receipt (state : RootState) (request : String) : Receipt :=
  ⟨state.identity, state.epoch, cursor state, request⟩

/-- Checking an acknowledgement uses the committed root, not a staged image.
    Authentication and the request digest are supplied by the protocol layer. -/
def ReceiptAccepted (state : RootState) (expectedRequest : String) (value : Receipt) : Prop :=
  expectedRequest ≠ "" ∧ value = receipt state expectedRequest

instance receiptAcceptedDecidable (state : RootState) (expectedRequest : String) (value : Receipt) :
    Decidable (ReceiptAccepted state expectedRequest value) := by
  unfold ReceiptAccepted
  infer_instance

theorem accepted_receipt_exact (state : RootState) (expectedRequest : String) (value : Receipt)
    (accepted : ReceiptAccepted state expectedRequest value) :
    value.identity = state.identity ∧ value.epoch = state.epoch ∧
    value.cursor = cursor state ∧ value.request = expectedRequest := by
  rw [accepted.2]
  exact ⟨rfl, rfl, rfl, rfl⟩

theorem wrong_request_receipt_refused (state : RootState) (expectedRequest : String) (value : Receipt)
    (wrong : value.request ≠ expectedRequest) : ¬ ReceiptAccepted state expectedRequest value :=
  fun accepted => wrong (accepted_receipt_exact state expectedRequest value accepted).2.2.2

theorem precommit_receipt_refused (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (state next : RootState)
    (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal requestDigest : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected mode request
      nextHead nextJournal nextImage = some next) :
    ¬ ReceiptAccepted state requestDigest (receipt next requestDigest) := by
  intro received
  have equal := congrArg (fun value : Receipt => value.cursor.serial) received.2
  change next.serial = state.serial at equal
  have incremented := committed_serial p contexts evaluators state next owner expected mode request
    nextHead nextJournal nextImage accepted
  omega

/-- A staging transaction keeps its durable state separate from its uncommitted
    candidate. A crash discards volatile knowledge only. This specifies the
    backend contract and does not prove an operating system implements it. -/
structure Transaction where
  durable : RootState
  staged : Option RootState
  acknowledgement : Option Receipt
  deriving DecidableEq

def begin (state : RootState) (proposal : RootState) : Transaction := ⟨state, some proposal, none⟩
def crash (transaction : Transaction) : Transaction := ⟨transaction.durable, none, none⟩
def afterCommit (state : RootState) : Transaction := ⟨state, none, none⟩

theorem precommit_crash_retains_root (state proposal : RootState) :
    (crash (begin state proposal)).durable = state ∧
    (crash (begin state proposal)).acknowledgement = none := ⟨rfl, rfl⟩

theorem lost_acknowledgement_retains_root (state : RootState) :
    (crash (afterCommit state)).durable = state ∧
    (crash (afterCommit state)).acknowledgement = none := ⟨rfl, rfl⟩

theorem crash_retains_pending_charges (transaction : Transaction) :
    (crash transaction).durable.witness.authority.pending = transaction.durable.witness.authority.pending ∧
    Phase17ControllerAuthority.reservedCost (crash transaction).durable.witness.authority =
      Phase17ControllerAuthority.reservedCost transaction.durable.witness.authority := ⟨rfl, rfl⟩

def initialRoot (p : RootProvision) (journal : String) (image : Image) : RootState :=
  ⟨p.identity, 0, 0, image, initial p.witness journal⟩

inductive Reachable (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (journal : String) (image : Image) : RootState → Prop where
  | initial : Reachable p contexts evaluators journal image (initialRoot p journal image)
  | commit {state next : RootState}
      (prior : Reachable p contexts evaluators journal image state)
      (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
      (nextHead nextJournal : String) (nextImage : Image)
      (accepted : commit p contexts evaluators state owner expected mode request
        nextHead nextJournal nextImage = some next) :
      Reachable p contexts evaluators journal image next

theorem reachable_witness (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (journal : String) (image : Image) (state : RootState)
    (reachable : Reachable p contexts evaluators journal image state) :
    Phase17AuthorityWitness.Reachable p.witness contexts evaluators journal state.witness := by
  induction reachable with
  | initial => exact .initial
  | @commit prior next priorReach owner expected mode request nextHead nextJournal nextImage accepted ih =>
      exact .advance ih request nextHead nextJournal
        (committed_witness_exact p contexts evaluators prior next owner expected mode request
          nextHead nextJournal nextImage accepted)

theorem reachable_serial_matches_witness (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (journal : String) (image : Image) (state : RootState)
    (reachable : Reachable p contexts evaluators journal image state) :
    state.serial = state.witness.revision := by
  induction reachable with
  | initial => rfl
  | @commit prior next priorReach owner expected mode request nextHead nextJournal nextImage accepted ih =>
      rw [committed_serial p contexts evaluators prior next owner expected mode request
        nextHead nextJournal nextImage accepted,
        committed_witness_revision p contexts evaluators prior next owner expected mode request
        nextHead nextJournal nextImage accepted, ih]

theorem reachable_epoch_bounded_by_commits (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (journal : String) (image : Image) (state : RootState)
    (reachable : Reachable p contexts evaluators journal image state) : state.epoch ≤ state.serial := by
  induction reachable with
  | initial => exact Nat.le_refl _
  | @commit prior next priorReach owner expected mode request nextHead nextJournal nextImage accepted ih =>
      rw [committed_serial p contexts evaluators prior next owner expected mode request
        nextHead nextJournal nextImage accepted,
        committed_epoch p contexts evaluators prior next owner expected mode request
        nextHead nextJournal nextImage accepted]
      cases mode <;> simp only [nextEpoch] <;> omega

theorem reachable_sources_consumed_once (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (journal : String) (image : Image) (state : RootState)
    (reachable : Reachable p contexts evaluators journal image state) : state.witness.authority.consumed.Nodup :=
  Phase17AuthorityWitness.reachable_sources_consumed_once p.witness contexts evaluators journal state.witness
    (reachable_witness p contexts evaluators journal image state reachable)

theorem reachable_within_authorized_pool (p : RootProvision) (contexts : Phase17ControllerAuthority.Contexts)
    (evaluators : Phase17ControllerAuthority.Evaluators) (journal : String) (image : Image) (state : RootState)
    (reachable : Reachable p contexts evaluators journal image state) :
    state.witness.authority.reservedAttempts ≤ p.witness.policy.poolAttempts :=
  Phase17AuthorityWitness.reachable_within_pool p.witness contexts evaluators journal state.witness
    (reachable_witness p contexts evaluators journal image state reachable)

theorem reachable_completed_and_pending_accounted (p : RootProvision)
    (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (journal : String) (image : Image) (state : RootState)
    (reachable : Reachable p contexts evaluators journal image state) :
    Phase17ControllerAuthority.completedCost state.witness.authority +
      Phase17ControllerAuthority.pendingCost p.witness.policy state.witness.authority ≤
      Phase17ControllerAuthority.reservedCost state.witness.authority :=
  Phase17AuthorityWitness.reachable_completed_and_pending_accounted p.witness contexts evaluators journal state.witness
    (reachable_witness p contexts evaluators journal image state reachable)

/-- Atomic serialization is a guarantee within one evolving root. Supplying a
    second root with exactly the old state permits the same accepted transition
    there. No rule in this model certifies global uniqueness of physical roots. -/
theorem identical_root_copies_accept_identically (p : RootProvision)
    (contexts : Phase17ControllerAuthority.Contexts) (evaluators : Phase17ControllerAuthority.Evaluators)
    (state next : RootState) (owner : Handle) (expected : Cursor) (mode : Mode) (request : Request)
    (nextHead nextJournal : String) (nextImage : Image)
    (accepted : commit p contexts evaluators state owner expected mode request
      nextHead nextJournal nextImage = some next) :
    ∃ first second : RootState, first = state ∧ second = state ∧
      commit p contexts evaluators first owner expected mode request nextHead nextJournal nextImage = some next ∧
      commit p contexts evaluators second owner expected mode request nextHead nextJournal nextImage = some next :=
  ⟨state, state, rfl, rfl, accepted, accepted⟩

end Phase17DurableAuthority

namespace Phase17DurableAuthorityExamples
open Phase17DurableAuthority
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
-- Exact AK packet SHA256: a8b3e68b777c87a7584d68f536913300d913b70eda1bb86d33dc6497926ee31e
-- Exact inherited AJ packet SHA256: dd7a8197c66cc88beaa31c4c18dac5c88ced3c6cb754421a80bc94abeb552a2a
def firstRequestDigest : String := "b54a4b355aa06b93f2f42c81cdce88b15717589800b78ba416a291cd496e747a"
def firstNativeReceipt : Receipt := ⟨"5d1a7d24e33934ffd2a7c7472c31c15e38d9bc9d5cc49fa4f942d0b38e405dc4", 1, ⟨"5d1a7d24e33934ffd2a7c7472c31c15e38d9bc9d5cc49fa4f942d0b38e405dc4", 1, 2, ⟨"f5a74f27ecdf989837face1cd9d3e6323ab65a32b16aa06aaf08af6a609f4ce4", "33e4777d8ab594180cddfc36eb23dd0284610aab8136d039e868bad90fdf6af1"⟩, 2, "acbad0038d7529df0b8ff3ba7a23bd3f5c8981c7c8f68ab9c31adc1982105720", "9e52ac55aba74d638bb9741d48a7253a73a6b090ce4a7002c69a9581893d4531"⟩, "b54a4b355aa06b93f2f42c81cdce88b15717589800b78ba416a291cd496e747a"⟩
def provision0 : RootProvision := ⟨"5d1a7d24e33934ffd2a7c7472c31c15e38d9bc9d5cc49fa4f942d0b38e405dc4", Phase17AuthorityWitnessExamples.provision0⟩
def image0_0 : Image := ⟨"a89dc9ecc0f63c1a5b42707d087845e5f3dd8e0e95d06b683753ec3f8c3d338c", "44674eb6a51f824a2c6f22100153c6eb9613e0d41e5b7845c935da62220b3546"⟩
def root0_0 : RootState := initialRoot provision0 Phase17AuthorityWitnessExamples.journal0 image0_0
theorem reachable0_0 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 Phase17AuthorityWitnessExamples.journal0 image0_0 root0_0 := .initial
-- Exact retained witness SHA256: e7ade3604a9164bb7be21dd19047c9cb4d8ad40ac55de45d008d2f821a7afd93
-- Exact retained authority SHA256: ede1a83d8e1a0d8642f729d505713c47ad62d515c36ac201576057e8dc886ca6
def image0_1 : Image := ⟨"0cf402d5531390459745dd62939b9611dcbd9f3d6152a56a2be5df0175fedd53", "9cadb7833e8c5e6fcdefcd9a429bb9ae4ea48f86785ec7604a78341d9e7d25bf"⟩
def root0_1 : RootState := installed root0_0 .reopen image0_1 Phase17AuthorityWitnessExamples.witness0_1
theorem guard0_1 : RootGuard provision0 root0_0 (handle root0_0) (cursor root0_0) .reopen Phase17AuthorityWitnessExamples.request0_1 image0_1 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step0_1 : commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_0 (handle root0_0) (cursor root0_0) .reopen Phase17AuthorityWitnessExamples.request0_1
    Phase17AuthorityWitnessExamples.witness0_1.head Phase17AuthorityWitnessExamples.witness0_1.journal image0_1 = some root0_1 :=
  committed_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_0 (handle root0_0) (cursor root0_0) .reopen Phase17AuthorityWitnessExamples.request0_1
    Phase17AuthorityWitnessExamples.witness0_1.head Phase17AuthorityWitnessExamples.witness0_1.journal image0_1 Phase17AuthorityWitnessExamples.witness0_1 guard0_1 Phase17AuthorityWitnessExamples.step0_1
theorem reachable0_1 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    Phase17AuthorityWitnessExamples.journal0 image0_0 root0_1 :=
  .commit reachable0_0 (handle root0_0) (cursor root0_0) .reopen Phase17AuthorityWitnessExamples.request0_1 Phase17AuthorityWitnessExamples.witness0_1.head Phase17AuthorityWitnessExamples.witness0_1.journal image0_1 step0_1
-- Exact retained witness SHA256: 5dfa0995482dfaf9871a66b4986b4bf2d47890e3ac640a15c99bd54132212023
-- Exact retained authority SHA256: c4069899bd2e5eec627522c06d71e90321892ddbab5fc4b83fcbaa879fe681fb
def image0_2 : Image := ⟨"f5a74f27ecdf989837face1cd9d3e6323ab65a32b16aa06aaf08af6a609f4ce4", "33e4777d8ab594180cddfc36eb23dd0284610aab8136d039e868bad90fdf6af1"⟩
def root0_2 : RootState := installed root0_1 .mutation image0_2 Phase17AuthorityWitnessExamples.witness0_2
theorem guard0_2 : RootGuard provision0 root0_1 (handle root0_1) (cursor root0_1) .mutation Phase17AuthorityWitnessExamples.request0_2 image0_2 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step0_2 : commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_1 (handle root0_1) (cursor root0_1) .mutation Phase17AuthorityWitnessExamples.request0_2
    Phase17AuthorityWitnessExamples.witness0_2.head Phase17AuthorityWitnessExamples.witness0_2.journal image0_2 = some root0_2 :=
  committed_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_1 (handle root0_1) (cursor root0_1) .mutation Phase17AuthorityWitnessExamples.request0_2
    Phase17AuthorityWitnessExamples.witness0_2.head Phase17AuthorityWitnessExamples.witness0_2.journal image0_2 Phase17AuthorityWitnessExamples.witness0_2 guard0_2 Phase17AuthorityWitnessExamples.step0_2
theorem reachable0_2 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    Phase17AuthorityWitnessExamples.journal0 image0_0 root0_2 :=
  .commit reachable0_1 (handle root0_1) (cursor root0_1) .mutation Phase17AuthorityWitnessExamples.request0_2 Phase17AuthorityWitnessExamples.witness0_2.head Phase17AuthorityWitnessExamples.witness0_2.journal image0_2 step0_2
-- Exact retained witness SHA256: 02c9a30d2e9b084ab8007947105f1a9ea10caae7a0315291be30c7495c3f5a66
-- Exact retained authority SHA256: 3df43264122c19cf3b4c8b0d1f15f13cf82a95e9e253c9bf6fa2994fa005df73
def image0_3 : Image := ⟨"0eda8b7ccff04a74ab7196d77ed1ab554ff9fdc2c3050a2cd4a3268788023915", "569c5ba7b17daf97d1c2da1ce31a69ac9b1a79cee1e54470d38853aaf1325183"⟩
def root0_3 : RootState := installed root0_2 .mutation image0_3 Phase17AuthorityWitnessExamples.witness0_3
theorem guard0_3 : RootGuard provision0 root0_2 (handle root0_2) (cursor root0_2) .mutation Phase17AuthorityWitnessExamples.request0_3 image0_3 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step0_3 : commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_2 (handle root0_2) (cursor root0_2) .mutation Phase17AuthorityWitnessExamples.request0_3
    Phase17AuthorityWitnessExamples.witness0_3.head Phase17AuthorityWitnessExamples.witness0_3.journal image0_3 = some root0_3 :=
  committed_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_2 (handle root0_2) (cursor root0_2) .mutation Phase17AuthorityWitnessExamples.request0_3
    Phase17AuthorityWitnessExamples.witness0_3.head Phase17AuthorityWitnessExamples.witness0_3.journal image0_3 Phase17AuthorityWitnessExamples.witness0_3 guard0_3 Phase17AuthorityWitnessExamples.step0_3
theorem reachable0_3 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    Phase17AuthorityWitnessExamples.journal0 image0_0 root0_3 :=
  .commit reachable0_2 (handle root0_2) (cursor root0_2) .mutation Phase17AuthorityWitnessExamples.request0_3 Phase17AuthorityWitnessExamples.witness0_3.head Phase17AuthorityWitnessExamples.witness0_3.journal image0_3 step0_3
-- Exact retained witness SHA256: fc6025028d023548a253d2832b225ab0f0225e55c8a3746ae6741017d99d90c3
-- Exact retained authority SHA256: 3df43264122c19cf3b4c8b0d1f15f13cf82a95e9e253c9bf6fa2994fa005df73
def image0_4 : Image := ⟨"72bfb3f663a3d28361a659dab645ee95caec60cd390b0723a479212bccbdcf44", "8d02fa1792493e033f0ad3f4f5a945800e172db0b43889343491d53e12fbfeb7"⟩
def root0_4 : RootState := installed root0_3 .reopen image0_4 Phase17AuthorityWitnessExamples.witness0_4
theorem guard0_4 : RootGuard provision0 root0_3 (handle root0_3) (cursor root0_3) .reopen Phase17AuthorityWitnessExamples.request0_4 image0_4 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step0_4 : commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_3 (handle root0_3) (cursor root0_3) .reopen Phase17AuthorityWitnessExamples.request0_4
    Phase17AuthorityWitnessExamples.witness0_4.head Phase17AuthorityWitnessExamples.witness0_4.journal image0_4 = some root0_4 :=
  committed_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_3 (handle root0_3) (cursor root0_3) .reopen Phase17AuthorityWitnessExamples.request0_4
    Phase17AuthorityWitnessExamples.witness0_4.head Phase17AuthorityWitnessExamples.witness0_4.journal image0_4 Phase17AuthorityWitnessExamples.witness0_4 guard0_4 Phase17AuthorityWitnessExamples.step0_4
theorem reachable0_4 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    Phase17AuthorityWitnessExamples.journal0 image0_0 root0_4 :=
  .commit reachable0_3 (handle root0_3) (cursor root0_3) .reopen Phase17AuthorityWitnessExamples.request0_4 Phase17AuthorityWitnessExamples.witness0_4.head Phase17AuthorityWitnessExamples.witness0_4.journal image0_4 step0_4
-- Exact retained witness SHA256: 6d8bd3ceeaf08e17aa53e7446d82fff7716f274b488e404b3081bb32efa75d91
-- Exact retained authority SHA256: ddce0d7c937130585edda1e6cecb763b8621542144efaaf32d259393df66cdac
def image0_5 : Image := ⟨"8122b3cc53af3e8a107c95d1cd044a9e991cc8bd7fb2056497c8f8ca6d311113", "ad5d35f2950497693c7cbd06db72ab5824477a6e06f65af3fc218ad0b7e485e1"⟩
def root0_5 : RootState := installed root0_4 .mutation image0_5 Phase17AuthorityWitnessExamples.witness0_5
theorem guard0_5 : RootGuard provision0 root0_4 (handle root0_4) (cursor root0_4) .mutation Phase17AuthorityWitnessExamples.request0_5 image0_5 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step0_5 : commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_4 (handle root0_4) (cursor root0_4) .mutation Phase17AuthorityWitnessExamples.request0_5
    Phase17AuthorityWitnessExamples.witness0_5.head Phase17AuthorityWitnessExamples.witness0_5.journal image0_5 = some root0_5 :=
  committed_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_4 (handle root0_4) (cursor root0_4) .mutation Phase17AuthorityWitnessExamples.request0_5
    Phase17AuthorityWitnessExamples.witness0_5.head Phase17AuthorityWitnessExamples.witness0_5.journal image0_5 Phase17AuthorityWitnessExamples.witness0_5 guard0_5 Phase17AuthorityWitnessExamples.step0_5
theorem reachable0_5 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    Phase17AuthorityWitnessExamples.journal0 image0_0 root0_5 :=
  .commit reachable0_4 (handle root0_4) (cursor root0_4) .mutation Phase17AuthorityWitnessExamples.request0_5 Phase17AuthorityWitnessExamples.witness0_5.head Phase17AuthorityWitnessExamples.witness0_5.journal image0_5 step0_5
-- Exact retained witness SHA256: dec99bf6792d103918a42c19b9c4a120f17c76bedf76865a3f0e659b734870b2
-- Exact retained authority SHA256: a1700ccb335167453112d40f58d2ad80099422f44c6a3dfb613acc2af92d3005
def image0_6 : Image := ⟨"11f04a6354ca992d90fd924eaadf6790a9a0aa875b4bdd1ecc61be705c5fffd0", "71f075b5b568ecea9721c6fb228ae3b46cc80b4c2419796a07b440749fc4d628"⟩
def root0_6 : RootState := installed root0_5 .mutation image0_6 Phase17AuthorityWitnessExamples.witness0_6
theorem guard0_6 : RootGuard provision0 root0_5 (handle root0_5) (cursor root0_5) .mutation Phase17AuthorityWitnessExamples.request0_6 image0_6 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step0_6 : commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_5 (handle root0_5) (cursor root0_5) .mutation Phase17AuthorityWitnessExamples.request0_6
    Phase17AuthorityWitnessExamples.witness0_6.head Phase17AuthorityWitnessExamples.witness0_6.journal image0_6 = some root0_6 :=
  committed_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_5 (handle root0_5) (cursor root0_5) .mutation Phase17AuthorityWitnessExamples.request0_6
    Phase17AuthorityWitnessExamples.witness0_6.head Phase17AuthorityWitnessExamples.witness0_6.journal image0_6 Phase17AuthorityWitnessExamples.witness0_6 guard0_6 Phase17AuthorityWitnessExamples.step0_6
theorem reachable0_6 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    Phase17AuthorityWitnessExamples.journal0 image0_0 root0_6 :=
  .commit reachable0_5 (handle root0_5) (cursor root0_5) .mutation Phase17AuthorityWitnessExamples.request0_6 Phase17AuthorityWitnessExamples.witness0_6.head Phase17AuthorityWitnessExamples.witness0_6.journal image0_6 step0_6
-- Exact retained witness SHA256: 68e8f08fc7e56bcf2276b9d560c7682070368b61e8f3226f9337f2421aaf421c
-- Exact retained authority SHA256: 6838f47a733644af060d8befa5ef670eb3bab988ffc556580a73a3b004a28cde
def image0_7 : Image := ⟨"a0f135aa84b0536f77757dad27e51bbea6cebecafde74cd0ded38448349dd1df", "9164436bf489932dd657bb0febffd373619cbcfc291d7e88b79e2411fe4ccd97"⟩
def root0_7 : RootState := installed root0_6 .mutation image0_7 Phase17AuthorityWitnessExamples.witness0_7
theorem guard0_7 : RootGuard provision0 root0_6 (handle root0_6) (cursor root0_6) .mutation Phase17AuthorityWitnessExamples.request0_7 image0_7 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step0_7 : commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_6 (handle root0_6) (cursor root0_6) .mutation Phase17AuthorityWitnessExamples.request0_7
    Phase17AuthorityWitnessExamples.witness0_7.head Phase17AuthorityWitnessExamples.witness0_7.journal image0_7 = some root0_7 :=
  committed_construct provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0 root0_6 (handle root0_6) (cursor root0_6) .mutation Phase17AuthorityWitnessExamples.request0_7
    Phase17AuthorityWitnessExamples.witness0_7.head Phase17AuthorityWitnessExamples.witness0_7.journal image0_7 Phase17AuthorityWitnessExamples.witness0_7 guard0_7 Phase17AuthorityWitnessExamples.step0_7
theorem reachable0_7 : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    Phase17AuthorityWitnessExamples.journal0 image0_0 root0_7 :=
  .commit reachable0_6 (handle root0_6) (cursor root0_6) .mutation Phase17AuthorityWitnessExamples.request0_7 Phase17AuthorityWitnessExamples.witness0_7.head Phase17AuthorityWitnessExamples.witness0_7.journal image0_7 step0_7
theorem case_shared_two_sources : Reachable provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
    Phase17AuthorityWitnessExamples.journal0 image0_0 root0_7 ∧ root0_7.serial = 7 ∧
    root0_7.epoch = 2 ∧ root0_7.witness = Phase17AuthorityWitnessExamples.witness0_7 :=
  ⟨reachable0_7, rfl, rfl, rfl⟩
def provision1 : RootProvision := ⟨"73c5355fa809c299a54ca70eab24e2645d8c9611ddca063a5005e073cd7bc5bd", Phase17AuthorityWitnessExamples.provision1⟩
def image1_0 : Image := ⟨"f796d3054a60f7a8b29bb76e73aa95c736f41445714021e65548fef1b1575ab4", "5ab68ae3d3b4c48c0c76bbabc41314f5142bb8243869c5bd24e9ed874882c02a"⟩
def root1_0 : RootState := initialRoot provision1 Phase17AuthorityWitnessExamples.journal1 image1_0
theorem reachable1_0 : Reachable provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4 Phase17AuthorityWitnessExamples.journal1 image1_0 root1_0 := .initial
-- Exact retained witness SHA256: 0816663a7489f0a282e3058574d635311a506fe63678b5b426a908fda0abf795
-- Exact retained authority SHA256: 3d0007b1a9ec5551737c88a448941a82a568b4c481ebbb910641ee8765928d27
def image1_1 : Image := ⟨"a64dd5a27cec7ca193214faafc310c3e10aa8200fbed89ff9687bd13164eba0a", "29338f7b5e0a656345814eabae1114a03231627ac0617c66e78ed89b3730221c"⟩
def root1_1 : RootState := installed root1_0 .reopen image1_1 Phase17AuthorityWitnessExamples.witness1_1
theorem guard1_1 : RootGuard provision1 root1_0 (handle root1_0) (cursor root1_0) .reopen Phase17AuthorityWitnessExamples.request1_1 image1_1 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step1_1 : commit provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4 root1_0 (handle root1_0) (cursor root1_0) .reopen Phase17AuthorityWitnessExamples.request1_1
    Phase17AuthorityWitnessExamples.witness1_1.head Phase17AuthorityWitnessExamples.witness1_1.journal image1_1 = some root1_1 :=
  committed_construct provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4 root1_0 (handle root1_0) (cursor root1_0) .reopen Phase17AuthorityWitnessExamples.request1_1
    Phase17AuthorityWitnessExamples.witness1_1.head Phase17AuthorityWitnessExamples.witness1_1.journal image1_1 Phase17AuthorityWitnessExamples.witness1_1 guard1_1 Phase17AuthorityWitnessExamples.step1_1
theorem reachable1_1 : Reachable provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    Phase17AuthorityWitnessExamples.journal1 image1_0 root1_1 :=
  .commit reachable1_0 (handle root1_0) (cursor root1_0) .reopen Phase17AuthorityWitnessExamples.request1_1 Phase17AuthorityWitnessExamples.witness1_1.head Phase17AuthorityWitnessExamples.witness1_1.journal image1_1 step1_1
-- Exact retained witness SHA256: 39ae584cb6808f84da6bdb0a9ca263d746c4137c1651cf49fc99e259a8cb9fa4
-- Exact retained authority SHA256: f2c4c404f070b916e3a50bc879d1953d0771ccd3c6e36d2a2dec295ded56171b
def image1_2 : Image := ⟨"369968505007873e10ff7ba83f64365455434b7b994bd6d4e2e970c27335a9ab", "6c7f3a2515eebdbe6996980be36de38565b8951897c159e954a6ecfaf3098a1b"⟩
def root1_2 : RootState := installed root1_1 .mutation image1_2 Phase17AuthorityWitnessExamples.witness1_2
theorem guard1_2 : RootGuard provision1 root1_1 (handle root1_1) (cursor root1_1) .mutation Phase17AuthorityWitnessExamples.request1_2 image1_2 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step1_2 : commit provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4 root1_1 (handle root1_1) (cursor root1_1) .mutation Phase17AuthorityWitnessExamples.request1_2
    Phase17AuthorityWitnessExamples.witness1_2.head Phase17AuthorityWitnessExamples.witness1_2.journal image1_2 = some root1_2 :=
  committed_construct provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4 root1_1 (handle root1_1) (cursor root1_1) .mutation Phase17AuthorityWitnessExamples.request1_2
    Phase17AuthorityWitnessExamples.witness1_2.head Phase17AuthorityWitnessExamples.witness1_2.journal image1_2 Phase17AuthorityWitnessExamples.witness1_2 guard1_2 Phase17AuthorityWitnessExamples.step1_2
theorem reachable1_2 : Reachable provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    Phase17AuthorityWitnessExamples.journal1 image1_0 root1_2 :=
  .commit reachable1_1 (handle root1_1) (cursor root1_1) .mutation Phase17AuthorityWitnessExamples.request1_2 Phase17AuthorityWitnessExamples.witness1_2.head Phase17AuthorityWitnessExamples.witness1_2.journal image1_2 step1_2
-- Exact retained witness SHA256: 85027d905283f8f58206fe7ab7017b9bf3f686349e676050b69ca14b96131433
-- Exact retained authority SHA256: f2c4c404f070b916e3a50bc879d1953d0771ccd3c6e36d2a2dec295ded56171b
def image1_3 : Image := ⟨"59159ea3a631876b608794e28619a524487534fba892ae006a2156f713795972", "7b322babd3896ca641d36216b254310fe60add1ed0105dbf6c14cc37a6ff52e1"⟩
def root1_3 : RootState := installed root1_2 .reopen image1_3 Phase17AuthorityWitnessExamples.witness1_3
theorem guard1_3 : RootGuard provision1 root1_2 (handle root1_2) (cursor root1_2) .reopen Phase17AuthorityWitnessExamples.request1_3 image1_3 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step1_3 : commit provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4 root1_2 (handle root1_2) (cursor root1_2) .reopen Phase17AuthorityWitnessExamples.request1_3
    Phase17AuthorityWitnessExamples.witness1_3.head Phase17AuthorityWitnessExamples.witness1_3.journal image1_3 = some root1_3 :=
  committed_construct provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4 root1_2 (handle root1_2) (cursor root1_2) .reopen Phase17AuthorityWitnessExamples.request1_3
    Phase17AuthorityWitnessExamples.witness1_3.head Phase17AuthorityWitnessExamples.witness1_3.journal image1_3 Phase17AuthorityWitnessExamples.witness1_3 guard1_3 Phase17AuthorityWitnessExamples.step1_3
theorem reachable1_3 : Reachable provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    Phase17AuthorityWitnessExamples.journal1 image1_0 root1_3 :=
  .commit reachable1_2 (handle root1_2) (cursor root1_2) .reopen Phase17AuthorityWitnessExamples.request1_3 Phase17AuthorityWitnessExamples.witness1_3.head Phase17AuthorityWitnessExamples.witness1_3.journal image1_3 step1_3
theorem case_interrupted_reservation : Reachable provision1 Phase17ControllerAuthorityExamples.contexts4 Phase17ControllerAuthorityExamples.evaluators4
    Phase17AuthorityWitnessExamples.journal1 image1_0 root1_3 ∧ root1_3.serial = 3 ∧
    root1_3.epoch = 2 ∧ root1_3.witness = Phase17AuthorityWitnessExamples.witness1_3 :=
  ⟨reachable1_3, rfl, rfl, rfl⟩
def provision2 : RootProvision := ⟨"85a9fcac97a848e50ba9fa3dbdcbc2260373dba529a50065a5869bf5ff4e5ffa", Phase17AuthorityWitnessExamples.provision2⟩
def image2_0 : Image := ⟨"6912b9f4f419f62f0098d1f41368653bc21f05e70d298c4957bc61117d9df524", "eff03dfd470b625cb7b632f865e7284727cd98fa35521b9abf66e244e65daf42"⟩
def root2_0 : RootState := initialRoot provision2 Phase17AuthorityWitnessExamples.journal2 image2_0
theorem reachable2_0 : Reachable provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1 Phase17AuthorityWitnessExamples.journal2 image2_0 root2_0 := .initial
-- Exact retained witness SHA256: 23b1037ff08ee67d6a7360871aad9d698e0caccfeeee2881b7ef956eb29cf6f8
-- Exact retained authority SHA256: 93c160cde99d06bfc75cf5d8b5144c8664f0a15d759135c087ebd4e224a27190
def image2_1 : Image := ⟨"a693565b2b50edf6b463afca49e9f88577bf6f62dc5abbfed8d40c63e1de6c77", "0f3c808a849e9a77adaa95f86c6084437f62640aefd916b936afbdc3f5636a1e"⟩
def root2_1 : RootState := installed root2_0 .reopen image2_1 Phase17AuthorityWitnessExamples.witness2_1
theorem guard2_1 : RootGuard provision2 root2_0 (handle root2_0) (cursor root2_0) .reopen Phase17AuthorityWitnessExamples.request2_1 image2_1 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step2_1 : commit provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1 root2_0 (handle root2_0) (cursor root2_0) .reopen Phase17AuthorityWitnessExamples.request2_1
    Phase17AuthorityWitnessExamples.witness2_1.head Phase17AuthorityWitnessExamples.witness2_1.journal image2_1 = some root2_1 :=
  committed_construct provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1 root2_0 (handle root2_0) (cursor root2_0) .reopen Phase17AuthorityWitnessExamples.request2_1
    Phase17AuthorityWitnessExamples.witness2_1.head Phase17AuthorityWitnessExamples.witness2_1.journal image2_1 Phase17AuthorityWitnessExamples.witness2_1 guard2_1 Phase17AuthorityWitnessExamples.step2_1
theorem reachable2_1 : Reachable provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    Phase17AuthorityWitnessExamples.journal2 image2_0 root2_1 :=
  .commit reachable2_0 (handle root2_0) (cursor root2_0) .reopen Phase17AuthorityWitnessExamples.request2_1 Phase17AuthorityWitnessExamples.witness2_1.head Phase17AuthorityWitnessExamples.witness2_1.journal image2_1 step2_1
-- Exact retained witness SHA256: 0cbbdb5474b0f61dfbcec4761b5185533bc309287f2b504daf6b8958b64f7ed2
-- Exact retained authority SHA256: 71cf477aeebc019f6c0928ede5c6accb94a4820bf61853ae2512d1928b0fc6e3
def image2_2 : Image := ⟨"5ee199c0ab2ce42ca038070cd12fdd528fcf479fcb8df39a45f68c2104885c87", "a46c7740afff1003cc810ec8837c9bfd00aee1405ea94878b53256d6a983ec8c"⟩
def root2_2 : RootState := installed root2_1 .mutation image2_2 Phase17AuthorityWitnessExamples.witness2_2
theorem guard2_2 : RootGuard provision2 root2_1 (handle root2_1) (cursor root2_1) .mutation Phase17AuthorityWitnessExamples.request2_2 image2_2 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step2_2 : commit provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1 root2_1 (handle root2_1) (cursor root2_1) .mutation Phase17AuthorityWitnessExamples.request2_2
    Phase17AuthorityWitnessExamples.witness2_2.head Phase17AuthorityWitnessExamples.witness2_2.journal image2_2 = some root2_2 :=
  committed_construct provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1 root2_1 (handle root2_1) (cursor root2_1) .mutation Phase17AuthorityWitnessExamples.request2_2
    Phase17AuthorityWitnessExamples.witness2_2.head Phase17AuthorityWitnessExamples.witness2_2.journal image2_2 Phase17AuthorityWitnessExamples.witness2_2 guard2_2 Phase17AuthorityWitnessExamples.step2_2
theorem reachable2_2 : Reachable provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    Phase17AuthorityWitnessExamples.journal2 image2_0 root2_2 :=
  .commit reachable2_1 (handle root2_1) (cursor root2_1) .mutation Phase17AuthorityWitnessExamples.request2_2 Phase17AuthorityWitnessExamples.witness2_2.head Phase17AuthorityWitnessExamples.witness2_2.journal image2_2 step2_2
-- Exact retained witness SHA256: 076b62fed511d1e2642eafe46ac9ea57f7baa85f6cde7ec4688936d697fc12f7
-- Exact retained authority SHA256: 48c1320044677064ceb59d36191ca417ed67f4dcfc6093ac5c2a1d071caacf72
def image2_3 : Image := ⟨"6f30394ac452f9b207564f7b522300641863558ed1f31b86be39f2d8a91d0c92", "2f250f670e7403275dc27c83bbf521ad3cdd2015481e32c7e372d94866316b51"⟩
def root2_3 : RootState := installed root2_2 .mutation image2_3 Phase17AuthorityWitnessExamples.witness2_3
theorem guard2_3 : RootGuard provision2 root2_2 (handle root2_2) (cursor root2_2) .mutation Phase17AuthorityWitnessExamples.request2_3 image2_3 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step2_3 : commit provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1 root2_2 (handle root2_2) (cursor root2_2) .mutation Phase17AuthorityWitnessExamples.request2_3
    Phase17AuthorityWitnessExamples.witness2_3.head Phase17AuthorityWitnessExamples.witness2_3.journal image2_3 = some root2_3 :=
  committed_construct provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1 root2_2 (handle root2_2) (cursor root2_2) .mutation Phase17AuthorityWitnessExamples.request2_3
    Phase17AuthorityWitnessExamples.witness2_3.head Phase17AuthorityWitnessExamples.witness2_3.journal image2_3 Phase17AuthorityWitnessExamples.witness2_3 guard2_3 Phase17AuthorityWitnessExamples.step2_3
theorem reachable2_3 : Reachable provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    Phase17AuthorityWitnessExamples.journal2 image2_0 root2_3 :=
  .commit reachable2_2 (handle root2_2) (cursor root2_2) .mutation Phase17AuthorityWitnessExamples.request2_3 Phase17AuthorityWitnessExamples.witness2_3.head Phase17AuthorityWitnessExamples.witness2_3.journal image2_3 step2_3
-- Exact retained witness SHA256: ce4fe33e0955074b288c9112088d6d868acbae0782aa7a5d4619b7267f5ba06f
-- Exact retained authority SHA256: c78cd30339a8d14a5035afc1028c3ef5c29fa36396c666914aaf79393d7be826
def image2_4 : Image := ⟨"7796032d7268a4aa528523ef9cbb29b970c9b8f6549a3cc72df5576e342ba616", "a7a6ef89ff2cb6d99bfc90c01958f9cfe7a207a626f5af2abe3e4bcc8d2d76e9"⟩
def root2_4 : RootState := installed root2_3 .mutation image2_4 Phase17AuthorityWitnessExamples.witness2_4
theorem guard2_4 : RootGuard provision2 root2_3 (handle root2_3) (cursor root2_3) .mutation Phase17AuthorityWitnessExamples.request2_4 image2_4 :=
  ⟨by decide +kernel, rfl, rfl, rfl, rfl, by decide +kernel,
    ⟨by decide +kernel, by decide +kernel⟩, ⟨by decide +kernel, by decide +kernel⟩⟩
theorem step2_4 : commit provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1 root2_3 (handle root2_3) (cursor root2_3) .mutation Phase17AuthorityWitnessExamples.request2_4
    Phase17AuthorityWitnessExamples.witness2_4.head Phase17AuthorityWitnessExamples.witness2_4.journal image2_4 = some root2_4 :=
  committed_construct provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1 root2_3 (handle root2_3) (cursor root2_3) .mutation Phase17AuthorityWitnessExamples.request2_4
    Phase17AuthorityWitnessExamples.witness2_4.head Phase17AuthorityWitnessExamples.witness2_4.journal image2_4 Phase17AuthorityWitnessExamples.witness2_4 guard2_4 Phase17AuthorityWitnessExamples.step2_4
theorem reachable2_4 : Reachable provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    Phase17AuthorityWitnessExamples.journal2 image2_0 root2_4 :=
  .commit reachable2_3 (handle root2_3) (cursor root2_3) .mutation Phase17AuthorityWitnessExamples.request2_4 Phase17AuthorityWitnessExamples.witness2_4.head Phase17AuthorityWitnessExamples.witness2_4.journal image2_4 step2_4
theorem case_aggregate_denial : Reachable provision2 Phase17ControllerAuthorityExamples.contexts1 Phase17ControllerAuthorityExamples.evaluators1
    Phase17AuthorityWitnessExamples.journal2 image2_0 root2_4 ∧ root2_4.serial = 4 ∧
    root2_4.epoch = 1 ∧ root2_4.witness = Phase17AuthorityWitnessExamples.witness2_4 :=
  ⟨reachable2_4, rfl, rfl, rfl⟩

theorem main_exact_witness_projection : root0_7.witness = Phase17AuthorityWitnessExamples.witness0_7 := rfl

theorem main_exact_reservation : Phase17ControllerAuthority.reservedCost root0_7.witness.authority = 7168 :=
  Phase17AuthorityWitnessExamples.main_exact_reservation.2

theorem main_actual_reference_work : Phase17ControllerAuthority.completedCost root0_7.witness.authority = 1008 :=
  Phase17AuthorityWitnessExamples.main_actual_reference_work

theorem main_completed_and_pending_accounted :
    Phase17ControllerAuthority.completedCost root0_7.witness.authority +
      Phase17ControllerAuthority.pendingCost provision0.witness.policy root0_7.witness.authority ≤
      Phase17ControllerAuthority.reservedCost root0_7.witness.authority :=
  reachable_completed_and_pending_accounted provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 Phase17AuthorityWitnessExamples.journal0 image0_0 root0_7 reachable0_7

theorem main_sources_consumed_once : root0_7.witness.authority.consumed.Nodup :=
  reachable_sources_consumed_once provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 Phase17AuthorityWitnessExamples.journal0 image0_0 root0_7 reachable0_7

theorem main_serial_and_epoch : root0_7.serial = 7 ∧ root0_7.epoch = 2 := ⟨rfl, rfl⟩

theorem first_committed_reservation :
    Phase17AuthorityWitness.advance provision0.witness Phase17ControllerAuthorityExamples.contexts0
      Phase17ControllerAuthorityExamples.evaluators0 root0_1.witness
      Phase17AuthorityWitnessExamples.request0_2 root0_2.witness.head root0_2.witness.journal =
      some root0_2.witness := Phase17AuthorityWitnessExamples.step0_2

theorem competing_former_cursor_refused :
    commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      root0_2 (handle root0_2) (cursor root0_1) .mutation Phase17AuthorityWitnessExamples.request0_2
      "competing-head" "competing-journal" ⟨"competing-root", "competing-pair"⟩ = none := by
  apply stale_cursor_refused
  decide +kernel

theorem reopened_former_handle_refused :
    commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      root0_4 (handle root0_3) (cursor root0_4) .mutation Phase17AuthorityWitnessExamples.request0_5
      root0_5.witness.head root0_5.witness.journal image0_5 = none := by
  apply stale_epoch_refused
  decide +kernel

theorem first_reservation_not_acknowledged_before_commit :
    ¬ ReceiptAccepted root0_1 firstRequestDigest firstNativeReceipt :=
  precommit_receipt_refused provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 root0_1 root0_2 (handle root0_1) (cursor root0_1)
    .mutation Phase17AuthorityWitnessExamples.request0_2 root0_2.witness.head root0_2.witness.journal
    firstRequestDigest image0_2 step0_2

theorem first_committed_receipt_bound :
    ReceiptAccepted root0_2 firstRequestDigest firstNativeReceipt :=
  ⟨by decide +kernel, rfl⟩

theorem old_receipt_is_not_current :
    ¬ ReceiptAccepted root0_3 firstRequestDigest firstNativeReceipt := by
  decide +kernel

theorem pending_reopen_retains_charge :
    root1_3.witness.authority.pending = some Phase17ControllerAuthorityExamples.lease4_0 ∧
    Phase17ControllerAuthority.reservedCost root1_3.witness.authority = 3584 ∧
    root1_3.witness.owner = none ∧ root1_3.epoch = 2 := by decide +kernel

theorem pending_reopen_cannot_execute (owner : String) (result : Phase17ControllerAuthority.Completion) :
    Phase17AuthorityWitness.perform provision1.witness Phase17ControllerAuthorityExamples.contexts4
      Phase17ControllerAuthorityExamples.evaluators4 root1_3.witness (.execute owner result) = none :=
  Phase17AuthorityWitnessExamples.pending_reopen_cannot_execute owner result

theorem precommit_crash_keeps_pending_reservation :
    (crash (begin root1_2 root1_3)).durable = root1_2 ∧
    Phase17ControllerAuthority.reservedCost (crash (begin root1_2 root1_3)).durable.witness.authority = 3584 :=
  ⟨rfl, by decide +kernel⟩

theorem lost_ack_keeps_committed_reservation :
    (crash (afterCommit root1_2)).durable = root1_2 ∧
    Phase17ControllerAuthority.reservedCost (crash (afterCommit root1_2)).durable.witness.authority = 3584 :=
  ⟨rfl, by decide +kernel⟩

theorem aggregate_denial_keeps_charge :
    Phase17ControllerAuthority.reservedCost root2_4.witness.authority = 3584 ∧
    root2_4.witness.authority.halted = true ∧ root2_4.epoch = 1 := by decide +kernel

theorem joint_root_rollback_is_outside_guarantee :
    commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
      root0_1 (handle root0_1) (cursor root0_1) .mutation Phase17AuthorityWitnessExamples.request0_2
      root0_2.witness.head root0_2.witness.journal image0_2 ≠ none := by
  have accepted : commit provision0 Phase17ControllerAuthorityExamples.contexts0
      Phase17ControllerAuthorityExamples.evaluators0 root0_1 (handle root0_1) (cursor root0_1)
      .mutation Phase17AuthorityWitnessExamples.request0_2 root0_2.witness.head
      root0_2.witness.journal image0_2 = some root0_2 := step0_2
  rw [accepted]
  exact Option.some_ne_none _

theorem root_cloning_is_outside_guarantee :
    ∃ first second : RootState, first = root0_1 ∧ second = root0_1 ∧
      commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
        first (handle root0_1) (cursor root0_1) .mutation Phase17AuthorityWitnessExamples.request0_2
        root0_2.witness.head root0_2.witness.journal image0_2 = some root0_2 ∧
      commit provision0 Phase17ControllerAuthorityExamples.contexts0 Phase17ControllerAuthorityExamples.evaluators0
        second (handle root0_1) (cursor root0_1) .mutation Phase17AuthorityWitnessExamples.request0_2
        root0_2.witness.head root0_2.witness.journal image0_2 = some root0_2 :=
  identical_root_copies_accept_identically provision0 Phase17ControllerAuthorityExamples.contexts0
    Phase17ControllerAuthorityExamples.evaluators0 root0_1 root0_2 (handle root0_1) (cursor root0_1)
    .mutation Phase17AuthorityWitnessExamples.request0_2 root0_2.witness.head root0_2.witness.journal image0_2 step0_2

end Phase17DurableAuthorityExamples
