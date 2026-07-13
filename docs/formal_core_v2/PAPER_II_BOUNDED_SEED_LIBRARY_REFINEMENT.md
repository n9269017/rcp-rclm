# Paper II bounded seed-library and packet-builder refinement

## Phase boundary

This phase identifies Paper II's declared bounded seed-library and
successor-verification packet-construction layer with the compiled Formal Core v2
architecture interfaces. It is Lean-only. It neither introduces an executable
runtime nor begins Gate C.

This phase establishes a generic bounded seed-library refinement and a concrete
finite binary instance. The executable phase remains unlicensed.

The refined chain is:

```text
bounded seed-domain predecessor
  -> finite witness library
  -> finite packet grammar
  -> bounded update word and proof word
  -> generated proposal
  -> constructed certificate
  -> selected typed candidate
  -> realized successor
  -> resource authorization
  -> trusted RCLM checker acceptance
  -> complete RCLM successor obligations
  -> complete Paper II successor-verification obligations
  -> complete forgotten RCP successor obligations
  -> successor bounded seed-domain membership
```

## Generic finite library and grammar

`RCLM.PaperIIBoundedSeedLibrary` carries:

```text
seedDomain
witnesses : State -> Finset Witness
grammar   : State -> Finset Word
wordDepth and maxWordDepth
proofLength and maxProofLength
witness, proposal, certificate, candidate, and resource decoders
seed-domain to architecture-domain refinement
grammar nonemptiness on every seed-domain state
word-to-witness membership
witness-library coverage
proposal generation
certificate construction
candidate selection
successor realization
resource authorization
checker acceptance
successor seed-domain closure
```

The finite `Finset` objects and the numerical bounds are theorem data. A label
such as “bounded library” does not by itself establish finiteness, coverage, or
completeness.

## Packet builder

A word together with seed-domain and grammar-membership proofs forms:

```lean
RCLM.PaperIIBoundedSeedPacket
```

The definition:

```lean
RCLM.PaperIIBoundedSeedPacket.toEngineStep
```

constructs the existing `ArchitectureEngineStep` without changing its trust
boundary. The resulting step still contains explicit witness, proposal,
certificate, candidate, resource, realization, and checker-acceptance evidence.

The theorem:

```lean
RCLM.paper_ii_bounded_seed_packet_builder_sound
```

returns:

```text
complete RCLM StepObligations
complete Paper II successor-verification obligations
successor bounded seed-domain membership
declared verifier-schema persistence
declared uncertainty-envelope persistence
declared goal-identity/drift bound
```

The architecture refinement theorem:

```lean
RCLM.paper_ii_bounded_seed_packet_refines_architecture
```

additionally returns:

```text
typed architecture successor evidence
forgotten core-checker acceptance
complete forgotten RCP StepObligations
transported recovery-composition laws
transported monitor-refinement evidence
```

## Semantic identification

`RCLM.PaperIISeedSemanticIdentification` prevents similarly named fields from
being treated as automatically equal. It requires pointwise equality proofs for:

```text
declared verifier schema
verifier-schema transport
verifier-schema refinement relation
declared uncertainty envelope
uncertainty-envelope transport
uncertainty-envelope refinement relation
declared goal
goal transport
goal distance
goal-drift budget
```

The packet-builder theorem rewrites through these equalities before returning the
declared Paper II conclusions.

## Recursive bounded seed-domain closure

`RCLM.PaperIIBoundedSeedPredecessor` combines an architecture predecessor with
explicit seed-domain membership. The recursive construction selects a word from
the supplied nonempty finite grammar, builds the corresponding checked engine
step, and constructs the next predecessor.

The public theorems are:

```lean
RCLM.conditional_infinite_paper_ii_bounded_seed_trajectory_exists
RCLM.infinite_paper_ii_bounded_seed_step_result
RCLM.infinite_paper_ii_bounded_seed_step_refines_architecture
```

The third theorem proves that every selected recursive step carries both the
complete RCLM result and the complete forgotten RCP architecture refinement.

The recursion uses classical choice only to select from the explicitly supplied
`Finset.Nonempty` witness. The theorem does not infer grammar nonemptiness or
successor seed-domain closure from checker soundness.

## Concrete binary reference

The concrete finite reference defines:

```text
packet words: improve, stabilize, rejected
active grammar at initial: {improve}
active grammar at target:  {stabilize}
maximum update-word depth: 1
maximum proof-word length: 1
rejected word: absent from every active grammar
```

The active word decodes to the already proved architecture witness, proposal,
certificate, candidate, resource record, realization, and checker evidence.

The concrete Paper II objects are identified as:

```text
verifier schema: trustedBinaryChecker
uncertainty envelope: contained
goal: biasedTarget
verifier transport: identity
uncertainty transport: identity
goal transport: identity
goal drift budget: zero
```

These meanings are exact for the finite binary reference. They do not claim
arbitrary verifier-schema semantics, real-world uncertainty containment, or
semantic goal identity for trained systems.

The concrete results include:

```lean
RCLM.ClassicalBinary.initial_bounded_seed_packet_builder_refinement
RCLM.ClassicalBinary.initial_bounded_seed_direct_engine_refinement
RCLM.ClassicalBinary.classical_bounded_seed_packet_builder_refinement
RCLM.ClassicalBinary.classical_infinite_bounded_seed_trajectory_exists
RCLM.ClassicalBinary.classical_infinite_bounded_seed_step_result
RCLM.ClassicalBinary.classical_infinite_bounded_seed_step_refines_architecture
```

The selected concrete path performs one strict KL-derived improvement and then
accepted stability continuations. It does not establish strict useful novelty at
every recursive step.

## Validation

The completed theorem surface passed the pinned Linux workflow:

```text
Branch source head:   a09c742ca2541ad3302a5c1041852974649e09c8
CI checkout commit:   02790b14d1fe9b16745ec8236bf91c9a0608e9b8
Workflow run:         29224543624
Build:                1953 jobs, success
No sorry/admit:       pass
Project-local axioms: none
No sorryAx:           pass
RCLM audit count:     47 declarations
Artifact:             formal-core-v2-audit-29224543624-1
Artifact SHA-256:     e1f00cad76ac2799b8006e01cfdf6ba47f9348b4074d664bb4d1a2314716b6b2
```

The audited foundational union is:

```lean
[propext, Classical.choice, Quot.sound]
```

Some concrete projection and domain-classification theorems are axiom-free. No
project-local axiom or admitted proof occurs.

## Exact claim boundary

This phase proves:

```text
finite bounded witness and packet grammars
explicit generator coverage on the declared finite class
explicit packet construction and checker acceptance
verifier/envelope/goal semantic identification by equality
successor seed-domain closure
conditional infinite bounded seed-library recursion
complete RCLM and forgotten RCP obligations at every selected step
```

It does not prove:

```text
unbounded packet-grammar completeness
unbounded proof-search completeness
arbitrary learned-system seed-domain entry
arbitrary learned generator coverage
strict useful improvement at every recursive step
full Paper II semantic identity beyond the binary reference
Gate C quantum relative entropy or channel recovery
Python checker or generator refinement
an executable recursive promotion loop
empirical or benchmark recursive self-improvement
```

## Next formal boundary

The next major gate is the finite-dimensional quantum Gate C extension, followed
by strengthening the RCLM refinement over the selected quantum objects. No
executable artifact should begin before those theorem boundaries and the final
paper-facing closure decision are explicit.
