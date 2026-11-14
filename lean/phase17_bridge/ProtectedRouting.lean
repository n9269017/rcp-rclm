/- Phase 17S: routing of original protected prompt literals through captured
   package objects and adapter bytes into the Phase 17R tensor interpretation.
   JSON decoding, file capture, digest authenticity and Python execution are
   outside this reference semantics. The admitted architecture selects the
   first layer's attn_output.B adapter; this is not a general transformer. -/
namespace Phase17Routing

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

/-- Complete captured JSON values, preserving list order and value types. -/
inductive Value where
  | null
  | boolean (value : Bool)
  | integer (value : Int)
  | string (value : String)
  | array (values : List Value)
  | object (fields : List (String × Value))

def field (value : Value) (key : String) : Value :=
  match value with
  | .object fields => ((fields.find? (fun pair => decide (pair.1 = key))).map Prod.snd).getD .null
  | _ => .null

def array : Value → List Value
  | .array values => values
  | _ => []

def integer? : Value → Option Int
  | .integer value => some value
  | _ => none

def string? : Value → Option String
  | .string value => some value
  | _ => none

def marker? (value : Value) : Option Nat :=
  match integer? value with
  | some marker => if 0 ≤ marker ∧ marker < 256 then some marker.toNat else none
  | none => none

def matchingRoutes (routes : List Value) (commitment : String) : List Value :=
  routes.filter (fun row => decide (string? (field row "challenge_commitment_hash") = some commitment))

def uniqueRoute (routes : List Value) (commitment : String) : Option Value :=
  match matchingRoutes routes commitment with
  | [row] => some row
  | _ => none

theorem unique_route_sound (routes : List Value) (commitment : String) (row : Value)
    (accepted : uniqueRoute routes commitment = some row) :
    matchingRoutes routes commitment = [row] := by
  cases equal : matchingRoutes routes commitment with
  | nil => simp [uniqueRoute, equal] at accepted
  | cons found rest =>
      cases rest with
      | nil =>
          have same : found = row := by simpa [uniqueRoute, equal] using accepted
          simp [same]
      | cons second rest => simp [uniqueRoute, equal] at accepted

theorem duplicate_route_rejected (routes : List Value) (commitment : String)
    (ambiguous : (matchingRoutes routes commitment).length ≠ 1) :
    uniqueRoute routes commitment = none := by
  cases equal : matchingRoutes routes commitment with
  | nil => simp [uniqueRoute, equal]
  | cons found rest =>
      cases rest with
      | nil => simp [equal] at ambiguous
      | cons second rest => simp [uniqueRoute, equal]

structure Package where
  memory : Value
  retrieval : Value
  generator : Value
  planner : Value
  optimizer : Value
  resource : Value
  packageManifest : Value
  adapterManifest : Value
  adapterImage : Phase17Sparse.TensorImage

def selectedAdapter (package : Package) : Option Value :=
  (array (field package.adapterManifest "records")).find? (fun row =>
    decide (string? (field (field row "spec") "name") = some "adapter.layers.00.attn_output.B"))

def selectedAdapterHash (package : Package) : Option String := do
  let row ← selectedAdapter package
  string? (field row "sha256")

def selectedAdapterShape (package : Package) : Bool :=
  match selectedAdapter package with
  | none => false
  | some row =>
      let spec := field row "spec"
      decide (string? (field spec "path") = some "model/adapters/tensors/adapter.layers.00.attn_output.B.i16le.bin" ∧
        integer? (field spec "size_bytes") = some 5120 ∧ string? (field spec "dtype") = some "int16" ∧
        string? (field spec "byte_order") = some "little" ∧ string? (field spec "role") = some "adapter_b" ∧
        (array (field spec "shape")).map integer? = [some 320, some 8])

def tensorManifestHash (package : Package) : Option String :=
  string? (field package.packageManifest "tensor_manifest_hash")

def CanonicalAdapter (image : Phase17Sparse.TensorImage) : Prop :=
  image.byteLength = 5120 ∧
  ((Phase17Sparse.entries image.support).map Prod.fst).Pairwise (· < ·) ∧
  ∀ entry ∈ Phase17Sparse.entries image.support,
    entry.1 < image.byteLength ∧ 0 < entry.2 ∧ entry.2 < 256

