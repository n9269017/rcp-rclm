# Artifact Inventory

## Published byte-identical authority archives

| Phase | Artifact ID | Created UTC | SHA-256 | File |
|---|---:|---|---|---|
| 15 | `8916070081` | `2026-08-05T02:35:28Z` | `1dd356cafda6bf7d2287b5d49e71b60ed9e917a84ce5ead0405079ba2e0c78c5` | `original-artifacts/runtime-v4-phase15-contract-macos-30969783629-1.zip` |
| 15 | `8916071270` | `2026-08-05T02:35:33Z` | `d4b93a612e20b5dacfa4e15b1fcf6a1902188cb8775ac2b86c2214b0dfc78baa` | `original-artifacts/runtime-v4-phase15-contract-ubuntu-30969783629-1.zip` |
| 15 | `8916078060` | `2026-08-05T02:35:58Z` | `530ac4e9e49cad91534ce0c29e9db4c89c9c309ff98e056f68b0eae49aa37925` | `original-artifacts/runtime-v4-phase15-contract-windows-30969783629-1.zip` |
| 15 | `8917973439` | `2026-08-05T04:27:09Z` | `197465275e7716a7a51eb4ffdc255696bd92129cdf0910e9712b7ca22028053e` | `original-artifacts/runtime-v4-phase15-final-30969783629-1.zip` |
| 15 | `8917966558` | `2026-08-05T04:26:44Z` | `c455e8475ff012b1fad540e85b00a62211926df90a8f98826263ccba36c15121` | `original-artifacts/runtime-v4-phase15-replay-macos-30969783629-1.zip` |
| 15 | `8916512196` | `2026-08-05T03:02:55Z` | `8cad9c795b9883ba8dbe412a40e328d52ef32b4702481d276fd5fc8e5ef5058d` | `original-artifacts/runtime-v4-phase15-replay-ubuntu-30969783629-1.zip` |
| 15 | `8917085240` | `2026-08-05T03:34:38Z` | `912dd797a20035e2cdb45553b8b9e1a598e169307cfa7028ad6d7e1142f71232` | `original-artifacts/runtime-v4-phase15-replay-windows-30969783629-1.zip` |
| 16 | `8984439868` | `2026-08-07T06:29:26Z` | `f9efe80e1c8336df913fdb5388684f8be6997bae31a507dd3a0b38444c100ab1` | `original-artifacts/runtime-v4-phase16-attacks-31153935872-1.zip` |
| 16 | `8984402546` | `2026-08-07T06:27:48Z` | `22d326bff176ed58047e405455c25678542a7e7e2dde8d92e88e082736534f25` | `original-artifacts/runtime-v4-phase16-contract-macos-31153935872-1.zip` |
| 16 | `8984401886` | `2026-08-07T06:27:47Z` | `de68349445031eb153892760e59e5799c80353a53d446742cfe9fd64359103f2` | `original-artifacts/runtime-v4-phase16-contract-ubuntu-31153935872-1.zip` |
| 16 | `8984411161` | `2026-08-07T06:28:11Z` | `e3bb776829f5fb98ec06e682950646fb031e5017cc40a449694c0ccd69533378` | `original-artifacts/runtime-v4-phase16-contract-windows-31153935872-1.zip` |
| 16 | `8984481241` | `2026-08-07T06:31:10Z` | `ce7f1de4654306d5280970dfc92453a8743cf1e02fe98963f1e940c0077582f9` | `original-artifacts/runtime-v4-phase16-final-closure-31153935872-1.zip` |
| 16 | `8984446330` | `2026-08-07T06:29:44Z` | `ec03d53a7e161c3d7815aab0ffb63af00b21b2478027e46a9031b337036459db` | `original-artifacts/runtime-v4-phase16-replay-macos-31153935872-1.zip` |
| 16 | `8984445356` | `2026-08-07T06:29:41Z` | `e7e1271cac897955537179db8a887559151886a1b89a1cf49758931ae8406817` | `original-artifacts/runtime-v4-phase16-replay-ubuntu-31153935872-1.zip` |
| 16 | `8984453664` | `2026-08-07T06:30:03Z` | `64eefdd5c6c6cda271b2cc935d95ad838dd610cedb580067e3c368d52ba70866` | `original-artifacts/runtime-v4-phase16-replay-windows-31153935872-1.zip` |

## Withheld private authority archives

| Phase | Artifact ID | Created UTC | SHA-256 | Reason |
|---|---:|---|---|---|
| 15 | `8916349242` | `2026-08-05T02:53:07Z` | `fb0d12fdfcb0b815d6b76d5b312a29f21d6caf5e71b45356c77135a13330d294` | Contains the aggregate capture and a full bundle manifest whose private member inventory crosses the results-only publication boundary. Safe constituent reports are published separately. |
| 15 | `8916353526` | `2026-08-05T02:53:23Z` | `56003f95ded054be21dd3f743c2145fdf6e92543af28bb350f64ec8f4fee00b5` | Contains model weights, candidate packages, private challenge/answer material, and runtime implementation evidence. |
| 16 | `8984430600` | `2026-08-07T06:29:01Z` | `7337079801916ecccce0e3a292d5379cea17b571acc6f31b9b38cb21f9f63dde` | Contains the complete 50.9 MB capture and reference campaign; safe bootstrap/foundation reports and final closure identities are published separately. |

## Additional safe capture receipts

The four non-sensitive Phase 16 capture schema-validation receipts are extracted byte-identically from the withheld full capture archive and retained under `phase16/`:

- `phase16/bootstrap_schema_validation.json` — SHA-256 `2f78dc23ad58bc9516e42c037d41ec91ff386adbdd4e881037338bd3f4311ed2`.
- `phase16/campaign_schema_validation.json` — SHA-256 `c5fca9c33f624dca9299934e70da60e2bd8a7e7a8b8fb61b55d3a3a2f4030d65`.
- `phase16/capture_schema_validation.json` — SHA-256 `0306821495fe23d664139169b1f62701113b4cddead5b7b64c0c6c35d76b20f4`.
- `phase16/foundation_schema_validation.json` — SHA-256 `822fb542758d30595a1d194c152d720e6f50cecbadc1610828d66478b3117a47`.

