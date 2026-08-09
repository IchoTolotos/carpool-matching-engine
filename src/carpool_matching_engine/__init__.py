"""Provider-neutral carpool assignment and route-ordering engine."""

from .errors import ErrorCode, MatchingEngineError
from .matrix import MatrixProvider, TravelMatrix
from .models import (
    Coordinate,
    Location,
    MatchingDiagnostics,
    MatchingProblem,
    MatchingResult,
    RouteStop,
    SearchAttemptResult,
    Shipment,
    SoftLowerBound,
    SolvedRoute,
    StopKind,
    TimeWindow,
    Vehicle,
)
from .search_config import (
    FirstSolutionStrategy,
    LocalSearchMetaheuristic,
    SearchAttempt,
    SearchConfig,
)
from .solver import solve, solve_with_provider

__all__ = [
    "Coordinate",
    "ErrorCode",
    "FirstSolutionStrategy",
    "LocalSearchMetaheuristic",
    "Location",
    "MatchingDiagnostics",
    "MatchingEngineError",
    "MatchingProblem",
    "MatchingResult",
    "MatrixProvider",
    "RouteStop",
    "SearchAttempt",
    "SearchAttemptResult",
    "SearchConfig",
    "Shipment",
    "SoftLowerBound",
    "SolvedRoute",
    "StopKind",
    "TimeWindow",
    "TravelMatrix",
    "Vehicle",
    "solve",
    "solve_with_provider",
]
