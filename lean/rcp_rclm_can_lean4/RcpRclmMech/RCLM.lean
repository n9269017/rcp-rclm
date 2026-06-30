/-
  RCLM canonical refinement module.

  This module proves that the finite RCLM canonical reference object
  refines/forgets down to the RCP canonical reference object.

  Scope:
  * finite canonical RCLM wrapper around the RCP diagonal reference core;
  * checker soundness for the RCLM proof-carrying packet;
  * RCLM-to-RCP forgetful refinement;
  * finite reference-entry and artifact theorems for the declared canonical class.

  Non-scope:
  * the full architecture paper;
  * arbitrary learned-system entry;
  * full empirical validation.
-/

import RcpRclmMech.RCP

namespace RcpRclmMech
namespace RCLM

/-- Canonical RCLM state.  The `core` field is the architecture-general
RCP canonical state; the remaining booleans model the RCLM-specific
certificate gates in the finite canonical witness. -/
structure RCLMState where
  core : RCP.CanonState
  regSemOK : Bool
  typeOK : Bool
  ledgerOK : Bool
  deriving DecidableEq, Repr

/-- Forget the RCLM-specific certificate wrapper to obtain the RCP core. -/
def forgetState (s : RCLMState) : RCP.CanonState :=
  s.core

/-- Canonical RCLM state at time `t`. -/
def stateAt (t : Nat) : RCLMState :=
  { core := RCP.stateAt t, regSemOK := true, typeOK := true, ledgerOK := true }

/-- Canonical RCLM append-only update. -/
def Phi (s : RCLMState) : RCLMState :=
  { core := RCP.Phi s.core, regSemOK := true, typeOK := true, ledgerOK := true }

/-- Canonical RCLM explicit residual vector, inherited from the RCP core. -/
def canonicalResiduals : RCP.SVResiduals :=
  RCP.canonicalResiduals

/-- Proof-carrying RCLM successor packet. -/
structure RCLMPCS where
  state : RCLMState
  next : RCLMState
  residuals : RCP.SVResiduals
  deriving DecidableEq, Repr

/-- Forget an RCLM packet to its RCP core packet. -/
def forgetPCS (p : RCLMPCS) : RCP.PCS :=
  { state := forgetState p.state, next := forgetState p.next, residuals := p.residuals }

/-- Canonical RCLM packet at time `t`. -/
def pcsAt (t : Nat) : RCLMPCS :=
  { state := stateAt t, next := stateAt (t + 1), residuals := canonicalResiduals }

/-- RCLM checker: it checks the RCP core checker plus the RCLM successor
relation, residual vector, and RCLM-specific type/semantic/ledger gates. -/
def CheckRCLM (p : RCLMPCS) : Bool :=
  decide (RCP.CheckRCP (forgetPCS p) = true ∧
          p.next = Phi p.state ∧
          p.residuals = canonicalResiduals ∧
          p.state.regSemOK = true ∧ p.state.typeOK = true ∧ p.state.ledgerOK = true ∧
          p.next.regSemOK = true ∧ p.next.typeOK = true ∧ p.next.ledgerOK = true)

/-- True RCLM canonical obligations. -/
def RCLMObligations (p : RCLMPCS) : Prop :=
  p.next = Phi p.state ∧
  RCP.ResidualsNonpos p.residuals ∧
  p.state.regSemOK = true ∧ p.state.typeOK = true ∧ p.state.ledgerOK = true ∧
  p.next.regSemOK = true ∧ p.next.typeOK = true ∧ p.next.ledgerOK = true ∧
  RCP.CanonicalObligations (forgetPCS p)

/-- RCLM checker soundness. -/
theorem checker_soundness_rclm (p : RCLMPCS) (h : CheckRCLM p = true) :
    RCLMObligations p := by
  unfold CheckRCLM at h
  have hp : RCP.CheckRCP (forgetPCS p) = true ∧
          p.next = Phi p.state ∧
          p.residuals = canonicalResiduals ∧
          p.state.regSemOK = true ∧ p.state.typeOK = true ∧ p.state.ledgerOK = true ∧
          p.next.regSemOK = true ∧ p.next.typeOK = true ∧ p.next.ledgerOK = true :=
    of_decide_eq_true h
  rcases hp with ⟨hcore, hnext, hres, hsReg, hsType, hsLedger, hnReg, hnType, hnLedger⟩
  unfold RCLMObligations
  exact ⟨hnext,
         by rw [hres]; exact RCP.canonical_residuals_nonpositive,
         hsReg, hsType, hsLedger, hnReg, hnType, hnLedger,
         RCP.checker_soundness_rcp (forgetPCS p) hcore⟩

