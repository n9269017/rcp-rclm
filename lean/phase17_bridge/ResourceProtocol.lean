/- Phase 17AA: the selected resource journal's typed admission and completion
   protocol. Event hashes are checked as structural links and opaque identities.
   Computing those hashes, authenticating the external head, durable appends,
   locking and execution of the recorded work remain external obligations. -/
namespace Phase17ResourceProtocol

open Phase17Routing

def maxNatural : Nat := 9223372036854775807
def maxEvents : Nat := 4096
def zeroHead : String := "0000000000000000000000000000000000000000000000000000000000000000"

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
abbrev Usage.Bounded (u : Usage) : Prop :=
  u.candidates ≤ maxNatural ∧ u.vectors ≤ maxNatural ∧
  u.inputs ≤ maxNatural ∧ u.outputs ≤ maxNatural
abbrev Usage.LE (a b : Usage) : Prop :=
  a.candidates ≤ b.candidates ∧ a.vectors ≤ b.vectors ∧
  a.inputs ≤ b.inputs ∧ a.outputs ≤ b.outputs
def charge : Phase17Resource.Kind → Usage
  | .candidate => ⟨1, 0, 0, 0⟩
  | .vector => ⟨0, 1, 4, 4⟩
def tally (ks : List Phase17Resource.Kind) : Usage :=
  ⟨Phase17Resource.counter ks 0, Phase17Resource.counter ks 1,
    Phase17Resource.counter ks 2, Phase17Resource.counter ks 3⟩

structure Policy where
  limits : Usage
  costLimit : Nat
  deriving DecidableEq

abbrev Policy.Valid (p : Policy) : Prop :=
  p.limits.Bounded ∧ p.costLimit ≤ maxNatural ∧ p.limits.cost ≤ maxNatural
abbrev Policy.Fits (p : Policy) (u : Usage) : Prop :=
  u.LE p.limits ∧ u.cost ≤ p.costLimit

structure Binding where
  predecessor : String
  candidate : String
  transcript : String
  verifier : String
  deriving DecidableEq

def digestValid (s : String) : Bool :=
  decide (s.toList.length = 64) && s.toList.all (fun c =>
    decide (('0' ≤ c ∧ c ≤ '9') ∨ ('a' ≤ c ∧ c ≤ 'f')))
abbrev Binding.Valid (b : Binding) : Prop :=
  digestValid b.predecessor = true ∧ digestValid b.candidate = true ∧
  digestValid b.transcript = true ∧ digestValid b.verifier = true
def identityValid (s : String) : Bool :=
  decide (0 < s.toList.length ∧ s.toList.length ≤ 96) &&
    s.toList.all (fun c => decide (('A' ≤ c ∧ c ≤ 'Z') ∨
      ('a' ≤ c ∧ c ≤ 'z') ∨ ('0' ≤ c ∧ c ≤ '9') ∨
      c = ':' ∨ c = '_' ∨ c = '-'))

structure Operation where
  kind : Phase17Resource.Kind
  identity : String
  inputDigest : String
  amount : Usage
  deriving DecidableEq

abbrev Operation.Valid (o : Operation) : Prop :=
  identityValid o.identity = true ∧ digestValid o.inputDigest = true ∧
  o.amount = charge o.kind

inductive Status where
  | new | open | pending | sealed | resourceExhausted | safetyHalt | externalStop
  deriving DecidableEq

inductive Body where
  | open (binding : Binding) (policy : Policy)
  | reserve (operation : Operation) (spentAfter : Usage)
  | exhausted (operation : Operation) (reason : String)
  | result (reservation : String) (ok : Bool) (resultDigest errorCode : Option String)
      (elapsed : Nat)
  | seal
  | stop
  deriving DecidableEq

structure Event where
  index : Nat
  previous : String
  hash : String
  body : Body
  deriving DecidableEq

structure State where
  head : String
  count : Nat
  spent : Usage
  status : Status
  pending : Option String
  operationIds : List String
  charges : List Phase17Resource.Kind
  deriving DecidableEq

def initial : State := ⟨zeroHead, 0, Usage.zero, .new, none, [], []⟩

abbrev ResultShape (ok : Bool) (resultDigest errorCode : Option String) : Prop :=
  if ok then
    (∃ digest, resultDigest = some digest ∧ digestValid digest = true) ∧ errorCode = none
  else resultDigest = none ∧
    (errorCode = some "operation_failed" ∨ errorCode = some "interrupted")

-- A bounded option predicate avoids a classical decision procedure for strings.
def resultShape (ok : Bool) (resultDigest errorCode : Option String) : Bool :=
  match ok, resultDigest, errorCode with
  | true, some digest, none => digestValid digest
  | false, none, some error => decide (error = "operation_failed" ∨ error = "interrupted")
  | _, _, _ => false

