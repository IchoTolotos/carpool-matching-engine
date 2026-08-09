from __future__ import annotations

import math

import pytest

from carpool_matching_engine import MatchingProblem, Shipment, Vehicle, solve_with_provider
from carpool_matching_engine.testing import StraightLineMatrixProvider
from tests.helpers import make_locations, one_second_search


def test_straight_line_provider_builds_a_complete_symmetric_matrix() -> None:
    locations = make_locations("a", "b", "c")
    provider = StraightLineMatrixProvider(speed_kilometers_per_hour=36)

    matrix = provider.build_matrix(locations)

    assert matrix.location_ids == ("a", "b", "c")
    assert matrix.duration("a", "a") == 0
    assert matrix.distance("a", "a") == 0
    assert matrix.distance("a", "b") == matrix.distance("b", "a")
    assert matrix.duration("a", "b") == matrix.duration("b", "a")
    assert matrix.duration("a", "b") == math.ceil(matrix.distance("a", "b") / 10)
    assert matrix.distance("a", "c") > matrix.distance("a", "b") > 0


def test_solve_with_provider_uses_the_public_matrix_provider_contract() -> None:
    locations = make_locations("depot", "pickup", "delivery")
    problem = MatchingProblem(
        locations=locations,
        vehicles=(Vehicle("car", "depot", "depot", capacity=1),),
        shipments=(Shipment("rider", "pickup", "delivery", required=True),),
        time_horizon_seconds=10_000,
    )

    result = solve_with_provider(
        problem,
        StraightLineMatrixProvider(speed_kilometers_per_hour=36),
        one_second_search(),
    )

    assert result.routes[0].shipment_ids == ("rider",)
    assert result.dropped_shipment_ids == ()
    assert result.routes[0].distance_meters > 0


@pytest.mark.parametrize("speed", [0, -1, math.inf, math.nan])
def test_straight_line_provider_rejects_invalid_speeds(speed: float) -> None:
    with pytest.raises(ValueError, match="must be finite and positive"):
        StraightLineMatrixProvider(speed_kilometers_per_hour=speed).build_matrix(
            make_locations("a")
        )
