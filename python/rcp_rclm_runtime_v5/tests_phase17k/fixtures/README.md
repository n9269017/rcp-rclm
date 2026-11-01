# Ordered synthetic known-challenge fixture

`ordered_known_challenge.json` is a public synthetic test fixture, NOT a fresh
hidden task, autonomous improvement result, historical attestation, or promotion.
SHA-256: `16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f`.

It takes the prior D-I known-answer fixture's public context and already revealed
entropy, runs the actual present-only controller once, and records all eight
rejections followed by a ninth passing candidate. No seed or winner search is
performed. The original isolated passing fixture remains unchanged and is a
required negative producer-order example. Both use the same final bounded program;
their transcripts and materialized candidate-package identities differ.

The new candidate identity is
`b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e`.
Earlier candidate capability proofs are not reassigned to this identity. Full
frontier/root verification and promotion remain false.