/-- The canonical RCLM packet checks. -/
theorem canonical_packet_checks (t : Nat) :
    CheckRCLM (pcsAt t) = true := by
  simp [CheckRCLM, pcsAt, stateAt, Phi, canonicalResiduals,
        forgetPCS, forgetState, RCP.CheckRCP, RCP.Phi, RCP.stateAt,
        RCP.canonicalResiduals]

/-- RCLM finite reference object. -/
structure RCLMRefSV where
  N : Nat
  state : Nat → RCLMState
  pcs : Nat → RCLMPCS

/-- Build the RCLM finite reference object. -/
def BuildRefSV (N : Nat) : RCLMRefSV :=
  { N := N, state := stateAt, pcs := pcsAt }

/-- Forget an RCLM finite reference object into the RCP finite reference object. -/
def forgetRefSV (r : RCLMRefSV) : RCP.RefSV :=
  { N := r.N, state := fun t => forgetState (r.state t), pcs := fun t => forgetPCS (r.pcs t) }

/-- The RCLM canonical reference refines/forgets to the RCP canonical reference. -/
theorem rclm_forget_refines_rcp (N : Nat) :
    forgetRefSV (BuildRefSV N) = RCP.BuildRefSV N := by
  rfl

/-- RCLM finite seed-library domain. -/
def InRCLMSVSeedLib (s : RCLMState) (N : Nat) : Prop :=
  RCP.InSVSeedLib (forgetState s) N ∧
  s.regSemOK = true ∧ s.typeOK = true ∧ s.ledgerOK = true

/-- RCLM finite successor-verification domain. -/
def InRCLMSVDomain (s : RCLMState) (N : Nat) : Prop :=
  RCP.InSVDomain (forgetState s) N ∧
  s.regSemOK = true ∧ s.typeOK = true ∧ s.ledgerOK = true

/-- RCLM reference-entry theorem. -/
theorem build_refsv_entry (N : Nat) (hN : 2 ≤ N) :
    InRCLMSVSeedLib (stateAt 0) N := by
  unfold InRCLMSVSeedLib stateAt forgetState
  exact ⟨RCP.build_refsv_entry N hN, rfl, rfl, rfl⟩

/-- RCLM finite checked trajectory theorem. -/
theorem finite_checked_trajectory (N t : Nat) (ht : t ≤ N) :
    InRCLMSVDomain (stateAt t) N := by
  unfold InRCLMSVDomain stateAt forgetState
  exact ⟨RCP.finite_checked_trajectory N t ht, rfl, rfl, rfl⟩

/-- For `t < N`, a checked canonical RCLM packet yields RCLM SV-domain membership. -/
theorem checked_packet_implies_sv_domain (N t : Nat) (ht : t < N)
    (_hcheck : CheckRCLM (pcsAt t) = true) :
    InRCLMSVDomain (stateAt t) N := by
  exact finite_checked_trajectory N t (Nat.le_of_lt ht)

/-- RCLM controlled executable artifact summary. -/
structure RCLMArtifact where
  N : Nat
  ref : RCLMRefSV
  allPacketsCheck : ∀ t, t < N → CheckRCLM (ref.pcs t) = true

/-- Build the canonical RCLM artifact. -/
def BuildArtifact (N : Nat) : RCLMArtifact :=
  { N := N,
    ref := BuildRefSV N,
    allPacketsCheck := by
      intro t _ht
      exact canonical_packet_checks t }

/-- RCLM artifact theorem. -/
theorem artifact_theorem (N : Nat) (hN : 2 ≤ N) :
    InRCLMSVSeedLib (stateAt 0) N ∧
    (∀ t, t ≤ N → InRCLMSVDomain (stateAt t) N) := by
  constructor
  · exact build_refsv_entry N hN
  · intro t ht
    exact finite_checked_trajectory N t ht

/-- RCLM singleton finite-world reality containment inherits the RCP singleton result. -/
def SingletonRCLMRealityContained : Prop := RCP.SingletonRealityContained

theorem canonical_rclm_reality_containment : SingletonRCLMRealityContained := by
  exact RCP.canonical_reality_containment

end RCLM
end RcpRclmMech
