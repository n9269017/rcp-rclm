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
noncomputable def beforeImage : PlannerImage := { byteLength := 65536, support := (.node (.node (.node (.node (.node (.node (.node (.node .empty 0 255 .empty) 1 255 .empty) 34 255 (.node .empty 35 255 .empty)) 66 255 (.node (.node .empty 67 255 .empty) 130 255 (.node .empty 131 255 .empty))) 132 255 (.node (.node (.node .empty 133 255 .empty) 134 255 (.node .empty 135 255 .empty)) 136 255 (.node (.node .empty 137 255 .empty) 138 255 (.node .empty 139 255 .empty)))) 140 255 (.node (.node (.node (.node .empty 141 255 .empty) 142 255 (.node .empty 143 255 .empty)) 144 255 (.node (.node .empty 145 255 .empty) 146 255 (.node .empty 147 255 .empty))) 148 255 (.node (.node (.node .empty 149 255 .empty) 150 255 (.node .empty 151 255 .empty)) 152 255 (.node (.node .empty 153 255 .empty) 154 255 (.node .empty 155 255 .empty))))) 156 255 (.node (.node (.node (.node (.node .empty 157 255 .empty) 158 255 (.node .empty 159 255 .empty)) 160 255 (.node (.node .empty 161 255 .empty) 162 255 (.node .empty 163 255 .empty))) 2054 255 (.node (.node (.node .empty 2055 255 .empty) 2062 1 (.node .empty 2088 255 .empty)) 2089 255 (.node (.node .empty 2094 1 .empty) 2124 1 (.node .empty 2132 1 .empty)))) 2152 255 (.node (.node (.node (.node .empty 2153 255 .empty) 2162 255 (.node .empty 2163 255 .empty)) 4098 255 (.node (.node .empty 4099 255 .empty) 4130 2 (.node .empty 4136 255 .empty))) 4137 255 (.node (.node (.node .empty 4162 1 .empty) 4206 255 (.node .empty 4207 255 .empty)) 6150 255 (.node (.node .empty 6151 255 .empty) 6154 255 (.node .empty 6155 255 .empty)))))) 6184 3 (.node (.node (.node (.node (.node (.node (.node .empty 6186 255 .empty) 6187 255 .empty) 6216 255 (.node .empty 6217 255 .empty)) 6248 255 (.node (.node .empty 6249 255 .empty) 6254 1 (.node .empty 6258 1 .empty))) 8234 1 (.node (.node (.node .empty 8236 255 .empty) 8237 255 (.node .empty 8264 1 .empty)) 8266 255 (.node (.node .empty 8267 255 .empty) 10284 1 (.node .empty 10286 255 .empty)))) 10287 255 (.node (.node (.node (.node .empty 10314 1 .empty) 10316 255 (.node .empty 10317 255 .empty)) 12290 2 (.node (.node .empty 12300 255 .empty) 12301 255 (.node .empty 12322 255 .empty))) 12323 255 (.node (.node (.node .empty 12354 1 .empty) 12370 255 (.node .empty 12371 255 .empty)) 14338 255 (.node (.node .empty 14339 255 .empty) 14342 2 (.node .empty 14346 255 .empty))))) 14347 255 (.node (.node (.node (.node (.node .empty 14402 255 .empty) 14403 255 (.node .empty 14440 1 .empty)) 16394 2 (.node (.node .empty 16398 255 .empty) 16399 255 (.node .empty 16424 255 .empty))) 16425 255 (.node (.node (.node .empty 16468 255 .empty) 16469 255 (.node .empty 16488 1 .empty)) 18432 1 (.node (.node .empty 18444 1 .empty) 18514 1 (.node .empty 24706 1 .empty)))) 26756 1 (.node (.node (.node (.node .empty 28806 1 .empty) 30856 1 (.node .empty 32906 1 .empty)) 34956 1 (.node (.node .empty 37006 1 .empty) 39056 1 (.node .empty 41106 1 .empty))) 43156 1 (.node (.node (.node .empty 45206 1 .empty) 47256 1 (.node .empty 49306 1 .empty)) 51356 1 (.node (.node .empty 53406 1 .empty) 55456 1 (.node .empty 57506 1 .empty))))))) }
noncomputable def afterImage : PlannerImage := { byteLength := 65536, support := (.node (.node (.node (.node (.node (.node (.node (.node .empty 0 255 .empty) 1 255 .empty) 34 255 (.node .empty 35 255 .empty)) 66 255 (.node (.node .empty 67 255 .empty) 130 255 (.node .empty 131 255 .empty))) 132 255 (.node (.node (.node .empty 133 255 .empty) 134 255 (.node .empty 135 255 .empty)) 136 255 (.node (.node .empty 137 255 .empty) 138 255 (.node .empty 139 255 .empty)))) 140 255 (.node (.node (.node (.node .empty 141 255 .empty) 142 255 (.node .empty 143 255 .empty)) 144 255 (.node (.node .empty 145 255 .empty) 146 255 (.node .empty 147 255 .empty))) 148 255 (.node (.node (.node .empty 149 255 .empty) 150 255 (.node .empty 151 255 .empty)) 152 255 (.node (.node .empty 153 255 .empty) 154 255 (.node .empty 155 255 .empty))))) 156 255 (.node (.node (.node (.node (.node .empty 157 255 .empty) 158 255 (.node .empty 159 255 .empty)) 160 255 (.node (.node .empty 161 255 .empty) 162 255 (.node .empty 163 255 .empty))) 2054 255 (.node (.node (.node .empty 2055 255 .empty) 2062 1 (.node .empty 2088 255 .empty)) 2089 255 (.node (.node .empty 2094 1 .empty) 2124 1 (.node .empty 2132 1 .empty)))) 2152 255 (.node (.node (.node (.node .empty 2153 255 .empty) 2162 255 (.node .empty 2163 255 .empty)) 4098 255 (.node (.node .empty 4099 255 .empty) 4130 2 (.node .empty 4136 255 .empty))) 4137 255 (.node (.node (.node .empty 4162 1 .empty) 4206 255 (.node .empty 4207 255 .empty)) 6150 255 (.node (.node .empty 6151 255 .empty) 6154 255 (.node .empty 6155 255 .empty)))))) 6184 3 (.node (.node (.node (.node (.node (.node (.node .empty 6186 255 .empty) 6187 255 .empty) 6216 255 (.node .empty 6217 255 .empty)) 6248 255 (.node (.node .empty 6249 255 .empty) 6254 1 (.node .empty 6258 1 .empty))) 8234 1 (.node (.node (.node .empty 8236 255 .empty) 8237 255 (.node .empty 8264 1 .empty)) 8266 255 (.node (.node .empty 8267 255 .empty) 10284 1 (.node .empty 10286 255 .empty)))) 10287 255 (.node (.node (.node (.node .empty 10314 1 .empty) 10316 255 (.node .empty 10317 255 .empty)) 12290 2 (.node (.node .empty 12300 255 .empty) 12301 255 (.node .empty 12322 255 .empty))) 12323 255 (.node (.node (.node .empty 12354 1 .empty) 12370 255 (.node .empty 12371 255 .empty)) 14338 255 (.node (.node .empty 14339 255 .empty) 14342 2 (.node .empty 14346 255 .empty))))) 14347 255 (.node (.node (.node (.node (.node .empty 14402 255 .empty) 14403 255 (.node .empty 14440 1 .empty)) 16394 2 (.node (.node .empty 16398 255 .empty) 16399 255 (.node .empty 16424 255 .empty))) 16425 255 (.node (.node (.node .empty 16468 255 .empty) 16469 255 (.node .empty 16488 1 .empty)) 18432 1 (.node (.node .empty 18444 1 .empty) 18514 1 (.node .empty 24706 1 .empty)))) 26756 1 (.node (.node (.node (.node .empty 28806 1 .empty) 30856 1 (.node .empty 32906 1 .empty)) 34956 1 (.node (.node .empty 37006 1 .empty) 39056 1 (.node .empty 41106 1 .empty))) 43156 1 (.node (.node (.node .empty 45206 1 .empty) 47256 1 (.node .empty 49306 1 .empty)) 51356 1 (.node (.node .empty 53406 1 .empty) 55456 1 (.node .empty 57506 1 .empty))))))) }
noncomputable def expectedProjection : List (Nat × Int) := [(0, (-1)), (17, (-1)), (33, (-1)), (65, (-1)), (66, (-1)), (67, (-1)), (68, (-1)), (69, (-1)), (70, (-1)), (71, (-1)), (72, (-1)), (73, (-1)), (74, (-1)), (75, (-1)), (76, (-1)), (77, (-1)), (78, (-1)), (79, (-1)), (80, (-1)), (81, (-1)), (1027, (-1)), (1031, 1), (1044, (-1)), (1047, 1), (1062, 1), (1066, 1), (1076, (-1)), (1081, (-1)), (2049, (-1)), (2065, 2), (2068, (-1)), (2081, 1), (2103, (-1)), (3075, (-1)), (3077, (-1)), (3092, 3), (3093, (-1)), (3108, (-1)), (3124, (-1)), (3127, 1), (3129, 1), (4117, 1), (4118, (-1)), (4132, 1), (4133, (-1)), (5142, 1), (5143, (-1)), (5157, 1), (5158, (-1)), (6145, 2), (6150, (-1)), (6161, (-1)), (6177, 1), (6185, (-1)), (7169, (-1)), (7171, 2), (7173, (-1)), (7201, (-1)), (7220, 1), (8197, 2), (8199, (-1)), (8212, (-1)), (8234, (-1)), (8244, 1), (9216, 1), (9222, 1), (9257, 1), (12353, 1), (13378, 1), (14403, 1), (15428, 1), (16453, 1), (17478, 1), (18503, 1), (19528, 1), (20553, 1), (21578, 1), (22603, 1), (23628, 1), (24653, 1), (25678, 1), (26703, 1), (27728, 1), (28753, 1)]
noncomputable def rowInputs : List RowInput := [
  { key := "0ccebe71727ce54ff3a19b21fe576e09d43e44f9e2e08ad36dcef047c1f79757", family := 7, variant := 3, generation := 2, familyCount := 1, featureDigest := "1def3fea12cc4de310de8b141cd9eabae213f07169a5f95820552fbb30b75e0b", tieDigests := ["84729ab1a2b2a8b3bc6f43bfc6aaedf458e7112a3b7a295d7d2202bfcaf26857", "3754093ec6707feebf6c8193cb0a17a3f401478084f1a681715fd9ac7e7be413", "0b75a4189b1c4ceea56fe8184c7f26d887c5af250927441f173acc421b5c9aff", "ebf0cd5245943ffc0f11e3db92a482fccd1fa7ecc63a44cc2b2691ac1a4ae3fc", "b9496fe33ddcb6ad7fc66c426b313a5f2d21e584b272b462633820d3781d8929"] },
  { key := "0e14e91e830ffbf45bf7393807a5aade7d3ee8687c812c947e3cc2531cbf63ac", family := 0, variant := 1, generation := 2, familyCount := 1, featureDigest := "7bbca756d41c2a7a7bacdc917e8c3ac4624eac62b2713710f763515eb5db36d2", tieDigests := ["226516c7e8d5596f569d1a8e5a2b3cd0bc271427ad27c0ecbf81f6b57cbf5c2b", "44b94c85a9d57ac59f57a226b85e0db10db32a388f72822b3ee06c992d372fdb", "58f7dd46f5def306fcb735371422eeb8c3ce01f2e5a0c5cdb4dedb151fe75f31", "694495e7583b208e598c36b7c5f23497aa70239d17d324e16150d07bdc63667f", "07d4f4cd6c1f243163845f5d38f800786fa4a0d1a1dc732d13d44b9b39e03674"] },
  { key := "1ecfac36f3c68428ba26508bca2f0c8db4a78db705c2389bf06c702fbd5f10b5", family := 4, variant := 3, generation := 2, familyCount := 1, featureDigest := "12fedb8602343995a86dbad620cec9cf6a24b6e2e7ca67e69dae8cbb79be6a62", tieDigests := ["602070fa5d8fb28329397d6c6b80153ea681c1f2cc178f4c9b40b175ac45358a", "dd31df9782e15dff67f6d2ab06c3ab53bdae41973c6888bf5ecccc80a8f7249a", "908b71bde7ec2737f95ed91e8c69deb6e307edab26588aec0f3a12c91ebda203", "c0144f0afe2006043cc8b445b6978f383c32d54d19d7fd802f38a7ffbfe6a841", "d75b2cfcb1b728097e4cc6856e3a9c345df9b756af4f8ce6095991c756cbb142"] },
  { key := "2cf62e580eb264801c146a82d7946b8ff3876c007ef906f4fa2ae155c2763933", family := 4, variant := 0, generation := 2, familyCount := 1, featureDigest := "e8e99d7e2fb0f36eaa143c15b059460c67aa9cf4cf81449aef3598185eada7af", tieDigests := ["711b171d0fee0cf5f296a3f26ca039826ff503a1737d9102cab72792b0facbd3", "d88827c496d8cb3acdcded7bc7438678b884dc20e4d9b5e1f0b128af1b692138", "b9dd55779571fec1c94e5a28cc68e1ec8fbc04d2a9320dc77f68d8c17704572c", "6dadd4a49a706b9a1001ce47df33a476299fdb40c17034158d9b3db6acc27fa5", "902fbbe19a2497f20622bd0a058be5f6372aec757b8fc81ff705a851c99cef63"] },
  { key := "2ecde82a7df7ff5575e47e129aa9f6763c0e9ee3000ef68a9e34d3c9597fe4a8", family := 7, variant := 2, generation := 2, familyCount := 1, featureDigest := "db0bb39e1fcd7cd2821035054d1572b6363ae05bb83d597dc4f889b62deb8931", tieDigests := ["56f9bdc905e0ae96eca512154e3ce2b16ea99b743abc65a2178e66a4b85fa0c3", "a3cb1b95ac327adc9ee0067edb83c904b06bca1b86d15fec80b123b802afeb6f", "3198e1879ccab067c2b16ed933deee5cd9de17a819024892e0ba4ea89d4a092f", "404ae247983fb6df785e361c91bc0343d7920977889c8b32be6d46bfcc7bbd1b", "701dd984d2925c42b469002b7c2ec11e6ae9e88ea3df9c08acb812bbbd99be1d"] },
  { key := "3c53b375ed7d796a6ead3f57edff0ca2bec48cd0d82d3f00e94891e20f67cf37", family := 2, variant := 0, generation := 2, familyCount := 1, featureDigest := "2a58fd4b47e1ab907aea3016997db5f6f64acc283b9c6f3f4ba2ba7e01bbe830", tieDigests := ["3380ff77d1930d4ac2496f0de77d1fada4a579e83f781614bcc1a26fabb157bb", "825884adcf32a4ddda198904ad3c4e4a38074bff0661bf09cb1128bdd27b18ea", "f6c0eeec34a75bd072668e2db0334ea061b45377a3c92f8c2c0bc980413818c1", "2f23dec53d734ba534fdaf4597ebe0f2a7c58cbcbf481e420130c4c9a7e77ba2", "5f0f2c482a9e38b8e3a389258d11c7adedf3d636da37219abe26a9758af1e40e"] },
  { key := "3d77cb7cac506bf87708193dfc6e6f77e291a65ef4827f51da60cad2816ac308", family := 1, variant := 3, generation := 2, familyCount := 1, featureDigest := "e60d6a0a061f76925069fdb37fc745174dab8f1bc98dc883152e2ca5865d37f3", tieDigests := ["24c50ee788d4639fd24a1c55e527f64b70c0450421556142ee3c554e51b010f5", "5f04c06eb1e8f2d7d3b31c2a639e55dfaeb0272844e65f6da12ffd4d013025fa", "f312e7a131468f3e0f7c1fae99fd8e8a0853c73deb0ad38acf71fcd06b08dd1e", "f8533770005dce6c991e1a21ef0430a4c7ad560e65f00ae94fb22d0b33b2ec7b", "653ecb206c8454d600581d1084c6531d09569dafdc4e99eef77a90db53464a2a"] },
  { key := "4022426ee83c2c3f99e3575db0b0dfdb2ee9c21d84c0dcd4bd16beddc79e9f1e", family := 2, variant := 2, generation := 2, familyCount := 1, featureDigest := "ed0e5c9fe7b499f06338ee6495df5634bade1a7383bf42513e79f3cbe8171f51", tieDigests := ["2ebc6cc6c549986d65758ccb59c9f2394ca864e33c48c8a9968e49aa970d8383", "206647f396c6d7c09e7f161dc295d172e169bfae96c61df3f7f8e063a0c97d67", "da6922ba560c3ca5f6a20882f667d27884a19928a77b99455ddd12e375614393", "c092ef022bc4ba39dd009d4f27bc7c2425ff67d5aeca1d75dd4243bf17fd9891", "ed2e1e98db69d04e3ed49a2fd9949525b1b55eb970aa3dccb944bfca0f068bef"] },
  { key := "4677d24595acdc93eb98a8756accf75cc209e7cb65f3da91fc413998d938bc90", family := 1, variant := 0, generation := 2, familyCount := 1, featureDigest := "9c8301e4300676a607ccd5d59dd8345de4c3a5aa6f496402499cbd9fd1510ab8", tieDigests := ["216dcbbbf7907641984657ba2b6c55dba8d63c64244e776b6abbd156c16ff4d3", "d9dbd5d9d9e28512aa1d78be07a167c583e30c945e086e2d9296746037f24b83", "a60f6f2187afe48979e13bc3cd35c02b57ef6636e608cbf1c1e0688ee4734fc1", "c8dfecde629b154610ba80d48e90fc3bbb1132bf8377a025302e4459d25ae6ac", "018fd4cdce286718f09427d7739981467ed06bf1f400e0fdaea33b028ceec25e"] },
  { key := "4a94e6caf0ffc3e0042b150248d3b002375fe03953dbe05505f1eec92e7540f3", family := 5, variant := 0, generation := 2, familyCount := 1, featureDigest := "f80d9b31d1108291d6a5b39aed69fb5a45638b9819734bcc8acb36f4417e5903", tieDigests := ["fa2ae309e0ffc7c5490d4fbd6fa5e4d7a20ee6cf3b02a8979f42696313b3d51c", "7834008785949d6dc8b899688f879aad2030f3b8506f14d78be376bdeccc5380", "38f73afabfa760c788eccf33bd281112c25913eb4b16fdf19c44cd82f16bfc75", "ab208ef56988e6442980fa203013c373b75b14486a643945b4337537bf6ebe28", "f7837e566771aba6d1e2b1f63a7c39332cb20733f3b4ff911abc423b6228b97b"] },
  { key := "4e46438f039bc9e03f8418bb954a356470a2b7ab19cf6325098d1a3c84693436", family := 3, variant := 0, generation := 2, familyCount := 1, featureDigest := "aaa76fd32819ed8fa7ea399c2ed361dfaee2e988bfe1e0d142e2ee97e50fb1dd", tieDigests := ["897b40325dccb1dd4d5a857a2a8ffbe6403cfdb68cae50385285dff0f7b68cf5", "d4f0f8ed602b9f37e5c985bd7c41fb4f446ca416eca8156b8e87806f01506c63", "9caa070667f723826f17fadf09e296b3a1772adcf6fa1902ef982502f21e9533", "60e215d4b1d2efea1a81bec743664710bcb0ea927026f4c5996ffcc4e7bc7a81", "eafc4c05327cc0d00f2af99748846330a22241887eb87a00134ee8900ac0d08e"] },
  { key := "5e093ff6378d7f51505e59154e642e54387f7e69536a47f038047309db2f21e4", family := 6, variant := 2, generation := 2, familyCount := 1, featureDigest := "7765aef4e660b6086f8934ea1828dc2f0e3f6efcbf3a10cb4762f8894902a637", tieDigests := ["acae0727a98ee636ed44dda1ce02fed94a92c626d85bab0a3e653c2a39e2006c", "2701649ffd7870078b1457c5e083ae949a092f8f374233f07449d7464d117267", "3c3b5057a68ca341bd8fbd2c4085745d74f0a1a05113d62a8fa48dcc4d6d683b", "ae06274159a9312a03d8d7dcb2bb8cfff623a2e0342409a76927b0907a3fa267", "b02d5a3b3678caadb64060c2785d4bf6b7dae1f08673b17159e7cb3bcace1a81"] },
  { key := "62284df64ad409933f2b7fb08307d037bc75b0af758f5b3f81de191803d00c6d", family := 4, variant := 1, generation := 2, familyCount := 1, featureDigest := "ca346586a9c268112b4a2edbc7c2fd94c8ceca5a47f8285078646254980b8c92", tieDigests := ["f1677dd95cde02f34356e20c8d8c42541c6bcaa0c97682ad01dd10eee13044c9", "c0174565295cf7364abddbe69ed995ed9e94309a312c440a0b8f343175c83e60", "5f4252d4c9947deeee9780481e9cb75dd90f79f5a13d9f010241174d69d7891f", "30c94df84d43a5d31c565c637eccf5d2694e0c3cbe24997c0f274e5cf8f3b57e", "06f4367eda133ad9b900138f72b93d40ed3e89f7665e33387882a56fda83c81e"] },
  { key := "634b6e89afa828bd87e36e8862f536c3053b84fa776eb102c3dc8d948d6915e7", family := 3, variant := 3, generation := 2, familyCount := 1, featureDigest := "e316da34e28db4904a7d3a9387050349a6450b4665d3907dd512b3050ce4766a", tieDigests := ["674c6594f88be2d241e19df80a599031202d813dbed796eebfc8d183b670a459", "ec2468c901a90b13c3bb7a9d8b957e0712a451e8636f1fa2a2cd9bf8cc57459c", "c361d522f633ecaddb8b7457c223813ec2a8fc36d0e377ff2352daef3d92e57d", "0cd151cc2096e7c2af4574d044c2b1279155b18d77fea1e2b8f908bac3dfba37", "1d6176b27fc6c447eca8ab1a0b41755cfbebc8a6321d61b113d4c331aec98e18"] },
  { key := "64ce7d9730e3f4d704c430a159c9dbc6d4d405d89f1148508e443202b8d653c3", family := 6, variant := 0, generation := 2, familyCount := 1, featureDigest := "7660a79fec41c7d2370cf489046cad0e0128c9e4f2eaa12c8cc21b9ff8ecef6d", tieDigests := ["19546a25fd727ae33d28cf755514f3deaae8b2fcdbc8df85f1358af152e1fa42", "6c38ad88fc41429cd000a7ba6444048d4822b3ebb8f2703cc96203ad52da5d00", "feff9b5667feed393d5960387cdc25fe627ebf1131702a6cc16e3dcb547a1d90", "8a805a795e1d7709e721ff33483829dfe83120d41509da70901454b461369aa2", "d29a0b3647f603735e18196e6b9836aebc397ccd7628439d036bf5dce2d78b7f"] },
  { key := "6ad7e6e11c5a715041c0d1e037b0d48ae072191e1433ae35c64e780231ecdc50", family := 1, variant := 1, generation := 2, familyCount := 1, featureDigest := "5dc550ad6e6b974b6b81a6e7c5b3536a9e3b7464538ab5ed4349a7fb312451f6", tieDigests := ["1fc09dc871a6758c09977302a815833baa466409195927b6afd9a6010472fd07", "81ce86c24b0d9e14ed65b96b28d367e61e2c40dd36f0af55c03846f7d8b0cb9a", "4142d77dafe64560507c54d01b95e429c420c698619091ca1b03294f49914c5a", "4ef951176ca3617745d8f7beb94e73f7a5fbc61f2c14bb25cb95c1ebbb15cbdb", "24f6e7a35a415657e9c794c8ce682a2fbb229051b9bf10f7734192212e76882e"] },
  { key := "71c947eeb13f0c166058414f7b64faf6798de23a191e36126957cfaae536a0bd", family := 2, variant := 1, generation := 2, familyCount := 1, featureDigest := "0e0e313c0e29b43c1672992a3287e93a0d45abfb03e43998e90abca225ea1562", tieDigests := ["560dda557f9154f928586ee0ceadf7fcc15e3aded5649f5fbc58374a987d8e79", "8849797d6adf1943e233a75d0bbbf071796e294359c12108740f3ec7babd0c16", "64f402989dc489cb028ae12098831ddfe131e92a0cc97fb5240f1a547561f7ab", "1326ae89d1880e43d06d6e91636a5786f5fd0cf836af1b16e2adc312856d2782", "170b0740e187c11d618b99e38901900fc2ff83c17e15b5c591603283454b1e60"] },
  { key := "74c67d91d381e32057f708cf07cb671d2575c852b66bd54c78ab0172577e888f", family := 1, variant := 2, generation := 2, familyCount := 1, featureDigest := "2aee005eacb4b0ef393838a2749ff4eb7e14b4e100bde3c6c5f1341db868e7a4", tieDigests := ["76879bea4b0cb9f88d8c3c03640f3aed5f7f7b73e6caf92a05e7911a2f7e54d9", "bc6cbcc131b5f2349e678af135572c156f186774f43e10d810d08f4019762813", "aa7b85c79a583f2b10bc47d9417ae8a116a5e6efcbc5b4eb7707f7481ba2dc27", "783200ea1beb87c7f6faf52a127f2eabbd51657e67a0a849c2782201da39d423", "5caf0663cee26758dc33fce090c2b1ca8c10cb2ccd4db54eaa2b2c2272a9b494"] },
  { key := "7936853f064d99b4c87ad0c017a502799a20b398a9948c9a4b71cae0642095e9", family := 5, variant := 1, generation := 2, familyCount := 1, featureDigest := "adabf1f0d08ba195f282a2bb4d26aa49c8f90c9a1adeb8450078bcd480016154", tieDigests := ["0df326f38acd20cab70dfe88131652e65eb72d8a5c2e7246d3e2d5611c73ec89", "d3ab1b61ac24eeeec6dd7cabad2ad2958a1672e5e6ef335c75492bf6cc1c25d7", "17472996f6fdeaf52924b8598e43c5815ab2927b7c11355c190f0deba0044a52", "cd4c281b203814334e27b42ad0ce0c7667e35d5fea7079d1163683a807c00f80", "17990db9de640fba9abe7ca7b234d69136048791932272dd13934718ec441415"] },
  { key := "7cf429d12e04c55acef236646a2b0a8e5a0b3c13371df064c5d8dad2fbf5bb4f", family := 7, variant := 0, generation := 2, familyCount := 1, featureDigest := "b76b4ff382ab9475f0673ce25ef591c00a361df3b642a2a9325eb6aec99e5b13", tieDigests := ["769b73a3a663da30faaa5ba9cc8ea15e5e933cf4e1d8754e32f3786e9f9eb5b1", "7045c2b3c7068942396b9aea7f871ea1f32c00e3dca7cea9607118e129deb582", "8a6ca6dfff5ca0bc52e7fed44a0ae193a3d8687e48baadc520c5c6821362a2e9", "f3aefd6eb853dd153311c3f589b5b25f28b2b879b003c0147feed8d93df9bfe3", "939f340127b1faee26a97d9161616ac0b1bdc439a412914d47fa6410704139c0"] },
  { key := "7ec7d557c116962ac4a13ef48d12e24f0cb56c5262bae03a84c40d88cbc54d7d", family := 5, variant := 3, generation := 2, familyCount := 1, featureDigest := "1d2ca1934d51eaaf32d2962367a1df75f9d37ef3864b6684b5d2f4d2cec23cd5", tieDigests := ["e78945f362714833731d4ff8b4b5bfee1289b148fee3c671d5ec7426ecbb38ed", "36bb9822ab8adc51f711aebe6b4555fc765bf4c25cb839e103d35cb9de48a7fd", "d51c79a124badd3a275a8a0535cb78d8c8f1147f2f95f9e1d21aa228489946f1", "7cf12a7800063c99230f15d8bc9814486ad281aad2163f47c02e04c7f061254b", "1cdcf0e71426b4b51f3abbc9721d96df77098aa087aa02b4a5a15a219f29cf6a"] },
  { key := "836a08670cdfdcb082f55c64677c8eaca60a62d0005749e54e72eb67f94554c0", family := 0, variant := 2, generation := 2, familyCount := 1, featureDigest := "b5d3146a69cdfae6c02f5e0c3168f8fbc1f9df2d9ef7c4baeabf6032775120a2", tieDigests := ["593e2eb823eeaa60b934c2b45a4bf0e27b1c1ac088eeaaf799d4435912ebd238", "2e2bd6c6661de752e89df46bbadcc9da923d568cb671d58947650dcf59113046", "6524ede4e9651410e1c3c966993e53c6bab0975bb543442420fcf9f0cb455e65", "ecc6110207e6a68cad54fe8faa6e6f0ffba6ef254f62ecb606f7cf1edd78ae00", "6cc191e18b5435f1c66ac04e002be29d551dab812444ab4b652b36304389d9a8"] },
  { key := "9862ef65bf4a9113a26f1734ad6ec98e0640eb6656cb1a4334972a2f9be1c6ac", family := 4, variant := 2, generation := 2, familyCount := 1, featureDigest := "041b6edd73e6c497e3e8e0ee7de83c577e92258add9ac66c1743c68adde214ce", tieDigests := ["72a1b26a72f5a47e521f452161067c41e11e92d1eea2c9a730e595a62bf512d0", "6f237bb314fa09101a1279231d9720ed02788dcfaed1491df79078d520b85afe", "6df43d671a1450d9f4920711cb38b710eb2252b2b460c8f7b36d6fe371134bfa", "fdb6ad978adbba5071f263d42f1e4ec5b034035ac802c5a62c22debc09ce8966", "963eebd2ea420a1925b36ea2820534f01e3b16b9b39fc0dce59f7b8589980ab8"] },
  { key := "a342c721f01211e03af69b331f4a012efb6a1efa012a406078278419e9272cc7", family := 5, variant := 2, generation := 2, familyCount := 1, featureDigest := "92cff5837ab0b5a9e9b5960105b4e34baa53cfe0d897538f62362a0b81cd97dd", tieDigests := ["42274ff995fe1a4d004f52c6a8eba772b4cf5323fed539f9baed9584235729a1", "2a495fd3fe72c79075bc77d67565d18dad80f777eb9798079a0a374006336df9", "89f2e02bd72b1a8152d7e13d909ba4aa7a7fe7bcc191920fae620ef2e05e28c1", "4279cf41aec7e4b52b6c27f7c9b1ac37090d2ef70da63347550a665e3a3da0e6", "c6457c13f965d65de4e2b68222bce04740822f115dd4cdd7af013b66f1b3eac4"] },
  { key := "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", family := 6, variant := 1, generation := 2, familyCount := 1, featureDigest := "dce347e4e383617b1c54af4ddd620fe716d27023acc8ff29ef83b858dead7882", tieDigests := ["a237537b716941373e0e8baa5e7b8148e6f6975f71103f85b414ac14103e8e7d", "badd1246cee4f98437dc81dd2191a4b37a636de3edc754e5c18e1269bd836c3e", "1d17b28b15075736d80e620c4c508bcf27d9f20b5f5550c747b6c23045a2136b", "67527a533cbb0e6735abdef04bc7cca0f4d0b0f816a6d0b5841224a5fa198a3f", "796a739ca935f9694b3d53528281f7d4df9f4bf88e6ce4e9bc556e86bd2af458"] },
  { key := "b1158ed7d34cfcad68c952f03a56102e7cb06b2c773129984a69e603960622d0", family := 2, variant := 3, generation := 2, familyCount := 1, featureDigest := "b50e9c21c8da70990748913ed361128a843344cb8f15c0be6f4925b43a89c507", tieDigests := ["09c2ba98c96877d1b71b5b947fed1a4ec8ee9a2a8c4312fab20d18e441026267", "4a694646368e9e98643b44649cae915cdde6a4f0fb1693ef7bd935d1805ecefe", "d040234d801b27aca0e1eb86dd5d43dd804445cfcd104a5ecfa5598eea7febb5", "8906c4906215304e5a489cb561a106c8fc996072b89818e27c43574cf18ab172", "8e3b2bf1deca823dd49efc6cc4386ec25848da67d88cb3614d9f95fabf6b0abd"] },
  { key := "c1f6e3e15772658a58c60b05772015054da09bb91580e62a49b4d0095f59eb66", family := 7, variant := 1, generation := 2, familyCount := 1, featureDigest := "0442ced3e86757a54fb04ff4ea54ec94ff27ef3ee849faf1e67f3530c06722b2", tieDigests := ["640b4b977be8e93071155fcaa8b6fdd72167012cf152580932ce7e038366a54b", "bee42d64693a33c2c92c102db67032e9afbaeb1890fe2c2d7618667f706fd540", "2499a49fc0edd69bacfdf222fb45e38f8cdd20bc497a4461a96d79c0ed730bb2", "bfc5e768687ee14a3b8d8b13505fad30e9e1f15f039fdeb7482f6567f91de369", "674fba60f58fb4ea637c5e7db9f0ba2a03bba111b56319f69ca1f03fcb5cd604"] },
  { key := "c55761ed74319ddefeb28f554779813e19bb1f9accb4bc85be93b56f01c657e1", family := 3, variant := 2, generation := 2, familyCount := 1, featureDigest := "1852d9dcb632ed4afd69b41ea7e6cc9785941e07b3f830fc4c753c0c73473065", tieDigests := ["7041826c900f0b3d719a1c0396de99978e857e1eddebc01fba519df6ea27a62e", "0d00025a92922519ad3b9fd861d599cc4952b2e92c9553935f10b4d7a5ba1e49", "537e1e5cf17bc72c0ccf64573c02efa29715348a46cdc4d703e620a9fc290a94", "6ecfd034491f508a8cb0c02dea9ee17e331fc8f4f7c5e0b0a4fa30437ae9b8a5", "c3bfd0f7b3d57d359efa55ddaed5b2b0d6675f9c990ac389d56362756de581c4"] },
  { key := "df564cb25de35976dfcbef5e28404498aafd1fce538d0a8aa0e454cf96b11b59", family := 0, variant := 0, generation := 2, familyCount := 1, featureDigest := "a9163c5056f3d609b2ac5eb7a6bf2da1c480599d7ef82b11f9c38354619093e3", tieDigests := ["7aa0900ab58befa5833f418fe7748963fc20017dbe38d214ddbb7460110f3e7b", "753f7feb7f8c0fd6dc09b090bcb24430a53b970ec9de601718fc0a8c389328a0", "75c029d01c8107e59ae764edb606ba488ebf4665ea87d3930eb9e6160c006829", "8517e622f6bed06812915344b2924af2b55687af2b2730a620f56f3a5503372c", "23552d6d4774f6446a4debcc4a8cb5f793c3b961e8289aaaf952a641a94f94b6"] },
  { key := "e2654af87c885cf417002f13400f5bef1ac23eae87fd7b9fd479aae38f443d21", family := 0, variant := 3, generation := 2, familyCount := 1, featureDigest := "a3479737f905a4d94a035d24d7016f834730b468eae09afc764b5dffc592caea", tieDigests := ["de38c4342400b107223f74848a3cc76bbc80678db52712a35b0be47626dd8d85", "6cf92121b94127d8d03087856e0d64a45c00e579b798ae252733aef6463d2a35", "4f3cc806968a744df696870d9adabb72905d5784140f569727b4e41669e1b153", "5c7c6e7bfedf99bcebb144be023dc856cfcfbe77188e8b7c72099bca6cb1e15d", "2d037470b8c7a091015e86d61547096955ca549e5076558fd9047ae6544716a9"] },
  { key := "e7579f5e4f38614a40454dca7ae484ae24ab7ffa0d2a03d8ad282fcb7bead25c", family := 6, variant := 3, generation := 2, familyCount := 1, featureDigest := "f0612dc9dc64716e14f7ae2a6f439d1896786541cede6602c2ebdf78bfe3b2d6", tieDigests := ["bd09b079238d49169cfb29f8c11f704ce508034077567df7f6afb7f2777e8746", "27ba68a31911063623598ac075c3d9b1951f4a024f7f1918c968cdfc6f592f5a", "90fd9fbb387ef2e8f5342363f8356cc16ecf9ab8917db9948ab1f777290a5c75", "f52e45ec734a12d9d76deda55c70a4f161906170fbd40fbbc51a4ff3784c643e", "dbf16aedcfa9d3d25cbf635c90891e1be8fd49f8f62d09e6505cfdd0fe6d0e89"] },
  { key := "f2a5dc234b5f195665d205b53e984e94ad894aa5b27e38b9056b9f03862d236b", family := 3, variant := 1, generation := 2, familyCount := 1, featureDigest := "7c74ab3bd275393849e366391049dffe26e184299a473b531788a9a6d93cf90e", tieDigests := ["7066eff49235c6ed3ca39e2e9eb0bfd82939f14be67f73336af176256c64233c", "18a6e3f29bb13ebd4ca3bf0cf38e5139727dacd33ce43c360db119f6737fba83", "137bb86bd104947e518999d8a03df9e58cf938a61b4c316cf18439d84745918a", "4765319fa1a6ea30247e30fa0983825a465d69cf631f147e8198de1176ef938d", "227ec6dcc2c2c84d346f5b26556363be0110770707a5f12b0bc056e0a301573a"] }
]
noncomputable def freezeDigest : String := "330aa97738a8e3148c0538a7a582f97464f3235c0427be8c6753c432188396ff"
noncomputable def selectedChoices : List Nat := [21, 28, 1, 29, 20, 5, 22, 7, 24]

