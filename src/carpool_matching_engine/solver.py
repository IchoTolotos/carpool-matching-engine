"""Public orchestration for validation, search portfolio, and result selection."""

from __future__ import annotations

from time import perf_counter

from .errors import ErrorCode, MatchingEngineError
from .matrix import MatrixProvider, TravelMatrix
from .models import MatchingDiagnostics, MatchingProblem, MatchingResult, SearchAttemptResult
from .ortools_backend import AttemptSolution, run_attempt
from .search_config import SearchConfig
from .validation import validate_matrix, validate_problem


def solve(
    problem: MatchingProblem,
    matrix: TravelMatrix,
    search_config: SearchConfig,
) -> MatchingResult:
    """Solve assignment and route ordering together, returning the best portfolio result."""
    validate_problem(problem, search_config)
    validate_matrix(problem, matrix)
    started_at = perf_counter()
    attempt_diagnostics: list[SearchAttemptResult] = []
    best: AttemptSolution | None = None

    for attempt in search_config.attempts:
        execution = run_attempt(problem, matrix, attempt)
        attempt_diagnostics.append(execution.diagnostics)
        attempt_solution = execution.solution
        if attempt_solution is None:
            continue
        if best is None or attempt_solution.objective_value < best.objective_value:
            best = attempt_solution

    if best is None:
        raise MatchingEngineError(
            ErrorCode.NO_SOLUTION,
            "No search attempt found a solution satisfying every required constraint.",
            attempt_names=[attempt.name for attempt in search_config.attempts],
        )

    return MatchingResult(
        routes=best.routes,
        dropped_shipment_ids=best.dropped_shipment_ids,
        diagnostics=MatchingDiagnostics(
            objective_value=best.objective_value,
            duration_milliseconds=(perf_counter() - started_at) * 1_000,
            attempts=tuple(attempt_diagnostics),
        ),
    )


def solve_with_provider(
    problem: MatchingProblem,
    matrix_provider: MatrixProvider,
    search_config: SearchConfig,
) -> MatchingResult:
    """Build the travel matrix through an application adapter, then solve."""
    validate_problem(problem, search_config)
    matrix = matrix_provider.build_matrix(problem.locations)
    return solve(problem, matrix, search_config)
