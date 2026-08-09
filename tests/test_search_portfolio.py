from __future__ import annotations

from carpool_matching_engine import MatchingProblem, SearchConfig, Vehicle, solve
from tests.helpers import make_line_matrix, make_locations


def test_balanced_portfolio_reports_every_attempt_in_order() -> None:
    location_ids = ("start", "end")
    problem = MatchingProblem(
        locations=make_locations(*location_ids),
        vehicles=(Vehicle("car", "start", "end", capacity=1),),
        shipments=(),
        time_horizon_seconds=100,
    )

    result = solve(
        problem,
        make_line_matrix(location_ids, (0, 10)),
        SearchConfig.balanced(seconds_per_attempt=1),
    )

    assert [attempt.name for attempt in result.diagnostics.attempts] == [
        "parallel-guided",
        "local-tabu",
        "local-guided",
    ]
    assert all(attempt.solved for attempt in result.diagnostics.attempts)
    assert all(
        attempt.objective_value == result.diagnostics.objective_value
        for attempt in result.diagnostics.attempts
    )
    assert all(attempt.duration_milliseconds >= 0 for attempt in result.diagnostics.attempts)
    assert result.diagnostics.duration_milliseconds >= 0
    assert result.routes[0].direct_duration_seconds == 10
    assert result.routes[0].direct_distance_meters == 100