theorem selected_byte_images :
    Canonical beforeImage ∧ Canonical afterImage ∧ beforeImage = afterImage := by
  unfold Canonical
  decide +kernel

private theorem checked_block_000 : decodedBlock beforeImage 0 = expectedBlock expectedProjection 0 := by decide +kernel

private theorem checked_block_001 : decodedBlock beforeImage 1 = expectedBlock expectedProjection 1 := by decide +kernel

private theorem checked_block_002 : decodedBlock beforeImage 2 = expectedBlock expectedProjection 2 := by decide +kernel

private theorem checked_block_003 : decodedBlock beforeImage 3 = expectedBlock expectedProjection 3 := by decide +kernel

private theorem checked_block_004 : decodedBlock beforeImage 4 = expectedBlock expectedProjection 4 := by decide +kernel

private theorem checked_block_005 : decodedBlock beforeImage 5 = expectedBlock expectedProjection 5 := by decide +kernel

private theorem checked_block_006 : decodedBlock beforeImage 6 = expectedBlock expectedProjection 6 := by decide +kernel

private theorem checked_block_007 : decodedBlock beforeImage 7 = expectedBlock expectedProjection 7 := by decide +kernel

private theorem checked_block_008 : decodedBlock beforeImage 8 = expectedBlock expectedProjection 8 := by decide +kernel

