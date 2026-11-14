# Phase 17W — producer hash inputs and seeded grammar parameters

This increment starts from completed Phase 17V at
`62338d94237f2b913bb2bd6ccd7367388678b92b`. Keep PR #68 draft and
unmerged. Phase 17, Gate E, active promotion, and EGC-0 remain open.

## The remaining computation premise

V interprets the selected complete registry and descriptor JSON images and
binds their typed values to U's actual producer row inputs and Q's actual
installed programs and selected update. It does not establish how the fixed
grammar constructed the descriptor parameters or how the producer constructed
the canonical inputs to its public hash calls.

W supplies those selected computations. From the declared current view,
inherited family counts, and supplied grammar seed digests, it derives all
32 candidate descriptors and requires equality with the descriptors and images
actually imported from V. It independently constructs the complete canonical
JSON and domain-prefixed bytes for the selected producer hash calls. Each
record retains its supplied digest, and the relevant digests are bound to the
actual imported U inputs.

The Lean claim ends at construction of these bytes and interpretation of the
supplied digest text. SHA-256 evaluation and authenticity of its inputs and
outputs remain external. A correct preimage construction does not by itself
prove that its supplied digest is the SHA-256 output for those bytes.

## Seed interpretation and complete grammar construction

For a lowercase 64-character hexadecimal seed digest and a nonnegative offset,
the declared parameter computation is:

```text
start = (2 * offset) mod 56
word  = the natural number represented by seed[start : start + 8]
value = word mod 33 - 16
```

The first parameter uses offset `family_index + variant`; the second uses
`family_index + variant + 7`. The result lies between -16 and 16 inclusive.
The descriptor's remaining fields come from the declared family/operation
mapping, variant, inherited count plus one, turn index, and public nonce.

All eight families and all four variants are required. The resulting 32
descriptors use the same canonical program-key order as the imported producer.
The inherited counts come from V's selected registry projection; the inactive
staged candidate is not counted as an inherited program.

The original fixed grammar remains fixed. This selected derivation does not
establish a learned grammar, an expanded improvement language, or a new
proposal campaign.

## Canonical producer hash inputs

The independent reference constructs a bounded canonical ASCII JSON encoding:
ordered object keys, exact declared field sets, decimal integers, literal
Boolean/null values, ordered arrays, and printable strings requiring no JSON
escapes. Selected values must satisfy this profile. The declared public hash
domain prefix, including its terminating zero byte, is part of every complete
preimage.

| Selected hash input | Count |
| --- | ---: |
| Grammar seed context | 32 |
| Complete candidate program descriptor | 32 |
| Planner feature context | 32 |
| Rejection-count tie context, five per alternative | 160 |
| Current-view ranking seed | 1 |
| Complete search freeze | 1 |
| **Total** | **258** |

The selected domain-prefixed images total 98,349 bytes. These are deterministic
reconstructions from the retained historical inputs. They are not original
worker byte captures and do not demonstrate a fresh live search. The packet
preserves the exact V packet and its retained execution/source/operator anchors.

The grammar-seed context binds the selected active package, turn, family,
variant, generation, and public nonce. Program images contain the complete
derived descriptors. Feature and tie inputs bind the actual program identity,
current public context, and their declared policy fields; all five rejection
counts are checked for each program. The complete search-freeze input includes
the current view and all 32 ordered ranked candidates with U's actual scores.

The Python preparation also recomputes public hashes to detect substitutions
and check the retained fixture. That Python computation is explicitly outside
the new Lean SHA-256 claim, which remains unestablished. The formal certificate
does not replace a missing hash proof with a caller-supplied success Boolean.

## Formal composition and validation

The reference derivation must agree with the actual imported V descriptors and
images, and its constructed producer inputs must bind the actual imported U
row digests, scores, and search-freeze data. Those equalities compose with V's
metadata interpretation, U's numerical producer table, and Q's selected
finite-observation acceptance. R, S, and T retain their separate tensor,
routing, and captured-JSON meanings.

The current-view fields already represented upstream use the actual imported
V public context and Q producer binding, including the predecessor-state and
challenge-commitment identifiers. The planner digest is read from Q's actual
planner-file reference, with its exact path, 65,536-byte size, and before/after
agreement checked. The ranking-seed digest remains a supplied selected packet
input because earlier Lean modules do not export a typed constant for that
string. W checks its placement in the complete preimages and binds the resulting
declared row digests to U through V. Neither importing a recorded file digest
nor constructing its hash input establishes its cryptographic authenticity.

The W gate freshly compiles Q, R, S, T, U, and V into one new import directory.
Each import resolution must identify the artifact produced during that run.
Previously saved compiler success cannot substitute for those compilations.
The pinned foundation import-cache assumption remains separately recorded.

Generated sources use Lean's kernel decision path. Named theorem audits allow
only `propext`, `Classical.choice`, and `Quot.sound`. Placeholder proofs, new
axioms, unsafe/partial definitions, and native-decision shortcuts remain
prohibited. The complete positive certificate must pass, and each deliberate
negative control must produce the designated false-proposition rejection.
Timeouts, process kills, missing imports, stuck reductions, and unrelated
compiler errors cannot count as successful rejection.

The 32 row certificates each check their complete input and parameter
conditions. Generic list projection theorems then compose their descriptor,
image, and public-row equalities into the selected aggregate result. This
composition retains every row condition and the same exported propositions;
it avoids repeating complete byte-list evaluations during aggregation.

The Python suite checks independent canonical encoding, seed windows and
parameter arithmetic, full input inventory and imported-value bindings,
malformed or substituted inputs, and strict saved-command validation. Its
controlled command fixtures are identified as fixtures and are not actual
Lean results.

The application starts from a clean checkout of completed V, verifies the
sealed additive payload, runs the W tests and pinned Lean gate, and reconstructs
the retained inputs and generated sources. It records implementation and
execution evidence in separate commits. Only successful completion permits
fast-forwarding the existing development checkout; an optional ordinary push
publishes that result. Earlier worker campaigns are not repeated.

## Claim boundaries

Successful W verification may set:

```text
grammar_parameters_from_seed_checked = true
producer_hash_preimages_checked      = true
```

These flags mean selected seed-text interpretation, descriptor construction,
and canonical hash-input construction in the declared Lean reference semantics.
General grammar derivation remains open, and even the selected end-to-end
hash-based procedure still depends on externally supplied SHA-256 results.

Physical byte capture and filesystem behavior, cryptographic digest origin and
authenticity, SHA-256 evaluation, Python/physical execution, and the pinned
foundation import cache remain explicit premises. General canonical-JSON
equivalence outside this bounded ASCII profile, arbitrary program registries,
planners, or transformers, and temporal secrecy of public/hidden contexts are
not established.

All twenty-four broader claim flags remain false. Full physical refinement and
attestation, full learned/autonomous-step instantiation, full goal/information
semantics, authenticated succession, frontier/productivity recertification,
complete resource accounting and authority, containment, active promotion and
rollback, hosted CI, broader platform/campaign validation, Phase 18 replay,
Phase 17 closure, and Gate E closure remain open. No live capability gain or
EGC-0 result is claimed. Unmeasured preparation, hashing, proof checking,
CPU/accelerator, memory, storage, and energy costs are not treated as zero.

```text
python scripts/run_phase17_producer_preimages_tests.py
python scripts/run_phase17_producer_preimages_gate.py --test-fixture --require-lean --lean-workspace <prepared-formal-root> --output <new-external-output>
```

Preparation-only output is useful for inspection and cannot satisfy the final
application helper. Selected Linux and Windows validation, when completed,
does not close the broader platform or campaign obligations.
