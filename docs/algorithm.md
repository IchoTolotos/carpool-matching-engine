# Algorithm and correctness boundaries

## Problem model

The engine assigns passengers to drivers traveling toward one shared destination. Drivers have a
fixed seat capacity. Passengers may be pinned to a driver, and both participant types may belong to
groups governed by one explicit compatibility policy.

Pinned passengers form part of a driver's required baseline route. The detour constraint therefore
measures the incremental cost of optional passengers against commitments already made to that
driver. It does not silently reinterpret or remove pinned assignments.

## Stages

### 1. Validation

Participant ids, coordinates, capacities, constraints, pinned references, group compatibility, and
execution limits are validated before routing begins. Invalid state is rejected with a stable error
code.

### 2. Baselines and candidate edges

The routing provider builds one baseline per driver. Each unpinned passenger is projected onto that
baseline geometry. The engine calculates:

- perpendicular pickup distance to the route
- progress along the route
- a lower bound on added travel time, using the passenger-to-destination duration and the remaining
  baseline duration at the projection point

Natural-carpool mode discards edges outside the pickup radius or lower-bound detour limit. Full
coverage mode keeps every group-compatible edge and lets real-route validation decide feasibility.

### 3. Minimum-cost maximum flow

The assignment graph contains source-to-passenger edges, passenger-to-driver candidate edges, and
driver-to-sink capacity edges. Successive shortest augmenting paths with reduced-cost potentials
maximize assigned passenger count and then minimize total integer candidate cost.

For `P` passengers, `D` drivers, and `E` candidate edges, each augmentation uses Dijkstra over the
residual graph. The practical upper bound is `O(P * E log(P + D))` for unit passenger demand.

### 4. Real-route validation and repair

The routing provider orders assigned stops and returns the route duration. When a route exceeds the
detour limit, the engine evaluates removing each optional passenger on that route, blacklists the
edge with the largest measured duration gain, and solves the flow problem again. Every repair and
routing call is bounded by caller-supplied limits.

Natural-carpool mode may return unassigned passengers. Full-coverage mode throws when any passenger
cannot be placed. Exhausted repair or routing-call budgets also throw; there is no partial hidden
fallback.

## What is and is not optimal

The min-cost-flow assignment is exact for the generated candidate graph and cost function. The
complete routing problem is not globally optimized: candidate costs are lower-bound surrogates, and
the route-repair phase is a deterministic bounded heuristic. Public benchmarks should therefore
compare the complete outcome against explicit baselines rather than describing the engine as a
globally optimal vehicle-routing solver.
