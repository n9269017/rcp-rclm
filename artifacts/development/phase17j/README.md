# Phase17J assistant development evidence

Target base `97bd7b334be7b91aa87f9965180e5522dce14a3b`. This is a reconstructed
historical dependency checkout with matching current Phase17 modules, not the
complete current public checkout. The runner integration binds to a LOCAL
reconstruction snapshot and explicitly rebinds only its Git base prerequisite.
It executes the real physical pipeline; no new Lean proof pass is claimed.

62 new runtime/control tests, 36 prior successor regressions, and 43 application
helper tests passed. Helper full flows use controlled formal-result fixtures.
The prepared catalog contains 21 inherited tasks and one eight-probe task.
New actual formal execution stopped before Lean because Mathlib was absent.
The user's pinned full-checkout run is required before branch advancement.

An initial theorem-parser preparation failure and exploratory prior-suite errors
from unavailable retained Phase17H evidence are preserved, not accepted or hidden.
The final new suite uses actual pinned archives and package outputs. See
`assistant-validation.json` for limits and exact source hashes. No promotion,
full root/phase closure, live gain, EGC, hosted CI, or platform closure.
