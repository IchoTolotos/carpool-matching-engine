"""Travel-matrix contract separating routing data from optimization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .models import Location


@dataclass(frozen=True, slots=True)
class TravelMatrix:
    """Directed travel durations and distances indexed by location id."""

    location_ids: tuple[str, ...]
    durations_seconds: tuple[tuple[int, ...], ...]
    distances_meters: tuple[tuple[int, ...], ...]
    _index_by_id: dict[str, int] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_index_by_id",
            dict(zip(self.location_ids, range(len(self.location_ids)), strict=True)),
        )

    def duration(self, origin_id: str, destination_id: str) -> int:
        """Return directed duration between two locations."""
        return self.durations_seconds[self._index_by_id[origin_id]][
            self._index_by_id[destination_id]
        ]

    def distance(self, origin_id: str, destination_id: str) -> int:
        """Return directed distance between two locations."""
        return self.distances_meters[self._index_by_id[origin_id]][
            self._index_by_id[destination_id]
        ]


class MatrixProvider(Protocol):
    """Application adapter that builds one complete directed travel matrix."""

    def build_matrix(self, locations: tuple[Location, ...]) -> TravelMatrix:
        """Build a matrix containing every supplied location exactly once."""
        ...
