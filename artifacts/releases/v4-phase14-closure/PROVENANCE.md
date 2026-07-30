# Phase 14 permanent evidence provenance

This directory permanently retains the compact, machine-readable evidence for
Executable Core v4 Phase 14. The files were copied byte-for-byte from the
successful GitHub Actions workflow artifacts before their 90-day retention
window expires.

## Certified boundary

```text
repository: n9269017/rcp-rclm
certified source head: 363235f7d5f03508aeeac85c6319533a900dbb00
audit tag: audit/phase-14-certified
workflow run: 30429512027
closure job: 90538529869
Phase 14 merge: e549590c6f3c35497939a107d589f66f2720e0c8
post-merge hygiene merge: 1517a235f76c80125a6d9f670e9bd87ab7da1046
```

The accepted machine boundary is:

```json
{
  "accepted": true,
  "phase14_exit_closed": true,
  "gate_e_closed": false,
  "next_phase": 15
}
```

## Source artifacts

| Evidence | Artifact ID | Artifact digest |
|---|---:|---|
| Final closure | `8719247901` | `sha256:5c489ddb6508c393d72ecf74f9703bc99c2518d8d2e007cc228d24e88762cb21` |
| Capture and adversarial audit | `8715404023` | `sha256:3eff196370c8b1c0c34e182e891af71d662705ff7ca99126af88d54e301fac62` |
| Ubuntu pinned replay | `8715642934` | `sha256:d63e184587b1b61be8e59951fa14ba321e48fe63a309df070e4028c1934225ee` |
| Windows pinned replay | `8716366143` | `sha256:96994984350c38f60d0c19f98267d7f453b4f586a64d5f41957e0cf17fdc9c38` |
| macOS pinned replay | `8719227870` | `sha256:4e03b974d9de5d8395362d5a6c89034bc17818092eec0ba74f2bd0c3582ff994` |
| Full content-addressed bundle (not duplicated here) | `8715403795` | `sha256:2331d850f809f27d1ee1c99f9d0b2bf7b0c5a7767d215cfc1b7b4369647651d8` |

The full approximately 6.6 MB content-addressed bundle remains identified by
its artifact ID and digest above. This tracked directory retains the compact
closure, trajectory, bundle manifest, adversarial report, and all platform
replay reports required to interpret and independently audit the result.

## Integrity

`SHA256SUMS.txt` in this directory hashes every retained evidence file and this
provenance record, excluding only the checksum file itself. The repository-root
`SHA256SUMS.txt` additionally binds this directory into the complete tracked
release surface.