abbrev BodyAllowed (b : Binding) (p : Policy) (s : State) (e : Event) : Prop :=
  match e.body with
  | .open binding policy =>
      s = initial ∧ binding = b ∧ policy = p ∧ b.Valid ∧ p.Valid
  | .reserve operation spentAfter =>
      s.status = .open ∧ s.pending = none ∧ operation.Valid ∧
      operation.identity ∉ s.operationIds ∧
      (s.spent.add operation.amount).Bounded ∧
      p.Fits (s.spent.add operation.amount) ∧ spentAfter = s.spent.add operation.amount
  | .exhausted operation reason =>
      s.status = .open ∧ s.pending = none ∧ operation.Valid ∧
      operation.identity ∉ s.operationIds ∧
      (s.spent.add operation.amount).Bounded ∧
      ¬ p.Fits (s.spent.add operation.amount) ∧ reason = "declared_budget"
  | .result reservation ok resultDigest errorCode elapsed =>
      s.status = .pending ∧ s.pending = some reservation ∧
      digestValid reservation = true ∧ elapsed ≤ maxNatural ∧
      resultShape ok resultDigest errorCode = true
  | .seal | .stop => s.status = .open ∧ s.pending = none

instance instDecidableBodyAllowed (b : Binding) (p : Policy) (s : State) (e : Event) :
    Decidable (BodyAllowed b p s e) := by
  unfold BodyAllowed
  split <;> infer_instance

def bodyNext (s : State) (e : Event) : State :=
  match e.body with
  | .open _ _ => { s with status := .open }
  | .reserve operation _ =>
      { s with
        spent := s.spent.add operation.amount
        status := .pending
        pending := some e.hash
        operationIds := s.operationIds ++ [operation.identity]
        charges := s.charges ++ [operation.kind] }
  | .exhausted _ _ => { s with status := .resourceExhausted }
  | .result _ ok _ _ _ =>
      { s with status := (if ok then .open else .safetyHalt), pending := none }
  | .seal => { s with status := .sealed }
  | .stop => { s with status := .externalStop }

def next (s : State) (e : Event) : State :=
  { bodyNext s e with head := e.hash, count := s.count + 1 }

abbrev Step (b : Binding) (p : Policy) (s : State) (e : Event) (t : State) : Prop :=
  s.count < maxEvents ∧ e.index = s.count ∧ e.previous = s.head ∧
  digestValid e.previous = true ∧ digestValid e.hash = true ∧
  BodyAllowed b p s e ∧ t = next s e

inductive Runs (b : Binding) (p : Policy) : State → List Event → State → Prop where
  | nil (s : State) : Runs b p s [] s
  | cons {s t u : State} {e : Event} {rest : List Event}
      (first : Step b p s e t) (later : Runs b p t rest u) : Runs b p s (e :: rest) u

abbrev CountersSound (s : State) : Prop :=
  s.spent = tally s.charges ∧ s.operationIds.length = s.charges.length
abbrev Terminal (s : State) : Prop :=
  s.status = .sealed ∨ s.status = .resourceExhausted ∨
  s.status = .safetyHalt ∨ s.status = .externalStop

theorem tally_append (ks : List Phase17Resource.Kind) (k : Phase17Resource.Kind) :
    tally (ks ++ [k]) = (tally ks).add (charge k) := by
  cases k <;> simp [tally, Usage.add, charge, Phase17Resource.counter,
    Phase17Resource.tariff, List.map_append, List.sum_append]

theorem reserve_charges_before_result {b p s e t operation spentAfter}
    (shape : e.body = .reserve operation spentAfter) (h : Step b p s e t) :
    t.spent = s.spent.add operation.amount ∧
    t.charges = s.charges ++ [operation.kind] ∧
    t.operationIds = s.operationIds ++ [operation.identity] ∧ t.pending = some e.hash := by
  rcases h with ⟨_, _, _, _, _, _, rfl⟩
  simp [next, bodyNext, shape]

theorem result_never_refunds {b p s e t reservation ok resultDigest errorCode elapsed}
    (shape : e.body = .result reservation ok resultDigest errorCode elapsed)
    (h : Step b p s e t) :
    t.spent = s.spent ∧ t.charges = s.charges ∧ t.operationIds = s.operationIds := by
  rcases h with ⟨_, _, _, _, _, _, rfl⟩
  simp [next, bodyNext, shape]

