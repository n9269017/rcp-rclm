import ProposalProvenance

/-
Phase 17AC: the present-only finite controller protocol.

Selection is the unchanged Phase17Provenance.choose. This module models control
observations, terminal priorities, and guarded continuation; it does not establish
evaluator truth, receipt/hash authentication, future-independent input provenance,
compiler-process resumption, physical root acceptance, or promotion.

The actual initial credit budget is a separate unbounded natural number. The
older provenance Context.credits is selection-inert metadata and is not replaced
or used to identify Python checkpoints here. ContextShape deliberately does not
assert the older ContextValid restriction credits <= 32.
-/
namespace Phase17Controller

open Phase17Provenance

inductive StopReason where
  | external
  | safety
  deriving DecidableEq, Repr

structure Observation where
  index : Nat
  passed : Bool
  deriving DecidableEq, Repr

structure Prefix where
  initialCredits : Nat
  observations : List Observation
  stop : Option StopReason
  deriving DecidableEq, Repr

inductive Action where
  | evaluate (index : Nat)
  | awaitRoot
  | searchExhausted
  | resourceExhausted
  | externalStop
  | safetyHalt
  deriving DecidableEq, Repr

def ContextShape (c : Context) : Prop := c.rows.length = 32 ∧ c.offset < 32

def initial (credits : Nat) : Prefix := ⟨credits, [], none⟩

def seen (p : Prefix) : List Nat := p.observations.map Observation.index

def lastPassed (p : Prefix) : Bool :=
  ((p.observations.getLast?).map Observation.passed).getD false

/-- None means that selection was unavailable for an ongoing malformed prefix.
    On replay-reachable prefixes with ContextShape this case is impossible. -/
def decision (c : Context) (p : Prefix) : Option Action :=
  match p.stop with
  | some .external => some .externalStop
  | some .safety => some .safetyHalt
  | none =>
    if lastPassed p then some .awaitRoot
    else if p.observations.length = 32 then some .searchExhausted
    else if p.observations.length < p.initialCredits then
      (choose c (seen p)).map Action.evaluate
    else some .resourceExhausted

def advance (c : Context) (p : Prefix) (o : Observation) : Option Prefix :=
  match decision c p with
  | some (.evaluate i) =>
    if o.index = i then some { p with observations := p.observations ++ [o] }
    else none
  | _ => none

def halt (c : Context) (p : Prefix) (reason : StopReason) : Option Prefix :=
  match decision c p with
  | some (.evaluate _) => some { p with stop := some reason }
  | _ => none

def replay (c : Context) (p : Prefix) : List Observation → Option Prefix
  | [] => some p
  | o :: rest => (advance c p o).bind (fun q => replay c q rest)

/-- Counterfactual protocol run with a rejection observation at every step.
    The function does not assert that an evaluator would actually reject. -/
def rejectionRun (c : Context) (p : Prefix) : Nat → Option Prefix
  | 0 => some p
  | n + 1 =>
    match decision c p with
    | some (.evaluate i) =>
      (advance c p ⟨i, false⟩).bind (fun q => rejectionRun c q n)
    | _ => none

def Terminal (a : Action) : Prop := ∀ i, a ≠ .evaluate i

def Invariant (p : Prefix) : Prop :=
  (seen p).Nodup ∧ (∀ i ∈ seen p, i < 32) ∧
  p.observations.length ≤ p.initialCredits ∧ p.observations.length ≤ 32

private theorem fold_select_member (c : Context) (prior : List Nat)
    (first : Nat) (rest : List Nat) :
    rest.foldl (fun best i => if beats c prior i best then i else best) first
      ∈ first :: rest := by
  induction rest generalizing first with
  | nil => simp
  | cons i rest ih =>
    simp only [List.foldl_cons]
    have member := ih (if beats c prior i first then i else first)
    simp only [List.mem_cons] at member ⊢
    rcases member with eq | member
    · by_cases h : beats c prior i first = true
      · simp only [h, if_true] at eq ⊢
        exact Or.inr (Or.inl eq)
      · simp only [h] at eq ⊢
        exact Or.inl eq
    · exact Or.inr (Or.inr member)

