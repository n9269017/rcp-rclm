# RCP/RCLM v5 Trajectory

**Version:** `v5-trajectory`  
**Publication date:** 2026-08-11  
**Status:** roadmap and technical note only  
**Implementation included:** no  
**Phase 17+ result claimed:** no  
**Gate E closed by this document:** no  
**Exact technical-note DOI:** [`10.5281/zenodo.21898263`](https://doi.org/10.5281/zenodo.21898263)  
**Technical-note concept DOI:** [`10.5281/zenodo.21898262`](https://doi.org/10.5281/zenodo.21898262)  
**GitHub prerelease:** [`v5-trajectory`](https://github.com/n9269017/rcp-rclm/releases/tag/v5-trajectory)

This public trajectory begins from the completed private Phase 16 boundary and sets the planned dependency order:

```text
Phase 17 → Phase 18 → Phase X → Phase Y → Phase Ω → Phase Z
```

A separate empirical track accompanies it:

```text
EGC-0 → EGC-1 → EGC-2 → EGC-3 → EGC-4 → EGC-5 → EGC-6
```

## Documents

- [`PHASE_17_TO_Z_TRAJECTORY.md`](PHASE_17_TO_Z_TRAJECTORY.md) — complete public-safe technical trajectory.
- [`EGC_GENERAL_CAPABILITY_TRACK.md`](EGC_GENERAL_CAPABILITY_TRACK.md) — empirical general-capability measurement program.
- [`PUBLICATION_AND_CLAIM_BOUNDARY.md`](PUBLICATION_AND_CLAIM_BOUNDARY.md) — exact publication, withholding, and nonclaim boundary.
- [`DOI_AND_RELEASE_STRATEGY.md`](DOI_AND_RELEASE_STRATEGY.md) — published GitHub prerelease and separate Zenodo technical-note identities.
- [`ROADMAP_MANIFEST.json`](ROADMAP_MANIFEST.json) — machine-readable roadmap status and dependency order.
- [`CITATION.cff`](CITATION.cff) — citation metadata for the roadmap object.
- [`GITHUB_RELEASE_NOTES.md`](GITHUB_RELEASE_NOTES.md) — notes for the `v5-trajectory` GitHub prerelease.
- [`SHA256SUMS.txt`](SHA256SUMS.txt) — checksum manifest for this roadmap directory.

## Immediate planned boundary

The next two workstreams are distinct:

1. **Core:** specify and implement Phase 17.
2. **Empirical:** freeze and run EGC-0 against the completed Phase 16 boundary.

They may proceed on isolated private branches, but neither may import hidden evaluation material or authority from the other.

## Publication boundary

This directory publishes the scientific architecture, dependency order, theorem shapes, and empirical questions. It does not publish the executable acceptance machinery, Phase 17+ code, hidden task corpora, exact attack payloads, resource schedules, or private evaluator internals.

Roadmap documents are licensed under CC BY 4.0; see `LICENSES/CC-BY-4.0-NOTICE.txt`.