def wordAt (image : Phase17Sparse.TensorImage) (offset : Nat) : Int :=
  Phase17Sparse.signed16 (Phase17Sparse.byteAt image offset)
    (Phase17Sparse.byteAt image (offset + 1))

def fourWords (image : Phase17Sparse.TensorImage) (offset : Nat) : Option (List Int) :=
  if offset + 8 ≤ image.byteLength then
    some ((List.range 4).map (fun index => wordAt image (offset + 2 * index)))
  else none

def legacyLookup (object : Value) (key : String) (marker : Nat) : Option Nat :=
  let selected := (array (field object key)).find? (fun row =>
    decide (integer? (field row "query_marker_token_id") = some marker ∧
      string? (field row "match_mode") = some "exact_terminal_byte"))
  selected.bind (fun row => marker? (field row "route_marker_token_id"))

def legacyAdapter (package : Package) (marker : Nat) : Option Nat :=
  if (selectedAdapter package).isSome ∧ marker = 87 ∧
      fourWords package.adapterImage 0 = some [87, 86, 8, 1] then some 86 else none

/-- The three tests are ordered, not iterated to a fixed point. -/
def legacyAttempt (package : Package) (start : Nat) : Option Nat := do
  let current ← if start = 87 then legacyAdapter package start else some start
  let current ← if current = 86 then legacyLookup package.planner "routes" current else some current
  if current = 85 then legacyLookup package.retrieval "entries" current else some current

structure LegacyResult where
  marker : Nat
  hit : Bool
  deriving DecidableEq

def legacyChain (package : Package) (start : Nat) : LegacyResult :=
  match legacyAttempt package start with
  | some marker => ⟨marker, true⟩
  | none => ⟨start, false⟩

theorem legacy_failure_restores_start (package : Package) (start : Nat)
    (failed : legacyAttempt package start = none) :
    legacyChain package start = ⟨start, false⟩ := by
  simp [legacyChain, failed]

def pairedHit (left right : Value) (commitment : String) (slot : Nat) : Bool :=
  match uniqueRoute (array (field left "phase14_routes")) commitment,
      uniqueRoute (array (field right "phase14_routes")) commitment with
  | some a, some b => decide
      (integer? (field a "slot_token_id") = some slot ∧ integer? (field b "slot_token_id") = some slot ∧
       integer? (field a "route_marker_token_id") = some 87 ∧ integer? (field b "route_marker_token_id") = some 87)
  | _, _ => false

def adapterHit (package : Package) (commitment : String) (slot : Nat) : Bool :=
  match uniqueRoute (array (field package.optimizer "phase14_routes")) commitment,
      selectedAdapterHash package with
  | some row, some tensorHash =>
      match integer? (field row "offset_bytes"), integer? (field row "commitment_prefix_u16") with
      | some offset, some commitmentPrefix => decide
          (0 ≤ offset ∧ string? (field row "tensor_sha256") = some tensorHash ∧
           fourWords package.adapterImage offset.toNat = some [(slot : Int), 87, commitmentPrefix, 1])
      | _, _ => false
  | _, _ => false

def weightHit (package : Package) (tensor : Phase17Sparse.TensorImage)
    (commitment : String) (slot : Nat) : Bool :=
  match uniqueRoute (array (field package.resource "phase14_weight_routes")) commitment,
      tensorManifestHash package with
  | some row, some manifestHash => decide
      (integer? (field row "slot_token_id") = some slot ∧
       integer? (field row "route_marker_token_id") = some 87 ∧
       string? (field row "tensor_manifest_hash") = some manifestHash ∧
       Phase17Sparse.greedyToken (Phase17Sparse.scoreRow tensor slot) = 87)
  | _, _ => false

inductive Family where
  | memoryRetrieval
  | generatorPlanner
  | adapterOptimizer
  | modelWeights
  deriving DecidableEq

def familyHits (package : Package) (tensor : Phase17Sparse.TensorImage)
    (commitment : String) (slot : Nat) : List Family :=
  let decisions := [(Family.memoryRetrieval, pairedHit package.memory package.retrieval commitment slot),
    (.generatorPlanner, pairedHit package.generator package.planner commitment slot),
    (.adapterOptimizer, adapterHit package commitment slot),
    (.modelWeights, weightHit package tensor commitment slot)]
  (decisions.filter Prod.snd).map Prod.fst

def uniqueFamily : List Family → Option Family
  | [family] => some family
  | _ => none

