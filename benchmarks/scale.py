"""Seeded synthetic scale benchmark for the OR-Tools engine."""

from __future__ import annotations

import argparse
import math
import os
import platform
import random
import statistics
from dataclasses import dataclass
from time import perf_counter

import ortools

from carpool_matching_engine import (
    Coordinate,
    FirstSolutionStrategy,
    LocalSearchMetaheuristic,
    Location,
    MatchingProblem,
    SearchAttempt,
    SearchConfig,
    Shipment,
    TravelMatrix,
    Vehicle,
    solve,
)
from carpool_matching_engine.testing import StraightLineMatrixProvider

_DESTINATION = Coordinate(48.1400, 11.5800)
_DROP_PENALTY = 1_000_000
_HORIZON_SECONDS = 28_800
_SCALE_SPECS = (
    ("small", 4, 16, 4_016),
    ("medium", 8, 32, 8_032),
    ("large", 16, 64, 16_064),
)


@dataclass(frozen=True, slots=True)
class ScaleScenario:
    """One deterministic generated problem and its matrix."""

    name: str
    seed: int
    problem: MatchingProblem
    matrix: TravelMatrix


@dataclass(frozen=True, slots=True)
class ScaleObservation:
    """One bounded solver observation."""

    scenario: str
    vehicles: int
    shipments: int
    served: int
    objective: int
    elapsed_milliseconds: float


@dataclass(frozen=True, slots=True)
class ScaleSummary:
    """Repeated-run statistics for one generated scenario."""

    scenario: str
    vehicles: int
    shipments: int
    served_minimum: int
    served_maximum: int
    objective_best: int
    objective_median: float
    runtime_median_milliseconds: float
    runtime_p95_milliseconds: float


def _random_coordinate(generator: random.Random) -> Coordinate:
    return Coordinate(
        latitude=_DESTINATION.latitude + generator.uniform(-0.09, 0.09),
        longitude=_DESTINATION.longitude + generator.uniform(-0.12, 0.12),
    )


def _build_scale_scenario(
    name: str,
    vehicle_count: int,
    shipment_count: int,
    seed: int,
) -> ScaleScenario:
    generator = random.Random(seed)  # noqa: S311 - deterministic synthetic fixture generation
    seats_per_vehicle = math.ceil(shipment_count / vehicle_count)
    locations = [Location("destination", _DESTINATION)]
    vehicles: list[Vehicle] = []
    shipments: list[Shipment] = []

    for index in range(vehicle_count):
        location_id = f"vehicle-start-{index:02d}"
        locations.append(Location(location_id, _random_coordinate(generator)))
        vehicles.append(
            Vehicle(
                id=f"vehicle-{index:02d}",
                start_location_id=location_id,
                end_location_id="destination",
                capacity=seats_per_vehicle,
                max_stops=seats_per_vehicle,
            )
        )

    for index in range(shipment_count):
        location_id = f"pickup-{index:03d}"
        locations.append(Location(location_id, _random_coordinate(generator)))
        shipments.append(
            Shipment(
                id=f"shipment-{index:03d}",
                pickup_location_id=location_id,
                delivery_location_id="destination",
                drop_penalty=_DROP_PENALTY,
            )
        )

    problem = MatchingProblem(
        locations=tuple(locations),
        vehicles=tuple(vehicles),
        shipments=tuple(shipments),
        time_horizon_seconds=_HORIZON_SECONDS,
    )
    matrix = StraightLineMatrixProvider(speed_kilometers_per_hour=36).build_matrix(
        problem.locations
    )
    return ScaleScenario(name=name, seed=seed, problem=problem, matrix=matrix)


def build_scale_scenarios() -> tuple[ScaleScenario, ...]:
    """Return the stable seeded scale suite."""
    return tuple(_build_scale_scenario(*spec) for spec in _SCALE_SPECS)


def _search_config(seconds_per_run: int) -> SearchConfig:
    return SearchConfig(
        attempts=(
            SearchAttempt(
                name="scale-parallel-guided",
                time_limit_seconds=seconds_per_run,
                first_solution_strategy=FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
                local_search_metaheuristic=LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
            ),
        )
    )


