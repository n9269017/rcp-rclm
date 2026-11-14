# Phase 17X — selected producer SHA-256 evaluation

This increment starts from completed Phase 17W at
`812510fa3e68212d8b0551c6facd23a6f3a90119`. Keep PR #68 draft and
unmerged. Phase 17, Gate E, active promotion, and EGC-0 remain open.
The suffix X identifies this Phase 17 increment; the roadmap's later
noncommuting-semantics Phase X remains a separate phase.

## The remaining computation premise

W constructs the complete selected canonical producer hash inputs and derives
fixed-grammar parameters from supplied seed digests. It binds those inputs and
parameters to V's decoded descriptors, U's producer rows, and Q's selected
finite-model accepted step. W deliberately leaves the equality between each
input's SHA-256 output and its supplied digest external.

X supplies that selected equality. Its certificate evaluates the declared
SHA-256 reference on every complete domain-prefixed input from W and requires
the result to equal that same imported record's digest. The domain separator,
its terminating zero byte, and every canonical JSON byte participate in the
hash. No digest supplied by Python or recorded in an earlier successful run
can substitute for the Lean calculation.

The result binds all selected grammar seeds, program identities, planner
feature digests, rejection-count tie digests, current-view ranking seed, and
the complete search-freeze digest. It does not establish the provenance or
authenticity of physical files, package identifiers, public nonces, challenge
commitments, or other contextual digest strings occurring inside these inputs.

## Declared SHA-256 reference

The algorithm follows the word operations, constants, preprocessing, initial
state, and compression equations in
[NIST FIPS 180-4](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf),
sections 4.1.2, 4.2.2, 5.1.1, 5.2.1, 5.3.3, and 6.2.2.

The declared input is a finite list of byte values in the range 0 through 255,
with a bit length representable in 64 bits. Preprocessing appends the one bit,
the required zero padding, and the complete big-endian 64-bit original bit
length. It parses the padded image into complete 64-byte blocks and each block
into sixteen big-endian 32-bit words.

For each block the reference constructs the complete 64-word schedule and
executes all 64 SHA-256 rounds. It uses the eight specified initial words,
all 64 fixed round constants, the specified rotations and logical shifts,
choice and majority functions, and addition modulo 2^32. Feed-forward adds the
incoming state to the final working state modulo 2^32. The final eight words
are encoded as the complete 64-character lowercase hexadecimal digest.

This is a selected evaluation theorem for the explicit Lean reference. It is
not NIST implementation validation, a proof of collision resistance, a
cryptographic origin attestation, or a theorem about every external SHA-256
implementation. The independent Python implementation and standard test vectors
provide additional implementation checks; they do not replace the Lean proof.

## Complete selected inventory

The original W packet and all its historical claim fields are retained
unchanged. X adds its own packet, execution records, and scoped results.

| Input category | Images | Complete input bytes | Padded 64-byte block occurrences |
| --- | ---: | ---: | ---: |
| Grammar-seed contexts | 32 | 10,356 | 192 |
| Complete program descriptors | 32 | 10,555 | 192 |
| Planner feature contexts | 32 | 22,427 | 374 |
| Tie contexts | 160 | 49,120 | 800 |
| Current-view ranking seed | 1 | 644 | 11 |
| Complete ordered search freeze | 1 | 5,247 | 83 |
| **Total** | **258** | **98,349** | **1,652** |

The block count includes SHA-256 padding. The 98,349 input bytes include each
complete domain prefix and terminating zero byte. These inputs are the same
deterministic reconstructions from the retained historical fixture used by W;
they are not new physical worker captures. The fixed grammar and selected
historical fixture retain their original provenance.

## Formal composition and evidence

The certificate binds its complete input inventory to actual imported W
records. Independently checked compression steps compose from the fixed initial
state through every padded block to the final digest. Intermediate values are
untrusted witnesses: each required state transition is checked by Lean and the
chain theorem connects them to the complete reference computation. Sharing an
identical checked transition between input chains does not omit a block from
either chain.

The selected chains contain 1,652 block occurrences, with 105,728 compression
round occurrences. Identical incoming-state and complete-block pairs are
shared, giving 692 distinct compression transitions. Each distinct transition
checks the complete schedule and all 64 supplied working states against the
local round equations before the generic soundness theorem supplies its
compression equality. Complete input partition and digest checks bind these
reused equalities to each original record.

