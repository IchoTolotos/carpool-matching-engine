"""Run a small synthetic matching problem through the public API."""

from carpool_matching_engine import (
    Coordinate,
    FirstSolutionStrategy,
    LocalSearchMetaheuristic,
    Location,
    MatchingProblem,
    SearchAttempt,
    SearchConfig,
    Shipment,
    Vehicle,
    solve_with_provider,
)
from carpool_matching_engine.testing import StraightLineMatrixProvider


def main() -> None:
    """Solve and print a deterministic synthetic eligibility problem."""
    locations = (
        Location("destination", Coordinate(48.1400, 11.5800)),
        Location("west-start", Coordinate(48.1050, 11.5000)),
        Location("east-start", Coordinate(48.1050, 11.6600)),
        Location("flexible-pickup", Coordinate(48.1180, 11.5250)),
        Location("west-only-pickup", Coordinate(48.1120, 11.4800)),
    )
    problem = MatchingProblem(
        locations=locations,
        vehicles=(
            Vehicle("vehicle-west", "west-start", "destination", capacity=1, max_stops=1),
            Vehicle("vehicle-east", "east-start", "destination", capacity=1, max_stops=1),
        ),
        shipments=(
            Shipment(
                "shipment-flexible",
                "flexible-pickup",
                "destination",
                drop_penalty=100_000,
            ),
            Shipment(
                "shipment-west-only",
                "west-only-pickup",
                "destination",
                allowed_vehicle_ids=("vehicle-west",),
                drop_penalty=100_000,
            ),
        ),
        time_horizon_seconds=7_200,
    )
    search = SearchConfig(
        attempts=(
            SearchAttempt(
                name="example-parallel-guided",
                time_limit_seconds=1,
                first_solution_strategy=FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
                local_search_metaheuristic=LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
            ),
        )
    )

    result = solve_with_provider(problem, StraightLineMatrixProvider(), search)

    for route in result.routes:
        path = " -> ".join(f"{stop.kind.value}:{stop.location_id}" for stop in route.stops)
        shipments = ", ".join(route.shipment_ids) or "none"
        print(f"{route.vehicle_id}: {path} (shipments: {shipments})")
    print(f"dropped: {', '.join(result.dropped_shipment_ids) or 'none'}")
    print(f"objective: {result.diagnostics.objective_value}")


if __name__ == "__main__":
    main()