private theorem checked_block_009 : decodedBlock beforeImage 9 = expectedBlock expectedProjection 9 := by decide +kernel

private theorem checked_block_010 : decodedBlock beforeImage 10 = expectedBlock expectedProjection 10 := by decide +kernel

private theorem checked_block_011 : decodedBlock beforeImage 11 = expectedBlock expectedProjection 11 := by decide +kernel

private theorem checked_block_012 : decodedBlock beforeImage 12 = expectedBlock expectedProjection 12 := by decide +kernel

private theorem checked_block_013 : decodedBlock beforeImage 13 = expectedBlock expectedProjection 13 := by decide +kernel

private theorem checked_block_014 : decodedBlock beforeImage 14 = expectedBlock expectedProjection 14 := by decide +kernel

private theorem checked_block_015 : decodedBlock beforeImage 15 = expectedBlock expectedProjection 15 := by decide +kernel

private theorem checked_block_016 : decodedBlock beforeImage 16 = expectedBlock expectedProjection 16 := by decide +kernel

private theorem checked_block_017 : decodedBlock beforeImage 17 = expectedBlock expectedProjection 17 := by decide +kernel

private theorem checked_block_018 : decodedBlock beforeImage 18 = expectedBlock expectedProjection 18 := by decide +kernel

private theorem checked_block_019 : decodedBlock beforeImage 19 = expectedBlock expectedProjection 19 := by decide +kernel