The generic equations and compression certificates are compiled in a separate
X auxiliary module that imports Lean without importing W. It checks all 692
selected transitions and four additional transitions for the three standard
vectors. The final certificate imports that newly compiled module together
with the actual W module, then checks every selected input partition, ordered
chain, and complete digest binding. This separation reduces the memory needed
while evaluating the arithmetic witnesses. Every selected input and digest
remains bound to its original W record.

The selected digest equalities compose with W's checked preimage construction
and seeded grammar derivation, then with the imported V/U/Q producer chain.
R, S, and T retain their separate sparse-tensor, routing, and captured-JSON
meanings. X does not recertify a full frontier or instantiate the complete
autonomous root transition.

The gate freshly compiles the Q, R, S, T, U, V, and W dependency modules in
order, once each, and the new X SHA auxiliary module in a new external import
directory: eight compilations in total. Import-resolution checks must identify
the exact compiled artifacts from that run, including both W and the X
auxiliary used by the final certificate. Saved compiler
reports and development import caches cannot supply this final acceptance.
The pinned foundation import-cache assumption remains separately recorded.

The gate records the environment observed by a fixed, hashed Python probe
launched by pinned Lake, then passes that exact recorded mapping to pinned
Lean with one worker and synchronous elaboration. The record describes the
probe's observed environment, including any Python startup adjustments.
This avoids retaining Lake as a parent process during each large proof check.
The environment-preparation command, interpreter identity, effective environment,
working directory, and every subsequent compiler invocation are bound in the
retained record. All source, import-resolution, axiom, and rejection checks
remain required; these process settings do not establish operating-system
containment or complete resource accounting.

Generated sources use Lean's kernel decision path. Named theorem audits allow
only `propext`, `Classical.choice`, and `Quot.sound`. Placeholder proofs, new
axioms, unsafe or partial shortcuts, and native-decision shortcuts are
prohibited. The positive certificate must pass. Every deliberate negative
control must fail for its designated false proposition; timeouts, process
terminations, missing imports, and unrelated compiler errors cannot count as
successful rejection.

The runtime suite checks the independent SHA-256 reference against known
vectors and Python's `hashlib`, complete selected input reconstruction,
padding and byte order, imported record bindings, malformed or substituted
inputs, and strict saved-command validation. Controlled compiler fixtures
and installer tests are labelled as such and cannot supply formal acceptance.

The application begins with the clean completed W checkout, verifies its
sealed additive payload, runs the new tests and actual pinned Lean gate, and
reconstructs retained inputs and generated sources. Implementation and
execution evidence receive separate commits. Successful completion is required
before the existing development checkout advances. An optional ordinary push
publishes the validated result. Earlier worker sessions, challenge campaigns,
and negative-control campaigns are not repeated.

## Claim boundaries

Successful X verification may set:

```text
producer_sha256_checked               = true
producer_digests_from_preimages_checked = true
```

These flags cover SHA-256 evaluation and complete digest binding for the
selected 258 W records in the declared Lean reference semantics. The original
W record continues to state W's historical, narrower claim. Its scope is not
rewritten retroactively.

Physical byte capture and filesystem behavior, contextual digest authenticity,
Python and physical execution, and the pinned foundation import-cache
assumption remain external. General parser, grammar, planner, and transformer
equivalence, and temporal secrecy of public or hidden contexts remain open.
The selected result does not establish a newly learned or self-hosted proposer,
an enlarged update language, or a fresh live capability gain.

All twenty-four broader claim flags remain false. Full physical refinement and
attestation, full learned or autonomous-step instantiation, full goal and
information semantics, authenticated succession, frontier and recursive-
productivity recertification, complete resource accounting and authority,
containment, active promotion and rollback, hosted CI, broader platform and
campaign validation, Phase 18 replay, Phase 17 closure, and Gate E closure
remain open. No EGC-0 result is claimed. Unmeasured preparation, hashing, proof
checking, CPU or accelerator, memory, storage, and energy costs are not
treated as zero.

```text
python scripts/run_phase17_producer_sha256_tests.py
python scripts/run_phase17_producer_sha256_gate.py --test-fixture --require-lean --lean-workspace <prepared-formal-root> --output <new-external-output>
```

Preparation-only output cannot satisfy the final application helper. Completed
selected Linux and Windows validation does not close the broader platform or
campaign obligations.
