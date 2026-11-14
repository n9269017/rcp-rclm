import Phase17QDependency

set_option Elab.async false

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

namespace Phase17Sparse
open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3
set_option maxRecDepth 32768
set_option maxHeartbeats 32000000
-- Fresh R packet SHA256: 505d704bbab6d1f72d22dd36f5f75ea128057ffb48b11000937728abaabb07ad
def beforeImage : TensorImage := { byteLength := 204800, support := (.node (.node (.node (.node (.node (.node (.node (.node .empty 28205 96 .empty) 28209 96 .empty) 28213 96 (.node (.node .empty 28219 96 .empty) 28223 96 .empty)) 28467 96 (.node (.node (.node .empty 28471 96 .empty) 28475 96 .empty) 28481 96 (.node (.node .empty 28485 96 .empty) 28597 96 .empty))) 28601 96 (.node (.node (.node (.node .empty 28605 96 .empty) 28611 96 .empty) 28615 96 (.node (.node .empty 30767 96 .empty) 31029 96 .empty)) 31159 96 (.node (.node (.node .empty 31363 96 .empty) 31403 96 .empty) 31421 96 (.node .empty 31425 96 .empty)))) 31449 96 (.node (.node (.node (.node (.node .empty 31457 96 .empty) 31619 96 .empty) 31665 96 (.node (.node .empty 31673 96 .empty) 31683 96 .empty)) 31687 96 (.node (.node (.node .empty 31747 96 .empty) 31795 96 .empty) 31803 96 (.node .empty 31813 96 .empty))) 31817 96 (.node (.node (.node (.node .empty 32051 96 .empty) 32357 96 .empty) 32365 96 (.node (.node .empty 32489 96 .empty) 32497 96 .empty)) 34617 96 (.node (.node (.node .empty 34879 96 .empty) 35009 96 .empty) 36535 96 (.node .empty 36797 96 .empty))))) 36927 96 (.node (.node (.node (.node (.node (.node .empty 37765 96 .empty) 37773 96 .empty) 37781 96 (.node (.node .empty 37789 96 .empty) 37797 96 .empty)) 37827 96 (.node (.node (.node .empty 37835 96 .empty) 37843 96 .empty) 37851 96 (.node (.node .empty 38021 96 .empty) 38029 96 .empty))) 38043 96 (.node (.node (.node (.node .empty 38051 96 .empty) 38059 96 .empty) 38089 96 (.node (.node .empty 38103 96 .empty) 38111 96 .empty)) 38119 96 (.node (.node (.node .empty 38149 96 .empty) 38157 96 .empty) 38173 96 (.node .empty 38181 96 .empty)))) 38189 96 (.node (.node (.node (.node (.node .empty 38219 96 .empty) 38235 96 .empty) 38243 96 (.node (.node .empty 38251 96 .empty) 39049 96 .empty)) 39057 96 (.node (.node (.node .empty 39065 96 .empty) 39073 96 .empty) 39081 96 (.node .empty 39111 96 .empty))) 39119 96 (.node (.node (.node (.node .empty 39127 96 .empty) 39135 96 .empty) 39305 96 (.node (.node .empty 39313 96 .empty) 39327 96 .empty)) 39335 96 (.node (.node (.node .empty 39343 96 .empty) 39373 96 .empty) 39387 96 (.node .empty 39395 96 .empty)))))) 39403 96 (.node (.node (.node (.node (.node (.node (.node .empty 39433 96 .empty) 39441 96 .empty) 39457 96 (.node (.node .empty 39465 96 .empty) 39473 96 .empty)) 39503 96 (.node (.node (.node .empty 39519 96 .empty) 39527 96 .empty) 39535 96 (.node (.node .empty 41627 96 .empty) 41631 96 .empty))) 41889 96 (.node (.node (.node (.node .empty 41893 96 .empty) 42019 96 .empty) 42023 96 (.node (.node .empty 42317 96 .empty) 42585 96 .empty)) 42717 96 (.node (.node (.node .empty 43287 96 .empty) 43349 96 .empty) 43543 96 (.node .empty 43805 96 .empty)))) 43935 96 (.node (.node (.node (.node (.node .empty 44229 96 .empty) 44491 96 .empty) 44621 96 (.node (.node .empty 44811 96 .empty) 45067 96 .empty)) 45195 96 (.node (.node (.node .empty 45525 96 .empty) 45719 96 .empty) 45779 96 (.node .empty 45793 96 .empty))) 45849 96 (.node (.node (.node (.node .empty 45911 96 .empty) 45925 96 .empty) 48917 96 (.node (.node .empty 48977 96 .empty) 49045 96 .empty)) 49107 96 (.node (.node (.node .empty 49955 96 .empty) 50217 96 .empty) 50347 96 (.node .empty 50567 96 .empty))))) 50823 96 (.node (.node (.node (.node (.node (.node .empty 50951 96 .empty) 51293 96 .empty) 51481 96 (.node (.node .empty 51541 96 .empty) 51561 96 .empty)) 51611 96 (.node (.node (.node .empty 51673 96 .empty) 51693 96 .empty) 52519 96 (.node .empty 52781 96 .empty))) 52911 96 (.node (.node (.node (.node .empty 54415 96 .empty) 54671 96 .empty) 54799 96 (.node (.node .empty 55041 96 .empty) 55059 96 .empty)) 55113 96 (.node (.node (.node .empty 55297 96 .empty) 55425 96 .empty) 55955 96 (.node .empty 56015 96 .empty)))) 56083 96 (.node (.node (.node (.node (.node .empty 56145 112 .empty) 56401 96 .empty) 56669 96 (.node (.node .empty 56801 96 .empty) 62287 96 .empty)) 64859 96 (.node (.node (.node .empty 65509 96 .empty) 66123 96 .empty) 69325 96 (.node .empty 69983 96 .empty))) 71199 96 (.node (.node (.node (.node .empty 72489 96 .empty) 73125 96 .empty) 78247 96 (.node (.node .empty 165219 96 .empty) 165315 96 .empty)) 165337 96 (.node (.node (.node .empty 165347 96 .empty) 165365 96 .empty) 165487 96 (.node .empty 165619 96 .empty))))))) }
def afterImage : TensorImage := { byteLength := 204800, support := (.node (.node (.node (.node (.node (.node (.node (.node .empty 28205 96 .empty) 28209 96 .empty) 28213 96 (.node (.node .empty 28219 96 .empty) 28223 96 .empty)) 28467 96 (.node (.node (.node .empty 28471 96 .empty) 28475 96 .empty) 28481 96 (.node (.node .empty 28485 96 .empty) 28597 96 .empty))) 28601 96 (.node (.node (.node (.node .empty 28605 96 .empty) 28611 96 .empty) 28615 96 (.node (.node .empty 30767 96 .empty) 31029 96 .empty)) 31159 96 (.node (.node (.node .empty 31363 96 .empty) 31403 96 .empty) 31421 96 (.node .empty 31425 96 .empty)))) 31449 96 (.node (.node (.node (.node (.node .empty 31457 96 .empty) 31619 96 .empty) 31665 96 (.node (.node .empty 31673 96 .empty) 31683 96 .empty)) 31687 96 (.node (.node (.node .empty 31747 96 .empty) 31795 96 .empty) 31803 96 (.node .empty 31813 96 .empty))) 31817 96 (.node (.node (.node (.node .empty 32051 96 .empty) 32357 96 .empty) 32365 96 (.node (.node .empty 32489 96 .empty) 32497 96 .empty)) 34617 96 (.node (.node (.node .empty 34879 96 .empty) 35009 96 .empty) 36535 96 (.node .empty 36797 96 .empty))))) 36927 96 (.node (.node (.node (.node (.node (.node .empty 37765 96 .empty) 37773 96 .empty) 37781 96 (.node (.node .empty 37789 96 .empty) 37797 96 .empty)) 37827 96 (.node (.node (.node .empty 37835 96 .empty) 37843 96 .empty) 37851 96 (.node (.node .empty 38021 96 .empty) 38029 96 .empty))) 38043 96 (.node (.node (.node (.node .empty 38051 96 .empty) 38059 96 .empty) 38089 96 (.node (.node .empty 38103 96 .empty) 38111 96 .empty)) 38119 96 (.node (.node (.node .empty 38149 96 .empty) 38157 96 .empty) 38173 96 (.node .empty 38181 96 .empty)))) 38189 96 (.node (.node (.node (.node (.node .empty 38219 96 .empty) 38235 96 .empty) 38243 96 (.node (.node .empty 38251 96 .empty) 39049 96 .empty)) 39057 96 (.node (.node (.node .empty 39065 96 .empty) 39073 96 .empty) 39081 96 (.node .empty 39111 96 .empty))) 39119 96 (.node (.node (.node (.node .empty 39127 96 .empty) 39135 96 .empty) 39305 96 (.node (.node .empty 39313 96 .empty) 39327 96 .empty)) 39335 96 (.node (.node (.node .empty 39343 96 .empty) 39373 96 .empty) 39387 96 (.node .empty 39395 96 .empty)))))) 39403 96 (.node (.node (.node (.node (.node (.node (.node .empty 39433 96 .empty) 39441 96 .empty) 39457 96 (.node (.node .empty 39465 96 .empty) 39473 96 .empty)) 39503 96 (.node (.node (.node .empty 39519 96 .empty) 39527 96 .empty) 39535 96 (.node (.node .empty 41627 96 .empty) 41631 96 .empty))) 41889 96 (.node (.node (.node (.node .empty 41893 96 .empty) 42019 96 .empty) 42023 96 (.node (.node .empty 42317 96 .empty) 42585 96 .empty)) 42717 96 (.node (.node (.node .empty 43287 96 .empty) 43349 96 .empty) 43543 96 (.node .empty 43805 96 .empty)))) 43935 96 (.node (.node (.node (.node (.node .empty 44229 96 .empty) 44491 96 .empty) 44621 96 (.node (.node .empty 44811 96 .empty) 45067 96 .empty)) 45195 96 (.node (.node (.node .empty 45525 96 .empty) 45719 96 .empty) 45779 96 (.node .empty 45793 96 .empty))) 45849 96 (.node (.node (.node (.node .empty 45911 96 .empty) 45925 96 .empty) 48917 96 (.node (.node .empty 48977 96 .empty) 49045 96 .empty)) 49107 96 (.node (.node (.node .empty 49955 96 .empty) 50217 96 .empty) 50347 96 (.node .empty 50567 96 .empty))))) 50823 96 (.node (.node (.node (.node (.node (.node .empty 50951 96 .empty) 51293 96 .empty) 51481 96 (.node (.node .empty 51541 96 .empty) 51561 96 .empty)) 51611 96 (.node (.node (.node .empty 51673 96 .empty) 51693 96 .empty) 52519 96 (.node .empty 52781 96 .empty))) 52911 96 (.node (.node (.node (.node .empty 54415 96 .empty) 54671 96 .empty) 54799 96 (.node (.node .empty 55041 96 .empty) 55059 96 .empty)) 55113 96 (.node (.node (.node .empty 55297 96 .empty) 55425 96 .empty) 55955 96 (.node .empty 56015 96 .empty)))) 56083 96 (.node (.node (.node (.node (.node .empty 56145 112 .empty) 56401 96 .empty) 56669 96 (.node (.node .empty 56801 96 .empty) 62287 96 .empty)) 64859 96 (.node (.node (.node .empty 65509 96 .empty) 66123 96 .empty) 69325 96 (.node .empty 69983 96 .empty))) 71199 96 (.node (.node (.node (.node .empty 72489 96 .empty) 73125 96 .empty) 78247 96 (.node (.node .empty 165219 96 .empty) 165315 96 .empty)) 165337 96 (.node (.node (.node .empty 165347 96 .empty) 165365 96 .empty) 165487 96 (.node .empty 165619 96 .empty))))))) }
def expectedScores : List (List Int) := [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]
def expectedSelectors : List Nat := [0, 1, 2, 3, 4, 5, 2, 6, 4, 0, 2, 7, 4, 8, 2, 8, 4, 9, 2, 10, 4, 1, 11, 12, 11, 13, 11, 14, 15, 11, 1, 11, 1, 2, 16, 4, 0, 2, 17, 4, 18, 2, 19, 4, 1, 2, 20, 4, 1, 21, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 23, 22, 22, 24, 25, 26, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 21, 22, 22, 22, 27, 28, 29, 22, 22, 22, 22, 21, 30, 22, 31, 22, 21, 32, 22, 22, 22, 22, 22, 22, 22, 21, 22, 22, 22, 22, 22, 0, 1, 2, 3, 4, 5, 2, 6, 4, 33, 34, 19, 20, 2, 7, 4, 8, 2, 8, 4, 9, 2, 10, 4, 1, 11, 12, 11, 1, 11, 14, 15, 11, 1, 11, 1, 2, 16, 4, 33, 34, 19, 20, 2, 17, 4, 18, 2, 19, 4, 13, 2, 20, 4, 13, 21, 22, 22, 22, 22, 22, 22, 22, 22, 0, 1, 2, 3, 4, 5, 2, 6, 4, 33, 34, 35, 19, 20, 2, 7, 4, 8, 2, 8, 4, 9, 2, 10, 4, 1, 11, 12, 11, 1, 11, 14, 15, 11, 1, 11, 1, 2, 16, 4, 36, 34, 35, 19, 20, 2, 17, 4, 18, 2, 19, 4, 13, 2, 20, 4, 13, 21, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22]
def selectedMarkers : List Nat := [79, 82, 83, 84, 84, 84, 84, 84, 84, 84, 84]
def selectedTargets : List (List Nat) := [[111, 109, 101, 103, 97, 258], [114, 102, 108, 258], [122, 258], [113, 258], [113, 258], [113, 258], [113, 258], [113, 258], [113, 258], [113, 258], [113, 258]]

