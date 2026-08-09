"""Validation for public models and provider-supplied matrices."""

from __future__ import annotations

import math
from collections.abc import Iterable

from .errors import ErrorCode, MatchingEngineError
from .matrix import TravelMatrix
from .models import MatchingProblem, Shipment, SoftLowerBound, TimeWindow
from .search_config import SearchConfig

_MIN_LATITUDE = -90
_MAX_LATITUDE = 90
_MIN_LONGITUDE = -180
_MAX_LONGITUDE = 180


def _fail(message: str, **context: object) -> None:
    raise MatchingEngineError(ErrorCode.INVALID_PROBLEM, message, **context)


def _assert_unique(values: Iterable[str], *, kind: str) -> set[str]:
    seen: set[str] = set()
    for value in values:
        if not value:
            _fail(f"{kind} ids must not be empty.")
        if value in seen:
            _fail(f"Duplicate {kind} id.", duplicate_id=value)
        seen.add(value)
    return seen


def _validate_window(window: TimeWindow | None, *, horizon: int, owner: str) -> None:
    if window is None:
        return
    earliest = window.earliest if window.earliest is not None else 0
    latest = window.latest if window.latest is not None else horizon
    if earliest < 0 or latest < 0 or earliest > horizon or latest > horizon:
        _fail("Time window falls outside the problem horizon.", owner=owner)
    if earliest > latest:
        _fail("Time window earliest bound exceeds latest bound.", owner=owner)


def _validate_soft_bound(
    bound: SoftLowerBound | None,
    *,
    horizon: int,
    owner: str,
) -> None:
    if bound is None:
        return
    if not 0 <= bound.target <= horizon:
        _fail("Soft lower bound falls outside the problem horizon.", owner=owner)
    if bound.penalty_per_second <= 0:
        _fail("Soft lower-bound penalty must be positive.", owner=owner)


def _validate_locations(problem: MatchingProblem) -> set[str]:
    location_ids = _assert_unique((location.id for location in problem.locations), kind="location")
    for location in problem.locations:
        coordinate = location.coordinate
        if not math.isfinite(coordinate.latitude) or not math.isfinite(coordinate.longitude):
            _fail("Coordinates must be finite.", location_id=location.id)
        if not _MIN_LATITUDE <= coordinate.latitude <= _MAX_LATITUDE or not (
            _MIN_LONGITUDE <= coordinate.longitude <= _MAX_LONGITUDE
        ):
            _fail("Coordinate falls outside WGS84 bounds.", location_id=location.id)
    return location_ids


def _validate_vehicles(problem: MatchingProblem, location_ids: set[str]) -> set[str]:
    vehicle_ids = _assert_unique((vehicle.id for vehicle in problem.vehicles), kind="vehicle")
    for vehicle in problem.vehicles:
        missing_locations = {
            vehicle.start_location_id,
            vehicle.end_location_id,
        } - location_ids
        if missing_locations:
            _fail(
                "Vehicle references unknown locations.",
                vehicle_id=vehicle.id,
                location_ids=sorted(missing_locations),
            )
        if vehicle.capacity <= 0:
            _fail("Vehicle capacity must be positive.", vehicle_id=vehicle.id)
        if vehicle.max_stops is not None and vehicle.max_stops < 0:
            _fail("Vehicle max_stops must not be negative.", vehicle_id=vehicle.id)
        if (
            vehicle.max_route_duration_seconds is not None
            and vehicle.max_route_duration_seconds <= 0
        ):
            _fail("Vehicle maximum route duration must be positive.", vehicle_id=vehicle.id)
        if (
            vehicle.max_route_duration_above_direct_seconds is not None
            and vehicle.max_route_duration_above_direct_seconds < 0
        ):
            _fail("Vehicle over-direct allowance must not be negative.", vehicle_id=vehicle.id)
        _validate_window(
            vehicle.start_time_window,
            horizon=problem.time_horizon_seconds,
            owner=f"vehicle:{vehicle.id}:start",
        )
        _validate_window(
            vehicle.end_time_window,
            horizon=problem.time_horizon_seconds,
            owner=f"vehicle:{vehicle.id}:end",
        )
        _validate_soft_bound(
            vehicle.end_soft_lower_bound,
            horizon=problem.time_horizon_seconds,
            owner=f"vehicle:{vehicle.id}:end",
        )
    return vehicle_ids


