"""OR-Tools adapter for the provider-neutral domain model."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from .matrix import TravelMatrix
from .models import (
    MatchingProblem,
    RouteStop,
    SearchAttemptResult,
    SolvedRoute,
    StopKind,
    TimeWindow,
)
from .search_config import (
    FirstSolutionStrategy,
    LocalSearchMetaheuristic,
    SearchAttempt,
)


@dataclass(frozen=True, slots=True)
class _RoutingNode:
    kind: StopKind
    location_id: str
    shipment_id: str | None = None


@dataclass(frozen=True, slots=True)
class _BuiltModel:
    manager: Any
    routing: Any
    time_dimension: Any
    nodes: tuple[_RoutingNode, ...]
    shipment_pickup_node_ids: dict[str, int]


@dataclass(frozen=True, slots=True)
class _NodeLayout:
    nodes: tuple[_RoutingNode, ...]
    start_node_ids: tuple[int, ...]
    end_node_ids: tuple[int, ...]
    shipment_pickup_node_ids: dict[str, int]
    shipment_delivery_node_ids: dict[str, int]


@dataclass(frozen=True, slots=True)
class AttemptSolution:
    """A fully extracted solution independent from OR-Tools object lifetimes."""

    routes: tuple[SolvedRoute, ...]
    dropped_shipment_ids: tuple[str, ...]
    objective_value: int


@dataclass(frozen=True, slots=True)
class AttemptExecution:
    """One attempt's diagnostics and optional feasible solution."""

    solution: AttemptSolution | None
    diagnostics: SearchAttemptResult


def _window_bounds(window: TimeWindow | None, horizon: int) -> tuple[int, int]:
    if window is None:
        return 0, horizon
    return (
        window.earliest if window.earliest is not None else 0,
        window.latest if window.latest is not None else horizon,
    )


def _route_limit(problem: MatchingProblem, matrix: TravelMatrix, vehicle_index: int) -> int | None:
    vehicle = problem.vehicles[vehicle_index]
    absolute_limit = vehicle.max_route_duration_seconds
    if vehicle.max_route_duration_above_direct_seconds is None:
        return absolute_limit
    relative_limit = (
        matrix.duration(vehicle.start_location_id, vehicle.end_location_id)
        + vehicle.max_route_duration_above_direct_seconds
    )
    return relative_limit if absolute_limit is None else min(relative_limit, absolute_limit)


def _build_node_layout(problem: MatchingProblem) -> _NodeLayout:
    nodes: list[_RoutingNode] = []
    start_node_ids: list[int] = []
    end_node_ids: list[int] = []
    for vehicle in problem.vehicles:
        start_node_ids.append(len(nodes))
        nodes.append(_RoutingNode(StopKind.START, vehicle.start_location_id))

    shipment_pickup_node_ids: dict[str, int] = {}
    shipment_delivery_node_ids: dict[str, int] = {}
    for shipment in problem.shipments:
        shipment_pickup_node_ids[shipment.id] = len(nodes)
        nodes.append(_RoutingNode(StopKind.PICKUP, shipment.pickup_location_id, shipment.id))
        shipment_delivery_node_ids[shipment.id] = len(nodes)
        nodes.append(_RoutingNode(StopKind.DELIVERY, shipment.delivery_location_id, shipment.id))

    for vehicle in problem.vehicles:
        end_node_ids.append(len(nodes))
        nodes.append(_RoutingNode(StopKind.END, vehicle.end_location_id))
    return _NodeLayout(
        nodes=tuple(nodes),
        start_node_ids=tuple(start_node_ids),
        end_node_ids=tuple(end_node_ids),
        shipment_pickup_node_ids=shipment_pickup_node_ids,
        shipment_delivery_node_ids=shipment_delivery_node_ids,
    )


def _register_dimensions(
    *,
    problem: MatchingProblem,
    matrix: TravelMatrix,
    layout: _NodeLayout,
    manager: Any,
    routing: Any,
) -> Any:
    shipment_by_id = {shipment.id: shipment for shipment in problem.shipments}

    def time_callback(from_index: int, to_index: int) -> int:
        from_node = layout.nodes[manager.IndexToNode(from_index)]
        to_node = layout.nodes[manager.IndexToNode(to_index)]
        service_seconds = 0
        if from_node.kind is StopKind.PICKUP and from_node.shipment_id is not None:
            service_seconds = shipment_by_id[from_node.shipment_id].pickup_service_seconds
        return matrix.duration(from_node.location_id, to_node.location_id) + service_seconds

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(time_callback_index)

    def demand_callback(index: int) -> int:
        node = layout.nodes[manager.IndexToNode(index)]
        if node.shipment_id is None:
            return 0
        size = shipment_by_id[node.shipment_id].size
        if node.kind is StopKind.PICKUP:
            return size
        if node.kind is StopKind.DELIVERY:
            return -size
        return 0

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        [vehicle.capacity for vehicle in problem.vehicles],
        True,
        "Capacity",
    )
    routing.AddDimension(
        time_callback_index,
        problem.time_horizon_seconds,
        problem.time_horizon_seconds,
        False,
        "Time",
    )
    time_dimension = routing.GetDimensionOrDie("Time")

    def pickup_count_callback(index: int) -> int:
        node = layout.nodes[manager.IndexToNode(index)]
        return int(node.kind is StopKind.PICKUP)

    pickup_count_callback_index = routing.RegisterUnaryTransitCallback(pickup_count_callback)
    routing.AddDimensionWithVehicleCapacity(
        pickup_count_callback_index,
        0,
        [
            vehicle.max_stops if vehicle.max_stops is not None else len(problem.shipments)
            for vehicle in problem.vehicles
        ],
        True,
        "PickupCount",
    )
    return time_dimension


