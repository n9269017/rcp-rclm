import Phase17SDependency

set_option Elab.async false

/- Phase 17T: total interpretation of the complete captured canonical ASCII
   JSON images used by Phase 17S. Capture, digest authenticity, arbitrary JSON,
   and execution of the external Python implementation remain outside this
   reference. The selected image is checked against the actual imported S
   package value, rather than a separately supplied successful observation. -/
namespace Phase17Json

open Phase17Routing

mutual
  def valueDecEq (left right : Value) : Decidable (left = right) :=
    match left, right with
    | .null, .null => isTrue rfl
    | .null, .boolean right => isFalse (by intro h; cases h)
    | .null, .integer right => isFalse (by intro h; cases h)
    | .null, .string right => isFalse (by intro h; cases h)
    | .null, .array right => isFalse (by intro h; cases h)
    | .null, .object right => isFalse (by intro h; cases h)
    | .boolean left, .null => isFalse (by intro h; cases h)
    | .boolean left, .boolean right => 
        match decEq left right with
        | isTrue h => isTrue (by cases h; rfl)
        | isFalse h => isFalse (fun equal => h (Value.boolean.inj equal))
    | .boolean left, .integer right => isFalse (by intro h; cases h)
    | .boolean left, .string right => isFalse (by intro h; cases h)
    | .boolean left, .array right => isFalse (by intro h; cases h)
    | .boolean left, .object right => isFalse (by intro h; cases h)
    | .integer left, .null => isFalse (by intro h; cases h)
    | .integer left, .boolean right => isFalse (by intro h; cases h)
    | .integer left, .integer right => 
        match decEq left right with
        | isTrue h => isTrue (by cases h; rfl)
        | isFalse h => isFalse (fun equal => h (Value.integer.inj equal))
    | .integer left, .string right => isFalse (by intro h; cases h)
    | .integer left, .array right => isFalse (by intro h; cases h)
    | .integer left, .object right => isFalse (by intro h; cases h)
    | .string left, .null => isFalse (by intro h; cases h)
    | .string left, .boolean right => isFalse (by intro h; cases h)
    | .string left, .integer right => isFalse (by intro h; cases h)
    | .string left, .string right => 
        match decEq left right with
        | isTrue h => isTrue (by cases h; rfl)
        | isFalse h => isFalse (fun equal => h (Value.string.inj equal))
    | .string left, .array right => isFalse (by intro h; cases h)
    | .string left, .object right => isFalse (by intro h; cases h)
    | .array left, .null => isFalse (by intro h; cases h)
    | .array left, .boolean right => isFalse (by intro h; cases h)
    | .array left, .integer right => isFalse (by intro h; cases h)
    | .array left, .string right => isFalse (by intro h; cases h)
    | .array left, .array right => 
        match valuesDecEq left right with
        | isTrue h => isTrue (by cases h; rfl)
        | isFalse h => isFalse (fun equal => h (Value.array.inj equal))
    | .array left, .object right => isFalse (by intro h; cases h)
    | .object left, .null => isFalse (by intro h; cases h)
    | .object left, .boolean right => isFalse (by intro h; cases h)
    | .object left, .integer right => isFalse (by intro h; cases h)
    | .object left, .string right => isFalse (by intro h; cases h)
    | .object left, .array right => isFalse (by intro h; cases h)
    | .object left, .object right => 
        match fieldsDecEq left right with
        | isTrue h => isTrue (by cases h; rfl)
        | isFalse h => isFalse (fun equal => h (Value.object.inj equal))
  termination_by sizeOf left
  decreasing_by all_goals simp_wf

  def valuesDecEq (left right : List Value) : Decidable (left = right) :=
    match left, right with
    | [], [] => isTrue rfl
    | [], _ :: _ => isFalse (by intro h; cases h)
    | _ :: _, [] => isFalse (by intro h; cases h)
    | a :: as, b :: bs =>
        match valueDecEq a b with
        | isFalse h => isFalse (fun equal => h (List.cons.inj equal).1)
        | isTrue h =>
            match valuesDecEq as bs with
            | isFalse tail => isFalse (fun equal => tail (List.cons.inj equal).2)
            | isTrue tail => isTrue (by cases h; cases tail; rfl)
  termination_by sizeOf left
  decreasing_by all_goals simp_wf <;> omega

  def fieldsDecEq (left right : List (String × Value)) : Decidable (left = right) :=
    match left, right with
    | [], [] => isTrue rfl
    | [], _ :: _ => isFalse (by intro h; cases h)
    | _ :: _, [] => isFalse (by intro h; cases h)
    | (ka, a) :: as, (kb, b) :: bs =>
        match decEq ka kb with
        | isFalse h => isFalse (fun equal => h (Prod.mk.inj (List.cons.inj equal).1).1)
        | isTrue keys =>
            match valueDecEq a b with
            | isFalse h => isFalse (fun equal => h (Prod.mk.inj (List.cons.inj equal).1).2)
            | isTrue h =>
                match fieldsDecEq as bs with
                | isFalse tail => isFalse (fun equal => tail (List.cons.inj equal).2)
                | isTrue tail => isTrue (by cases keys; cases h; cases tail; rfl)
  termination_by sizeOf left
  decreasing_by all_goals simp_wf <;> omega
