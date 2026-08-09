from __future__ import annotations

from dataclasses import replace

import pytest

from carpool_matching_engine import (
    ErrorCode,
    MatchingEngineError,
    MatchingProblem,
    Shipment,
    SoftLowerBound,
    StopKind,
    TimeWindow,
    Vehicle,
    solve,
)
from tests.helpers import make_line_matrix, make_locations, make_matrix, one_second_search


def test_assigns_shipments_to_the_lowest_cost_vehicle() -> None:
    location_ids = ("west", "west-pickup", "west-delivery", "east-delivery", "east-pickup", "east")
    locations = make_locations(*location_ids)
    problem = MatchingProblem(
        locations=locations,
        vehicles=(
            Vehicle(id="west-car", start_location_id="west", end_location_id="west", capacity=1),
            Vehicle(id="east-car", start_location_id="east", end_location_id="east", capacity=1),
        ),
        shipments=(
            Shipment(
                id="west-rider",
                pickup_location_id="west-pickup",
                delivery_location_id="west-delivery",
                required=True,
            ),
            Shipment(
                id="east-rider",
                pickup_location_id="east-pickup",
                delivery_location_id="east-delivery",
                required=True,
            ),
        ),
        time_horizon_seconds=1_000,
    )

    result = solve(
        problem,
        make_line_matrix(location_ids, (0, 1, 2, 98, 99, 100)),
        one_second_search(),
    )

    routes = {route.vehicle_id: route for route in result.routes}
    assert routes["west-car"].shipment_ids == ("west-rider",)
    assert routes["east-car"].shipment_ids == ("east-rider",)
    assert result.dropped_shipment_ids == ()


def test_orders_pickups_and_deliveries_by_total_route_cost() -> None:
    location_ids = ("start", "pickup-a", "pickup-b", "delivery-b", "delivery-a", "end")
    problem = MatchingProblem(
        locations=make_locations(*location_ids),
        vehicles=(Vehicle("car", "start", "end", capacity=2),),
        shipments=(
            Shipment("a", "pickup-a", "delivery-a", required=True),
            Shipment("b", "pickup-b", "delivery-b", required=True),
        ),
        time_horizon_seconds=1_000,
    )

    route = solve(
        problem,
        make_line_matrix(location_ids, (0, 10, 20, 30, 40, 50)),
        one_second_search(),
    ).routes[0]

    assert [(stop.kind, stop.shipment_id) for stop in route.stops] == [
        (StopKind.START, None),
        (StopKind.PICKUP, "a"),
        (StopKind.PICKUP, "b"),
        (StopKind.DELIVERY, "b"),
        (StopKind.DELIVERY, "a"),
        (StopKind.END, None),
    ]
    assert route.shipment_ids == ("a", "b")
    assert route.duration_seconds == 50
    assert route.distance_meters == 500


def test_capacity_applies_to_heterogeneous_shipment_sizes() -> None:
    location_ids = ("depot", "pickup", "small-delivery", "large-delivery")
    problem = MatchingProblem(
        locations=make_locations(*location_ids),
        vehicles=(Vehicle("car", "depot", "depot", capacity=2),),
        shipments=(
            Shipment(
                "large",
                "pickup",
                "large-delivery",
                size=2,
                pickup_time_window=TimeWindow(earliest=0, latest=0),
                drop_penalty=10_000,
            ),
            Shipment(
                "small",
                "pickup",
                "small-delivery",
                size=1,
                pickup_time_window=TimeWindow(earliest=0, latest=0),
                drop_penalty=100,
            ),
        ),
        time_horizon_seconds=100,
    )

    result = solve(
        problem,
        make_line_matrix(location_ids, (0, 0, 1, 10)),
        one_second_search(),
    )

    assert result.routes[0].shipment_ids == ("large",)
    assert result.dropped_shipment_ids == ("small",)


def test_max_stops_limits_the_number_of_served_shipments() -> None:
    location_ids = ("depot", "pickup-high", "delivery-high", "pickup-low", "delivery-low")
    problem = MatchingProblem(
        locations=make_locations(*location_ids),
        vehicles=(Vehicle("car", "depot", "depot", capacity=2, max_stops=1),),
        shipments=(
            Shipment("high", "pickup-high", "delivery-high", drop_penalty=10_000),
            Shipment("low", "pickup-low", "delivery-low", drop_penalty=100),
        ),
        time_horizon_seconds=100,
    )

    result = solve(problem, make_line_matrix(location_ids), one_second_search())

    assert result.routes[0].shipment_ids == ("high",)
    assert result.dropped_shipment_ids == ("low",)


def test_allowed_vehicle_ids_restrict_assignment() -> None:
    location_ids = ("depot", "pickup", "delivery")
    problem = MatchingProblem(
        locations=make_locations(*location_ids),
        vehicles=(
            Vehicle("car-a", "depot", "depot", capacity=1),
            Vehicle("car-b", "depot", "depot", capacity=1),
        ),
        shipments=(
            Shipment(
                "rider",
                "pickup",
                "delivery",
                allowed_vehicle_ids=("car-b",),
                required=True,
            ),
        ),
        time_horizon_seconds=100,
    )

    result = solve(problem, make_line_matrix(location_ids), one_second_search())
    routes = {route.vehicle_id: route.shipment_ids for route in result.routes}

    assert routes == {"car-a": (), "car-b": ("rider",)}


