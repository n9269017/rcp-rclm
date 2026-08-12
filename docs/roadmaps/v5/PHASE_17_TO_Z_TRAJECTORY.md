# Phase 17 → 18 → X → Y → Ω → Z trajectory

## Status and predecessor boundary

This document is normative roadmap material, not a report of completed work.

The predecessor boundary is the completed Phase 16 result:

```text
phase16_exit_closed = true
gate_e_closed       = false
next_phase          = 17
```

The remaining sequence is:

\[
17 \longrightarrow 18 \longrightarrow X \longrightarrow Y \longrightarrow \Omega \longrightarrow Z.
\]

The strongest scientific organization is to remove one previously fixed boundary at each stage.

| Phase | Boundary removed | Boundary still fixed |
|---|---|---|
| 17 | Predeclared trajectory horizon and host continuation decisions | Improvement language, verifier, diagonal semantics, atomic turn harness |
| 18 | Dependence on original learned workers and unclosed Gate E evidence | Improvement language, verifier, diagonal semantics, atomic turn harness |
| X | Commuting/diagonal semantic restriction | Root verifier, improvement language, atomic turn harness |
| Y | Fixed verification-facing automation and policy | Root proof kernel, root meta-gate, promotion authority |
| Ω | Fixed admissible update language and representation class | Immutable root constitution, serialized promotion |
| Z | External turn-by-turn operating harness | Immutable root constitution, atomic parent-linked promotion |

## Phase 17 — horizon-independent turn-based autonomous RSI

Phase 17 removes the known successful trajectory horizon while preserving the fixed Phase 16 improvement language, verifier, diagonal/classical semantics, and externally serialized transaction boundary.

The controller must not know:

- the number of future promotions;
- the successful update-family order;
- the future challenge sequence;
- the accepted candidate identity;
- the terminal package;
- the successful stopping time.

The turn protocol remains:

```text
freeze
→ realize
→ verify
→ promote or reject
→ commit ledger state
→ next turn
```

### Horizon noninterference

For histories that are identical through turn \(t\), with the same visible current resource state, future horizon information must not alter the present controller decision:

\[
H_{\le t}^{(1)}=H_{\le t}^{(2)}
\land
B_t^{(1)}=B_t^{(2)}
\Longrightarrow
\pi(H_{\le t}^{(1)},B_t^{(1)})
=
\pi(H_{\le t}^{(2)},B_t^{(2)}).
\]

A future target length, terminal hash, route table, future challenge sequence, or resource envelope may not covertly encode a successful schedule.

### Planned Phase 17 terminal claim

A successful future Phase 17 may support a domain-relative, proof-carrying, horizon-independent, turn-based autonomous RCLM self-improvement loop under an immutable external verification constitution.

It will not by itself close Gate E, establish asynchronous operation, or expand the admissible improvement language.

## Phase 18 — independent replay and adversarial Gate E closure

Phase 18 removes the original training, proposal, generator, planner, and model-serving workers. An independent reproducer must reconstruct from immutable evidence:

- hidden challenge bindings;
- objective selections;
- proposals and candidates;
- rejections and rollback;
- accepted transitions;
- capability and recursive-productivity frontiers;
- resource and information records;
- ledger mutations;
- promoted packages;
- exhaustion certificates.

Adversarial validation is required across high-level categories including information leakage, lineage substitution, resource-accounting evasion, evaluator or verifier substitution, replay dependence, hidden scheduling, and post-check mutation. Exact private attack payloads remain unpublished until the corresponding result is frozen.

### Planned Phase 18 terminal claim

Only Phase 18 may close Gate E for the fixed-language, fixed-verifier, diagonal/classical autonomous loop.

## Phase X — selected general noncommuting quantum-coherence semantics

Phase X removes the commuting/diagonal restriction while the root verifier and turn-based autonomy remain fixed.

The formal program targets selected finite-dimensional:

- complex density matrices;
- noncommuting state pairs;
- positivity and trace-one certification;
- Kraus or Choi representations of CPTP maps;
- matrix-log quantum relative entropy;
- support-aware data processing;
- recoverability and Petz or rotated-Petz witnesses;
- noncommuting coherence measures;
- certified numerical spectral bounds;
- RCLM-update-to-channel refinement.

A selected update \(u_t\) induces a certified channel:

\[
\rho_{t+1}=\Phi_{u_t}(\rho_t),
\qquad
\Phi_{u_t}\ \text{CPTP},
\]

with a declared non-loss/recovery relation such as:

\[
D(\rho_t\Vert\sigma_t)
-
D(\Phi_{u_t}(\rho_t)\Vert\Phi_{u_t}(\sigma_t))
\le \varepsilon_t,
\]

together with a certified recovery channel.

CPTP validity constrains the semantic transformation; it does not itself choose or optimize an architecture.

### Representation enlargement support

To prepare for later representation-space expansion, Phase X also targets selected certified embeddings:

\[
\iota_t:\mathcal H_t\hookrightarrow\mathcal H_{t+1},
\qquad
\iota_t^\dagger\iota_t=I.
\]

These embeddings permit conservative lifting of predecessor states into selected enlarged informational spaces.

## Phase Y — proof-carrying meta-verification and verifier succession

Phase Y distinguishes untrusted proof production from actual verifier-policy succession.

An active proof-producing verification layer may return:

\[
V_t(x)=(\mathrm{accept},\pi_x),
\]