end
instance : DecidableEq Value := valueDecEq

def maxBytes : Nat := 65536
def maxDepth : Nat := 20
def maxArray : Nat := 1024
def maxObject : Nat := 256
def maxString : Nat := 8192

def digit (byte : Nat) : Bool := decide (48 ≤ byte ∧ byte ≤ 57)

/-- Strings in this declared profile are unescaped printable ASCII. -/
def stringRest : List Nat → List Char → Nat → Option (String × List Nat)
  | [], _, _ => none
  | byte :: rest, reversed, remaining =>
      if byte = 34 then some (String.ofList reversed.reverse, rest)
      else if remaining = 0 ∨ byte < 32 ∨ 126 < byte ∨ byte = 92 then none
      else stringRest rest (Char.ofNat byte :: reversed) (remaining - 1)

def stringValue : List Nat → Option (String × List Nat)
  | 34 :: rest => stringRest rest [] maxString
  | _ => none

/-- Decimal scanning is structurally recursive and has a nineteen-digit cap. -/
def digitsRest : List Nat → Nat → Nat → Option (Nat × List Nat)
  | [], value, _ => some (value, [])
  | byte :: rest, value, remaining =>
      if digit byte then
        if remaining = 0 then none
        else digitsRest rest (10 * value + (byte - 48)) (remaining - 1)
      else some (value, byte :: rest)

def magnitude : List Nat → Option (Nat × List Nat)
  | 48 :: rest => some (0, rest)
  | byte :: rest =>
      if 49 ≤ byte ∧ byte ≤ 57 then digitsRest rest (byte - 48) 18 else none
  | [] => none

def numberValue (bytes : List Nat) : Option (Value × List Nat) := do
  match bytes with
  | 45 :: rest =>
      let (value, tail) ← magnitude rest
      if value = 0 ∨ 9223372036854775808 < value then none
      else some (.integer (-(Int.ofNat value)), tail)
  | _ =>
      let (value, tail) ← magnitude bytes
      if 9223372036854775807 < value then none
      else some (.integer (Int.ofNat value), tail)