private theorem checked_block_020 : decodedBlock beforeImage 20 = expectedBlock expectedProjection 20 := by decide +kernel

private theorem checked_block_021 : decodedBlock beforeImage 21 = expectedBlock expectedProjection 21 := by decide +kernel

private theorem checked_block_022 : decodedBlock beforeImage 22 = expectedBlock expectedProjection 22 := by decide +kernel

private theorem checked_block_023 : decodedBlock beforeImage 23 = expectedBlock expectedProjection 23 := by decide +kernel

private theorem checked_block_024 : decodedBlock beforeImage 24 = expectedBlock expectedProjection 24 := by decide +kernel

private theorem checked_block_025 : decodedBlock beforeImage 25 = expectedBlock expectedProjection 25 := by decide +kernel

private theorem checked_block_026 : decodedBlock beforeImage 26 = expectedBlock expectedProjection 26 := by decide +kernel

private theorem checked_block_027 : decodedBlock beforeImage 27 = expectedBlock expectedProjection 27 := by decide +kernel

private theorem checked_block_028 : decodedBlock beforeImage 28 = expectedBlock expectedProjection 28 := by decide +kernel

private theorem checked_block_029 : decodedBlock beforeImage 29 = expectedBlock expectedProjection 29 := by decide +kernel

private theorem checked_block_030 : decodedBlock beforeImage 30 = expectedBlock expectedProjection 30 := by decide +kernel

