# Phase 17K — package-bound deterministic producer conformance

Development increment after `dac5bc9c6ab41e8a18a58b45cc6c8bb3f047288a`.
Keep PR #68 draft and unmerged. This is not full-root acceptance or phase closure.

## Producer provenance is stronger than evaluator validity

The earlier `tests_phase17d/fixtures/known_candidate_pass.json` is deliberately
an isolated known-answer candidate fixture. Its evaluator transcript is valid,
but its first submitted program is not the current controller's first choice.
Earlier candidate/proof tests did not claim an autonomous producer campaign.
Phase17K preserves that fixture and requires its rejection by the new ordered
producer-conformance verifier. No earlier source or evidence is rewritten.

The new `tests_phase17k/fixtures/ordered_known_challenge.json` uses the SAME already
known challenge/entropy and public nonce. It executes the actual controller's
choices, preserving eight rejected proposals before the ninth passes. There is
no seed search, winner filtering, fresh hidden evaluation, training, or promotion.
The final bounded program equals the older fixture's selected program, but the
new transcript and therefore physical candidate-package identity are different.
Earlier candidate capability proof reports are NOT reassigned to this new package.

## Exactly which producer is checked

The producer is a fixed external controller with a package-bound inherited
ranking projection, not self-hosted neural program synthesis. The verifier checks
eight reviewed source identities, independently regenerates the 32-program
bounded grammar, and reads the actual 32,768 signed 16-bit planner parameters
from the physical predecessor (84 nonzero). It recomputes every ranking score
and relevant tie-break using those weights, independently of the production
ranking implementation, and compares both the production and reference choices.

The first four proposals use rejection-conditioned ranking. Remaining proposals
use the unchanged complete stride-17 permutation. For each freeze/evaluation
pair, selection is computed before the current evaluation is consumed. Only the
present public control view and prior independently checked rejection outcomes
enter selection; future entropy, targets, winner, and terminal package are not
proposer inputs. The verifier may use the sealed reveal to validate evaluator
receipts separately. That is not proof of physical temporal secrecy or hostile
same-user isolation.

The verifier recomputes the objective/freeze, active semantic identity, physical
package binding, candidate artifact, evaluator receipt, prefix hash, decision
hash and checkpoint, rather than accepting a supplied success report. The final
physical program file must equal the frozen descriptor's realization. Duplicate,
reordered, skipped, stale or substituted choices reject, including when an outer
record is rehashed. Exhaustion, partial-resource stop, external stop and safety
halt remain distinct and cannot create a selected passing proposal certificate.

## Formal connection to the existing root

`ProposalProvenance.lean` defines the complete 32-row selection table, the same
four-ranked-then-fair selection rule, and a full rejection prefix. The selected
certificate kernel-reduces the entire nine-step choice sequence, requires no
repetitions, binds parent/generator/context/transcript/program/candidate identities,
and checks that the verdict sequence has eight rejections followed by one pass.

An adapter supplies these actual `Learned.FrontierKernel` fields:

- `activeGenerator` and `generatorBound`;
- `activePackageHash` and `packageHashBound`;
- `proposalProducedBy` and `proposalBindsCandidate`.

The remaining compatible kernel and physical observation projections are still
parameters. In particular the predicate denotes deterministic conformance to the
declared producer, NOT cryptographic attestation that a particular historical
process ran. The current mapping does not promote an external controller into a
self-hosted learned generator by renaming it. No complete `LearnedAcceptedStep`
or `AutonomousAcceptedStep` is constructed.

The gate requires eight exact named theorem-axiom audits and three separate
compiler rejections: omitted rejected-prefix history, wrong parent, wrong output
program. All selected records use single-line Lean field layout. A timeout,
missing compiler, changed source, unapproved axiom, unexpected output, or passing
negative certificate cannot satisfy installation. Preparation mode exists for
inspection only and cannot satisfy the installer.

## Trust boundary and remaining work

Python hashing/canonical parsing, physical-byte measurement, extraction of Lean
literals, arithmetic-score/tie computation and the evaluator replay remain
externally checked trusted bindings, not universally formally verified Python.
Lean checks the selected finite trace from the complete supplied table and the
root-field adapter. Trusted toolchain and import-cache assumptions remain.

Eight-source pinning and package identity are integrity relative to reviewed
anchors, not independent attestation or a successor-acquired generator capability.
The code has no active-store mutation or promotion API. The full-root assessment
remains `blocked_missing_semantic_witnesses`; goal/information semantics, concrete
base and learned refinement, recursive productivity, complete resource enforcement,
durable challenge/history consumption, atomic active promotion/rollback and
cross-turn campaigns remain outstanding. No historical recursive task closes.

Always retain false: root_transition_verified, recursive_productivity_recertified,
full_frontier_recertified, full_learned_semantic_refinement,
neural_decoder_formally_verified, complete_resource_accounting,
promotion_authorized, promotion_performed, live_capability_gain_demonstrated,
phase17_exit_closed, gate_e_closed, egc0_started.

## Reproduction

`scripts/run_phase17_provenance_tests.py` requires 63 tests.
`scripts/run_phase17_provenance_regressions.py` runs the unchanged 33 controller
and Phase16-adapter tests. This is not a rerun of historical proof campaigns.

`run_phase17_provenance_gate.py --test-fixture --require-lean --lean-workspace
<prepared formal-root> --output <new external directory>` recomputes the physical
trace and requires real pinned Lean. No tool/dependency installation is performed.

The application kit uses a separate short-path checkout, canonical Git-blob
checksums, literal NUL-delimited staging and byte-preserved evidence. It advances
and pushes normally only after success; no reset, amend, force-push, main merge,
release/DOI modification or hosted-CI claim. The only preexisting document change
corrects Phase17J's stale reproduction count from 62 to 70. Prior evidence remains
untouched. Local Linux/Windows tests do not establish independent replay or full
platform coverage.