def _run_once(scenario: ScaleScenario, seconds_per_run: int) -> ScaleObservation:
    started_at = perf_counter()
    result = solve(scenario.problem, scenario.matrix, _search_config(seconds_per_run))
    elapsed_milliseconds = (perf_counter() - started_at) * 1_000
    return ScaleObservation(
        scenario=scenario.name,
        vehicles=len(scenario.problem.vehicles),
        shipments=len(scenario.problem.shipments),
        served=len(scenario.problem.shipments) - len(result.dropped_shipment_ids),
        objective=result.diagnostics.objective_value,
        elapsed_milliseconds=elapsed_milliseconds,
    )


def _nearest_rank_p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def _summarize(observations: list[ScaleObservation]) -> ScaleSummary:
    first = observations[0]
    return ScaleSummary(
        scenario=first.scenario,
        vehicles=first.vehicles,
        shipments=first.shipments,
        served_minimum=min(item.served for item in observations),
        served_maximum=max(item.served for item in observations),
        objective_best=min(item.objective for item in observations),
        objective_median=statistics.median(item.objective for item in observations),
        runtime_median_milliseconds=statistics.median(
            item.elapsed_milliseconds for item in observations
        ),
        runtime_p95_milliseconds=_nearest_rank_p95(
            [item.elapsed_milliseconds for item in observations]
        ),
    )


def run_scale_benchmark(*, repetitions: int, seconds_per_run: int) -> tuple[ScaleSummary, ...]:
    """Run every scale case repeatedly and summarize the observations."""
    if repetitions < 1:
        msg = "repetitions must be at least 1"
        raise ValueError(msg)
    if seconds_per_run < 1:
        msg = "seconds per run must be at least 1"
        raise ValueError(msg)

    summaries: list[ScaleSummary] = []
    for scenario in build_scale_scenarios():
        observations = [_run_once(scenario, seconds_per_run) for _ in range(repetitions)]
        summaries.append(_summarize(observations))
    return tuple(summaries)


def _format_table(summaries: tuple[ScaleSummary, ...]) -> str:
    headers = (
        "scenario",
        "vehicles",
        "shipments",
        "served range",
        "best objective",
        "median objective",
        "median ms",
        "p95 ms",
    )
    rows = [
        (
            item.scenario,
            str(item.vehicles),
            str(item.shipments),
            f"{item.served_minimum}-{item.served_maximum}",
            str(item.objective_best),
            f"{item.objective_median:g}",
            f"{item.runtime_median_milliseconds:.2f}",
            f"{item.runtime_p95_milliseconds:.2f}",
        )
        for item in summaries
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]

    def format_row(row: tuple[str, ...]) -> str:
        return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))

    divider = "  ".join("-" * width for width in widths)
    return "\n".join((format_row(headers), divider, *(format_row(row) for row in rows)))


def _hardware_summary(hardware_label: str | None) -> str:
    details = [
        f"platform={platform.platform()}",
        f"architecture={platform.machine()}",
        f"logical_cpus={os.cpu_count() or 'unknown'}",
        f"python={platform.python_version()}",
        f"ortools={ortools.__version__}",
    ]
    if hardware_label is not None:
        details.insert(0, f"hardware={hardware_label}")
    return ", ".join(details)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--seconds-per-run", type=int, default=1)
    parser.add_argument(
        "--hardware-label",
        help="Optional human-readable CPU or machine description recorded with the results.",
    )
    return parser.parse_args()


def main() -> None:
    """Run and print the seeded scale suite."""
    args = _parse_args()
    summaries = run_scale_benchmark(
        repetitions=args.repetitions,
        seconds_per_run=args.seconds_per_run,
    )
    print("Synthetic scale benchmark")
    print(_hardware_summary(args.hardware_label))
    print(
        f"repetitions={args.repetitions}, seconds_per_run={args.seconds_per_run}, p95=nearest-rank"
    )
    print(_format_table(summaries))
    print()
    print("Inputs are seeded and synthetic; wall-clock-bounded solver results can still vary.")
    print(
        "This measures the in-process optimizer only, not routing-provider or application latency."
    )


if __name__ == "__main__":
    main()