mutual
  /-- Fuel makes all recursive paths total; depth and collection bounds are
      independent checks. The entire image must later be consumed. -/
  def parseValue : Nat → Nat → List Nat → Option (Value × List Nat)
    | 0, _, _ => none
    | fuel + 1, depth, bytes =>
        if maxDepth < depth then none
        else
          match bytes with
          | 110 :: 117 :: 108 :: 108 :: rest => some (.null, rest)
          | 116 :: 114 :: 117 :: 101 :: rest => some (.boolean true, rest)
          | 102 :: 97 :: 108 :: 115 :: 101 :: rest => some (.boolean false, rest)
          | 34 :: rest => do
              let (value, tail) ← stringRest rest [] maxString
              some (.string value, tail)
          | 91 :: 93 :: rest => some (.array [], rest)
          | 91 :: rest => arrayItems fuel (depth + 1) 0 [] rest
          | 123 :: 125 :: rest => some (.object [], rest)
          | 123 :: rest => objectItems fuel (depth + 1) 0 none [] rest
          | _ => numberValue bytes

  def arrayItems : Nat → Nat → Nat → List Value → List Nat → Option (Value × List Nat)
    | 0, _, _, _, _ => none
    | fuel + 1, depth, count, reversed, bytes => do
        if maxArray ≤ count then none
        else
          let (value, tail) ← parseValue fuel depth bytes
          match tail with
          | 93 :: rest => some (.array (value :: reversed).reverse, rest)
          | 44 :: rest => arrayItems fuel depth (count + 1) (value :: reversed) rest
          | _ => none

  def objectItems : Nat → Nat → Nat → Option String → List (String × Value) → List Nat →
      Option (Value × List Nat)
    | 0, _, _, _, _, _ => none
    | fuel + 1, depth, count, previous, reversed, bytes => do
        if maxDepth < depth ∨ maxObject ≤ count then none
        else
          let (key, tail) ← stringValue bytes
          if previous.any (fun prior => !(decide (prior < key))) then none
          else
            match tail with
            | 58 :: body => do
                let (value, tail) ← parseValue fuel depth body
                match tail with
                | 125 :: rest => some (.object ((key, value) :: reversed).reverse, rest)
                | 44 :: rest => objectItems fuel depth (count + 1) (some key) ((key, value) :: reversed) rest
                | _ => none
            | _ => none
end

/-- Twice the bounded image length plus one is a conservative recursion fuel.
    Acceptance additionally requires exact, whole-image consumption. -/
def decode (bytes : List Nat) : Option Value :=
  if bytes.length ≤ maxBytes ∧ bytes.all (fun byte => decide (byte < 128)) = true then
    match parseValue (2 * bytes.length + 1) 0 bytes with
    | some (value, []) => some value
    | _ => none
  else none

theorem decode_unique (bytes : List Nat) (left right : Value)
    (first : decode bytes = some left) (second : decode bytes = some right) : left = right := by
  exact Option.some.inj (first.symm.trans second)

theorem decode_byte_domain (bytes : List Nat) (value : Value)
    (accepted : decode bytes = some value) :
    bytes.length ≤ maxBytes ∧ bytes.all (fun byte => decide (byte < 128)) = true := by
  by_cases valid : bytes.length ≤ maxBytes ∧ bytes.all (fun byte => decide (byte < 128)) = true
  · exact valid
  · unfold decode at accepted
    rw [if_neg valid] at accepted
    cases accepted

theorem decode_consumes_all (bytes : List Nat) (value : Value)
    (accepted : decode bytes = some value) :
    parseValue (2 * bytes.length + 1) 0 bytes = some (value, []) := by
  have domain := decode_byte_domain bytes value accepted
  unfold decode at accepted
  simp only [domain] at accepted
  cases parsed : parseValue (2 * bytes.length + 1) 0 bytes with
  | none => simp [parsed] at accepted
  | some result =>
      rcases result with ⟨found, tail⟩
      cases tail with
      | nil =>
          have same : found = value := by simpa [parsed] using accepted
          cases same
          rfl
      | cons byte rest => simp [parsed] at accepted

structure PackageImages where
  memory : List Nat
  retrieval : List Nat
  generator : List Nat
  planner : List Nat
  optimizer : List Nat
  resource : List Nat
  packageManifest : List Nat
  adapterManifest : List Nat
  deriving DecidableEq

def ImagesBound (images : PackageImages) (package : Package) : Prop :=
  decode images.memory = some package.memory ∧
  decode images.retrieval = some package.retrieval ∧
  decode images.generator = some package.generator ∧
  decode images.planner = some package.planner ∧
  decode images.optimizer = some package.optimizer ∧
  decode images.resource = some package.resource ∧
  decode images.packageManifest = some package.packageManifest ∧
  decode images.adapterManifest = some package.adapterManifest