private theorem ranked_choice_member (c : Context) (prior : List Nat) (i : Nat)
    (early : prior.length < 4) (chosen : choose c prior = some i) :
    i ∈ (List.range c.rows.length).filter (fun j => !prior.contains j) := by
  cases hs : (List.range c.rows.length).filter (fun j => !prior.contains j) with
  | nil => simp only [choose, if_pos early, hs, reduceCtorEq] at chosen
  | cons first rest =>
    have eq : rest.foldl (fun best j => if beats c prior j best then j else best) first = i := by
      simpa only [choose, if_pos early, hs, Option.some.injEq] using chosen
    rw [← eq]
    exact fold_select_member c prior first rest

/-- Every original selector result is fresh; this is not a no-repeat premise. -/
theorem choose_fresh (c : Context) (prior : List Nat) (i : Nat)
    (chosen : choose c prior = some i) : i ∉ prior := by
  by_cases early : prior.length < 4
  · have member := ranked_choice_member c prior i early chosen
    have filtered := (List.mem_filter.mp member).2
    simpa using filtered
  · have found : ((List.range 32).map (fun j => (c.offset + 17 * j) % 32)).find?
        (fun j => !prior.contains j) = some i := by
      simpa [choose, early] using chosen
    have filtered := List.find?_some found
    simpa using filtered

theorem choose_in_range (c : Context) (shape : ContextShape c)
    (prior : List Nat) (i : Nat) (chosen : choose c prior = some i) : i < 32 := by
  by_cases early : prior.length < 4
  · have member := (List.mem_filter.mp (ranked_choice_member c prior i early chosen)).1
    have bound := List.mem_range.mp member
    simpa [shape.1] using bound
  · have found : ((List.range 32).map (fun j => (c.offset + 17 * j) % 32)).find?
        (fun j => !prior.contains j) = some i := by
      simpa [choose, early] using chosen
    rcases List.mem_map.mp (List.mem_of_find?_eq_some found) with ⟨j, _, eq⟩
    rw [← eq]
    exact Nat.mod_lt _ (by decide)

/-- The fixed finite stride is checked by the kernel for every permitted offset.
    This is a finite mathematical fact, not native execution or sampled offsets. -/
theorem fallback_complete (offset : Nat) (bound : offset < 32) (i : Nat) (hi : i < 32) :
    i ∈ (List.range 32).map (fun j => (offset + 17 * j) % 32) := by
  have checked : ∀ offset : Fin 32, ∀ i : Fin 32,
      i.val ∈ (List.range 32).map (fun j => (offset.val + 17 * j) % 32) := by
    decide +kernel
  exact checked ⟨offset, bound⟩ ⟨i, hi⟩

theorem fallback_nodup (offset : Nat) (bound : offset < 32) :
    ((List.range 32).map (fun j => (offset + 17 * j) % 32)).Nodup := by
  have checked : ∀ offset : Fin 32,
      ((List.range 32).map (fun j => (offset.val + 17 * j) % 32)).Nodup := by
    decide +kernel
  exact checked ⟨offset, bound⟩

private theorem choose_none_covers (c : Context) (shape : ContextShape c)
    (prior : List Nat) (missing : choose c prior = none) :
    ∀ i, i < 32 → i ∈ prior := by
  intro i hi
  by_cases early : prior.length < 4
  · have empty : (List.range c.rows.length).filter (fun j => !prior.contains j) = [] := by
      cases hs : (List.range c.rows.length).filter (fun j => !prior.contains j) with
      | nil => rfl
      | cons first rest => simp only [choose, if_pos early, hs, reduceCtorEq] at missing
    by_contra absent
    have member : i ∈ (List.range c.rows.length).filter (fun j => !prior.contains j) := by
      simp [shape.1, hi, absent]
    rw [empty] at member
    simp at member
  · have none : ((List.range 32).map (fun j => (c.offset + 17 * j) % 32)).find?
        (fun j => !prior.contains j) = none := by
      simpa [choose, early] using missing
    have rejected := List.find?_eq_none.mp none i (fallback_complete c.offset shape.2 i hi)
    simpa using rejected

