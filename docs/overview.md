# Overview

This repository is a two-paper companion package plus one shared Lean/artifact repository.

## Package map

- **Paper I** develops the architecture-general Recursive Coherence Preservation / RCP-II theorem stack.
- **Paper II** instantiates that theorem stack in the RSI--RCLM architecture.
- **Lean** supplies a shared Lean 4 proof project for the canonical finite RCP/RCLM witness and the RCLM-to-RCP refinement core.
- **Artifacts** supply controlled executable reference objects, replay checkers, and run logs.

## Main result in one paragraph

The package develops a domain-relative, certificate-relative robust reflective successor theorem for certified seed-library classes. Inside those certified classes, the theorem stack supports recoverable-monotone, non-lossy, successor-verification-preserving finite or infinite self-improvement paths under declared uncertainty envelopes. Reality-containment and tractability are separately certified. Learned systems enter the theorem domain only if they pass the M3-Min learned-entry certificate boundary.

## Publication format

The recommended public release format is two companion papers plus one repository:

1. Paper I: mathematical foundations.
2. Paper II: architecture and artifact realization.
3. Shared Lean/artifact repository.

The papers should not be merged into one back-to-back 400-page paper for the initial public release.