def test_required_infeasibility_has_stable_no_solution_error() -> None:
    location_ids = ("depot", "pickup", "delivery")
    problem = MatchingProblem(
        locations=make_locations(*location_ids),
        vehicles=(Vehicle("car", "depot", "depot", capacity=1),),
        shipments=(Shipment("too-large", "pickup", "delivery", size=2, required=True),),
        time_horizon_seconds=100,
    )

    with pytest.raises(MatchingEngineError) as raised:
        solve(problem, make_line_matrix(location_ids), one_second_search(name="required"))

    assert raised.value.code is ErrorCode.NO_SOLUTION
    assert raised.value.context == {"attempt_names": ["required"]}


def test_optional_infeasible_shipment_is_dropped() -> None:
    location_ids = ("depot", "pickup", "delivery")
    problem = MatchingProblem(
        locations=make_locations(*location_ids),
        vehicles=(Vehicle("car", "depot", "depot", capacity=1),),
        shipments=(Shipment("too-large", "pickup", "delivery", size=2),),
        time_horizon_seconds=100,
    )

    result = solve(problem, make_line_matrix(location_ids), one_second_search())

    assert result.routes[0].shipment_ids == ()
    assert result.dropped_shipment_ids == ("too-large",)


def test_pickup_and_delivery_time_windows_are_reflected_in_arrivals() -> None:
    location_ids = ("start", "pickup", "delivery", "end")
    shipment = Shipment(
        "timed",
        "pickup",
        "delivery",
        pickup_service_seconds=5,
        pickup_time_window=TimeWindow(earliest=50, latest=60),
        delivery_time_window=TimeWindow(earliest=90, latest=100),
        delivery_soft_lower_bound=SoftLowerBound(target=95, penalty_per_second=2),
        required=True,
    )
    problem = MatchingProblem(
        locations=make_locations(*location_ids),
        vehicles=(
            Vehicle(
                "car",
                "start",
                "end",
                capacity=1,
                start_time_window=TimeWindow(earliest=0, latest=20),
                end_time_window=TimeWindow(earliest=100, latest=140),
                end_soft_lower_bound=SoftLowerBound(target=120, penalty_per_second=1),
            ),
        ),
        shipments=(shipment,),
        time_horizon_seconds=200,
    )

    route = solve(
        problem,
        make_line_matrix(location_ids, (0, 10, 20, 30)),
        one_second_search(),
    ).routes[0]
    arrivals = {stop.kind: stop.arrival_seconds for stop in route.stops}

    assert 0 <= arrivals[StopKind.START] <= 20
    assert 50 <= arrivals[StopKind.PICKUP] <= 60
    assert 95 <= arrivals[StopKind.DELIVERY] <= 100
    assert 120 <= arrivals[StopKind.END] <= 140
    assert arrivals[StopKind.PICKUP] < arrivals[StopKind.DELIVERY]


@pytest.mark.parametrize(
    ("allowance", "expected_shipments", "expected_drops"),
    [
        pytest.param(5, (), ("detour",), id="above-direct-limit-drops"),
        pytest.param(6, ("detour",), (), id="exact-above-direct-limit-serves"),
    ],
)
def test_max_route_duration_above_direct(
    allowance: int,
    expected_shipments: tuple[str, ...],
    expected_drops: tuple[str, ...],
) -> None:
    location_ids = ("start", "pickup", "delivery", "end")
    matrix = make_matrix(
        location_ids,
        (
            (0, 4, 50, 10),
            (50, 0, 4, 50),
            (50, 50, 0, 8),
            (50, 50, 50, 0),
        ),
    )
    vehicle = Vehicle(
        "car",
        "start",
        "end",
        capacity=1,
        max_route_duration_above_direct_seconds=allowance,
    )
    problem = MatchingProblem(
        locations=make_locations(*location_ids),
        vehicles=(vehicle,),
        shipments=(Shipment("detour", "pickup", "delivery", drop_penalty=10_000),),
        time_horizon_seconds=100,
    )

    result = solve(problem, matrix, one_second_search())

    assert result.routes[0].direct_duration_seconds == 10
    assert result.routes[0].shipment_ids == expected_shipments
    assert result.dropped_shipment_ids == expected_drops
    assert result.routes[0].duration_seconds <= 10 + allowance


def test_absolute_route_duration_uses_the_stricter_limit() -> None:
    location_ids = ("start", "pickup", "delivery", "end")
    problem = MatchingProblem(
        locations=make_locations(*location_ids),
        vehicles=(
            Vehicle(
                "car",
                "start",
                "end",
                capacity=1,
                max_route_duration_seconds=15,
                max_route_duration_above_direct_seconds=20,
            ),
        ),
        shipments=(Shipment("detour", "pickup", "delivery"),),
        time_horizon_seconds=100,
    )
    matrix = make_matrix(
        location_ids,
        (
            (0, 4, 50, 10),
            (50, 0, 4, 50),
            (50, 50, 0, 8),
            (50, 50, 50, 0),
        ),
    )

    result = solve(problem, matrix, one_second_search())

    assert result.dropped_shipment_ids == ("detour",)
    assert result.routes[0].duration_seconds == 10


def test_optional_drop_ids_are_sorted_independently_of_input_order() -> None:
    location_ids = ("depot", "pickup", "delivery")
    base = MatchingProblem(
        locations=make_locations(*location_ids),
        vehicles=(Vehicle("car", "depot", "depot", capacity=1),),
        shipments=(
            Shipment("z-last", "pickup", "delivery", size=2),
            Shipment("a-first", "pickup", "delivery", size=2),
        ),
        time_horizon_seconds=100,
    )

    result = solve(base, make_line_matrix(location_ids), one_second_search())

    assert result.dropped_shipment_ids == ("a-first", "z-last")
    assert replace(result.routes[0], stops=()).vehicle_id == "car"