def _validate_shipments(
    problem: MatchingProblem,
    location_ids: set[str],
    vehicle_ids: set[str],
) -> None:
    _assert_unique((shipment.id for shipment in problem.shipments), kind="shipment")
    for shipment in problem.shipments:
        missing_locations = {
            shipment.pickup_location_id,
            shipment.delivery_location_id,
        } - location_ids
        if missing_locations:
            _fail(
                "Shipment references unknown locations.",
                shipment_id=shipment.id,
                location_ids=sorted(missing_locations),
            )
        if shipment.size <= 0:
            _fail("Shipment size must be positive.", shipment_id=shipment.id)
        if shipment.pickup_service_seconds < 0:
            _fail("Pickup service duration must not be negative.", shipment_id=shipment.id)
        if not shipment.required and shipment.drop_penalty <= 0:
            _fail("Optional shipment drop penalty must be positive.", shipment_id=shipment.id)
        _validate_allowed_vehicles(shipment, vehicle_ids)
        _validate_window(
            shipment.pickup_time_window,
            horizon=problem.time_horizon_seconds,
            owner=f"shipment:{shipment.id}:pickup",
        )
        _validate_window(
            shipment.delivery_time_window,
            horizon=problem.time_horizon_seconds,
            owner=f"shipment:{shipment.id}:delivery",
        )
        _validate_soft_bound(
            shipment.delivery_soft_lower_bound,
            horizon=problem.time_horizon_seconds,
            owner=f"shipment:{shipment.id}:delivery",
        )


def _validate_allowed_vehicles(shipment: Shipment, vehicle_ids: set[str]) -> None:
    allowed_vehicle_ids = shipment.allowed_vehicle_ids
    shipment_id = shipment.id
    if allowed_vehicle_ids is None:
        return
    if not allowed_vehicle_ids:
        _fail("allowed_vehicle_ids must not be empty.", shipment_id=shipment_id)
    allowed = set(allowed_vehicle_ids)
    if len(allowed) != len(allowed_vehicle_ids):
        _fail("allowed_vehicle_ids must be unique.", shipment_id=shipment_id)
    unknown = allowed - vehicle_ids
    if unknown:
        _fail(
            "Shipment references unknown allowed vehicles.",
            shipment_id=shipment_id,
            vehicle_ids=sorted(unknown),
        )


def _validate_search(search_config: SearchConfig) -> None:
    if not search_config.attempts:
        _fail("At least one search attempt is required.")
    _assert_unique((attempt.name for attempt in search_config.attempts), kind="search attempt")
    for attempt in search_config.attempts:
        if attempt.time_limit_seconds <= 0:
            _fail("Search attempt time limit must be positive.", attempt=attempt.name)


def validate_problem(problem: MatchingProblem, search_config: SearchConfig) -> None:
    """Reject impossible or ambiguous caller input before optimization."""
    if problem.time_horizon_seconds <= 0:
        _fail("time_horizon_seconds must be positive.")
    if not problem.vehicles:
        _fail("At least one vehicle is required.")
    location_ids = _validate_locations(problem)
    vehicle_ids = _validate_vehicles(problem, location_ids)
    _validate_shipments(problem, location_ids, vehicle_ids)
    _validate_search(search_config)


def validate_matrix(problem: MatchingProblem, matrix: TravelMatrix) -> None:
    """Validate the complete matrix contract before OR-Tools sees it."""
    expected_ids = {location.id for location in problem.locations}
    actual_ids = set(matrix.location_ids)
    if len(actual_ids) != len(matrix.location_ids) or actual_ids != expected_ids:
        raise MatchingEngineError(
            ErrorCode.INVALID_MATRIX,
            "Matrix location ids must match the problem locations exactly.",
            missing_location_ids=sorted(expected_ids - actual_ids),
            unexpected_location_ids=sorted(actual_ids - expected_ids),
        )

    expected_size = len(matrix.location_ids)
    for name, rows in (
        ("durations_seconds", matrix.durations_seconds),
        ("distances_meters", matrix.distances_meters),
    ):
        if len(rows) != expected_size or any(len(row) != expected_size for row in rows):
            raise MatchingEngineError(
                ErrorCode.INVALID_MATRIX,
                f"{name} must be a square matrix.",
                expected_size=expected_size,
            )
        _validate_matrix_rows(name, rows)


def _validate_matrix_rows(name: str, rows: tuple[tuple[int, ...], ...]) -> None:
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise MatchingEngineError(
                    ErrorCode.INVALID_MATRIX,
                    f"{name} entries must be non-negative integers.",
                    row=row_index,
                    column=column_index,
                )
            if row_index == column_index and value != 0:
                raise MatchingEngineError(
                    ErrorCode.INVALID_MATRIX,
                    f"{name} diagonal entries must be zero.",
                    row=row_index,
                )