private theorem checked_block_031 : decodedBlock beforeImage 31 = expectedBlock expectedProjection 31 := by decide +kernel

private theorem checked_block_032 : decodedBlock beforeImage 32 = expectedBlock expectedProjection 32 := by decide +kernel

private theorem checked_block_033 : decodedBlock beforeImage 33 = expectedBlock expectedProjection 33 := by decide +kernel

private theorem checked_block_034 : decodedBlock beforeImage 34 = expectedBlock expectedProjection 34 := by decide +kernel

private theorem checked_block_035 : decodedBlock beforeImage 35 = expectedBlock expectedProjection 35 := by decide +kernel

private theorem checked_block_036 : decodedBlock beforeImage 36 = expectedBlock expectedProjection 36 := by decide +kernel

private theorem checked_block_037 : decodedBlock beforeImage 37 = expectedBlock expectedProjection 37 := by decide +kernel

private theorem checked_block_038 : decodedBlock beforeImage 38 = expectedBlock expectedProjection 38 := by decide +kernel

private theorem checked_block_039 : decodedBlock beforeImage 39 = expectedBlock expectedProjection 39 := by decide +kernel

private theorem checked_block_040 : decodedBlock beforeImage 40 = expectedBlock expectedProjection 40 := by decide +kernel

private theorem checked_block_041 : decodedBlock beforeImage 41 = expectedBlock expectedProjection 41 := by decide +kernel

private theorem checked_block_042 : decodedBlock beforeImage 42 = expectedBlock expectedProjection 42 := by decide +kernel

private theorem checked_block_043 : decodedBlock beforeImage 43 = expectedBlock expectedProjection 43 := by decide +kernel

private theorem checked_block_044 : decodedBlock beforeImage 44 = expectedBlock expectedProjection 44 := by decide +kernel

private theorem checked_block_045 : decodedBlock beforeImage 45 = expectedBlock expectedProjection 45 := by decide +kernel

private theorem checked_block_046 : decodedBlock beforeImage 46 = expectedBlock expectedProjection 46 := by decide +kernel

private theorem checked_block_047 : decodedBlock beforeImage 47 = expectedBlock expectedProjection 47 := by decide +kernel

private theorem checked_block_048 : decodedBlock beforeImage 48 = expectedBlock expectedProjection 48 := by decide +kernel

