# DOI and release strategy

## Published GitHub object

The roadmap is published as a GitHub prerelease:

```text
tag:              v5-trajectory
title:            RCP/RCLM v5 Trajectory
status:           prerelease
target commit:    ca79ae182a4f32fa67d265b6d2d2b737ff10557d
roadmap ZIP SHA:  e52938a228a0c202141430ffb6eec9c8ee274ef8287d0403eb948b2e4d410bd6
```

GitHub release: [https://github.com/n9269017/rcp-rclm/releases/tag/v5-trajectory](https://github.com/n9269017/rcp-rclm/releases/tag/v5-trajectory)

It is a roadmap and technical-note release, not completed software and not a Phase 17+ result. The completed `v4.5-phase15-phase16-results` release remains the latest completed software/results release.

## Published Zenodo technical note

The roadmap was deposited manually as a separate Zenodo publication rather than as a new software-series version:

```text
title:        RCP/RCLM v5 Trajectory
resource:     Publication — Technical note
version:      v5-trajectory
access:       Open
license:      CC BY 4.0
exact DOI:    10.5281/zenodo.21898263
concept DOI:  10.5281/zenodo.21898262
```

Exact technical-note DOI: [https://doi.org/10.5281/zenodo.21898263](https://doi.org/10.5281/zenodo.21898263)

All-versions technical-note DOI: [https://doi.org/10.5281/zenodo.21898262](https://doi.org/10.5281/zenodo.21898262)

The technical note is related to:

- software concept DOI `10.5281/zenodo.21710857`;
- exact v4.5 Phase 15–16 results DOI `10.5281/zenodo.21843289`;
- Paper I DOI `10.5281/zenodo.21710273`;
- Paper II DOI `10.5281/zenodo.21710376`;
- the exact GitHub `v5-trajectory` prerelease.

## Integration boundary

Automatic Zenodo ingestion was disabled before the GitHub prerelease was published, preventing the roadmap from entering the software DOI version chain. It may be re-enabled for later actual software/results releases.

Do not modify or replace the v4.5 tag or DOI. Post-publication repository metadata and GitHub-rendering corrections are recorded on `main` without rewriting the archived technical-note files.
