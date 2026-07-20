# Executable Core v3 contract schemas

`phase_9_contract.schema.json` freezes the selected learned RCLM package, update,
certificate, capability-frontier, held-out-access, and transition-report records.

`phase_10_substrate.schema.json` freezes the selected compact-transformer architecture,
fixed tokenizer, canonical tensor and adapter manifests, model package, package report,
and zero-output conservative-extension report.

Both schemas cover only `compact_decoder_only_transformer_v1` and the selected Phase 9
`lean_theorem_completion_v1` task class. They do not authorize arbitrary models or task
classes. The Phase 10 schema establishes a package substrate, not a trained successor or
frontier-expansion claim.
