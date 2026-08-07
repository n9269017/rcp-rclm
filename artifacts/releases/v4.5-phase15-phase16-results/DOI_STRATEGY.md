# DOI Strategy

The existing Zenodo software concept DOI remains `10.5281/zenodo.21710857` and should be used for general citations of the evolving RCP/RCLM public project.

After this results-only tree is merged, create the GitHub release/tag `v4.5-phase15-phase16-results`. With the `n9269017/rcp-rclm` Zenodo GitHub integration enabled, Zenodo will archive that release and mint a new version DOI under the existing concept DOI. Do not insert a guessed version DOI before Zenodo creates it.

A separate DOI for the still-private implementation repository is deliberately deferred. A restricted Zenodo deposition is possible, but its DOI and descriptive metadata would be public even when files are restricted. The preferred boundary is to retain private-code provenance through exact private Git commit/tree IDs and artifact hashes through Phase 18 / Gate E closure, then reconsider a restricted implementation deposition.
