import Phase17TDependency

set_option Elab.async false

/- Phase 17U: complete captured planner bytes to the numerical producer table.
   The fixed reference reads all 32,768 signed little-endian words. It interprets
   the supplied public feature/tie/freeze digests, and reconstructs the actual
   producer rows imported from Q. Capture, hash computation/authenticity,
   descriptor JSON interpretation and external process execution remain outside
   this reference. The fixed external controller is not a self-hosted proposer. -/
namespace Phase17Planner

open Phase17Sparse

abbrev PlannerImage := Phase17Sparse.TensorImage

def Canonical (image : PlannerImage) : Prop :=
  image.byteLength = 65536 ∧
  ((entries image.support).map Prod.fst).Pairwise (· < ·) ∧
  ∀ entry ∈ entries image.support,
    entry.1 < image.byteLength ∧ 0 < entry.2 ∧ entry.2 < 256

def wordAt (image : PlannerImage) (index : Nat) : Int :=
  signed16 (byteAt image (2 * index)) (byteAt image (2 * index + 1))

/-- One complete 256-word interval. Zero words are read, then discarded from
    the sparse result; the support is not assumed complete from a supplied list. -/
def decodedBlock (image : PlannerImage) (block : Nat) : List (Nat × Int) :=
  ((List.range 256).map (fun offset =>
    let index := 256 * block + offset
    (index, wordAt image index))).filter (fun row => row.2 != 0)

/-- All 128 consecutive blocks cover exactly the 32,768-word image. -/
def decodedProjection (image : PlannerImage) : List (Nat × Int) :=
  (List.range 128).flatMap (decodedBlock image)

def expectedBlock (projection : List (Nat × Int)) (block : Nat) : List (Nat × Int) :=
  projection.filter (fun row => decide (256 * block ≤ row.1 ∧ row.1 < 256 * (block + 1)))

theorem word_projection_sound (image : PlannerImage) (index : Nat) (value : Int)
    (member : (index, value) ∈ decodedProjection image) :
    index < 32768 ∧ wordAt image index = value ∧ value ≠ 0 := by
  rcases List.mem_flatMap.mp member with ⟨block, blockMember, member⟩
  have blockBound : block < 128 := List.mem_range.mp blockMember
  rcases List.mem_filter.mp member with ⟨member, nonzero⟩
  rcases List.mem_map.mp member with ⟨offset, offsetMember, equal⟩
  have offsetBound : offset < 256 := List.mem_range.mp offsetMember
  have indexes : 256 * block + offset = index := congrArg Prod.fst equal
  have values : wordAt image (256 * block + offset) = value := congrArg Prod.snd equal
  refine ⟨by omega, ?_, ?_⟩
  · simpa only [indexes] using values
  · simpa using nonzero

theorem nonzero_word_covered (image : PlannerImage) (index : Nat)
    (bounded : index < 32768) (nonzero : wordAt image index ≠ 0) :
    (index, wordAt image index) ∈ decodedProjection image := by
  have blockBound : index / 256 < 128 := by omega
  have offsetBound : index % 256 < 256 := Nat.mod_lt _ (by decide)
  have position : 256 * (index / 256) + index % 256 = index := by omega
  apply List.mem_flatMap.mpr
  refine ⟨index / 256, List.mem_range.mpr blockBound, ?_⟩
  apply List.mem_filter.mpr
  constructor
  · apply List.mem_map.mpr
    refine ⟨index % 256, List.mem_range.mpr offsetBound, ?_⟩
    simp only [position]
  · simpa using nonzero

theorem projection_from_blocks (image : PlannerImage) (projection : List (Nat × Int))
    (blocks : ∀ block < 128, decodedBlock image block = expectedBlock projection block)
    (partition : (List.range 128).flatMap (expectedBlock projection) = projection) :
    decodedProjection image = projection := by
  unfold decodedProjection
  rw [← partition]
  exact List.flatMap_congr (fun block member => blocks block (List.mem_range.mp member))

/-- Strict lower-case hexadecimal interpretation, including the entire digest
    suffix even when only its first sixteen digits determine a tie or offset. -/
def hexDigit (byte : Nat) : Option Nat :=
  if 48 ≤ byte ∧ byte ≤ 57 then some (byte - 48)
  else if 97 ≤ byte ∧ byte ≤ 102 then some (byte - 87)
  else none