but an immutable root must independently check:

\[
V_\star(\pi_x,x)=\mathrm{accept}.
\]

For conservative verifier succession, require:

\[
\operatorname{Accept}(V_{t+1})
\subseteq
\operatorname{Accept}(V_\star),
\]

or an explicitly proved equivalence on a declared domain.

The planned hierarchy is:

- untrusted proof scripts, lemmas, tactics, and proof search;
- proof-automation policy succession;
- proof-carrying checker extension;
- a dual-verifier shadow period in which all disagreement rejects.

The immutable root retains the proof kernel, cryptographic trust anchor, meta-verification rule, and atomic promotion authority. Phase Y makes verification capacity extensible, not self-authorizing.

## Phase Ω — root-certified recursive improvement-space expansion

Phase Ω removes the fixed admissible improvement-language and representation-class restriction.

Let:

\[
M_t\in\mathcal R_t
\]

denote the active package and its admissible representation class;

\[
\mathcal L_t
\]

the active typed improvement language; and

\[
\mathcal U_t^B
\]

the independently certifiable transformations executable within the same normalized resource class \(B\).

The public headline targets are:

\[
\mathcal L_t\subsetneq\mathcal L_{t+1},
\]

\[
\mathcal R_t\subsetneq\mathcal R_{t+1},
\]

and, most importantly,

\[
\mathcal U_t^B\subsetneq\mathcal U_{t+1}^B.
\]

The comparison is resource-normalized: expansion cannot be claimed merely by granting the successor a larger budget.

### Abstract extension contract

A successor-generated extension packet publicly consists only of the following abstract categories:

\[
\Xi_t=
(
\text{syntax and types},
\text{semantics},
\text{executor},
\text{canonicalization},
\text{cost},
\text{migration},
\text{certificate}
).
\]

The exact schema, byte encoding, compiler ABI, proof-object representation, migration algorithm, activation transaction, and private verifier dispatch remain outside this public roadmap.

### Genuine novelty

A new name or predeclared empty enum slot does not establish expansion. The future closure must prove that the predecessor language cannot represent the new transformation within the same declared resource and certification class.

Suitable proof forms may include finite normal-form enumeration, decidable type separation, a predecessor-language semantic invariant, or a certified lower bound.

### Three-generation recursive meta-productivity

The decisive target is:

\[
\mathcal U_0^B
\subsetneq
\mathcal U_1^B
\subsetneq
\mathcal U_2^B.
\]

The first acquired extension must causally help generate the second. A future closure therefore requires an ablation demonstrating that the first successor can produce the second extension with the acquired extension active, but cannot do so when that acquired extension is removed, and that the original predecessor cannot do so.

This is stronger than adding a single designer-provided primitive: a successor-acquired extension becomes productive at the meta-level.

## Phase Z — thermodynamically resource-bounded asynchronous RCLM RSI

Phase Z removes the external turn-by-turn operating harness.

Search may be asynchronous, but promotion remains singular and atomic:

```text
many asynchronous untrusted search workers
                    ↓
immutable candidate or extension snapshot
                    ↓
quiescence and freeze barrier
                    ↓
isolated root-checked verification
                    ↓
one serialized atomic parent-linked promotion
                    ↓
new active package
```

The runtime controls objective selection, search launches, candidate budgets, archive lineages, candidate freezing, verification submission, rejection response, and continuation decisions.

### Resource-normalized growth

Let \(T_B(t)\) denote cumulative declared resource cost. Because frontier cardinality is step-valued, the correct finite-event target is:

\[
|F_{\tau_{k+1}}|>|F_{\tau_k}|,
\]

with:

\[
T_B(\tau_{k+1})-T_B(\tau_k)<\infty.
\]

A finite experiment cannot establish an actual infinite-time limit. It may demonstrate positive resource-normalized growth over a declared run, no frontier regression, bounded inter-promotion resource costs, and a conditional theorem for indefinite continuation.

### Planned Phase Z terminal claim

A successful future Phase Z may support a standalone, asynchronous, thermodynamically resource-bounded RCLM process operating under immutable root verification and atomic promotion while its admissible resource-bounded improvement language and representation class may themselves undergo proof-carrying conservative extension.

## Dependency rationale

The order is deliberate:

1. prove horizon-independent autonomous search before changing semantic mathematics;
2. independently reconstruct and adversarially close that autonomy;
3. generalize the semantics while the verifier remains fixed;
4. make verification-facing machinery proof-carryingly extensible;
5. expand the admissible improvement language and representation class;
6. remove the external operating harness only after those boundaries are separately isolated.

## Conditional final destination

A successful complete program may support:

> A domain-relative, root-constituted, proof-carrying, thermodynamically resource-bounded autonomous RCLM recursive self-improvement architecture under uncertainty, capable of horizon-independent and asynchronous self-modification, root-certified conservative extension of its typed representation and admissible resource-bounded improvement languages, recursive multi-generation use of acquired extension capabilities, and independently replayed empirical capability gains across post-freeze hidden domains.

The claim remains conditional on root-verifier soundness, fresh challenges, successor and extension existence, nonterminal domains, and fair resources.

It does not establish universal successor or extension availability, arbitrary-domain RSI, expansion beyond all computable transformations, empirically infinite execution, an infallible generator, an unrestricted mutable trust root, universal goal preservation, AGI, or a claim that every language-model update is literally a quantum physical process.
