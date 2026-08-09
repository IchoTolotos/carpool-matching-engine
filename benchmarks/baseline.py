"""Plain deterministic greedy baseline for the documented benchmark subset."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

from carpool_matching_engine import MatchingProblem, Shipment, TravelMatrix, Vehicle


@dataclass(frozen=True, slots=True)
class GreedyResult:
    """Comparable outcome produced by the greedy baseline."""

    served_shipment_ids: tuple[str, ...]
    dropped_shipment_ids: tuple[str, ...]
    objective_value: int
    travel_duration_seconds: int
    travel_distance_meters: int


@dataclass(slots=True)
class _VehicleState:
    vehicle: Vehicle
    shipment_ids: list[str]


@dataclass(frozen=True, slots=True)
class _Insertion:
    objective_delta: int
    travel_delta: int
    shipment_id: str
    vehicle_id: str
    position: int


def _validate_supported_subset(problem: MatchingProblem) -> None:
    destination_ids = {vehicle.end_location_id for vehicle in problem.vehicles}
    if len(destination_ids) != 1:
        msg = "Greedy baseline requires one common vehicle destination."
        raise ValueError(msg)
    destination_id = next(iter(destination_ids))
    for vehicle in problem.vehicles:
        if (
            vehicle.start_time_window is not None
            or vehicle.end_time_window is not None
            or vehicle.end_soft_lower_bound is not None
            or vehicle.max_route_duration_seconds is not None
            or vehicle.max_route_duration_above_direct_seconds is not None
        ):
            msg = "Greedy baseline does not support vehicle time or route-duration constraints."
            raise ValueError(msg)
    for shipment in problem.shipments:
        if shipment.required or shipment.delivery_location_id != destination_id:
            msg = "Greedy baseline requires optional shipments with one common delivery."
            raise ValueError(msg)
        if (
            shipment.pickup_service_seconds != 0
            or shipment.pickup_time_window is not None
            or shipment.delivery_time_window is not None
            or shipment.delivery_soft_lower_bound is not None
        ):
            msg = "Greedy baseline does not support service time or shipment time constraints."
            raise ValueError(msg)


def _route_duration(
    state: _VehicleState,
    shipment_ids: list[str],
    shipments: dict[str, Shipment],
    matrix: TravelMatrix,
) -> int:
    location_ids = [state.vehicle.start_location_id]
    location_ids.extend(shipments[shipment_id].pickup_location_id for shipment_id in shipment_ids)
    location_ids.append(state.vehicle.end_location_id)
    return sum(
        matrix.duration(origin_id, destination_id)
        for origin_id, destination_id in pairwise(location_ids)
    )


def _route_distance(
    state: _VehicleState,
    shipments: dict[str, Shipment],
    matrix: TravelMatrix,
) -> int:
    location_ids = [state.vehicle.start_location_id]
    location_ids.extend(
        shipments[shipment_id].pickup_location_id for shipment_id in state.shipment_ids
    )
    location_ids.append(state.vehicle.end_location_id)
    return sum(
        matrix.distance(origin_id, destination_id)
        for origin_id, destination_id in pairwise(location_ids)
    )


def _has_capacity(
    state: _VehicleState,
    shipment: Shipment,
    shipments: dict[str, Shipment],
) -> bool:
    used_capacity = sum(shipments[shipment_id].size for shipment_id in state.shipment_ids)
    within_capacity = used_capacity + shipment.size <= state.vehicle.capacity
    within_stop_limit = (
        state.vehicle.max_stops is None or len(state.shipment_ids) + 1 <= state.vehicle.max_stops
    )
    return within_capacity and within_stop_limit


def _is_allowed(state: _VehicleState, shipment: Shipment) -> bool:
    return shipment.allowed_vehicle_ids is None or state.vehicle.id in shipment.allowed_vehicle_ids


def _candidate_insertions(
    *,
    states: list[_VehicleState],
    unassigned_ids: set[str],
    shipments: dict[str, Shipment],
    matrix: TravelMatrix,
) -> list[_Insertion]:
    candidates: list[_Insertion] = []
    for shipment_id in sorted(unassigned_ids):
        shipment = shipments[shipment_id]
        for state in states:
            if not _is_allowed(state, shipment) or not _has_capacity(state, shipment, shipments):
                continue
            current_duration = _route_duration(state, state.shipment_ids, shipments, matrix)
            for position in range(len(state.shipment_ids) + 1):
                proposed_ids = state.shipment_ids.copy()
                proposed_ids.insert(position, shipment_id)
                travel_delta = (
                    _route_duration(state, proposed_ids, shipments, matrix) - current_duration
                )
                objective_delta = travel_delta - shipment.drop_penalty
                if objective_delta < 0:
                    candidates.append(
                        _Insertion(
                            objective_delta,
                            travel_delta,
                            shipment_id,
                            state.vehicle.id,
                            position,
                        )
                    )
    return candidates


def solve_greedily(problem: MatchingProblem, matrix: TravelMatrix) -> GreedyResult:
    """Insert the locally best optional shipment until no insertion improves objective."""
    _validate_supported_subset(problem)
    shipments = {shipment.id: shipment for shipment in problem.shipments}
    states = [_VehicleState(vehicle, []) for vehicle in problem.vehicles]
    state_by_vehicle_id = {state.vehicle.id: state for state in states}
    unassigned_ids = set(shipments)

    while candidates := _candidate_insertions(
        states=states,
        unassigned_ids=unassigned_ids,
        shipments=shipments,
        matrix=matrix,
    ):
        selected = min(
            candidates,
            key=lambda candidate: (
                candidate.objective_delta,
                candidate.travel_delta,
                candidate.shipment_id,
                candidate.vehicle_id,
                candidate.position,
            ),
        )
        state = state_by_vehicle_id[selected.vehicle_id]
        state.shipment_ids.insert(selected.position, selected.shipment_id)
        unassigned_ids.remove(selected.shipment_id)

    served_ids = tuple(sorted(set(shipments) - unassigned_ids))
    dropped_ids = tuple(sorted(unassigned_ids))
    travel_duration = sum(
        _route_duration(state, state.shipment_ids, shipments, matrix) for state in states
    )
    travel_distance = sum(_route_distance(state, shipments, matrix) for state in states)
    objective = travel_duration + sum(shipments[item].drop_penalty for item in dropped_ids)
    return GreedyResult(
        served_shipment_ids=served_ids,
        dropped_shipment_ids=dropped_ids,
        objective_value=objective,
        travel_duration_seconds=travel_duration,
        travel_distance_meters=travel_distance,
    )
