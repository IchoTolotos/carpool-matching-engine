# Seeded scale benchmark

## Purpose

The scale suite records repeated, in-process observations as the number of vehicles and shipments
grows. It complements the small greedy comparison; it does not simulate production traffic or
include routing-provider, database, network, serialization, or application latency.

## Method

`benchmarks/scale.py` generates three stable synthetic shared-destination problems:

| Scenario | Vehicles | Shipments | Seed |
| --- | ---: | ---: | ---: |
| small | 4 | 16 | 4,016 |
| medium | 8 | 32 | 8,032 |
| large | 16 | 64 | 16,064 |

Each vehicle has enough capacity for an even share of the shipments. All coordinates are generated
from the documented seed around an invented center and converted to a complete matrix by the
straight-line synthetic provider. Each run uses parallel cheapest insertion plus guided local
search with a caller-selected wall-clock limit.

Run five observations per case and record the machine label:

```bash
.venv/bin/python -m benchmarks.scale \
  --repetitions 5 \
  --seconds-per-run 1 \
  --hardware-label "Apple M4, 10 logical CPUs"
```

The report includes:

- minimum and maximum served shipments across runs
- best and median objective across runs
- median elapsed time
- nearest-rank p95 elapsed time
- platform, architecture, logical CPU count, Python version, and OR-Tools version

## Recorded reference run

The table below records the release-polish implementation run. It is a reference point, not a
portable performance promise.

<!-- SCALE_BENCHMARK_RESULTS_START -->
Source baseline: `a4d2e738367c5ddd979c04f4085f1d9eef94aefb` plus the release-polish change set.

```text
hardware=Apple M4, 10 logical CPUs
platform=macOS-15.7.3-arm64-arm-64bit, architecture=arm64, logical_cpus=10
python=3.12.12, ortools=9.15.6755
repetitions=5, seconds_per_run=1, p95=nearest-rank

scenario  vehicles  shipments  served range  best objective  median objective  median ms  p95 ms
small     4         16         16-16         9468            9468              1001.81    1004.41
medium    8         32         32-32         13214           13214             1003.68    1007.32
large     16        64         64-64         23197           23197             1006.30    1008.29
```
<!-- SCALE_BENCHMARK_RESULTS_END -->

## Interpretation limits

The generated inputs are deterministic, but wall-clock-bounded local search can return different
objectives across machines or runs. The one-second limit also creates a runtime floor close to the
configured budget for cases where local search consumes the full allowance. Compare quality and
runtime together, and do not extrapolate these three points into a production capacity claim.
