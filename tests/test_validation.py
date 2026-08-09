from __future__ import annotations

import math
from dataclasses import replace

import pytest

from carpool_matching_engine import (
    Coordinate,
    ErrorCode,
    MatchingEngineError,
    MatchingProblem,
    SearchConfig,
    Shipment,
    SoftLowerBound,
    TimeWindow,
    TravelMatrix,
    Vehicle,
    solve,
)
from tests.helpers import make_line_matrix, make_locations, one_second_search

LOCATIONS = make_locations("a", "b", "c")
VEHICLE = Vehicle("car", "a", "c", capacity=2)
SHIPMENT = Shipment("rider", "a", "b")
VALID_PROBLEM = MatchingProblem(
    locations=LOCATIONS,
    vehicles=(VEHICLE,),
    shipments=(SHIPMENT,),
    time_horizon_seconds=100,
)
VALID_MATRIX = make_line_matrix(("a", "b", "c"))
VALID_SEARCH = one_second_search()
VALID_ATTEMPT = VALID_SEARCH.attempts[0]


INVALID_PROBLEM_CASES = [
    pytest.param(replace(VALID_PROBLEM, time_horizon_seconds=0), VALID_SEARCH, id="zero-horizon"),
    pytest.param(replace(VALID_PROBLEM, vehicles=()), VALID_SEARCH, id="no-vehicles"),
    pytest.param(
        replace(
            VALID_PROBLEM, locations=(LOCATIONS[0], replace(LOCATIONS[1], id="a"), LOCATIONS[2])
        ),
        VALID_SEARCH,
        id="duplicate-location",
    ),
    pytest.param(
        replace(VALID_PROBLEM, locations=(replace(LOCATIONS[0], id=""), *LOCATIONS[1:])),
        VALID_SEARCH,
        id="empty-location-id",
    ),
    pytest.param(
        replace(
            VALID_PROBLEM,
            locations=(replace(LOCATIONS[0], coordinate=Coordinate(math.inf, 0)), *LOCATIONS[1:]),
        ),
        VALID_SEARCH,
        id="non-finite-coordinate",
    ),
    pytest.param(
        replace(
            VALID_PROBLEM,
            locations=(replace(LOCATIONS[0], coordinate=Coordinate(91, 0)), *LOCATIONS[1:]),
        ),
        VALID_SEARCH,
        id="out-of-bounds-coordinate",
    ),
    pytest.param(
        replace(VALID_PROBLEM, vehicles=(VEHICLE, replace(VEHICLE))),
        VALID_SEARCH,
        id="duplicate-vehicle",
    ),
    pytest.param(
        replace(VALID_PROBLEM, vehicles=(replace(VEHICLE, start_location_id="missing"),)),
        VALID_SEARCH,
        id="unknown-vehicle-location",
    ),
    pytest.param(
        replace(VALID_PROBLEM, vehicles=(replace(VEHICLE, capacity=0),)),
        VALID_SEARCH,
        id="zero-capacity",
    ),
    pytest.param(
        replace(VALID_PROBLEM, vehicles=(replace(VEHICLE, max_stops=-1),)),
        VALID_SEARCH,
        id="negative-max-stops",
    ),
    pytest.param(
        replace(VALID_PROBLEM, vehicles=(replace(VEHICLE, max_route_duration_seconds=0),)),
        VALID_SEARCH,
        id="zero-route-duration",
    ),
    pytest.param(
        replace(
            VALID_PROBLEM,
            vehicles=(replace(VEHICLE, max_route_duration_above_direct_seconds=-1),),
        ),
        VALID_SEARCH,
        id="negative-over-direct-duration",
    ),
    pytest.param(
        replace(
            VALID_PROBLEM,
            vehicles=(replace(VEHICLE, start_time_window=TimeWindow(earliest=-1)),),
        ),
        VALID_SEARCH,
        id="vehicle-window-outside-horizon",
    ),
    pytest.param(
        replace(
            VALID_PROBLEM,
            vehicles=(replace(VEHICLE, end_time_window=TimeWindow(earliest=20, latest=10)),),
        ),
        VALID_SEARCH,
        id="vehicle-window-reversed",
    ),
    pytest.param(
        replace(
            VALID_PROBLEM,
            vehicles=(
                replace(
                    VEHICLE,
                    end_soft_lower_bound=SoftLowerBound(target=101, penalty_per_second=1),
                ),
            ),
        ),
        VALID_SEARCH,
        id="vehicle-soft-bound-outside-horizon",
    ),
    pytest.param(
        replace(
            VALID_PROBLEM,
            vehicles=(
                replace(
                    VEHICLE,
                    end_soft_lower_bound=SoftLowerBound(target=50, penalty_per_second=0),
                ),
            ),
        ),
        VALID_SEARCH,
        id="vehicle-soft-bound-zero-penalty",
    ),
    pytest.param(
        replace(VALID_PROBLEM, shipments=(SHIPMENT, replace(SHIPMENT))),
        VALID_SEARCH,
        id="duplicate-shipment",
    ),
    pytest.param(
        replace(VALID_PROBLEM, shipments=(replace(SHIPMENT, delivery_location_id="missing"),)),
        VALID_SEARCH,
        id="unknown-shipment-location",
    ),
    pytest.param(
        replace(VALID_PROBLEM, shipments=(replace(SHIPMENT, size=0),)),
        VALID_SEARCH,
        id="zero-shipment-size",
    ),
    pytest.param(
        replace(VALID_PROBLEM, shipments=(replace(SHIPMENT, pickup_service_seconds=-1),)),
        VALID_SEARCH,
        id="negative-pickup-service",
    ),
    pytest.param(
        replace(VALID_PROBLEM, shipments=(replace(SHIPMENT, drop_penalty=0),)),
        VALID_SEARCH,
        id="zero-drop-penalty",
    ),
    pytest.param(
        replace(VALID_PROBLEM, shipments=(replace(SHIPMENT, allowed_vehicle_ids=()),)),
        VALID_SEARCH,
        id="empty-allowed-vehicles",
    ),
    pytest.param(
        replace(
            VALID_PROBLEM,
            shipments=(replace(SHIPMENT, allowed_vehicle_ids=("car", "car")),),
        ),
        VALID_SEARCH,
        id="duplicate-allowed-vehicles",
    ),
    pytest.param(
        replace(
            VALID_PROBLEM,
            shipments=(replace(SHIPMENT, allowed_vehicle_ids=("missing",)),),
        ),
        VALID_SEARCH,
        id="unknown-allowed-vehicle",
    ),
    pytest.param(
        replace(
            VALID_PROBLEM,
            shipments=(replace(SHIPMENT, pickup_time_window=TimeWindow(latest=101)),),
        ),
        VALID_SEARCH,
        id="shipment-window-outside-horizon",
    ),
    pytest.param(
        replace(
            VALID_PROBLEM,
            shipments=(
                replace(
                    SHIPMENT,
                    delivery_soft_lower_bound=SoftLowerBound(target=50, penalty_per_second=-1),
                ),
            ),
        ),
        VALID_SEARCH,
        id="shipment-soft-bound-negative-penalty",
    ),
    pytest.param(VALID_PROBLEM, SearchConfig(attempts=()), id="no-search-attempts"),
    pytest.param(
        VALID_PROBLEM,
        SearchConfig(attempts=(VALID_ATTEMPT, replace(VALID_ATTEMPT))),
        id="duplicate-search-attempt",
    ),
    pytest.param(
        VALID_PROBLEM,
        SearchConfig(attempts=(replace(VALID_ATTEMPT, name=""),)),
        id="empty-search-attempt-name",
    ),
    pytest.param(
        VALID_PROBLEM,
        SearchConfig(attempts=(replace(VALID_ATTEMPT, time_limit_seconds=0),)),
        id="zero-search-time-limit",
    ),
]