private theorem checked_block_049 : decodedBlock beforeImage 49 = expectedBlock expectedProjection 49 := by decide +kernel

private theorem checked_block_050 : decodedBlock beforeImage 50 = expectedBlock expectedProjection 50 := by decide +kernel

private theorem checked_block_051 : decodedBlock beforeImage 51 = expectedBlock expectedProjection 51 := by decide +kernel

private theorem checked_block_052 : decodedBlock beforeImage 52 = expectedBlock expectedProjection 52 := by decide +kernel

private theorem checked_block_053 : decodedBlock beforeImage 53 = expectedBlock expectedProjection 53 := by decide +kernel

private theorem checked_block_054 : decodedBlock beforeImage 54 = expectedBlock expectedProjection 54 := by decide +kernel

private theorem checked_block_055 : decodedBlock beforeImage 55 = expectedBlock expectedProjection 55 := by decide +kernel

private theorem checked_block_056 : decodedBlock beforeImage 56 = expectedBlock expectedProjection 56 := by decide +kernel

private theorem checked_block_057 : decodedBlock beforeImage 57 = expectedBlock expectedProjection 57 := by decide +kernel

private theorem checked_block_058 : decodedBlock beforeImage 58 = expectedBlock expectedProjection 58 := by decide +kernel

private theorem checked_block_059 : decodedBlock beforeImage 59 = expectedBlock expectedProjection 59 := by decide +kernel

private theorem checked_block_060 : decodedBlock beforeImage 60 = expectedBlock expectedProjection 60 := by decide +kernel

private theorem checked_block_061 : decodedBlock beforeImage 61 = expectedBlock expectedProjection 61 := by decide +kernel

private theorem checked_block_062 : decodedBlock beforeImage 62 = expectedBlock expectedProjection 62 := by decide +kernel

private theorem checked_block_063 : decodedBlock beforeImage 63 = expectedBlock expectedProjection 63 := by decide +kernel

private theorem checked_block_064 : decodedBlock beforeImage 64 = expectedBlock expectedProjection 64 := by decide +kernel

private theorem checked_block_065 : decodedBlock beforeImage 65 = expectedBlock expectedProjection 65 := by decide +kernel

private theorem checked_block_066 : decodedBlock beforeImage 66 = expectedBlock expectedProjection 66 := by decide +kernel

private theorem checked_block_067 : decodedBlock beforeImage 67 = expectedBlock expectedProjection 67 := by decide +kernel

private theorem checked_block_068 : decodedBlock beforeImage 68 = expectedBlock expectedProjection 68 := by decide +kernel

private theorem checked_block_069 : decodedBlock beforeImage 69 = expectedBlock expectedProjection 69 := by decide +kernel

private theorem checked_block_070 : decodedBlock beforeImage 70 = expectedBlock expectedProjection 70 := by decide +kernel

private theorem checked_block_071 : decodedBlock beforeImage 71 = expectedBlock expectedProjection 71 := by decide +kernel

private theorem checked_block_072 : decodedBlock beforeImage 72 = expectedBlock expectedProjection 72 := by decide +kernel

private theorem checked_block_073 : decodedBlock beforeImage 73 = expectedBlock expectedProjection 73 := by decide +kernel

private theorem checked_block_074 : decodedBlock beforeImage 74 = expectedBlock expectedProjection 74 := by decide +kernel

private theorem checked_block_075 : decodedBlock beforeImage 75 = expectedBlock expectedProjection 75 := by decide +kernel

private theorem checked_block_076 : decodedBlock beforeImage 76 = expectedBlock expectedProjection 76 := by decide +kernel

private theorem checked_block_077 : decodedBlock beforeImage 77 = expectedBlock expectedProjection 77 := by decide +kernel

private theorem checked_block_078 : decodedBlock beforeImage 78 = expectedBlock expectedProjection 78 := by decide +kernel

private theorem checked_block_079 : decodedBlock beforeImage 79 = expectedBlock expectedProjection 79 := by decide +kernel

private theorem checked_block_080 : decodedBlock beforeImage 80 = expectedBlock expectedProjection 80 := by decide +kernel

private theorem checked_block_081 : decodedBlock beforeImage 81 = expectedBlock expectedProjection 81 := by decide +kernel

private theorem checked_block_082 : decodedBlock beforeImage 82 = expectedBlock expectedProjection 82 := by decide +kernel

private theorem checked_block_083 : decodedBlock beforeImage 83 = expectedBlock expectedProjection 83 := by decide +kernel

private theorem checked_block_084 : decodedBlock beforeImage 84 = expectedBlock expectedProjection 84 := by decide +kernel

private theorem checked_block_085 : decodedBlock beforeImage 85 = expectedBlock expectedProjection 85 := by decide +kernel

private theorem checked_block_086 : decodedBlock beforeImage 86 = expectedBlock expectedProjection 86 := by decide +kernel

private theorem checked_block_087 : decodedBlock beforeImage 87 = expectedBlock expectedProjection 87 := by decide +kernel

private theorem checked_block_088 : decodedBlock beforeImage 88 = expectedBlock expectedProjection 88 := by decide +kernel

private theorem checked_block_089 : decodedBlock beforeImage 89 = expectedBlock expectedProjection 89 := by decide +kernel

private theorem checked_block_090 : decodedBlock beforeImage 90 = expectedBlock expectedProjection 90 := by decide +kernel

private theorem checked_block_091 : decodedBlock beforeImage 91 = expectedBlock expectedProjection 91 := by decide +kernel

private theorem checked_block_092 : decodedBlock beforeImage 92 = expectedBlock expectedProjection 92 := by decide +kernel

private theorem checked_block_093 : decodedBlock beforeImage 93 = expectedBlock expectedProjection 93 := by decide +kernel

private theorem checked_block_094 : decodedBlock beforeImage 94 = expectedBlock expectedProjection 94 := by decide +kernel

private theorem checked_block_095 : decodedBlock beforeImage 95 = expectedBlock expectedProjection 95 := by decide +kernel

private theorem checked_block_096 : decodedBlock beforeImage 96 = expectedBlock expectedProjection 96 := by decide +kernel

private theorem checked_block_097 : decodedBlock beforeImage 97 = expectedBlock expectedProjection 97 := by decide +kernel

private theorem checked_block_098 : decodedBlock beforeImage 98 = expectedBlock expectedProjection 98 := by decide +kernel

private theorem checked_block_099 : decodedBlock beforeImage 99 = expectedBlock expectedProjection 99 := by decide +kernel

private theorem checked_block_100 : decodedBlock beforeImage 100 = expectedBlock expectedProjection 100 := by decide +kernel

private theorem checked_block_101 : decodedBlock beforeImage 101 = expectedBlock expectedProjection 101 := by decide +kernel

private theorem checked_block_102 : decodedBlock beforeImage 102 = expectedBlock expectedProjection 102 := by decide +kernel

private theorem checked_block_103 : decodedBlock beforeImage 103 = expectedBlock expectedProjection 103 := by decide +kernel

private theorem checked_block_104 : decodedBlock beforeImage 104 = expectedBlock expectedProjection 104 := by decide +kernel

private theorem checked_block_105 : decodedBlock beforeImage 105 = expectedBlock expectedProjection 105 := by decide +kernel

private theorem checked_block_106 : decodedBlock beforeImage 106 = expectedBlock expectedProjection 106 := by decide +kernel

private theorem checked_block_107 : decodedBlock beforeImage 107 = expectedBlock expectedProjection 107 := by decide +kernel

private theorem checked_block_108 : decodedBlock beforeImage 108 = expectedBlock expectedProjection 108 := by decide +kernel

private theorem checked_block_109 : decodedBlock beforeImage 109 = expectedBlock expectedProjection 109 := by decide +kernel

private theorem checked_block_110 : decodedBlock beforeImage 110 = expectedBlock expectedProjection 110 := by decide +kernel

private theorem checked_block_111 : decodedBlock beforeImage 111 = expectedBlock expectedProjection 111 := by decide +kernel

private theorem checked_block_112 : decodedBlock beforeImage 112 = expectedBlock expectedProjection 112 := by decide +kernel

private theorem checked_block_113 : decodedBlock beforeImage 113 = expectedBlock expectedProjection 113 := by decide +kernel

private theorem checked_block_114 : decodedBlock beforeImage 114 = expectedBlock expectedProjection 114 := by decide +kernel

private theorem checked_block_115 : decodedBlock beforeImage 115 = expectedBlock expectedProjection 115 := by decide +kernel

private theorem checked_block_116 : decodedBlock beforeImage 116 = expectedBlock expectedProjection 116 := by decide +kernel

private theorem checked_block_117 : decodedBlock beforeImage 117 = expectedBlock expectedProjection 117 := by decide +kernel

private theorem checked_block_118 : decodedBlock beforeImage 118 = expectedBlock expectedProjection 118 := by decide +kernel

