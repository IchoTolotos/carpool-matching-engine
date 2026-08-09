# Carpool Matching Engine

A provider-neutral Python core for jointly assigning passenger shipments to vehicles and ordering
their pickup and delivery stops. It is a technical extraction of matching work developed for
RideAssign, with application policy and routing-provider operations kept outside the package.

> **Status:** private technical extraction. Copyright is all rights reserved. No permission is
> granted to use, copy, modify, publish, distribute, sublicense, or sell this software while a
> future open-source license and public-release scope are under review.

## What it demonstrates

- the application compiles product and business policy into explicit vehicles, shipments,
  constraints, penalties, and a bounded search portfolio
- a provider adapter supplies one complete directed duration-and-distance matrix for every problem
  location
- the core validates those contracts before optimization
- OR-Tools jointly chooses vehicle assignment and pickup/delivery ordering
- capacity, pickup-before-delivery, vehicle eligibility, time windows, stop limits, route-duration
  limits, required shipments, and optional-shipment drop penalties are represented explicitly
- the result contains ordered routes, explicit dropped shipment ids, an objective value, total
  runtime, and diagnostics for every search attempt

The package contains no database access, web framework, authentication, billing, analytics,
application configuration, or routing-vendor SDK. See [the architecture](docs/architecture.md) and
[algorithm boundaries](docs/algorithm.md).

## Correctness boundary

The engine runs a caller-defined sequence of time-bounded OR-Tools search attempts and returns the
best feasible objective they find. A feasible result satisfies the modeled constraints, but a
time-bounded search result is **not proof of global optimality**. The objective also reflects the
policy compiled into costs and penalties; it is not a universal measure of carpool quality.

## Development

Requirements: Python 3.12 through 3.14.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
make check
```

`make check` runs Ruff, strict mypy, deterministic tests, coverage checks, and the package build.

## API sketch

```python
from carpool_matching_engine import (
    Coordinate,
    Location,
    MatchingProblem,
    SearchConfig,
    Shipment,
    Vehicle,
    solve_with_provider,
)

locations = (
    Location("driver-start", Coordinate(48.120, 11.540)),
    Location("pickup", Coordinate(48.130, 11.560)),
    Location("destination", Coordinate(48.140, 11.580)),
)
problem = MatchingProblem(
    locations=locations,
    vehicles=(
        Vehicle(
            id="vehicle-1",
            start_location_id="driver-start",
            end_location_id="destination",
            capacity=3,
        ),
    ),
    shipments=(
        Shipment(
            id="shipment-1",
            pickup_location_id="pickup",
            delivery_location_id="destination",
            required=False,
            drop_penalty=100_000,
        ),
    ),
    time_horizon_seconds=7_200,
)

# Implement MatrixProvider with a production routing adapter. This synthetic helper is only for
# examples and tests and must not be presented as a road-network router.
from carpool_matching_engine.testing import StraightLineMatrixProvider

result = solve_with_provider(
    problem,
    StraightLineMatrixProvider(),
    SearchConfig.balanced(seconds_per_attempt=2),
)
```

`result.routes` contains each vehicle's ordered start, pickup, delivery, and end stops.
`result.dropped_shipment_ids` makes non-service explicit. `result.diagnostics` exposes the selected
objective, total runtime, and solved status, objective, and runtime for each configured attempt.

## Synthetic benchmark

Run the fixed synthetic comparison from the repository root:

```bash
.venv/bin/python -m benchmarks.run
```

It compares the OR-Tools engine with a deterministic greedy insertion baseline and reports
coverage, objective, matrix travel cost, and elapsed time. The baseline intentionally supports only
the benchmark's narrow shared-destination subset, and elapsed times are single-run observations,
not performance claims. Methodology and limitations are documented in
[docs/benchmarking.md](docs/benchmarking.md).

The committed eligibility-trap scenario makes the architectural difference observable: joint
optimization serves both shipments, while the greedy baseline commits the flexible shipment to the
only vehicle eligible for the restricted shipment and serves one of two.

## Data and IP boundary

All committed examples, tests, and benchmarks must be synthetic. Do not add RideAssign customer
data, production coordinates, routing-provider payloads copied from production, credentials,
database schemas, private prompts, or application-specific policy code.

Before making this repository public:

1. confirm company ownership and approval for the extracted algorithm
2. choose and add the intended open-source license
3. complete dependency/license and secret-history scans
4. add public contribution and conduct policies
5. review benchmark methodology and claims for the intended audience
