# Executable Core v3 contract schemas

`phase_9_contract.schema.json` freezes the selected learned RCLM package, update,
certificate, capability-frontier, held-out-access, and transition-report records.

`phase_10_substrate.schema.json` freezes the selected compact-transformer architecture,
fixed tokenizer, canonical tensor and adapter manifests, model package, package report,
and zero-output conservative-extension report.

`phase_10_learned.schema.json` freezes the Phase 10B learned-evidence summary that binds
the predecessor and candidate packages, current-model Lean verifier reports, selected
entropy/KL/diagonal-QRE evidence, held-out policy, and accepting Phase 9 learned
transition.

All schemas cover only `compact_decoder_only_transformer_v1` and the selected
`lean_theorem_completion_v1` task class.  They do not authorize arbitrary models, task
classes, general native-float transformer equivalence, or generic successor
availability.  Phase 10B establishes learned execution and frontier expansion, not yet
promotion or independent replay.