theorem choose_available (c : Context) (shape : ContextShape c) (prior : List Nat)
    (short : prior.length < 32) : ∃ i, choose c prior = some i := by
  cases chosen : choose c prior with
  | some i => exact ⟨i, rfl⟩
  | none =>
    have covered := choose_none_covers c shape prior chosen
    have subset : Finset.range 32 ⊆ prior.toFinset := by
      intro i hi
      exact List.mem_toFinset.mpr (covered i (Finset.mem_range.mp hi))
    have lower : 32 ≤ prior.length := calc
      32 = (Finset.range 32).card := by simp
      _ ≤ prior.toFinset.card := Finset.card_le_card subset
      _ ≤ prior.length := List.toFinset_card_le prior
    omega

theorem decision_evaluate_iff (c : Context) (p : Prefix) (i : Nat) :
    decision c p = some (.evaluate i) ↔
      p.stop = none ∧ lastPassed p = false ∧ p.observations.length ≠ 32 ∧
      p.observations.length < p.initialCredits ∧ choose c (seen p) = some i := by
  cases hs : p.stop with
  | some reason => cases reason <;> simp [decision, hs]
  | none =>
    cases hp : lastPassed p <;>
      by_cases full : p.observations.length = 32 <;>
      by_cases credit : p.observations.length < p.initialCredits <;>
      simp [decision, hs, hp, full, credit]

theorem advance_spec (c : Context) (p q : Prefix) (o : Observation)
    (advanced : advance c p o = some q) :
    ∃ i, decision c p = some (.evaluate i) ∧ o.index = i ∧
      q = { p with observations := p.observations ++ [o] } := by
  cases hd : decision c p with
  | none => simp [advance, hd] at advanced
  | some action =>
    cases action with
    | evaluate i =>
      by_cases eq : o.index = i
      · exact ⟨i, rfl, eq, (by simpa [advance, hd, eq] using advanced.symm)⟩
      · simp [advance, hd, eq] at advanced
    | awaitRoot => simp [advance, hd] at advanced
    | searchExhausted => simp [advance, hd] at advanced
    | resourceExhausted => simp [advance, hd] at advanced
    | externalStop => simp [advance, hd] at advanced
    | safetyHalt => simp [advance, hd] at advanced

theorem initial_invariant (credits : Nat) : Invariant (initial credits) := by
  simp [Invariant, initial, seen]

theorem advance_invariant (c : Context) (shape : ContextShape c) (p q : Prefix)
    (o : Observation) (valid : Invariant p) (advanced : advance c p o = some q) :
    Invariant q := by
  rcases advance_spec c p q o advanced with ⟨i, selected, eq, rfl⟩
  rcases (decision_evaluate_iff c p i).mp selected with ⟨_, _, notFull, credit, chosen⟩
  have fresh : o.index ∉ seen p := by rw [eq]; exact choose_fresh c (seen p) i chosen
  have bound : o.index < 32 := by rw [eq]; exact choose_in_range c shape (seen p) i chosen
  rcases valid with ⟨unique, range, _, length⟩
  refine ⟨?_, ?_, ?_, ?_⟩
  · simpa [seen, List.concat_eq_append] using (List.Nodup.concat fresh unique)
  · intro j member
    simp only [seen, List.map_append, List.map_singleton, List.mem_append,
      List.mem_singleton] at member
    rcases member with member | rfl
    · exact range j member
    · exact bound
  · simp only [List.length_append, List.length_singleton]
    omega
  · simp only [List.length_append, List.length_singleton]
    omega

theorem replay_invariant (c : Context) (shape : ContextShape c) (p q : Prefix)
    (xs : List Observation) (valid : Invariant p) (run : replay c p xs = some q) :
    Invariant q := by
  induction xs generalizing p with
  | nil =>
    have eq : p = q := by simpa [replay] using run
    exact eq ▸ valid
  | cons o rest ih =>
    cases hs : advance c p o with
    | none => simp [replay, hs] at run
    | some next =>
      apply ih next (advance_invariant c shape p next o valid hs)
      simpa [replay, hs] using run

theorem replay_no_repeat (c : Context) (shape : ContextShape c) (credits : Nat)
    (xs : List Observation) (p : Prefix) (run : replay c (initial credits) xs = some p) :
    (seen p).Nodup :=
  (replay_invariant c shape (initial credits) p xs (initial_invariant credits) run).1

