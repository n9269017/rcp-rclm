# Phase 17U — captured planner bytes and producer scores

This increment starts from the completed Phase 17T evidence head
`db13c5fbaba20151d5d313885cb4e663859f45c1`. Keep PR #68 draft and unmerged.
Phase 17, Gate E, active promotion, and EGC-0 remain open.

## The missing premise

K checks deterministic proposal conformance against a complete ranking table.
Q incorporates that producer context into its concrete finite-observation
`LearnedAcceptedStep`. R, S, and T connect protected execution to captured tensor,
routing, and JSON inputs. Those results do not formally construct the producer's
ranking table from the inherited planner tensor: `ProposalProvenance.lean`
explicitly leaves score-table construction external.

U supplies a selected numerical interpretation of that tensor and binds the
computed rows to the actual imported `Phase17Provenance.selectedContext.rows`.
This is the existing fixed external controller with a package-bound inherited
ranking projection. It is not a newly learned or self-hosted neural proposer.

## Complete input domain

The preparation reopens the anchored T evidence and reconstructs the same
historical inactive candidate and predecessor. It retains the exact T packet,
its candidate/parent/transcript bindings, and the original current public view.
There are no new workers, live challenges, seeds, candidate searches, or promoted
packages.

| Input | Selected extent |
| --- | --- |
| Planner tensor | Complete `base/model/phase15_planner/weights.i16le.bin` from both packages |
| Tensor shape | 65,536 bytes; 32,768 signed little-endian 16-bit words per package |
| Nonzero projection | 129 nonzero bytes and all 84 nonzero words per package |
| Ranking alternatives | All 32 programs from the fixed inherited grammar |
| Score terms | 84 terms for each of the 32 alternatives |
| Tie values | Five public rejection-count tie values for every alternative |
| Producer trace | Eight rejected proposals followed by the ninth passing proposal |

The sparse byte representation includes its total length and complete nonzero
support. Python checks an exact round trip against every captured byte. Lean
checks canonical support and the complete signed-word projection, including
indices that decode to zero. A collection of 84 unchecked handpicked weights
does not satisfy that projection.

The two package images are captured separately. Transport between them requires
equality of their complete byte representations; a common digest string alone
is not a Lean proof of image equality.

## Declared numerical interpretation

For ordered nonzero planner words `(i_j, w_j)`, program family index `f`, variant
`v`, generation `g`, family count `c_f`, and the declared lowercase hexadecimal
feature string `H`, the base score is

```text
20,000 - 521 * c_f
  + sum_j w_j * ((hex(H[(i_j + 11*j) mod 64])
                   + 3*f + 5*v + g + j) mod 9 - 4).
```

Byte decoding uses explicit two's-complement arithmetic. Feature digits, the
first sixteen digits of each tie digest, and the freeze-derived enumeration
offset are interpreted in the Lean reference semantics. Every resulting row
must equal Q's imported row, including program identity, family, signed base
score, and all five tie values. The offset must equal Q's actual context offset.

The existing producer rule adds `797 * prior_family_rejections` to each base
score for the first four choices. It resolves ties by the public tie value and
the canonical program order. Later choices use the fixed stride-17 permutation
of the 32 alternatives. U composes its reconstructed context with the existing
checked proposal trace and Q's selected finite-model accepted step. It does not
accept a new caller-supplied winner or success flag.

## Public hashes and metadata remain external

The packet retains the complete seed, feature, tie, and freeze hash preimages.
Python independently recomputes their canonical SHA-256 digests, using the exact
existing `RCPRCLM-CANONICAL-JSON-V2\0` domain prefix, and compares the
resulting scores with the unchanged production ranking implementation and the
imported provenance table. This catches substitutions relative to the retained
anchors, but U does not formalize SHA-256 or the canonical hash-preimage encoder.

Lean's new claim starts with the supplied feature/tie/freeze digest strings and
the supplied program metadata. Their lowercase hexadecimal interpretation and
numerical use are checked; their cryptographic origin and the parsing of program
descriptors into family/variant/generation/count fields remain external premises.
In particular, the installed-program registry JSON is a separate remaining
projection obligation, not silently covered by T's protected routing documents.

