# Gate D foundation exit criteria

## Status vocabulary

Gate D uses three distinct status levels:

```text
started
  theorem objects or implementation exist but authoritative validation is incomplete

foundation complete
  the abstract learned-frontier theorem stack and declared finite reference are built,
  audited, documented, and validated at one exact source head

learned-language-model Gate D complete
  a real learned language-model package, task verifier, runtime checker refinement,
  self-hosted proposal path, promotion, and independent replay have closed under a
  separate executable contract
```

This document governs only **Gate D foundation complete**.

## A. Dependency and source boundary

- [x] Gate D is located in a new Formal Core v3 project.
- [x] Formal Core v2 is consumed as a local dependency rather than edited.
- [x] CI verifies that the v2 project tree equals the `main` tree.
- [x] Lean and mathlib resolve through the existing pinned v2 dependency graph.
- [x] The exact v3 `lake-manifest.json` is committed and unchanged by `lake update`.

## B. Learned object surface

- [x] Typed learned package state exists.
- [x] Typed learned package update exists.
- [x] Learned certificate packet exists.
- [x] The package state contains a finite capability frontier.
- [x] Generator, proposal, and package hash are explicit theorem objects.
- [x] Goal drift, resources, and selected information values have explicit budgets.
- [x] The trusted checker and trust anchor remain external to the learned package.

## C. One-step theorem

- [x] A learned checker refines an existing trusted base checker.
- [x] Base acceptance is reconstructed rather than asserted by the learned packet.
- [x] The learned checker proves protected-frontier certification and retention.
- [x] The learned checker proves strict frontier inclusion/cardinality growth.
- [x] The learned checker proves active-generator binding.
- [x] The learned checker proves proposal-to-candidate binding.
- [x] The learned checker proves active-package-hash binding.
- [x] The learned checker proves goal-drift, resource, and information bounds.
- [x] `learned_accepted_step_sound` returns complete inherited and Gate D obligations.

## D. Finite composition

- [x] Finite learned trajectories are defined.
- [x] Every accepted learned step has complete Gate D obligations.
- [x] The initial frontier is retained at every time.
- [x] Every accepted step has strict adjacent cardinal growth.
- [x] The theorem `card(F_0) + t ≤ card(F_t)` is proved.
- [x] The final theorem `card(F_0) + N ≤ card(F_N)` is proved.
- [x] Cumulative resource use is bounded.
- [x] Cumulative goal drift is bounded.
- [x] Cumulative selected information regression is bounded.
- [x] Existing protected-loss, endpoint-recovery, Lyapunov/motion, and trust results are inherited.

## E. Conditional infinite theorem

- [x] Frontier-expanding successor availability is an explicit proposition.
- [x] It is not inferred from learned-checker soundness.
- [x] An infinite learned trajectory is constructed under the availability premise.
- [x] Every transition in that trajectory strictly expands the frontier.
- [x] Documentation explicitly states that availability remains unproved generically.

## F. Concrete finite reference

- [x] The existing Gate B RCLM improvement state is used as predecessor.
- [x] The existing Gate B RCLM target state is used as successor.
- [x] The learned checker refines the existing Gate B RCLM checker.
- [x] Initial frontier is `{baseline}`.
- [x] Target frontier is `{baseline, frontierOne}`.
- [x] The proposal binds the actual Gate B RCLM improvement candidate.
- [x] Goal drift, resources, package hash, and information value are non-vacuously instantiated.
- [x] A one-step learned accepted-step theorem is proved.
- [x] A one-step cardinal-growth trajectory theorem is proved.

## G. Proof hygiene and audit

- [x] The project builds with pinned Lean.
- [x] Generated/build source contains no `sorry`, `sorryAx`, or `admit` token.
- [x] Project source declares no local `axiom`.
- [x] Public Gate D theorems are covered by a `#print axioms` audit.
- [x] The audit reports no `sorryAx`.
- [x] The reported axiom union is limited to the ordinary Lean/mathlib foundations already present in v2.
- [x] CI retains build, source-scan, axiom, manifest, and metadata artifacts.

## H. Documentation and machine-readable record

- [x] Scope record exists.
- [x] Theorem contract exists.
- [x] Assumption register exists.
- [x] Exit criteria exist.
- [x] Exact source-head validation record is closed.
- [x] Machine-readable Formal Core v3 manifest is committed and validated.
- [x] PR description and discussion bind the exact validated source head and artifact digest.

## I. Explicit nonclaims

Foundation closure continues to state that it does not establish:

```text
frontier-expanding successor availability
an LLM-scale RCLM
an independently verified open task universe
open-ended learned planning
generator self-modification
self-hosted multi-generation recursion
arbitrary learned-system refinement
strict broad usefulness at every step
full Paper I or Paper II semantic equivalence
general noncommuting quantum semantics
autonomous or unbounded RSI
```

## Closure rule

The Gate D formal foundation is closed at the validated source head recorded in
`GATE_D_VALIDATION.md`. The evidence-only branch head must pass the same pinned build,
manifest checks, source gates, and theorem audit before the PR is marked ready.
