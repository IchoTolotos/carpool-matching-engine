# Synthetic benchmark methodology

## Purpose

The benchmark is a small, reproducible engineering comparison. It checks that the public engine can
solve fixed synthetic pickup-and-delivery scenarios and places its observed objective beside a
plain deterministic baseline. It is not a production traffic study, a road-network simulation, or
evidence that either method is globally optimal.

Run it from the repository root with the pinned environment:

```bash
.venv/bin/python -m benchmarks.run
```

## Fixed inputs

`benchmarks/scenarios.py` constructs four synthetic shared-destination cases:

- `balanced-clusters`: enough capacity for every shipment, with pickups near two driver corridors
- `capacity-pressure`: fewer seats than optional shipments, making explicit drops unavoidable
- `vehicle-eligibility`: shipment-to-vehicle restrictions constrain otherwise available capacity
- `greedy-eligibility-trap`: a locally cheap flexible assignment can occupy the only vehicle
  eligible for another shipment, exposing the greedy baseline's lack of reassignment

Coordinates are invented and converted by the deterministic straight-line test provider into a
complete symmetric matrix at a fixed speed. This is a valid instance of the directed matrix
contract, but it is not road travel and contains no production coordinates or provider responses.

The OR-Tools side uses one named, one-second attempt with parallel cheapest insertion and guided
local search. The dependency version is pinned in `pyproject.toml`. Inputs and the greedy tie-breaks
are deterministic, but elapsed time varies by machine, and a wall-clock search cutoff can produce a
different final objective on different hardware or OR-Tools versions.

With the pinned implementation, `greedy-eligibility-trap` is the intentionally discriminating
case: the joint solver serves both shipments, while the greedy baseline serves only the flexible
shipment and then lacks an eligible seat for the restricted shipment. The other cases establish
parity on straightforward capacity and clustering inputs rather than manufacturing a win in every
row.

## Greedy insertion baseline

The baseline begins with every vehicle traveling directly from its start to the shared destination
and every shipment dropped. On each iteration it examines every remaining shipment, eligible
vehicle, and pickup insertion position. It chooses the lexicographically deterministic candidate
with the greatest immediate objective improvement:

```text
objective delta = added directed travel seconds - avoided drop penalty
```

It applies improving insertions until none remain. Ties are resolved by objective delta, added
travel, shipment id, vehicle id, and insertion position. This is a myopic construction heuristic;
it does not revise an earlier assignment and makes no optimality claim.

The implementation intentionally supports only the benchmark subset:

- every shipment is optional and delivers to the common vehicle destination
- pickup service durations are zero
- there are no time windows, soft time bounds, or route-duration limits
- capacity, shipment size, maximum pickup stops, allowed vehicles, and drop penalties are supported

It raises an error for unsupported inputs rather than silently approximating them. The production
engine supports constraints that this baseline and scenario set do not exercise.

## Reported metrics

Each solver/scenario row reports:

- `served`: served shipments divided by total shipments
- `coverage`: the same ratio as a percentage
- `objective`: directed travel duration plus optional-shipment drop penalties for this subset
- `travel_s`: summed directed matrix duration over all reported routes
- `travel_m`: summed directed matrix distance over all reported routes
- `elapsed_ms`: one wall-clock observation around that solver invocation

OR-Tools objective values come directly from `MatchingResult.diagnostics`. The benchmark separately
recomputes route travel from returned stop order so the travel columns use the same matrix accounting
as the baseline.

Do not use the elapsed column as a throughput or latency claim: there is no warm-up, repetition,
statistical summary, hardware normalization, or production provider call. Do not infer general
solution quality from four small scenarios. The useful comparison is the transparent outcome on
these exact committed inputs.