theorem selected_byte_images :
    Canonical beforeImage ∧ Canonical afterImage ∧ beforeImage = afterImage := by
  unfold Canonical
  decide +kernel

private theorem checked_row_000 : RowFacts beforeImage expectedScores expectedSelectors 0 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_001 : RowFacts beforeImage expectedScores expectedSelectors 1 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_002 : RowFacts beforeImage expectedScores expectedSelectors 2 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_003 : RowFacts beforeImage expectedScores expectedSelectors 3 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_004 : RowFacts beforeImage expectedScores expectedSelectors 4 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_005 : RowFacts beforeImage expectedScores expectedSelectors 5 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_006 : RowFacts beforeImage expectedScores expectedSelectors 6 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_007 : RowFacts beforeImage expectedScores expectedSelectors 7 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_008 : RowFacts beforeImage expectedScores expectedSelectors 8 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_009 : RowFacts beforeImage expectedScores expectedSelectors 9 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_010 : RowFacts beforeImage expectedScores expectedSelectors 10 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_011 : RowFacts beforeImage expectedScores expectedSelectors 11 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_012 : RowFacts beforeImage expectedScores expectedSelectors 12 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_013 : RowFacts beforeImage expectedScores expectedSelectors 13 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_014 : RowFacts beforeImage expectedScores expectedSelectors 14 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_015 : RowFacts beforeImage expectedScores expectedSelectors 15 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_016 : RowFacts beforeImage expectedScores expectedSelectors 16 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_017 : RowFacts beforeImage expectedScores expectedSelectors 17 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_018 : RowFacts beforeImage expectedScores expectedSelectors 18 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_019 : RowFacts beforeImage expectedScores expectedSelectors 19 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_020 : RowFacts beforeImage expectedScores expectedSelectors 20 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_021 : RowFacts beforeImage expectedScores expectedSelectors 21 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_022 : RowFacts beforeImage expectedScores expectedSelectors 22 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_023 : RowFacts beforeImage expectedScores expectedSelectors 23 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_024 : RowFacts beforeImage expectedScores expectedSelectors 24 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_025 : RowFacts beforeImage expectedScores expectedSelectors 25 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_026 : RowFacts beforeImage expectedScores expectedSelectors 26 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_027 : RowFacts beforeImage expectedScores expectedSelectors 27 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_028 : RowFacts beforeImage expectedScores expectedSelectors 28 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_029 : RowFacts beforeImage expectedScores expectedSelectors 29 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_030 : RowFacts beforeImage expectedScores expectedSelectors 30 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_031 : RowFacts beforeImage expectedScores expectedSelectors 31 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_032 : RowFacts beforeImage expectedScores expectedSelectors 32 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_033 : RowFacts beforeImage expectedScores expectedSelectors 33 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_034 : RowFacts beforeImage expectedScores expectedSelectors 34 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_035 : RowFacts beforeImage expectedScores expectedSelectors 35 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_036 : RowFacts beforeImage expectedScores expectedSelectors 36 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_037 : RowFacts beforeImage expectedScores expectedSelectors 37 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_038 : RowFacts beforeImage expectedScores expectedSelectors 38 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_039 : RowFacts beforeImage expectedScores expectedSelectors 39 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_040 : RowFacts beforeImage expectedScores expectedSelectors 40 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_041 : RowFacts beforeImage expectedScores expectedSelectors 41 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_042 : RowFacts beforeImage expectedScores expectedSelectors 42 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_043 : RowFacts beforeImage expectedScores expectedSelectors 43 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_044 : RowFacts beforeImage expectedScores expectedSelectors 44 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_045 : RowFacts beforeImage expectedScores expectedSelectors 45 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_046 : RowFacts beforeImage expectedScores expectedSelectors 46 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_047 : RowFacts beforeImage expectedScores expectedSelectors 47 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_048 : RowFacts beforeImage expectedScores expectedSelectors 48 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_049 : RowFacts beforeImage expectedScores expectedSelectors 49 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_050 : RowFacts beforeImage expectedScores expectedSelectors 50 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_051 : RowFacts beforeImage expectedScores expectedSelectors 51 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_052 : RowFacts beforeImage expectedScores expectedSelectors 52 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_053 : RowFacts beforeImage expectedScores expectedSelectors 53 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_054 : RowFacts beforeImage expectedScores expectedSelectors 54 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_055 : RowFacts beforeImage expectedScores expectedSelectors 55 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_056 : RowFacts beforeImage expectedScores expectedSelectors 56 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_057 : RowFacts beforeImage expectedScores expectedSelectors 57 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_058 : RowFacts beforeImage expectedScores expectedSelectors 58 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_059 : RowFacts beforeImage expectedScores expectedSelectors 59 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_060 : RowFacts beforeImage expectedScores expectedSelectors 60 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_061 : RowFacts beforeImage expectedScores expectedSelectors 61 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_062 : RowFacts beforeImage expectedScores expectedSelectors 62 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_063 : RowFacts beforeImage expectedScores expectedSelectors 63 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_064 : RowFacts beforeImage expectedScores expectedSelectors 64 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_065 : RowFacts beforeImage expectedScores expectedSelectors 65 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_066 : RowFacts beforeImage expectedScores expectedSelectors 66 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_067 : RowFacts beforeImage expectedScores expectedSelectors 67 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_068 : RowFacts beforeImage expectedScores expectedSelectors 68 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_069 : RowFacts beforeImage expectedScores expectedSelectors 69 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_070 : RowFacts beforeImage expectedScores expectedSelectors 70 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_071 : RowFacts beforeImage expectedScores expectedSelectors 71 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_072 : RowFacts beforeImage expectedScores expectedSelectors 72 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_073 : RowFacts beforeImage expectedScores expectedSelectors 73 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_074 : RowFacts beforeImage expectedScores expectedSelectors 74 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_075 : RowFacts beforeImage expectedScores expectedSelectors 75 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_076 : RowFacts beforeImage expectedScores expectedSelectors 76 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_077 : RowFacts beforeImage expectedScores expectedSelectors 77 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_078 : RowFacts beforeImage expectedScores expectedSelectors 78 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_079 : RowFacts beforeImage expectedScores expectedSelectors 79 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_080 : RowFacts beforeImage expectedScores expectedSelectors 80 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_081 : RowFacts beforeImage expectedScores expectedSelectors 81 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_082 : RowFacts beforeImage expectedScores expectedSelectors 82 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_083 : RowFacts beforeImage expectedScores expectedSelectors 83 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_084 : RowFacts beforeImage expectedScores expectedSelectors 84 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_085 : RowFacts beforeImage expectedScores expectedSelectors 85 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_086 : RowFacts beforeImage expectedScores expectedSelectors 86 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_087 : RowFacts beforeImage expectedScores expectedSelectors 87 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_088 : RowFacts beforeImage expectedScores expectedSelectors 88 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_089 : RowFacts beforeImage expectedScores expectedSelectors 89 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_090 : RowFacts beforeImage expectedScores expectedSelectors 90 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_091 : RowFacts beforeImage expectedScores expectedSelectors 91 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_092 : RowFacts beforeImage expectedScores expectedSelectors 92 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_093 : RowFacts beforeImage expectedScores expectedSelectors 93 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_094 : RowFacts beforeImage expectedScores expectedSelectors 94 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_095 : RowFacts beforeImage expectedScores expectedSelectors 95 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_096 : RowFacts beforeImage expectedScores expectedSelectors 96 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_097 : RowFacts beforeImage expectedScores expectedSelectors 97 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_098 : RowFacts beforeImage expectedScores expectedSelectors 98 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_099 : RowFacts beforeImage expectedScores expectedSelectors 99 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_100 : RowFacts beforeImage expectedScores expectedSelectors 100 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_101 : RowFacts beforeImage expectedScores expectedSelectors 101 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_102 : RowFacts beforeImage expectedScores expectedSelectors 102 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_103 : RowFacts beforeImage expectedScores expectedSelectors 103 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_104 : RowFacts beforeImage expectedScores expectedSelectors 104 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_105 : RowFacts beforeImage expectedScores expectedSelectors 105 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_106 : RowFacts beforeImage expectedScores expectedSelectors 106 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_107 : RowFacts beforeImage expectedScores expectedSelectors 107 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_108 : RowFacts beforeImage expectedScores expectedSelectors 108 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_109 : RowFacts beforeImage expectedScores expectedSelectors 109 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_110 : RowFacts beforeImage expectedScores expectedSelectors 110 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_111 : RowFacts beforeImage expectedScores expectedSelectors 111 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_112 : RowFacts beforeImage expectedScores expectedSelectors 112 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_113 : RowFacts beforeImage expectedScores expectedSelectors 113 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_114 : RowFacts beforeImage expectedScores expectedSelectors 114 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_115 : RowFacts beforeImage expectedScores expectedSelectors 115 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_116 : RowFacts beforeImage expectedScores expectedSelectors 116 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_117 : RowFacts beforeImage expectedScores expectedSelectors 117 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_118 : RowFacts beforeImage expectedScores expectedSelectors 118 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_119 : RowFacts beforeImage expectedScores expectedSelectors 119 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_120 : RowFacts beforeImage expectedScores expectedSelectors 120 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_121 : RowFacts beforeImage expectedScores expectedSelectors 121 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_122 : RowFacts beforeImage expectedScores expectedSelectors 122 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_123 : RowFacts beforeImage expectedScores expectedSelectors 123 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_124 : RowFacts beforeImage expectedScores expectedSelectors 124 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_125 : RowFacts beforeImage expectedScores expectedSelectors 125 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_126 : RowFacts beforeImage expectedScores expectedSelectors 126 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_127 : RowFacts beforeImage expectedScores expectedSelectors 127 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_128 : RowFacts beforeImage expectedScores expectedSelectors 128 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_129 : RowFacts beforeImage expectedScores expectedSelectors 129 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_130 : RowFacts beforeImage expectedScores expectedSelectors 130 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_131 : RowFacts beforeImage expectedScores expectedSelectors 131 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_132 : RowFacts beforeImage expectedScores expectedSelectors 132 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_133 : RowFacts beforeImage expectedScores expectedSelectors 133 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_134 : RowFacts beforeImage expectedScores expectedSelectors 134 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_135 : RowFacts beforeImage expectedScores expectedSelectors 135 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_136 : RowFacts beforeImage expectedScores expectedSelectors 136 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_137 : RowFacts beforeImage expectedScores expectedSelectors 137 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_138 : RowFacts beforeImage expectedScores expectedSelectors 138 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_139 : RowFacts beforeImage expectedScores expectedSelectors 139 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_140 : RowFacts beforeImage expectedScores expectedSelectors 140 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_141 : RowFacts beforeImage expectedScores expectedSelectors 141 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_142 : RowFacts beforeImage expectedScores expectedSelectors 142 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_143 : RowFacts beforeImage expectedScores expectedSelectors 143 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_144 : RowFacts beforeImage expectedScores expectedSelectors 144 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_145 : RowFacts beforeImage expectedScores expectedSelectors 145 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_146 : RowFacts beforeImage expectedScores expectedSelectors 146 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_147 : RowFacts beforeImage expectedScores expectedSelectors 147 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_148 : RowFacts beforeImage expectedScores expectedSelectors 148 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_149 : RowFacts beforeImage expectedScores expectedSelectors 149 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_150 : RowFacts beforeImage expectedScores expectedSelectors 150 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_151 : RowFacts beforeImage expectedScores expectedSelectors 151 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_152 : RowFacts beforeImage expectedScores expectedSelectors 152 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_153 : RowFacts beforeImage expectedScores expectedSelectors 153 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_154 : RowFacts beforeImage expectedScores expectedSelectors 154 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_155 : RowFacts beforeImage expectedScores expectedSelectors 155 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_156 : RowFacts beforeImage expectedScores expectedSelectors 156 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_157 : RowFacts beforeImage expectedScores expectedSelectors 157 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_158 : RowFacts beforeImage expectedScores expectedSelectors 158 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_159 : RowFacts beforeImage expectedScores expectedSelectors 159 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_160 : RowFacts beforeImage expectedScores expectedSelectors 160 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_161 : RowFacts beforeImage expectedScores expectedSelectors 161 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_162 : RowFacts beforeImage expectedScores expectedSelectors 162 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_163 : RowFacts beforeImage expectedScores expectedSelectors 163 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_164 : RowFacts beforeImage expectedScores expectedSelectors 164 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_165 : RowFacts beforeImage expectedScores expectedSelectors 165 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_166 : RowFacts beforeImage expectedScores expectedSelectors 166 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_167 : RowFacts beforeImage expectedScores expectedSelectors 167 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_168 : RowFacts beforeImage expectedScores expectedSelectors 168 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_169 : RowFacts beforeImage expectedScores expectedSelectors 169 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_170 : RowFacts beforeImage expectedScores expectedSelectors 170 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_171 : RowFacts beforeImage expectedScores expectedSelectors 171 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_172 : RowFacts beforeImage expectedScores expectedSelectors 172 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_173 : RowFacts beforeImage expectedScores expectedSelectors 173 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_174 : RowFacts beforeImage expectedScores expectedSelectors 174 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_175 : RowFacts beforeImage expectedScores expectedSelectors 175 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_176 : RowFacts beforeImage expectedScores expectedSelectors 176 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_177 : RowFacts beforeImage expectedScores expectedSelectors 177 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_178 : RowFacts beforeImage expectedScores expectedSelectors 178 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_179 : RowFacts beforeImage expectedScores expectedSelectors 179 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_180 : RowFacts beforeImage expectedScores expectedSelectors 180 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_181 : RowFacts beforeImage expectedScores expectedSelectors 181 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_182 : RowFacts beforeImage expectedScores expectedSelectors 182 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_183 : RowFacts beforeImage expectedScores expectedSelectors 183 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_184 : RowFacts beforeImage expectedScores expectedSelectors 184 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_185 : RowFacts beforeImage expectedScores expectedSelectors 185 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_186 : RowFacts beforeImage expectedScores expectedSelectors 186 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_187 : RowFacts beforeImage expectedScores expectedSelectors 187 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_188 : RowFacts beforeImage expectedScores expectedSelectors 188 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_189 : RowFacts beforeImage expectedScores expectedSelectors 189 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_190 : RowFacts beforeImage expectedScores expectedSelectors 190 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_191 : RowFacts beforeImage expectedScores expectedSelectors 191 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_192 : RowFacts beforeImage expectedScores expectedSelectors 192 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_193 : RowFacts beforeImage expectedScores expectedSelectors 193 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_194 : RowFacts beforeImage expectedScores expectedSelectors 194 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_195 : RowFacts beforeImage expectedScores expectedSelectors 195 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_196 : RowFacts beforeImage expectedScores expectedSelectors 196 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_197 : RowFacts beforeImage expectedScores expectedSelectors 197 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_198 : RowFacts beforeImage expectedScores expectedSelectors 198 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_199 : RowFacts beforeImage expectedScores expectedSelectors 199 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_200 : RowFacts beforeImage expectedScores expectedSelectors 200 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_201 : RowFacts beforeImage expectedScores expectedSelectors 201 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_202 : RowFacts beforeImage expectedScores expectedSelectors 202 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_203 : RowFacts beforeImage expectedScores expectedSelectors 203 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_204 : RowFacts beforeImage expectedScores expectedSelectors 204 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_205 : RowFacts beforeImage expectedScores expectedSelectors 205 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_206 : RowFacts beforeImage expectedScores expectedSelectors 206 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_207 : RowFacts beforeImage expectedScores expectedSelectors 207 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_208 : RowFacts beforeImage expectedScores expectedSelectors 208 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_209 : RowFacts beforeImage expectedScores expectedSelectors 209 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_210 : RowFacts beforeImage expectedScores expectedSelectors 210 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_211 : RowFacts beforeImage expectedScores expectedSelectors 211 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_212 : RowFacts beforeImage expectedScores expectedSelectors 212 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_213 : RowFacts beforeImage expectedScores expectedSelectors 213 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_214 : RowFacts beforeImage expectedScores expectedSelectors 214 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_215 : RowFacts beforeImage expectedScores expectedSelectors 215 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_216 : RowFacts beforeImage expectedScores expectedSelectors 216 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_217 : RowFacts beforeImage expectedScores expectedSelectors 217 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_218 : RowFacts beforeImage expectedScores expectedSelectors 218 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_219 : RowFacts beforeImage expectedScores expectedSelectors 219 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_220 : RowFacts beforeImage expectedScores expectedSelectors 220 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_221 : RowFacts beforeImage expectedScores expectedSelectors 221 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_222 : RowFacts beforeImage expectedScores expectedSelectors 222 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_223 : RowFacts beforeImage expectedScores expectedSelectors 223 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_224 : RowFacts beforeImage expectedScores expectedSelectors 224 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_225 : RowFacts beforeImage expectedScores expectedSelectors 225 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_226 : RowFacts beforeImage expectedScores expectedSelectors 226 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_227 : RowFacts beforeImage expectedScores expectedSelectors 227 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_228 : RowFacts beforeImage expectedScores expectedSelectors 228 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_229 : RowFacts beforeImage expectedScores expectedSelectors 229 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_230 : RowFacts beforeImage expectedScores expectedSelectors 230 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_231 : RowFacts beforeImage expectedScores expectedSelectors 231 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_232 : RowFacts beforeImage expectedScores expectedSelectors 232 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_233 : RowFacts beforeImage expectedScores expectedSelectors 233 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_234 : RowFacts beforeImage expectedScores expectedSelectors 234 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_235 : RowFacts beforeImage expectedScores expectedSelectors 235 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_236 : RowFacts beforeImage expectedScores expectedSelectors 236 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_237 : RowFacts beforeImage expectedScores expectedSelectors 237 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_238 : RowFacts beforeImage expectedScores expectedSelectors 238 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_239 : RowFacts beforeImage expectedScores expectedSelectors 239 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_240 : RowFacts beforeImage expectedScores expectedSelectors 240 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_241 : RowFacts beforeImage expectedScores expectedSelectors 241 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_242 : RowFacts beforeImage expectedScores expectedSelectors 242 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_243 : RowFacts beforeImage expectedScores expectedSelectors 243 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_244 : RowFacts beforeImage expectedScores expectedSelectors 244 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_245 : RowFacts beforeImage expectedScores expectedSelectors 245 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_246 : RowFacts beforeImage expectedScores expectedSelectors 246 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_247 : RowFacts beforeImage expectedScores expectedSelectors 247 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_248 : RowFacts beforeImage expectedScores expectedSelectors 248 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_249 : RowFacts beforeImage expectedScores expectedSelectors 249 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_250 : RowFacts beforeImage expectedScores expectedSelectors 250 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_251 : RowFacts beforeImage expectedScores expectedSelectors 251 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_252 : RowFacts beforeImage expectedScores expectedSelectors 252 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_253 : RowFacts beforeImage expectedScores expectedSelectors 253 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_254 : RowFacts beforeImage expectedScores expectedSelectors 254 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_255 : RowFacts beforeImage expectedScores expectedSelectors 255 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_256 : RowFacts beforeImage expectedScores expectedSelectors 256 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_257 : RowFacts beforeImage expectedScores expectedSelectors 257 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_258 : RowFacts beforeImage expectedScores expectedSelectors 258 := by
  unfold RowFacts
  decide +kernel

