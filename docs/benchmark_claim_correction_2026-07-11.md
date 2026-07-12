# Benchmark claim correction — 2026-07-11

The previously published HumanEval/EvalPlus artifacts have been withdrawn from
the active repository claim surface.

The submitted evaluation corpus consisted of task-indexed, prewritten Python
solutions associated directly with the HumanEval task IDs. EvalPlus genuinely
evaluated that corpus, but the result was not:

- prompt-to-code generation by an RCLM model;
- a held-out generative-model benchmark;
- evidence of recursive self-improvement;
- evidence that RCP/RCLM Lean theorems certified program semantics; or
- evidence of predecessor-generated successor capability improvement.

The raw historical artifacts remain recoverable from Git history for provenance,
but no HumanEval, HumanEval+, or EvalPlus capability claim is currently active.

A future benchmark result must use a non-task-indexed generator, preserve raw
prompt-to-output provenance, prohibit answer-corpus lookup, use held-out
evaluation tasks, and run through the official evaluator under a predeclared
protocol.
