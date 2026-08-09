"""Provider-neutral input and output models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class Coordinate:
    """A WGS84 coordinate."""

    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class Location:
    """A stable location identifier and coordinate."""

    id: str
    coordinate: Coordinate


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """Inclusive bounds in seconds relative to the caller's epoch."""

    earliest: int | None = None
    latest: int | None = None


@dataclass(frozen=True, slots=True)
class SoftLowerBound:
    """Penalty applied for each second before a preferred time."""

    target: int
    penalty_per_second: int


@dataclass(frozen=True, slots=True)
class Vehicle:
    """A driver's vehicle and route constraints."""

    id: str
    start_location_id: str
    end_location_id: str
    capacity: int
    start_time_window: TimeWindow | None = None
    end_time_window: TimeWindow | None = None
    end_soft_lower_bound: SoftLowerBound | None = None
    max_stops: int | None = None
    max_route_duration_seconds: int | None = None
    max_route_duration_above_direct_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class Shipment:
    """One passenger movement from pickup to delivery."""

    id: str
    pickup_location_id: str
    delivery_location_id: str
    size: int = 1
    pickup_service_seconds: int = 0
    pickup_time_window: TimeWindow | None = None
    delivery_time_window: TimeWindow | None = None
    delivery_soft_lower_bound: SoftLowerBound | None = None
    allowed_vehicle_ids: tuple[str, ...] | None = None
    required: bool = False
    drop_penalty: int = 1_000_000


@dataclass(frozen=True, slots=True)
class MatchingProblem:
    """A complete, application-independent vehicle-routing problem."""

    locations: tuple[Location, ...]
    vehicles: tuple[Vehicle, ...]
    shipments: tuple[Shipment, ...]
    time_horizon_seconds: int


class StopKind(StrEnum):
    """Kinds of stops returned in solved routes."""

    START = "start"
    PICKUP = "pickup"
    DELIVERY = "delivery"
    END = "end"


@dataclass(frozen=True, slots=True)
class RouteStop:
    """A visited stop and its solved arrival time."""

    kind: StopKind
    location_id: str
    arrival_seconds: int
    shipment_id: str | None = None


@dataclass(frozen=True, slots=True)
class SolvedRoute:
    """One vehicle's solved route."""

    vehicle_id: str
    stops: tuple[RouteStop, ...]
    shipment_ids: tuple[str, ...]
    duration_seconds: int
    distance_meters: int
    direct_duration_seconds: int
    direct_distance_meters: int


@dataclass(frozen=True, slots=True)
class SearchAttemptResult:
    """Diagnostics for one search strategy."""

    name: str
    solved: bool
    objective_value: int | None
    duration_milliseconds: float


@dataclass(frozen=True, slots=True)
class MatchingDiagnostics:
    """Solver diagnostics that make quality and runtime observable."""

    objective_value: int
    duration_milliseconds: float
    attempts: tuple[SearchAttemptResult, ...]


@dataclass(frozen=True, slots=True)
class MatchingResult:
    """Solved routes, explicit drops, and search diagnostics."""

    routes: tuple[SolvedRoute, ...]
    dropped_shipment_ids: tuple[str, ...]
    diagnostics: MatchingDiagnostics