theorem hex_digit_bound (byte value : Nat) (decoded : hexDigit byte = some value) :
    value < 16 := by
  unfold hexDigit at decoded
  split at decoded
  · simp only [Option.some.injEq] at decoded
    omega
  · split at decoded
    · simp only [Option.some.injEq] at decoded
      omega
    · contradiction

def hexDigits (digest : String) : Option (List Nat) :=
  let chars := digest.toList
  if chars.length = 64 then chars.mapM (fun char => hexDigit char.toNat) else none

def prefix16 (digest : String) : Option Nat := do
  let digits ← hexDigits digest
  pure ((digits.take 16).foldl (fun result digit => 16 * result + digit) 0)

structure RowInput where
  key : String
  family : Nat
  variant : Nat
  generation : Nat
  familyCount : Nat
  featureDigest : String
  tieDigests : List String
  deriving DecidableEq

def feature (row : RowInput) (digits : List Nat) (position index : Nat) : Int :=
  Int.ofNat ((digits.getD ((index + 11 * position) % 64) 0 +
    3 * row.family + 5 * row.variant + row.generation + position) % 9) - 4

def scoreTerms (projection : List (Nat × Int)) (row : RowInput)
    (digits : List Nat) : List Int :=
  projection.zipIdx.map (fun pair => pair.1.2 * feature row digits pair.2 pair.1.1)

def baseScore (projection : List (Nat × Int)) (row : RowInput)
    (digits : List Nat) : Int :=
  20000 - 521 * Int.ofNat row.familyCount + (scoreTerms projection row digits).sum

def projectedRow (projection : List (Nat × Int)) (row : RowInput) :
    Option Phase17Provenance.RankedProgram := do
  if row.family < 8 ∧ row.variant < 4 ∧ 0 < row.generation ∧
      row.generation ≤ 9223372036854775807 ∧ row.familyCount ≤ 9223372036854775807 ∧
      row.generation = row.familyCount + 1 ∧ row.tieDigests.length = 5 then
    let _ ← hexDigits row.key
    let digits ← hexDigits row.featureDigest
    let ties ← row.tieDigests.mapM prefix16
    pure { key := row.key, family := row.family, baseScore := baseScore projection row digits, ties := ties }
  else none

def projectedRows (projection : List (Nat × Int)) (inputs : List RowInput) :
    Option (List Phase17Provenance.RankedProgram) :=
  inputs.mapM (projectedRow projection)

/-- A complete row check includes every numerical input and the actual imported
    ranked row.  The finite aggregate is assembled from these proofs. -/
def RowChecked (projection : List (Nat × Int)) (input : RowInput)
    (target : Phase17Provenance.RankedProgram) : Prop :=
  (hexDigits input.featureDigest).map (fun digits => (scoreTerms projection input digits).length) =
    some projection.length ∧
  (hexDigits input.featureDigest).map (baseScore projection input) = some target.baseScore ∧
  input.tieDigests.mapM prefix16 = some target.ties ∧
  input.tieDigests.length = 5 ∧ projectedRow projection input = some target