theorem replay_result (c : Context) (p q : Prefix) (xs : List Observation)
    (run : replay c p xs = some q) :
    q.initialCredits = p.initialCredits ∧ q.observations = p.observations ++ xs ∧ q.stop = p.stop := by
  induction xs generalizing p with
  | nil =>
    have eq : p = q := by simpa [replay] using run
    subst q
    simp
  | cons o rest ih =>
    cases hs : advance c p o with
    | none => simp [replay, hs] at run
    | some next =>
      have tail : replay c next rest = some q := by simpa [replay, hs] using run
      rcases ih next tail with ⟨credits, observations, stop⟩
      rcases advance_spec c p next o hs with ⟨_, _, _, rfl⟩
      refine ⟨credits, ?_, stop⟩
      simpa [List.append_assoc] using observations

/-- Successful guarded replay supplies the original provenance choice-order
    predicate. Together with replay_no_repeat it discharges, rather than assumes,
    those two parts of Produced. Other provenance premises remain separate. -/
theorem replay_follows (c : Context) (p q : Prefix) (xs : List Observation)
    (run : replay c p xs = some q) :
    follows c (seen p) (xs.map Observation.index) = true := by
  induction xs generalizing p with
  | nil => rfl
  | cons o rest ih =>
    cases hs : advance c p o with
    | none => simp [replay, hs] at run
    | some next =>
      have tail : replay c next rest = some q := by simpa [replay, hs] using run
      have followed := ih next tail
      rcases advance_spec c p next o hs with ⟨i, selected, eq, rfl⟩
      have chosen := ((decision_evaluate_iff c p i).mp selected).2.2.2.2
      have chosen' : choose c (seen p) = some o.index := by simpa only [eq] using chosen
      simp only [List.map_cons, follows, chosen', beq_self_eq_true, Bool.true_and]
      simpa only [seen, List.map_append, List.map_singleton] using followed

theorem replay_append (c : Context) (p : Prefix) (xs ys : List Observation) :
    replay c p (xs ++ ys) = (replay c p xs).bind (fun q => replay c q ys) := by
  induction xs generalizing p with
  | nil => rfl
  | cons o rest ih =>
    cases hs : advance c p o with
    | none => simp [replay, hs]
    | some next => simp [replay, hs, ih]

theorem deterministic_prefix_splice (c : Context) (p middle final : Prefix)
    (xs ys : List Observation) (first : replay c p xs = some middle)
    (second : replay c middle ys = some final) :
    replay c p (xs ++ ys) = some final := by
  rw [replay_append, first]
  exact second

theorem pass_priority (c : Context) (p : Prefix)
    (openPrefix : p.stop = none) (passed : lastPassed p = true) :
    decision c p = some .awaitRoot := by
  simp [decision, openPrefix, passed]

theorem exhaustion_priority (c : Context) (p : Prefix)
    (openPrefix : p.stop = none) (rejected : lastPassed p = false)
    (full : p.observations.length = 32) :
    decision c p = some .searchExhausted := by
  simp [decision, openPrefix, rejected, full]

theorem resource_exhaustion (c : Context) (p : Prefix)
    (openPrefix : p.stop = none) (rejected : lastPassed p = false)
    (short : p.observations.length < 32) (empty : p.initialCredits = p.observations.length) :
    decision c p = some .resourceExhausted := by
  simp [decision, openPrefix, rejected, Nat.ne_of_lt short, empty]

theorem terminal_cannot_advance (c : Context) (p : Prefix) (a : Action)
    (terminal : Terminal a) (recorded : decision c p = some a) (o : Observation) :
    advance c p o = none := by
  cases a with
  | evaluate i => exact False.elim (terminal i rfl)
  | awaitRoot => simp [advance, recorded]
  | searchExhausted => simp [advance, recorded]
  | resourceExhausted => simp [advance, recorded]
  | externalStop => simp [advance, recorded]
  | safetyHalt => simp [advance, recorded]

theorem terminal_cannot_halt (c : Context) (p : Prefix) (a : Action)
    (terminal : Terminal a) (recorded : decision c p = some a) (reason : StopReason) :
    halt c p reason = none := by
  cases a with
  | evaluate i => exact False.elim (terminal i rfl)
  | awaitRoot => simp [halt, recorded]
  | searchExhausted => simp [halt, recorded]
  | resourceExhausted => simp [halt, recorded]
  | externalStop => simp [halt, recorded]
  | safetyHalt => simp [halt, recorded]

theorem halt_preserves_history (c : Context) (p q : Prefix) (reason : StopReason)
    (stopped : halt c p reason = some q) :
    q.initialCredits = p.initialCredits ∧ q.observations = p.observations ∧
      q.stop = some reason := by
  cases hd : decision c p with
  | none => simp [halt, hd] at stopped
  | some a =>
    cases a <;> simp [halt, hd] at stopped
    subst q
    exact ⟨rfl, rfl, rfl⟩

theorem halted_decision (c : Context) (p q : Prefix) (reason : StopReason)
    (stopped : halt c p reason = some q) :
    decision c q = some (match reason with | .external => .externalStop | .safety => .safetyHalt) := by
  have hs := (halt_preserves_history c p q reason stopped).2.2
  cases reason <;> simp [decision, hs]

theorem decision_search_exhausted_length (c : Context) (p : Prefix)
    (terminal : decision c p = some .searchExhausted) : p.observations.length = 32 := by
  cases hs : p.stop with
  | some reason => cases reason <;> simp [decision, hs] at terminal
  | none =>
    cases hp : lastPassed p with
    | true => simp [decision, hs, hp] at terminal
    | false =>
      by_cases full : p.observations.length = 32
      · exact full
      · by_cases credit : p.observations.length < p.initialCredits
        · cases hc : choose c (seen p) <;> simp [decision, hs, hp, full, credit, hc] at terminal
        · simp [decision, hs, hp, full, credit] at terminal

theorem invariant_full_coverage (p : Prefix) (valid : Invariant p)
    (full : p.observations.length = 32) :
    (seen p).toFinset = Finset.range 32 := by
  have subset : (seen p).toFinset ⊆ Finset.range 32 := by
    intro i hi
    exact Finset.mem_range.mpr (valid.2.1 i (List.mem_toFinset.mp hi))
  apply Finset.eq_of_subset_of_card_le subset
  have card : (seen p).toFinset.card = 32 := calc
    _ = (seen p).length := List.toFinset_card_of_nodup valid.1
    _ = 32 := by simpa only [seen, List.length_map] using full
  simp only [Finset.card_range, card, le_refl]

theorem exhaustion_covers_grammar (c : Context) (shape : ContextShape c) (credits : Nat)
    (xs : List Observation) (p : Prefix) (run : replay c (initial credits) xs = some p)
    (terminal : decision c p = some .searchExhausted) :
    (seen p).toFinset = Finset.range 32 := by
  have valid := replay_invariant c shape (initial credits) p xs (initial_invariant credits) run
  have full := decision_search_exhausted_length c p terminal
  exact invariant_full_coverage p valid full

theorem decision_progress (c : Context) (shape : ContextShape c) (p : Prefix)
    (openPrefix : p.stop = none) (rejected : lastPassed p = false)
    (short : p.observations.length < 32) (credit : p.observations.length < p.initialCredits) :
    ∃ i, decision c p = some (.evaluate i) := by
  obtain ⟨i, chosen⟩ := choose_available c shape (seen p) (by simpa [seen] using short)
  exact ⟨i, (decision_evaluate_iff c p i).mpr
    ⟨openPrefix, rejected, Nat.ne_of_lt short, credit, chosen⟩⟩

theorem decision_total (c : Context) (shape : ContextShape c) (p : Prefix)
    (valid : Invariant p) : ∃ a, decision c p = some a := by
  cases hs : p.stop with
  | some reason =>
    cases reason with
    | external => exact ⟨.externalStop, by simp [decision, hs]⟩
    | safety => exact ⟨.safetyHalt, by simp [decision, hs]⟩
  | none =>
    cases hp : lastPassed p with
    | true => exact ⟨.awaitRoot, pass_priority c p hs hp⟩
    | false =>
      by_cases full : p.observations.length = 32
      · exact ⟨.searchExhausted, exhaustion_priority c p hs hp full⟩
      · by_cases credit : p.observations.length < p.initialCredits
        · have length := valid.2.2.2
          obtain ⟨i, chosen⟩ := decision_progress c shape p hs hp (by omega) credit
          exact ⟨.evaluate i, chosen⟩
        · exact ⟨.resourceExhausted, by simp [decision, hs, hp, full, credit]⟩

theorem replay_decision_total (c : Context) (shape : ContextShape c) (credits : Nat)
    (xs : List Observation) (p : Prefix) (run : replay c (initial credits) xs = some p) :
    ∃ a, decision c p = some a :=
  decision_total c shape p
    (replay_invariant c shape (initial credits) p xs (initial_invariant credits) run)

theorem rejection_run_progress (c : Context) (shape : ContextShape c) (p : Prefix)
    (n : Nat) (valid : Invariant p) (openPrefix : p.stop = none)
    (rejected : lastPassed p = false)
    (grammarBound : p.observations.length + n ≤ 32)
    (creditBound : p.observations.length + n ≤ p.initialCredits) :
    ∃ q, rejectionRun c p n = some q ∧ Invariant q ∧ q.stop = none ∧
      lastPassed q = false ∧ q.initialCredits = p.initialCredits ∧
      q.observations.length = p.observations.length + n := by
  induction n generalizing p with
  | zero => exact ⟨p, rfl, valid, openPrefix, rejected, rfl, by omega⟩
  | succ n ih =>
    obtain ⟨i, selected⟩ := decision_progress c shape p openPrefix rejected (by omega) (by omega)
    let o : Observation := ⟨i, false⟩
    let next : Prefix := { p with observations := p.observations ++ [o] }
    have step : advance c p o = some next := by simp [advance, selected, o, next]
    have nextValid := advance_invariant c shape p next o valid step
    have nextOpen : next.stop = none := openPrefix
    have nextRejected : lastPassed next = false := by simp [lastPassed, next, o]
    have nextLength : next.observations.length = p.observations.length + 1 := by simp [next]
    have nextCredits : next.initialCredits = p.initialCredits := rfl
    obtain ⟨q, run, qValid, qOpen, qRejected, qCredits, qLength⟩ :=
      ih next nextValid nextOpen nextRejected (by omega) (by omega)
    refine ⟨q, ?_, qValid, qOpen, qRejected, qCredits.trans nextCredits, ?_⟩
    · simpa [rejectionRun, selected, o, step] using run
    · omega

/-- With at least 32 actual credits, every ranking context of the specified
    shape has a complete rejection-only run. No evaluator verdict is inferred. -/
theorem all_rejections_exhaust (c : Context) (shape : ContextShape c) (credits : Nat)
    (enough : 32 ≤ credits) :
    ∃ p, rejectionRun c (initial credits) 32 = some p ∧
      decision c p = some .searchExhausted ∧
      (seen p).toFinset = Finset.range 32 ∧
      p.observations.length = 32 ∧ p.initialCredits = credits := by
  obtain ⟨p, run, valid, openPrefix, rejected, budget, count⟩ :=
    rejection_run_progress c shape (initial credits) 32 (initial_invariant credits)
      rfl (by simp [lastPassed, initial]) (by simp [initial]) (by simpa [initial] using enough)
  have full : p.observations.length = 32 := by simpa [initial] using count
  exact ⟨p, run, exhaustion_priority c p openPrefix rejected full,
    invariant_full_coverage p valid full, full, budget⟩

theorem partial_rejections_resource_exhaust (c : Context) (shape : ContextShape c)
    (credits : Nat) (short : credits < 32) :
    ∃ p, rejectionRun c (initial credits) credits = some p ∧
      decision c p = some .resourceExhausted ∧
      p.observations.length = credits ∧ p.initialCredits = credits := by
  obtain ⟨p, run, _, openPrefix, rejected, budget, count⟩ :=
    rejection_run_progress c shape (initial credits) credits (initial_invariant credits)
      rfl (by simp [lastPassed, initial]) (by simpa [initial] using short.le)
      (by simp [initial])
  have length : p.observations.length = credits := by simpa [initial] using count
  have budget : p.initialCredits = credits := budget
  refine ⟨p, run, resource_exhaustion c p openPrefix rejected ?_ ?_, length, budget⟩
  · omega
  · omega

theorem rejection_run_replays (c : Context) (p q : Prefix) (n : Nat)
    (run : rejectionRun c p n = some q) :
    ∃ xs : List Observation, replay c p xs = some q ∧ xs.length = n ∧
      ∀ o ∈ xs, o.passed = false := by
  induction n generalizing p with
  | zero =>
    have eq : p = q := by simpa [rejectionRun] using run
    exact ⟨[], by simpa [replay] using congrArg some eq, rfl, by simp⟩
  | succ n ih =>
    cases hd : decision c p with
    | none => simp [rejectionRun, hd] at run
    | some action =>
      cases action with
      | evaluate i =>
        let o : Observation := ⟨i, false⟩
        let next : Prefix := { p with observations := p.observations ++ [o] }
        have step : advance c p o = some next := by simp [advance, hd, o, next]
        have tail : rejectionRun c next n = some q := by
          simpa [rejectionRun, hd, o, step] using run
        obtain ⟨xs, replayed, length, rejected⟩ := ih next tail
        refine ⟨o :: xs, ?_, by simp [length], ?_⟩
        · simpa [replay, step] using replayed
        · intro x member
          rcases List.mem_cons.mp member with rfl | member
          · rfl
          · exact rejected x member
      | awaitRoot => simp [rejectionRun, hd] at run
      | searchExhausted => simp [rejectionRun, hd] at run
      | resourceExhausted => simp [rejectionRun, hd] at run
      | externalStop => simp [rejectionRun, hd] at run
      | safetyHalt => simp [rejectionRun, hd] at run

theorem choose_selection_inputs (c d : Context) (prior : List Nat)
    (sameRows : c.rows = d.rows) (sameOffset : c.offset = d.offset) :
    choose c prior = choose d prior := by
  simp only [choose, beats, score, tie, rejectedCount, rowAt, sameRows, sameOffset]
  rfl

theorem decision_selection_inputs (c d : Context) (p : Prefix)
    (sameRows : c.rows = d.rows) (sameOffset : c.offset = d.offset) :
    decision c p = decision d p := by
  simp only [decision, choose_selection_inputs c d (seen p) sameRows sameOffset]

/-- While both actual budgets have current headroom, their different future
    stopping bounds do not change this next action. Prefix identities may differ. -/
theorem decision_credit_headroom (c : Context) (p q : Prefix)
    (sameObservations : p.observations = q.observations) (sameStop : p.stop = q.stop)
    (leftCredit : p.observations.length < p.initialCredits)
    (rightCredit : q.observations.length < q.initialCredits) :
    decision c p = decision c q := by
  have sameLast : lastPassed p = lastPassed q := by simp [lastPassed, sameObservations]
  have sameSeen : seen p = seen q := by simp [seen, sameObservations]
  have sameLength : p.observations.length = q.observations.length := congrArg List.length sameObservations
  have leftCredit' : q.observations.length < p.initialCredits := by omega
  simp only [decision, sameStop, sameLast, sameSeen, sameLength, leftCredit', rightCredit, if_true]

/-- Explicitly scoped policy invariance. The frozen inputs and the present prefix
    agree; no statement authenticates how those inputs were selected. -/
theorem present_input_invariance (c d : Context) (p q : Prefix)
    (sameContext : c = d) (samePrefix : p = q) : decision c p = decision d q := by
  subst d
  subst q
  rfl

/-- The original selector does not read Context.credits. Changing that metadata
    does not change selection; it does not preserve a Python checkpoint hash. -/
theorem choose_context_credits_irrelevant (c : Context) (credits : Nat) (prior : List Nat) :
    choose { c with credits := credits } prior = choose c prior := by
  rfl

theorem decision_context_credits_irrelevant (c : Context) (credits : Nat) (p : Prefix) :
    decision { c with credits := credits } p = decision c p := by
  simp only [decision, choose_context_credits_irrelevant]

theorem credits_above_grammar_allowed (c : Context) (shape : ContextShape c) (credits : Nat)
    (positive : 0 < credits) : ∃ i, decision c (initial credits) = some (.evaluate i) := by
  obtain ⟨i, chosen⟩ := choose_available c shape [] (by decide)
  exact ⟨i, by simp [decision, initial, lastPassed, seen, positive, chosen]⟩

end Phase17Controller