private theorem checked_block_119 : decodedBlock beforeImage 119 = expectedBlock expectedProjection 119 := by decide +kernel

private theorem checked_block_120 : decodedBlock beforeImage 120 = expectedBlock expectedProjection 120 := by decide +kernel

private theorem checked_block_121 : decodedBlock beforeImage 121 = expectedBlock expectedProjection 121 := by decide +kernel

private theorem checked_block_122 : decodedBlock beforeImage 122 = expectedBlock expectedProjection 122 := by decide +kernel

private theorem checked_block_123 : decodedBlock beforeImage 123 = expectedBlock expectedProjection 123 := by decide +kernel

private theorem checked_block_124 : decodedBlock beforeImage 124 = expectedBlock expectedProjection 124 := by decide +kernel

private theorem checked_block_125 : decodedBlock beforeImage 125 = expectedBlock expectedProjection 125 := by decide +kernel

private theorem checked_block_126 : decodedBlock beforeImage 126 = expectedBlock expectedProjection 126 := by decide +kernel

private theorem checked_block_127 : decodedBlock beforeImage 127 = expectedBlock expectedProjection 127 := by decide +kernel

private theorem checked_blocks (block : Nat) (bounded : block < 128) :
    decodedBlock beforeImage block = expectedBlock expectedProjection block := by
  interval_cases block

  · exact checked_block_000

  · exact checked_block_001

  · exact checked_block_002

  · exact checked_block_003

  · exact checked_block_004

  · exact checked_block_005

  · exact checked_block_006

  · exact checked_block_007

  · exact checked_block_008

  · exact checked_block_009

  · exact checked_block_010

  · exact checked_block_011

  · exact checked_block_012

  · exact checked_block_013

  · exact checked_block_014

  · exact checked_block_015

  · exact checked_block_016

  · exact checked_block_017

  · exact checked_block_018

  · exact checked_block_019

  · exact checked_block_020

  · exact checked_block_021

  · exact checked_block_022

  · exact checked_block_023

  · exact checked_block_024

  · exact checked_block_025

  · exact checked_block_026

  · exact checked_block_027

  · exact checked_block_028

  · exact checked_block_029

  · exact checked_block_030

  · exact checked_block_031

  · exact checked_block_032

  · exact checked_block_033

  · exact checked_block_034

  · exact checked_block_035

  · exact checked_block_036

  · exact checked_block_037

  · exact checked_block_038

  · exact checked_block_039

  · exact checked_block_040

  · exact checked_block_041

  · exact checked_block_042

  · exact checked_block_043

  · exact checked_block_044

  · exact checked_block_045

  · exact checked_block_046

  · exact checked_block_047

  · exact checked_block_048

  · exact checked_block_049

  · exact checked_block_050

  · exact checked_block_051

  · exact checked_block_052

  · exact checked_block_053

  · exact checked_block_054

  · exact checked_block_055

  · exact checked_block_056

  · exact checked_block_057

  · exact checked_block_058

  · exact checked_block_059

  · exact checked_block_060

  · exact checked_block_061

  · exact checked_block_062

  · exact checked_block_063

  · exact checked_block_064

  · exact checked_block_065

  · exact checked_block_066

  · exact checked_block_067

  · exact checked_block_068

  · exact checked_block_069

  · exact checked_block_070

  · exact checked_block_071

  · exact checked_block_072

  · exact checked_block_073

  · exact checked_block_074

  · exact checked_block_075

  · exact checked_block_076

  · exact checked_block_077

  · exact checked_block_078

  · exact checked_block_079

  · exact checked_block_080

  · exact checked_block_081

  · exact checked_block_082

  · exact checked_block_083

  · exact checked_block_084

  · exact checked_block_085

  · exact checked_block_086

  · exact checked_block_087

  · exact checked_block_088

  · exact checked_block_089

  · exact checked_block_090

  · exact checked_block_091

  · exact checked_block_092

  · exact checked_block_093

  · exact checked_block_094

  · exact checked_block_095

  · exact checked_block_096

  · exact checked_block_097

  · exact checked_block_098

  · exact checked_block_099

  · exact checked_block_100

  · exact checked_block_101

  · exact checked_block_102

  · exact checked_block_103

  · exact checked_block_104

  · exact checked_block_105

  · exact checked_block_106

  · exact checked_block_107

  · exact checked_block_108

  · exact checked_block_109

  · exact checked_block_110

  · exact checked_block_111

  · exact checked_block_112

  · exact checked_block_113

  · exact checked_block_114

  · exact checked_block_115

  · exact checked_block_116

  · exact checked_block_117

  · exact checked_block_118

  · exact checked_block_119

  · exact checked_block_120

  · exact checked_block_121

  · exact checked_block_122

  · exact checked_block_123

  · exact checked_block_124

  · exact checked_block_125

  · exact checked_block_126

  · exact checked_block_127


theorem selected_complete_word_projection :
    decodedProjection beforeImage = expectedProjection ∧
    decodedProjection afterImage = expectedProjection ∧ expectedProjection.length = 84 := by
  have before : decodedProjection beforeImage = expectedProjection :=
    projection_from_blocks beforeImage expectedProjection checked_blocks (by decide +kernel)
  rw [← selected_byte_images.2.2]
  exact ⟨before, before, by decide +kernel⟩

private noncomputable def inputAt (index : Nat) : RowInput := rowInputs.getD index { key := "", family := 0, variant := 0, generation := 0, familyCount := 0, featureDigest := "", tieDigests := [] }

private noncomputable def targetAt (index : Nat) : Phase17Provenance.RankedProgram := Phase17Provenance.selectedContext.rows.getD index { key := "", family := 0, baseScore := 0, ties := [] }

private theorem checked_row_000 : RowChecked expectedProjection (inputAt 0) (targetAt 0) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_001 : RowChecked expectedProjection (inputAt 1) (targetAt 1) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_002 : RowChecked expectedProjection (inputAt 2) (targetAt 2) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_003 : RowChecked expectedProjection (inputAt 3) (targetAt 3) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_004 : RowChecked expectedProjection (inputAt 4) (targetAt 4) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_005 : RowChecked expectedProjection (inputAt 5) (targetAt 5) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_006 : RowChecked expectedProjection (inputAt 6) (targetAt 6) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_007 : RowChecked expectedProjection (inputAt 7) (targetAt 7) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_008 : RowChecked expectedProjection (inputAt 8) (targetAt 8) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_009 : RowChecked expectedProjection (inputAt 9) (targetAt 9) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_010 : RowChecked expectedProjection (inputAt 10) (targetAt 10) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_011 : RowChecked expectedProjection (inputAt 11) (targetAt 11) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_012 : RowChecked expectedProjection (inputAt 12) (targetAt 12) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_013 : RowChecked expectedProjection (inputAt 13) (targetAt 13) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_014 : RowChecked expectedProjection (inputAt 14) (targetAt 14) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_015 : RowChecked expectedProjection (inputAt 15) (targetAt 15) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_016 : RowChecked expectedProjection (inputAt 16) (targetAt 16) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_017 : RowChecked expectedProjection (inputAt 17) (targetAt 17) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_018 : RowChecked expectedProjection (inputAt 18) (targetAt 18) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_019 : RowChecked expectedProjection (inputAt 19) (targetAt 19) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_020 : RowChecked expectedProjection (inputAt 20) (targetAt 20) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_021 : RowChecked expectedProjection (inputAt 21) (targetAt 21) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_022 : RowChecked expectedProjection (inputAt 22) (targetAt 22) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_023 : RowChecked expectedProjection (inputAt 23) (targetAt 23) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_024 : RowChecked expectedProjection (inputAt 24) (targetAt 24) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_025 : RowChecked expectedProjection (inputAt 25) (targetAt 25) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_026 : RowChecked expectedProjection (inputAt 26) (targetAt 26) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_027 : RowChecked expectedProjection (inputAt 27) (targetAt 27) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_028 : RowChecked expectedProjection (inputAt 28) (targetAt 28) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_029 : RowChecked expectedProjection (inputAt 29) (targetAt 29) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_030 : RowChecked expectedProjection (inputAt 30) (targetAt 30) := by
  unfold RowChecked
  decide +kernel

private theorem checked_row_031 : RowChecked expectedProjection (inputAt 31) (targetAt 31) := by
  unfold RowChecked
  decide +kernel