Physical byte capture, operating-system behavior, digest authenticity, Python
execution, temporal secrecy, and the pinned foundation import-cache assumption
remain external. The finite planner interpretation is not a proof of arbitrary
planner networks, arbitrary transformer execution, general goal interpretation,
or a physical autonomous successor transition.

## Checking and retained evidence

The gate compiles the exact Q, R, S, and T dependency sources into a fresh private
directory for the U run. It checks that each direct import resolves to the module
compiled in that directory and records source and artifact hashes. Historical
success reports are input anchors, not substitutes for these compilations.

The new positive certificate is checked with the pinned Lean 4.31.0 kernel. Its
named theorem audits allow only the existing approved logical axioms
`propext`, `Classical.choice`, and `Quot.sound`. Separate semantic mutations must
be rejected by actual compiler false-proposition diagnostics. A timeout, killed
process, missing import, stuck decision instance, unrelated elaboration error,
or failed false-decision witness cannot satisfy a negative control.

The new inventory contains fifteen named theorem audits and twelve separate
negative certificates. The latter change a planner byte, swap byte order, omit
a nonzero word, inject a word into the zero complement, supply an invalid byte,
change a feature digest, change a family count, change a generation, change a
tie digest, change the freeze offset input, introduce a non-hexadecimal digest
suffix, or substitute a row's program key. The positive projection is split
into 128 checked blocks of 256 words; a generic coverage theorem combines them
without discarding any image index.

The 32 numerical rows are also checked separately. A generic `List.Forall₂`
composition proof reconstructs the complete ordered score and tie table against
Q's imported rows. Literal captured-data definitions are `noncomputable` to omit
unused native code generation; their transparent bodies are still reduced by
Lean's kernel proofs. The renderer rejects native decision shortcuts.

The family-count and generation mutations specifically violate the declared
`generation = familyCount + 1` metadata invariant. They do not independently
isolate every numerical effect of an otherwise valid metadata change.

The Python tests include independent numerical checks, malformed and substituted
packet attacks, and strict compiler-record validation. Synthetic command logs
in those unit tests are identified as controlled fixtures and are not Lean proof
evidence. The application additionally requires a complete actual gate and a
fresh reconstruction of the retained packet and generated proof inputs before
advancing its isolated checkout.

The code and evidence commits remain separate. The delivered application helper
requires the completed T baseline, verifies its sealed additive payload, uses a
new short-path workspace, and only advances/pushes the development branch after
all required checks succeed. It does not merge PR #68 or touch main, the
bootstrap branch, an active model store, release assets, or DOIs.

## Scoped results and broader boundaries

A successful actual U gate may set only these new scoped results:

```text
planner_tensor_projection_checked = true
producer_scores_from_bytes_checked = true
```

These mean the selected numerical reference interpretation and its binding to
Q's producer context were checked. They do not attest that a historical process
executed, that the generator acquired new capability, or that a live successor
was authorized. All 24 broader claim flags retain `false`, including
`root_transition_verified`, `physical_projection_formally_verified`,
`physical_execution_attested`, `full_learned_step_instantiated`,
`full_autonomous_step_instantiated`, `recursive_productivity_recertified`,
`complete_resource_accounting`, `promotion_performed`, `phase17_exit_closed`,
`gate_e_closed`, `cross_platform_validation`, and `phase18_independent_replay`.

The historical reference-work tariff remains historical evidence. U's setup,
archive reconstruction, byte capture, parsing/hashing, numerical preparation,
proof checking, CPU/accelerator use, memory, storage, energy, and future active
promotion/rollback costs are unmeasured in the complete-pipeline sense. They are
not zero and do not establish comprehensive resource authority or containment.

## Reproduction

```text
python scripts/run_phase17_planner_refinement_tests.py
python scripts/run_phase17_planner_refinement_gate.py --test-fixture --require-lean --lean-workspace <prepared-formal-root> --output <new-external-output>
```

Preparation-only mode supports inspection and cannot satisfy the installer.
Retain the exact tested source commit for `--verify-only` reconstruction. A local
Linux application result and a later Windows operator result describe this
selected increment, not broader platform/campaign closure or Phase 18 replay.
