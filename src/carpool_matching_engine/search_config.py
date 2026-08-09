"""Explicit, bounded OR-Tools search configuration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FirstSolutionStrategy(StrEnum):
    """Supported first-solution strategies."""

    PARALLEL_CHEAPEST_INSERTION = "parallel_cheapest_insertion"
    LOCAL_CHEAPEST_INSERTION = "local_cheapest_insertion"


class LocalSearchMetaheuristic(StrEnum):
    """Supported local-search strategies."""

    GUIDED_LOCAL_SEARCH = "guided_local_search"
    TABU_SEARCH = "tabu_search"


@dataclass(frozen=True, slots=True)
class SearchAttempt:
    """One bounded OR-Tools search attempt."""

    name: str
    time_limit_seconds: int
    first_solution_strategy: FirstSolutionStrategy
    local_search_metaheuristic: LocalSearchMetaheuristic


@dataclass(frozen=True, slots=True)
class SearchConfig:
    """A sequential search portfolio; the best feasible attempt wins."""

    attempts: tuple[SearchAttempt, ...]

    @classmethod
    def balanced(cls, *, seconds_per_attempt: int = 2) -> SearchConfig:
        """Build the documented three-strategy portfolio."""
        return cls(
            attempts=(
                SearchAttempt(
                    name="parallel-guided",
                    time_limit_seconds=seconds_per_attempt,
                    first_solution_strategy=FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
                    local_search_metaheuristic=LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
                ),
                SearchAttempt(
                    name="local-tabu",
                    time_limit_seconds=seconds_per_attempt,
                    first_solution_strategy=FirstSolutionStrategy.LOCAL_CHEAPEST_INSERTION,
                    local_search_metaheuristic=LocalSearchMetaheuristic.TABU_SEARCH,
                ),
                SearchAttempt(
                    name="local-guided",
                    time_limit_seconds=seconds_per_attempt,
                    first_solution_strategy=FirstSolutionStrategy.LOCAL_CHEAPEST_INSERTION,
                    local_search_metaheuristic=LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
                ),
            )
        )
