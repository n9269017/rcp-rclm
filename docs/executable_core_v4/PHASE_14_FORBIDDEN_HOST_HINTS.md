# Phase 14 forbidden host-route hints

Every autonomous-search input record must contain the following exact false-valued fields:

```json
{
  "next_successful_transition_index_present": false,
  "required_successful_component_set_present": false,
  "accepted_program_bytes_present": false,
  "expected_candidate_hash_present": false,
  "expected_new_capability_present": false,
  "expected_final_model_identity_present": false,
  "host_selected_objective_present": false
}
```

## Rejection rule

Any true field rejects the search input before the active package is invoked.

Equivalent information hidden under another field, filename, environment variable, process
argument, archive member, retrieval entry, memory entry, training record, or challenge record
also rejects.

## Additional prohibited route data

```text
ordered list of component families expected to be promoted
fixed accepted transition count embedded in the controller
expected first accepted attempt index
expected rejection count used to steer the package
expected final frontier member
expected final package or model hash
reference mutation program or decoded completion
host-written correction after a rejection
```

## Permitted host data

```text
legal mutation grammar
immutable total resource budget
current active package hash
current history and ledger hash
challenge commitment
verifier-policy hashes
canonical schema versions
rejection evidence from attempts that actually occurred
```

The distinction is:

```text
permitted: rules defining what may be attempted and how attempts are judged
forbidden: answers identifying which legal attempt should succeed
```