def _apply_vehicle_constraints(
    *,
    problem: MatchingProblem,
    matrix: TravelMatrix,
    routing: Any,
    time_dimension: Any,
) -> None:
    for vehicle_index, vehicle in enumerate(problem.vehicles):
        start_index = routing.Start(vehicle_index)
        end_index = routing.End(vehicle_index)
        time_dimension.CumulVar(start_index).SetRange(
            *_window_bounds(vehicle.start_time_window, problem.time_horizon_seconds)
        )
        time_dimension.CumulVar(end_index).SetRange(
            *_window_bounds(vehicle.end_time_window, problem.time_horizon_seconds)
        )
        if vehicle.end_soft_lower_bound is not None:
            time_dimension.SetCumulVarSoftLowerBound(
                end_index,
                vehicle.end_soft_lower_bound.target,
                vehicle.end_soft_lower_bound.penalty_per_second,
            )
        route_limit = _route_limit(problem, matrix, vehicle_index)
        if route_limit is not None:
            routing.solver().Add(
                time_dimension.CumulVar(end_index)
                <= time_dimension.CumulVar(start_index) + route_limit
            )
        routing.AddVariableMaximizedByFinalizer(time_dimension.CumulVar(start_index))
        routing.AddVariableMaximizedByFinalizer(time_dimension.CumulVar(end_index))


def _apply_shipment_constraints(
    *,
    problem: MatchingProblem,
    layout: _NodeLayout,
    manager: Any,
    routing: Any,
    time_dimension: Any,
) -> None:
    vehicle_index_by_id = {
        vehicle.id: vehicle_index for vehicle_index, vehicle in enumerate(problem.vehicles)
    }
    for shipment in problem.shipments:
        pickup_index = manager.NodeToIndex(layout.shipment_pickup_node_ids[shipment.id])
        delivery_index = manager.NodeToIndex(layout.shipment_delivery_node_ids[shipment.id])
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index))
        routing.solver().Add(routing.ActiveVar(pickup_index) == routing.ActiveVar(delivery_index))
        routing.solver().Add(
            time_dimension.CumulVar(pickup_index) <= time_dimension.CumulVar(delivery_index)
        )

        if not shipment.required:
            pickup_penalty = shipment.drop_penalty // 2
            delivery_penalty = shipment.drop_penalty - pickup_penalty
            routing.AddDisjunction([pickup_index], pickup_penalty)
            routing.AddDisjunction([delivery_index], delivery_penalty)

        if shipment.allowed_vehicle_ids is not None:
            allowed_indices = {
                vehicle_index_by_id[vehicle_id] for vehicle_id in shipment.allowed_vehicle_ids
            }
            for vehicle_index in range(len(problem.vehicles)):
                if vehicle_index in allowed_indices:
                    continue
                routing.solver().Add(routing.VehicleVar(pickup_index) != vehicle_index)
                routing.solver().Add(routing.VehicleVar(delivery_index) != vehicle_index)

        time_dimension.CumulVar(pickup_index).SetRange(
            *_window_bounds(shipment.pickup_time_window, problem.time_horizon_seconds)
        )
        time_dimension.CumulVar(delivery_index).SetRange(
            *_window_bounds(shipment.delivery_time_window, problem.time_horizon_seconds)
        )
        if shipment.delivery_soft_lower_bound is not None:
            time_dimension.SetCumulVarSoftLowerBound(
                delivery_index,
                shipment.delivery_soft_lower_bound.target,
                shipment.delivery_soft_lower_bound.penalty_per_second,
            )
        routing.AddVariableMaximizedByFinalizer(time_dimension.CumulVar(pickup_index))
        routing.AddVariableMaximizedByFinalizer(time_dimension.CumulVar(delivery_index))


