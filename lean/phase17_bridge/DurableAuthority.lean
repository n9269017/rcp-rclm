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
