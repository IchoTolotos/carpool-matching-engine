from __future__ import annotations

import pytest

from benchmarks.scale import (
    ScaleObservation,
    _nearest_rank_p95,
    _summarize,
    build_scale_scenarios,
    run_scale_benchmark,
)


def test_scale_scenarios_are_seeded_and_stable() -> None:
    first = build_scale_scenarios()
    second = build_scale_scenarios()

    assert first == second
    assert [
        (item.name, len(item.problem.vehicles), len(item.problem.shipments), item.seed)
        for item in first
    ] == [
        ("small", 4, 16, 4_016),
        ("medium", 8, 32, 8_032),
        ("large", 16, 64, 16_064),
    ]


def test_scale_summary_uses_best_objective_and_repeated_run_statistics() -> None:
    observations = [
        ScaleObservation("small", 4, 16, 15, 1_200, 900.0),
        ScaleObservation("small", 4, 16, 16, 1_000, 1_100.0),
        ScaleObservation("small", 4, 16, 16, 1_100, 1_000.0),
    ]

    summary = _summarize(observations)

    assert summary.served_minimum == 15
    assert summary.served_maximum == 16
    assert summary.objective_best == 1_000
    assert summary.objective_median == 1_100.0
    assert summary.runtime_median_milliseconds == 1_000.0
    assert summary.runtime_p95_milliseconds == 1_100.0


def test_nearest_rank_p95_requires_no_interpolation() -> None:
    assert _nearest_rank_p95([1.0, 2.0, 3.0, 4.0, 5.0]) == 5.0


@pytest.mark.parametrize(
    ("repetitions", "seconds_per_run", "message"),
    [
        pytest.param(0, 1, "repetitions", id="zero-repetitions"),
        pytest.param(1, 0, "seconds per run", id="zero-time-limit"),
    ],
)
def test_scale_benchmark_rejects_invalid_run_controls(
    repetitions: int,
    seconds_per_run: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        run_scale_benchmark(repetitions=repetitions, seconds_per_run=seconds_per_run)