private theorem checked_row_259 : RowFacts beforeImage expectedScores expectedSelectors 259 := by
  unfold RowFacts
  decide +kernel

private theorem checked_rows (current : Nat) (bounded : current < 260) :
    RowFacts beforeImage expectedScores expectedSelectors current := by
  interval_cases current

  · exact checked_row_000

  · exact checked_row_001

  · exact checked_row_002

  · exact checked_row_003

  · exact checked_row_004

  · exact checked_row_005

  · exact checked_row_006

  · exact checked_row_007

  · exact checked_row_008

  · exact checked_row_009

  · exact checked_row_010

  · exact checked_row_011

  · exact checked_row_012

  · exact checked_row_013

  · exact checked_row_014

  · exact checked_row_015

  · exact checked_row_016

  · exact checked_row_017

  · exact checked_row_018

  · exact checked_row_019

  · exact checked_row_020

  · exact checked_row_021

  · exact checked_row_022

  · exact checked_row_023

  · exact checked_row_024

  · exact checked_row_025

  · exact checked_row_026

  · exact checked_row_027

  · exact checked_row_028

  · exact checked_row_029

  · exact checked_row_030

  · exact checked_row_031

  · exact checked_row_032

  · exact checked_row_033

  · exact checked_row_034

  · exact checked_row_035

  · exact checked_row_036

  · exact checked_row_037

  · exact checked_row_038

  · exact checked_row_039

  · exact checked_row_040

  · exact checked_row_041

  · exact checked_row_042

  · exact checked_row_043

  · exact checked_row_044

  · exact checked_row_045

  · exact checked_row_046

  · exact checked_row_047

  · exact checked_row_048

  · exact checked_row_049

  · exact checked_row_050

  · exact checked_row_051

  · exact checked_row_052

  · exact checked_row_053

  · exact checked_row_054

  · exact checked_row_055

  · exact checked_row_056

  · exact checked_row_057

  · exact checked_row_058

  · exact checked_row_059

  · exact checked_row_060

  · exact checked_row_061

  · exact checked_row_062

  · exact checked_row_063

  · exact checked_row_064

  · exact checked_row_065

  · exact checked_row_066

  · exact checked_row_067

  · exact checked_row_068

  · exact checked_row_069

  · exact checked_row_070

  · exact checked_row_071

  · exact checked_row_072

  · exact checked_row_073

  · exact checked_row_074

  · exact checked_row_075

  · exact checked_row_076

  · exact checked_row_077

  · exact checked_row_078

  · exact checked_row_079

  · exact checked_row_080

  · exact checked_row_081

  · exact checked_row_082

  · exact checked_row_083

  · exact checked_row_084

  · exact checked_row_085

  · exact checked_row_086

  · exact checked_row_087

  · exact checked_row_088

  · exact checked_row_089

  · exact checked_row_090

  · exact checked_row_091

  · exact checked_row_092

  · exact checked_row_093

  · exact checked_row_094

  · exact checked_row_095

  · exact checked_row_096

  · exact checked_row_097

  · exact checked_row_098

  · exact checked_row_099

  · exact checked_row_100

  · exact checked_row_101

  · exact checked_row_102

  · exact checked_row_103

  · exact checked_row_104

  · exact checked_row_105

  · exact checked_row_106

  · exact checked_row_107

  · exact checked_row_108

  · exact checked_row_109

  · exact checked_row_110

  · exact checked_row_111

  · exact checked_row_112

  · exact checked_row_113

  · exact checked_row_114

  · exact checked_row_115

  · exact checked_row_116

  · exact checked_row_117

  · exact checked_row_118

  · exact checked_row_119

  · exact checked_row_120

  · exact checked_row_121

  · exact checked_row_122

  · exact checked_row_123

  · exact checked_row_124

  · exact checked_row_125

  · exact checked_row_126

  · exact checked_row_127

  · exact checked_row_128

  · exact checked_row_129

  · exact checked_row_130

  · exact checked_row_131

  · exact checked_row_132

  · exact checked_row_133

  · exact checked_row_134

  · exact checked_row_135

  · exact checked_row_136

  · exact checked_row_137

  · exact checked_row_138

  · exact checked_row_139

  · exact checked_row_140

  · exact checked_row_141

  · exact checked_row_142

  · exact checked_row_143

  · exact checked_row_144

  · exact checked_row_145

  · exact checked_row_146

  · exact checked_row_147

  · exact checked_row_148

  · exact checked_row_149

  · exact checked_row_150

  · exact checked_row_151

  · exact checked_row_152

  · exact checked_row_153

  · exact checked_row_154

  · exact checked_row_155

  · exact checked_row_156

  · exact checked_row_157

  · exact checked_row_158

  · exact checked_row_159

  · exact checked_row_160

  · exact checked_row_161

  · exact checked_row_162

  · exact checked_row_163

  · exact checked_row_164

  · exact checked_row_165

  · exact checked_row_166

  · exact checked_row_167

  · exact checked_row_168

  · exact checked_row_169

  · exact checked_row_170

  · exact checked_row_171

  · exact checked_row_172

  · exact checked_row_173

  · exact checked_row_174

  · exact checked_row_175

  · exact checked_row_176

  · exact checked_row_177

  · exact checked_row_178

  · exact checked_row_179

  · exact checked_row_180

  · exact checked_row_181

  · exact checked_row_182

  · exact checked_row_183

  · exact checked_row_184

  · exact checked_row_185

  · exact checked_row_186

  · exact checked_row_187

  · exact checked_row_188

  · exact checked_row_189

  · exact checked_row_190

  · exact checked_row_191

  · exact checked_row_192

  · exact checked_row_193

  · exact checked_row_194

  · exact checked_row_195

  · exact checked_row_196

  · exact checked_row_197

  · exact checked_row_198

  · exact checked_row_199

  · exact checked_row_200

  · exact checked_row_201

  · exact checked_row_202

  · exact checked_row_203

  · exact checked_row_204

  · exact checked_row_205

  · exact checked_row_206

  · exact checked_row_207

  · exact checked_row_208

  · exact checked_row_209

  · exact checked_row_210

  · exact checked_row_211

  · exact checked_row_212

  · exact checked_row_213

  · exact checked_row_214

  · exact checked_row_215

  · exact checked_row_216

  · exact checked_row_217

  · exact checked_row_218

  · exact checked_row_219

  · exact checked_row_220

  · exact checked_row_221

  · exact checked_row_222

  · exact checked_row_223

  · exact checked_row_224

  · exact checked_row_225

  · exact checked_row_226

  · exact checked_row_227

  · exact checked_row_228

  · exact checked_row_229

  · exact checked_row_230

  · exact checked_row_231

  · exact checked_row_232

  · exact checked_row_233

  · exact checked_row_234

  · exact checked_row_235

  · exact checked_row_236

  · exact checked_row_237

  · exact checked_row_238

  · exact checked_row_239

  · exact checked_row_240

  · exact checked_row_241

  · exact checked_row_242

  · exact checked_row_243

  · exact checked_row_244

  · exact checked_row_245

  · exact checked_row_246

  · exact checked_row_247

  · exact checked_row_248

  · exact checked_row_249

  · exact checked_row_250

  · exact checked_row_251

  · exact checked_row_252

  · exact checked_row_253

  · exact checked_row_254

  · exact checked_row_255

  · exact checked_row_256

  · exact checked_row_257

  · exact checked_row_258

  · exact checked_row_259


