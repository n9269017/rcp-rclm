# Phase 11 validation

## Phase 11A exact code proof

The active-model typed-proposal implementation closed at:

```text
validated branch head:
4d408f4ec6ff62e1b60a6e2344a252d05bc1c9eb

PR merge-test commit:
de744688afb97fe1fec5a06912656c171a295439

workflow run:
29724450584

workflow attempt:
1
```

Every job succeeded:

```text
Ubuntu Phase 9 and Phase 10 regression       success
Windows Phase 9 and Phase 10 regression      success
macOS Phase 9 and Phase 10 regression        success
source-quality gate                           success
focused Phase 11A tests                       success
Draft 2020-12 evidence schema                 success
canonical reference recomputation             success
repository-root entry point                   success
phase11a_slice_closed=true record              success
```

## Stable evidence

```text
active package:
724fcda02a1124eeeb2f2c0207052d16705d6fdb95afc6b87a7f5e6b658e47c4

active state:
13e5f135b635b6282b9076b849b6ff1c6d4a59189744a52f76c17ba37ee0242e

active model:
94a07482cf243964d54e6f9079103f7d1ca85745d351a0a28a9030cbb11ef023

active generator:
166966f0e0724c65f1137529fb774882cdeb88c2c1262ff243ad0709f8a12b8b

active planner:
6d3b7dff5117791ba50c7b0b89eddb07d8acaf1afb0deb56e32d06fcff55dff2

bootstrap validation:
6b36353fa52001b4a25fac297638d30a4f6408c44723083b2c578ca24a876966

proposal protocol:
5fbf5cb884187dc37e492ce9cd0057f746d60138e9a542fa1723072a3914b7d8

fixed budget:
a01b0dc9454a4e59f0b9380dfa073009779c4d009c76628c36ac57c6f13a646e
```

The first model invocation and rejection are:

```text
invocation:
d33ef2b1399884fcf1b4669c2e9c46b59fcd8da997ea8c7a6bd800074c8ead1d

program:
0d602b6cdb2d44eedbd967cad1ec7c2e0d2c8db6f88bfcb15dccaecd3be95b10

validation:
25919209c90e7710cb50706ebad8d0085e66067eb8a95686205d01a79fac3c74

reason codes:
PHASE11_BUDGET_EXCEEDED
PHASE11_FORBIDDEN_UPDATE_CLASS
```

The fresh second model invocation is:

```text
invocation:
ed14627f8debf0e2cac6007feea4bb0cc0456e39fbc906e6b5d547106988c926

program:
cf34b0b9e153a99f63757d087f52a12cf3388c3b54c4afadad2b5815953f0dae

validation:
be71dd82defd33ab82ef736922ace696b8f453b7a493678d61a07acc3c862aa6

accepted:
true
```

The complete summary hash is:

```text
fe32f0d879f26929505170fbf695657af02be623090cfc41b383aabc32e8312e
```

The canonical summary file itself has SHA-256:

```text
ef286eaab9bee4a1ef4a752f25755b5e084a5af04056cf0a5df0a25f54b78663
```

Ubuntu, Windows, and macOS produced identical bytes.

## Code-proof artifacts

```text
Ubuntu:
8453735527
sha256:248ef5e6b9d5c91be629aff8be4d235c95143a11314b270645a6d64d5c655e05

Windows:
8453754142
sha256:ceea2b370652263daa69ab51ed6184e2d35c9c9f7c26d7a8aee0440992088296

macOS:
8453740290
sha256:35f960fd44e4b217c4d20d16fe6dbaa5e54acc9d50565e448347910bd035e61b

final closure:
8453757707
sha256:30b23dc8c4f754377a1407fea57f57278f63989c3505f0cb15923d93959b0f13
```

## Final-head binding

The committed `phase_11_generator_manifest.json` retains the stable reference hashes and
this exact code-proof run.  The final documentation and manifest head is rerun through the
same full cross-platform workflow.  That later run is recorded in PR #31 without editing
the source again, avoiding a self-referential commit or artifact digest.

## Remaining Phase 11 boundary

The code proof closes model-owned typed proposal generation and rejection behavior. It does
not yet close candidate realization, candidate rejection after realization, accepted
promotion, or installation of changed generator/planner bytes. Those are Phase 11B.
