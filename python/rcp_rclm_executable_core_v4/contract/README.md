# Executable Core v4 Gate E contract

`gate_e_autonomous_search.schema.json` is the Draft 2020-12 schema for the initial
schedule-free bounded-search report.

The schema freezes:

```text
false-valued route-hint fields
predecessor capability and recursive-productivity frontiers
ordered package-generated attempts
canonical attempt and enumeration hashes
search budget and zero-manual-repair boundary
post-freeze hidden-challenge boundary
promotion versus proof-carrying exhaustion result
open Gate E and Phase 14 closure flags
```

Semantic validation beyond JSON shape is implemented by Runtime v4. In particular, the
runtime recomputes attempt hashes, enumeration hashes, report hashes, first-accepted
selection, frontier retention/expansion, recursive-productivity retention, total search cost,
and exhaustion consistency.
