# Phase 15 private bootstrap artifact

`runtime-v4-phase14-bundle-30429512027-1.zip` is the exact GitHub Actions artifact archive downloaded from the public Phase 14 authoritative closure workflow.

```text
public repository: n9269017/rcp-rclm
workflow run:      30429512027
artifact id:       8715403795
artifact name:     runtime-v4-phase14-bundle-30429512027-1
artifact SHA-256:  2331d850f809f27d1ee1c99f9d0b2bf7b0c5a7767d215cfc1b7b4369647651d8
source head:       363235f7d5f03508aeeac85c6319533a900dbb00
```

The archive is retained inside the private Phase 15 line so authoritative Phase 15 CI can reconstruct the exact certified M8 starting state without relying on cross-repository Actions credentials or mutable artifact availability. The extracted bundle is still independently validated against its own content-addressed manifest and the frozen Phase 14 trajectory identities before use.