theorem selected_score_projection :
    ScoreBinding beforeImage expectedScores expectedSelectors ∧
    ScoreBinding afterImage expectedScores expectedSelectors ∧
    IntegralScores beforeImage ∧ IntegralScores afterImage := by
  have allRows := score_binding_from_rows beforeImage expectedScores expectedSelectors checked_rows
  rw [← selected_byte_images.2.2]
  exact ⟨allRows.1, allRows.1, allRows.2, allRows.2⟩

theorem selected_mass_projection :
    (∀ current < 260, Phase17Protected.rowAt Phase17Protected.observedBefore current =
      decodedRow beforeImage current) ∧
    (∀ current < 260, Phase17Protected.rowAt Phase17Protected.observedAfter current =
      decodedRow afterImage current) := by
  have beforeRows : Phase17Protected.observedBefore.rows = expectedScores.map massMinusOne := by decide +kernel
  have afterRows : Phase17Protected.observedAfter.rows = expectedScores.map massMinusOne := by decide +kernel
  have beforeSelectors : Phase17Protected.observedBefore.selectors = expectedSelectors := by decide +kernel
  have afterSelectors : Phase17Protected.observedAfter.selectors = expectedSelectors := by decide +kernel
  exact ⟨mass_binding_sound beforeImage expectedScores expectedSelectors
      Phase17Protected.observedBefore selected_score_projection.1 beforeRows beforeSelectors,
    mass_binding_sound afterImage expectedScores expectedSelectors
      Phase17Protected.observedAfter selected_score_projection.2.1 afterRows afterSelectors⟩

