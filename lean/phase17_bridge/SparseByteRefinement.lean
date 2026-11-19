/- Phase 17R: the captured sparse tensor is an exact finite byte image, encoded
   by its complete nonzero support and an explicit total length. The external
   reader checks its full round trip against all physical bytes, including
   padding. This file independently interprets those byte literals. It does not
   prove OS reads, Python execution, cryptographic authenticity, prompt routing,
   or full-transformer equivalence. -/
namespace Phase17Sparse

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3
open scoped BigOperators

/-- An ordered binary representation of finite nonzero byte support. -/
inductive ByteTree where
  | empty
  | node (left : ByteTree) (offset value : Nat) (right : ByteTree)
  deriving DecidableEq

def entries : ByteTree → List (Nat × Nat)
  | .empty => []
  | .node left offset value right => entries left ++ [(offset, value)] ++ entries right

def lookup : ByteTree → Nat → Nat
  | .empty, _ => 0
  | .node left offset value right, index =>
      if index = offset then value
      else if index < offset then lookup left index else lookup right index

structure TensorImage where
  byteLength : Nat
  support : ByteTree
  deriving DecidableEq

def Canonical (image : TensorImage) : Prop :=
  image.byteLength = 204800 ∧
  ((entries image.support).map Prod.fst).Pairwise (· < ·) ∧
  ∀ entry ∈ entries image.support,
    entry.1 < image.byteLength ∧ 0 < entry.2 ∧ entry.2 < 256

def byteAt (image : TensorImage) (offset : Nat) : Nat :=
  if offset < image.byteLength then lookup image.support offset else 0

/-- Explicit little-endian two's-complement interpretation. -/
def signed16 (lo hi : Nat) : Int :=
  let word := lo + 256 * hi
  if word < 32768 then Int.ofNat word else Int.ofNat word - 65536

theorem signed16_range (lo hi : Nat) (low : lo < 256) (high : hi < 256) :
    -32768 ≤ signed16 lo hi ∧ signed16 lo hi ≤ 32767 := by
  by_cases half : lo + 256 * hi < 32768
  · simp only [signed16, half, ite_true]
    change -32768 ≤ (lo : Int) + 256 * (hi : Int) ∧
      (lo : Int) + 256 * (hi : Int) ≤ 32767
    omega
  · simp only [signed16, half, ite_false]
    change -32768 ≤ (lo : Int) + 256 * (hi : Int) - 65536 ∧
      (lo : Int) + 256 * (hi : Int) - 65536 ≤ 32767
    omega

def rawWord (image : TensorImage) (current target : Nat) : Int :=
  let offset := 2 * (target * 320 + current)
  signed16 (byteAt image offset) (byteAt image (offset + 1))

def rawScore (image : TensorImage) (current target : Nat) : Int :=
  rawWord image current target / 2048

def scoreRow (image : TensorImage) (current : Nat) : List Int :=
  (List.range 260).map (rawScore image current)

def IntegralScores (image : TensorImage) : Prop :=
  (List.range 260).all (fun current =>
    (List.range 260).all (fun target => decide (rawWord image current target % 2048 = 0))) = true

def clip (score : Int) : Int := max (-15) (min 15 score)

theorem clipped_score_range (score : Int) : -15 ≤ clip score ∧ clip score ≤ 15 := by
  unfold clip
  omega

def minimum : List Int → Int
  | [] => 0
  | first :: rest => rest.foldl min first

def dyadicWeight (score lower : Int) : Nat := 2 ^ (score - lower).toNat

theorem dyadic_weight_positive (score lower : Int) : 0 < dyadicWeight score lower := by
  exact pow_pos (by decide) _

def massMinusOne (scores : List Int) : List Nat :=
  let clipped := scores.map clip
  let lower := minimum clipped
  clipped.map (fun score => dyadicWeight score lower - 1)

def decodedRow (image : TensorImage) (current : Nat) : List Nat :=
  massMinusOne (scoreRow image current)

noncomputable def decodedDistribution (image : TensorImage) (current : Nat) :=
  Phase17Protected.distribution (decodedRow image current)

theorem row_probability_normalized (image : TensorImage) (current : Nat) :
    (∑ token : Phase17Protected.Token,
      (decodedDistribution image current).distribution.mass token) = 1 :=
  Phase17Protected.mass_distribution_normalized _

def ScoreBinding (image : TensorImage) (dictionary : List (List Int))
    (selectors : List Nat) : Prop :=
  (List.range 260).all (fun current => decide
    (scoreRow image current = dictionary.getD (selectors.getD current 0) [])) = true

/-- One bounded row certificate, in precisely the Boolean form consumed by the
    all-context predicates. Separate row proofs bound kernel reduction memory. -/
def RowFacts (image : TensorImage) (dictionary : List (List Int))
    (selectors : List Nat) (current : Nat) : Prop :=
  decide (scoreRow image current = dictionary.getD (selectors.getD current 0) []) = true ∧
  (List.range 260).all (fun target => decide (rawWord image current target % 2048 = 0)) = true

theorem score_binding_from_rows (image : TensorImage) (dictionary : List (List Int))
    (selectors : List Nat)
    (rows : ∀ current < 260, RowFacts image dictionary selectors current) :
    ScoreBinding image dictionary selectors ∧ IntegralScores image := by
  constructor
  · exact List.all_eq_true.mpr (fun current member =>
      (rows current (List.mem_range.mp member)).1)
  · exact List.all_eq_true.mpr (fun current member =>
      (rows current (List.mem_range.mp member)).2)