@pytest.mark.parametrize(("problem", "search_config"), INVALID_PROBLEM_CASES)
def test_invalid_problem_has_stable_error_code(
    problem: MatchingProblem,
    search_config: SearchConfig,
) -> None:
    with pytest.raises(MatchingEngineError) as raised:
        solve(problem, VALID_MATRIX, search_config)

    assert raised.value.code is ErrorCode.INVALID_PROBLEM
    assert str(raised.value) == raised.value.message
    assert isinstance(raised.value.context, dict)


def _matrix_with(
    *,
    location_ids: tuple[str, ...] = ("a", "b", "c"),
    durations: tuple[tuple[int, ...], ...] | None = None,
    distances: tuple[tuple[int, ...], ...] | None = None,
) -> TravelMatrix:
    return TravelMatrix(
        location_ids=location_ids,
        durations_seconds=durations or VALID_MATRIX.durations_seconds,
        distances_meters=distances or VALID_MATRIX.distances_meters,
    )


INVALID_MATRICES = [
    pytest.param(_matrix_with(location_ids=("a", "b", "missing")), id="mismatched-ids"),
    pytest.param(_matrix_with(location_ids=("a", "a", "b")), id="duplicate-ids"),
    pytest.param(_matrix_with(durations=((0, 1), (1, 0))), id="non-square-durations"),
    pytest.param(_matrix_with(distances=((0, 10), (10, 0))), id="non-square-distances"),
    pytest.param(
        _matrix_with(durations=((0, -1, 2), (1, 0, 1), (2, 1, 0))),
        id="negative-duration",
    ),
    pytest.param(
        _matrix_with(durations=((0, True, 2), (1, 0, 1), (2, 1, 0))),
        id="boolean-duration",
    ),
    pytest.param(
        _matrix_with(distances=((1, 10, 20), (10, 0, 10), (20, 10, 0))),
        id="nonzero-distance-diagonal",
    ),
]


@pytest.mark.parametrize("matrix", INVALID_MATRICES)
def test_invalid_matrix_has_stable_error_code(matrix: TravelMatrix) -> None:
    with pytest.raises(MatchingEngineError) as raised:
        solve(VALID_PROBLEM, matrix, VALID_SEARCH)

    assert raised.value.code is ErrorCode.INVALID_MATRIX


def test_invalid_matrix_id_error_reports_missing_and_unexpected_ids() -> None:
    matrix = _matrix_with(location_ids=("a", "b", "unexpected"))

    with pytest.raises(MatchingEngineError) as raised:
        solve(VALID_PROBLEM, matrix, VALID_SEARCH)

    assert raised.value.context == {
        "missing_location_ids": ["c"],
        "unexpected_location_ids": ["unexpected"],
    }
