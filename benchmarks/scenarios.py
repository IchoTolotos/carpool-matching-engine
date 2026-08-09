"""Fixed synthetic scenarios for the public benchmark."""

from __future__ import annotations

from dataclasses import dataclass

from carpool_matching_engine import (
    Coordinate,
    Location,
    MatchingProblem,
    Shipment,
    TravelMatrix,
    Vehicle,
)
from carpool_matching_engine.testing import StraightLineMatrixProvider

_DESTINATION = (48.1400, 11.5800)
_HORIZON_SECONDS = 14_400
_DROP_PENALTY = 100_000


@dataclass(frozen=True, slots=True)
class BenchmarkScenario:
    """One named synthetic problem and its fixed generated matrix."""

    name: str
    description: str
    problem: MatchingProblem
    matrix: TravelMatrix


def _location(location_id: str, latitude: float, longitude: float) -> Location:
    return Location(location_id, Coordinate(latitude, longitude))


def _scenario(
    *,
    name: str,
    description: str,
    locations: tuple[Location, ...],
    vehicles: tuple[Vehicle, ...],
    shipments: tuple[Shipment, ...],
) -> BenchmarkScenario:
    problem = MatchingProblem(
        locations=locations,
        vehicles=vehicles,
        shipments=shipments,
        time_horizon_seconds=_HORIZON_SECONDS,
    )
    matrix = StraightLineMatrixProvider(speed_kilometers_per_hour=36).build_matrix(locations)
    return BenchmarkScenario(name, description, problem, matrix)


def _balanced_clusters() -> BenchmarkScenario:
    locations = (
        _location("destination", *_DESTINATION),
        _location("west-start", 48.1050, 11.5000),
        _location("east-start", 48.1050, 11.6600),
        _location("west-1", 48.1120, 11.5150),
        _location("west-2", 48.1210, 11.5350),
        _location("west-3", 48.1300, 11.5550),
        _location("east-1", 48.1120, 11.6450),
        _location("east-2", 48.1210, 11.6250),
        _location("east-3", 48.1300, 11.6050),
    )
    vehicles = (
        Vehicle("vehicle-west", "west-start", "destination", capacity=3, max_stops=3),
        Vehicle("vehicle-east", "east-start", "destination", capacity=3, max_stops=3),
    )
    shipments = tuple(
        Shipment(
            id=f"shipment-{side}-{index}",
            pickup_location_id=f"{side}-{index}",
            delivery_location_id="destination",
            drop_penalty=_DROP_PENALTY,
        )
        for side in ("west", "east")
        for index in range(1, 4)
    )
    return _scenario(
        name="balanced-clusters",
        description="Two pickup clusters with enough seats for full coverage.",
        locations=locations,
        vehicles=vehicles,
        shipments=shipments,
    )


def _capacity_pressure() -> BenchmarkScenario:
    locations = (
        _location("destination", *_DESTINATION),
        _location("north-start", 48.1900, 11.5800),
        _location("south-start", 48.0900, 11.5800),
        _location("north-1", 48.1800, 11.5700),
        _location("north-2", 48.1650, 11.5850),
        _location("north-3", 48.1550, 11.6000),
        _location("south-1", 48.1000, 11.5700),
        _location("south-2", 48.1150, 11.5850),
        _location("south-3", 48.1250, 11.6000),
    )
    vehicles = (
        Vehicle("vehicle-north", "north-start", "destination", capacity=2, max_stops=2),
        Vehicle("vehicle-south", "south-start", "destination", capacity=2, max_stops=2),
    )
    shipments = tuple(
        Shipment(
            id=f"shipment-{side}-{index}",
            pickup_location_id=f"{side}-{index}",
            delivery_location_id="destination",
            drop_penalty=_DROP_PENALTY,
        )
        for side in ("north", "south")
        for index in range(1, 4)
    )
    return _scenario(
        name="capacity-pressure",
        description="Four seats for six optional shipments.",
        locations=locations,
        vehicles=vehicles,
        shipments=shipments,
    )


def _vehicle_eligibility() -> BenchmarkScenario:
    locations = (
        _location("destination", *_DESTINATION),
        _location("west-start", 48.1050, 11.5000),
        _location("east-start", 48.1050, 11.6600),
        _location("pickup-west-only", 48.1200, 11.5250),
        _location("pickup-east-only", 48.1200, 11.6350),
        _location("pickup-flex-1", 48.1250, 11.5700),
        _location("pickup-flex-2", 48.1300, 11.5900),
    )
    vehicles = (
        Vehicle("vehicle-west", "west-start", "destination", capacity=2, max_stops=2),
        Vehicle("vehicle-east", "east-start", "destination", capacity=2, max_stops=2),
    )
    shipments = (
        Shipment(
            "shipment-west-only",
            "pickup-west-only",
            "destination",
            allowed_vehicle_ids=("vehicle-west",),
            drop_penalty=_DROP_PENALTY,
        ),
        Shipment(
            "shipment-east-only",
            "pickup-east-only",
            "destination",
            allowed_vehicle_ids=("vehicle-east",),
            drop_penalty=_DROP_PENALTY,
        ),
        Shipment(
            "shipment-flex-1",
            "pickup-flex-1",
            "destination",
            drop_penalty=_DROP_PENALTY,
        ),
        Shipment(
            "shipment-flex-2",
            "pickup-flex-2",
            "destination",
            drop_penalty=_DROP_PENALTY,
        ),
    )
    return _scenario(
        name="vehicle-eligibility",
        description="Eligibility restrictions constrain two flexible assignments.",
        locations=locations,
        vehicles=vehicles,
        shipments=shipments,
    )


def _greedy_eligibility_trap() -> BenchmarkScenario:
    locations = (
        _location("destination", *_DESTINATION),
        _location("west-start", 48.1050, 11.5000),
        _location("east-start", 48.1050, 11.6600),
        _location("flexible-pickup", 48.1180, 11.5250),
        _location("west-only-pickup", 48.1120, 11.4800),
    )
    vehicles = (
        Vehicle("vehicle-west", "west-start", "destination", capacity=1, max_stops=1),
        Vehicle("vehicle-east", "east-start", "destination", capacity=1, max_stops=1),
    )
    shipments = (
        Shipment(
            "shipment-flexible",
            "flexible-pickup",
            "destination",
            drop_penalty=_DROP_PENALTY,
        ),
        Shipment(
            "shipment-west-only",
            "west-only-pickup",
            "destination",
            allowed_vehicle_ids=("vehicle-west",),
            drop_penalty=_DROP_PENALTY,
        ),
    )
    return _scenario(
        name="greedy-eligibility-trap",
        description="A locally cheap flexible assignment can block a restricted shipment.",
        locations=locations,
        vehicles=vehicles,
        shipments=shipments,
    )


def build_scenarios() -> tuple[BenchmarkScenario, ...]:
    """Return benchmark scenarios in stable report order."""
    return (
        _balanced_clusters(),
        _capacity_pressure(),
        _vehicle_eligibility(),
        _greedy_eligibility_trap(),
    )