theorem score_binding_at (image : TensorImage) (dictionary : List (List Int))
    (selectors : List Nat) (binding : ScoreBinding image dictionary selectors)
    (current : Nat) (bounded : current < 260) :
    scoreRow image current = dictionary.getD (selectors.getD current 0) [] := by
  exact of_decide_eq_true ((List.all_eq_true.mp binding) current (List.mem_range.mpr bounded))

private theorem getD_map_default {α β : Type*} (f : α → β)
    (xs : List α) (index : Nat) (fallback : α) :
    (xs.map f).getD index (f fallback) = f (xs.getD index fallback) := by
  induction xs generalizing index with
  | nil => simp
  | cons x xs ih =>
    cases index with
    | zero => rfl
    | succ index => exact ih index

/-- The compressed Q mass observation is now bound to the actual byte decoder,
    for every conditional context, rather than accepted as a score oracle. -/
theorem mass_binding_sound (image : TensorImage) (dictionary : List (List Int))
    (selectors : List Nat) (observed : Phase17Protected.Observation)
    (scores : ScoreBinding image dictionary selectors)
    (rows : observed.rows = dictionary.map massMinusOne)
    (selection : observed.selectors = selectors)
    (current : Nat) (bounded : current < 260) :
    Phase17Protected.rowAt observed current = decodedRow image current := by
  unfold Phase17Protected.rowAt
  rw [rows, selection]
  change (dictionary.map massMinusOne).getD (selectors.getD current 0)
    (massMinusOne []) = decodedRow image current
  rw [getD_map_default]
  exact congrArg massMinusOne (score_binding_at image dictionary selectors scores current bounded).symm

theorem distribution_binding_sound (image : TensorImage)
    (observed : Phase17Protected.Observation)
    (binding : ∀ current < 260,
      Phase17Protected.rowAt observed current = decodedRow image current)
    (current : Phase17Protected.Token) :
    Phase17Protected.distribution (Phase17Protected.rowAt observed current.val) =
      decodedDistribution image current.val := by
  rw [binding current.val current.isLt]
  rfl

noncomputable def decodedInformationSum (image : TensorImage) : List (Nat × Nat) → ℝ
  | [] => 0
  | (current, target) :: rest =>
      RCP.ClassicalFinite.positiveKLDivergence
        (decodedDistribution image current)
        (Phase17Protected.distribution (Phase17Protected.targetRow target)) +
      decodedInformationSum image rest

theorem information_binding_sound (image : TensorImage)
    (observed : Phase17Protected.Observation)
    (binding : ∀ current < 260,
      Phase17Protected.rowAt observed current = decodedRow image current)
    (positions : List (Nat × Nat))
    (bounded : ∀ position ∈ positions, position.1 < 260) :
    Phase17Protected.informationSum observed positions = decodedInformationSum image positions := by
  induction positions with
  | nil => rfl
  | cons pair rest ih =>
    rcases pair with ⟨current, target⟩
    simp only [Phase17Protected.informationSum, decodedInformationSum]
    rw [binding current (bounded (current, target) (by simp))]
    rw [ih (by intro position member; exact bounded position (by simp [member]))]
    rfl

/-- Strict comparison preserves the earliest (lowest) token id on every tie.
    Goal decoding uses RAW scores, before probability clipping. -/
def greedyScan (best next : Nat) (highest : Int) : List Int → Nat
  | [] => best
  | score :: rest =>
      if highest < score then greedyScan next (next + 1) score rest
      else greedyScan best (next + 1) highest rest

def greedyToken : List Int → Nat
  | [] => 0
  | first :: rest => greedyScan 0 1 first rest

inductive Termination where
  | eos
  | nonByte
  | limit
  deriving DecidableEq

structure DecodeResult where
  tokens : List Nat
  termination : Termination
  deriving DecidableEq

def decodeWith (scores : Nat → List Int) : Nat → Nat → DecodeResult
  | 0, _ => ⟨[], .limit⟩
  | fuel + 1, current =>
      let selected := greedyToken (scores current)
      if selected = 258 then ⟨[selected], .eos⟩
      else if selected ≥ 256 then ⟨[selected], .nonByte⟩
      else
        let rest := decodeWith scores fuel selected
        ⟨selected :: rest.tokens, rest.termination⟩

def decode (image : TensorImage) (marker : Nat) : DecodeResult :=
  decodeWith (scoreRow image) 16 marker

def GoalBinding (image : TensorImage) (markers : List Nat)
    (targets : List (List Nat)) : Prop :=
  markers.length = 11 ∧ targets.length = 11 ∧
  (markers.zip targets).all (fun pair => decide
    (decode image pair.1 = ⟨pair.2, .eos⟩)) = true

structure CapturedProjection (image : TensorImage)
    (observed : Phase17Protected.Observation) (markers : List Nat)
    (targets : List (List Nat)) : Prop where
  canonical : Canonical image
  integral : IntegralScores image
  rows : ∀ current < 260,
    Phase17Protected.rowAt observed current = decodedRow image current
  goals : observed.goals = (markers.zip targets).map (fun pair => pair.1 :: pair.2)
  decoded : GoalBinding image markers targets

end Phase17Sparse
