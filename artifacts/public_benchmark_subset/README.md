# B9-Bridge Phase 4: Certificate-Preserving Public Benchmark Subset Adapter

Phase 4 starts public-benchmark-subset integration.  The default runnable target
is `local-terminal-public-subset-v0`, a controlled public-style subset.  It is
not an official SWE-bench / Terminal-Bench / RE-Bench / MLE-bench / WebArena
result.

The harness records:

```text
BenchmarkRun_B(M_0,...,M_N) ⇓ (Score_{B,0},...,Score_{B,N})
∀t<N, Check_RCP(PCS_t)=1
Score_B(M_N) - Score_B(M_0) = Δ_B > 0
```

plus LECert FullPass status, checker output, certificate preservation, runlog
hashes, certificate hashes, and claim boundaries.

## Smoke test

```powershell
python .\artifacts\public_benchmark_subset\certified_public_subset_harness.py --modes rclm --N 5 --seeds 0
```

## RCP + RCLM controlled public-style subset

```powershell
python .\artifacts\public_benchmark_subset\certified_public_subset_harness.py --modes rcp rclm --N 5 --seeds 0
```

Outputs:

```text
artifacts/public_benchmark_subset/results/
  public_subset_benchmark_summary.json
  public_subset_benchmark_detailed.json
  public_subset_benchmark_results.csv
  rcp_N5_seed0_local-terminal-public-subset-v0/
  rclm_N5_seed0_local-terminal-public-subset-v0/
```

## External public benchmark mode

After running an official/public benchmark harness externally, fill:

```text
artifacts/public_benchmark_subset/manifests/external_public_subset_template.json
```

then run:

```powershell
python .\artifacts\public_benchmark_subset\certified_public_subset_harness.py --benchmark external-manifest --external-manifest path\to\filled_manifest.json
```

## Claim boundary

This phase creates the sidecar protocol needed for public benchmark subsets. The
default run is controlled and local. It does not claim full public B10, broad
learned-agent entry, frontier-scale validation, or full autonomous RSI.