theorem checked_rows_compose (projection : List (Nat × Int))
    (inputs : List RowInput) (targets : List Phase17Provenance.RankedProgram)
    (checked : List.Forall₂ (RowChecked projection) inputs targets) :
    inputs.map (fun row => (hexDigits row.featureDigest).map
      (fun digits => (scoreTerms projection row digits).length)) =
      List.replicate inputs.length (some projection.length) ∧
    inputs.map (fun row => (hexDigits row.featureDigest).map (baseScore projection row)) =
      targets.map (fun row => some row.baseScore) ∧
    inputs.map (fun row => row.tieDigests.mapM prefix16) =
      targets.map (fun row => some row.ties) ∧
    inputs.map (fun row => row.tieDigests.length) = List.replicate inputs.length 5 ∧
    projectedRows projection inputs = some targets := by
  induction checked with
  | nil => simp [projectedRows]
  | @cons input target inputs targets checked rest ih =>
      rcases checked with ⟨terms, score, ties, tieLength, row⟩
      rcases ih with ⟨termsTail, scoreTail, tiesTail, lengthTail, rowTail⟩
      refine ⟨?_, ?_, ?_, ?_, ?_⟩
      · simp only [List.map_cons, terms, termsTail, List.length_cons, List.replicate_succ]
      · simp only [List.map_cons, score, scoreTail]
      · simp only [List.map_cons, ties, tiesTail]
      · simp only [List.map_cons, tieLength, lengthTail, List.length_cons, List.replicate_succ]
      · have rowTail' : inputs.mapM (projectedRow projection) = some targets := rowTail
        simp only [projectedRows, List.mapM_cons, row, rowTail']
        rfl

def decodedRows (image : PlannerImage) (inputs : List RowInput) :
    Option (List Phase17Provenance.RankedProgram) :=
  projectedRows (decodedProjection image) inputs

theorem table_from_projection (image : PlannerImage) (projection : List (Nat × Int))
    (inputs : List RowInput) (bound : decodedProjection image = projection) :
    decodedRows image inputs = projectedRows projection inputs := by
  simp only [decodedRows, bound]

def decodedOffset (freezeDigest : String) : Option Nat :=
  (prefix16 freezeDigest).map (fun value => value % 32)

def decodedContext (original : Phase17Provenance.Context) (image : PlannerImage)
    (inputs : List RowInput) (freezeDigest : String) : Option Phase17Provenance.Context := do
  let rows ← decodedRows image inputs
  let offset ← decodedOffset freezeDigest
  pure { original with rows := rows, offset := offset }

theorem context_reconstruction (original : Phase17Provenance.Context) (image : PlannerImage)
    (inputs : List RowInput) (freezeDigest : String)
    (rows : decodedRows image inputs = some original.rows)
    (offset : decodedOffset freezeDigest = some original.offset) :
    decodedContext original image inputs freezeDigest = some original := by
  simp [decodedContext, rows, offset]

end Phase17Planner

namespace Phase17Planner
open Phase17Sparse RcpRclmFormalCoreV2 RcpRclmFormalCoreV3
set_option maxRecDepth 32768
set_option maxHeartbeats 32000000
-- Fresh U packet SHA256: b5f637e2eb50030a38f193ba888faa157731ceb0cc9505d3f36fea46322c7aae
def expectedProjection : List (Nat × Int) := [(0, (-1)), (17, (-1)), (33, (-1)), (65, (-1)), (66, (-1)), (67, (-1)), (68, (-1)), (69, (-1)), (70, (-1)), (71, (-1)), (72, (-1)), (73, (-1)), (74, (-1)), (75, (-1)), (76, (-1)), (77, (-1)), (78, (-1)), (79, (-1)), (80, (-1)), (81, (-1)), (1027, (-1)), (1031, 1), (1044, (-1)), (1047, 1), (1062, 1), (1066, 1), (1076, (-1)), (1081, (-1)), (2049, (-1)), (2065, 2), (2068, (-1)), (2081, 1), (2103, (-1)), (3075, (-1)), (3077, (-1)), (3092, 3), (3093, (-1)), (3108, (-1)), (3124, (-1)), (3127, 1), (3129, 1), (4117, 1), (4118, (-1)), (4132, 1), (4133, (-1)), (5142, 1), (5143, (-1)), (5157, 1), (5158, (-1)), (6145, 2), (6150, (-1)), (6161, (-1)), (6177, 1), (6185, (-1)), (7169, (-1)), (7171, 2), (7173, (-1)), (7201, (-1)), (7220, 1), (8197, 2), (8199, (-1)), (8212, (-1)), (8234, (-1)), (8244, 1), (9216, 1), (9222, 1), (9257, 1), (12353, 1), (13378, 1), (14403, 1), (15428, 1), (16453, 1), (17478, 1), (18503, 1), (19528, 1), (20553, 1), (21578, 1), (22603, 1), (23628, 1), (24653, 1), (25678, 1), (26703, 1), (27728, 1), (28753, 1)]
def controlImage : PlannerImage := { byteLength := 65536, support := (.node (.node (.node (.node (.node (.node (.node (.node .empty 0 255 .empty) 1 255 .empty) 34 255 (.node .empty 35 255 .empty)) 66 255 (.node (.node .empty 67 255 .empty) 130 255 (.node .empty 131 255 .empty))) 132 255 (.node (.node (.node .empty 133 255 .empty) 134 255 (.node .empty 135 255 .empty)) 136 255 (.node (.node .empty 137 255 .empty) 138 255 (.node .empty 139 255 .empty)))) 140 255 (.node (.node (.node (.node .empty 141 255 .empty) 142 255 (.node .empty 143 255 .empty)) 144 255 (.node (.node .empty 145 255 .empty) 146 255 (.node .empty 147 255 .empty))) 148 255 (.node (.node (.node .empty 149 255 .empty) 150 255 (.node .empty 151 255 .empty)) 152 255 (.node (.node .empty 153 255 .empty) 154 255 (.node .empty 155 255 .empty))))) 156 255 (.node (.node (.node (.node (.node .empty 157 255 .empty) 158 255 (.node .empty 159 255 .empty)) 160 255 (.node (.node .empty 161 255 .empty) 162 255 (.node .empty 163 255 .empty))) 2054 255 (.node (.node (.node .empty 2055 255 .empty) 2063 1 (.node .empty 2088 255 .empty)) 2089 255 (.node (.node .empty 2095 1 .empty) 2125 1 (.node .empty 2133 1 .empty)))) 2152 255 (.node (.node (.node (.node .empty 2153 255 .empty) 2162 255 (.node .empty 2163 255 .empty)) 4098 255 (.node (.node .empty 4099 255 .empty) 4131 2 (.node .empty 4136 255 .empty))) 4137 255 (.node (.node (.node .empty 4163 1 .empty) 4206 255 (.node .empty 4207 255 .empty)) 6150 255 (.node (.node .empty 6151 255 .empty) 6154 255 (.node .empty 6155 255 .empty)))))) 6185 3 (.node (.node (.node (.node (.node (.node (.node .empty 6186 255 .empty) 6187 255 .empty) 6216 255 (.node .empty 6217 255 .empty)) 6248 255 (.node (.node .empty 6249 255 .empty) 6255 1 (.node .empty 6259 1 .empty))) 8235 1 (.node (.node (.node .empty 8236 255 .empty) 8237 255 (.node .empty 8265 1 .empty)) 8266 255 (.node (.node .empty 8267 255 .empty) 10285 1 (.node .empty 10286 255 .empty)))) 10287 255 (.node (.node (.node (.node .empty 10315 1 .empty) 10316 255 (.node .empty 10317 255 .empty)) 12291 2 (.node (.node .empty 12300 255 .empty) 12301 255 (.node .empty 12322 255 .empty))) 12323 255 (.node (.node (.node .empty 12355 1 .empty) 12370 255 (.node .empty 12371 255 .empty)) 14338 255 (.node (.node .empty 14339 255 .empty) 14343 2 (.node .empty 14346 255 .empty))))) 14347 255 (.node (.node (.node (.node (.node .empty 14402 255 .empty) 14403 255 (.node .empty 14441 1 .empty)) 16395 2 (.node (.node .empty 16398 255 .empty) 16399 255 (.node .empty 16424 255 .empty))) 16425 255 (.node (.node (.node .empty 16468 255 .empty) 16469 255 (.node .empty 16489 1 .empty)) 18433 1 (.node (.node .empty 18445 1 .empty) 18515 1 (.node .empty 24707 1 .empty)))) 26757 1 (.node (.node (.node (.node .empty 28807 1 .empty) 30857 1 (.node .empty 32907 1 .empty)) 34957 1 (.node (.node .empty 37007 1 .empty) 39057 1 (.node .empty 41107 1 .empty))) 43157 1 (.node (.node (.node .empty 45207 1 .empty) 47257 1 (.node .empty 49307 1 .empty)) 51357 1 (.node (.node .empty 53407 1 .empty) 55457 1 (.node .empty 57507 1 .empty))))))) }
theorem control_false :
    decide (decodedBlock controlImage 4 = expectedBlock expectedProjection 4) = false := by
  with_unfolding_all rfl

theorem rejected_control :
    decodedBlock controlImage 4 = expectedBlock expectedProjection 4 := by
  have h : ¬ (decodedBlock controlImage 4 = expectedBlock expectedProjection 4) := of_decide_eq_false control_false
  simp only [h]
  decide +kernel

end Phase17Planner