theorem selected_goal_decode :
    GoalBinding beforeImage selectedMarkers selectedTargets ∧
    GoalBinding afterImage selectedMarkers selectedTargets := by
  have before : GoalBinding beforeImage selectedMarkers selectedTargets := by
    unfold GoalBinding
    decide +kernel
  rw [← selected_byte_images.2.2]
  exact ⟨before, before⟩

theorem selected_information_transport :
    (Phase17Finite.learned Phase17Finite.selectedConfiguration).informationValue Phase17Finite.selectedBefore =
      decodedInformationSum beforeImage Phase17Protected.boundContract.positions ∧
    (Phase17Finite.learned Phase17Finite.selectedConfiguration).informationValue Phase17Finite.selectedAfter =
      decodedInformationSum afterImage Phase17Protected.boundContract.positions ∧
    decodedInformationSum afterImage Phase17Protected.boundContract.positions =
      decodedInformationSum beforeImage Phase17Protected.boundContract.positions := by
  have positions : ∀ position ∈ Phase17Protected.boundContract.positions, position.1 < 260 := by decide +kernel
  exact ⟨information_binding_sound beforeImage Phase17Protected.observedBefore
      selected_mass_projection.1 _ positions,
    information_binding_sound afterImage Phase17Protected.observedAfter
      selected_mass_projection.2 _ positions,
    congrArg (fun image => decodedInformationSum image Phase17Protected.boundContract.positions)
      selected_byte_images.2.2.symm⟩