def _build_model(problem: MatchingProblem, matrix: TravelMatrix) -> _BuiltModel:
    layout = _build_node_layout(problem)
    manager = pywrapcp.RoutingIndexManager(
        len(layout.nodes),
        len(problem.vehicles),
        layout.start_node_ids,
        layout.end_node_ids,
    )
    routing = pywrapcp.RoutingModel(manager)
    time_dimension = _register_dimensions(
        problem=problem,
        matrix=matrix,
        layout=layout,
        manager=manager,
        routing=routing,
    )
    _apply_vehicle_constraints(
        problem=problem,
        matrix=matrix,
        routing=routing,
        time_dimension=time_dimension,
    )
    _apply_shipment_constraints(
        problem=problem,
        layout=layout,
        manager=manager,
        routing=routing,
        time_dimension=time_dimension,
    )
    return _BuiltModel(
        manager=manager,
        routing=routing,
        time_dimension=time_dimension,
        nodes=layout.nodes,
        shipment_pickup_node_ids=layout.shipment_pickup_node_ids,
    )


def _search_parameters(attempt: SearchAttempt) -> Any:
    first_solution_values = {
        FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION: (
            routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        ),
        FirstSolutionStrategy.LOCAL_CHEAPEST_INSERTION: (
            routing_enums_pb2.FirstSolutionStrategy.LOCAL_CHEAPEST_INSERTION
        ),
    }
    local_search_values = {
        LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH: (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        ),
        LocalSearchMetaheuristic.TABU_SEARCH: (
            routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH
        ),
    }
    parameters = pywrapcp.DefaultRoutingSearchParameters()
    parameters.first_solution_strategy = first_solution_values[attempt.first_solution_strategy]
    parameters.local_search_metaheuristic = local_search_values[attempt.local_search_metaheuristic]
    parameters.time_limit.seconds = attempt.time_limit_seconds
    parameters.use_full_propagation = True
    return parameters


def _extract_route(
    *,
    built: _BuiltModel,
    matrix: TravelMatrix,
    problem: MatchingProblem,
    solution: Any,
    vehicle_index: int,
) -> SolvedRoute:
    vehicle = problem.vehicles[vehicle_index]
    route_stops: list[RouteStop] = []
    shipment_ids: list[str] = []
    distance_meters = 0
    index = built.routing.Start(vehicle_index)

    while True:
        node = built.nodes[built.manager.IndexToNode(index)]
        route_stops.append(
            RouteStop(
                kind=node.kind,
                location_id=node.location_id,
                arrival_seconds=solution.Value(built.time_dimension.CumulVar(index)),
                shipment_id=node.shipment_id,
            )
        )
        if node.kind is StopKind.PICKUP and node.shipment_id is not None:
            shipment_ids.append(node.shipment_id)
        if built.routing.IsEnd(index):
            break
        next_index = solution.Value(built.routing.NextVar(index))
        next_node = built.nodes[built.manager.IndexToNode(next_index)]
        distance_meters += matrix.distance(node.location_id, next_node.location_id)
        index = next_index

    duration_seconds = route_stops[-1].arrival_seconds - route_stops[0].arrival_seconds
    return SolvedRoute(
        vehicle_id=vehicle.id,
        stops=tuple(route_stops),
        shipment_ids=tuple(shipment_ids),
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        direct_duration_seconds=matrix.duration(
            vehicle.start_location_id,
            vehicle.end_location_id,
        ),
        direct_distance_meters=matrix.distance(
            vehicle.start_location_id,
            vehicle.end_location_id,
        ),
    )


def run_attempt(
    problem: MatchingProblem,
    matrix: TravelMatrix,
    attempt: SearchAttempt,
) -> AttemptExecution:
    """Build and solve one independent OR-Tools model."""
    built = _build_model(problem, matrix)
    started_at = perf_counter()
    solution = built.routing.SolveWithParameters(_search_parameters(attempt))
    duration_milliseconds = (perf_counter() - started_at) * 1_000
    if solution is None:
        return AttemptExecution(
            solution=None,
            diagnostics=SearchAttemptResult(
                name=attempt.name,
                solved=False,
                objective_value=None,
                duration_milliseconds=duration_milliseconds,
            ),
        )

    dropped_ids = tuple(
        sorted(
            shipment.id
            for shipment in problem.shipments
            if solution.Value(
                built.routing.ActiveVar(
                    built.manager.NodeToIndex(built.shipment_pickup_node_ids[shipment.id])
                )
            )
            == 0
        )
    )
    routes = tuple(
        _extract_route(
            built=built,
            matrix=matrix,
            problem=problem,
            solution=solution,
            vehicle_index=vehicle_index,
        )
        for vehicle_index in range(len(problem.vehicles))
    )
    objective_value = int(solution.ObjectiveValue())
    return AttemptExecution(
        solution=AttemptSolution(
            routes=routes,
            dropped_shipment_ids=dropped_ids,
            objective_value=objective_value,
        ),
        diagnostics=SearchAttemptResult(
            name=attempt.name,
            solved=True,
            objective_value=objective_value,
            duration_milliseconds=duration_milliseconds,
        ),
    )