theorem result_requires_pending {b p s e t reservation ok resultDigest errorCode elapsed}
    (shape : e.body = .result reservation ok resultDigest errorCode elapsed)
    (h : Step b p s e t) : s.status = .pending ∧ s.pending = some reservation := by
  have allowed := h.2.2.2.2.2.1
  simp only [BodyAllowed, shape] at allowed
  exact ⟨allowed.1, allowed.2.1⟩

theorem terminal_state_rejects_events {b p s e t}
    (terminal : Terminal s) : ¬ Step b p s e t := by
  intro h
  have allowed := h.2.2.2.2.2.1
  cases shape : e.body <;> simp only [BodyAllowed, shape] at allowed
  all_goals rcases terminal with term | term | term | term
  all_goals simp_all [initial]

theorem step_counters_sound {b p s e t}
    (before : CountersSound s) (h : Step b p s e t) : CountersSound t := by
  rcases h with ⟨_, _, _, _, _, allowed, rfl⟩
  cases shape : e.body with
  | reserve operation spentAfter =>
      simp only [BodyAllowed, shape] at allowed
      have amount := allowed.2.2.1.2.2
      simp only [CountersSound, next, bodyNext, shape]
      constructor
      · rw [amount, before.1, tally_append]
      · simp only [List.length_append, List.length_singleton, before.2]
  | «open» binding policy => simpa [CountersSound, next, bodyNext, shape] using before
  | exhausted operation reason => simpa [CountersSound, next, bodyNext, shape] using before
  | result reservation ok resultDigest errorCode elapsed =>
      simpa [CountersSound, next, bodyNext, shape] using before
  | «seal» => simpa [CountersSound, next, bodyNext, shape] using before
  | stop => simpa [CountersSound, next, bodyNext, shape] using before

theorem replay_counters_sound {b p s events t}
    (before : CountersSound s) (h : Runs b p s events t) : CountersSound t := by
  induction h with
  | nil => exact before
  | cons first _ ih => exact ih (step_counters_sound before first)

theorem next_spending_monotone (s : State) (e : Event) : s.spent.LE (next s e).spent := by
  cases shape : e.body <;> simp [next, bodyNext, shape, Usage.LE, Usage.add]

theorem usage_le_trans {a b c : Usage} (h : a.LE b) (k : b.LE c) : a.LE c :=
  ⟨le_trans h.1 k.1, le_trans h.2.1 k.2.1,
    le_trans h.2.2.1 k.2.2.1, le_trans h.2.2.2 k.2.2.2⟩

theorem replay_spending_monotone {b p s events t}
    (h : Runs b p s events t) : s.spent.LE t.spent := by
  induction h with
  | nil => exact ⟨le_rfl, le_rfl, le_rfl, le_rfl⟩
  | cons first _ ih =>
      have equal := first.2.2.2.2.2.2
      exact usage_le_trans (equal ▸ next_spending_monotone _ _) ih

theorem step_within_policy {b p s e t} (before : p.Fits s.spent)
    (h : Step b p s e t) : p.Fits t.spent := by
  rcases h with ⟨_, _, _, _, _, allowed, rfl⟩
  cases shape : e.body with
  | reserve operation spentAfter =>
      simp only [BodyAllowed, shape] at allowed
      simpa only [next, bodyNext, shape] using allowed.2.2.2.2.2.1
  | «open» binding policy => simpa [next, bodyNext, shape] using before
  | exhausted operation reason => simpa [next, bodyNext, shape] using before
  | result reservation ok resultDigest errorCode elapsed => simpa [next, bodyNext, shape] using before
  | «seal» => simpa [next, bodyNext, shape] using before
  | stop => simpa [next, bodyNext, shape] using before

theorem replay_within_policy {b p s events t} (before : p.Fits s.spent)
    (h : Runs b p s events t) : p.Fits t.spent := by
  induction h with
  | nil => exact before
  | cons first _ ih => exact ih (step_within_policy before first)

theorem sealed_has_no_pending {b p s e t} (h : Step b p s e t)
    (sealed : t.status = .sealed) : t.pending = none := by
  rcases h with ⟨_, _, _, _, _, allowed, rfl⟩
  cases shape : e.body <;> simp_all [BodyAllowed, next, bodyNext]

/- Complete canonical JSON values for the typed events. Every object key and
   optional value is included. Only the imported T decoder interprets bytes. -/
def natValue (n : Nat) : Value := .integer (Int.ofNat n)
def usageValue (u : Usage) : Value :=
  .array [natValue u.candidates, natValue u.vectors, natValue u.inputs, natValue u.outputs]
def bindingValue (b : Binding) : Value := .object [
  ("candidate_package_hash", .string b.candidate), ("fixed_verifier_hash", .string b.verifier),
  ("predecessor_package_hash", .string b.predecessor), ("transcript_sha256", .string b.transcript)]