/-- The existing selected finite-model acceptance now carries concrete decoded
    byte/probability/goal bindings. It is still not physical root acceptance. -/
theorem selected_learned_acceptance_bound :
    Learned.LearnedAcceptedStep (Phase17Finite.learned Phase17Finite.selectedConfiguration)
      Phase17Finite.selectedBefore Phase17Finite.selectedCandidate
      (Phase17Finite.packet Phase17Finite.selectedConfiguration
        Phase17Finite.selectedBefore Phase17Finite.selectedEvidence) ∧
    CapturedProjection beforeImage Phase17Protected.observedBefore selectedMarkers selectedTargets ∧
    CapturedProjection afterImage Phase17Protected.observedAfter selectedMarkers selectedTargets := by
  refine ⟨Phase17Finite.selected_learned_accepted, ?_, ?_⟩
  · exact ⟨selected_byte_images.1, selected_score_projection.2.2.1,
      selected_mass_projection.1, by decide +kernel, selected_goal_decode.1⟩
  · exact ⟨selected_byte_images.2.1, selected_score_projection.2.2.2,
      selected_mass_projection.2, by decide +kernel, selected_goal_decode.2⟩

theorem selected_codec_edges :
    signed16 0 128 = -32768 ∧ signed16 255 127 = 32767 ∧
    signed16 255 255 = -1 ∧ signed16 0 248 = -2048 ∧
    (-2049 : Int) / 2048 = -2 ∧ (-2049 : Int) % 2048 ≠ 0 ∧
    (-2048 : Int) / 2048 = -1 ∧ (-2048 : Int) % 2048 = 0 ∧
    clip (-16) = -15 ∧ clip 16 = 15 ∧
    massMinusOne [-16, -15] = [0, 0] ∧
    massMinusOne [-16, 15] = [0, 1073741823] := by decide +kernel

theorem selected_decoder_edges :
    greedyToken ([7, 7, 3] ++ List.replicate 257 0) = 0 ∧
    greedyToken ([1, 5, 5, 0] ++ List.replicate 256 0) = 1 ∧
    greedyToken ([-16, -15] ++ List.replicate 258 (-16)) = 1 ∧
    decodeWith (fun _ => List.replicate 258 0 ++ [1, 0]) 16 42 = ⟨[258], .eos⟩ ∧
    decodeWith (fun _ => List.replicate 256 0 ++ [1, 0, 0, 0]) 16 42 = ⟨[256], .nonByte⟩ ∧
    decodeWith (fun _ => 1 :: List.replicate 259 0) 2 42 = ⟨[0, 0], .limit⟩ := by decide +kernel

end Phase17Sparse
