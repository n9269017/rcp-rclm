# Phase 9 held-out task and reference-answer policy

The authoritative held-out partition is external to the learned predecessor and proposal
backend.

Before candidate freeze:

```text
generator sees held-out task IDs:          false
generator sees held-out prompts:           false
generator sees reference answers:          false
training backend sees held-out prompts:     false
training backend sees reference answers:   false
```

After the candidate state and candidate package hashes are frozen:

```text
independent evaluator sees prompts:          true
independent evaluator sees reference answers:true
```

The learned package stores only the final independently certified task record after an
accepted evaluation. It never stores the external reference-answer content. The contract
binds the held-out task manifest, answer store, and evaluator policy by SHA-256.

A new capability-frontier entry is valid only when:

1. its task partition is `heldout`;
2. it was absent from the predecessor frontier;
3. it has a current-model certification from `pinned_lean_theorem_verifier_v1`;
4. the certificate binds the frozen held-out access policy;
5. every protected predecessor task is recertified for the candidate model.