def policyValue (p : Policy) : Value := .object [
  ("cost_limit", natValue p.costLimit),
  ("dimensions", .array [.string "candidate_attempts", .string "vector_calls",
    .string "input_values", .string "output_values"]),
  ("limits", usageValue p.limits),
  ("profile", .string "phase17n.bounded-vector-reference-work.v1"),
  ("weights", .array [natValue 64, natValue 16, natValue 1, natValue 1])]
def kindString : Phase17Resource.Kind → String
  | .candidate => "candidate"
  | .vector => "vector"
def optionalString : Option String → Value
  | none => .null
  | some s => .string s
def bodyValue : Body → Value
  | .open b p => .object [("binding", bindingValue b), ("kind", .string "open"),
      ("policy", policyValue p), ("schema", .string "runtime.v5.phase17.resource-ledger.v1")]
  | .reserve op after => .object [("charge", usageValue op.amount),
      ("input_sha256", .string op.inputDigest), ("kind", .string "reserve"),
      ("operation", .string (kindString op.kind)), ("operation_id", .string op.identity),
      ("spent_after", usageValue after)]
  | .exhausted op reason => .object [("charge", usageValue op.amount),
      ("input_sha256", .string op.inputDigest), ("kind", .string "exhausted"),
      ("operation", .string (kindString op.kind)), ("operation_id", .string op.identity),
      ("reason", .string reason)]
  | .result reservation ok resultDigest errorCode elapsed => .object [
      ("elapsed_ns", natValue elapsed), ("error_code", optionalString errorCode),
      ("kind", .string "result"), ("ok", .boolean ok),
      ("reservation_hash", .string reservation), ("result_sha256", optionalString resultDigest)]
  | .seal => .object [("kind", .string "seal")]
  | .stop => .object [("kind", .string "stop")]
def eventValue (e : Event) : Value := .object [
  ("body", bodyValue e.body), ("hash", .string e.hash),
  ("index", natValue e.index), ("previous", .string e.previous)]
abbrev EventImageChecked (image : List Nat) (e : Event) : Prop :=
  0 < image.length ∧ image.length ≤ 4096 ∧ Phase17Json.decode image = some (eventValue e)
def framed (images : List (List Nat)) : List Nat :=
  (images.map (fun image => image ++ [10])).flatten
theorem framed_of_lines {lines images : List (List Nat)}
    (h : List.Forall₂ (fun line image => line = image ++ [10]) lines images) :
    lines.flatten = framed images := by
  induction h with
  | nil => rfl
  | cons first _ ih =>
      simpa [framed, first] using ih

theorem flatten_length_of_lines {lines : List (List Nat)} {lengths : List Nat}
    (h : List.Forall₂ (fun line n => line.length = n) lines lengths) :
    lines.flatten.length = lengths.sum := by
  induction h with
  | nil => rfl
  | cons first _ ih =>
      simp only [List.flatten_cons, List.length_append, List.sum_cons, first, ih]

abbrev JournalChecked (b : Binding) (p : Policy) (raw : List Nat)
    (images : List (List Nat)) (events : List Event) (expectedHead : String) (final : State) : Prop :=
  0 < raw.length ∧ raw.length ≤ 4194304 ∧ raw = framed images ∧
  List.Forall₂ EventImageChecked images events ∧
  Runs b p initial events final ∧ final.head = expectedHead

structure WorkReference where
  identity : String
  kind : Phase17Resource.Kind
  inputImage : List Nat
  outputImage : List Nat
  inputDigest : String
  outputDigest : String
  deriving DecidableEq

-- Digest strings below are captured associations. This is not a SHA theorem.
abbrev WorkBound (w : WorkReference) (pair : Event × Event) : Prop :=
  match pair.1.body, pair.2.body with
  | .reserve op _, .result reservation ok resultDigest errorCode _ =>
      op.identity = w.identity ∧ op.kind = w.kind ∧
      op.inputDigest = w.inputDigest ∧ digestValid w.inputDigest = true ∧
      reservation = pair.1.hash ∧ ok = true ∧ resultDigest = some w.outputDigest ∧
      digestValid w.outputDigest = true ∧ errorCode = none
  | _, _ => False

instance instDecidableWorkBound (w : WorkReference) (first second : Event) :
    Decidable (WorkBound w (first, second)) := by
  unfold WorkBound
  split <;> infer_instance

def pairEvents (pairs : List (Event × Event)) : List Event :=
  (pairs.map (fun pair => [pair.1, pair.2])).flatten

end Phase17ResourceProtocol
