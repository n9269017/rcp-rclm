# DOI and release strategy

## GitHub object

The intended GitHub object is:

```text
tag:    v5-trajectory
title:  RCP/RCLM v5 Trajectory
status: prerelease
```

It is a roadmap and technical-note release, not completed software and not a Phase 17+ result.

The completed `v4.5-phase15-phase16-results` release remains the latest completed software/results release.

## Zenodo object

Create a separate manual Zenodo record titled:

```text
RCP/RCLM v5 Trajectory
```

Recommended metadata:

```text
resource type: Publication — Technical note
version:       v5-trajectory
access:        Open
license:       CC BY 4.0
```

The roadmap should receive its own DOI series rather than becoming the newest version in the existing software concept DOI series.

Relate the roadmap record to:

- software concept DOI `10.5281/zenodo.21710857`;
- exact v4.5 Phase 15–16 results DOI `10.5281/zenodo.21843289`;
- Paper I DOI `10.5281/zenodo.21710273`;
- Paper II DOI `10.5281/zenodo.21710376`.

## Integration boundary

Before publishing the `v5-trajectory` GitHub prerelease, temporarily disable automatic Zenodo ingestion for this repository. Deposit the roadmap package manually as a technical note, record the minted roadmap DOI, then re-enable automatic GitHub ingestion for later actual software/results releases.

Do not modify or replace the v4.5 tag or DOI.
