# Phase 17B — historical bootstrap and initial objective selection

Status: development implementation. Phase 17 and executable Gate E remain open;
EGC-0 is not started. This component creates no successor, promotion, release or DOI.
The source is public; evaluator separation is a runtime information boundary,
not a return to private-source development.

## Inputs and pinned identity

The loader accepts the exact following archive bytes. It does not download,
regenerate, extract, execute, or trust a replacement supplied by a candidate.

| Archive | SHA-256 |
| --- | --- |
| Phase 16 full capture, run 31153935872 | `7337079801916ecccce0e3a292d5379cea17b571acc6f31b9b38cb21f9f63dde` |
| Phase 16 final closure, same run | `ce7f1de4654306d5280970dfc92453a8743cf1e02fe98963f1e940c0077582f9` |
| Phase 15 M9 bundle, run 30969783629 | `56003f95ded054be21dd3f743c2145fdf6e92543af28bb350f64ec8f4fee00b5` |

The closure and M9 bundle were already in the public repository. This increment
also retains the full historical capture under `artifacts/development/phase17b/`
so a fresh checkout does not require an expired Actions download. It contains
completed Phase 16 campaign records, including historical challenge data, not
future Phase 17/EGC hidden answers. Missing or changed bytes reject rather than
falling back to the small serialization fixture. Only selected members of the
approximately one-gigabyte expanded M9 archive are read, in memory; the archive
is not unpacked to disk. Paths, duplicate members, symlinks, encryption, and
member sizes are checked before reading selected data.

Original Phase 16 source: `b870b3cff8ae5c7fe5e26c2308279bea357bc99c`.
The final closure's logical report hash is
`f5c4943647c3a54ab4e1686a45c64926844fb97a99f7eafe054679a34ba896ee`.
The capture's intermediate exit flags are NOT used as final closure authority.
The separate final closure must be accepted, Phase 16 closed, Gate E open,
and next phase 17. Source, verifier and diagonal-semantics identities are fixed.

Here, "authenticated" means byte/content identity relative to explicit trusted
historical pins and retained closure linkage. No new signature, external witness,
fresh theorem proof, or trusted execution environment is asserted. Possession of
hash-matching public fixture bytes is not evidence that an archive-ingestion run
occurred. The command entry point records its actual ingestion execution.

## Selection and preserved inventory

The bootstrap choice is the minimum completed ladder rung, then UTF-8 seed,
then UTF-8 challenge stream. The chosen campaign is the eight-transition
`phase16-seed-alpha` / `dynamic-stream-a` history. This is a fixed engineering
bootstrap selection, not a claim that the package is the empirically best model.
No EGC task or score is read.

- selected campaign: `e4e68386d2896d843bd741c0de93897ceeda7eecef503ec4a396b6d235dcb170`
- terminal state: `7d2b823c05e4e4cef7566a89d3d440dba60a6417c6a3401f1248e59f89e91567`
- active package: `9a519919e2289cb5a568039b0d36f07c49570d07ccb92fca22ace408e4367c30`

The catalog retains all 16 scaling-campaign terminal identities plus the separate
100-promotion stretch terminal: 17 entries, covering the historical 580 accepted
promotions and 3,752 rejected attempts. Historical campaign lengths are evidence,
not a future controller horizon. The catalog is not an input to the objective
ranking policy. Keeping this inventory does not freeze or run an EGC evaluation.

For the chosen lineage the loader reconstructs each predecessor/successor state,
component generation, accepted program identity, installed-program set, archive
hash chain, and capability/recursive-frontier progression. It recomputes semantic
package hashes with the inherited Phase 16 domain. Evaluation records are checked
for their retained hashes and bindings, not independently re-executed as new
proofs. Other campaigns' report/terminal hashes are inventoried, not replayed.

## Initial objective policy

The M9 semantic package, planner manifest, and 65,536-byte int16 tensor are pinned.
The tensor has 32,768 entries and 84 nonzero values. The new selector reads those
actual inherited bytes and computes a declared integer projection heuristic over
current package/state/frontiers, current turn, family and public nonce. It does
not train a model or establish that the heuristic is a learned improvement.

All eight existing families are ranked. The selected family describes the next
objective; it is not a target winning program, does not choose a hidden answer,
and does not narrow or extend the fixed 32-program mutation grammar. The API has
no future promotion target, successful route, terminal model, future challenge,
evaluator seed, or EGC-score input.

The verifier recomputes the policy rather than trusting a serialized winner or
score. The freeze receipt binds objective, predecessor, package, trust root,
current turn and nonce. It explicitly sets `challenge_bound=false` and
`promotion_authorized=false`. A deterministic receipt is not a clock-order proof
or an operating-system isolation boundary. The future evaluator must issue a
fresh challenge AFTER this freeze; hostile nonce selection and evaluator
isolation are not solved by this data structure alone.

This policy applies to the pinned historical bootstrap state. Supporting newly
promoted states, cross-turn objective-policy evolution, and resource-budgeted
continuation are separate integration work.

## Local commands

From a complete committed checkout (Python 3.11+, ordinary Git):

```sh
python scripts/run_phase17_tests.py
python scripts/run_phase17_bootstrap_tests.py
python scripts/run_phase17_bootstrap.py --output /outside/repo/new-phase17b-run
```

All input archives default to their retained repository paths; explicit overrides
still must match the same fixed hashes. The output directory must not already
exist and must be outside the checkout.
The last command uses the actual Phase 16 `ModelState` constructor and checks the
round-trip state hash. It writes bootstrap/catalog/objective/freeze/execution
records and a SHA-256 manifest. An explicit `--public-nonce-hash` reproduces a
prior objective; omitting it generates a current random public nonce.

The ten real-archive tests exercise ingestion, fixture equivalence, initial
objective freeze, and rehashed lineage-tampering rejection. They do not invoke
Lean, training workers, the original full campaign generator, or Phase 18 replay.

## Evidence and remaining work

The retained assistant validation report separates 34 new unit tests, 26
controller regressions, and ten tests using real archived inputs. Its workspace
is a historical dependency checkout with current Phase 17 overlay, not the full
current public tree. The complete 67-test suite and normal Phase 16 constructor
must run on the operator's full checkout; no Windows/macOS result is invented.
The provided application kit records these actual future runs before any push.

The remaining substantive boundary is fresh post-freeze challenge generation
and separation, actual realization/evaluation, full-frontier recertification,
pinned Lean/root verification, atomic promotion/rollback, durable cross-turn
ledgering, complete resource accounting and horizon-independent campaigns.
No phase-closure or promotion authority is delegated to this loader or selector.
