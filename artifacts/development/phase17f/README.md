# Phase 17F development evidence

Assistant results use a reconstructed dependency checkout. Twelve existing Phase17
module blob identities and 72 formal-root file pins were checked. All new source
hashes and exact limitations are in assistant-validation.json. The candidate is the
existing deliberate known-answer fixture, not a live improvement.

Thirty-six new tests, 35 package regressions and 33 installer checks passed.
Mocked tool-control and installer fixtures are not Lean proofs. The new real Lean
request was blocked before any compiler execution because Mathlib is absent here.
Actual preparation succeeded; generated sources remain unverified by Lean here.

Operator evidence is retained separately under op-<tested-source>. Only actual
formal gate success permits installer advancement. All complete-root, promotion,
phase-closure, EGC and live-improvement claims remain false.