theorem unique_family_sound (hits : List Family) (family : Family)
    (accepted : uniqueFamily hits = some family) : hits = [family] := by
  cases hits with
  | nil => simp [uniqueFamily] at accepted
  | cons found rest =>
      cases rest with
      | nil =>
          have same : found = family := by simpa [uniqueFamily] using accepted
          simp [same]
      | cons second rest => simp [uniqueFamily] at accepted

structure Challenge where
  taskId : String
  commitment : String
  slot : Nat
  deriving DecidableEq

structure Task where
  taskId : String
  prompt : List Nat
  challenge : Option Challenge
  deriving DecidableEq

def hexDigit (character : Char) : Option Nat :=
  let code := character.toNat
  if 48 ≤ code ∧ code ≤ 57 then some (code - 48)
  else if 97 ≤ code ∧ code ≤ 102 then some (code - 87)
  else none

/-- This checks the captured digest's syntax and deterministic slot mapping;
    it does not assert that any external digest calculation was authentic. -/
def commitmentSlot (commitment : String) : Option Nat := do
  let characters := commitment.toList
  if characters.length ≠ 64 ∨ !characters.all (fun character => (hexDigit character).isSome) then none
  else
    let firstEight ← (characters.take 8).foldl (fun total character => do
      let prior ← total
      let digit ← hexDigit character
      some (16 * prior + digit)) (some 0)
    some (180 + firstEight % 64)

def promptBound (task : Task) : Bool :=
  !task.prompt.isEmpty && task.prompt.all (fun byte => decide (byte < 256)) &&
    match task.challenge with
    | none => true
    | some challenge => decide
        (task.taskId = challenge.taskId ∧ task.prompt.getLast? = some challenge.slot ∧
         commitmentSlot challenge.commitment = some challenge.slot)

structure RouteResult where
  marker : Nat
  hit : Bool
  family : Option Family
  deriving DecidableEq

/-- Route inputs are original prompt literals and complete package objects.
    No success flag, selected family or effective marker is supplied. -/
def route (package : Package) (tensor : Phase17Sparse.TensorImage) (task : Task) : RouteResult :=
  let original := task.prompt.getLast?.getD 0
  if !promptBound task then ⟨original, false, none⟩
  else
    let family := task.challenge.bind (fun challenge =>
      uniqueFamily (familyHits package tensor challenge.commitment original))
    let start := if task.challenge.isSome && family.isSome then 87 else original
    let legacy := legacyChain package start
    let hit := if task.challenge.isSome then family.isSome && legacy.hit else legacy.hit
    ⟨legacy.marker, hit, family⟩

def effectiveMarkers (package : Package) (tensor : Phase17Sparse.TensorImage)
    (tasks : List Task) : List Nat := tasks.map (fun task => (route package tensor task).marker)

def RoutingBinding (package : Package) (tensor : Phase17Sparse.TensorImage)
    (tasks : List Task) (markers : List Nat) : Prop :=
  tasks.length = 11 ∧
  tasks.all (fun task => (route package tensor task).hit) = true ∧
  effectiveMarkers package tensor tasks = markers

def RoutedGoalBinding (package : Package) (tensor : Phase17Sparse.TensorImage)
    (tasks : List Task) (targets : List (List Nat)) : Prop :=
  tasks.length = 11 ∧
  tasks.all (fun task => (route package tensor task).hit) = true ∧
  Phase17Sparse.GoalBinding tensor (effectiveMarkers package tensor tasks) targets

theorem routed_goal_binding_sound (package : Package) (tensor : Phase17Sparse.TensorImage)
    (tasks : List Task) (markers : List Nat) (targets : List (List Nat))
    (routing : RoutingBinding package tensor tasks markers)
    (decoding : Phase17Sparse.GoalBinding tensor markers targets) :
    RoutedGoalBinding package tensor tasks targets := by
  exact ⟨routing.1, routing.2.1, routing.2.2.symm ▸ decoding⟩

def teacherPositions : Nat → List Nat → List (Nat × Nat)
  | _, [] => []
  | current, target :: rest => (current, target) :: teacherPositions target rest

def routedPositions (package : Package) (tensor : Phase17Sparse.TensorImage)
    (tasks : List Task) (targets : List (List Nat)) : List (Nat × Nat) :=
  (tasks.zip targets).flatMap (fun pair => teacherPositions (route package tensor pair.1).marker pair.2)

end Phase17Routing
