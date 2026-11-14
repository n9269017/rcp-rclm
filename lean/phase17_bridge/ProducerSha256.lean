/- Phase 17X: selected SHA-256 evaluation of Phase 17W producer preimages.
   Executable mathematical reference for the SHA-256 equations in FIPS 180-4,
   sections 4.1.2, 4.2.2, 5.1.1, 5.2.1, 5.3.3 and 6.2.2.
   Words use natural numbers reduced modulo 2^32. Input is complete byte data;
   length must be below 2^61 bytes. The selected proof checks full padding,
   big-endian words, every schedule recurrence and compression round, ordered
   chaining and the full lowercase digest. Supplied traces are untrusted.
   This does not establish physical capture, origin authenticity, collision
   resistance, Python execution, or general external implementation equivalence. -/
namespace Phase17Sha256
abbrev Word := Nat
abbrev State := List Word
abbrev Block := List Nat
def modulus : Nat := 4294967296
def mask : Nat := 4294967295
def u32 (n : Nat) := n % modulus
def ror (x n : Nat) : Nat := (x >>> n) ||| ((x <<< (32 - n)) &&& mask)
def ch (x y z : Nat) : Nat := (x &&& y) ^^^ ((x ^^^ mask) &&& z)
def maj (x y z : Nat) : Nat := (x &&& y) ^^^ (x &&& z) ^^^ (y &&& z)
def big0 (x : Nat) := ror x 2 ^^^ ror x 13 ^^^ ror x 22
def big1 (x : Nat) := ror x 6 ^^^ ror x 11 ^^^ ror x 25
def small0 (x : Nat) := ror x 7 ^^^ ror x 18 ^^^ (x >>> 3)
def small1 (x : Nat) := ror x 17 ^^^ ror x 19 ^^^ (x >>> 10)
def constants : List Nat := [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2]
def initial : State := [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
def round (s : State) (kw : Nat × Nat) : State :=
  match s with
  | [a,b,c,d,e,f,g,h] =>
      let t1 := u32 (h + big1 e + ch e f g + kw.1 + kw.2)
      let t2 := u32 (big0 a + maj a b c)
      [u32 (t1+t2), a,b,c,u32 (d+t1),e,f,g]
  | _ => []
def nextWord (ws : List Nat) : Nat :=
  let m := ws.length
  u32 (small1 (ws.getD (m-2) 0) + ws.getD (m-7) 0 +
       small0 (ws.getD (m-15) 0) + ws.getD (m-16) 0)
def expand : Nat → List Nat → List Nat
  | 0, ws => ws
  | n+1, ws => expand n (ws ++ [nextWord ws])
def word (bs : List Nat) : Nat := bs.foldl (fun x b => x * 256 + b) 0
def readWords (bs : List Nat) : List Nat := (List.range 16).map (fun n => word ((bs.drop (n*4)).take 4))
def feedForward (before after : State) : State :=
  (before.zip after).map (fun p => u32 (p.1+p.2))
def compress (s : State) (bs : List Nat) : State :=
  let ws := expand 48 (readWords bs)
  let out := (constants.zip ws).foldl round s
  feedForward s out
def be64 (n : Nat) : List Nat := (List.range 8).map (fun i => (n >>> (8*(7-i))) % 256)
def pad (bs : List Nat) : List Nat := bs ++ [128] ++ List.replicate ((55 + 64 - bs.length % 64) % 64) 0 ++ be64 (bs.length*8)
def blocks (bs : List Nat) : List (List Nat) := (List.range (bs.length/64)).map (fun i => (bs.drop (i*64)).take 64)
def hashWords (bs : List Nat) : State := (blocks (pad bs)).foldl compress initial

def hexDigit (n : Nat) : Char := Char.ofNat (if n < 10 then n + 48 else n - 10 + 97)
def wordHex (n : Nat) : List Char :=
  (List.range 8).map (fun i => hexDigit ((n >>> (4*(7-i))) % 16))
def digestHex (state : State) : String := String.ofList (state.flatMap wordHex)
def InputValid (bytes : List Nat) : Prop :=
  bytes.length < 2305843009213693952 ∧ bytes.all (fun b => decide (b < 256)) = true
instance (bytes : List Nat) : Decidable (InputValid bytes) :=
  inferInstanceAs (Decidable (_ ∧ _))
def sha256 (bytes : List Nat) : Option String :=
  if InputValid bytes then some (digestHex (hashWords bytes)) else none

/-- Each constructor contains an independently kernel-checked compression
    equality. The list consumes every complete padded block in order. -/
inductive CompressionChain : State → List Block → State → Prop
  | nil (state : State) : CompressionChain state [] state
  | cons {before after final : State} {block : Block} {rest : List Block}
      (step : compress before block = after)
      (tail : CompressionChain after rest final) :
      CompressionChain before (block :: rest) final

theorem compression_chain_sound {before final : State} {parts : List Block}
    (chain : CompressionChain before parts final) :
    parts.foldl compress before = final := by
  induction chain with
  | nil => rfl
  | cons step tail ih =>
      simp only [List.foldl_cons, step, ih]

theorem sha256_of_chain {bytes : List Nat} {parts : List Block} {final : State}
    {expected : String} (valid : InputValid bytes)
    (partition : blocks (pad bytes) = parts)
    (chain : CompressionChain initial parts final)
    (digest : digestHex final = expected) : sha256 bytes = some expected := by
  simp only [sha256, if_pos valid, hashWords, partition,
    compression_chain_sound chain, digest]


/-- The schedule witness is untrusted. Each newly appended literal word must
    equal the specified small-sigma recurrence over the earlier words. -/
def ScheduleChecked : List Word → List Word → Prop
  | _, [] => True
  | prior, word :: rest =>
      nextWord prior = word ∧ ScheduleChecked (prior ++ [word]) rest
noncomputable instance (prior rest : List Word) : Decidable (ScheduleChecked prior rest) := by
  induction rest generalizing prior with
  | nil => exact isTrue trivial
  | cons first rest ih => exact inferInstanceAs
      (Decidable (nextWord prior = first ∧ ScheduleChecked (prior ++ [first]) rest))

theorem schedule_checked_sound (prior rest : List Word)
    (checked : ScheduleChecked prior rest) :
    expand rest.length prior = prior ++ rest := by
  induction rest generalizing prior with
  | nil => simp only [List.length_nil, expand, List.append_nil]
  | cons first rest ih =>
      change nextWord prior = first ∧ ScheduleChecked (prior ++ [first]) rest at checked
      simp only [List.length_cons, expand, checked.1]
      rw [ih (prior ++ [first]) checked.2]
      simp only [List.append_assoc, List.singleton_append]

/-- Every supplied working state follows one of the 64 specified rounds;
    the final equality prevents a shortened trace from being accepted. -/
def RoundsChecked : State → List (Word × Word) → List State → State → Prop
  | before, [], [], final => before = final
  | before, kw :: rest, next :: states, final =>
      round before kw = next ∧ RoundsChecked next rest states final
  | _, _, _, _ => False
noncomputable instance (before : State) (kws : List (Word × Word)) (states : List State)
    (final : State) : Decidable (RoundsChecked before kws states final) := by
  induction kws generalizing before states with
  | nil => cases states <;> unfold RoundsChecked <;> infer_instance
  | cons kw rest ih =>
      cases states with
      | nil => exact isFalse id
      | cons next states => exact inferInstanceAs
          (Decidable (round before kw = next ∧ RoundsChecked next rest states final))

theorem rounds_checked_sound (before : State) (kws : List (Word × Word))
    (states : List State) (final : State)
    (checked : RoundsChecked before kws states final) :
    kws.foldl round before = final := by
  induction kws generalizing before states with
  | nil => cases states with
      | nil => exact checked
      | cons _ _ => exact False.elim checked
  | cons kw rest ih =>
      cases states with
      | nil => exact False.elim checked
      | cons next states =>
          change round before kw = next ∧ RoundsChecked next rest states final at checked
          simp only [List.foldl_cons, checked.1]
          exact ih next states checked.2

structure BlockTrace where
  schedule : List Word
  roundStates : List State
  finalState : State
  deriving DecidableEq

def BlockChecked (before : State) (block : Block) (trace : BlockTrace) (after : State) : Prop :=
  trace.schedule.length = 64 ∧
  trace.schedule.take 16 = readWords block ∧
  ScheduleChecked (trace.schedule.take 16) (trace.schedule.drop 16) ∧
  RoundsChecked before (constants.zip trace.schedule) trace.roundStates trace.finalState ∧
  feedForward before trace.finalState = after
noncomputable instance (before : State) (block : Block) (trace : BlockTrace) (after : State) :
    Decidable (BlockChecked before block trace after) :=
  inferInstanceAs (Decidable (_ ∧ _ ∧ _ ∧ _ ∧ _))

theorem block_checked_sound (before : State) (block : Block) (trace : BlockTrace)
    (after : State) (checked : BlockChecked before block trace after) :
    compress before block = after := by
  rcases checked with ⟨length, prior, schedule, rounds, final⟩
  have count : (trace.schedule.drop 16).length = 48 := by
    simp only [List.length_drop, length]
  have expanded : expand 48 (readWords block) = trace.schedule := by
    have sound := schedule_checked_sound (trace.schedule.take 16) (trace.schedule.drop 16) schedule
    rw [count, List.take_append_drop, prior] at sound
    exact sound
  simp only [compress, expanded, rounds_checked_sound before _ _ _ rounds, final]

/-- The actual imported W input record now has its complete digest evaluated. -/
def HashEvaluated (record : Phase17Preimages.HashRecord) : Prop :=
  sha256 record.preimage = some record.digest

inductive AllHashed : List Phase17Preimages.HashRecord → Prop
  | nil : AllHashed []
  | cons {record : Phase17Preimages.HashRecord} {rest : List Phase17Preimages.HashRecord}
      (head : HashEvaluated record) (tail : AllHashed rest) : AllHashed (record :: rest)

def digestRecords (records : List Phase17Preimages.HashRecord) : Option (List String) :=
  records.mapM (fun record => sha256 record.preimage)

theorem digest_records_sound (records : List Phase17Preimages.HashRecord)
    (checked : AllHashed records) :
    digestRecords records = some (records.map Phase17Preimages.HashRecord.digest) := by
  induction checked with
  | nil => rfl
  | cons head tail ih =>
      unfold HashEvaluated at head
      simp only [digestRecords, List.mapM_cons, head, List.map_cons]
      change (do
        let rest ← digestRecords _
        pure (_ :: rest)) = some (_ :: _)
      rw [ih]
      rfl

/-- Compose W's checked canonical input construction with X's checked hash
    evaluation. Neither premise asserts physical origin authenticity. -/
theorem preimage_digest_bound (value : Phase17Routing.Value)
    (record : Phase17Preimages.HashRecord)
    (encoded : Phase17Preimages.HashInputChecked value record)
    (evaluated : HashEvaluated record) :
    (Phase17Preimages.hashInput value).bind sha256 = some record.digest := by
  rw [Phase17Preimages.preimage_encoding_bound value record encoded]
  exact evaluated

end Phase17Sha256