def decodePackage (images : PackageImages) (adapter : Phase17Sparse.TensorImage) : Option Package := do
  let memory ← decode images.memory
  let retrieval ← decode images.retrieval
  let generator ← decode images.generator
  let planner ← decode images.planner
  let optimizer ← decode images.optimizer
  let resource ← decode images.resource
  let packageManifest ← decode images.packageManifest
  let adapterManifest ← decode images.adapterManifest
  pure { memory := memory, retrieval := retrieval, generator := generator, planner := planner, optimizer := optimizer, resource := resource, packageManifest := packageManifest, adapterManifest := adapterManifest, adapterImage := adapter }

theorem images_binding_sound (images : PackageImages) (package : Package)
    (bound : ImagesBound images package) :
    decodePackage images package.adapterImage = some package := by
  rcases bound with ⟨a, b, c, d, e, f, g, h⟩
  simp [decodePackage, a, b, c, d, e, f, g, h]

theorem decoded_package_unique (images : PackageImages) (adapter : Phase17Sparse.TensorImage)
    (left right : Package) (first : decodePackage images adapter = some left)
    (second : decodePackage images adapter = some right) : left = right := by
  exact Option.some.inj (first.symm.trans second)

end Phase17Json

namespace Phase17Json
open Phase17Routing RcpRclmFormalCoreV2 RcpRclmFormalCoreV3
set_option maxRecDepth 32768
set_option maxHeartbeats 32000000
-- Fresh T packet SHA256: 1c1706cf77fd7cef65f9bbded78ff63796624c27cb1932032c5d7459e70c8410
def controlImage : List Nat := [123, 34, 99, 97, 110, 100, 105, 100, 97, 116, 101, 95, 115, 101, 108, 102, 95, 114, 101, 112, 111, 114, 116, 95, 97, 117, 116, 104, 111, 114, 105, 116, 97, 116, 105, 118, 92, 117, 48, 48, 54, 53, 34, 58, 102, 97, 108, 115, 101, 44, 34, 101, 110, 116, 114, 105, 101, 115, 34, 58, 91, 123, 34, 99, 111, 110, 116, 101, 110, 116, 95, 99, 108, 97, 115, 115, 34, 58, 34, 99, 101, 114, 116, 105, 102, 105, 101, 100, 95, 99, 97, 112, 97, 98, 105, 108, 105, 116, 121, 95, 114, 111, 117, 116, 101, 34, 44, 34, 101, 110, 116, 114, 121, 95, 104, 97, 115, 104, 34, 58, 34, 100, 54, 55, 50, 52, 54, 100, 55, 101, 56, 98, 102, 51, 56, 101, 56, 50, 57, 51, 51, 53, 100, 53, 98, 102, 99, 51, 101, 55, 49, 98, 97, 101, 52, 57, 57, 57, 55, 54, 50, 100, 51, 98, 56, 97, 100, 48, 55, 99, 55, 49, 99, 99, 53, 49, 54, 48, 102, 48, 99, 101, 52, 51, 52, 34, 44, 34, 101, 110, 116, 114, 121, 95, 105, 100, 34, 58, 34, 112, 104, 97, 115, 101, 49, 50, 99, 45, 99, 101, 114, 116, 105, 102, 105, 101, 100, 45, 111, 114, 100, 101, 114, 45, 115, 107, 105, 108, 108, 45, 114, 111, 117, 116, 101, 34, 44, 34, 104, 101, 108, 100, 111, 117, 116, 95, 112, 114, 111, 109, 112, 116, 95, 112, 114, 101, 115, 101, 110, 116, 34, 58, 102, 97, 108, 115, 101, 44, 34, 104, 101, 108, 100, 111, 117, 116, 95, 114, 101, 102, 101, 114, 101, 110, 99, 101, 95, 97, 110, 115, 119, 101, 114, 95, 112, 114, 101, 115, 101, 110, 116, 34, 58, 102, 97, 108, 115, 101, 44, 34, 104, 101, 108, 100, 111, 117, 116, 95, 116, 97, 115, 107, 95, 105, 100, 95, 112, 114, 101, 115, 101, 110, 116, 34, 58, 102, 97, 108, 115, 101, 44, 34, 114, 111, 117, 116, 101, 95, 109, 97, 114, 107, 101, 114, 95, 116, 111, 107, 101, 110, 95, 105, 100, 34, 58, 56, 52, 44, 34, 115, 99, 104, 101, 109, 97, 95, 105, 100, 34, 58, 34, 114, 117, 110, 116, 105, 109, 101, 46, 118, 51, 46, 112, 104, 97, 115, 101, 49, 50, 99, 46, 109, 101, 109, 111, 114, 121, 95, 101, 110, 116, 114, 121, 46, 118, 49, 34, 44, 34, 115, 111, 117, 114, 99, 101, 95, 102, 114, 111, 110, 116, 105, 101, 114, 95, 116, 97, 115, 107, 95, 105, 100, 34, 58, 34, 108, 101, 97, 110, 46, 112, 104, 97, 115, 101, 49, 50, 46, 103, 101, 110, 101, 114, 97, 116, 105, 111, 110, 49, 46, 108, 101, 95, 114, 101, 102, 108, 95, 109, 97, 99, 114, 111, 34, 125, 93, 44, 34, 101, 110, 116, 114, 121, 95, 99, 111, 117, 110, 116, 34, 58, 49, 44, 34, 104, 101, 108, 100, 111, 117, 116, 95, 109, 97, 116, 101, 114, 105, 97, 108, 95, 112, 114, 101, 115, 101, 110, 116, 34, 58, 102, 97, 108, 115, 101, 44, 34, 104, 101, 108, 100, 111, 117, 116, 95, 109, 97, 116, 101, 114, 105, 97, 108, 95, 118, 105, 115, 105, 98, 108, 101, 34, 58, 102, 97, 108, 115, 101, 44, 34, 109, 97, 110, 105, 102, 101, 115, 116, 95, 104, 97, 115, 104, 34, 58, 34, 53, 57, 54, 52, 48, 54, 102, 98, 98, 56, 53, 51, 55, 99, 98, 102, 50, 50, 99, 97, 98, 54, 100, 56, 52, 100, 54, 51, 101, 55, 56, 48, 48, 100, 98, 52, 48, 99, 54, 57, 53, 50, 102, 50, 55, 99, 55, 55, 101, 97, 57, 49, 99, 54, 53, 55, 48, 51, 56, 54, 48, 98, 48, 49, 34, 44, 34, 112, 101, 114, 115, 105, 115, 116, 101, 110, 99, 101, 34, 58, 34, 112, 97, 99, 107, 97, 103, 101, 95, 98, 111, 117, 110, 100, 34, 44, 34, 112, 104, 97, 115, 101, 49, 52, 95, 114, 111, 117, 116, 101, 95, 99, 111, 117, 110, 116, 34, 58, 49, 44, 34, 112, 104, 97, 115, 101, 49, 52, 95, 114, 111, 117, 116, 101, 115, 34, 58, 91, 123, 34, 99, 104, 97, 108, 108, 101, 110, 103, 101, 95, 99, 111, 109, 109, 105, 116, 109, 101, 110, 116, 95, 104, 97, 115, 104, 34, 58, 34, 101, 53, 99, 49, 100, 97, 56, 100, 100, 56, 99, 52, 99, 53, 55, 48, 55, 49, 54, 53, 99, 102, 55, 53, 102, 97, 53, 99, 51, 49, 99, 102, 53, 49, 55, 54, 101, 99, 100, 99, 98, 54, 57, 56, 49, 49, 51, 53, 97, 51, 102, 97, 53, 100, 97, 56, 100, 98, 50, 56, 50, 51, 57, 55, 34, 44, 34, 104, 101, 108, 100, 111, 117, 116, 95, 112, 114, 111, 109, 112, 116, 95, 112, 114, 101, 115, 101, 110, 116, 34, 58, 102, 97, 108, 115, 101, 44, 34, 104, 101, 108, 100, 111, 117, 116, 95, 114, 101, 102, 101, 114, 101, 110, 99, 101, 95, 97, 110, 115, 119, 101, 114, 95, 112, 114, 101, 115, 101, 110, 116, 34, 58, 102, 97, 108, 115, 101, 44, 34, 112, 97, 99, 107, 97, 103, 101, 95, 103, 101, 110, 101, 114, 97, 116, 101, 100, 34, 58, 116, 114, 117, 101, 44, 34, 112, 114, 111, 103, 114, 97, 109, 95, 118, 97, 114, 105, 97, 110, 116, 34, 58, 34, 114, 101, 99, 111, 118, 101, 114, 34, 44, 34, 114, 111, 117, 116, 101, 95, 104, 97, 115, 104, 34, 58, 34, 56, 101, 49, 101, 101, 57, 54, 101, 56, 99, 52, 52, 54, 100, 52, 100, 98, 50, 51, 51, 53, 102, 48, 100, 56, 48, 53, 51, 53, 55, 101, 101, 101, 102, 100, 53, 53, 55, 55, 52, 97, 55, 57, 101, 51, 50, 56, 53, 50, 100, 54, 101, 52, 53, 99, 102, 101, 48, 49, 52, 53, 57, 99, 102, 34, 44, 34, 114, 111, 117, 116, 101, 95, 109, 97, 114, 107, 101, 114, 95, 116, 111, 107, 101, 110, 95, 105, 100, 34, 58, 56, 55, 44, 34, 115, 99, 104, 101, 109, 97, 95, 105, 100, 34, 58, 34, 114, 117, 110, 116, 105, 109, 101, 46, 118, 52, 46, 112, 104, 97, 115, 101, 49, 52, 46, 109, 101, 109, 111, 114, 121, 95, 114, 101, 116, 114, 105, 101, 118, 97, 108, 95, 114, 111, 117, 116, 101, 46, 118, 49, 34, 44, 34, 115, 108, 111, 116, 95, 116, 111, 107, 101, 110, 95, 105, 100, 34, 58, 49, 57, 51, 44, 34, 115, 117, 99, 99, 101, 115, 115, 102, 117, 108, 95, 102, 97, 109, 105, 108, 121, 95, 104, 105, 110, 116, 95, 118, 105, 115, 105, 98, 108, 101, 34, 58, 102, 97, 108, 115, 101, 44, 34, 117, 112, 100, 97, 116, 101, 95, 102, 97, 109, 105, 108, 121, 34, 58, 34, 109, 101, 109, 111, 114, 121, 95, 114, 101, 116, 114, 105, 101, 118, 97, 108, 34, 125, 93, 44, 34, 115, 99, 104, 101, 109, 97, 95, 105, 100, 34, 58, 34, 114, 117, 110, 116, 105, 109, 101, 46, 118, 52, 46, 112, 104, 97, 115, 101, 49, 52, 46, 109, 101, 109, 111, 114, 121, 95, 109, 97, 110, 105, 102, 101, 115, 116, 46, 118, 49, 34, 44, 34, 119, 114, 105, 116, 101, 95, 97, 117, 116, 104, 111, 114, 105, 116, 121, 34, 58, 34, 104, 111, 115, 116, 95, 114, 101, 97, 108, 105, 122, 101, 114, 95, 111, 110, 108, 121, 34, 125]
theorem control_false :
    decide (decode controlImage = some Phase17Routing.beforePackage.memory) = false := by
  with_unfolding_all rfl

theorem rejected_control :
    decode controlImage = some Phase17Routing.beforePackage.memory := by
  have h : ¬ (decode controlImage = some Phase17Routing.beforePackage.memory) :=
    of_decide_eq_false control_false
  simp only [h]
  decide +kernel

end Phase17Json