private theorem checked_rows :
    List.Forall₂ (RowChecked expectedProjection) rowInputs Phase17Provenance.selectedContext.rows := by

  refine List.Forall₂.cons checked_row_000 ?_

  refine List.Forall₂.cons checked_row_001 ?_

  refine List.Forall₂.cons checked_row_002 ?_

  refine List.Forall₂.cons checked_row_003 ?_

  refine List.Forall₂.cons checked_row_004 ?_

  refine List.Forall₂.cons checked_row_005 ?_

  refine List.Forall₂.cons checked_row_006 ?_

  refine List.Forall₂.cons checked_row_007 ?_

  refine List.Forall₂.cons checked_row_008 ?_

  refine List.Forall₂.cons checked_row_009 ?_

  refine List.Forall₂.cons checked_row_010 ?_

  refine List.Forall₂.cons checked_row_011 ?_

  refine List.Forall₂.cons checked_row_012 ?_

  refine List.Forall₂.cons checked_row_013 ?_

  refine List.Forall₂.cons checked_row_014 ?_

  refine List.Forall₂.cons checked_row_015 ?_

  refine List.Forall₂.cons checked_row_016 ?_

  refine List.Forall₂.cons checked_row_017 ?_

  refine List.Forall₂.cons checked_row_018 ?_

  refine List.Forall₂.cons checked_row_019 ?_

  refine List.Forall₂.cons checked_row_020 ?_

  refine List.Forall₂.cons checked_row_021 ?_

  refine List.Forall₂.cons checked_row_022 ?_

  refine List.Forall₂.cons checked_row_023 ?_

  refine List.Forall₂.cons checked_row_024 ?_

  refine List.Forall₂.cons checked_row_025 ?_

  refine List.Forall₂.cons checked_row_026 ?_

  refine List.Forall₂.cons checked_row_027 ?_

  refine List.Forall₂.cons checked_row_028 ?_

  refine List.Forall₂.cons checked_row_029 ?_

  refine List.Forall₂.cons checked_row_030 ?_

  refine List.Forall₂.cons checked_row_031 ?_

  exact List.Forall₂.nil


theorem selected_all_score_terms :
    rowInputs.length = 32 ∧
    rowInputs.map (fun row => (hexDigits row.featureDigest).map
      (fun digits => (scoreTerms expectedProjection row digits).length)) =
      List.replicate 32 (some 84) ∧
    rowInputs.map (fun row => (hexDigits row.featureDigest).map
      (baseScore expectedProjection row)) =
      Phase17Provenance.selectedContext.rows.map (fun row => some row.baseScore) := by
  have assembled := checked_rows_compose expectedProjection rowInputs
    Phase17Provenance.selectedContext.rows checked_rows
  have rowLength : rowInputs.length = 32 := by decide +kernel
  have projectionLength : expectedProjection.length = 84 := by decide +kernel
  refine ⟨rowLength, ?_, assembled.2.1⟩
  simpa only [rowLength, projectionLength] using assembled.1

theorem selected_all_tie_prefixes :
    rowInputs.map (fun row => row.tieDigests.mapM prefix16) =
      Phase17Provenance.selectedContext.rows.map (fun row => some row.ties) ∧
    rowInputs.map (fun row => row.tieDigests.length) = List.replicate 32 5 ∧
    decodedOffset freezeDigest = some Phase17Provenance.selectedContext.offset := by
  have assembled := checked_rows_compose expectedProjection rowInputs
    Phase17Provenance.selectedContext.rows checked_rows
  refine ⟨assembled.2.2.1, ?_, by decide +kernel⟩
  simpa only [selected_all_score_terms.1] using assembled.2.2.2.1

theorem selected_rows_bound :
    decodedRows beforeImage rowInputs = some Phase17Provenance.selectedContext.rows ∧
    decodedRows afterImage rowInputs = some Phase17Provenance.selectedContext.rows := by
  have before : decodedRows beforeImage rowInputs = some Phase17Provenance.selectedContext.rows := by
    rw [table_from_projection beforeImage expectedProjection rowInputs
      selected_complete_word_projection.1]
    exact (checked_rows_compose expectedProjection rowInputs
      Phase17Provenance.selectedContext.rows checked_rows).2.2.2.2
  rw [← selected_byte_images.2.2]
  exact ⟨before, before⟩

theorem selected_context_bound :
    decodedContext Phase17Provenance.selectedContext beforeImage rowInputs freezeDigest =
      some Phase17Finite.selectedConfiguration.context ∧
    decodedContext Phase17Provenance.selectedContext afterImage rowInputs freezeDigest =
      some Phase17Finite.selectedConfiguration.context := by
  exact ⟨context_reconstruction _ _ _ _ selected_rows_bound.1 selected_all_tie_prefixes.2.2,
    context_reconstruction _ _ _ _ selected_rows_bound.2 selected_all_tie_prefixes.2.2⟩

/-- The whole selected proposal prefix uses the context reconstructed from
    the byte-derived table. Supplied digest preimages remain external inputs. -/
theorem selected_produced_trace :
    ∃ context : Phase17Provenance.Context,
      decodedContext Phase17Provenance.selectedContext beforeImage rowInputs freezeDigest = some context ∧
      context = Phase17Finite.selectedConfiguration.context ∧
      Phase17Provenance.Produced context Phase17Provenance.selectedProposal ∧
      selectedChoices = Phase17Provenance.selectedProposal.choices ∧
      Phase17Provenance.follows context [] selectedChoices = true := by
  refine ⟨Phase17Provenance.selectedContext, selected_context_bound.1, rfl,
    Phase17Provenance.selected_provenance, ?_, ?_⟩ <;> decide +kernel

/-- The selected finite acceptance carries both the producer numerical binding
    and T's captured JSON-to-package binding. This is not a physical or general
    autonomous-transition acceptance statement. -/
theorem selected_learned_acceptance_bound :
    ∃ context : Phase17Provenance.Context,
      decodedContext Phase17Provenance.selectedContext beforeImage rowInputs freezeDigest = some context ∧
      decodedContext Phase17Provenance.selectedContext afterImage rowInputs freezeDigest = some context ∧
      context = Phase17Finite.selectedConfiguration.context ∧
      Phase17Provenance.Produced context Phase17Finite.selectedEvidence.proposal ∧
      Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
        Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
        (Phase17Finite.packet Phase17Finite.selectedConfiguration
          Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) ∧
      Phase17Json.ImagesBound Phase17Json.beforeImages Phase17Routing.beforePackage ∧
      Phase17Json.ImagesBound Phase17Json.afterImages Phase17Routing.afterPackage ∧
      Phase17Json.decodePackage Phase17Json.beforeImages Phase17Routing.beforePackage.adapterImage =
        some Phase17Routing.beforePackage ∧
      Phase17Json.decodePackage Phase17Json.afterImages Phase17Routing.afterPackage.adapterImage =
        some Phase17Routing.afterPackage ∧
      Phase17Routing.RoutedGoalBinding Phase17Routing.beforePackage Phase17Sparse.beforeImage
        Phase17Routing.originalTasks Phase17Sparse.selectedTargets ∧
      Phase17Routing.RoutedGoalBinding Phase17Routing.afterPackage Phase17Sparse.afterImage
        Phase17Routing.originalTasks Phase17Sparse.selectedTargets := by
  exact ⟨Phase17Provenance.selectedContext, selected_context_bound.1, selected_context_bound.2,
    rfl, Phase17Provenance.selected_provenance, Phase17Finite.selected_learned_accepted,
    Phase17Json.selected_before_decode, Phase17Json.selected_after_decode,
    Phase17Json.selected_package_reconstruction.1, Phase17Json.selected_package_reconstruction.2,
    Phase17Routing.selected_routed_goals.1, Phase17Routing.selected_routed_goals.2⟩

theorem selected_decoder_edges :
    signed16 0 128 = -32768 ∧ signed16 255 127 = 32767 ∧
    signed16 255 255 = -1 ∧ signed16 1 0 = 1 ∧ signed16 0 1 = 256 ∧
    hexDigit 48 = some 0 ∧ hexDigit 57 = some 9 ∧ hexDigit 97 = some 10 ∧
    hexDigit 102 = some 15 ∧ hexDigit 65 = none ∧ hexDigit 103 = none ∧
    prefix16 "0000000000000000000000000000000000000000000000000000000000000000" = some 0 ∧
    prefix16 "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff" = some 18446744073709551615 ∧
    decodedOffset "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff" = some 31 ∧
    prefix16 "000000000000000000000000000000000000000000000000000000000000000g" = none ∧
    prefix16 "0" = none := by decide +kernel

end Phase17Planner
#print axioms Phase17Planner.hex_digit_bound
#print axioms Phase17Planner.word_projection_sound
#print axioms Phase17Planner.nonzero_word_covered
#print axioms Phase17Planner.projection_from_blocks
#print axioms Phase17Planner.table_from_projection
#print axioms Phase17Planner.context_reconstruction
#print axioms Phase17Planner.selected_byte_images
#print axioms Phase17Planner.selected_complete_word_projection
#print axioms Phase17Planner.selected_all_score_terms
#print axioms Phase17Planner.selected_all_tie_prefixes
#print axioms Phase17Planner.selected_rows_bound
#print axioms Phase17Planner.selected_context_bound
#print axioms Phase17Planner.selected_produced_trace
#print axioms Phase17Planner.selected_learned_acceptance_bound
#print axioms Phase17Planner.selected_decoder_edges
