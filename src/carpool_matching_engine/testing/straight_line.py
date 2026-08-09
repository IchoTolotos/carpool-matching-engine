"""Deterministic straight-line matrix provider for tests and examples."""

from __future__ import annotations

import math
from dataclasses import dataclass

from carpool_matching_engine.matrix import TravelMatrix
from carpool_matching_engine.models import Coordinate, Location

_EARTH_RADIUS_METERS = 6_371_008.8


def _haversine_meters(origin: Coordinate, destination: Coordinate) -> int:
    origin_latitude = math.radians(origin.latitude)
    destination_latitude = math.radians(destination.latitude)
    latitude_delta = destination_latitude - origin_latitude
    longitude_delta = math.radians(destination.longitude - origin.longitude)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(origin_latitude)
        * math.cos(destination_latitude)
        * math.sin(longitude_delta / 2) ** 2
    )
    return round(
        2 * _EARTH_RADIUS_METERS * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
    )


@dataclass(frozen=True, slots=True)
class StraightLineMatrixProvider:
    """Synthetic provider; it is not a road-network router."""

    speed_kilometers_per_hour: float = 40

    def build_matrix(self, locations: tuple[Location, ...]) -> TravelMatrix:
        """Build a symmetric matrix from great-circle distances and constant speed."""
        if not math.isfinite(self.speed_kilometers_per_hour) or self.speed_kilometers_per_hour <= 0:
            msg = "speed_kilometers_per_hour must be finite and positive"
            raise ValueError(msg)
        meters_per_second = self.speed_kilometers_per_hour / 3.6
        distances: list[tuple[int, ...]] = []
        durations: list[tuple[int, ...]] = []
        for origin in locations:
            distance_row: list[int] = []
            duration_row: list[int] = []
            for destination in locations:
                distance = _haversine_meters(origin.coordinate, destination.coordinate)
                distance_row.append(distance)
                duration_row.append(math.ceil(distance / meters_per_second))
            distances.append(tuple(distance_row))
            durations.append(tuple(duration_row))
        return TravelMatrix(
            location_ids=tuple(location.id for location in locations),
            durations_seconds=tuple(durations),
            distances_meters=tuple(distances),
        )
