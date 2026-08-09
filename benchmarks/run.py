"""Command-line entry point for the fixed synthetic benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from time import perf_counter

from benchmarks.baseline import solve_greedily
from benchmarks.scenarios import BenchmarkScenario, build_scenarios
from carpool_matching_engine import (
    FirstSolutionStrategy,
    LocalSearchMetaheuristic,
    MatchingResult,
    SearchAttempt,
    SearchConfig,
    TravelMatrix,
    solve,
)

_ATTEMPT_SECONDS = 1


@dataclass(frozen=True, slots=True)
class _ReportRow:
    scenario: str
    solver: str
    served: int
    total: int
    objective: int
    travel_seconds: int
    travel_meters: int
    elapsed_milliseconds: float


def _engine_config() -> SearchConfig:
    return SearchConfig(
        attempts=(
            SearchAttempt(
                name="benchmark-parallel-guided",
                time_limit_seconds=_ATTEMPT_SECONDS,
                first_solution_strategy=FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
                local_search_metaheuristic=LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
            ),
        )
    )


def _engine_travel(result: MatchingResult, matrix: TravelMatrix) -> tuple[int, int]:
    duration = 0
    distance = 0
    for route in result.routes:
        for origin, destination in pairwise(route.stops):
            duration += matrix.duration(origin.location_id, destination.location_id)
            distance += matrix.distance(origin.location_id, destination.location_id)
    return duration, distance


def _run_engine(scenario: BenchmarkScenario) -> _ReportRow:
    started_at = perf_counter()
    result = solve(scenario.problem, scenario.matrix, _engine_config())
    elapsed_milliseconds = (perf_counter() - started_at) * 1_000
    travel_seconds, travel_meters = _engine_travel(result, scenario.matrix)
    return _ReportRow(
        scenario=scenario.name,
        solver="OR-Tools",
        served=len(scenario.problem.shipments) - len(result.dropped_shipment_ids),
        total=len(scenario.problem.shipments),
        objective=result.diagnostics.objective_value,
        travel_seconds=travel_seconds,
        travel_meters=travel_meters,
        elapsed_milliseconds=elapsed_milliseconds,
    )


def _run_greedy(scenario: BenchmarkScenario) -> _ReportRow:
    started_at = perf_counter()
    result = solve_greedily(scenario.problem, scenario.matrix)
    elapsed_milliseconds = (perf_counter() - started_at) * 1_000
    return _ReportRow(
        scenario=scenario.name,
        solver="greedy",
        served=len(result.served_shipment_ids),
        total=len(scenario.problem.shipments),
        objective=result.objective_value,
        travel_seconds=result.travel_duration_seconds,
        travel_meters=result.travel_distance_meters,
        elapsed_milliseconds=elapsed_milliseconds,
    )


def _format_table(rows: list[_ReportRow]) -> str:
    headers = (
        "scenario",
        "solver",
        "served",
        "coverage",
        "objective",
        "travel_s",
        "travel_m",
        "elapsed_ms",
    )
    values = [
        (
            row.scenario,
            row.solver,
            f"{row.served}/{row.total}",
            f"{100 * row.served / row.total:.1f}%",
            str(row.objective),
            str(row.travel_seconds),
            str(row.travel_meters),
            f"{row.elapsed_milliseconds:.2f}",
        )
        for row in rows
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in values))
        for index in range(len(headers))
    ]

    def format_row(row: tuple[str, ...]) -> str:
        return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))

    divider = "  ".join("-" * width for width in widths)
    return "\n".join((format_row(headers), divider, *(format_row(row) for row in values)))


def main() -> None:
    """Run both solvers on every fixed scenario and print comparable metrics."""
    rows: list[_ReportRow] = []
    for scenario in build_scenarios():
        rows.extend((_run_engine(scenario), _run_greedy(scenario)))

    print("Synthetic benchmark: fixed shared-destination scenarios")
    print(_format_table(rows))
    print()
    print("OR-Tools search: one 1-second bounded attempt; feasible is not globally optimal proof.")
    print("Elapsed times are single-run observations, not throughput or latency claims.")
    print(
        "Greedy baseline supports only the documented benchmark subset; see docs/benchmarking.md."
    )


if __name__ == "__main__":
    main()
