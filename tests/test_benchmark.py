from __future__ import annotations

from dataclasses import replace

import pytest

from benchmarks.baseline import solve_greedily
from benchmarks.scenarios import build_scenarios
from carpool_matching_engine import MatchingProblem, solve
from tests.helpers import one_second_search


def test_global_solver_avoids_the_documented_greedy_eligibility_trap() -> None:
    scenario = next(item for item in build_scenarios() if item.name == "greedy-eligibility-trap")

    optimized = solve(scenario.problem, scenario.matrix, one_second_search())
    greedy = solve_greedily(scenario.problem, scenario.matrix)

    assert optimized.dropped_shipment_ids == ()
    assert greedy.dropped_shipment_ids == ("shipment-west-only",)
    assert optimized.diagnostics.objective_value < greedy.objective_value


def test_greedy_baseline_rejects_constraints_outside_its_documented_subset() -> None:
    scenario = build_scenarios()[0]
    required_shipment = replace(scenario.problem.shipments[0], required=True)
    unsupported_problem = MatchingProblem(
        locations=scenario.problem.locations,
        vehicles=scenario.problem.vehicles,
        shipments=(required_shipment, *scenario.problem.shipments[1:]),
        time_horizon_seconds=scenario.problem.time_horizon_seconds,
    )

    with pytest.raises(ValueError, match="optional shipments"):
        solve_greedily(unsupported_problem, scenario.matrix)
