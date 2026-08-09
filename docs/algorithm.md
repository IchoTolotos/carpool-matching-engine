# Algorithm and correctness boundaries

## Problem model

The public model is an application-independent pickup-and-delivery problem:

- `Vehicle` defines start and end locations, capacity, optional time windows, stop limits, and
  absolute or over-direct route-duration limits.
- `Shipment` defines pickup and delivery locations, demand size, pickup service time, optional time
  windows and soft delivery targets, allowed vehicles, and whether dropping is forbidden or
  penalized.
- `TravelMatrix` provides directed duration and distance for every ordered pair of problem
  locations.
- `SearchConfig` defines one or more named, time-bounded OR-Tools attempts.

Application concepts such as groups, pinned assignments, eligibility policy, service tiers, or
product-specific priorities are not inferred by the core. The application compiles them into the
public constraints, allowed-vehicle sets, required flags, penalties, and search configuration.

## Solve stages

### 1. Validate explicit contracts

The engine rejects malformed participant ids, locations, coordinates, capacities, time bounds,
eligibility references, penalties, search attempts, and matrices before invoking OR-Tools. The
matrix location set must exactly match the problem location set; duration and distance tables must
both be square and contain non-negative integer values with zero diagonals.

### 2. Build one pickup-and-delivery model

The OR-Tools routing model contains a start and end node for every vehicle and paired pickup and
delivery nodes for every shipment. Assignment and ordering are decision variables in the same
model. Constraints enforce:

- pickup and delivery on the same vehicle, with pickup no later than delivery
- vehicle capacity over the route
- shipment-to-vehicle eligibility
- vehicle, pickup, and delivery time windows
- maximum pickup-stop counts
- absolute and over-direct route-duration limits
- required shipment service or explicit optional-shipment dropping

Directed matrix duration plus pickup service time is the arc cost and the time-dimension transit.
Optional shipment drops and soft lower time bounds add their configured penalties. Matrix distance
does not affect the objective; it is accumulated for result reporting.

### 3. Run the bounded search portfolio

Every configured attempt builds an independent model and runs its named first-solution strategy and
local-search metaheuristic for its time limit. The engine records whether each attempt solved, its
objective when available, and its elapsed time. The feasible attempt with the lowest objective is
selected. If none is feasible within the configured attempts, the engine raises `NO_SOLUTION`; it
does not silently return a partial result or switch algorithms.

### 4. Extract explicit results

For every vehicle, the result includes ordered start, pickup, delivery, and end stops with solved
arrival times, served shipment ids, route duration and distance, and direct-route duration and
distance. Dropped shipment ids are returned separately. Top-level diagnostics contain the selected
objective, total portfolio runtime, and every per-attempt diagnostic.

## What is and is not proven

A returned route set is feasible for the validated model and supplied matrix. The selected
objective is the best value found by the configured attempts.

It is not a certificate of global optimality. OR-Tools routing uses constructive and local-search
strategies here, and every attempt is stopped by a wall-clock limit. A longer or different search
portfolio may find a lower objective. Results can also only be as representative as the application
policy and travel matrix supplied to the core.

The synthetic benchmark therefore reports observed outcomes against a named baseline. It does not
describe the engine as globally optimal and does not generalize fixed synthetic results to
production demand or road networks.
