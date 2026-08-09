from __future__ import annotations

from carpool_matching_engine import (
    Coordinate,
    FirstSolutionStrategy,
    LocalSearchMetaheuristic,
    Location,
    SearchAttempt,
    SearchConfig,
    TravelMatrix,
)


def make_locations(*location_ids: str) -> tuple[Location, ...]:
    return tuple(
        Location(
            id=location_id,
            coordinate=Coordinate(latitude=0.0, longitude=index / 1_000),
        )
        for index, location_id in enumerate(location_ids)
    )


def make_matrix(
    location_ids: tuple[str, ...],
    durations_seconds: tuple[tuple[int, ...], ...],
) -> TravelMatrix:
    return TravelMatrix(
        location_ids=location_ids,
        durations_seconds=durations_seconds,
        distances_meters=tuple(
            tuple(duration * 10 for duration in row) for row in durations_seconds
        ),
    )


def make_line_matrix(
    location_ids: tuple[str, ...],
    positions: tuple[int, ...] | None = None,
) -> TravelMatrix:
    resolved_positions = positions if positions is not None else tuple(range(len(location_ids)))
    durations = tuple(
        tuple(abs(origin - destination) for destination in resolved_positions)
        for origin in resolved_positions
    )
    return make_matrix(location_ids, durations)


def one_second_search(*, name: str = "deterministic-test") -> SearchConfig:
    return SearchConfig(
        attempts=(
            SearchAttempt(
                name=name,
                time_limit_seconds=1,
                first_solution_strategy=FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
                local_search_metaheuristic=LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
            ),
        )
    )
